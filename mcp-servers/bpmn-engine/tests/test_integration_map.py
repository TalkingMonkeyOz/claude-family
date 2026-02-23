"""
Tests for L1_claude_integration_map.bpmn - Claude Code Integration Point Map.

Maps every external integration point where we can configure, hook into,
or extend Claude's behavior. Organized by lifecycle phase:

  Bootstrap:  Settings → MCPs → CLAUDE.md (global → project) → Rules → Instructions → Skills → Memory
  Session:    SessionStart hooks fire
  Per-prompt: UserPromptSubmit hooks → Claude processes → PreToolUse → Execute → PostToolUse
  Lifecycle:  continue (loop) | compact (PreCompact → loop) | end (SessionEnd → done)

Actor prefixes:
  [CONFIG]  = static config files we control (loaded at startup)
  [HOOK]    = dynamic hook scripts we control (fire at events)
  [BUILTIN] = Claude Code native features (Anthropic controls)

Gateway seed data:
  needs_tool: True/False (default=False)
  more_tools: True/False (default=False)
  lifecycle_event: "continue" (default), "compact", "end"
  needs_rag: True/False (default=True)
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "architecture", "L1_claude_integration_map.bpmn")
)
PROCESS_ID = "L1_claude_integration_map"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the integration map BPMN and return a workflow seeded with initial_data."""
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
    """Default seed data for the integration map."""
    data = {
        "needs_tool": False,
        "more_tools": False,
        "lifecycle_event": "continue",
        "needs_rag": True,
    }
    data.update(overrides)
    return data


# ===========================================================================
# Bootstrap Phase Tests
# ===========================================================================


class TestBootstrapSequence:
    """All 8 config layers load in correct order before session init."""

    def test_bootstrap_completes_before_session(self):
        """All CONFIG elements complete before SessionStart hooks fire."""
        wf = load_workflow(_base_data())
        completed = completed_spec_names(wf)

        config_elements = [
            "load_settings",
            "connect_mcps",
            "load_claude_md_global",
            "load_claude_md_project",
            "load_rules",
            "load_instructions",
            "load_skills",
            "load_memory",
        ]
        for elem in config_elements:
            assert elem in completed, f"Expected {elem} to be completed during bootstrap"

        # SessionStart should also be completed (fires after bootstrap)
        assert "fire_session_start" in completed

    def test_bootstrap_order_preserved(self):
        """Config layers load in dependency order: settings first, memory last."""
        wf = load_workflow(_base_data())
        completed = completed_spec_names(wf)

        ordered_elements = [
            "load_settings",
            "connect_mcps",
            "load_claude_md_global",
            "load_claude_md_project",
            "load_rules",
            "load_instructions",
            "load_skills",
            "load_memory",
        ]

        # Verify all appear and in correct relative order
        indices = [completed.index(e) for e in ordered_elements]
        assert indices == sorted(indices), "Bootstrap elements should execute in order"

    def test_settings_loaded_sets_flags(self):
        """Settings load sets tool_permissions_set flag."""
        wf = load_workflow(_base_data())
        # Find the load_settings task and check its data
        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        settings_tasks = [t for t in tasks if t.task_spec.name == "load_settings"]
        assert settings_tasks
        assert settings_tasks[0].data.get("settings_loaded") is True
        assert settings_tasks[0].data.get("tool_permissions_set") is True

    def test_bootstrap_complete_flag_set(self):
        """The bootstrap_complete flag is set after load_memory."""
        wf = load_workflow(_base_data())
        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        memory_tasks = [t for t in tasks if t.task_spec.name == "load_memory"]
        assert memory_tasks
        assert memory_tasks[0].data.get("bootstrap_complete") is True


class TestConfigCascade:
    """CLAUDE.md global loads before project, demonstrating cascade."""

    def test_global_before_project(self):
        """Global CLAUDE.md loads before project CLAUDE.md."""
        wf = load_workflow(_base_data())
        completed = completed_spec_names(wf)
        global_idx = completed.index("load_claude_md_global")
        project_idx = completed.index("load_claude_md_project")
        assert global_idx < project_idx

    def test_rules_always_active(self):
        """Rules are loaded and marked as always active."""
        wf = load_workflow(_base_data())
        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        rules_tasks = [t for t in tasks if t.task_spec.name == "load_rules"]
        assert rules_tasks
        assert rules_tasks[0].data.get("rules_always_active") is True


# ===========================================================================
# Session Init Tests
# ===========================================================================


