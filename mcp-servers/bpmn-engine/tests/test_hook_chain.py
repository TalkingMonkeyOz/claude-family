"""
Tests for the Hook Chain BPMN process.

Uses SpiffWorkflow 3.x API directly against the hook_chain.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Hook Chain Process:
  receive_prompt → rag_query → is_tool_call_gateway
    [is_tool_call=True] → check_discipline → discipline_result_gateway
      [discipline_blocked=True] → mark_blocked → end_blocked
      [default]               → inject_context → execute_tool → post_tool_sync → end_tool_complete
    [default/no tool]  → generate_response → end_response
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "hook_chain.bpmn")
)
PROCESS_ID = "hook_chain"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past any initial automated steps (e.g. the start event)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() so the engine advances through any subsequent automated
    tasks (script tasks, gateways) until the next user task or end event.

    Raises AssertionError if the task is not currently READY.
    """
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected user task '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return the spec names of all COMPLETED tasks in the workflow."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTextResponsePath:
    """
    Prompt with no tool call: receive_prompt → rag_query → generate_response → end_response.

    Flow:
        start_event → receive_prompt [is_tool_call=False]
        → rag_query → is_tool_call_gateway [default branch]
        → generate_response → end_response
    """

    def test_text_response_path(self):
        workflow = load_workflow()

        # is_tool_call=False routes to the default (no-tool) branch
        complete_user_task(workflow, "receive_prompt", {"is_tool_call": False})

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Script tasks that must have run
        assert "rag_query" in names, "rag_query script must have run"
        assert "generate_response" in names, "generate_response script must have run"
        assert "end_response" in names, "end_response end event must be reached"

        # Steps that must NOT have executed
        assert "execute_tool" not in names, "execute_tool must NOT be executed on text path"
        assert "mark_blocked" not in names, "mark_blocked must NOT run on text path"
        assert "end_blocked" not in names, "end_blocked must NOT be reached on text path"
        assert "end_tool_complete" not in names, "end_tool_complete must NOT be reached on text path"

        # Verify script task outputs in workflow.data
        assert workflow.data.get("rag_executed") is True, (
            "rag_query should have set rag_executed=True"
        )
        assert workflow.data.get("response_generated") is True, (
            "generate_response should have set response_generated=True"
        )


class TestToolCallAllowed:
    """
    Tool call that passes discipline: receive_prompt → check_discipline → inject_context
    → execute_tool → post_tool_sync → end_tool_complete.

    Flow:
        start_event → receive_prompt [is_tool_call=True]
        → rag_query → is_tool_call_gateway [is_tool_call=True]
        → check_discipline → discipline_result_gateway [default/pass]
        → inject_context → execute_tool → post_tool_sync → end_tool_complete
    """

    def test_tool_call_allowed(self):
        workflow = load_workflow()

        # is_tool_call=True routes to check_discipline;
        # discipline_blocked is absent (falsy) so discipline_result_gateway takes default
        complete_user_task(
            workflow,
            "receive_prompt",
            {"is_tool_call": True, "discipline_blocked": False},
        )

        # Engine stops at execute_tool (user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "execute_tool" in ready_names, (
            f"execute_tool should be READY after discipline passes, got: {ready_names}"
        )

        # Complete the tool execution
        complete_user_task(workflow, "execute_tool", {})

        assert workflow.is_completed(), "Workflow should be completed after tool execution"

        names = completed_spec_names(workflow)

        # Script tasks that must have run
        assert "rag_query" in names, "rag_query script must have run"
        assert "check_discipline" in names, "check_discipline script must have run"
        assert "inject_context" in names, "inject_context script must have run"
        assert "post_tool_sync" in names, "post_tool_sync script must have run"
        assert "end_tool_complete" in names, "end_tool_complete end event must be reached"

        # Steps that must NOT have executed
        assert "mark_blocked" not in names, "mark_blocked must NOT run when discipline passes"
        assert "end_blocked" not in names, "end_blocked must NOT be reached when discipline passes"
        assert "generate_response" not in names, "generate_response must NOT run on tool path"

        # Verify script task outputs in workflow.data
        assert workflow.data.get("rag_executed") is True, (
            "rag_query should have set rag_executed=True"
        )
        assert workflow.data.get("discipline_checked") is True, (
            "check_discipline should have set discipline_checked=True"
        )
        assert workflow.data.get("context_injected") is True, (
            "inject_context should have set context_injected=True"
        )
        assert workflow.data.get("tool_synced") is True, (
            "post_tool_sync should have set tool_synced=True"
        )


class TestToolCallBlocked:
    """
    Tool call blocked by discipline gate: receive_prompt → check_discipline
    → mark_blocked → end_blocked.

    Flow:
        start_event → receive_prompt [is_tool_call=True, discipline_blocked=True]
        → rag_query → is_tool_call_gateway [is_tool_call=True]
        → check_discipline → discipline_result_gateway [discipline_blocked=True]
        → mark_blocked → end_blocked
    """

    def test_tool_call_blocked(self):
        workflow = load_workflow()

        # is_tool_call=True routes to discipline check;
        # discipline_blocked=True routes to mark_blocked
        complete_user_task(
            workflow,
            "receive_prompt",
            {"is_tool_call": True, "discipline_blocked": True},
        )

        assert workflow.is_completed(), "Workflow should be completed after blocking"

        names = completed_spec_names(workflow)

        # Script tasks that must have run
        assert "rag_query" in names, "rag_query script must have run"
        assert "check_discipline" in names, "check_discipline script must have run"
        assert "mark_blocked" in names, "mark_blocked script must have run"
        assert "end_blocked" in names, "end_blocked end event must be reached"

        # Steps that must NOT have executed
        assert "execute_tool" not in names, "execute_tool must NOT be completed when blocked"
        assert "inject_context" not in names, "inject_context must NOT run when blocked"
        assert "post_tool_sync" not in names, "post_tool_sync must NOT run when blocked"
        assert "generate_response" not in names, "generate_response must NOT run on tool path"
        assert "end_tool_complete" not in names, "end_tool_complete must NOT be reached when blocked"

        # Verify script task output
        assert workflow.data.get("blocked") is True, (
            "mark_blocked should have set blocked=True"
        )
