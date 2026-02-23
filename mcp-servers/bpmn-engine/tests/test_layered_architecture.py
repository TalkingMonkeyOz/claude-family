"""
Tests for the 3-layer BPMN architecture:
  L1_claude_family_extensions -> L2_task_work_cycle -> L1_core_claude

Cross-layer integration tests that verify:
  1. Core runs in isolation without extension files
  2. Extensions properly wrap core via CallActivity (through L2 task work cycle)
  3. Hook injection points are correctly ordered relative to core
  4. "Anthropic update" simulation: changing core data doesn't break extensions

These tests load ALL THREE layers and verify the layering contract between them.
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

ARCH_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "architecture")
)
CORE_FILE = os.path.join(ARCH_DIR, "L1_core_claude.bpmn")
TWC_FILE = os.path.join(ARCH_DIR, "L2_task_work_cycle.bpmn")
EXTENSIONS_FILE = os.path.join(ARCH_DIR, "L1_claude_family_extensions.bpmn")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_core_only(initial_data: dict = None) -> BpmnWorkflow:
    """Load ONLY the core model (no extensions)."""
    parser = BpmnParser()
    parser.add_bpmn_file(CORE_FILE)
    spec = parser.get_spec("L1_core_claude")
    wf = BpmnWorkflow(spec)
    if initial_data:
        for task in wf.get_tasks(state=TaskState.READY):
            task.data.update(initial_data)
    wf.do_engine_steps()
    return wf


def load_extensions_with_core() -> BpmnWorkflow:
    """Load all 3 layers: extensions + task work cycle + core."""
    parser = BpmnParser()
    parser.add_bpmn_file(CORE_FILE)
    parser.add_bpmn_file(TWC_FILE)
    parser.add_bpmn_file(EXTENSIONS_FILE)
    spec = parser.get_spec("L1_claude_family_extensions")
    subspecs = parser.get_subprocess_specs("L1_claude_family_extensions")
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


def all_task_names(wf: BpmnWorkflow) -> list:
    """Return all task spec names (all states) for structural analysis."""
    return [t.task_spec.name for t in wf.get_tasks()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCoreIsolation:
    """Core model runs without extension files and has no hook elements."""

    def test_core_runs_standalone(self):
        """Core completes a question path without extensions."""
        wf = load_core_only({
            "intent_type": "question",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        assert wf.is_completed()
        names = completed_names(wf)
        assert "load_context" in names
        assert "formulate_answer" in names
        assert "deliver_response" in names

    def test_core_has_no_hook_elements(self):
        """No [HOOK], [DB], or [KM] elements exist in core model."""
        wf = load_core_only({
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        all_names = all_task_names(wf)
        for name in all_names:
            assert "[HOOK]" not in name, f"Core has hook element: {name}"
            assert "[DB]" not in name, f"Core has DB element: {name}"
            assert "[KM]" not in name, f"Core has KM element: {name}"

    def test_core_all_elements_are_claude(self):
        """Every non-framework task in core uses [CLAUDE] prefix."""
        parser = BpmnParser()
        parser.add_bpmn_file(CORE_FILE)
        spec = parser.get_spec("L1_core_claude")
        wf = BpmnWorkflow(spec)

        # Check task spec names (not framework internals)
        framework_names = {"Start", "End", "Root", "cc_start", "cc_end",
                          "StartEvent", "EndEvent"}
        for task in wf.get_tasks():
            name = task.task_spec.name
            # Skip framework/internal tasks and gateways
            if (name in framework_names or
                name.endswith("_gw") or
                name.endswith("_merge") or
                "Gateway" in type(task.task_spec).__name__):
                continue
            # All substantive tasks should have [CLAUDE] prefix
            if hasattr(task.task_spec, 'name') and task.task_spec.bpmn_name:
                assert "[CLAUDE]" in task.task_spec.bpmn_name, (
                    f"Core task '{name}' (bpmn_name='{task.task_spec.bpmn_name}') "
                    f"should have [CLAUDE] actor prefix"
                )


class TestExtensionWrapping:
    """Parser resolves CallActivity and both layers' tasks appear."""

    def test_subprocess_spec_resolved(self):
        """Parser resolves L2_task_work_cycle and L1_core_claude as subspecs."""
        parser = BpmnParser()
        parser.add_bpmn_file(CORE_FILE)
        parser.add_bpmn_file(TWC_FILE)
        parser.add_bpmn_file(EXTENSIONS_FILE)
        subspecs = parser.get_subprocess_specs("L1_claude_family_extensions")

        assert "L2_task_work_cycle" in subspecs, (
            f"Expected L2_task_work_cycle in subspecs, got: {list(subspecs.keys())}"
        )
        assert "L1_core_claude" in subspecs, (
            f"Expected L1_core_claude in subspecs, got: {list(subspecs.keys())}"
        )

    def test_all_layers_tasks_appear(self):
        """Extension + L2 + core tasks all appear in completed list."""
        wf = load_extensions_with_core()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })
        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2 task work cycle: decompose prompt
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

        # L2: checkpoint after core completes
        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        # Extension-layer tasks
        assert "hook_log_session" in names
        assert "hook_inject_context" in names
        assert "hook_post_sync" in names
        assert "auto_close" in names

        # L2 task work cycle tasks
        assert "decompose_prompt" in names
        assert "sync_tasks_to_db" in names
        assert "select_next_task" in names
        assert "checkpoint_task" in names
        assert "mark_completed" in names

        # Core-layer tasks (from nested subprocess)
        assert "load_context" in names
        assert "parse_intent" in names
        assert "formulate_answer" in names
        assert "compose_response" in names
        assert "deliver_response" in names


