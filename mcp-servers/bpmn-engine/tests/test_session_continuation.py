"""
Tests for the Session Continuation BPMN process.

Uses SpiffWorkflow 3.x API directly against the session_continuation.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Process flow summary:
  start -> initiate_compaction (user, seeds session_id_changed + critical_context_lost)
        -> precompact_inject (script, work_items_injected=True)
        -> save_checkpoint (script, checkpoint_saved=True)
        -> context_compacted (script, context_compacted=True)
        -> session_id_gateway
             [session_id_changed==True] -> log_continuation_warning
                                        -> reload_session_facts
                                        -> verify_task_map
                                        -> continuation_merge
             [default/same session]     -> continuation_merge
        -> context_loss_gateway
             [critical_context_lost==True] -> manual_recovery (user) -> end_recovered
             [default/context ok]          -> resume_work (user)     -> end_resumed
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "session_continuation.bpmn")
)
PROCESS_ID = "session_continuation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past the start event - stops at initiate_compaction (first user task)
    wf.do_engine_steps()
    return wf


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() so the engine advances through any subsequent automated
    tasks (script tasks, gateways) until the next user task or end event.

    Raises AssertionError if the task is not currently READY.
    """
    tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
    target = [t for t in tasks if t.task_spec.name == task_name]
    assert target, (
        f"No READY manual task named '{task_name}'. "
        f"Ready: {[t.task_spec.name for t in tasks]}"
    )
    task = target[0]
    if data:
        task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_names(workflow: BpmnWorkflow) -> set:
    """Return the spec names of all COMPLETED tasks in the workflow as a set."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSameSessionContinues:
    """
    Same session (no session ID change), no context loss.

    session_id_changed=False, critical_context_lost=False
    -> session_id_gateway takes default (flow_same_session)
    -> continuation_merge
    -> context_loss_gateway takes default (flow_context_ok)
    -> resume_work
    -> end_resumed

    Verifies:
    - log_continuation_warning NOT completed (new-session branch skipped)
    - reload_session_facts NOT completed
    - verify_task_map NOT completed
    - resume_work completed
    - end_resumed reached
    - workflow.data flags set by script tasks
    """

    def test_same_session_skips_continuation_branch(self):
        workflow = load_workflow()

        # Engine stops at initiate_compaction (first user task).
        # Set both gateway variables here so all downstream gateways can evaluate them.
        complete_user_task(workflow, "initiate_compaction", {
            "session_id_changed": False,
            "critical_context_lost": False,
        })

        # Script tasks auto-run; engine stops at resume_work (user task).
        ready_tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
        ready_task_names = [t.task_spec.name for t in ready_tasks]
        assert "resume_work" in ready_task_names, (
            f"Expected resume_work to be READY after same-session path. Got: {ready_task_names}"
        )

        complete_user_task(workflow, "resume_work", {})

        assert workflow.is_completed(), "Workflow should be completed after resume_work"

        names = completed_names(workflow)
        assert "log_continuation_warning" not in names, (
            "log_continuation_warning must NOT run on same-session path"
        )
        assert "reload_session_facts" not in names, (
            "reload_session_facts must NOT run on same-session path"
        )
        assert "verify_task_map" not in names, (
            "verify_task_map must NOT run on same-session path"
        )
        assert "resume_work" in names, "resume_work must be completed"
        assert "end_resumed" in names, "end_resumed must be reached"
        assert "end_recovered" not in names, "end_recovered must NOT be reached"

        # Verify script task flags
        assert workflow.data.get("work_items_injected") is True, (
            "precompact_inject should have set work_items_injected=True"
        )
        assert workflow.data.get("checkpoint_saved") is True, (
            "save_checkpoint should have set checkpoint_saved=True"
        )
        assert workflow.data.get("context_compacted") is True, (
            "context_compacted script should have set context_compacted=True"
        )


class TestContinuationSession:
    """
    New session ID detected (compaction created a new session), no context loss.

    session_id_changed=True, critical_context_lost=False
    -> session_id_gateway takes flow_new_session branch
    -> log_continuation_warning, reload_session_facts, verify_task_map (all script tasks)
    -> continuation_merge
    -> context_loss_gateway takes default (flow_context_ok)
    -> resume_work
    -> end_resumed

    Verifies:
    - log_continuation_warning completed (continuation_logged=True)
    - reload_session_facts completed (facts_reloaded=True)
    - verify_task_map completed (task_map_valid=True)
    - resume_work completed
    - end_resumed reached
    - end_recovered NOT reached
    """

    def test_continuation_session_runs_warning_and_reload(self):
        workflow = load_workflow()

        # Seed both gateway variables: new session, but context is intact
        complete_user_task(workflow, "initiate_compaction", {
            "session_id_changed": True,
            "critical_context_lost": False,
        })

        # All new-session script tasks auto-run; engine stops at resume_work (user task)
        ready_tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
        ready_task_names = [t.task_spec.name for t in ready_tasks]
        assert "resume_work" in ready_task_names, (
            f"Expected resume_work to be READY after new-session path. Got: {ready_task_names}"
        )

        complete_user_task(workflow, "resume_work", {})

        assert workflow.is_completed(), "Workflow should be completed after resume_work"

        names = completed_names(workflow)
        assert "log_continuation_warning" in names, (
            "log_continuation_warning must be completed on new-session path"
        )
        assert "reload_session_facts" in names, (
            "reload_session_facts must be completed on new-session path"
        )
        assert "verify_task_map" in names, (
            "verify_task_map must be completed on new-session path"
        )
        assert "resume_work" in names, "resume_work must be completed"
        assert "end_resumed" in names, "end_resumed must be reached"
        assert "end_recovered" not in names, "end_recovered must NOT be reached"

        # Verify script task flags written by the new-session branch
        assert workflow.data.get("continuation_logged") is True, (
            "log_continuation_warning should have set continuation_logged=True"
        )
        assert workflow.data.get("facts_reloaded") is True, (
            "reload_session_facts should have set facts_reloaded=True"
        )
        assert workflow.data.get("task_map_valid") is True, (
            "verify_task_map should have set task_map_valid=True"
        )


class TestContextLossRecovery:
    """
    New session ID AND critical context was lost during compaction.

    session_id_changed=True, critical_context_lost=True
    -> session_id_gateway takes flow_new_session branch
    -> log_continuation_warning, reload_session_facts, verify_task_map
    -> continuation_merge
    -> context_loss_gateway takes flow_context_lost branch
    -> manual_recovery (user task)
    -> end_recovered

    Verifies:
    - manual_recovery completed
    - resume_work NOT completed (context-ok branch skipped)
    - end_recovered reached
    - end_resumed NOT reached
    """

    def test_context_loss_routes_to_manual_recovery(self):
        workflow = load_workflow()

        # Seed both gateway variables: new session AND critical context lost
        complete_user_task(workflow, "initiate_compaction", {
            "session_id_changed": True,
            "critical_context_lost": True,
        })

        # Script tasks auto-run; engine stops at manual_recovery (user task)
        ready_tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
        ready_task_names = [t.task_spec.name for t in ready_tasks]
        assert "manual_recovery" in ready_task_names, (
            f"Expected manual_recovery to be READY after context loss path. Got: {ready_task_names}"
        )

        complete_user_task(workflow, "manual_recovery", {})

        assert workflow.is_completed(), "Workflow should be completed after manual_recovery"

        names = completed_names(workflow)
        assert "manual_recovery" in names, "manual_recovery must be completed"
        assert "end_recovered" in names, "end_recovered must be reached"
        assert "resume_work" not in names, (
            "resume_work must NOT be completed on context-loss path"
        )
        assert "end_resumed" not in names, "end_resumed must NOT be reached"

        # New-session branch tasks should also have run
        assert "log_continuation_warning" in names, (
            "log_continuation_warning must be completed (new-session path ran)"
        )
        assert "reload_session_facts" in names, (
            "reload_session_facts must be completed (new-session path ran)"
        )
        assert "verify_task_map" in names, (
            "verify_task_map must be completed (new-session path ran)"
        )
