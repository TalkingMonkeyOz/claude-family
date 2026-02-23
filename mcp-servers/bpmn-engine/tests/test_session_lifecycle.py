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

Process flow summary (updated 2026-02-24 - display-only resume):
  start_event -> session_start -> load_state -> has_prior_state_gateway
    [prior_state==True] -> display_session_summary -> has_prior_tasks_gateway
      [has_prior_tasks==True] -> display_prior_tasks -> prior_tasks_merge
      [default]               -> prior_tasks_merge
    -> work_merge_gateway
    [default] -> fresh_start -> work_merge_gateway
  -> do_work (user)
  -> work_action_gateway
    [action=="end_session"] -> save_summary -> close_session -> end_normal
    [action=="compact"]     -> save_checkpoint -> do_work (loop)
    [default]               -> do_work (loop, continue working)

Key change: "Restore Context" replaced with display-only flow.
Tasks are NOT restored via TaskCreate. Claude Code natively persists tasks
in ~/.claude/tasks/. DB todo restoration was creating zombie tasks.
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
        start_event -> session_start -> load_state
        -> has_prior_state_gateway [prior_state=False, default] -> fresh_start
        -> work_merge_gateway -> do_work
        -> work_action_gateway [action="end_session"] -> save_summary
        -> close_session -> end_normal
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

        # The display-only resume flow must NOT run on fresh start
        assert "display_session_summary" not in names, (
            "display_session_summary must NOT run on fresh start"
        )
        assert "display_prior_tasks" not in names, (
            "display_prior_tasks must NOT run on fresh start"
        )

        # Script tasks write flags into task.data; workflow.data contains the final state
        assert workflow.data.get("session_started") is True
        assert workflow.data.get("state_loaded") is True
        assert workflow.data.get("context") == "fresh"
        assert workflow.data.get("summary_saved") is True
        assert workflow.data.get("session_closed") is True


class TestResumedSession:
    """
    Prior state exists -> display_session_summary -> display_prior_tasks
    -> do_work -> end_session -> end_normal.

    Key change from old model: restore_context (which called TaskCreate to
    restore zombie tasks) is replaced with display-only scriptTasks that
    show the summary and prior tasks as informational text only.
    """

    def test_resumed_session_displays_context_with_tasks(self):
        """Resume with prior state AND prior tasks - both display steps run."""
        workflow = load_workflow()

        # Complete load_state with prior_state=True to take the resume path
        complete_user_task(workflow, "load_state", {
            "state_loaded": True,
            "prior_state": True,
            "has_prior_tasks": True,
        })

        # All scriptTasks auto-run (display_session_summary, gateway, display_prior_tasks)
        # Engine should advance all the way to do_work
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY after resume with tasks. Got: {ready_names}"
        )

        # End the session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "display_session_summary" in names, (
            "display_session_summary must run on resumed session"
        )
        assert "display_prior_tasks" in names, (
            "display_prior_tasks must run when has_prior_tasks=True"
        )
        assert "fresh_start" not in names, "fresh_start must NOT run on resumed session"
        assert "save_summary" in names
        assert "close_session" in names
        assert "end_normal" in names

        # Verify display flags were set (display-only, no task restoration)
        assert workflow.data.get("context_displayed") is True, (
            "display_session_summary should set context_displayed=True"
        )
        assert workflow.data.get("prior_tasks_displayed") is True, (
            "display_prior_tasks should set prior_tasks_displayed=True"
        )
        assert workflow.data.get("session_closed") is True

    def test_resumed_session_no_prior_tasks(self):
        """Resume with prior state but NO prior tasks - skip display_prior_tasks."""
        workflow = load_workflow()

        complete_user_task(workflow, "load_state", {
            "state_loaded": True,
            "prior_state": True,
            "has_prior_tasks": False,
        })

        # Should reach do_work, skipping display_prior_tasks
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY after resume without tasks. Got: {ready_names}"
        )

        complete_user_task(workflow, "do_work", {"action": "end_session"})
        assert workflow.is_completed()

        names = completed_spec_names(workflow)
        assert "display_session_summary" in names, (
            "display_session_summary must always run on resume"
        )
        assert "display_prior_tasks" not in names, (
            "display_prior_tasks must NOT run when has_prior_tasks=False"
        )
        assert workflow.data.get("context_displayed") is True
        assert workflow.data.get("prior_tasks_displayed") is not True, (
            "prior_tasks_displayed should NOT be set when tasks were skipped"
        )


class TestCompactAndContinue:
    """
    do_work with action="compact" -> save_checkpoint -> loop back to do_work
    -> action="end_session" -> end_normal.
    """

    def test_compact_then_end_session(self):
        workflow = load_workflow()

        # Complete load_state with fresh start (no prior state)
        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # Should be at do_work (fresh start path)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names

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
        assert "save_checkpoint" in comp_names

        # Second do_work pass: end session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed after end_session"

        names = completed_spec_names(workflow)
        assert "save_summary" in names
        assert "close_session" in names
        assert "end_normal" in names
        assert workflow.data.get("checkpoint_saved") is True
        assert workflow.data.get("summary_saved") is True
        assert workflow.data.get("session_closed") is True

    def test_continue_work_loops_back(self):
        """
        do_work with the default action (no action key set, triggers default flow)
        loops back to do_work, then end_session completes the workflow.
        """
        workflow = load_workflow()

        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # First do_work pass: continue (default flow)
        complete_user_task(workflow, "do_work", {"action": "continue"})

        assert not workflow.is_completed()

        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names

        # Second pass: end session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed()

        names = completed_spec_names(workflow)
        assert "end_normal" in names
        assert "save_checkpoint" not in names


class TestNoTaskRestoration:
    """
    Explicitly verify that the old restore_context element is gone
    and that no TaskCreate-style restoration happens.

    This is the key regression test for the zombie task fix.
    """

    def test_old_restore_context_element_does_not_exist(self):
        """The old 'restore_context' userTask must not exist in the process."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        task_spec_names = list(spec.task_specs.keys())
        assert "restore_context" not in task_spec_names, (
            "The old 'restore_context' userTask must be removed. "
            "It has been replaced with display-only scriptTasks: "
            "display_session_summary and display_prior_tasks."
        )

    def test_resume_path_is_all_script_tasks(self):
        """
        The resume path should be all scriptTasks (automated), not userTasks.
        This ensures no manual intervention (like TaskCreate) is needed
        during the resume flow. The first userTask should be do_work.
        """
        workflow = load_workflow()

        complete_user_task(workflow, "load_state", {
            "state_loaded": True,
            "prior_state": True,
            "has_prior_tasks": True,
        })

        # After load_state with prior_state=True, the engine should auto-run
        # through all scriptTasks and stop at do_work (the first userTask).
        # If any element in the resume path were a userTask, the engine
        # would stop there instead.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert ready_names == ["do_work"], (
            f"After resume, only do_work should be READY (all resume steps are automated). "
            f"Got: {ready_names}"
        )
