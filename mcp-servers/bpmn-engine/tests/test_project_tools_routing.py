"""
Tests for the Project Tools Routing BPMN process.

Models how the project-tools MCP server routes incoming tool calls and how
the WorkflowEngine validates and executes state transitions.

All tasks are scriptTasks (no userTasks). Initial data controls which branches
the gateway conditions take.

Paths tested:
  1. Session tool: dispatch(session) → session_handler → format_response → end
  2. Workflow valid, no condition, no side effect:
       dispatch(workflow) → resolve → validate(True) → has_condition(None) → execute_update
       → side_effect(False) → audit_merge → log_audit → format → end
  3. Workflow valid, condition met, with side effect:
       dispatch(workflow) → resolve → validate(True) → has_condition(cond) → check(True)
       → execute_merge → execute_update → side_effect(True) → execute_side_effect
       → audit_merge → log_audit → format → end
  4. Workflow invalid transition:
       dispatch(workflow) → resolve → validate(False) → return_invalid → format → end
  5. Workflow condition failed:
       dispatch(workflow) → resolve → validate(True) → has_condition(cond) → check(False)
       → return_condition_error → format → end
  6. Creation tool: dispatch(creation) → creation_handler → format → end
  7. Knowledge tool: dispatch(knowledge) → knowledge_handler → format → end
  8. Config tool: dispatch(config) → config_handler → format → end
  9. Query tool (default): dispatch() → query_handler → format → end

Key notes:
  - category_gw: category == "session"/"workflow"/"creation"/"knowledge"/"config"; default → query
  - valid_transition_gw: transition_valid == False → return_invalid; default → has_condition_gw
  - has_condition_gw: requires_condition != None → check_condition; default → execute_merge
  - condition_met_gw: condition_met == False → return_condition_error; default → execute_merge
  - side_effect_gw: has_side_effect == True → execute_side_effect; default → audit_merge
  - All paths converge at response_merge → format_response → end

Implementation: mcp-servers/project-tools/server_v2.py (WorkflowEngine class)
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "project_tools_routing.bpmn")
)
PROCESS_ID = "project_tools_routing"


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


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Session Tool
# ---------------------------------------------------------------------------

class TestSessionToolRouting:
    """
    dispatch(category=session) → session_handler → response_merge → format_response → end.
    """

    def test_session_tool_routed(self):
        wf = load_workflow(initial_data={"category": "session"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fastmcp_dispatch" in names
        assert "session_handler" in names
        assert "format_response" in names
        assert "end" in names

        # Workflow-engine steps must not appear
        assert "resolve_entity" not in names
        assert "validate_transition" not in names

        assert wf.data.get("session_handled") is True
        assert wf.data.get("response_formatted") is True


# ---------------------------------------------------------------------------
# Test 2: Workflow - Valid, No Condition, No Side Effect
# ---------------------------------------------------------------------------

class TestWorkflowValidNoConditionNoSideEffect:
    """
    dispatch(workflow) → resolve → validate(True) → has_condition(None)
    → execute_merge → execute_update → side_effect(False) → audit_merge
    → log_audit → format → end.

    requires_condition must be None for no-condition branch (default).
    has_side_effect must be False for no-side-effect branch (default).
    """

    def test_valid_workflow_no_condition_no_side_effect(self):
        wf = load_workflow(initial_data={
            "category": "workflow",
            "transition_valid": True,
            "requires_condition": None,
            "has_side_effect": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "resolve_entity" in names
        assert "validate_transition" in names
        assert "execute_update" in names
        assert "log_audit" in names
        assert "format_response" in names

        # Should NOT hit condition check or side effect branches
        assert "check_condition" not in names
        assert "execute_side_effect" not in names
        assert "return_invalid" not in names
        assert "return_condition_error" not in names

        assert wf.data.get("status_updated") is True
        assert wf.data.get("audit_logged") is True
        assert wf.data.get("response_formatted") is True


# ---------------------------------------------------------------------------
# Test 3: Workflow - Valid, Condition Met, With Side Effect
# ---------------------------------------------------------------------------

class TestWorkflowValidConditionMetWithSideEffect:
    """
    dispatch(workflow) → resolve → validate(True) → has_condition(all_tasks_done)
    → check_condition(True) → execute_merge → execute_update
    → side_effect(True) → execute_side_effect → audit_merge → log_audit → format → end.
    """

    def test_valid_workflow_condition_met_with_side_effect(self):
        wf = load_workflow(initial_data={
            "category": "workflow",
            "transition_valid": True,
            "requires_condition": "all_tasks_done",
            "condition_met": True,
            "has_side_effect": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "resolve_entity" in names
        assert "validate_transition" in names
        assert "check_condition" in names
        assert "execute_update" in names
        assert "execute_side_effect" in names
        assert "log_audit" in names
        assert "format_response" in names

        assert "return_condition_error" not in names
        assert "return_invalid" not in names

        assert wf.data.get("side_effect_executed") is True
        assert wf.data.get("audit_logged") is True


# ---------------------------------------------------------------------------
# Test 4: Workflow - Invalid Transition
# ---------------------------------------------------------------------------

class TestWorkflowInvalidTransition:
    """
    dispatch(workflow) → resolve → validate(False) → return_invalid
    → response_merge → format → end.
    """

    def test_invalid_workflow_transition(self):
        wf = load_workflow(initial_data={
            "category": "workflow",
            "transition_valid": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "resolve_entity" in names
        assert "validate_transition" in names
        assert "return_invalid" in names
        assert "format_response" in names

        # Should NOT reach execution steps
        assert "execute_update" not in names
        assert "log_audit" not in names
        assert "check_condition" not in names

        assert wf.data.get("error_returned") is True
        assert wf.data.get("response_formatted") is True


# ---------------------------------------------------------------------------
# Test 5: Workflow - Condition Failed
# ---------------------------------------------------------------------------

class TestWorkflowConditionFailed:
    """
    dispatch(workflow) → resolve → validate(True) → has_condition(all_tasks_done)
    → check_condition(False) → return_condition_error → format → end.
    """

    def test_workflow_condition_failed(self):
        wf = load_workflow(initial_data={
            "category": "workflow",
            "transition_valid": True,
            "requires_condition": "all_tasks_done",
            "condition_met": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "check_condition" in names
        assert "return_condition_error" in names
        assert "format_response" in names

        assert "execute_update" not in names
        assert "execute_side_effect" not in names

        assert wf.data.get("condition_error") is True


# ---------------------------------------------------------------------------
# Test 6: Creation Tool
# ---------------------------------------------------------------------------

class TestCreationToolRouting:
    """
    dispatch(category=creation) → creation_handler → response_merge → format → end.
    """

    def test_creation_tool_routed(self):
        wf = load_workflow(initial_data={"category": "creation"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "creation_handler" in names
        assert "format_response" in names
        assert "resolve_entity" not in names

        assert wf.data.get("work_created") is True
        assert wf.data.get("response_formatted") is True


# ---------------------------------------------------------------------------
# Test 7: Knowledge Tool
# ---------------------------------------------------------------------------

class TestKnowledgeToolRouting:
    """
    dispatch(category=knowledge) → knowledge_handler → response_merge → format → end.
    """

    def test_knowledge_tool_routed(self):
        wf = load_workflow(initial_data={"category": "knowledge"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "knowledge_handler" in names
        assert "format_response" in names
        assert "creation_handler" not in names

        assert wf.data.get("knowledge_handled") is True


# ---------------------------------------------------------------------------
# Test 8: Config Tool
# ---------------------------------------------------------------------------

class TestConfigToolRouting:
    """
    dispatch(category=config) → config_handler → response_merge → format → end.
    """

    def test_config_tool_routed(self):
        wf = load_workflow(initial_data={"category": "config"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "config_handler" in names
        assert "format_response" in names
        assert "knowledge_handler" not in names

        assert wf.data.get("config_handled") is True


# ---------------------------------------------------------------------------
# Test 9: Query Tool (Default)
# ---------------------------------------------------------------------------

class TestQueryToolRouting:
    """
    dispatch() → category_gw(default) → query_handler → response_merge → format → end.

    The default branch fires when no category condition matches.
    """

    def test_query_tool_default_routing(self):
        wf = load_workflow()

        # No category set → default branch → query_handler
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fastmcp_dispatch" in names
        assert "query_handler" in names
        assert "format_response" in names
        assert "end" in names

        assert "session_handler" not in names
        assert "resolve_entity" not in names
        assert "creation_handler" not in names
        assert "knowledge_handler" not in names
        assert "config_handler" not in names

        assert wf.data.get("query_handled") is True
        assert wf.data.get("response_formatted") is True


# ---------------------------------------------------------------------------
# Test 10: Response Always Formatted (all paths)
# ---------------------------------------------------------------------------

class TestResponseAlwaysFormatted:
    """
    format_response must execute on every path, including error paths.
    """

    def test_invalid_transition_still_formats(self):
        wf = load_workflow(initial_data={
            "category": "workflow",
            "transition_valid": False,
        })
        assert wf.is_completed()
        assert "format_response" in completed_spec_names(wf)
        assert wf.data.get("response_formatted") is True

    def test_condition_error_still_formats(self):
        wf = load_workflow(initial_data={
            "category": "workflow",
            "transition_valid": True,
            "requires_condition": "all_tasks_done",
            "condition_met": False,
        })
        assert wf.is_completed()
        assert "format_response" in completed_spec_names(wf)
        assert wf.data.get("response_formatted") is True

    def test_session_tool_formats(self):
        wf = load_workflow(initial_data={"category": "session"})
        assert wf.is_completed()
        assert "format_response" in completed_spec_names(wf)
