"""
Tests for the Session Lifecycle BPMN process.

Uses SpiffWorkflow 3.x API directly against the session_lifecycle.bpmn definition.
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
  start_event → session_start → load_state → has_prior_state_gateway
    [prior_state==True] → restore_context (user) → work_merge_gateway
    [default]           → fresh_start (script)    → work_merge_gateway
  → do_work (user)
  → work_action_gateway
    [action=="end_session"] → save_summary → close_session → end_normal
    [action=="compact"]     → save_checkpoint → do_work (loop)
    [default]               → do_work (loop, continue working)
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "session_lifecycle.bpmn")
)
PROCESS_ID = "session_lifecycle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past any initial automated steps (script tasks, start event)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() so the engine advances through any subsequent automated
    tasks (script tasks, gateways) until the next user task or end event.

    Raises AssertionError if the task is not currently READY.
    """
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected user task '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return the spec names of all COMPLETED tasks in the workflow."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFreshSession:
    """
    No prior state -> fresh_start -> do_work -> end_session -> end_normal.

    Flow:
        start_event → session_start → load_state
        → has_prior_state_gateway [prior_state=False, default] → fresh_start
        → work_merge_gateway → do_work
        → work_action_gateway [action="end_session"] → save_summary
        → close_session → end_normal
    """

    def test_fresh_session_completes_normally(self):
        workflow = load_workflow()

        # Engine has run session_start (script), stops at load_state (user task).
        # Complete load_state with prior_state=False to take the fresh_start path.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "load_state" in ready_names, (
            f"Expected load_state to be READY. Got: {ready_names}"
        )

        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # fresh_start script auto-runs, merge gateway passes through, stops at do_work
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY after fresh start. Got: {ready_names}"
        )

        # Complete do_work with action="end_session" to end the session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed after end_session"

        names = completed_spec_names(workflow)
        assert "session_start" in names, "session_start script must have run"
        assert "load_state" in names, "load_state script must have run"
        assert "fresh_start" in names, "fresh_start script must have run"
        assert "save_summary" in names, "save_summary script must have run"
        assert "close_session" in names, "close_session script must have run"
        assert "end_normal" in names, "end_normal end event must be reached"
        assert "restore_context" not in names, "restore_context must NOT run on fresh start"

        # Script tasks write flags into task.data; workflow.data contains the final state
        assert workflow.data.get("session_started") is True, (
            "session_start should have set session_started=True"
        )
        assert workflow.data.get("state_loaded") is True, (
            "load_state should have set state_loaded=True"
        )
        assert workflow.data.get("context") == "fresh", (
            "fresh_start should have set context='fresh'"
        )
        assert workflow.data.get("summary_saved") is True, (
            "save_summary should have set summary_saved=True"
        )
        assert workflow.data.get("session_closed") is True, (
            "close_session should have set session_closed=True"
        )


class TestResumedSession:
    """
    Prior state exists -> restore_context -> do_work -> end_session -> end_normal.

    Flow:
        start_event → session_start → load_state
        → has_prior_state_gateway [prior_state=True] → restore_context (user task)
        → work_merge_gateway → do_work
        → work_action_gateway [action="end_session"] → save_summary
        → close_session → end_normal
    """

    def test_resumed_session_restores_context(self):
        workflow = load_workflow()

        # Complete load_state with prior_state=True to take the restore_context path
        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": True})

        # Engine stops at restore_context (user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "restore_context" in ready_names, (
            f"Expected restore_context to be READY when prior_state=True. Got: {ready_names}"
        )

        # Complete restore_context to proceed
        complete_user_task(workflow, "restore_context", {})

        # Engine should now be at do_work
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY after restore_context. Got: {ready_names}"
        )

        # End the session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "restore_context" in names, "restore_context must have been completed"
        assert "fresh_start" not in names, "fresh_start must NOT run on resumed session"
        assert "save_summary" in names, "save_summary must have run"
        assert "close_session" in names, "close_session must have run"
        assert "end_normal" in names, "end_normal must be reached"

        assert workflow.data.get("session_closed") is True, (
            "close_session should have set session_closed=True"
        )


class TestCompactAndContinue:
    """
    do_work with action="compact" -> save_checkpoint -> loop back to do_work
    -> action="end_session" -> end_normal.

    Flow:
        ... (fresh start path) ...
        → do_work [action="compact"] → save_checkpoint → do_work (loop)
        → do_work [action="end_session"] → save_summary → close_session → end_normal
    """

    def test_compact_then_end_session(self):
        workflow = load_workflow()

        # Complete load_state with fresh start (no prior state)
        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # Should be at do_work (fresh start path)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY at start. Got: {ready_names}"
        )

        # First do_work pass: compact
        complete_user_task(workflow, "do_work", {"action": "compact"})

        # Engine runs save_checkpoint and loops back to do_work
        assert not workflow.is_completed(), "Workflow must NOT be completed after compact"

        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY again after compact loop. Got: {ready_names}"
        )

        # Verify checkpoint was saved
        comp_names = completed_spec_names(workflow)
        assert "save_checkpoint" in comp_names, (
            "save_checkpoint script must have run after compact action"
        )

        # Second do_work pass: end session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed after end_session"

        names = completed_spec_names(workflow)
        assert "save_summary" in names, "save_summary must have run"
        assert "close_session" in names, "close_session must have run"
        assert "end_normal" in names, "end_normal must be reached"

        assert workflow.data.get("checkpoint_saved") is True, (
            "save_checkpoint should have set checkpoint_saved=True"
        )
        assert workflow.data.get("summary_saved") is True, (
            "save_summary should have set summary_saved=True"
        )
        assert workflow.data.get("session_closed") is True, (
            "close_session should have set session_closed=True"
        )

    def test_continue_work_loops_back(self):
        """
        do_work with the default action (no action key set, triggers default flow)
        loops back to do_work, then end_session completes the workflow.
        """
        workflow = load_workflow()

        # Complete load_state with fresh start
        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # First do_work pass: no action - triggers the default continue flow
        # We pass action="continue" which does NOT match "end_session" or "compact",
        # so the default flow fires.
        complete_user_task(workflow, "do_work", {"action": "continue"})

        assert not workflow.is_completed(), "Workflow must NOT be completed after continue"

        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY again after continue loop. Got: {ready_names}"
        )

        # Second pass: end session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed after end_session"

        names = completed_spec_names(workflow)
        assert "end_normal" in names, "end_normal must be reached"
        assert "save_checkpoint" not in names, (
            "save_checkpoint must NOT run on continue (non-compact) path"
        )
