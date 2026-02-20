"""
Tests for the MCP Usage Logging BPMN process.

Covers the PostToolUse hook that logs MCP tool usage metrics to the database.

Process flow:
  start → check_mcp_prefix → mcp_gw
    [is_mcp_tool == False] → end_skip (default)
    [is_mcp_tool == True] → extract_metrics → connect_db → db_gw
      [db_available == True] → insert_usage → end_logged
      [db_available == False] → end_no_db (default)

Test cases:
  1. Non-MCP tool (builtin) → skipped without extraction
  2. MCP tool + DB available → metrics extracted → usage logged
  3. MCP tool + DB down → metrics extracted → fail-open to end_no_db
  4. Both paths complete check_mcp_prefix
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "mcp_usage_logging.bpmn")
)
PROCESS_ID = "mcp_usage_logging"


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


class TestNotMcpTool:
    """
    Non-MCP tool (builtin like Read, Write, Edit) → skips without reaching extract_metrics.

    Flow:
        start → check_mcp_prefix → mcp_gw [is_mcp_tool=False, default]
        → end_skip
    """

    def test_builtin_tool_skipped(self):
        """Builtin tools (not mcp__) should be skipped at the gateway."""
        wf = load_workflow({
            "is_mcp_tool": False,
        })

        assert wf.is_completed(), "Workflow should be completed after skipping"

        names = completed_spec_names(wf)

        # These MUST be completed
        assert "check_mcp_prefix" in names, "check_mcp_prefix must always run"
        assert "end_skip" in names, "end_skip must be reached for non-MCP tools"

        # These MUST NOT be completed
        assert "extract_metrics" not in names, "extract_metrics must NOT run for non-MCP tools"
        assert "insert_usage" not in names, "insert_usage must NOT run for non-MCP tools"
        assert "connect_db" not in names, "connect_db must NOT run for non-MCP tools"


class TestMcpToolDBAvailable:
    """
    MCP tool + DB available → metrics extracted → usage logged.

    Flow:
        start → check_mcp_prefix → mcp_gw [is_mcp_tool=True]
        → extract_metrics → connect_db → db_gw [db_available=True]
        → insert_usage → end_logged
    """

    def test_mcp_tool_logged_success(self):
        """MCP tools with available DB should complete the full logging path."""
        wf = load_workflow({
            "is_mcp_tool": True,
            "db_available": True,
        })

        assert wf.is_completed(), "Workflow should be completed successfully"

        names = completed_spec_names(wf)

        # Full path must be completed
        assert "check_mcp_prefix" in names, "check_mcp_prefix must always run"
        assert "extract_metrics" in names, "extract_metrics must run for MCP tools"
        assert "connect_db" in names, "connect_db must run when metrics extracted"
        assert "insert_usage" in names, "insert_usage must run when DB available"
        assert "end_logged" in names, "end_logged must be reached on success"

        # Alternate paths must NOT be completed
        assert "end_skip" not in names, "end_skip must NOT be reached for MCP tools"
        assert "end_no_db" not in names, "end_no_db must NOT be reached when DB available"

        # Data flag should be set by insert_usage script
        assert wf.data.get("usage_logged") is True, "insert_usage should set usage_logged=True"


class TestMcpToolNoDB:
    """
    MCP tool + DB unavailable → metrics extracted but fails-open to end_no_db.

    Flow:
        start → check_mcp_prefix → mcp_gw [is_mcp_tool=True]
        → extract_metrics → connect_db → db_gw [db_available=False, default]
        → end_no_db
    """

    def test_mcp_tool_db_unavailable(self):
        """MCP tools should fail-open when DB is down (not block agent)."""
        wf = load_workflow({
            "is_mcp_tool": True,
            "db_available": False,
        })

        assert wf.is_completed(), "Workflow should be completed (fail-open)"

        names = completed_spec_names(wf)

        # Extraction should happen
        assert "check_mcp_prefix" in names, "check_mcp_prefix must always run"
        assert "extract_metrics" in names, "extract_metrics must run for MCP tools"
        assert "connect_db" in names, "connect_db must run even if DB check fails"

        # But insertion should NOT happen
        assert "insert_usage" not in names, "insert_usage must NOT run when DB unavailable"

        # Must reach fail-open end event
        assert "end_no_db" in names, "end_no_db must be reached when DB unavailable"
        assert "end_logged" not in names, "end_logged must NOT be reached on DB failure"
        assert "end_skip" not in names, "end_skip must NOT be reached for MCP tools"


class TestAlwaysChecksPrefix:
    """
    Both MCP and non-MCP paths should complete check_mcp_prefix.

    This validates the common validation point in the process.
    """

    def test_mcp_prefix_check_runs_for_mcp_tool(self):
        """check_mcp_prefix must run for MCP tools."""
        wf = load_workflow({
            "is_mcp_tool": True,
            "db_available": True,
        })

        names = completed_spec_names(wf)
        assert "check_mcp_prefix" in names, "check_mcp_prefix must always run"

    def test_mcp_prefix_check_runs_for_non_mcp_tool(self):
        """check_mcp_prefix must run for non-MCP tools."""
        wf = load_workflow({
            "is_mcp_tool": False,
        })

        names = completed_spec_names(wf)
        assert "check_mcp_prefix" in names, "check_mcp_prefix must always run"
