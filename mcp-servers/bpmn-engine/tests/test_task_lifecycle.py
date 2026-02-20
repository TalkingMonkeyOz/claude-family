"""
Tests for the Task Lifecycle BPMN process.

Uses SpiffWorkflow 3.x API directly against the task_lifecycle.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "task_lifecycle.bpmn")
)
PROCESS_ID = "task_lifecycle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past any initial automated steps (e.g. the start event)
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


class TestHappyPath:
    """
    Create task → sync → work on it → complete it.

    Flow:
        start_event → create_task → sync_to_db
        → has_tasks_gateway [has_tasks=True] → work_on_task
        → task_action_gateway [default/complete] → mark_completed
        → end_completed
    """

    def test_happy_path(self):
        workflow = load_workflow()

        # --- Create Task ---------------------------------------------------
        # has_tasks=True routes through the "Yes" branch of has_tasks_gateway.
        # action="complete" routes through the default branch of task_action_gateway.
        complete_user_task(workflow, "create_task", {"has_tasks": True})

        # --- Work on Task --------------------------------------------------
        # Explicitly pass action="complete" so the gateway condition "action == 'block'"
        # evaluates to False and the default (complete) branch fires.
        complete_user_task(workflow, "work_on_task", {"action": "complete"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "sync_to_db" in names, "sync_to_db script must have run"
        assert "mark_completed" in names, "mark_completed script must have run"
        assert "end_completed" in names, "end_completed end event must be reached"
        assert "end_blocked" not in names, "end_blocked must NOT be reached"

        # Script tasks write to task.data; the final end-event task inherits the
        # full data chain, and workflow._mark_complete() copies it into workflow.data.
        assert workflow.data.get("synced") is True, (
            "sync_to_db should have set synced=True in task data"
        )
        assert workflow.data.get("status") == "completed", (
            "mark_completed should have set status='completed'"
        )


class TestDisciplineGateBlocks:
    """
    has_tasks=False routes through the 'No' branch → Blocked by Discipline Gate.

    Flow:
        start_event → create_task → sync_to_db
        → has_tasks_gateway [has_tasks=False, default branch] → mark_gate_blocked
        → end_blocked
    """

    def test_discipline_gate_blocks(self):
        workflow = load_workflow()

        # has_tasks=False routes to the default (no-tasks) branch
        complete_user_task(workflow, "create_task", {"has_tasks": False})

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "mark_gate_blocked" in names, "mark_gate_blocked script must have run"
        assert "end_blocked" in names, "end_blocked end event must be reached"
        assert "work_on_task" not in names, "work_on_task must NOT be executed"
        assert "end_completed" not in names, "end_completed must NOT be reached"

        assert workflow.data.get("gate_blocked") is True, (
            "mark_gate_blocked should have set gate_blocked=True"
        )


class TestTaskBlockedThenCompleted:
    """
    Work on task → hit blocker → resolve blocker → loop back → complete.

    Flow:
        start_event → create_task → sync_to_db
        → has_tasks_gateway [True] → work_on_task
        → task_action_gateway [action="block"] → resolve_blocker
        → work_on_task (second pass)
        → task_action_gateway [action="complete"] → mark_completed
        → end_completed
    """

    def test_task_blocked_then_completed(self):
        workflow = load_workflow()

        # --- Create Task ---------------------------------------------------
        complete_user_task(workflow, "create_task", {"has_tasks": True})

        # --- First pass: block the task ------------------------------------
        complete_user_task(workflow, "work_on_task", {"action": "block"})

        # Engine should stop at resolve_blocker (a user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "resolve_blocker" in ready_names, (
            f"resolve_blocker should be READY after blocking, got: {ready_names}"
        )

        # --- Resolve the blocker ------------------------------------------
        complete_user_task(workflow, "resolve_blocker", {})

        # Should loop back to work_on_task
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "work_on_task" in ready_names, (
            f"work_on_task should be READY after resolving blocker, got: {ready_names}"
        )

        # --- Second pass: complete the task --------------------------------
        # Explicitly set action="complete" to override the inherited action="block"
        complete_user_task(workflow, "work_on_task", {"action": "complete"})

        # --- Final assertions ----------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after second pass"

        names = completed_spec_names(workflow)
        assert "resolve_blocker" in names, "resolve_blocker must have been completed"
        assert "mark_completed" in names, "mark_completed script must have run"
        assert "end_completed" in names, "end_completed must be reached"
        assert "end_blocked" not in names, "end_blocked must NOT be reached"

        assert workflow.data.get("status") == "completed", (
            "Final status should be 'completed'"
        )
