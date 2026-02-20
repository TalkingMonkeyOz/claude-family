"""
Tests for simple hook lifecycle BPMN processes.

Covers 4 hooks:
  - MCP Usage Logging (mcp_usage_logging)
  - PreCompact (precompact)
  - Session End (session_end)
  - SubagentStart (subagent_start)

MCP Usage Logging tests:
  1. MCP tool → logged
  2. Non-MCP tool → skipped
  3. MCP tool + DB down → end_no_db

PreCompact tests:
  4. DB available → state queried → message built
  5. DB unavailable → fallback message

Session End tests:
  6. DB available → todos demoted → session closed
  7. DB unavailable → end_no_db

SubagentStart tests:
  8. Agent ID + DB → logged
  9. No agent ID → skipped
  10. Agent ID + no DB → end_no_db
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

BPMN_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure")
)

MCP_LOGGING_FILE = os.path.join(BPMN_DIR, "mcp_usage_logging.bpmn")
PRECOMPACT_FILE = os.path.join(BPMN_DIR, "precompact.bpmn")
SESSION_END_FILE = os.path.join(BPMN_DIR, "session_end.bpmn")
SUBAGENT_FILE = os.path.join(BPMN_DIR, "subagent_start.bpmn")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(bpmn_file: str, process_id: str, initial_data: dict = None) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(bpmn_file)
    spec = parser.get_spec(process_id)
    wf = BpmnWorkflow(spec)
    if initial_data:
        start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
        assert start_tasks, "Could not find BPMN start event"
        start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ===========================================================================
# MCP USAGE LOGGING TESTS
# ===========================================================================

class TestMCPLoggingHappyPath:
    """MCP tool → extract metrics → DB available → logged."""

    def test_mcp_tool_logged(self):
        wf = load_workflow(MCP_LOGGING_FILE, "mcp_usage_logging", {
            "is_mcp_tool": True,
            "db_available": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "check_mcp_prefix" in names
        assert "extract_metrics" in names
        assert "insert_usage" in names
        assert "end_logged" in names
        assert "end_skip" not in names
        assert wf.data.get("usage_logged") is True


class TestMCPLoggingSkipNonMCP:
    """Non-MCP tool (builtin) → skipped."""

    def test_non_mcp_skipped(self):
        wf = load_workflow(MCP_LOGGING_FILE, "mcp_usage_logging", {
            "is_mcp_tool": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_skip" in names
        assert "extract_metrics" not in names
        assert "insert_usage" not in names


class TestMCPLoggingDBDown:
    """MCP tool but DB unavailable → end_no_db."""

    def test_mcp_db_down(self):
        wf = load_workflow(MCP_LOGGING_FILE, "mcp_usage_logging", {
            "is_mcp_tool": True,
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "extract_metrics" in names
        assert "end_no_db" in names
        assert "insert_usage" not in names


# ===========================================================================
# PRECOMPACT TESTS
# ===========================================================================

class TestPreCompactHappyPath:
    """DB available → query state → build message → injected."""

    def test_state_preserved(self):
        wf = load_workflow(PRECOMPACT_FILE, "precompact", {
            "project_name": "test-project",
            "db_available": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "get_project" in names
        assert "query_session_state" in names
        assert "build_message" in names
        assert "end_injected" in names
        assert "fallback_message" not in names
        assert wf.data.get("state_injected") is True


class TestPreCompactDBDown:
    """DB unavailable → fallback message."""

    def test_fallback_on_db_failure(self):
        wf = load_workflow(PRECOMPACT_FILE, "precompact", {
            "project_name": "test-project",
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "fallback_message" in names
        assert "end_injected" in names
        assert "query_session_state" not in names
        assert wf.data.get("state_injected") is False


# ===========================================================================
# SESSION END TESTS
# ===========================================================================

class TestSessionEndHappyPath:
    """DB available → demote todos → close session → saved."""

    def test_session_auto_saved(self):
        wf = load_workflow(SESSION_END_FILE, "session_end", {
            "has_session_id": True,
            "db_available": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "parse_input" in names
        assert "demote_todos" in names
        assert "close_session" in names
        assert "end_saved" in names
        assert wf.data.get("session_closed") is True
        assert wf.data.get("todos_demoted") is True


class TestSessionEndDBDown:
    """DB unavailable → end_no_db."""

    def test_no_db_exits_cleanly(self):
        wf = load_workflow(SESSION_END_FILE, "session_end", {
            "has_session_id": True,
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_no_db" in names
        assert "demote_todos" not in names
        assert "close_session" not in names


# ===========================================================================
# SUBAGENT START TESTS
# ===========================================================================

class TestSubagentStartHappyPath:
    """Agent ID present + DB available → logged."""

    def test_agent_spawn_logged(self):
        wf = load_workflow(SUBAGENT_FILE, "subagent_start", {
            "has_agent_id": True,
            "db_available": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "parse_input" in names
        assert "insert_agent_session" in names
        assert "end_logged" in names
        assert "end_skip" not in names
        assert wf.data.get("agent_logged") is True


class TestSubagentStartNoID:
    """No agent ID → skip."""

    def test_no_id_skips(self):
        wf = load_workflow(SUBAGENT_FILE, "subagent_start", {
            "has_agent_id": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_skip" in names
        assert "connect_db" not in names
        assert "insert_agent_session" not in names


class TestSubagentStartDBDown:
    """Agent ID present but DB down → end_no_db."""

    def test_db_down_fails_open(self):
        wf = load_workflow(SUBAGENT_FILE, "subagent_start", {
            "has_agent_id": True,
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_no_db" in names
        assert "insert_agent_session" not in names
