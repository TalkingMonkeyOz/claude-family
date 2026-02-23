"""
Tests for L2_task_work_cycle.bpmn - Task Work Cycle.

Tests the multi-task decompose -> work -> checkpoint -> complete loop.
Loads L2_task_work_cycle.bpmn + L1_core_claude.bpmn (subprocess).

The task work cycle models how Claude processes a user message:
  1. Decompose prompt into tasks (TaskCreate x N)
  2. For each task:
     - Mark in_progress
     - [build] -> BPMN-first gate -> execute via core
     - [simple] -> execute via core directly
     - Checkpoint task context (decisions, files, progress)
     - Mark completed / blocked / session_end
  3. Loop until all tasks done or session interrupted

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
    """One simple task: decompose -> work -> checkpoint -> complete."""

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

        # Core subprocess auto-completes (conversation path)
        # Then checkpoint is a userTask
        assert "checkpoint_task" in ready_names(wf)

        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        assert "decompose_prompt" in names
        assert "sync_tasks_to_db" in names
        assert "select_next_task" in names
        assert "mark_in_progress" in names
        assert "call_core_claude" in names
        assert "checkpoint_task" in names
        assert "sync_checkpoint" in names
        assert "mark_completed" in names
        assert "check_feature" in names

        # BPMN-first gate NOT triggered for simple tasks
        assert "bpmn_first_check" not in names

        assert wf.data.get("tasks_synced") is True
        assert wf.data.get("task_selected") is True
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

        # BPMN-first gate is a userTask
        assert "bpmn_first_check" in ready_names(wf)
        complete(wf, "bpmn_first_check")

        # Then core runs, then checkpoint
        assert "checkpoint_task" in ready_names(wf)
        complete(wf, "checkpoint_task")

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

        # Task 1: checkpoint -> completed -> more_tasks=True -> loop
        complete(wf, "checkpoint_task", {"more_tasks": True})
        assert not wf.is_completed()

        # Task 2: checkpoint -> completed -> more_tasks=True -> loop
        complete(wf, "checkpoint_task", {"more_tasks": True})
        assert not wf.is_completed()

        # Task 3: checkpoint -> completed -> more_tasks=False -> end
        complete(wf, "checkpoint_task", {"more_tasks": False})

        assert wf.is_completed()
        names = completed_names(wf)

        # select_next_task ran 3 times (once per task)
        assert names.count("select_next_task") >= 1  # At least once visible
        assert names.count("mark_completed") >= 1
        assert names.count("checkpoint_task") >= 1


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

        # Checkpoint then outcome=blocked
        complete(wf, "checkpoint_task", {"task_outcome": "blocked", "more_tasks": True})

        # Record blocker (userTask)
        assert "record_blocker" in ready_names(wf)
        complete(wf, "record_blocker", {"more_tasks": True})

        # Loops back, next task completes normally
        assert not wf.is_completed()
        complete(wf, "checkpoint_task", {
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

        complete(wf, "checkpoint_task", {"task_outcome": "blocked", "more_tasks": False})
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

        # Work on first task, then session_end during checkpoint
        complete(wf, "checkpoint_task", {"task_outcome": "session_end"})

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

        complete(wf, "checkpoint_task")

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

        # Core subprocess pauses at execute_tool (userTask)
        assert "execute_tool" in ready_names(wf)
        complete(wf, "execute_tool")

        # Then checkpoint
        assert "checkpoint_task" in ready_names(wf)
        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        assert "select_tool" in names
        assert "execute_tool" in names
        assert "evaluate_result" in names
        assert "checkpoint_task" in names
        assert "mark_completed" in names


class TestBuildTaskWithToolCall:
    """Build task: BPMN-first -> core with tool call -> checkpoint -> complete."""

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

        # BPMN-first gate
        complete(wf, "bpmn_first_check")

        # Core tool execution
        complete(wf, "execute_tool")

        # Checkpoint
        complete(wf, "checkpoint_task")

        assert wf.is_completed()
        names = completed_names(wf)

        assert "bpmn_first_check" in names
        assert "select_tool" in names
        assert "execute_tool" in names
        assert "checkpoint_task" in names
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
        complete(wf, "bpmn_first_check")
        complete(wf, "checkpoint_task", {
            "more_tasks": True,
            "task_type": "simple",  # Next task is simple
        })

        assert not wf.is_completed()

        # Task 2: simple -> no BPMN gate
        complete(wf, "checkpoint_task", {"more_tasks": False})

        assert wf.is_completed()
        names = completed_names(wf)

        assert "bpmn_first_check" in names
        assert names.count("checkpoint_task") >= 2
