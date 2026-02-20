"""
Tests for the L0 Claude Family Capability Map BPMN process.

Tests the top-level collaboration diagram with 6 call activities
that delegate to L1 subprocess stubs. Validates:
  - Parser resolves all 6 call activities to L1 subprocess specs
  - Full execution walks through all 6 capabilities in sequence
  - Each call activity invokes its L1 subprocess correctly
  - Non-executable participant processes are rejected (by design)

Key API notes (SpiffWorkflow 3.1.x):
  - Call activities require subprocess specs passed to BpmnWorkflow constructor
  - parser.get_subprocess_specs(process_id) resolves calledElement references
  - Non-executable processes (isExecutable=false) cannot be instantiated
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute paths to BPMN files
ARCH_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "architecture")
)
L0_FILE = os.path.join(ARCH_DIR, "L0_claude_family.bpmn")
L1_STUBS = os.path.join(ARCH_DIR, "L1_stubs.bpmn")

PROCESS_ID = "claude_process"

# The 6 capabilities in sequence order
CAPABILITIES = [
    ("cap_session", "L1_session_management", "sm_placeholder"),
    ("cap_work_tracking", "L1_work_tracking", "wt_placeholder"),
    ("cap_knowledge", "L1_knowledge_management", "km_l1_placeholder"),
    ("cap_enforcement", "L1_enforcement", "ef_placeholder"),
    ("cap_agents", "L1_agent_orchestration", "ao_placeholder"),
    ("cap_config", "L1_config_management", "cm_placeholder"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse L0 + L1 stubs and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(L1_STUBS)
    parser.add_bpmn_file(L0_FILE)
    spec = parser.get_spec(PROCESS_ID)
    subspecs = parser.get_subprocess_specs(PROCESS_ID)
    wf = BpmnWorkflow(spec, subspecs)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """Find and complete a named READY user task."""
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
    """Return the spec names of all COMPLETED tasks."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestL0SubprocessResolution:
    """
    Verify that the parser resolves all 6 call activities to L1 subprocess specs.
    """

    def test_all_six_subprocess_specs_resolved(self):
        parser = BpmnParser()
        parser.add_bpmn_file(L1_STUBS)
        parser.add_bpmn_file(L0_FILE)

        subspecs = parser.get_subprocess_specs(PROCESS_ID)
        expected_ids = {cap[1] for cap in CAPABILITIES}
        assert set(subspecs.keys()) == expected_ids, (
            f"Expected subprocess specs: {expected_ids}, got: {set(subspecs.keys())}"
        )

    def test_non_executable_processes_rejected(self):
        """Participant pools (human, database, etc.) are non-executable by design."""
        parser = BpmnParser()
        parser.add_bpmn_file(L0_FILE)

        import pytest
        for pid in ["human_process", "database_process", "hooks_process",
                     "knowledge_process", "agents_process"]:
            with pytest.raises(Exception):
                parser.get_spec(pid)


class TestL0FullSequence:
    """
    Walk through all 6 capabilities in sequence: session → work tracking
    → knowledge → enforcement → agents → config → complete.
    """

    def test_full_capability_sequence(self):
        workflow = load_workflow()

        # Each capability's call activity surfaces its L1 stub's user task
        for call_activity, l1_process, stub_task in CAPABILITIES:
            ready = get_ready_user_tasks(workflow)
            assert len(ready) == 1, (
                f"Expected exactly 1 ready task for {call_activity}, "
                f"got: {[t.task_spec.name for t in ready]}"
            )
            assert ready[0].task_spec.name == stub_task, (
                f"Expected stub task '{stub_task}' but got '{ready[0].task_spec.name}'"
            )
            complete_user_task(workflow, stub_task)

        assert workflow.is_completed(), "Workflow should be completed after all 6 capabilities"

    def test_completed_steps_include_all_call_activities(self):
        workflow = load_workflow()

        # Complete all stubs
        for _, _, stub_task in CAPABILITIES:
            complete_user_task(workflow, stub_task)

        names = completed_spec_names(workflow)

        # All 6 call activity names should appear in completed steps
        for call_activity, _, _ in CAPABILITIES:
            assert call_activity in names, (
                f"Call activity '{call_activity}' should be in completed steps"
            )

        # Start and end events
        assert "claude_start" in names
        assert "claude_end" in names


class TestL0PartialExecution:
    """
    Test that workflow stops at the correct capability when not all are completed.
    """

    def test_stops_at_second_capability(self):
        workflow = load_workflow()

        # Complete only the first capability (session management)
        complete_user_task(workflow, "sm_placeholder")

        assert not workflow.is_completed(), "Should not be complete after 1 of 6"

        ready = get_ready_user_tasks(workflow)
        assert len(ready) == 1
        assert ready[0].task_spec.name == "wt_placeholder", (
            "Second capability should be work tracking"
        )

    def test_stops_at_fourth_capability(self):
        workflow = load_workflow()

        # Complete first 3 capabilities
        for _, _, stub_task in CAPABILITIES[:3]:
            complete_user_task(workflow, stub_task)

        assert not workflow.is_completed(), "Should not be complete after 3 of 6"

        ready = get_ready_user_tasks(workflow)
        assert ready[0].task_spec.name == "ef_placeholder", (
            "Fourth capability should be enforcement"
        )
