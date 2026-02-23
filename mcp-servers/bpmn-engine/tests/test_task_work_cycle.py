"""
Tests for L2_task_work_cycle.bpmn - Task Work Cycle.

Tests the multi-task decompose -> work -> auto-checkpoint -> complete loop.
Loads L2_task_work_cycle.bpmn + L1_core_claude.bpmn (subprocess).

The task work cycle models how Claude processes a user message:
  1. Decompose prompt into tasks (TaskCreate x N)
  2. For each task:
     - Select next ready task (manual decision point)
     - Mark in_progress (auto hook)
     - [build] -> BPMN-first gate -> execute via core
     - [simple] -> execute via core directly
     - Mark completed + auto-checkpoint (auto hook)
     - Check feature completion (auto hook)
  3. Loop until all tasks done, blocked, or session interrupted

Gateway seed data:
  has_tasks: True/False (default=False)
  task_type: "build", default="simple"
  task_outcome: "completed" (default), "blocked", "session_end"
  more_tasks: True/False (default=False)

Core subprocess seed data (passed through):
  intent_type, complexity, needs_tool, more_tools_needed
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

ARCH_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "architecture")
)
TWC_FILE = os.path.join(ARCH_DIR, "L2_task_work_cycle.bpmn")
CORE_FILE = os.path.join(ARCH_DIR, "L1_core_claude.bpmn")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse task work cycle + core BPMN, return workflow with subprocess specs."""
    parser = BpmnParser()
    parser.add_bpmn_file(CORE_FILE)
    parser.add_bpmn_file(TWC_FILE)
    spec = parser.get_spec("L2_task_work_cycle")
    subspecs = parser.get_subprocess_specs("L2_task_work_cycle")
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


class TestNoTasksBlocked:
    """No tasks created -> discipline gate blocks."""

    def test_discipline_gate_blocks(self):
        wf = load_workflow()

        # Decompose but create no tasks
        complete(wf, "decompose_prompt", {
            "has_tasks": False,
            # Core subprocess data (won't be used but needed for gateway eval)
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": False,
        })

        assert wf.is_completed()
        names = completed_names(wf)

        assert "decompose_prompt" in names
        assert "sync_tasks_to_db" in names
        assert "gate_blocked" in names
        assert "select_next_task" not in names
        assert wf.data.get("gate_blocked") is True


class TestSingleSimpleTask:
    """One simple task: decompose -> select -> work -> auto-checkpoint -> complete."""

    def test_single_task_happy_path(self):
        wf = load_workflow()

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

        # select_next_task is the manual pause point
        assert "select_next_task" in ready_names(wf)
        complete(wf, "select_next_task")

        # Core auto-completes (conversation path)
        # mark_completed + auto-checkpoint runs automatically
        # check_feature runs automatically
        # more_tasks=False -> end
        assert wf.is_completed()
        names = completed_names(wf)

        assert "decompose_prompt" in names
        assert "sync_tasks_to_db" in names
        assert "select_next_task" in names
        assert "mark_in_progress" in names
        assert "call_core_claude" in names
        assert "mark_completed" in names
        assert "check_feature" in names

        # BPMN-first gate NOT triggered for simple tasks
        assert "bpmn_first_check" not in names

        # Auto-checkpoint data set by mark_completed script
        assert wf.data.get("tasks_synced") is True
        assert wf.data.get("checkpoint_stored") is True
        assert wf.data.get("feature_checked") is True


class TestBuildTaskBPMNFirst:
    """Build task triggers BPMN-first gate before core execution."""

    def test_bpmn_first_gate(self):
        wf = load_workflow()

        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "build",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # Select task (manual)
        complete(wf, "select_next_task")

        # BPMN-first gate is a userTask
        assert "bpmn_first_check" in ready_names(wf)
        complete(wf, "bpmn_first_check")

        # Core auto-runs, mark_completed auto-runs, check_feature auto-runs
        assert wf.is_completed()
        names = completed_names(wf)

        assert "bpmn_first_check" in names
        assert "call_core_claude" in names
        assert "mark_completed" in names
        assert "check_feature" in names


class TestMultipleTasksLoop:
    """Three tasks: complete first two, complete third -> all done."""

    def test_three_task_loop(self):
        wf = load_workflow()

        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "completed",
            "more_tasks": True,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # Task 1: select -> core -> auto-checkpoint -> more_tasks=True -> loop
        complete(wf, "select_next_task")
        assert not wf.is_completed()

        # Task 2: loop back to select_next_task
        complete(wf, "select_next_task")
        assert not wf.is_completed()

        # Task 3: set more_tasks=False -> completes after core
        complete(wf, "select_next_task", {"more_tasks": False})

        assert wf.is_completed()
        names = completed_names(wf)

        # Tasks executed at least once
        assert "select_next_task" in names
        assert "mark_in_progress" in names
        assert "mark_completed" in names
        assert wf.data.get("checkpoint_stored") is True


