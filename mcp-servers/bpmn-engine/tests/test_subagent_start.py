"""
Tests for the SubagentStart Hook BPMN process.

Covers the SubagentStart hook that logs agent spawns for tracking and analytics.

Process flow:
  start → parse_input → has_id_gw
    [has_agent_id == False] → end_skip (default)
    [has_agent_id == True] → connect_db → db_gw
      [db_available == True] → insert_agent_session → end_logged
      [db_available == False] → end_no_db (default)

Test cases:
  1. No agent ID → skipped without DB connection
  2. Agent ID + DB available → agent session logged
  3. Agent ID + DB down → fail-open to end_no_db
  4. Both paths complete parse_input
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "subagent_start.bpmn")
)
PROCESS_ID = "subagent_start"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """
    Parse the BPMN and return a fresh, initialized workflow instance.

    Args:
        initial_data: Optional dict to set on the start event's data

    Returns:
        Initialized BpmnWorkflow with engine steps completed
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


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    """Return the set of all completed task spec names in the workflow."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNoAgentId:
    """
    No agent ID → skipped without reaching DB connection.

    Flow:
        start → parse_input → has_id_gw [has_agent_id=False, default]
        → end_skip
    """

    def test_missing_agent_id_skipped(self):
        """Agent spawns without an ID should be skipped."""
        wf = load_workflow({
            "has_agent_id": False,
        })

        assert wf.is_completed(), "Workflow should be completed after skipping"

        names = completed_spec_names(wf)

        # These MUST be completed
        assert "parse_input" in names, "parse_input must always run"
        assert "end_skip" in names, "end_skip must be reached when no agent ID"

        # These MUST NOT be completed
        assert "connect_db" not in names, "connect_db must NOT run when no agent ID"
        assert "insert_agent_session" not in names, "insert_agent_session must NOT run when no agent ID"


class TestAgentIdDBAvailable:
    """
    Agent ID present + DB available → agent session logged.

    Flow:
        start → parse_input → has_id_gw [has_agent_id=True]
        → connect_db → db_gw [db_available=True]
        → insert_agent_session → end_logged
    """

    def test_agent_spawn_logged_success(self):
        """Agent spawns with ID and DB available should complete the full logging path."""
        wf = load_workflow({
            "has_agent_id": True,
            "db_available": True,
        })

        assert wf.is_completed(), "Workflow should be completed successfully"

        names = completed_spec_names(wf)

        # Full path must be completed
        assert "parse_input" in names, "parse_input must always run"
        assert "connect_db" in names, "connect_db must run when agent ID present"
        assert "insert_agent_session" in names, "insert_agent_session must run when DB available"
        assert "end_logged" in names, "end_logged must be reached on success"

        # Alternate paths must NOT be completed
        assert "end_skip" not in names, "end_skip must NOT be reached when agent ID present"
        assert "end_no_db" not in names, "end_no_db must NOT be reached when DB available"

        # Data flag should be set by insert_agent_session script
        assert wf.data.get("agent_logged") is True, "insert_agent_session should set agent_logged=True"


class TestAgentIdNoDb:
    """
    Agent ID present + DB unavailable → fails-open to end_no_db.

    Flow:
        start → parse_input → has_id_gw [has_agent_id=True]
        → connect_db → db_gw [db_available=False, default]
        → end_no_db
    """

    def test_agent_spawn_db_unavailable(self):
        """Agent spawns should fail-open when DB is down (not block agent)."""
        wf = load_workflow({
            "has_agent_id": True,
            "db_available": False,
        })

        assert wf.is_completed(), "Workflow should be completed (fail-open)"

        names = completed_spec_names(wf)

        # Input parsing should happen
        assert "parse_input" in names, "parse_input must always run"
        assert "connect_db" in names, "connect_db must run when agent ID present"

        # But insertion should NOT happen
        assert "insert_agent_session" not in names, "insert_agent_session must NOT run when DB unavailable"

        # Must reach fail-open end event
        assert "end_no_db" in names, "end_no_db must be reached when DB unavailable"
        assert "end_logged" not in names, "end_logged must NOT be reached on DB failure"
        assert "end_skip" not in names, "end_skip must NOT be reached when agent ID present"


class TestAlwaysParses:
    """
    Both agent spawn and no-ID paths should complete parse_input.

    This validates the common validation point in the process.
    """

    def test_parse_input_runs_with_agent_id(self):
        """parse_input must run when agent ID is present."""
        wf = load_workflow({
            "has_agent_id": True,
            "db_available": True,
        })

        names = completed_spec_names(wf)
        assert "parse_input" in names, "parse_input must always run"

    def test_parse_input_runs_without_agent_id(self):
        """parse_input must run even when agent ID is missing."""
        wf = load_workflow({
            "has_agent_id": False,
        })

        names = completed_spec_names(wf)
        assert "parse_input" in names, "parse_input must always run"
