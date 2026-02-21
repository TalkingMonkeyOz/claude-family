"""
Tests for the Hook Chain BPMN process (v2 - rewritten model).

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

Hook Chain Process (v2):
  Phase 1 - RAG Hook (UserPromptSubmit):
    start → check_session_changed → session_changed_gw
      [session_changed] → reset_task_map → classify_prompt
      [default/same]    → classify_prompt
    classify_prompt → needs_rag_gw
      [needs_rag]  → query_rag → query_skill_suggestions → inject_rag_context
      [default]    → inject_rag_context

  Phase 2 - Discipline (PreToolUse):
    inject_rag_context → is_tool_call_gw
      [is_tool_call] → check_discipline → discipline_result_gw
        [discipline_blocked] → mark_blocked → end_blocked
        [default/pass]       → inject_tool_context → execute_tool [user task]
      [default/no tool] → generate_response → end_response

  Phase 3 - Post-tool (PostToolUse):
    execute_tool → post_tool_sync → end_tool_complete
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


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow instance seeded with initial_data.

    The new model has no user task at the start - all script tasks auto-execute.
    Seed data is required for script tasks to evaluate correctly (task_map,
    current_session_id, prompt, is_tool_call, tool_name).
    """
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)

    if initial_data:
        # Seed data on the READY start event task before advancing
        ready = wf.get_tasks(state=TaskState.READY)
        for task in ready:
            task.data.update(initial_data)

    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    """Find the named READY user task, merge data, run it, then advance."""
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
# Default seed data
# ---------------------------------------------------------------------------

