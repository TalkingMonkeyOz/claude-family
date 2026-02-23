"""
Tests for L1_claude_family_extensions.bpmn - Claude Family Extension Wrapper.

Tests extensions WITH the core subprocess - loads ALL 3 bpmn files.
The extension model wraps L2_task_work_cycle via CallActivity, which in turn
calls L1_core_claude per task.

Extension lifecycle:
  Session Started
    -> 4 startup hooks
    -> Load state -> [resume] Restore / [fresh] Fresh
    -> Prompt loop:
        receive_prompt -> session change check -> classify -> [RAG] -> inject context
        -> CallActivity(L2_task_work_cycle)
            -> decompose -> for each task: select -> [BPMN-first?] -> core -> auto-checkpoint -> complete
        -> post-sync
        -> action: continue/compact/end_auto/end_manual

Gateway seed data (extensions layer):
  prior_state: True/False (default=False)
  session_changed: True/False (default=False)
  needs_rag: True/False
  action: "continue" (default), "compact", "end_auto", "end_manual"
  session_id_changed: True/False (default=False)

L2 task work cycle seed data (passed to decompose_prompt):
  has_tasks: True/False
  task_type: "simple" (default), "build"
  task_outcome: "completed" (default), "blocked", "session_end"
  more_tasks: True/False (default=False)

Core subprocess seed data (passed through decompose_prompt):
  intent_type, complexity, needs_tool, more_tools_needed
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

ARCH_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "architecture")
)
EXTENSIONS_FILE = os.path.join(ARCH_DIR, "L1_claude_family_extensions.bpmn")
TWC_FILE = os.path.join(ARCH_DIR, "L2_task_work_cycle.bpmn")
CORE_FILE = os.path.join(ARCH_DIR, "L1_core_claude.bpmn")

PROCESS_ID = "L1_claude_family_extensions"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse extensions + task work cycle + core BPMN, return workflow with all subspecs."""
    parser = BpmnParser()
    parser.add_bpmn_file(CORE_FILE)
    parser.add_bpmn_file(TWC_FILE)
    parser.add_bpmn_file(EXTENSIONS_FILE)
    spec = parser.get_spec(PROCESS_ID)
    subspecs = parser.get_subprocess_specs(PROCESS_ID)
    wf = BpmnWorkflow(spec, subspecs)
    wf.do_engine_steps()
    return wf


def ready_names(wf: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.READY, manual=True)]


def complete(wf: BpmnWorkflow, name: str, data: dict = None):
    tasks = [t for t in wf.get_tasks(state=TaskState.READY, manual=True)
             if t.task_spec.name == name]
    assert tasks, f"'{name}' not READY. Ready: {ready_names(wf)}"
    if data:
        tasks[0].data.update(data)
    tasks[0].run()
    wf.do_engine_steps()


def completed_names(wf: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSessionStartupHooks:
    """All 4 startup hooks fire before any user interaction."""

    def test_startup_hooks_auto_fire(self):
        wf = load_workflow()

        names = completed_names(wf)
        assert "hook_log_session" in names
        assert "hook_init_task_map" in names
        assert "hook_archive_stale" in names
        assert "hook_check_inbox" in names

        # First user task should be load_state
        assert "load_state" in ready_names(wf)


class TestFreshAutoClose:
    """Fresh session -> one prompt -> task work cycle -> core processes -> auto-close."""

    def test_fresh_session_auto_close(self):
        wf = load_workflow()

        # Load state: fresh (default path)
        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        # Receive prompt: extensions-layer data only
        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 task work cycle starts - decompose_prompt is now READY
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            # Core subprocess seed data
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # select_next_task is the manual pause point in L2
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        # Core auto-completes (conversation path has no userTasks)
        # mark_completed + auto-checkpoint runs automatically
        # Post-sync and auto-close run as scriptTasks
        assert wf.is_completed()

        names = completed_names(wf)
        assert "hook_inject_context" in names
        assert "call_core_claude" in names
        assert "hook_post_sync" in names
        assert "auto_close" in names
        assert wf.data.get("close_type") == "auto"


class TestResumedManualClose:
    """Resume prior state -> prompt -> task work cycle -> manual /session-end."""

    def test_resumed_session_manual_close(self):
        wf = load_workflow()

        # Load state: has prior state
        complete(wf, "load_state", {
            "prior_state": True,
            "session_changed": False,
            "needs_rag": False,
        })

        # Restore context (userTask for resumed sessions)
        complete(wf, "restore_context")

        # Receive prompt with manual end
        complete(wf, "receive_prompt", {
            "action": "end_manual",
            "session_id_changed": False,
        })

        # L2 task work cycle - decompose
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        # Manual end path: write_summary should now be ready
        complete(wf, "write_summary")

        assert wf.is_completed()
        names = completed_names(wf)
        assert "restore_context" in names
        assert "capture_knowledge" in names
        assert "manual_close" in names
        assert wf.data.get("knowledge_captured") is True
        assert wf.data.get("close_type") == "manual"


class TestRAGForQuestion:
    """Question-type prompt triggers RAG + skill suggestions."""

    def test_rag_fires_for_question(self):
        wf = load_workflow()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": True,  # Question triggers RAG
        })

        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 task work cycle - decompose
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "question",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        # Core auto-completes (question path), auto-checkpoint, auto-close
        assert wf.is_completed()
        names = completed_names(wf)

        assert "hook_query_rag" in names
        assert "hook_suggest_skills" in names
        assert "hook_inject_context" in names
        assert wf.data.get("rag_executed") is True
        assert wf.data.get("skills_suggested") is True


