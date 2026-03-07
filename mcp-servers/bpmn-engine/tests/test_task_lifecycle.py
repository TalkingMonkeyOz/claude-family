"""
Tests for the Task Lifecycle BPMN process (v3 - multi-task, bridge, feature completion).

Tests all logic paths through the task lifecycle:
  1. Happy path: Create → Bridge → (no more tasks) → Work(complete) → FeatureCheck → Completed
  2. Multi-task loop: Create → Bridge → (more tasks) → Create → Bridge → (done) → Work → Complete
  3. Discipline block: Create → (no tasks) → Blocked
  4. Midway update: Work(update) → MidwayUpdate → Work(complete) → Completed
  5. Block + resolve: Work(block) → Resolve → Complete (resolve = done, no retry loop)
  6. Session end + resume: Work(session_end) → NotStale → Resume → Complete
  7. Session end + stale: Work(session_end) → Stale → Archived
  8. Session end + abandon: Work(session_end) → NotStale → Abandon → Archived
  9. Multiple session interrupts

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run()
  - Gateway conditions are Python expressions eval'd against task.data
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
    """Create task → bridge → (no more tasks) → sync → in_progress → work → feature_check → complete."""

    def test_happy_path(self):
        wf = load_workflow()

        # Create task with tasks available and no more tasks to create
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # Work on task, outcome = complete (default)
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "sync_to_db" in names
        assert "bridge_to_build_task" in names
        assert "mark_in_progress" in names
        assert "mark_completed" in names
        assert "check_feature_completion" in names
        assert "end_completed" in names
        assert "end_blocked" not in names
        assert "end_archived" not in names

        assert wf.data.get("synced") is True
        assert wf.data.get("bridge_attempted") is True
        assert wf.data.get("status") == "completed"
        assert wf.data.get("feature_completion_checked") is True


# ---------------------------------------------------------------------------
# Test 2: Multi-Task Loop
# ---------------------------------------------------------------------------

class TestMultiTaskLoop:
    """Create → bridge → (more tasks=True loop) → Create → bridge → (done) → Work → Complete."""

    def test_multi_task_loop(self):
        wf = load_workflow()

        # First create: signal there are more tasks to create
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": True})

        # Engine loops back to create_task
        assert "create_task" in ready_task_names(wf), (
            "create_task should loop back when has_more_tasks=True"
        )

        # Second create: no more tasks
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # Should proceed to work
        assert "work_on_task" in ready_task_names(wf)

        # Complete the task
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "mark_completed" in names
        assert "check_feature_completion" in names
        assert "end_completed" in names


# ---------------------------------------------------------------------------
# Test 3: Discipline Gate Blocks (no tasks)
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
        assert "work_on_task" not in names
        assert "end_completed" not in names

        assert wf.data.get("gate_blocked") is True


# ---------------------------------------------------------------------------
# Test 4: Midway Status Update
# ---------------------------------------------------------------------------

class TestMidwayUpdate:
    """Work → update → MidwayStatusUpdate → Work → complete."""

    def test_midway_update_then_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # First pass: midway update
        complete_user_task(wf, "work_on_task", {"action": "update"})

        # Engine runs midway_status_update and loops back to work_on_task
        assert not wf.is_completed(), "Should not be complete after midway update"
        assert "work_on_task" in ready_task_names(wf), (
            "work_on_task should be READY again after midway update"
        )

        names = completed_spec_names(wf)
        assert "midway_status_update" in names

        # Second pass: complete
        complete_user_task(wf, "work_on_task", {"action": "complete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "mark_completed" in names
        assert "check_feature_completion" in names
        assert wf.data.get("midway_updated") is True


# ---------------------------------------------------------------------------
# Test 5: Blocked → Resolve → Complete (resolve = done, no retry loop)
# ---------------------------------------------------------------------------

class TestBlockAndResolve:
    """Work → block → resolve → mark_completed (not back to work)."""

    def test_block_then_resolve_goes_to_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # First pass: blocked
        complete_user_task(wf, "work_on_task", {"action": "block"})
        assert "resolve_blocker" in ready_task_names(wf)

        # Resolve the blocker - goes directly to complete, NOT back to work_on_task
        complete_user_task(wf, "resolve_blocker", {})

        assert wf.is_completed(), (
            "Workflow should complete after resolve_blocker (resolve = done)"
        )
        names = completed_spec_names(wf)
        assert "resolve_blocker" in names
        assert "mark_completed" in names
        assert "check_feature_completion" in names
        assert "end_completed" in names
        assert wf.data.get("status") == "completed"


# ---------------------------------------------------------------------------
# Test 6: Session End → Fresh → Resume → Complete
# ---------------------------------------------------------------------------

class TestSessionEndResumeComplete:
    """
    Work → session ends → demote to pending → not stale → resume → work → complete.
    """

    def test_session_end_resume_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # Working, then session ends
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 1,
            "staleness_threshold": 3,
        })

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
        assert "check_feature_completion" in names
        assert "end_completed" in names
        assert "end_archived" not in names

        assert wf.data.get("status") == "completed"


# ---------------------------------------------------------------------------
# Test 7: Session End → Stale → Archived
# ---------------------------------------------------------------------------

class TestSessionEndStaleArchived:
    """Work → session ends → demote → stale (age > threshold) → archive → end."""

    def test_stale_task_archived(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

        # Session ends, task is old (age_days=10 > threshold=3)
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 10,
            "staleness_threshold": 3,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "demote_to_pending" in names
        assert "check_staleness" in names
        assert "archive_task" in names
        assert "end_archived" in names
        assert "resume_decision" not in names  # skipped - went straight to archive

        assert wf.data.get("status") == "archived"


# ---------------------------------------------------------------------------
# Test 8: Session End → Fresh → Abandon → Archived
# ---------------------------------------------------------------------------

class TestSessionEndAbandon:
    """Work → session ends → not stale → Claude decides to abandon → archive."""

    def test_abandon_task(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

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
# Test 9: Multiple Session Interruptions
# ---------------------------------------------------------------------------

class TestMultipleSessionInterrupts:
    """Work → session_end → resume → work → session_end → resume → complete."""

    def test_two_session_interrupts_then_complete(self):
        wf = load_workflow()

        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})

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
# Test 10: Edge case - staleness at exact threshold boundary
# ---------------------------------------------------------------------------

class TestStalenessEdgeCases:
    """Boundary conditions for staleness calculation."""

    def test_at_threshold_not_stale(self):
        """age_days == threshold → is_stale should be False (> not >=)."""
        wf = load_workflow()
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})
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
        complete_user_task(wf, "create_task", {"has_tasks": True, "has_more_tasks": False})
        complete_user_task(wf, "work_on_task", {
            "action": "session_end",
            "age_days": 4,
            "staleness_threshold": 3,
        })
        # age_days=4 > threshold=3 → stale → archive
        assert wf.is_completed()
        assert "archive_task" in completed_spec_names(wf)
        assert wf.data.get("status") == "archived"


# ---------------------------------------------------------------------------
# Test 11: New elements exist in model
# ---------------------------------------------------------------------------

class TestNewModelElements:
    """Verify new v3 elements are present in the BPMN model."""

    def test_new_elements_in_spec(self):
        """bridge_to_build_task, has_more_tasks_gw, check_feature_completion, midway_status_update present."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        task_spec_names = list(spec.task_specs.keys())

        assert "bridge_to_build_task" in task_spec_names, (
            "bridge_to_build_task scriptTask must exist"
        )
        assert "has_more_tasks_gw" in task_spec_names, (
            "has_more_tasks_gw gateway must exist"
        )
        assert "check_feature_completion" in task_spec_names, (
            "check_feature_completion scriptTask must exist"
        )
        assert "midway_status_update" in task_spec_names, (
            "midway_status_update scriptTask must exist"
        )

    def test_gate_blocked_and_staleness_names_in_bpmn_xml(self):
        """mark_gate_blocked and check_staleness should have updated display names in BPMN XML."""
        with open(BPMN_FILE, 'r', encoding='utf-8') as f:
            bpmn_content = f.read()
        # Discipline gate name should reference Discipline Gate with tool list
        assert "Discipline Gate" in bpmn_content, (
            "mark_gate_blocked name should include 'Discipline Gate' reference"
        )
        assert "GATED_TOOLS" in bpmn_content, (
            "mark_gate_blocked documentation should reference GATED_TOOLS"
        )
        # Staleness check should reference session_id matching in name
        assert "Session Staleness" in bpmn_content, (
            "check_staleness name should reference 'Session Staleness'"
        )
