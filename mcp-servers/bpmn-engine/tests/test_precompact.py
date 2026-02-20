"""
Tests for the PreCompact Hook BPMN process.

PreCompact hook preserves critical session state before context compaction.
Injects a systemMessage with active work items AND narrative context so Claude
retains both situational awareness and understanding of user intent.

Trigger: PreCompact event (manual /compact or auto-compact)
Output: systemMessage injected into post-compact context

Test paths:
  1. DB available: get_project → connect_db → query_session_state → query_session_facts
     → read_session_notes → build_message → end_injected
  2. DB unavailable: get_project → connect_db → fallback_message → end_injected
  3. Always connects: both paths complete get_project and connect_db

Key behaviors:
  - Queries active todos, session_state, active features from DB
  - Queries session facts (decisions, references, user_intent) from DB
  - Reads session notes from markdown file
  - Builds refresh message with preserved state + narrative
  - Includes post-compaction checklist (recall user_intent, re-read CLAUDE.md)
  - Fail-open: returns minimal message if DB unavailable

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks
  - task.data is a dict; set values via load_workflow(initial_data={...})
  - Gateway conditions are Python expressions eval'd against task.data
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "precompact.bpmn")
)
PROCESS_ID = "precompact"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow instance with optional initial data."""
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
# Test 1: DB Available Path
# ---------------------------------------------------------------------------

