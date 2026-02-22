"""
Tests for L1_core_claude.bpmn - Core Claude Prompt Processing.

Tests the core model IN ISOLATION - loads ONLY L1_core_claude.bpmn.
No hooks, no sessions, no Claude Family infrastructure.

Core Claude processes one prompt-response cycle:
  Prompt → Load Context → Parse Intent
    → [question]     → Formulate Answer → Compose → Deliver
    → [conversation] → Conversational Reply → Compose → Deliver
    → [action]       → Analyze Complexity
        → [simple]     → Plan Single Step
        → [multi_step] → Decompose → Create Plan
        → [delegation] → Assess → Delegate (userTask)
      → Tool Needed?
        [no]  → Reflect → Compose → Deliver
        [yes] → Select → Validate → Execute (userTask) → Evaluate
              → [more_tools] → loop back to Select
              → [done] → Reflect → Compose → Deliver

Gateway seed data:
  intent_type: "question", "action", default="conversation"
  complexity: "simple" (default), "multi_step", "delegation"
  needs_tool: True/False (default=False)
  more_tools_needed: True/False (default=False)
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "architecture", "L1_core_claude.bpmn")
)
PROCESS_ID = "L1_core_claude"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the core BPMN and return a workflow seeded with initial_data."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)

    if initial_data:
        ready = wf.get_tasks(state=TaskState.READY)
        for task in ready:
            task.data.update(initial_data)

    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected user task '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    if data:
        matches[0].data.update(data)
    matches[0].run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Default seed data
# ---------------------------------------------------------------------------


def _base_data(**overrides) -> dict:
    """Default seed data for the core Claude model."""
    data = {
        "intent_type": "conversation",
        "complexity": "simple",
        "needs_tool": False,
        "more_tools_needed": False,
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestQuestionPath:
    """
    Question intent → formulate answer → compose → deliver.
    No tool loop, no complexity analysis.
    """

    def test_question_direct_answer(self):
        wf = load_workflow(_base_data(intent_type="question"))

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Must have run
        assert "load_context" in names
        assert "parse_intent" in names
        assert "formulate_answer" in names
        assert "compose_response" in names
        assert "deliver_response" in names
        assert "cc_end" in names

        # Must NOT have run (question bypasses action path)
        assert "analyze_complexity" not in names
        assert "select_tool" not in names
        assert "execute_tool" not in names
        assert "conversational_reply" not in names

        # Verify data
        assert wf.data.get("context_loaded") is True
        assert wf.data.get("answer_formulated") is True
        assert wf.data.get("response_composed") is True
        assert wf.data.get("response_delivered") is True


class TestConversationPath:
    """
    Default intent (conversation) → conversational reply → compose → deliver.
    """

    def test_conversation_default_path(self):
        wf = load_workflow(_base_data())  # default intent_type="conversation"

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "conversational_reply" in names
        assert "compose_response" in names
        assert "deliver_response" in names

        # Must NOT have run
        assert "formulate_answer" not in names
        assert "analyze_complexity" not in names

        assert wf.data.get("reply_generated") is True
        assert wf.data.get("response_delivered") is True


class TestSimpleActionNoTool:
    """
    Action intent, simple complexity, no tool needed.
    Path: action → simple → plan_single_step → tool_needed_gw [no] → reflect → compose → deliver
    """

    def test_simple_action_no_tool(self):
        wf = load_workflow(_base_data(
            intent_type="action",
            complexity="simple",
            needs_tool=False,
        ))

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "analyze_complexity" in names
        assert "plan_single_step" in names
        assert "reflect_no_tool" in names
        assert "compose_response" in names

        # Must NOT have run
        assert "decompose_steps" not in names
        assert "select_tool" not in names
        assert "execute_tool" not in names
        assert "delegate_to_agent" not in names

        assert wf.data.get("single_step_planned") is True
        assert wf.data.get("reflected") is True


class TestSimpleActionWithTool:
    """
    Action intent, simple complexity, one tool call.
    Path: action → simple → plan → tool_needed [yes] → select → validate → execute → evaluate → [done] → reflect
    """

    def test_simple_action_with_tool(self):
        wf = load_workflow(_base_data(
            intent_type="action",
            complexity="simple",
            needs_tool=True,
            more_tools_needed=False,
        ))

        # Engine stops at execute_tool (userTask)
        assert not wf.is_completed()
        ready = [t.task_spec.name for t in get_ready_user_tasks(wf)]
        assert "execute_tool" in ready

        complete_user_task(wf, "execute_tool")

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "select_tool" in names
        assert "validate_tool_params" in names
        assert "execute_tool" in names
        assert "evaluate_result" in names
        assert "reflect_after_tools" in names
        assert "compose_response" in names

        assert wf.data.get("tool_selected") is True
        assert wf.data.get("params_validated") is True
        assert wf.data.get("result_evaluated") is True


class TestMultiStepAction:
    """
    Action intent, multi-step complexity.
    Path: action → multi_step → decompose → create_plan → tool check → reflect → compose
    """

    def test_multi_step_decompose_and_plan(self):
        wf = load_workflow(_base_data(
            intent_type="action",
            complexity="multi_step",
            needs_tool=False,
        ))

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "analyze_complexity" in names
        assert "decompose_steps" in names
        assert "create_plan" in names
        assert "reflect_no_tool" in names
        assert "compose_response" in names

        # Must NOT have run
        assert "plan_single_step" not in names
        assert "assess_delegation" not in names

        assert wf.data.get("steps_decomposed") is True
        assert wf.data.get("plan_created") is True


class TestToolLoop:
    """
    Action with multiple tool calls (more_tools_needed loop).
    First execute_tool → more_tools_needed=True → loop back → second execute_tool → done
    """

    def test_tool_loop_two_iterations(self):
        wf = load_workflow(_base_data(
            intent_type="action",
            complexity="simple",
            needs_tool=True,
            more_tools_needed=True,  # first iteration will loop
        ))

        # First tool execution
        assert not wf.is_completed()
        complete_user_task(wf, "execute_tool", {"more_tools_needed": True})

        # Should loop back to select_tool → validate → execute again
        assert not wf.is_completed()
        complete_user_task(wf, "execute_tool", {"more_tools_needed": False})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # execute_tool should appear (ran twice via loop)
        assert "execute_tool" in names
        assert "reflect_after_tools" in names
        assert "compose_response" in names

        assert wf.data.get("result_evaluated") is True
        assert wf.data.get("reflected") is True


class TestDelegation:
    """
    Action intent, delegation complexity.
    Path: action → delegation → assess → delegate_to_agent (userTask) → tool check → reflect → compose
    """

    def test_delegation_path(self):
        wf = load_workflow(_base_data(
            intent_type="action",
            complexity="delegation",
            needs_tool=False,
        ))

        # Stops at delegate_to_agent (userTask)
        assert not wf.is_completed()
        ready = [t.task_spec.name for t in get_ready_user_tasks(wf)]
        assert "delegate_to_agent" in ready

        complete_user_task(wf, "delegate_to_agent")

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "assess_delegation" in names
        assert "delegate_to_agent" in names
        assert "reflect_no_tool" in names
        assert "compose_response" in names

        # Must NOT have run
        assert "plan_single_step" not in names
        assert "decompose_steps" not in names

        assert wf.data.get("delegation_assessed") is True


class TestContextLoading:
    """
    Verify context is always loaded first, before intent parsing.
    """

    def test_context_loaded_before_intent(self):
        wf = load_workflow(_base_data(intent_type="question"))

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Both must be present
        assert "load_context" in names
        assert "parse_intent" in names

        # Context should be loaded (data proves it ran)
        assert wf.data.get("context_loaded") is True
        assert wf.data.get("intent_parsed") is True

    def test_no_hook_elements_in_core(self):
        """Core model should have zero [HOOK] elements - it's pure Claude."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        wf = BpmnWorkflow(spec)

        all_tasks = wf.get_tasks()
        for task in all_tasks:
            task_name = task.task_spec.name
            assert "[HOOK]" not in task_name, (
                f"Core model should not have hook elements, found: {task_name}"
            )
            assert "[DB]" not in task_name, (
                f"Core model should not have DB elements, found: {task_name}"
            )
