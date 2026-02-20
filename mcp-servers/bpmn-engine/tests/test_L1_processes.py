"""
Tests for all 6 L1 architecture processes.

Each L1 process is tested individually with:
  - Happy path (default/simplest flow)
  - Alternative paths (branches via gateways)
  - Loop paths where applicable

Also tests L0→L1 integration: full hierarchy execution with real L1 processes.
And L1→L2 integration: L1_work_tracking delegates to task_lifecycle via callActivity.

SpiffWorkflow gotcha: ALL gateway conditions are evaluated (not short-circuit).
Variables in ANY condition branch must exist in task.data, even for default branches.
"""

import os

import pytest
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

ARCH_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "architecture")
)

LIFECYCLE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle")
)

L1_FILES = {
    "L1_session_management": os.path.join(ARCH_DIR, "L1_session_management.bpmn"),
    "L1_work_tracking": os.path.join(ARCH_DIR, "L1_work_tracking.bpmn"),
    "L1_knowledge_management": os.path.join(ARCH_DIR, "L1_knowledge_management.bpmn"),
    "L1_enforcement": os.path.join(ARCH_DIR, "L1_enforcement.bpmn"),
    "L1_agent_orchestration": os.path.join(ARCH_DIR, "L1_agent_orchestration.bpmn"),
    "L1_config_management": os.path.join(ARCH_DIR, "L1_config_management.bpmn"),
}

L2_FILES = {
    "task_lifecycle": os.path.join(LIFECYCLE_DIR, "task_lifecycle.bpmn"),
}

L0_FILE = os.path.join(ARCH_DIR, "L0_claude_family.bpmn")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_l1(process_id: str, extra_bpmn_files: list = None) -> BpmnWorkflow:
    """Load an L1 process, optionally with L2 subprocess files."""
    parser = BpmnParser()
    parser.add_bpmn_file(L1_FILES[process_id])
    if extra_bpmn_files:
        for f in extra_bpmn_files:
            parser.add_bpmn_file(f)
    spec = parser.get_spec(process_id)
    subspecs = parser.get_subprocess_specs(process_id) if extra_bpmn_files else {}
    wf = BpmnWorkflow(spec, subspecs)
    wf.do_engine_steps()
    return wf


def ready_names(wf: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.READY, manual=True)]


def complete(wf: BpmnWorkflow, name: str, data: dict = None):
    tasks = [t for t in wf.get_tasks(state=TaskState.READY, manual=True) if t.task_spec.name == name]
    assert tasks, f"'{name}' not READY. Ready: {ready_names(wf)}"
    if data:
        tasks[0].data.update(data)
    tasks[0].run()
    wf.do_engine_steps()


def completed_names(wf: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)]


# ===========================================================================
# L1: Session Management
# ===========================================================================


class TestL1SessionManagement:

    def test_fresh_session_auto_close(self):
        """Fresh start -> one prompt -> auto-close."""
        wf = load_l1("L1_session_management")

        # Startup script tasks fire automatically - check they completed
        names = completed_names(wf)
        assert "hook_log_session" in names
        assert "hook_reset_task_map" in names
        assert "hook_archive_stale" in names
        assert "hook_check_inbox" in names

        # Load state: no prior state (must provide prior_state for condition eval)
        complete(wf, "load_state", {"prior_state": False})

        # Work loop: receive prompt, RAG fires, process, auto-close
        complete(wf, "receive_prompt", {"action": "end_auto"})
        complete(wf, "process_prompt")

        assert wf.is_completed()
        assert wf.data.get("close_type") == "auto"

    def test_resumed_session_manual_close(self):
        """Resume prior state -> prompt -> manual /session-end."""
        wf = load_l1("L1_session_management")
        complete(wf, "load_state", {"prior_state": True})
        complete(wf, "restore_context")
        complete(wf, "receive_prompt", {"action": "end_manual"})
        complete(wf, "process_prompt")
        complete(wf, "session_summary")

        assert wf.is_completed()
        assert wf.data.get("knowledge_captured") is True
        assert wf.data.get("close_type") == "manual"

    def test_compact_then_continue(self):
        """Prompt -> compact (same session) -> second prompt -> auto-close."""
        wf = load_l1("L1_session_management")
        complete(wf, "load_state", {"prior_state": False})

        # First prompt: compact (session_id stays the same)
        complete(wf, "receive_prompt", {"action": "compact", "session_id_changed": False})
        complete(wf, "process_prompt")

        # After compact, precompact_inject and save_checkpoint run as script tasks
        names = completed_names(wf)
        assert "precompact_inject" in names
        assert "save_checkpoint" in names

        # Second prompt: auto-close
        complete(wf, "receive_prompt", {"action": "end_auto", "session_id_changed": False})
        complete(wf, "process_prompt")
        assert wf.is_completed()

    def test_continuation_after_compact(self):
        """Compact with session_id change -> continuation warning -> continue (FB108)."""
        wf = load_l1("L1_session_management")
        complete(wf, "load_state", {"prior_state": False})

        # First prompt: compact triggers session_id change
        complete(wf, "receive_prompt", {"action": "compact", "session_id_changed": True})
        complete(wf, "process_prompt")

        # After compact, continuation path should fire (log_continuation proves FB108 path taken)
        names = completed_names(wf)
        assert "precompact_inject" in names
        assert "save_checkpoint" in names
        assert "log_continuation" in names

        # Work continues: second prompt with auto-close
        complete(wf, "receive_prompt", {"action": "end_auto", "session_id_changed": False})
        complete(wf, "process_prompt")
        assert wf.is_completed()


