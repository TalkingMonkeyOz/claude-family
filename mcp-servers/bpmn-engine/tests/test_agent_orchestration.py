"""
Tests for the Agent Orchestration BPMN process.

Models the full lifecycle: complexity assessment, agent selection, spawn mechanism,
agent execution, result coordination, and integration review.

Two spawn mechanisms:
  1. Native agents (Task tool): default, in-session, hooks active
  2. Orchestrator MCP (spawn_agent): DB tracked, process isolation

Three coordination patterns:
  1. single (default): Receive single result → integrate → review
  2. parallel: Collect parallel results → integrate → review
  3. sequential: Chain sequential outputs → integrate → review

Key BPMN notes:
  - assess_complexity is a userTask (first stop after start).
  - init_assessment is a scriptTask; sets needs_delegation=False, spawn_mechanism="native",
    coordination_pattern="single" as defaults when not already in task.data.
  - delegate_gw default (flow_do_inline) fires when needs_delegation is not True.
  - mechanism_gw default (flow_native) fires when spawn_mechanism is not "orchestrator".
  - pattern_gw default (flow_single) fires when coordination_pattern is not "parallel"/"sequential".
  - select_agent_type and review_result are userTasks.
  - All spawn/hook/context/work/collection nodes are scriptTasks (auto-run).
  - end_merge merges inline path and delegation path before the final end.

Paths tested:
  1. Inline (default): assess(needs_delegation=False) → work_inline → end
  2. Native spawn, single result: assess(needs_delegation=True)
                                  → select_agent_type → spawn_native → log_merge
                                  → subagent_hook_logs → inject_agent_context → agent_works
                                  → pattern_gw [single] → single_result → review_result → end
  3. Orchestrator spawn, parallel: assess(needs_delegation=True, spawn_mechanism=orchestrator,
                                          coordination_pattern=parallel)
                                   → select_agent_type → spawn_orchestrator → log_merge
                                   → … → parallel_collect → review_result → end
  4. Sequential chain: assess(needs_delegation=True, coordination_pattern=sequential)
                       → spawn_native → … → sequential_chain → review_result → end
  5. Inline path isolation: verify work_inline runs without any delegation steps.
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "agent_orchestration.bpmn")
)
PROCESS_ID = "agent_orchestration"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
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


def get_ready_user_tasks(wf: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return wf.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(wf: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(wf)]


def complete_user_task(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() to advance through any subsequent automated tasks.

    Raises AssertionError if the task is not currently READY.
    """
    ready = get_ready_user_tasks(wf)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    wf.do_engine_steps()


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return the spec names of all COMPLETED tasks as a set."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Inline Path (Default - No Delegation)
# ---------------------------------------------------------------------------


class TestInlinePath:
    """
    Simplest path: Claude does the work inline without spawning any agent.

    Flow:
      start → assess_complexity(user, needs_delegation=False)
      → init_assessment(script) → delegate_gw [default/inline]
      → work_inline(script) → end_merge → end

    Assertions:
      - work_inline completed
      - select_agent_type, spawn_native, spawn_orchestrator NOT completed
      - review_result NOT completed (only reached via delegation path)
      - work_done_inline == True
    """

    def test_inline_no_delegation(self):
        wf = load_workflow()

        # assess_complexity is the first userTask
        assert "assess_complexity" in ready_task_names(wf), (
            f"Expected assess_complexity READY. Got: {ready_task_names(wf)}"
        )

        # needs_delegation=False → default delegate_gw branch → work_inline
        complete_user_task(wf, "assess_complexity", {"needs_delegation": False})

        # work_inline is a scriptTask (auto-runs) → end_merge → end
        assert wf.is_completed(), "Workflow should complete on inline path"
        names = completed_spec_names(wf)

        assert "work_inline" in names
        assert "end" in names

        # Delegation-path steps must NOT appear
        assert "select_agent_type" not in names
        assert "spawn_native" not in names
        assert "spawn_orchestrator" not in names
        assert "subagent_hook_logs" not in names
        assert "inject_agent_context" not in names
        assert "agent_works" not in names
        assert "single_result" not in names
        assert "parallel_collect" not in names
        assert "sequential_chain" not in names
        assert "review_result" not in names

        assert wf.data.get("work_done_inline") is True


