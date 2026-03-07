"""
Tests for the Context Preservation Pipeline BPMN process.

Proactive context preservation with graduated urgency levels:
  - Green (>30%): No action needed
  - Yellow (20-30%): Advisory message injected
  - Orange (10-20%): Specific save directive injected
  - Red (<10%) + recent checkpoint: Red warning but tools allowed
  - Red (<10%) + no checkpoint: Tools blocked until checkpoint saved
  - Stale/missing data: Fallback to prompt count heuristic

Sensor: StatusLine script writes context_health.json
Directive: RAG hook reads health file, injects graduated messages
Enforcement: Task discipline hook blocks at Red without recent checkpoint

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks
  - task.data is a dict; set values via load_workflow(initial_data={...})
  - Gateway conditions are Python expressions eval'd against task.data
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "context_preservation.bpmn")
)
PROCESS_ID = "context_preservation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow instance with optional initial data."""
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
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Green Level - No Action
# ---------------------------------------------------------------------------

class TestGreenLevel:
    """
    Context is healthy (>30% remaining). No action needed.
    """

    def test_green_fresh_data_no_action(self):
        """Fresh data with >30% remaining → green → end_no_action."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 50},
            "data_age_seconds": 30,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "read_context_health" in names
        assert "use_statusline_data" in names
        assert "compute_level" in names
        assert "end_no_action" in names

        # Should NOT take any action paths
        assert "inject_advisory" not in names
        assert "inject_directive" not in names
        assert "check_recent_checkpoint" not in names

        assert wf.data.get("level") == "green"
        assert wf.data.get("used_fallback") is False

    def test_green_fallback_low_interaction(self):
        """Stale data + low interaction count → fallback → green."""
        wf = load_workflow(initial_data={
            "health_data": {},
            "data_age_seconds": 300,
            "interaction_count": 10,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fallback_heuristic" in names
        assert "end_no_action" in names
        assert wf.data.get("level") == "green"
        assert wf.data.get("used_fallback") is True


# ---------------------------------------------------------------------------
# Test 2: Yellow Level - Advisory
# ---------------------------------------------------------------------------

class TestYellowLevel:
    """
    Context is getting low (20-30%). Advisory injected.
    """

    def test_yellow_advisory_injected(self):
        """remaining_pct=25 → yellow → inject_advisory → end_advisory."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 25},
            "data_age_seconds": 10,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "inject_advisory" in names
        assert "end_advisory" in names
        assert wf.data.get("level") == "yellow"
        assert wf.data.get("action_taken") == "advisory"

    def test_yellow_boundary_30(self):
        """remaining_pct=30 → yellow (30 is not > 30)."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 30},
            "data_age_seconds": 5,
        })

        assert wf.is_completed()
        assert wf.data.get("level") == "yellow"

    def test_yellow_fallback_40_interactions(self):
        """Stale data + 40 interactions → fallback remaining_pct=25 → yellow."""
        wf = load_workflow(initial_data={
            "health_data": {},
            "data_age_seconds": 300,
            "interaction_count": 40,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fallback_heuristic" in names
        assert "inject_advisory" in names
        assert wf.data.get("level") == "yellow"
        assert wf.data.get("used_fallback") is True


# ---------------------------------------------------------------------------
# Test 3: Orange Level - Save Directive
# ---------------------------------------------------------------------------

class TestOrangeLevel:
    """
    Context is low (10-20%). Specific save directive injected.
    """

    def test_orange_directive_injected(self):
        """remaining_pct=15 → orange → inject_directive → end_directive."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 15},
            "data_age_seconds": 10,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "inject_directive" in names
        assert "end_directive" in names
        assert wf.data.get("level") == "orange"
        assert wf.data.get("action_taken") == "directive"

    def test_orange_boundary_20(self):
        """remaining_pct=20 → orange (20 is not > 20)."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 20},
            "data_age_seconds": 5,
        })

        assert wf.is_completed()
        assert wf.data.get("level") == "orange"

    def test_orange_fallback_55_interactions(self):
        """Stale data + 55 interactions → fallback remaining_pct=15 → orange."""
        wf = load_workflow(initial_data={
            "health_data": {},
            "data_age_seconds": 300,
            "interaction_count": 55,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fallback_heuristic" in names
        assert "inject_directive" in names
        assert wf.data.get("level") == "orange"


# ---------------------------------------------------------------------------
# Test 4: Red Level + Recent Checkpoint - Warning Only
# ---------------------------------------------------------------------------

class TestRedWithCheckpoint:
    """
    Context critical (<10%) but checkpoint was saved recently.
    Warning injected but tools NOT blocked.
    """

    def test_red_with_checkpoint_warns_but_allows(self):
        """remaining_pct=5 + checkpoint_recent=True → red_warning, not blocked."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 5},
            "data_age_seconds": 10,
            "checkpoint_recent": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "check_recent_checkpoint" in names
        assert "inject_red_advisory" in names
        assert "end_red_ok" in names
        assert wf.data.get("level") == "red"
        assert wf.data.get("action_taken") == "red_warning"
        assert wf.data.get("tools_blocked") is False

    def test_red_does_not_block_when_checkpoint_fresh(self):
        """block_and_inject should NOT be reached when checkpoint is recent."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 3},
            "data_age_seconds": 10,
            "checkpoint_recent": True,
        })

        names = completed_spec_names(wf)
        assert "block_and_inject" not in names


# ---------------------------------------------------------------------------
# Test 5: Red Level + No Checkpoint - Tools Blocked
# ---------------------------------------------------------------------------

class TestRedWithoutCheckpoint:
    """
    Context critical (<10%) and no recent checkpoint.
    Gated tools blocked until checkpoint saved.
    """

    def test_red_no_checkpoint_blocks_tools(self):
        """remaining_pct=5 + checkpoint_recent=False → tools blocked."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 5},
            "data_age_seconds": 10,
            "checkpoint_recent": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "check_recent_checkpoint" in names
        assert "block_and_inject" in names
        assert "end_blocked" in names
        assert wf.data.get("level") == "red"
        assert wf.data.get("action_taken") == "blocked"
        assert wf.data.get("tools_blocked") is True

    def test_red_default_no_checkpoint(self):
        """No checkpoint_recent set → defaults to False → blocked."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 8},
            "data_age_seconds": 10,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "block_and_inject" in names
        assert wf.data.get("tools_blocked") is True

    def test_red_boundary_10(self):
        """remaining_pct=10 → red (10 is not > 10)."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 10},
            "data_age_seconds": 5,
        })

        assert wf.is_completed()
        assert wf.data.get("level") == "red"

    def test_red_fallback_70_interactions(self):
        """Stale data + 70 interactions → fallback remaining_pct=5 → red → blocked."""
        wf = load_workflow(initial_data={
            "health_data": {},
            "data_age_seconds": 300,
            "interaction_count": 70,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fallback_heuristic" in names
        assert "block_and_inject" in names
        assert wf.data.get("level") == "red"
        assert wf.data.get("tools_blocked") is True


# ---------------------------------------------------------------------------
# Test 6: Stale Data Fallback
# ---------------------------------------------------------------------------

class TestStaleFallback:
    """
    StatusLine data is stale (>120s) or missing.
    Falls back to prompt count heuristic.
    """

    def test_stale_data_uses_fallback(self):
        """data_age_seconds=300 → stale → fallback_heuristic."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 50},
            "data_age_seconds": 300,
            "interaction_count": 10,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fallback_heuristic" in names
        assert "use_statusline_data" not in names
        assert wf.data.get("used_fallback") is True

    def test_fresh_data_uses_statusline(self):
        """data_age_seconds=30 → fresh → use_statusline_data."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 50},
            "data_age_seconds": 30,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "use_statusline_data" in names
        assert "fallback_heuristic" not in names
        assert wf.data.get("used_fallback") is False

    def test_boundary_120_stale(self):
        """data_age_seconds=120 → stale (120 is not < 120)."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 50},
            "data_age_seconds": 120,
            "interaction_count": 10,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "fallback_heuristic" in names

    def test_boundary_119_fresh(self):
        """data_age_seconds=119 → fresh (119 < 120)."""
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 50},
            "data_age_seconds": 119,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "use_statusline_data" in names


# ---------------------------------------------------------------------------
# Test 7: No Data File
# ---------------------------------------------------------------------------

class TestNoDataFile:
    """
    No context_health.json exists (StatusLine not configured).
    Falls back to prompt count heuristic.
    """

    def test_no_health_data_defaults_to_fallback(self):
        """health_data=None, data_age_seconds=999 → stale → fallback."""
        wf = load_workflow(initial_data={
            "interaction_count": 20,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fallback_heuristic" in names
        assert wf.data.get("used_fallback") is True
        # 20 interactions = remaining_pct=50 = green
        assert wf.data.get("level") == "green"

    def test_no_data_high_interactions_triggers_red(self):
        """No health file + 70+ interactions → red."""
        wf = load_workflow(initial_data={
            "interaction_count": 75,
        })

        assert wf.is_completed()
        assert wf.data.get("level") == "red"


# ---------------------------------------------------------------------------
# Test 8: Workflow Completion
# ---------------------------------------------------------------------------

class TestWorkflowCompletion:
    """All paths should result in workflow completion."""

    def test_green_completes(self):
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 50},
            "data_age_seconds": 10,
        })
        assert wf.is_completed()

    def test_yellow_completes(self):
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 25},
            "data_age_seconds": 10,
        })
        assert wf.is_completed()

    def test_orange_completes(self):
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 15},
            "data_age_seconds": 10,
        })
        assert wf.is_completed()

    def test_red_blocked_completes(self):
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 5},
            "data_age_seconds": 10,
            "checkpoint_recent": False,
        })
        assert wf.is_completed()

    def test_red_ok_completes(self):
        wf = load_workflow(initial_data={
            "health_data": {"remaining_pct": 5},
            "data_age_seconds": 10,
            "checkpoint_recent": True,
        })
        assert wf.is_completed()

    def test_fallback_green_completes(self):
        wf = load_workflow(initial_data={
            "data_age_seconds": 999,
            "interaction_count": 5,
        })
        assert wf.is_completed()

    def test_fallback_red_completes(self):
        wf = load_workflow(initial_data={
            "data_age_seconds": 999,
            "interaction_count": 80,
        })
        assert wf.is_completed()