# ===========================================================================
# L1: Work Tracking
# ===========================================================================


class TestL1WorkTracking:

    def test_feature_lifecycle_with_l2(self):
        """Feature: draft -> planned -> execute task via L2 subprocess -> complete."""
        wf = load_l1("L1_work_tracking", extra_bpmn_files=[L2_FILES["task_lifecycle"]])
        complete(wf, "identify_work", {"work_type": "feature"})
        complete(wf, "plan_feature")

        # CallActivity invokes task_lifecycle (L2) - walk through its user tasks
        complete(wf, "create_task", {"has_tasks": True, "action": "complete"})
        complete(wf, "work_on_task", {"action": "complete"})
        # task_lifecycle ends (mark_completed runs as script task)

        # Back in L1: assess if all tasks done
        complete(wf, "assess_task_completion", {"all_tasks_done": True})

        assert wf.is_completed()
        assert wf.data.get("feature_status") == "completed"

    def test_feature_task_loop_with_l2(self):
        """Feature with multiple task rounds through L2 subprocess."""
        wf = load_l1("L1_work_tracking", extra_bpmn_files=[L2_FILES["task_lifecycle"]])
        complete(wf, "identify_work", {"work_type": "feature"})
        complete(wf, "plan_feature")

        # First task via L2: not done yet
        complete(wf, "create_task", {"has_tasks": True, "action": "complete"})
        complete(wf, "work_on_task", {"action": "complete"})
        complete(wf, "assess_task_completion", {"all_tasks_done": False})

        # Second task via L2: now done
        complete(wf, "create_task", {"has_tasks": True, "action": "complete"})
        complete(wf, "work_on_task", {"action": "complete"})
        complete(wf, "assess_task_completion", {"all_tasks_done": True})

        assert wf.is_completed()

    def test_feature_l2_task_with_blocker(self):
        """Feature task hits blocker in L2, resolves, then completes."""
        wf = load_l1("L1_work_tracking", extra_bpmn_files=[L2_FILES["task_lifecycle"]])
        complete(wf, "identify_work", {"work_type": "feature"})
        complete(wf, "plan_feature")

        # Task hits blocker during L2 execution
        complete(wf, "create_task", {"has_tasks": True, "action": "block"})
        complete(wf, "work_on_task", {"action": "block"})
        complete(wf, "resolve_blocker")
        # After resolving, back to work_on_task
        complete(wf, "work_on_task", {"action": "complete"})

        # Back in L1: done
        complete(wf, "assess_task_completion", {"all_tasks_done": True})

        assert wf.is_completed()
        assert wf.data.get("feature_status") == "completed"

    def test_feedback_path(self):
        """Bug/idea feedback created directly (default branch)."""
        wf = load_l1("L1_work_tracking", extra_bpmn_files=[L2_FILES["task_lifecycle"]])
        # Must provide work_type so gateway can evaluate all conditions
        complete(wf, "identify_work", {"work_type": "feedback"})

        assert wf.is_completed()
        assert wf.data.get("feedback_created") is True

    def test_adhoc_tasks(self):
        """Ad-hoc session tasks synced to DB."""
        wf = load_l1("L1_work_tracking", extra_bpmn_files=[L2_FILES["task_lifecycle"]])
        complete(wf, "identify_work", {"work_type": "adhoc"})
        complete(wf, "create_tasks")

        assert wf.is_completed()
        assert wf.data.get("tasks_synced") is True


# ===========================================================================
# L1: Knowledge Management
# ===========================================================================


