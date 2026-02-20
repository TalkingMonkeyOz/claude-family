"""
Tests for the Context Budget Management BPMN process.

Models the decision flow for preventing context exhaustion:
  - Estimate context cost before starting a batch of tasks
  - Choose execution strategy: direct, delegate_all, split_and_delegate
  - Checkpoint state before delegating heavy work

Test scenarios:
  1. Small batch within budget → execute directly
  2. Large batch, all heavy → delegate all to agents
  3. Large batch, mixed → split (execute light, delegate heavy)
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "context_budget_management.bpmn")
)
PROCESS_ID = "context_budget_management"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
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


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestWithinBudget:
    """Small batch, within context budget → execute directly."""

    def test_direct_execution(self):
        wf = load_workflow({
            "batch_size": 2,
            "tokens_per_task": 500,
            "budget_threshold": 5000,
            "within_budget": True,
        })
        completed = completed_spec_names(wf)
        assert "estimate_context_cost" in completed
        assert "execute_directly" in completed
        assert "end_complete" in completed
        # Should NOT enter delegation path
        assert "choose_strategy" not in completed
        assert "spawn_agents" not in completed


class TestDelegateAll:
    """All tasks heavy → delegate everything to agents."""

    def test_spawn_agents_path(self):
        wf = load_workflow({
            "batch_size": 7,
            "tokens_per_task": 10000,
            "budget_threshold": 5000,
            "within_budget": False,
            "all_tasks_heavy": True,
            "strategy": "delegate_all",
        })
        completed = completed_spec_names(wf)
        assert "estimate_context_cost" in completed
        assert "choose_strategy" in completed
        assert "spawn_agents" in completed
        assert "collect_results" in completed
        assert "end_complete" in completed
        # Should NOT execute directly or split
        assert "execute_directly" not in completed
        assert "split_and_execute_chunk" not in completed


class TestSplitAndDelegate:
    """Mixed batch → split: do light tasks, delegate heavy ones."""

    def test_split_path(self):
        wf = load_workflow({
            "batch_size": 5,
            "tokens_per_task": 8000,
            "budget_threshold": 5000,
            "within_budget": False,
            "all_tasks_heavy": False,
            "strategy": "split_and_delegate",
        })
        completed = completed_spec_names(wf)
        assert "estimate_context_cost" in completed
        assert "choose_strategy" in completed
        assert "split_and_execute_chunk" in completed
        assert "checkpoint_state" in completed
        assert "delegate_remainder" in completed
        assert "collect_results" in completed
        assert "end_complete" in completed
        # Should NOT execute directly or spawn_agents directly
        assert "execute_directly" not in completed
        assert "spawn_agents" not in completed


class TestAlwaysEstimates:
    """All paths should always complete the estimation step."""

    def test_estimate_on_direct(self):
        wf = load_workflow({"within_budget": True, "batch_size": 1, "tokens_per_task": 100, "budget_threshold": 5000})
        assert "estimate_context_cost" in completed_spec_names(wf)

    def test_estimate_on_delegate(self):
        wf = load_workflow({"within_budget": False, "all_tasks_heavy": True, "strategy": "delegate_all",
                            "batch_size": 10, "tokens_per_task": 10000, "budget_threshold": 5000})
        assert "estimate_context_cost" in completed_spec_names(wf)


class TestCheckpointOnSplit:
    """Split path must save checkpoint before delegating remainder."""

    def test_checkpoint_before_delegate(self):
        wf = load_workflow({
            "within_budget": False,
            "all_tasks_heavy": False,
            "strategy": "split_and_delegate",
            "batch_size": 5,
            "tokens_per_task": 8000,
            "budget_threshold": 5000,
        })
        completed = completed_spec_names(wf)
        assert "checkpoint_state" in completed
        assert "delegate_remainder" in completed

    def test_no_checkpoint_on_direct(self):
        wf = load_workflow({"within_budget": True, "batch_size": 1, "tokens_per_task": 100, "budget_threshold": 5000})
        assert "checkpoint_state" not in completed_spec_names(wf)

    def test_no_checkpoint_on_delegate_all(self):
        wf = load_workflow({"within_budget": False, "all_tasks_heavy": True, "strategy": "delegate_all",
                            "batch_size": 10, "tokens_per_task": 10000, "budget_threshold": 5000})
        assert "checkpoint_state" not in completed_spec_names(wf)