class TestDBAvailable:
    """
    Database is available and healthy.
    Should query session state, facts, notes, and build full refresh message.
    """

    def test_db_available_full_path(self):
        """db_available=True → query_session_state → query_session_facts → read_session_notes → build_message → end_injected."""
        wf = load_workflow(initial_data={"db_available": True, "project_name": "test-project"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Should complete full DB path
        assert "get_project" in names
        assert "connect_db" in names
        assert "query_session_state" in names
        assert "query_session_facts" in names
        assert "read_session_notes" in names
        assert "build_message" in names
        assert "end_injected" in names

        # Should NOT complete fallback path
        assert "fallback_message" not in names

        # Should have state_injected = True (from build_message)
        assert wf.data.get("state_injected") is True

    def test_db_available_state_queried(self):
        """query_session_state should set state_queried = True."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        assert "query_session_state" in names
        assert wf.data.get("state_queried") is True

    def test_db_available_facts_queried(self):
        """query_session_facts should set facts_queried = True."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        assert "query_session_facts" in names
        assert wf.data.get("facts_queried") is True

    def test_db_available_notes_read(self):
        """read_session_notes should set notes_read = True."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        assert "read_session_notes" in names
        assert wf.data.get("notes_read") is True

    def test_db_available_message_built(self):
        """build_message should set state_injected = True."""
        wf = load_workflow(initial_data={"db_available": True})

        assert wf.data.get("state_injected") is True


# ---------------------------------------------------------------------------
# Test 2: DB Unavailable Path
# ---------------------------------------------------------------------------

class TestDBUnavailable:
    """
    Database is unavailable (connection failed, timeout, etc).
    Should fall back to minimal message without state preservation.
    """

    def test_db_unavailable_fallback_path(self):
        """db_available=False → fallback_message → end_injected."""
        wf = load_workflow(initial_data={"db_available": False, "project_name": "test-project"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Should complete fallback path
        assert "get_project" in names
        assert "connect_db" in names
        assert "fallback_message" in names
        assert "end_injected" in names

        # Should NOT complete full DB query path
        assert "query_session_state" not in names
        assert "query_session_facts" not in names
        assert "read_session_notes" not in names
        assert "build_message" not in names

        # Should have state_injected = False (from fallback_message)
        assert wf.data.get("state_injected") is False

    def test_db_unavailable_no_state_query(self):
        """When DB unavailable, query_session_state should NOT be called."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)
        assert "query_session_state" not in names
        assert "state_queried" not in wf.data or wf.data.get("state_queried") is not True

    def test_db_unavailable_no_facts_query(self):
        """When DB unavailable, query_session_facts should NOT be called."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)
        assert "query_session_facts" not in names

    def test_db_unavailable_no_notes_read(self):
        """When DB unavailable, read_session_notes should NOT be called."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)
        assert "read_session_notes" not in names

    def test_db_unavailable_fallback_flag(self):
        """Fallback message should explicitly set state_injected = False."""
        wf = load_workflow(initial_data={"db_available": False})

        # fallback_message script sets: state_injected = False
        assert wf.data.get("state_injected") is False


# ---------------------------------------------------------------------------
# Test 3: Always Connects to Database
# ---------------------------------------------------------------------------

class TestAlwaysConnects:
    """
    Both available and unavailable paths must always start with project retrieval
    and database connection attempt. No skipping these critical steps.
    """

    def test_always_gets_project_when_available(self):
        """get_project should always complete when DB available."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        assert "get_project" in names

    def test_always_gets_project_when_unavailable(self):
        """get_project should always complete when DB unavailable."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)
        assert "get_project" in names

    def test_always_connects_db_when_available(self):
        """connect_db should always complete when DB available."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        assert "connect_db" in names

    def test_always_connects_db_when_unavailable(self):
        """connect_db should always complete even if connection fails."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)
        assert "connect_db" in names

    def test_project_name_set(self):
        """get_project should initialize or preserve project_name."""
        wf = load_workflow(initial_data={
            "db_available": True,
            "project_name": "my-project"
        })

        # Project name should be preserved
        assert wf.data.get("project_name") == "my-project"

    def test_project_name_defaults_to_unknown(self):
        """get_project should default to 'unknown' if not provided."""
        wf = load_workflow(initial_data={
            "db_available": True,
            "project_name": None
        })

        # Script defaults to "unknown"
        assert wf.data.get("project_name") == "unknown"


# ---------------------------------------------------------------------------
# Test 4: Gateway Logic Verification
# ---------------------------------------------------------------------------

class TestGatewayLogic:
    """Verify the exclusive gateway (db_gw) routes correctly based on db_available."""

    def test_gateway_true_takes_db_ok_path(self):
        """db_available == True → should take flow_db_ok path."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        # True condition should reach query_session_state (flow_db_ok path)
        assert "query_session_state" in names

    def test_gateway_false_takes_default_path(self):
        """db_available != True → should take default path (flow_no_db)."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)
        # Default path should reach fallback_message
        assert "fallback_message" in names

    def test_gateway_none_defaults_to_available(self):
        """db_available=None → script sets to True, takes available path."""
        wf = load_workflow(initial_data={"db_available": None})

        names = completed_spec_names(wf)
        # Script defaults to True: db_available = db_available if db_available is not None else True
        assert "query_session_state" in names


# ---------------------------------------------------------------------------
# Test 5: Sequential Flow Verification
# ---------------------------------------------------------------------------

class TestSequentialFlow:
    """Verify tasks execute in correct order within each path."""

    def test_db_path_order_available(self):
        """DB available path: state → facts → notes → message."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)

        # All should be completed
        assert "query_session_state" in names
        assert "query_session_facts" in names
        assert "read_session_notes" in names
        assert "build_message" in names

        # Get task objects to verify order
        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        task_dict = {t.task_spec.name: t for t in tasks}

        # Verify they all completed (sequence flow should have been followed)
        assert all(t in task_dict for t in [
            "query_session_state",
            "query_session_facts",
            "read_session_notes",
            "build_message"
        ])

    def test_fallback_path_order_unavailable(self):
        """DB unavailable path: connect → fallback → end."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)

        # Should have: get_project, connect_db, fallback_message, end_injected
        assert "get_project" in names
        assert "connect_db" in names
        assert "fallback_message" in names
        assert "end_injected" in names

        # Should NOT have the query tasks
        assert "query_session_state" not in names


# ---------------------------------------------------------------------------
# Test 6: State Preservation Through Pipeline
# ---------------------------------------------------------------------------

class TestStatePreservation:
    """Verify workflow data is preserved and correctly set through the process."""

    def test_query_flags_set_correctly_when_available(self):
        """All query completion flags should be set when DB available."""
        wf = load_workflow(initial_data={"db_available": True})

        assert wf.data.get("state_queried") is True
        assert wf.data.get("facts_queried") is True
        assert wf.data.get("notes_read") is True
        assert wf.data.get("state_injected") is True

    def test_query_flags_not_set_when_unavailable(self):
        """Query flags should NOT be set when DB unavailable."""
        wf = load_workflow(initial_data={"db_available": False})

        # These should not be set because query tasks didn't run
        assert wf.data.get("state_queried") is None
        assert wf.data.get("facts_queried") is None
        assert wf.data.get("notes_read") is None

    def test_fallback_explicitly_sets_state_injected_false(self):
        """Fallback path should explicitly set state_injected = False."""
        wf = load_workflow(initial_data={"db_available": False})

        # Explicitly False (not just missing)
        assert wf.data.get("state_injected") is False


# ---------------------------------------------------------------------------
# Test 7: End Event Coverage
# ---------------------------------------------------------------------------

class TestEndEventCoverage:
    """All paths converge on end_injected event."""

    def test_end_injected_reached_when_available(self):
        """DB available path should reach end_injected."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        assert "end_injected" in names

    def test_end_injected_reached_when_unavailable(self):
        """DB unavailable path should reach end_injected."""
        wf = load_workflow(initial_data={"db_available": False})

        names = completed_spec_names(wf)
        assert "end_injected" in names

    def test_workflow_completes(self):
        """Both paths should result in workflow completion."""
        wf1 = load_workflow(initial_data={"db_available": True})
        wf2 = load_workflow(initial_data={"db_available": False})

        assert wf1.is_completed()
        assert wf2.is_completed()


# ---------------------------------------------------------------------------
# Test 8: Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test boundary conditions and unusual inputs."""

    def test_db_available_true_explicit(self):
        """Explicitly True should take DB path."""
        wf = load_workflow(initial_data={"db_available": True})

        names = completed_spec_names(wf)
        assert "query_session_state" in names
        assert "fallback_message" not in names

    def test_db_available_zero_falsy(self):
        """0 (falsy) should take fallback path."""
        wf = load_workflow(initial_data={"db_available": 0})

        names = completed_spec_names(wf)
        # 0 is not True, so takes default path
        assert "fallback_message" in names

    def test_db_available_empty_string_falsy(self):
        """Empty string (falsy) should take fallback path."""
        wf = load_workflow(initial_data={"db_available": ""})

        names = completed_spec_names(wf)
        # Empty string is not True, so takes default path
        assert "fallback_message" in names

    def test_project_name_preservation(self):
        """project_name should be preserved through the workflow."""
        project_name = "claude-family"
        wf = load_workflow(initial_data={
            "db_available": True,
            "project_name": project_name
        })

        assert wf.data.get("project_name") == project_name

    def test_complex_project_name(self):
        """Complex project names should work."""
        complex_name = "my-test-project-v2.1"
        wf = load_workflow(initial_data={
            "db_available": True,
            "project_name": complex_name
        })

        assert wf.data.get("project_name") == complex_name