# ---------------------------------------------------------------------------
# Test 2: Native Spawn, Single Result
# ---------------------------------------------------------------------------


class TestNativeSpawnSingleResult:
    """
    Claude delegates to a native agent; single coordination pattern (default).

    Flow:
      start → assess_complexity(user, needs_delegation=True)
      → init_assessment(script) → delegate_gw [delegate]
      → select_agent_type(user) → mechanism_gw [default/native]
      → spawn_native(script) → log_merge → subagent_hook_logs(script)
      → inject_agent_context(script) → agent_works(script)
      → pattern_gw [default/single] → single_result(script)
      → integrate_merge → review_result(user) → end_merge → end

    Assertions:
      - spawn_native completed (NOT spawn_orchestrator)
      - single_result completed (NOT parallel_collect, sequential_chain)
      - review_result completed
      - native_spawned == True, agent_logged == True, single_completed == True
    """

    def test_native_spawn_single_result(self):
        wf = load_workflow()

        # assess_complexity: delegate needed
        complete_user_task(wf, "assess_complexity", {"needs_delegation": True})

        # init_assessment (script) runs; select_agent_type is the next userTask
        assert "select_agent_type" in ready_task_names(wf), (
            f"Expected select_agent_type READY after delegation decision. Got: {ready_task_names(wf)}"
        )

        # Select agent type; mechanism defaults to "native", pattern defaults to "single"
        complete_user_task(wf, "select_agent_type", {})

        # spawn_native, log_merge, subagent_hook_logs, inject_agent_context, agent_works,
        # single_result are all scriptTasks → review_result is the next userTask
        assert "review_result" in ready_task_names(wf), (
            f"Expected review_result READY after single_result. Got: {ready_task_names(wf)}"
        )

        # Verify automated steps ran before reaching review_result
        names = completed_spec_names(wf)
        assert "spawn_native" in names, "spawn_native must run before review_result"
        assert "subagent_hook_logs" in names, "subagent_hook_logs must run before review_result"
        assert "inject_agent_context" in names
        assert "agent_works" in names
        assert "single_result" in names

        complete_user_task(wf, "review_result", {})

        assert wf.is_completed(), "Workflow should complete after review_result"
        names = completed_spec_names(wf)

        assert "select_agent_type" in names
        assert "spawn_native" in names
        assert "single_result" in names
        assert "review_result" in names
        assert "end" in names

        # Orchestrator and other pattern branches must NOT appear
        assert "spawn_orchestrator" not in names
        assert "parallel_collect" not in names
        assert "sequential_chain" not in names
        assert "work_inline" not in names

        assert wf.data.get("native_spawned") is True
        assert wf.data.get("agent_logged") is True
        assert wf.data.get("single_completed") is True


# ---------------------------------------------------------------------------
# Test 3: Orchestrator Spawn, Parallel Coordination
# ---------------------------------------------------------------------------