class TestL1KnowledgeManagement:

    def test_capture_path(self):
        """Capture new knowledge: formulate -> embed -> store."""
        wf = load_l1("L1_knowledge_management")
        complete(wf, "identify_km_action", {"km_action": "capture"})
        complete(wf, "capture_knowledge")

        assert wf.is_completed()
        assert wf.data.get("embedded") is True
        assert wf.data.get("stored") is True

    def test_retrieve_path(self):
        """Retrieve existing knowledge: RAG search -> apply -> track."""
        wf = load_l1("L1_knowledge_management")
        # Must provide km_action so gateway can evaluate capture condition
        complete(wf, "identify_km_action", {"km_action": "retrieve"})
        complete(wf, "apply_knowledge")

        assert wf.is_completed()
        assert wf.data.get("results_found") is True
        assert wf.data.get("application_tracked") is True


# ===========================================================================
# L1: Enforcement
# ===========================================================================


class TestL1Enforcement:

    def test_ungated_tool(self):
        """Read/Glob/Grep bypass discipline gate."""
        wf = load_l1("L1_enforcement")
        complete(wf, "identify_tool", {"is_gated": False})
        complete(wf, "execute_tool")

        assert wf.is_completed()
        assert wf.data.get("post_synced") is True
        # discipline_check was never reached
        assert "discipline_check" not in completed_names(wf)

    def test_gated_tool_allowed(self):
        """Write/Edit/Bash with tasks: allowed through full chain."""
        wf = load_l1("L1_enforcement")
        # Must provide discipline_result so gateway can evaluate all conditions
        complete(wf, "identify_tool", {"is_gated": True, "discipline_result": "allowed"})
        complete(wf, "execute_tool")

        assert wf.is_completed()
        assert wf.data.get("discipline_checked") is True
        assert wf.data.get("context_injected") is True
        assert wf.data.get("standards_validated") is True
        assert wf.data.get("post_synced") is True
        # No continuation warning on exact match
        assert wf.data.get("continuation_warning") is not True

    def test_gated_tool_continuation(self):
        """Session mismatch but fresh map: allowed with warning (FB108 fix)."""
        wf = load_l1("L1_enforcement")
        complete(wf, "identify_tool", {"is_gated": True, "discipline_result": "continuation"})
        complete(wf, "execute_tool")

        assert wf.is_completed()
        assert wf.data.get("discipline_checked") is True
        assert wf.data.get("continuation_warning") is True  # Warning logged
        assert wf.data.get("context_injected") is True       # Still gets full chain
        assert wf.data.get("standards_validated") is True
        assert wf.data.get("post_synced") is True

    def test_gated_tool_blocked(self):
        """Write without tasks: blocked by discipline gate."""
        wf = load_l1("L1_enforcement")
        complete(wf, "identify_tool", {"is_gated": True, "discipline_result": "blocked"})

        assert wf.is_completed()
        assert wf.data.get("tool_blocked") is True
        # inject_context was never reached
        assert "inject_context" not in completed_names(wf)


# ===========================================================================
# L1: Agent Orchestration
# ===========================================================================


class TestL1AgentOrchestration:

    def test_direct_execution(self):
        """Simple task: no agent needed, execute directly."""
        wf = load_l1("L1_agent_orchestration")
        # Must provide need_agent so gateway can evaluate condition
        complete(wf, "assess_complexity", {"need_agent": False})
        complete(wf, "execute_direct")

        assert wf.is_completed()
        assert "spawn_agent" not in completed_names(wf)

    def test_agent_spawn_success(self):
        """Complex task: spawn agent -> success -> integrate."""
        wf = load_l1("L1_agent_orchestration")
        complete(wf, "assess_complexity", {"need_agent": True})
        complete(wf, "select_agent")
        # Must provide agent_result so gateway can evaluate retry condition
        complete(wf, "monitor_agent", {"agent_result": "success"})
        complete(wf, "integrate_result")

        assert wf.is_completed()
        assert wf.data.get("agent_spawned") is True

    def test_agent_retry(self):
        """Agent fails -> retry with different agent -> success."""
        wf = load_l1("L1_agent_orchestration")
        complete(wf, "assess_complexity", {"need_agent": True})
        complete(wf, "select_agent")

        # First attempt: retry
        complete(wf, "monitor_agent", {"agent_result": "retry"})
        assert "select_agent" in ready_names(wf)

        # Second attempt: success
        complete(wf, "select_agent")
        complete(wf, "monitor_agent", {"agent_result": "success"})
        complete(wf, "integrate_result")

        assert wf.is_completed()


# ===========================================================================
# L1: Configuration Management
# ===========================================================================