class TestSessionInit:
    """SessionStart hooks fire after bootstrap, before first prompt."""

    def test_session_start_fires(self):
        """SessionStart hooks fire and set initialization flags."""
        wf = load_workflow(_base_data())
        completed = completed_spec_names(wf)
        assert "fire_session_start" in completed

    def test_session_start_sets_flags(self):
        """SessionStart sets session_logged, task_map_initialized, etc."""
        wf = load_workflow(_base_data())
        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        session_tasks = [t for t in tasks if t.task_spec.name == "fire_session_start"]
        assert session_tasks
        data = session_tasks[0].data
        assert data.get("session_logged") is True
        assert data.get("task_map_initialized") is True
        assert data.get("stale_archived") is True
        assert data.get("inbox_checked") is True
        assert data.get("session_initialized") is True

    def test_session_start_after_bootstrap(self):
        """SessionStart fires after all bootstrap config is loaded."""
        wf = load_workflow(_base_data())
        completed = completed_spec_names(wf)
        bootstrap_idx = completed.index("load_memory")
        session_idx = completed.index("fire_session_start")
        assert session_idx > bootstrap_idx

    def test_first_user_task_is_receive_prompt(self):
        """After bootstrap + session init, first user task is receive_prompt."""
        wf = load_workflow(_base_data())
        ready = get_ready_user_tasks(wf)
        assert len(ready) == 1
        assert ready[0].task_spec.name == "receive_prompt"


# ===========================================================================
# Prompt Loop Tests
# ===========================================================================