class TestOrchestratorSpawnParallel:
    """
    Claude delegates via orchestrator MCP with parallel result collection.

    Flow:
      start → assess_complexity(user, needs_delegation=True,
                                 spawn_mechanism=orchestrator, coordination_pattern=parallel)
      → init_assessment(script) → delegate_gw [delegate]
      → select_agent_type(user) → mechanism_gw [orchestrator]
      → spawn_orchestrator(script) → log_merge → subagent_hook_logs(script)
      → inject_agent_context(script) → agent_works(script)
      → pattern_gw [parallel] → parallel_collect(script)
      → integrate_merge → review_result(user) → end_merge → end

    Assertions:
      - spawn_orchestrator completed (NOT spawn_native)
      - parallel_collect completed (NOT single_result, sequential_chain)
      - orchestrator_spawned == True, parallel_collected == True
    """

    def test_orchestrator_spawn_parallel_collection(self):
        wf = load_workflow()

        # assess_complexity: delegate via orchestrator, parallel pattern
        complete_user_task(wf, "assess_complexity", {
            "needs_delegation": True,
            "spawn_mechanism": "orchestrator",
            "coordination_pattern": "parallel",
        })

        # select_agent_type should be READY
        assert "select_agent_type" in ready_task_names(wf), (
            f"Expected select_agent_type READY. Got: {ready_task_names(wf)}"
        )

        # Pass spawn_mechanism and coordination_pattern through select_agent_type
        # so the downstream gateway conditions can evaluate them
        complete_user_task(wf, "select_agent_type", {
            "spawn_mechanism": "orchestrator",
            "coordination_pattern": "parallel",
        })

        # All scriptTasks auto-run → review_result is the next userTask
        assert "review_result" in ready_task_names(wf), (
            f"Expected review_result READY after parallel_collect. Got: {ready_task_names(wf)}"
        )

        names = completed_spec_names(wf)
        assert "spawn_orchestrator" in names, "spawn_orchestrator must run on orchestrator path"
        assert "parallel_collect" in names, "parallel_collect must run on parallel path"

        complete_user_task(wf, "review_result", {})

        assert wf.is_completed(), "Workflow should complete after review_result"
        names = completed_spec_names(wf)

        assert "spawn_orchestrator" in names
        assert "parallel_collect" in names
        assert "review_result" in names
        assert "end" in names

        # Wrong spawn and pattern branches must NOT appear
        assert "spawn_native" not in names
        assert "single_result" not in names
        assert "sequential_chain" not in names
        assert "work_inline" not in names

        assert wf.data.get("orchestrator_spawned") is True
        assert wf.data.get("parallel_collected") is True


# ---------------------------------------------------------------------------
# Test 4: Sequential Chain Coordination
# ---------------------------------------------------------------------------