def _base_data(**overrides) -> dict:
    """Return default seed data for the hook chain, with overrides applied."""
    data = {
        'task_map': {'_session_id': 'sess-abc123'},
        'current_session_id': 'sess-abc123',
        'prompt': 'how does the hook chain work?',
        'is_tool_call': False,
        'tool_name': '',
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestActionPromptNoTool:
    """
    Action prompt (starts with /) skips RAG, no tool call -> text response.

    Path: start -> check_session_changed -> session_changed_gw [same]
          -> classify_prompt [is_action=True, needs_rag=False]
          -> needs_rag_gw [skip] -> inject_rag_context
          -> is_tool_call_gw [no tool] -> generate_response -> end_response
    """

    def test_action_prompt_skips_rag(self):
        wf = load_workflow(_base_data(
            prompt='/commit changes',
            is_tool_call=False,
        ))

        assert wf.is_completed(), "Workflow should complete without user tasks"

        names = completed_spec_names(wf)

        # Must have run
        assert "check_session_changed" in names
        assert "classify_prompt" in names
        assert "inject_rag_context" in names
        assert "generate_response" in names
        assert "end_response" in names

        # Must NOT have run (RAG skipped)
        assert "query_rag" not in names, "RAG should be skipped for action prompts"
        assert "query_skill_suggestions" not in names
        assert "reset_task_map" not in names, "Session didn't change"

        # Must NOT have run (no tool call)
        assert "execute_tool" not in names
        assert "check_discipline" not in names
        assert "mark_blocked" not in names

        # Verify data
        assert wf.data.get("session_changed") is False
        assert wf.data.get("needs_rag") is False
        assert wf.data.get("response_generated") is True
        assert wf.data.get("context_injected") is True


class TestQuestionPromptWithRAG:
    """
    Question prompt triggers RAG + skill suggestions, no tool call -> text response.

    Path: start -> check_session_changed -> session_changed_gw [same]
          -> classify_prompt [needs_rag=True]
          -> needs_rag_gw [do_rag] -> query_rag -> query_skill_suggestions
          -> inject_rag_context
          -> is_tool_call_gw [no tool] -> generate_response -> end_response
    """

    def test_question_prompt_triggers_rag(self):
        wf = load_workflow(_base_data(
            prompt='how does the hook chain work?',
            is_tool_call=False,
        ))

        assert wf.is_completed(), "Workflow should complete without user tasks"

        names = completed_spec_names(wf)

        # RAG path must have run
        assert "query_rag" in names, "RAG should run for question prompts"
        assert "query_skill_suggestions" in names, "Skills should run after RAG"
        assert "inject_rag_context" in names
        assert "generate_response" in names
        assert "end_response" in names

        # Must NOT have run
        assert "reset_task_map" not in names
        assert "execute_tool" not in names
        assert "check_discipline" not in names

        # Verify data
        assert wf.data.get("needs_rag") is True
        assert wf.data.get("rag_executed") is True
        assert wf.data.get("response_generated") is True


class TestToolCallAllowed:
    """
    Tool call with tasks present -> discipline passes -> execute_tool -> complete.

    Path: start -> ... -> is_tool_call_gw [tool call]
          -> check_discipline [has_tasks=True, discipline_blocked=False]
          -> discipline_result_gw [pass] -> inject_tool_context
          -> execute_tool [user task] -> post_tool_sync -> end_tool_complete
    """

    def test_tool_call_allowed_with_tasks(self):
        wf = load_workflow(_base_data(
            prompt='fix the bug in auth.py',
            is_tool_call=True,
            tool_name='Write',
            task_map={'_session_id': 'sess-abc123', 'tasks': {'1': 'Fix auth bug'}},
        ))

        # Engine stops at execute_tool (user task)
        assert not wf.is_completed()
        ready = [t.task_spec.name for t in get_ready_user_tasks(wf)]
        assert "execute_tool" in ready, f"execute_tool should be READY, got: {ready}"

        # Complete the tool execution
        complete_user_task(wf, "execute_tool", {})

        assert wf.is_completed(), "Workflow should complete after tool execution"

        names = completed_spec_names(wf)

        # Must have run
        assert "check_discipline" in names
        assert "inject_tool_context" in names
        assert "post_tool_sync" in names
        assert "end_tool_complete" in names

        # Must NOT have run
        assert "mark_blocked" not in names
        assert "end_blocked" not in names
        assert "generate_response" not in names

        # Verify data
        assert wf.data.get("discipline_blocked") is False
        assert wf.data.get("coding_standards_injected") is True
        assert wf.data.get("tool_synced") is True


class TestToolCallBlocked:
    """
    Gated tool with no tasks -> discipline blocks -> end_blocked.

    Path: start -> ... -> is_tool_call_gw [tool call]
          -> check_discipline [has_tasks=False, is_gated=True, discipline_blocked=True]
          -> discipline_result_gw [blocked] -> mark_blocked -> end_blocked
    """

    def test_gated_tool_blocked_without_tasks(self):
        wf = load_workflow(_base_data(
            prompt='fix the bug',
            is_tool_call=True,
            tool_name='Write',
            # task_map has no 'tasks' key - empty
            task_map={'_session_id': 'sess-abc123'},
        ))

        assert wf.is_completed(), "Workflow should complete (blocked path has no user tasks)"

        names = completed_spec_names(wf)

        # Must have run
        assert "check_discipline" in names
        assert "mark_blocked" in names
        assert "end_blocked" in names

        # Must NOT have run
        assert "inject_tool_context" not in names
        assert "execute_tool" not in names
        assert "post_tool_sync" not in names
        assert "end_tool_complete" not in names
        assert "generate_response" not in names

        # Verify data
        assert wf.data.get("discipline_blocked") is True
        assert wf.data.get("blocked") is True


class TestNonGatedToolAllowed:
    """
    Non-gated tool (e.g. Read) passes discipline even without tasks.

    Path: same as TestToolCallAllowed, but tool_name='Read' is not in GATED_TOOLS.
    check_discipline computes discipline_blocked=False because is_gated=False.
    """

    def test_non_gated_tool_passes_without_tasks(self):
        wf = load_workflow(_base_data(
            prompt='read the file',
            is_tool_call=True,
            tool_name='Read',  # Not in GATED_TOOLS
            task_map={'_session_id': 'sess-abc123'},  # No tasks
        ))

        # Should reach execute_tool (non-gated tools pass discipline)
        assert not wf.is_completed()
        ready = [t.task_spec.name for t in get_ready_user_tasks(wf)]
        assert "execute_tool" in ready

        complete_user_task(wf, "execute_tool", {})
        assert wf.is_completed()

        names = completed_spec_names(wf)
        assert "check_discipline" in names
        assert "inject_tool_context" in names
        assert "end_tool_complete" in names
        assert "mark_blocked" not in names

        # discipline_blocked should be False (Read not gated)
        assert wf.data.get("discipline_blocked") is False


class TestSessionChanged:
    """
    Session changed -> task_map reset -> continues normally.

    Path: start -> check_session_changed [session_changed=True]
          -> session_changed_gw [changed] -> reset_task_map
          -> classify_prompt -> ... -> end_response
    """

    def test_session_change_triggers_reset(self):
        wf = load_workflow(_base_data(
            task_map={'_session_id': 'old-session-id', 'tasks': {'1': 'Old task'}},
            current_session_id='new-session-id',
            prompt='/commit',
            is_tool_call=False,
        ))

        assert wf.is_completed()

        names = completed_spec_names(wf)

        # Reset path must have run
        assert "check_session_changed" in names
        assert "reset_task_map" in names, "Task map should be reset when session changes"
        assert "classify_prompt" in names
        assert "end_response" in names

        # Verify data
        assert wf.data.get("session_changed") is True
        assert wf.data.get("task_map_reset") is True
        # After reset, task_map should have new session_id and no tasks
        assert wf.data.get("task_map") == {'_session_id': 'new-session-id'}


class TestSessionSame:
    """
    Same session -> no reset -> continues with existing task_map.

    Path: start -> check_session_changed [session_changed=False]
          -> session_changed_gw [same/default] -> classify_prompt -> ...
    """

    def test_same_session_preserves_task_map(self):
        original_map = {'_session_id': 'sess-abc123', 'tasks': {'1': 'My task'}}
        wf = load_workflow(_base_data(
            task_map=original_map,
            prompt='/status',
            is_tool_call=False,
        ))

        assert wf.is_completed()

        names = completed_spec_names(wf)

        # Reset must NOT have run
        assert "reset_task_map" not in names, "Task map should NOT be reset for same session"

        # Verify data
        assert wf.data.get("session_changed") is False
        # Task map should be preserved (not wiped)
        assert wf.data.get("task_map") == original_map


class TestSessionChangedThenToolBlocked:
    """
    Session changed + gated tool + no tasks after reset -> blocked.

    This tests the FB141 fix: session change resets task_map, so discipline
    correctly sees no tasks and blocks the gated tool.
    """

    def test_session_change_resets_tasks_then_blocks(self):
        wf = load_workflow(_base_data(
            task_map={'_session_id': 'old-session', 'tasks': {'1': 'Old task'}},
            current_session_id='new-session',
            prompt='fix the bug',
            is_tool_call=True,
            tool_name='Edit',
        ))

        assert wf.is_completed(), "Blocked path completes without user tasks"

        names = completed_spec_names(wf)

        # Session reset happened
        assert "reset_task_map" in names
        # Then discipline blocked (no tasks after reset)
        assert "check_discipline" in names
        assert "mark_blocked" in names
        assert "end_blocked" in names

        # Task map was reset - old tasks gone
        assert wf.data.get("task_map_reset") is True
        assert wf.data.get("discipline_blocked") is True