class TestL1ConfigManagement:

    def test_project_config(self):
        """Project-specific config: update workspace -> generate -> deploy."""
        wf = load_l1("L1_config_management")
        # Must provide config_scope so gateway can evaluate global condition
        complete(wf, "identify_config", {"config_scope": "project"})
        complete(wf, "validate_config")

        assert wf.is_completed()
        assert wf.data.get("workspace_updated") is True
        assert wf.data.get("settings_generated") is True
        assert wf.data.get("components_deployed") is True

    def test_global_config(self):
        """Global config: update template -> generate -> deploy."""
        wf = load_l1("L1_config_management")
        complete(wf, "identify_config", {"config_scope": "global"})
        complete(wf, "validate_config")

        assert wf.is_completed()
        assert wf.data.get("template_updated") is True
        assert wf.data.get("settings_generated") is True


# ===========================================================================
# L0 -> L1 -> L2 Integration
# ===========================================================================


class TestL0L1L2Integration:

    def _load_full_hierarchy(self):
        """Load L0 + all L1s + L2 subprocess files for full hierarchy."""
        parser = BpmnParser()
        for filename in L1_FILES.values():
            parser.add_bpmn_file(filename)
        for filename in L2_FILES.values():
            parser.add_bpmn_file(filename)
        parser.add_bpmn_file(L0_FILE)
        spec = parser.get_spec("claude_process")
        subspecs = parser.get_subprocess_specs("claude_process")
        return BpmnWorkflow(spec, subspecs)

    def test_full_hierarchy_execution(self):
        """L0 -> all 6 L1 processes execute and complete (adhoc path avoids L2)."""
        wf = self._load_full_hierarchy()
        wf.do_engine_steps()

        # Walk through each L1's user tasks with all required gateway variables.
        # Uses adhoc work path to avoid L2 callActivity complexity in integration test.
        scenarios = [
            ("load_state", {"prior_state": False}),
            ("receive_prompt", {"action": "end_auto"}),
            ("process_prompt", {}),
            ("identify_work", {"work_type": "adhoc"}),
            ("create_tasks", {}),
            ("identify_km_action", {"km_action": "retrieve"}),
            ("apply_knowledge", {}),
            ("identify_tool", {"is_gated": False}),
            ("execute_tool", {}),
            ("assess_complexity", {"need_agent": False}),
            ("execute_direct", {}),
            ("identify_config", {"config_scope": "project"}),
            ("validate_config", {}),
        ]

        for name, data in scenarios:
            complete(wf, name, data)

        assert wf.is_completed()

    def test_full_hierarchy_with_feature_l2(self):
        """L0 -> L1_work_tracking feature path -> L2 task_lifecycle subprocess."""
        wf = self._load_full_hierarchy()
        wf.do_engine_steps()

        # Session management: fresh, auto-close
        complete(wf, "load_state", {"prior_state": False})
        complete(wf, "receive_prompt", {"action": "end_auto"})
        complete(wf, "process_prompt")

        # Work tracking: feature path with L2 subprocess
        complete(wf, "identify_work", {"work_type": "feature"})
        complete(wf, "plan_feature")

        # L2 task_lifecycle subprocess executes within L1_work_tracking
        complete(wf, "create_task", {"has_tasks": True, "action": "complete"})
        complete(wf, "work_on_task", {"action": "complete"})
        complete(wf, "assess_task_completion", {"all_tasks_done": True})

        # Knowledge management
        complete(wf, "identify_km_action", {"km_action": "retrieve"})
        complete(wf, "apply_knowledge")

        # Enforcement
        complete(wf, "identify_tool", {"is_gated": False})
        complete(wf, "execute_tool")

        # Agent orchestration
        complete(wf, "assess_complexity", {"need_agent": False})
        complete(wf, "execute_direct")

        # Config management
        complete(wf, "identify_config", {"config_scope": "project"})
        complete(wf, "validate_config")

        assert wf.is_completed()

    def test_all_six_l1_specs_resolved(self):
        """Parser resolves all 6 real L1 processes (not stubs)."""
        parser = BpmnParser()
        for filename in L1_FILES.values():
            parser.add_bpmn_file(filename)
        for filename in L2_FILES.values():
            parser.add_bpmn_file(filename)
        parser.add_bpmn_file(L0_FILE)
        subspecs = parser.get_subprocess_specs("claude_process")

        # 6 L1s + 1 L2 (task_lifecycle referenced by L1_work_tracking)
        assert len(subspecs) >= 6
        assert set(L1_FILES.keys()).issubset(set(subspecs.keys()))