class TestHookInjectionPoints:
    """Hooks inject BEFORE core and sync AFTER core."""

    def test_context_injected_before_core(self):
        """hook_inject_context completes before core's load_context."""
        wf = load_extensions_with_core()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })
        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2: decompose prompt seeds core data
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
        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        # Both must exist
        assert "hook_inject_context" in names
        assert "load_context" in names

        # Injection happens before core (structural guarantee via sequence flows)
        inject_idx = names.index("hook_inject_context")
        context_idx = names.index("load_context")
        assert inject_idx < context_idx, (
            f"hook_inject_context ({inject_idx}) should appear before "
            f"load_context ({context_idx}) in completed order"
        )

    def test_post_sync_after_deliver(self):
        """hook_post_sync runs after core's deliver_response."""
        wf = load_extensions_with_core()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })
        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2: decompose prompt seeds core data
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
        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        deliver_idx = names.index("deliver_response")
        sync_idx = names.index("hook_post_sync")
        assert sync_idx > deliver_idx, (
            f"hook_post_sync ({sync_idx}) should appear after "
            f"deliver_response ({deliver_idx}) in completed order"
        )


class TestAnthropicUpdateSimulation:
    """Simulate changing core model data and verify extensions still work."""

    def test_new_intent_type_extensions_still_work(self):
        """
        If Anthropic adds a new intent type, the core model takes the default
        (conversation) path. Extensions don't care about core internals.
        """
        wf = load_extensions_with_core()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2: decompose with unknown intent type -> core falls to default
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "unknown_new_type",  # Not question/action
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })
        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        # Core takes default (conversation) path
        assert "conversational_reply" in names

        # Extension hooks still fire correctly
        assert "hook_inject_context" in names
        assert "hook_post_sync" in names
        assert "auto_close" in names

    def test_core_tool_loop_extensions_unaffected(self):
        """
        Core doing multiple tool calls doesn't affect extension hook ordering.
        Extensions inject before and sync after, regardless of core internals.
        """
        wf = load_extensions_with_core()

        complete(wf, "load_state", {
            "prior_state": False,
            "session_changed": False,
            "needs_rag": False,
        })

        complete(wf, "receive_prompt", {
            "action": "end_auto",
            "session_id_changed": False,
        })

        # L2: decompose with tool-using action
        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "action",
            "complexity": "simple",
            "needs_tool": True,
            "more_tools_needed": True,
        })

        # First tool call
        complete(wf, "execute_tool", {"more_tools_needed": True})
        # Second tool call
        complete(wf, "execute_tool", {"more_tools_needed": False})

        # L2: checkpoint after core
        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        # Extension hooks ran exactly once each (not multiplied by tool iterations)
        assert names.count("hook_inject_context") == 1
        assert names.count("hook_post_sync") == 1

        # Core tool elements ran
        assert "select_tool" in names
        assert "evaluate_result" in names
        assert "reflect_after_tools" in names

    def test_data_contract_detection(self):
        """
        If core model changes its output variables, extensions can detect this.
        This test verifies the data contract between layers.
        """
        # Run core standalone
        core_wf = load_core_only({
            "intent_type": "question",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })
        assert core_wf.is_completed()

        # Core model guarantees these output variables
        expected_outputs = [
            "context_loaded",
            "intent_parsed",
            "response_composed",
            "response_delivered",
        ]

        for var in expected_outputs:
            assert core_wf.data.get(var) is True, (
                f"Core data contract violation: '{var}' should be True, "
                f"got {core_wf.data.get(var)}"
            )
