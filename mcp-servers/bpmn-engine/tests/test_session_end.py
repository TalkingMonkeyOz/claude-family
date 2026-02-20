"""
Tests for the Session End BPMN process.

Session End Hook (session_end):
  Trigger: SessionEnd event (Claude Code process exit)
  Input: session_id, cwd, db_available (optional)

  Key behaviors:
    1. Parse session info from hook input
    2. Connect to PostgreSQL
    3. If DB available: demote in_progress todos, close session, end_saved
    4. If DB unavailable (fail-open): skip DB operations, end_no_db

  Test paths:
    1. DB available → parse → connect → demote → close → end_saved
    2. DB unavailable → parse → connect → end_no_db (no demote/close)
    3. Common path → parse and connect always executed

Implementation: scripts/session_end_hook.py
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "session_end.bpmn")
)
PROCESS_ID = "session_end"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
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


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: DB Available - Happy Path
# ---------------------------------------------------------------------------

class TestDBAvailable:
    """
    DB is available → demote todos → close session → end_saved.

    Expected path:
      start → parse_input → connect_db → db_gw (True) →
      demote_todos → close_session → end_saved
    """

    def test_db_available_completes_full_save(self):
        wf = load_workflow({
            "db_available": True,
            "has_session_id": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Required tasks should be completed
        assert "parse_input" in names
        assert "connect_db" in names
        assert "demote_todos" in names
        assert "close_session" in names
        assert "end_saved" in names

        # Should not hit the no-DB end event
        assert "end_no_db" not in names

        # Check data state
        assert wf.data.get("db_available") is True
        assert wf.data.get("todos_demoted") is True
        assert wf.data.get("session_closed") is True


# ---------------------------------------------------------------------------
# Test 2: DB Unavailable - Fail-Open Path
# ---------------------------------------------------------------------------

class TestDBUnavailable:
    """
    DB is unavailable → skip demote/close → end_no_db (fail-open).

    Expected path:
      start → parse_input → connect_db → db_gw (False) → end_no_db

    Demote and close tasks should NOT execute (fail-open design).
    """

    def test_db_unavailable_skips_demote_and_close(self):
        wf = load_workflow({
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Parse and connect should still execute
        assert "parse_input" in names
        assert "connect_db" in names

        # DB-dependent tasks should NOT execute
        assert "demote_todos" not in names
        assert "close_session" not in names

        # Should hit no-DB end event
        assert "end_no_db" in names

        # Should not hit saved end event
        assert "end_saved" not in names


# ---------------------------------------------------------------------------
# Test 3: Always Parse - Common Path
# ---------------------------------------------------------------------------

class TestAlwaysParses:
    """
    Both DB available and unavailable paths execute parse_input and connect_db.

    This ensures the hook always attempts to capture session info and connect,
    regardless of whether the DB operations complete.
    """

    def test_db_available_parses_and_connects(self):
        wf = load_workflow({"db_available": True})
        names = completed_spec_names(wf)
        assert "parse_input" in names
        assert "connect_db" in names

    def test_db_unavailable_still_parses_and_connects(self):
        wf = load_workflow({"db_available": False})
        names = completed_spec_names(wf)
        assert "parse_input" in names
        assert "connect_db" in names


# ---------------------------------------------------------------------------
# Test 4: Data Preservation
# ---------------------------------------------------------------------------

class TestDataPreservation:
    """Workflow data is properly set by script tasks."""

    def test_workflow_data_set_on_success(self):
        wf = load_workflow({"db_available": True})

        # Script tasks set these flags
        assert wf.data.get("has_session_id") is not None
        assert wf.data.get("db_available") is True
        assert wf.data.get("todos_demoted") is True
        assert wf.data.get("session_closed") is True

    def test_workflow_data_on_db_fail(self):
        wf = load_workflow({"db_available": False})

        # DB checks should be attempted
        assert wf.data.get("db_available") is False
        # But demote/close should not execute
        assert wf.data.get("todos_demoted") is None or wf.data.get("todos_demoted") is False
        assert wf.data.get("session_closed") is None or wf.data.get("session_closed") is False
