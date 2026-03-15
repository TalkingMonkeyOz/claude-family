"""
Tests for the Task Lifecycle BPMN process (v4 - startup read-back, no staleness).

v4 Changes:
  - NEW: Startup phase tests (read from DB → inject context → existing tasks check)
  - REMOVED: Staleness tests (no time-based auto-archive — holiday-safe)
  - UPDATED: Session end goes directly to resume_decision (no staleness gate)

Tests all logic paths:
  1. Startup with existing tasks: Start → ReadDB → InjectContext → (existing) → Work → Complete
  2. Startup with no existing tasks: Start → ReadDB → InjectContext → (none) → Create → Work → Complete
  3. Multi-task loop: Create → (more) → Create → (done) → Work → Complete
  4. Discipline block: (no tasks) → Blocked
  5. Midway update: Work(update) → MidwayUpdate → Work(complete) → Completed
  6. Block + resolve: Work(block) → Resolve → Complete
  7. Session end + resume: Work(session_end) → Demote → Resume → Work → Complete
  8. Session end + abandon: Work(session_end) → Demote → Abandon → Archived
  9. Multiple session interrupts
  10. Completed tasks read back on next startup
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "task_lifecycle.bpmn")
)
PROCESS_ID = "task_lifecycle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance.

    initial_data: Optional dict to seed workflow data before engine steps.
    Used to control gateway conditions in startup phase (e.g., tasks_loaded=True).
    """
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    if initial_data:
        # Seed data into the start task so script tasks can read it
        start_tasks = wf.get_tasks(state=TaskState.READY)
        for t in start_tasks:
            t.data.update(initial_data)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(workflow: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(workflow)]


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    """Find named READY user task, merge data, run it, advance engine."""
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return spec names of all COMPLETED tasks."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Test 1: Startup with existing tasks → Work → Complete
# ---------------------------------------------------------------------------

class TestStartupWithExistingTasks:
    """Session starts → reads tasks from DB → has existing → work → complete."""

    def test_startup_existing_tasks_happy_path(self):
        wf = load_workflow(initial_data={"tasks_loaded": True, "has_tasks": True})

        # Startup phase auto-runs (script tasks), existing_tasks_gw sees tasks_loaded=True
        # Goes to has_tasks_gw → has_tasks=True → mark_in_progress → work_on_task
        names = completed_spec_names(wf)
        assert "read_tasks_from_db" in names, "Should have read tasks from DB"
        assert "read_completed_history" in names, "Should have read completed history"
        assert "inject_task_context" in names, "Should have injected context"

        # Should be ready to work (skipped create_task entirely)
        assert "work_on_task" in ready_task_names(wf), "Should go straight to work with existing tasks"
        assert "create_task" not in completed_spec_names(wf), "Should NOT have gone through create_task"

        # Complete the task
        complete_user_task(wf, "work_on_task", {"action": "complete"})
        assert wf.is_completed()
        assert "end_completed" in completed_spec_names(wf)


# ---------------------------------------------------------------------------
# Test 2: Startup with no existing tasks → Create → Work → Complete
# ---------------------------------------------------------------------------

class TestStartupNoExistingTasks:
    """Session starts → reads tasks from DB → none found → create → work → complete."""

    def test_startup_create_then_complete(self):
        wf = load_workflow()

        # Engine auto-runs startup phase. Default path: tasks_loaded is falsy → create_task
        # Create a task
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # Work on it
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "read_tasks_from_db" in names
        assert "inject_task_context" in names
        assert "sync_to_db" in names
        assert "mark_completed" in names
        assert "end_completed" in names


# ---------------------------------------------------------------------------
# Test 3: Multi-Task Loop
# ---------------------------------------------------------------------------

class TestMultiTaskLoop:
    """Create → bridge → (more tasks=True loop) → Create → bridge → (done) → Work → Complete."""

    def test_multi_task_loop(self):
        wf = load_workflow()

        # First create: more tasks
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": True})
        assert "create_task" in ready_task_names(wf)

        # Second create: no more
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})
        assert "work_on_task" in ready_task_names(wf)

        # Complete
        complete_user_task(wf, "work_on_task", {"action": "complete"})
        assert wf.is_completed()
        assert "end_completed" in completed_spec_names(wf)


# ---------------------------------------------------------------------------
# Test 4: Discipline Gate Blocks (no tasks)
# ---------------------------------------------------------------------------

