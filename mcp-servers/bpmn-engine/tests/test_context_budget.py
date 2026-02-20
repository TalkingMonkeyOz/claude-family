"""
Tests for the Context Budget Enforcement BPMN process (v2).

Models the full lifecycle from task classification to execution strategy:
  - Classify tasks by complexity (heavy/medium/light)
  - Estimate context budget with safety margin
  - Choose strategy: direct, delegate_all, split_and_delegate, direct_fallback
  - Prepare agent instructions, checkpoint state, collect results

4 execution paths:
  1. Within budget -> execute with progressive checkpoints
  2. Over budget, all heavy -> delegate all to agents
  3. Over budget, mixed -> split (light inline, heavy delegated)
  4. Over budget, no heavy -> direct with aggressive checkpoints (fallback)
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


def get_task_data(workflow: BpmnWorkflow, spec_name: str) -> dict:
    """Get data dict from a specific completed task by spec name."""
    for t in workflow.get_tasks(state=TaskState.COMPLETED):
        if t.task_spec.name == spec_name:
            return dict(t.data)
    return {}


# ---------------------------------------------------------------------------
# PATH A: Within Budget - Direct Execution
# ---------------------------------------------------------------------------

class TestWithinBudget:
    """Small batch within context budget -> execute directly with checkpoints."""

    def test_direct_path_completes(self):
        wf = load_workflow({
            "task_count": 3,
            "heavy_count": 0,
            "medium_count": 2,
            "light_count": 1,
            "remaining_budget": 50000,
        })
        completed = completed_spec_names(wf)
        assert "classify_tasks" in completed
        assert "estimate_budget" in completed
        assert "execute_with_checkpoints" in completed
        assert wf.is_completed()
        data = get_task_data(wf, "execute_with_checkpoints")
        assert data.get("execution_strategy") == "direct_with_checkpoints"
        assert data.get("checkpoints_enabled") is True

    def test_direct_path_skips_delegation(self):
        wf = load_workflow({
            "task_count": 2,
            "heavy_count": 0,
            "medium_count": 1,
            "light_count": 1,
            "remaining_budget": 50000,
        })
        completed = completed_spec_names(wf)
        assert "choose_strategy" not in completed
        assert "spawn_agents" not in completed
        assert "execute_light_tasks" not in completed
        assert "collect_and_verify" not in completed

    def test_budget_estimation_math(self):
        """Verify: 2 heavy + 3 medium + 5 light = 2*800 + 3*400 + 5*100 = 3300 tokens.
        With budget 50000 and 0.6 safety: 3300 < 30000 = within budget."""
        wf = load_workflow({
            "task_count": 10,
            "heavy_count": 2,
            "medium_count": 3,
            "light_count": 5,
            "remaining_budget": 50000,
        })
        data = get_task_data(wf, "estimate_budget")
        assert data.get("estimated_tokens") == 3300
        assert data.get("within_budget") is True


# ---------------------------------------------------------------------------
# PATH B: Delegate All
# ---------------------------------------------------------------------------

class TestDelegateAll:
    """All tasks heavy, over budget -> prepare instructions, checkpoint, spawn agents."""

    def test_delegate_all_full_path(self):
        wf = load_workflow({
            "task_count": 5,
            "heavy_count": 5,
            "medium_count": 0,
            "light_count": 0,
            "remaining_budget": 3000,
        })
        completed = completed_spec_names(wf)
        assert "classify_tasks" in completed
        assert "estimate_budget" in completed
        assert "choose_strategy" in completed
        assert "prepare_all_instructions" in completed
        assert "checkpoint_before_delegate" in completed
        assert "spawn_agents" in completed
        assert "collect_and_verify" in completed
        assert wf.is_completed()

    def test_delegate_all_sets_strategy(self):
        wf = load_workflow({
            "task_count": 5,
            "heavy_count": 5,
            "medium_count": 0,
            "light_count": 0,
            "remaining_budget": 3000,
        })
        data = get_task_data(wf, "choose_strategy")
        assert data.get("strategy") == "delegate_all"
        assert get_task_data(wf, "prepare_all_instructions").get("instructions_prepared") is True
        assert get_task_data(wf, "checkpoint_before_delegate").get("checkpoint_saved") is True
        assert get_task_data(wf, "spawn_agents").get("agents_spawned") is True
        assert get_task_data(wf, "collect_and_verify").get("results_verified") is True

    def test_delegate_all_skips_light_execution(self):
        wf = load_workflow({
            "task_count": 3,
            "heavy_count": 3,
            "medium_count": 0,
            "light_count": 0,
            "remaining_budget": 1000,
        })
        completed = completed_spec_names(wf)
        assert "execute_with_checkpoints" not in completed
        assert "execute_light_tasks" not in completed
        assert "execute_direct_fallback" not in completed
        assert "spawn_heavy_agents" not in completed


# ---------------------------------------------------------------------------
# PATH C: Split and Delegate
# ---------------------------------------------------------------------------

class TestSplitAndDelegate:
    """Mixed batch -> execute light inline, delegate heavy to agents."""

    def test_split_full_path(self):
        wf = load_workflow({
            "task_count": 6,
            "heavy_count": 3,
            "medium_count": 1,
            "light_count": 2,
            "remaining_budget": 2000,
        })
        completed = completed_spec_names(wf)
        assert "classify_tasks" in completed
        assert "estimate_budget" in completed
        assert "choose_strategy" in completed
        assert "execute_light_tasks" in completed
        assert "checkpoint_before_heavy" in completed
        assert "prepare_heavy_instructions" in completed
        assert "spawn_heavy_agents" in completed
        assert "collect_and_verify" in completed
        assert wf.is_completed()

    def test_split_sets_correct_flags(self):
        wf = load_workflow({
            "task_count": 4,
            "heavy_count": 2,
            "medium_count": 0,
            "light_count": 2,
            "remaining_budget": 1500,
        })
        data = get_task_data(wf, "choose_strategy")
        assert data.get("strategy") == "split_and_delegate"
        assert get_task_data(wf, "execute_light_tasks").get("light_tasks_executed") is True
        assert get_task_data(wf, "checkpoint_before_heavy").get("checkpoint_saved") is True
        assert get_task_data(wf, "prepare_heavy_instructions").get("instructions_prepared") is True
        assert get_task_data(wf, "spawn_heavy_agents").get("agents_spawned") is True
        assert get_task_data(wf, "collect_and_verify").get("results_verified") is True

    def test_split_skips_delegate_all_path(self):
        wf = load_workflow({
            "task_count": 4,
            "heavy_count": 2,
            "medium_count": 0,
            "light_count": 2,
            "remaining_budget": 1500,
        })
        completed = completed_spec_names(wf)
        assert "prepare_all_instructions" not in completed
        assert "checkpoint_before_delegate" not in completed
        assert "spawn_agents" not in completed
        assert "execute_with_checkpoints" not in completed


# ---------------------------------------------------------------------------
# PATH D: Direct Fallback (over budget but no heavy tasks)
# ---------------------------------------------------------------------------

class TestDirectFallback:
    """Over budget but no heavy tasks -> execute directly with aggressive checkpoints."""

    def test_fallback_path(self):
        wf = load_workflow({
            "task_count": 20,
            "heavy_count": 0,
            "medium_count": 15,
            "light_count": 5,
            "remaining_budget": 5000,
        })
        completed = completed_spec_names(wf)
        assert "classify_tasks" in completed
        assert "estimate_budget" in completed
        assert "choose_strategy" in completed
        assert "execute_direct_fallback" in completed
        assert wf.is_completed()
        data = get_task_data(wf, "execute_direct_fallback")
        assert data.get("execution_strategy") == "direct_aggressive_checkpoints"

    def test_fallback_skips_all_agent_paths(self):
        wf = load_workflow({
            "task_count": 10,
            "heavy_count": 0,
            "medium_count": 8,
            "light_count": 2,
            "remaining_budget": 3000,
        })
        completed = completed_spec_names(wf)
        assert "spawn_agents" not in completed
        assert "spawn_heavy_agents" not in completed
        assert "collect_and_verify" not in completed
        assert "execute_light_tasks" not in completed
        assert "execute_with_checkpoints" not in completed


# ---------------------------------------------------------------------------
# CROSS-CUTTING: Classification and Estimation
# ---------------------------------------------------------------------------

class TestAlwaysClassifiesAndEstimates:
    """All paths must classify tasks and estimate budget first."""

    def test_classify_on_direct(self):
        wf = load_workflow({"heavy_count": 0, "medium_count": 1, "light_count": 0, "remaining_budget": 50000})
        assert "classify_tasks" in completed_spec_names(wf)
        assert "estimate_budget" in completed_spec_names(wf)

    def test_classify_on_delegate(self):
        wf = load_workflow({"heavy_count": 5, "medium_count": 0, "light_count": 0, "remaining_budget": 1000})
        assert "classify_tasks" in completed_spec_names(wf)
        assert "estimate_budget" in completed_spec_names(wf)

    def test_classify_on_split(self):
        wf = load_workflow({"heavy_count": 2, "medium_count": 0, "light_count": 3, "remaining_budget": 1000})
        assert "classify_tasks" in completed_spec_names(wf)
        assert "estimate_budget" in completed_spec_names(wf)

    def test_classify_on_fallback(self):
        wf = load_workflow({"heavy_count": 0, "medium_count": 10, "light_count": 0, "remaining_budget": 2000})
        assert "classify_tasks" in completed_spec_names(wf)
        assert "estimate_budget" in completed_spec_names(wf)


# ---------------------------------------------------------------------------
# CROSS-CUTTING: Checkpoints
# ---------------------------------------------------------------------------

class TestCheckpointBehavior:
    """Checkpoints happen on delegation paths, progressive on direct."""

    def test_checkpoint_on_delegate_all(self):
        wf = load_workflow({"heavy_count": 5, "medium_count": 0, "light_count": 0, "remaining_budget": 1000})
        assert "checkpoint_before_delegate" in completed_spec_names(wf)
        data = get_task_data(wf, "checkpoint_before_delegate")
        assert data.get("checkpoint_saved") is True

    def test_checkpoint_on_split(self):
        wf = load_workflow({"heavy_count": 2, "medium_count": 0, "light_count": 3, "remaining_budget": 1000})
        assert "checkpoint_before_heavy" in completed_spec_names(wf)
        data = get_task_data(wf, "checkpoint_before_heavy")
        assert data.get("checkpoint_saved") is True

    def test_no_checkpoint_task_on_direct(self):
        wf = load_workflow({"heavy_count": 0, "medium_count": 1, "light_count": 0, "remaining_budget": 50000})
        completed = completed_spec_names(wf)
        assert "checkpoint_before_delegate" not in completed
        assert "checkpoint_before_heavy" not in completed

    def test_checkpoints_enabled_on_direct(self):
        wf = load_workflow({"heavy_count": 0, "medium_count": 1, "light_count": 0, "remaining_budget": 50000})
        data = get_task_data(wf, "execute_with_checkpoints")
        assert data.get("checkpoints_enabled") is True


# ---------------------------------------------------------------------------
# EDGE CASES
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_zero_tasks_within_budget(self):
        """Zero tasks = zero tokens = within budget."""
        wf = load_workflow({"heavy_count": 0, "medium_count": 0, "light_count": 0, "remaining_budget": 50000})
        data = get_task_data(wf, "estimate_budget")
        assert data.get("within_budget") is True
        assert data.get("estimated_tokens") == 0

    def test_defaults_when_no_data(self):
        """Process should handle missing initial data via try/except defaults."""
        wf = load_workflow()
        assert wf.is_completed()
        assert "classify_tasks" in completed_spec_names(wf)

    def test_very_low_remaining_budget(self):
        """Even 1 light task exceeds budget of 100 tokens (100 < 100*0.6 = 60 is False)."""
        wf = load_workflow({"heavy_count": 0, "medium_count": 0, "light_count": 1, "remaining_budget": 100})
        data = get_task_data(wf, "estimate_budget")
        assert data.get("within_budget") is False
        # No heavy tasks -> fallback path
        assert "execute_direct_fallback" in completed_spec_names(wf)

    def test_agent_instruction_preparation_on_both_delegation_paths(self):
        """Both delegate_all and split paths prepare instructions."""
        wf_all = load_workflow({"heavy_count": 5, "medium_count": 0, "light_count": 0, "remaining_budget": 1000})
        wf_split = load_workflow({"heavy_count": 2, "medium_count": 0, "light_count": 3, "remaining_budget": 1000})
        assert get_task_data(wf_all, "prepare_all_instructions").get("instructions_prepared") is True
        assert get_task_data(wf_split, "prepare_heavy_instructions").get("instructions_prepared") is True

    def test_results_verified_on_both_delegation_paths(self):
        """Both delegation paths verify results."""
        wf_all = load_workflow({"heavy_count": 5, "medium_count": 0, "light_count": 0, "remaining_budget": 1000})
        wf_split = load_workflow({"heavy_count": 2, "medium_count": 0, "light_count": 3, "remaining_budget": 1000})
        assert get_task_data(wf_all, "collect_and_verify").get("results_verified") is True
        assert get_task_data(wf_split, "collect_and_verify").get("results_verified") is True
