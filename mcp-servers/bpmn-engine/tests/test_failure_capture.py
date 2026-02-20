"""
Tests for the Failure Capture Pipeline BPMN process.

Validates the self-improvement loop:
  1. Happy path: failure → JSONL → DB(new feedback) → surface → Claude fixes → resolved
  2. DB unavailable: failure → JSONL only → end
  3. Duplicate: failure → JSONL → DB(duplicate found) → reuse → surface → deferred
  4. Fix now: Claude sees failure → follows SCP → resolves feedback
  5. Defer: Claude sees failure → triages → deferred (resurfaces next prompt)
  6. New feedback + defer: Full path through new feedback creation → defer

Implementation mapping:
  - log_to_jsonl → failure_capture.py write to process_failures.jsonl
  - check_duplicate → SELECT from claude.feedback WHERE title LIKE 'Auto: %'
  - create_feedback → INSERT into claude.feedback (type=bug)
  - wait_for_prompt → rag_query_hook.py get_pending_failures()
  - follow_scp → system_change_process.bpmn (callActivity conceptually)
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "failure_capture.bpmn")
)
PROCESS_ID = "failure_capture"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow with optional seeded data.

    Uses the SpiffWorkflow 3.1.x pattern: seed data on the BPMN start event
    task so it propagates to child tasks during execution.
    """
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    if initial_data:
        start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
        assert start_tasks, "Could not find BPMN start event"
        start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(workflow: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(workflow)]


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """Find named READY user task, merge data, run it, advance engine."""
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Happy Path - Full capture + fix
# ---------------------------------------------------------------------------

class TestHappyPath:
    """Failure → JSONL → new feedback → surface → Claude fixes → resolved."""

    def test_full_capture_and_fix(self):
        wf = load_workflow({
            "db_available": True,
            "is_duplicate": False,
            "action": "fix_now",
        })

        # Phase 1-2: log_to_jsonl → db_available(yes) → check_duplicate → not dup → create_feedback
        # Phase 3: surface_merge → wait_for_prompt → claude_sees_failure (userTask)
        assert "claude_sees_failure" in ready_task_names(wf)

        # Verify path taken via completed task names (wf.data empty until completion in 3.1.x)
        names = completed_spec_names(wf)
        assert "log_to_jsonl" in names
        assert "check_duplicate" in names
        assert "create_feedback" in names
        assert "wait_for_prompt" in names
        assert "reuse_existing" not in names  # New feedback, not duplicate

        # Phase 4: Claude fixes
        complete_user_task(wf, "claude_sees_failure")
        # action=fix_now → follow_scp
        complete_user_task(wf, "follow_scp")
        # resolve_feedback script → end_resolved

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "follow_scp" in names
        assert "resolve_feedback" in names
        assert "end_resolved" in names
        assert wf.data.get("resolved") is True


# ---------------------------------------------------------------------------
# Test 2: DB Unavailable
# ---------------------------------------------------------------------------

class TestDBUnavailable:
    """Failure → JSONL → DB unavailable → end (logged only)."""

    def test_db_down_logs_only(self):
        wf = load_workflow({
            "db_available": False,
        })

        # Should complete immediately (all scriptTasks)
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "log_to_jsonl" in names
        assert "log_db_failure" in names
        assert "end_logged_only" in names

        # Feedback NOT filed
        assert "check_duplicate" not in names
        assert "create_feedback" not in names
        assert wf.data.get("feedback_filed") is False
        assert wf.data.get("db_available") is False


# ---------------------------------------------------------------------------
# Test 3: Duplicate Feedback
# ---------------------------------------------------------------------------

class TestDuplicateFeedback:
    """Failure → JSONL → DB(duplicate) → reuse existing → surface → defer."""

    def test_duplicate_reuses_existing(self):
        wf = load_workflow({
            "db_available": True,
            "is_duplicate": True,
            "action": "defer",
        })

        # Should reach claude_sees_failure
        assert "claude_sees_failure" in ready_task_names(wf)

        # Verify path: duplicate detected, reuse existing (not create new)
        names = completed_spec_names(wf)
        assert "check_duplicate" in names
        assert "reuse_existing" in names
        assert "create_feedback" not in names  # Skipped - duplicate

        # Claude defers
        complete_user_task(wf, "claude_sees_failure")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "mark_triaged" in names
        assert "end_deferred" in names
        assert wf.data.get("triaged") is True


# ---------------------------------------------------------------------------
# Test 4: Fix Now Path
# ---------------------------------------------------------------------------

class TestFixNow:
    """Claude sees failure → follows system-change-process → resolves."""

    def test_fix_now_resolves(self):
        wf = load_workflow({
            "db_available": True,
            "is_duplicate": False,
            "action": "fix_now",
        })

        complete_user_task(wf, "claude_sees_failure")
        assert "follow_scp" in ready_task_names(wf)

        complete_user_task(wf, "follow_scp")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "follow_scp" in names
        assert "resolve_feedback" in names
        assert "end_resolved" in names
        assert "mark_triaged" not in names


# ---------------------------------------------------------------------------
# Test 5: Defer Path
# ---------------------------------------------------------------------------

class TestDefer:
    """Claude sees failure → defers → triaged (will resurface)."""

    def test_defer_triages(self):
        wf = load_workflow({
            "db_available": True,
            "is_duplicate": False,
            "action": "defer",
        })

        complete_user_task(wf, "claude_sees_failure")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "mark_triaged" in names
        assert "end_deferred" in names
        assert "follow_scp" not in names
        assert "resolve_feedback" not in names
        assert wf.data.get("triaged") is True


# ---------------------------------------------------------------------------
# Test 6: New Feedback Created + Deferred
# ---------------------------------------------------------------------------

class TestNewFeedbackDeferred:
    """Verify new feedback creation flow → defer path."""

    def test_new_feedback_then_defer(self):
        wf = load_workflow({
            "db_available": True,
            "is_duplicate": False,
            "action": "defer",
        })

        # Verify intermediate path: new feedback created (not duplicate)
        names = completed_spec_names(wf)
        assert "create_feedback" in names
        assert "reuse_existing" not in names
        assert "wait_for_prompt" in names

        # Complete the human decision
        complete_user_task(wf, "claude_sees_failure")

        assert wf.is_completed()
        assert wf.data.get("triaged") is True