class TestRAGSkippedForAction:
    """Action prompt skips RAG (needs_rag=False)."""

    def test_rag_skipped_for_action(self):
        wf = load_workflow()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 task work cycle - decompose
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "action",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        # Core auto-completes (action, no tool), auto-checkpoint, auto-close
        assert wf.is_completed()
        names = completed_names(wf)

        assert "hook_query_rag" not in names
        assert "hook_suggest_skills" not in names
        assert "hook_inject_context" in names  # Always injects


class TestCoreCalledViaCallActivity:
    """Core subprocess executes via CallActivity chain and its tasks appear in completed."""

    def test_core_tasks_appear(self):
        wf = load_workflow()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 decompose - question path so core auto-completes
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "question",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        assert wf.is_completed()
        names = completed_names(wf)

        # Core Claude tasks should appear from subprocess execution
        assert "load_context" in names
        assert "parse_intent" in names
        assert "formulate_answer" in names
        assert "compose_response" in names
        assert "deliver_response" in names

        # L2 elements should also appear
        assert "decompose_prompt" in names
        assert "sync_tasks_to_db" in names
        assert "select_next_task" in names
        assert "mark_in_progress" in names
        assert "mark_completed" in names
        assert "check_feature" in names

        # call_core_claude element is still the ID in the extensions model
        assert "call_core_claude" in names


class TestToolCallThroughCore:
    """Tool call within core subprocess: extension hooks wrap the full call chain."""

    def test_tool_call_order(self):
        wf = load_workflow()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 decompose - action with tool so core pauses at execute_tool
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "action",
            "complexity": "simple",
            "needs_tool": True,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        # Core subprocess stops at execute_tool (userTask)
        assert not wf.is_completed()
        assert "execute_tool" in ready_names(wf)
        complete(wf, "execute_tool")

        # After core, auto-checkpoint, auto-close
        assert wf.is_completed()
        names = completed_names(wf)

        # Extension hooks ran
        assert "hook_inject_context" in names
        assert "hook_post_sync" in names

        # Core tasks ran
        assert "select_tool" in names
        assert "execute_tool" in names
        assert "evaluate_result" in names


class TestCompactPath:
    """Compact -> checkpoint -> loop back to receive_prompt."""

    def test_compact_loops_back(self):
        wf = load_workflow()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        # First prompt: compact
        complete(wf, "receive_prompt", {
            "action": "compact",
            "session_id_changed": False,
        })

        # L2 task work cycle - decompose for first prompt
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        # After compact, precompact_inject and save_checkpoint should be done
        names = completed_names(wf)
        assert "precompact_inject" in names
        assert "save_checkpoint" in names

        # Should be waiting for next prompt
        assert "receive_prompt" in ready_names(wf)

        # Second prompt: auto-close
        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 task work cycle for second prompt
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        assert wf.is_completed()
        assert wf.data.get("precompact_injected") is True
        assert wf.data.get("checkpoint_saved") is True


class TestContinuationDetection:
    """Compact with session ID change -> continuation warning -> loops back."""

    def test_continuation_warning_logged(self):
        wf = load_workflow()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        # First prompt: compact with session_id change
        complete(wf, "receive_prompt", {
            "action": "compact",
            "session_id_changed": True,
        })

        # L2 task work cycle - decompose for first prompt
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        names = completed_names(wf)
        assert "log_continuation" in names

        # Loops back to receive_prompt
        assert "receive_prompt" in ready_names(wf)

        # Close out with second prompt
        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 task work cycle for second prompt
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        assert wf.is_completed()
        assert wf.data.get("continuation_warning") is True


class TestSessionChangeResetsMap:
    """New session detected -> task map reset -> continues normally."""

    def test_session_change_resets_task_map(self):
        wf = load_workflow()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": True,  # Session changed on first prompt
            "needs_rag": False,
        })

        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 task work cycle - decompose
        assert "decompose_prompt" in ready_names(wf)
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # L2 select next task
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        assert wf.is_completed()
        names = completed_names(wf)

        assert "hook_reset_task_map" in names
        assert wf.data.get("task_map_reset") is True
