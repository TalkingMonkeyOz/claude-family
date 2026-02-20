"""
Tests for the Task Lifecycle BPMN process (v2 - with session boundaries).

Tests all 7 logic paths through the task lifecycle:
  1. Happy path: Create → Work(complete) → Completed
  2. Discipline block: Create(no tasks) → Blocked
  3. Block + resolve: Work(block) → Resolve → Work(complete) → Completed
  4. Session end + fresh + resume: Work(session_end) → NotStale → Resume → Complete
  5. Session end + stale: Work(session_end) → Stale → Archived
  6. Session end + abandon: Work(session_end) → NotStale → Abandon → Archived
  7. Multiple session interrupts: session_end → resume → session_end → resume → complete

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run()
  - Gateway conditions are Python expressions eval'd against task.data
"""

import os
import pytest

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

def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
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
# Test 1: Happy Path (Create → Work → Complete)
# ---------------------------------------------------------------------------

class TestHappyPath:
    """Create task → sync → in_progress → work → complete → end."""

    def test_happy_path(self):
        wf = load_workflow()

        # Create task with tasks available
        complete_user_task(wf, "create_task", {"has_tasks": True})

        # Work on task, outcome = complete (default)
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "sync_to_db" in names
        assert "mark_in_progress" in names
        assert "mark_completed" in names
        assert "end_completed" in names
        assert "end_blocked" not in names
        assert "end_archived" not in names

        assert wf.data.get("synced") is True
        assert wf.data.get("status") == "completed"


# ---------------------------------------------------------------------------
# Test 2: Discipline Gate Blocks (no tasks)
# ---------------------------------------------------------------------------

class TestDisciplineGateBlocks:
    """has_tasks=False → gate blocked → end."""

    def test_discipline_gate_blocks(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": False})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "mark_gate_blocked" in names
        assert "end_blocked" in names
        assert "work_on_task" not in names
        assert "end_completed" not in names

        assert wf.data.get("gate_blocked") is True


# ---------------------------------------------------------------------------
# Test 3: Blocked → Resolve → Complete
# ---------------------------------------------------------------------------

class TestBlockAndResolve:
    """Work → block → resolve → work again → complete."""

    def test_block_then_resolve(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True})

        # First pass: blocked
        complete_user_task(wf, "work_on_task", {"action": "block"})
        assert "resolve_blocker" in ready_task_names(wf)

        # Resolve the blocker
        complete_user_task(wf, "resolve_blocker", {})
        assert "work_on_task" in ready_task_names(wf)

        # Second pass: complete
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "resolve_blocker" in names
        assert "mark_completed" in names
        assert "end_completed" in names
        assert wf.data.get("status") == "completed"


# ---------------------------------------------------------------------------
# Test 4: Session End → Fresh → Resume → Complete
# ---------------------------------------------------------------------------

class TestSessionEndResumeComplete:
    """
    Work → session ends → demote to pending → not stale → resume → work → complete.

    This is the cross-session lifecycle: a task survives a session boundary
    and gets picked up in the next session.
    """

    def test_session_end_resume_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True})

        # Working, then session ends
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 1,
            "staleness_threshold": 3,
        })

        # Engine should have run demote_to_pending and check_staleness scripts
        # age_days=1, threshold=3 → is_stale=False → resume_decision is READY
        assert "resume_decision" in ready_task_names(wf)

        # Claude decides to resume
        complete_user_task(wf, "resume_decision", {"decision": "resume"})

        # Should loop back to work_on_task via mark_in_progress
        assert "work_on_task" in ready_task_names(wf)

        # Now complete it
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "demote_to_pending" in names
        assert "check_staleness" in names
        assert "resume_decision" in names
        assert "mark_completed" in names
        assert "end_completed" in names
        assert "end_archived" not in names

        # Final status should be completed (set by mark_completed, overriding earlier statuses)
        assert wf.data.get("status") == "completed"


# ---------------------------------------------------------------------------
# Test 5: Session End → Stale → Archived
# ---------------------------------------------------------------------------

class TestSessionEndStaleArchived:
    """
    Work → session ends → demote → stale (age > threshold) → archive → end.

    This proves that old tasks get auto-archived instead of restored forever.
    """

    def test_stale_task_archived(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True})

        # Session ends, task is old (age_days=10 > threshold=3)
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 10,
            "staleness_threshold": 3,
        })

        # Engine should have run demote + staleness check → is_stale=True → archive
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "demote_to_pending" in names
        assert "check_staleness" in names
        assert "archive_task" in names
        assert "end_archived" in names
        assert "resume_decision" not in names  # skipped - went straight to archive

        assert wf.data.get("status") == "archived"


# ---------------------------------------------------------------------------
# Test 6: Session End → Fresh → Abandon → Archived
# ---------------------------------------------------------------------------

class TestSessionEndAbandon:
    """
    Work → session ends → not stale → Claude decides to abandon → archive.

    This covers the explicit abandonment path where a task is no longer relevant.
    """

    def test_abandon_task(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True})

        # Session ends, task is fresh
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 1,
            "staleness_threshold": 3,
        })

        assert "resume_decision" in ready_task_names(wf)

        # Claude decides to abandon
        complete_user_task(wf, "resume_decision", {"decision": "abandon"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "resume_decision" in names
        assert "archive_task" in names
        assert "end_archived" in names
        assert "end_completed" not in names

        assert wf.data.get("status") == "archived"


# ---------------------------------------------------------------------------
# Test 7: Multiple Session Interruptions
# ---------------------------------------------------------------------------

class TestMultipleSessionInterrupts:
    """
    Work → session_end → resume → work → session_end → resume → complete.

    Proves the loop works across multiple session boundaries.
    """

    def test_two_session_interrupts_then_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True})

        # --- Session 1: start working, session ends ---
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 0,
            "staleness_threshold": 3,
        })
        assert "resume_decision" in ready_task_names(wf)
        complete_user_task(wf, "resume_decision", {"decision": "resume"})

        # --- Session 2: resume working, session ends again ---
        assert "work_on_task" in ready_task_names(wf)
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 1,
            "staleness_threshold": 3,
        })
        assert "resume_decision" in ready_task_names(wf)
        complete_user_task(wf, "resume_decision", {"decision": "resume"})

        # --- Session 3: finally complete ---
        assert "work_on_task" in ready_task_names(wf)
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_completed" in names
        assert wf.data.get("status") == "completed"


# ---------------------------------------------------------------------------
# Test 8: Edge case - staleness at exact threshold boundary
# ---------------------------------------------------------------------------

class TestStalenessEdgeCases:
    """Boundary conditions for staleness calculation."""

    def test_at_threshold_not_stale(self):
        """age_days == threshold → is_stale should be False (> not >=)."""
        wf = load_workflow()
        complete_user_task(wf, "create_task", {"has_tasks": True})
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 3,
            "staleness_threshold": 3,
        })
        # age_days=3, threshold=3 → 3 > 3 is False → not stale
        assert "resume_decision" in ready_task_names(wf)

    def test_just_over_threshold_is_stale(self):
        """age_days > threshold → stale → auto-archived."""
        wf = load_workflow()
        complete_user_task(wf, "create_task", {"has_tasks": True})
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 4,
            "staleness_threshold": 3,
        })
        # age_days=4 > threshold=3 → stale → archive
        assert wf.is_completed()
        assert "archive_task" in completed_spec_names(wf)
        assert wf.data.get("status") == "archived"