class TestTaskBlocked:
    """Task gets blocked -> record blocker -> skip to next -> complete last."""

    def test_blocked_then_continue(self):
        wf = load_workflow()

        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "blocked",
            "more_tasks": True,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # Task 1: select -> core -> outcome=blocked
        complete(wf, "select_next_task")

        # Record blocker (userTask)
        assert "record_blocker" in ready_names(wf)
        complete(wf, "record_blocker", {"more_tasks": True})

        # Loops back, next task completes normally
        assert not wf.is_completed()
        complete(wf, "select_next_task", {
            "task_outcome": "completed",
            "more_tasks": False,
        })

        assert wf.is_completed()
        names = completed_names(wf)

        assert "record_blocker" in names
        assert "mark_blocked" in names
        assert "mark_completed" in names
        assert wf.data.get("task_status") == "completed"


class TestBlockedNoMoreTasks:
    """Single task blocked with no more tasks -> ends at more_tasks_gw."""

    def test_blocked_only_task(self):
        wf = load_workflow()

        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "blocked",
            "more_tasks": False,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        complete(wf, "select_next_task")
        complete(wf, "record_blocker", {"more_tasks": False})

        assert wf.is_completed()
        names = completed_names(wf)

        assert "mark_blocked" in names
        assert "mark_completed" not in names


class TestSessionEndInterruption:
    """Mid-work session end -> snapshot states -> store context -> end."""

    def test_session_end_mid_task(self):
        wf = load_workflow()

        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "simple",
            "task_outcome": "session_end",
            "more_tasks": True,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # Select task, core runs, then session_end outcome
        complete(wf, "select_next_task")

        assert wf.is_completed()
        names = completed_names(wf)

        assert "snapshot_states" in names
        assert "store_session_context" in names
        assert "mark_completed" not in names  # Didn't get to complete

        assert wf.data.get("states_snapshot") is True
        assert wf.data.get("session_context_stored") is True


class TestCoreSubprocessExecutes:
    """Core Claude subprocess executes within task work cycle."""

    def test_core_tasks_appear(self):
        wf = load_workflow()

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

        complete(wf, "select_next_task")

        assert wf.is_completed()
        names = completed_names(wf)

        # Core subprocess tasks should appear
        assert "load_context" in names
        assert "parse_intent" in names
        assert "formulate_answer" in names
        assert "compose_response" in names
        assert "deliver_response" in names


class TestToolCallWithinTask:
    """Task requires tool use -> execute_tool userTask appears."""

    def test_tool_call_pauses_for_execution(self):
        wf = load_workflow()

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

        # Select task
        complete(wf, "select_next_task")

        # Core subprocess pauses at execute_tool (userTask)
        assert "execute_tool" in ready_names(wf)
        complete(wf, "execute_tool")

        # Auto-completes: mark_completed + auto-checkpoint -> end
        assert wf.is_completed()
        names = completed_names(wf)

        assert "select_tool" in names
        assert "execute_tool" in names
        assert "evaluate_result" in names
        assert "mark_completed" in names


class TestBuildTaskWithToolCall:
    """Build task: BPMN-first -> core with tool call -> auto-checkpoint -> complete."""

    def test_build_task_full_flow(self):
        wf = load_workflow()

        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "build",
            "task_outcome": "completed",
            "more_tasks": False,
            "intent_type": "action",
            "complexity": "simple",
            "needs_tool": True,
            "more_tools_needed": False,
        })

        # Select task
        complete(wf, "select_next_task")

        # BPMN-first gate
        complete(wf, "bpmn_first_check")

        # Core tool execution
        complete(wf, "execute_tool")

        # Auto-completes: mark_completed + auto-checkpoint + check_feature -> end
        assert wf.is_completed()
        names = completed_names(wf)

        assert "bpmn_first_check" in names
        assert "select_tool" in names
        assert "execute_tool" in names
        assert "mark_completed" in names
        assert "check_feature" in names


class TestMixedTaskTypes:
    """Two tasks: first is build (BPMN-first), second is simple."""

    def test_mixed_build_and_simple(self):
        wf = load_workflow()

        complete(wf, "decompose_prompt", {
            "has_tasks": True,
            "task_type": "build",
            "task_outcome": "completed",
            "more_tasks": True,
            "intent_type": "conversation",
            "complexity": "simple",
            "needs_tool": False,
            "more_tools_needed": False,
        })

        # Task 1: build -> BPMN-first gate
        complete(wf, "select_next_task")
        complete(wf, "bpmn_first_check")

        # Core auto-runs, mark_completed auto-runs, loops back
        assert not wf.is_completed()

        # Task 2: simple -> switch type, last task
        complete(wf, "select_next_task", {
            "more_tasks": False,
            "task_type": "simple",
        })

        assert wf.is_completed()
        names = completed_names(wf)

        assert "bpmn_first_check" in names


class TestAutoCheckpointData:
    """Verify that mark_completed sets checkpoint_stored automatically."""

    def test_checkpoint_stored_on_completion(self):
        wf = load_workflow()

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

        complete(wf, "select_next_task")

        assert wf.is_completed()

        # Auto-checkpoint data set by mark_completed script
        assert wf.data.get("task_status") == "completed"
        assert wf.data.get("checkpoint_stored") is True
        assert wf.data.get("feature_checked") is True