class TestDisciplineGateBlocks:
    """has_tasks=False → gate blocked → end."""

    def test_discipline_gate_blocks(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": False, "has_more_tasks": False})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "mark_gate_blocked" in names
        assert "end_blocked" in names
        assert wf.data.get("gate_blocked") is True


# ---------------------------------------------------------------------------
# Test 5: Midway Status Update
# ---------------------------------------------------------------------------

class TestMidwayUpdate:
    """Work → update → MidwayStatusUpdate → Work → complete."""

    def test_midway_update_then_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})
        complete_user_task(wf, "work_on_task", {"action": "update"})

        assert "work_on_task" in ready_task_names(wf)

        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        assert wf.data.get("midway_updated") is True


# ---------------------------------------------------------------------------
# Test 6: Blocked → Resolve → Complete
# ---------------------------------------------------------------------------

class TestBlockAndResolve:
    """Work → block → resolve → mark_completed."""

    def test_block_then_resolve(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})
        complete_user_task(wf, "work_on_task", {"action": "block"})
        assert "resolve_blocker" in ready_task_names(wf)

        complete_user_task(wf, "resolve_blocker", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "resolve_blocker" in names
        assert "mark_completed" in names
        assert "end_completed" in names


# ---------------------------------------------------------------------------
# Test 7: Session End → Resume → Complete (no staleness — holiday-safe)
# ---------------------------------------------------------------------------

class TestSessionEndResumeComplete:
    """Work → session ends → demote → resume → work → complete.
    No staleness check — tasks persist indefinitely."""

    def test_session_end_resume_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})
        complete_user_task(wf, "work_on_task", {"action": "session_end"})

        # Goes directly to resume_decision (no staleness gate)
        assert "resume_decision" in ready_task_names(wf)

        complete_user_task(wf, "resume_decision", {"decision": "resume"})
        assert "work_on_task" in ready_task_names(wf)

        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "demote_to_pending" in names
        assert "resume_decision" in names
        assert "mark_completed" in names
        assert "end_completed" in names


# ---------------------------------------------------------------------------
# Test 8: Session End → Abandon → Archived
# ---------------------------------------------------------------------------

class TestSessionEndAbandon:
    """Work → session ends → demote → abandon → archive."""

    def test_abandon_task(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})
        complete_user_task(wf, "work_on_task", {"action": "session_end"})

        assert "resume_decision" in ready_task_names(wf)

        complete_user_task(wf, "resume_decision", {"decision": "abandon"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "archive_task" in names
        assert "end_archived" in names
        assert wf.data.get("status") == "archived"


# ---------------------------------------------------------------------------
# Test 9: Multiple Session Interruptions (holiday scenario)
# ---------------------------------------------------------------------------

class TestMultipleSessionInterrupts:
    """Work → session_end → resume → work → session_end → resume → complete.
    No staleness — tasks survive any number of session boundaries."""

    def test_two_session_interrupts_then_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # Session 1: start working, session ends
        complete_user_task(wf, "work_on_task", {"action": "session_end"})
        complete_user_task(wf, "resume_decision", {"decision": "resume"})

        # Session 2: resume, session ends again
        complete_user_task(wf, "work_on_task", {"action": "session_end"})
        complete_user_task(wf, "resume_decision", {"decision": "resume"})

        # Session 3: complete
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        assert "end_completed" in completed_spec_names(wf)


# ---------------------------------------------------------------------------
# Test 10: New v4 startup elements exist in model
# ---------------------------------------------------------------------------

class TestV4ModelElements:
    """Verify new v4 elements are present in the BPMN model."""

    def test_startup_elements_in_spec(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        task_spec_names = list(spec.task_specs.keys())

        assert "read_tasks_from_db" in task_spec_names, "read_tasks_from_db must exist"
        assert "read_completed_history" in task_spec_names, "read_completed_history must exist"
        assert "inject_task_context" in task_spec_names, "inject_task_context must exist"
        assert "existing_tasks_gw" in task_spec_names, "existing_tasks_gw must exist"

    def test_staleness_removed(self):
        """Staleness check and staleness gateway should NOT exist in v4."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        task_spec_names = list(spec.task_specs.keys())

        assert "check_staleness" not in task_spec_names, "check_staleness should be removed in v4"
        assert "staleness_gw" not in task_spec_names, "staleness_gw should be removed in v4"

    def test_no_time_based_archive_in_bpmn(self):
        """No staleness_threshold or age_days references in BPMN XML."""
        with open(BPMN_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "staleness_threshold" not in content, "No staleness_threshold in v4"
        assert "age_days" not in content, "No age_days in v4"