class TestSequentialChain:
    """
    Claude delegates to a native agent; sequential chaining coordination pattern.

    Flow:
      start → assess_complexity(user, needs_delegation=True, coordination_pattern=sequential)
      → init_assessment(script) → delegate_gw [delegate]
      → select_agent_type(user) → mechanism_gw [default/native]
      → spawn_native(script) → log_merge → subagent_hook_logs → inject_agent_context
      → agent_works(script) → pattern_gw [sequential]
      → sequential_chain(script) → integrate_merge
      → review_result(user) → end_merge → end

    Assertions:
      - spawn_native completed (native is default mechanism)
      - sequential_chain completed (NOT single_result, parallel_collect)
      - sequential_chained == True
    """

    def test_sequential_chain_coordination(self):
        wf = load_workflow()

        # assess_complexity: delegate with sequential pattern (native mechanism is default)
        complete_user_task(wf, "assess_complexity", {
            "needs_delegation": True,
            "coordination_pattern": "sequential",
        })

        assert "select_agent_type" in ready_task_names(wf), (
            f"Expected select_agent_type READY. Got: {ready_task_names(wf)}"
        )

        # Pass coordination_pattern so pattern_gw can evaluate it downstream
        complete_user_task(wf, "select_agent_type", {
            "coordination_pattern": "sequential",
        })

        # review_result should be READY after sequential_chain auto-runs
        assert "review_result" in ready_task_names(wf), (
            f"Expected review_result READY after sequential_chain. Got: {ready_task_names(wf)}"
        )

        names = completed_spec_names(wf)
        assert "sequential_chain" in names, "sequential_chain must run on sequential path"
        assert "spawn_native" in names, "spawn_native is the default mechanism"

        complete_user_task(wf, "review_result", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "spawn_native" in names
        assert "sequential_chain" in names
        assert "review_result" in names
        assert "end" in names

        # Other pattern branches must NOT appear
        assert "single_result" not in names
        assert "parallel_collect" not in names
        assert "spawn_orchestrator" not in names
        assert "work_inline" not in names

        assert wf.data.get("sequential_chained") is True


# ---------------------------------------------------------------------------
# Test 5: Inline Path Isolation - Delegation Steps Absent
# ---------------------------------------------------------------------------


class TestInlinePathIsolation:
    """
    Inline path must not touch any delegation infrastructure at all.
    Verifies the end_merge correctly accepts the inline path directly.
    """

    def test_inline_path_absent_delegation_steps(self):
        """All agent-related nodes must be absent when work is done inline."""
        wf = load_workflow()
        complete_user_task(wf, "assess_complexity", {"needs_delegation": False})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Full set of delegation-path nodes that must NOT appear
        delegation_nodes = {
            "select_agent_type",
            "spawn_native",
            "spawn_orchestrator",
            "log_merge",
            "subagent_hook_logs",
            "inject_agent_context",
            "agent_works",
            "pattern_gw",
            "single_result",
            "parallel_collect",
            "sequential_chain",
            "integrate_merge",
            "review_result",
        }
        for node in delegation_nodes:
            assert node not in names, (
                f"Delegation node '{node}' must NOT appear on inline path"
            )

        assert "work_inline" in names
        assert wf.data.get("work_done_inline") is True

    def test_default_load_is_inline(self):
        """With no initial data, init_assessment defaults needs_delegation=False → inline."""
        wf = load_workflow()
        # assess_complexity must be READY first
        assert "assess_complexity" in ready_task_names(wf)
        # Complete with no data → init_assessment defaults needs_delegation=False
        complete_user_task(wf, "assess_complexity", {})

        assert wf.is_completed()
        assert "work_inline" in completed_spec_names(wf)
        assert "select_agent_type" not in completed_spec_names(wf)


# ---------------------------------------------------------------------------
# Test 6: Script Data Flags - Automated Task Outputs
# ---------------------------------------------------------------------------


class TestScriptDataFlags:
    """Verify scriptTask data flags propagate correctly for each spawn path."""

    def test_native_single_sets_all_flags(self):
        """Native spawn + single result must set native_spawned, agent_logged, single_completed."""
        wf = load_workflow()
        complete_user_task(wf, "assess_complexity", {"needs_delegation": True})
        complete_user_task(wf, "select_agent_type", {})
        complete_user_task(wf, "review_result", {})

        assert wf.is_completed()
        assert wf.data.get("native_spawned") is True
        assert wf.data.get("agent_logged") is True
        assert wf.data.get("context_injected") is True
        assert wf.data.get("agent_completed") is True
        assert wf.data.get("single_completed") is True

    def test_orchestrator_parallel_sets_all_flags(self):
        """Orchestrator + parallel must set orchestrator_spawned, parallel_collected."""
        wf = load_workflow()
        complete_user_task(wf, "assess_complexity", {
            "needs_delegation": True,
            "spawn_mechanism": "orchestrator",
            "coordination_pattern": "parallel",
        })
        complete_user_task(wf, "select_agent_type", {
            "spawn_mechanism": "orchestrator",
            "coordination_pattern": "parallel",
        })
        complete_user_task(wf, "review_result", {})

        assert wf.is_completed()
        assert wf.data.get("orchestrator_spawned") is True
        assert wf.data.get("parallel_collected") is True

    def test_sequential_sets_chained_flag(self):
        """Sequential pattern must set sequential_chained=True."""
        wf = load_workflow()
        complete_user_task(wf, "assess_complexity", {
            "needs_delegation": True,
            "coordination_pattern": "sequential",
        })
        complete_user_task(wf, "select_agent_type", {"coordination_pattern": "sequential"})
        complete_user_task(wf, "review_result", {})

        assert wf.is_completed()
        assert wf.data.get("sequential_chained") is True
