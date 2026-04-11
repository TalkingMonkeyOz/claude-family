"""
Tests for the L1 Enforcement BPMN process.

Models the hook chain on each tool call:
  1. Task discipline gate (PreToolUse) for gated tools
  2. SQL governance check (BT582/F194) for execute_sql on governed tables
  3. Context injection + standards validation for gated tools
  4. Tool execution
  5. PostToolUse sync

Implementation file:
  processes/architecture/L1_enforcement.bpmn
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


_BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "architecture",
        "L1_enforcement.bpmn"
    )
)
_PROCESS_ID = "L1_enforcement"

_DEFAULT_DATA = {
    "is_gated": False,
    "discipline_result": "allowed",
    "is_sql_write_on_governed": False,
    "sql_governance_warned": False,
}


def _load(data_overrides: dict = None) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(_BPMN_FILE)
    spec = parser.get_spec(_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    data = dict(_DEFAULT_DATA)
    if data_overrides:
        data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "ef_start"]
    assert start_tasks, "Could not find start event"
    start_tasks[0].data.update(data)
    wf.do_engine_steps()
    return wf


def _ready_names(wf):
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.READY, manual=True)]


def _complete(wf, task_name, data=None):
    ready = wf.get_tasks(state=TaskState.READY, manual=True)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    if data:
        matches[0].data.update(data)
    matches[0].run()
    wf.do_engine_steps()


def _completed_names(wf):
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


class TestUngatedToolNormal:
    """Non-gated, non-SQL tool → straight to execution."""

    def test_ungated_happy_path(self):
        wf = _load()
        _complete(wf, "identify_tool")
        _complete(wf, "execute_tool")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "execute_tool" in names
        assert "post_sync" in names
        assert "discipline_check" not in names
        assert "warn_sql_governance" not in names


class TestGatedToolAllowed:
    """Gated tool, discipline passes → inject context, validate, execute."""

    def test_gated_allowed(self):
        wf = _load({"is_gated": True})
        _complete(wf, "identify_tool")
        _complete(wf, "execute_tool")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "discipline_check" in names
        assert "inject_context" in names
        assert "validate_standards" in names
        assert "execute_tool" in names


class TestGatedToolBlocked:
    """Gated tool, discipline blocked → deny, no execution."""

    def test_gated_blocked(self):
        wf = _load({"is_gated": True, "discipline_result": "blocked"})
        _complete(wf, "identify_tool")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "discipline_check" in names
        assert "blocked_response" in names
        assert "execute_tool" not in names


class TestGatedToolContinuation:
    """Gated tool, continuation session → warn but allow."""

    def test_gated_continuation(self):
        wf = _load({"is_gated": True, "discipline_result": "continuation"})
        _complete(wf, "identify_tool")
        _complete(wf, "execute_tool")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "log_continuation" in names
        assert "inject_context" in names
        assert "execute_tool" in names


class TestSqlGovernanceWarned:
    """SQL write on governed table → warn but allow execution."""

    def test_sql_governed_warns_and_continues(self):
        wf = _load({"is_sql_write_on_governed": True})
        _complete(wf, "identify_tool")
        _complete(wf, "execute_tool")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "warn_sql_governance" in names
        assert "execute_tool" in names
        assert "post_sync" in names
        assert wf.data.get("sql_governance_warned") is True


class TestSqlNonGovernedSkipsWarn:
    """Non-governed SQL → no warning."""

    def test_sql_non_governed_no_warn(self):
        wf = _load({"is_sql_write_on_governed": False})
        _complete(wf, "identify_tool")
        _complete(wf, "execute_tool")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "warn_sql_governance" not in names
        assert "execute_tool" in names