class TestPromptLoopNoTools:
    """Prompt cycle without tool usage."""

    def test_no_tools_path(self):
        """Prompt → UserPromptSubmit → process → no tools → deliver → continue loop."""
        wf = load_workflow(_base_data(lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")

        completed = completed_spec_names(wf)
        assert "fire_user_prompt_submit" in completed
        assert "process_prompt" in completed
        assert "deliver_response" in completed
        assert "fire_session_end" in completed

        # Tool loop should NOT fire
        assert "fire_pre_tool_use" not in completed
        assert "execute_tool" not in completed

    def test_prompt_submit_hooks_fire(self):
        """UserPromptSubmit hooks set classification and RAG flags."""
        wf = load_workflow(_base_data(lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")

        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        submit_tasks = [t for t in tasks if t.task_spec.name == "fire_user_prompt_submit"]
        assert submit_tasks
        data = submit_tasks[0].data
        assert data.get("prompt_classified") is True
        assert data.get("protocol_injected") is True
        assert data.get("skills_suggested") is True


class TestPromptLoopWithTools:
    """Prompt cycle with tool usage and hook wrapping."""

    def test_single_tool_call(self):
        """Tool loop fires PreToolUse → Execute → PostToolUse → deliver."""
        wf = load_workflow(_base_data(needs_tool=True, lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")

        # Should be waiting for execute_tool (userTask)
        ready = get_ready_user_tasks(wf)
        assert len(ready) == 1
        assert ready[0].task_spec.name == "execute_tool"

        # Pre-tool hooks should have fired
        completed = completed_spec_names(wf)
        assert "fire_pre_tool_use" in completed

        # Complete tool execution
        complete_user_task(wf, "execute_tool")

        completed = completed_spec_names(wf)
        assert "fire_post_tool_use" in completed
        assert "deliver_response" in completed
        assert "fire_session_end" in completed

    def test_multi_tool_loop(self):
        """Multiple tool calls loop through PreToolUse → Execute → PostToolUse."""
        wf = load_workflow(_base_data(needs_tool=True, more_tools=True, lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")

        # First tool call
        complete_user_task(wf, "execute_tool")

        # more_tools=True should loop back to pre_tool_use
        ready = get_ready_user_tasks(wf)
        assert len(ready) == 1
        assert ready[0].task_spec.name == "execute_tool"

        # Second tool call - set more_tools=False to exit loop
        complete_user_task(wf, "execute_tool", data={"more_tools": False})

        completed = completed_spec_names(wf)
        assert "deliver_response" in completed
        assert "fire_session_end" in completed

    def test_pre_tool_hooks_wrap_every_call(self):
        """PreToolUse hooks fire before EVERY tool execution."""
        wf = load_workflow(_base_data(needs_tool=True, lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")

        completed = completed_spec_names(wf)
        assert "fire_pre_tool_use" in completed

        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        pre_tasks = [t for t in tasks if t.task_spec.name == "fire_pre_tool_use"]
        assert pre_tasks
        assert pre_tasks[0].data.get("discipline_checked") is True
        assert pre_tasks[0].data.get("context_injected") is True

    def test_post_tool_hooks_sync(self):
        """PostToolUse hooks sync todos, tasks, and log MCP usage."""
        wf = load_workflow(_base_data(needs_tool=True, lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")
        complete_user_task(wf, "execute_tool")

        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        post_tasks = [t for t in tasks if t.task_spec.name == "fire_post_tool_use"]
        assert post_tasks
        data = post_tasks[0].data
        assert data.get("todos_synced") is True
        assert data.get("tasks_synced") is True
        assert data.get("mcp_logged") is True


# ===========================================================================
# Lifecycle Event Tests
# ===========================================================================


class TestContinueLoop:
    """Default lifecycle_event="continue" loops back to receive_prompt."""

    def test_continue_loops_back(self):
        """After deliver, continue loops back to receive_prompt."""
        wf = load_workflow(_base_data(lifecycle_event="continue"))
        complete_user_task(wf, "receive_prompt")

        # Should loop back to receive_prompt
        ready = get_ready_user_tasks(wf)
        assert len(ready) == 1
        assert ready[0].task_spec.name == "receive_prompt"


class TestCompactPath:
    """Compaction lifecycle event fires PreCompact then loops back."""

    def test_compact_fires_precompact(self):
        """Compact event fires PreCompact hooks then returns to prompt loop."""
        wf = load_workflow(_base_data(lifecycle_event="compact"))
        complete_user_task(wf, "receive_prompt")

        completed = completed_spec_names(wf)
        assert "fire_pre_compact" in completed

        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        compact_tasks = [t for t in tasks if t.task_spec.name == "fire_pre_compact"]
        assert compact_tasks
        data = compact_tasks[0].data
        assert data.get("work_items_preserved") is True
        assert data.get("checkpoint_saved") is True

    def test_compact_loops_back_to_prompt(self):
        """After compaction, loops back to receive_prompt (not end)."""
        wf = load_workflow(_base_data(lifecycle_event="compact"))
        complete_user_task(wf, "receive_prompt")

        # Should loop back to receive_prompt after compaction
        ready = get_ready_user_tasks(wf)
        assert len(ready) == 1
        assert ready[0].task_spec.name == "receive_prompt"


class TestEndPath:
    """Session end lifecycle event fires SessionEnd hooks and terminates."""

    def test_end_fires_session_end(self):
        """End event fires SessionEnd hooks then completes workflow."""
        wf = load_workflow(_base_data(lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")

        completed = completed_spec_names(wf)
        assert "fire_session_end" in completed
        assert wf.is_completed()

    def test_session_end_sets_closed_flag(self):
        """SessionEnd hook sets session_closed flag."""
        wf = load_workflow(_base_data(lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")

        tasks = wf.get_tasks(state=TaskState.COMPLETED)
        end_tasks = [t for t in tasks if t.task_spec.name == "fire_session_end"]
        assert end_tasks
        assert end_tasks[0].data.get("session_closed") is True


# ===========================================================================
# Integration Point Classification Tests
# ===========================================================================


class TestIntegrationPointClassification:
    """Verify elements are correctly classified by actor prefix."""

    def test_config_elements_count(self):
        """There are exactly 8 CONFIG integration points (bootstrap layer)."""
        wf = load_workflow(_base_data())
        all_tasks = wf.get_tasks()
        config_tasks = [t for t in all_tasks if "[CONFIG]" in (getattr(t.task_spec, "bpmn_name", "") or "")]
        assert len(config_tasks) == 8

    def test_hook_elements_count(self):
        """There are exactly 6 HOOK integration points (our injection surface)."""
        wf = load_workflow(_base_data(needs_tool=True, lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")
        complete_user_task(wf, "execute_tool")

        all_tasks = wf.get_tasks(state=TaskState.COMPLETED)
        hook_tasks = [t for t in all_tasks if "[HOOK]" in (getattr(t.task_spec, "bpmn_name", "") or "")]
        # SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, SessionEnd = 5
        # (PreCompact only fires on compact path, not here)
        assert len(hook_tasks) == 5

    def test_builtin_elements_exist(self):
        """BUILTIN elements represent Anthropic-controlled features."""
        wf = load_workflow(_base_data(needs_tool=True, lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")
        complete_user_task(wf, "execute_tool")

        all_tasks = wf.get_tasks(state=TaskState.COMPLETED)
        builtin_tasks = [t for t in all_tasks if "[BUILTIN]" in (getattr(t.task_spec, "bpmn_name", "") or "")]
        # receive_prompt (userTask), process_prompt, execute_tool (userTask), deliver_response
        assert len(builtin_tasks) >= 3

    def test_all_hook_events_covered(self):
        """All Claude Code hook events are represented in the model."""
        wf = load_workflow(_base_data(needs_tool=True, lifecycle_event="end"))
        complete_user_task(wf, "receive_prompt")
        complete_user_task(wf, "execute_tool")

        completed = completed_spec_names(wf)

        # Run compact path separately to get PreCompact
        wf2 = load_workflow(_base_data(lifecycle_event="compact"))
        complete_user_task(wf2, "receive_prompt")
        completed2 = completed_spec_names(wf2)

        hook_events = {
            "fire_session_start",          # SessionStart
            "fire_user_prompt_submit",     # UserPromptSubmit
            "fire_pre_tool_use",           # PreToolUse
            "fire_post_tool_use",          # PostToolUse
            "fire_session_end",            # SessionEnd
        }

        compact_events = {
            "fire_pre_compact",            # PreCompact
        }

        for event in hook_events:
            assert event in completed, f"Missing hook event: {event}"
        for event in compact_events:
            assert event in completed2, f"Missing hook event: {event}"


# ===========================================================================
# New Feature Simulation Tests
# ===========================================================================


class TestNewFeatureSimulation:
    """Simulate adding new features and verify model still works."""

    def test_model_with_extra_data(self):
        """Model handles unknown data keys gracefully (new feature params)."""
        wf = load_workflow(_base_data(
            new_anthropic_feature=True,
            interagent_comms_enabled=True,
            lifecycle_event="end",
        ))
        complete_user_task(wf, "receive_prompt")
        assert wf.is_completed()

    def test_tool_loop_resilient_to_extra_flags(self):
        """Tool loop works with additional feature flags present."""
        wf = load_workflow(_base_data(
            needs_tool=True,
            mcp_tool_search_confidence=0.85,
            lifecycle_event="end",
        ))
        complete_user_task(wf, "receive_prompt")
        complete_user_task(wf, "execute_tool")
        assert wf.is_completed()


# ===========================================================================
# Full Session Flow Tests
# ===========================================================================


class TestFullSessionFlow:
    """End-to-end session from launch to close."""

    def test_full_session_no_tools(self):
        """Bootstrap → session → prompt (no tools) → end."""
        wf = load_workflow(_base_data(lifecycle_event="end"))

        # Bootstrap and session init already complete
        completed = completed_spec_names(wf)
        assert "load_settings" in completed
        assert "fire_session_start" in completed

        # Complete prompt cycle
        complete_user_task(wf, "receive_prompt")
        assert wf.is_completed()

        completed = completed_spec_names(wf)
        assert "fire_session_end" in completed

    def test_multi_prompt_session(self):
        """Multiple prompts in one session with continue loop."""
        wf = load_workflow(_base_data(lifecycle_event="continue"))

        # First prompt
        complete_user_task(wf, "receive_prompt")
        assert not wf.is_completed()

        # Second prompt - change to end
        complete_user_task(wf, "receive_prompt", data={"lifecycle_event": "end"})
        assert wf.is_completed()

    def test_session_with_compact_then_end(self):
        """Prompt → compact → prompt → end."""
        wf = load_workflow(_base_data(lifecycle_event="compact"))

        # First prompt triggers compaction
        complete_user_task(wf, "receive_prompt")
        assert not wf.is_completed()

        completed = completed_spec_names(wf)
        assert "fire_pre_compact" in completed

        # Second prompt ends session
        complete_user_task(wf, "receive_prompt", data={"lifecycle_event": "end"})
        assert wf.is_completed()

    def test_session_with_tools_compact_and_end(self):
        """Full flow: prompt with tools → compact → prompt without tools → end."""
        wf = load_workflow(_base_data(needs_tool=True, lifecycle_event="compact"))

        # First prompt - tool call then compact
        complete_user_task(wf, "receive_prompt")
        complete_user_task(wf, "execute_tool")
        assert not wf.is_completed()

        # Second prompt - no tools, end session
        complete_user_task(wf, "receive_prompt", data={
            "needs_tool": False,
            "lifecycle_event": "end",
        })
        assert wf.is_completed()

        completed = completed_spec_names(wf)
        assert "fire_pre_compact" in completed
        assert "fire_session_end" in completed
