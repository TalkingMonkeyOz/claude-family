"""
Tests for the Project Lifecycle BPMN process.

Models the full lifecycle of a Claude Family project from creation through
phase advancement to retirement.

Paths tested:
  1. New project path: classify(new) → define → register → generate → docs → mcp → check → work → end_active
  2. Existing project path: classify(existing) → load → check(ok) → work → end_active
  3. Non-compliant fix: classify(existing) → load → check(fail) → fix → work → end_active
  4. Config change loop: work → config_change → update_db → regen → verify → work → end_active
  5. Phase advancement: work → phase_advance → assess → advance → work → end_active
  6. Retirement: work → retire → archive → end_archived

Key notes:
  - classify_project is a userTask that sets project_type
  - check_compliance is a scriptTask: sets compliance_ok (try/except pattern, default True)
  - Gateway flow_new_project: condition project_type == "new"
  - Gateway flow_not_compliant: condition compliance_ok == False
  - Action gateway conditions: action == "config_change", "phase_advance", "retire"; default → end_active
  - fix_compliance feeds back to work_merge (not re-check)

Implementation: /project-init skill, Config Management SOP, generate_project_settings.py
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "project_lifecycle.bpmn")
)
PROCESS_ID = "project_lifecycle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
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
    """Return all READY user tasks."""
    return wf.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(wf: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(wf)]


def complete_user_task(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """Find named READY user task, merge data, run it, advance engine."""
    ready = get_ready_user_tasks(wf)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    wf.do_engine_steps()


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: New Project Path
# ---------------------------------------------------------------------------

class TestNewProjectPath:
    """
    New project: classify(new) → define → register_in_db → generate_settings
    → create_governance_docs → register_mcp → check_compliance(ok) → do_work(continue) → end_active.
    """

    def test_new_project_full_setup(self):
        wf = load_workflow()

        # Classify as a new project
        complete_user_task(wf, "classify_project", {"project_type": "new"})

        # Should reach define_project (userTask on the new path)
        assert "define_project" in ready_task_names(wf), (
            f"Expected define_project READY after new classify. Got: {ready_task_names(wf)}"
        )

        # Define project: engine then runs register_in_db, generate_settings (scriptTasks)
        complete_user_task(wf, "define_project", {"project_name": "test-project"})

        # create_governance_docs is a userTask
        assert "create_governance_docs" in ready_task_names(wf)
        complete_user_task(wf, "create_governance_docs", {})

        # register_mcp is a scriptTask (auto-runs), compliance check is a scriptTask too
        # Next userTask is do_work
        assert "do_work" in ready_task_names(wf)
        complete_user_task(wf, "do_work", {"action": "continue"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # New-path steps
        assert "define_project" in names
        assert "register_in_db" in names
        assert "generate_settings" in names
        assert "create_governance_docs" in names
        assert "register_mcp" in names
        assert "check_compliance" in names
        assert "do_work" in names
        assert "end_active" in names

        # Existing-only step must not appear
        assert "load_project" not in names
        assert "end_archived" not in names

        # Script flags set by scriptTasks
        assert wf.data.get("registered") is True
        assert wf.data.get("settings_generated") is True
        assert wf.data.get("mcp_registered") is True


# ---------------------------------------------------------------------------
# Test 2: Existing Project Path (compliant)
# ---------------------------------------------------------------------------

class TestExistingProjectCompliant:
    """
    Existing project, compliance passes:
    classify(existing) → load_project → check_compliance(ok) → do_work(continue) → end_active.
    """

    def test_existing_project_compliant(self):
        wf = load_workflow()

        # Classify as existing (default gateway branch)
        complete_user_task(wf, "classify_project", {"project_type": "existing"})

        # load_project is a scriptTask (auto-runs after classify)
        # check_compliance is a scriptTask (auto-runs, compliance_ok defaults True)
        # Next userTask is do_work
        assert "do_work" in ready_task_names(wf)
        complete_user_task(wf, "do_work", {"action": "continue"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "load_project" in names
        assert "check_compliance" in names
        assert "do_work" in names
        assert "end_active" in names

        # New-project-only steps must not appear
        assert "define_project" not in names
        assert "register_in_db" not in names
        assert "create_governance_docs" not in names
        assert "fix_compliance" not in names


# ---------------------------------------------------------------------------
# Test 3: Non-Compliant Fix Path
# ---------------------------------------------------------------------------

class TestNonCompliantFix:
    """
    Existing project, compliance fails:
    classify(existing) → load_project → check_compliance(fail) → fix_compliance
    → do_work(continue) → end_active.

    The compliance_ok value must be injected via initial_data because check_compliance
    is a scriptTask that uses try/except: if compliance_ok is None → True.
    We set compliance_ok=False upfront via initial_data.
    """

    def test_non_compliant_then_fixed(self):
        wf = load_workflow(initial_data={"compliance_ok": False})

        # Classify existing → load_project (script) → check_compliance (script, reads compliance_ok=False)
        # → fix_compliance (userTask, non-compliant branch)
        complete_user_task(wf, "classify_project", {"project_type": "existing"})

        assert "fix_compliance" in ready_task_names(wf), (
            f"Expected fix_compliance when compliance_ok=False. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "fix_compliance", {})

        # After fix, merges to work phase
        assert "do_work" in ready_task_names(wf)
        complete_user_task(wf, "do_work", {"action": "continue"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fix_compliance" in names
        assert "do_work" in names
        assert "end_active" in names
        assert "end_archived" not in names


# ---------------------------------------------------------------------------
# Test 4: Config Change Loop
# ---------------------------------------------------------------------------

class TestConfigChangeLoop:
    """
    Work phase → config change → update_config_db → regenerate_files → verify_config
    → back to do_work → continue → end_active.
    """

    def test_config_change_then_continue(self):
        wf = load_workflow()

        complete_user_task(wf, "classify_project", {"project_type": "existing"})
        assert "do_work" in ready_task_names(wf)

        # First pass: trigger config change
        complete_user_task(wf, "do_work", {"action": "config_change"})

        # update_config_db, regenerate_files, verify_config are all scriptTasks
        # Engine should loop back to do_work
        assert not wf.is_completed(), "Workflow must not be completed mid-config-change loop"
        assert "do_work" in ready_task_names(wf), (
            f"Expected do_work after config loop. Got: {ready_task_names(wf)}"
        )

        # Second pass: continue working
        complete_user_task(wf, "do_work", {"action": "continue"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "update_config_db" in names
        assert "regenerate_files" in names
        assert "verify_config" in names
        assert "end_active" in names
        assert "end_archived" not in names

        assert wf.data.get("config_updated") is True
        assert wf.data.get("files_regenerated") is True
        assert wf.data.get("config_verified") is True


# ---------------------------------------------------------------------------
# Test 5: Phase Advancement
# ---------------------------------------------------------------------------

class TestPhaseAdvancement:
    """
    Work phase → phase_advance → assess_phase (userTask) → advance_phase (script)
    → back to do_work → continue → end_active.
    """

    def test_phase_advance_then_continue(self):
        wf = load_workflow()

        complete_user_task(wf, "classify_project", {"project_type": "existing"})
        assert "do_work" in ready_task_names(wf)

        # Trigger phase advancement
        complete_user_task(wf, "do_work", {"action": "phase_advance"})

        # assess_phase is a userTask
        assert "assess_phase" in ready_task_names(wf), (
            f"Expected assess_phase after phase_advance. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "assess_phase", {"phase_ready": True})

        # advance_phase is a scriptTask → loops back to do_work
        assert "do_work" in ready_task_names(wf)
        complete_user_task(wf, "do_work", {"action": "continue"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "assess_phase" in names
        assert "advance_phase" in names
        assert "end_active" in names
        assert "end_archived" not in names

        assert wf.data.get("phase_advanced") is True


# ---------------------------------------------------------------------------
# Test 6: Retirement
# ---------------------------------------------------------------------------

class TestRetirement:
    """
    Work phase → retire → archive_project (script) → end_archived.
    """

    def test_project_retirement(self):
        wf = load_workflow()

        complete_user_task(wf, "classify_project", {"project_type": "existing"})
        assert "do_work" in ready_task_names(wf)

        # Trigger retirement
        complete_user_task(wf, "do_work", {"action": "retire"})

        # archive_project is a scriptTask → end_archived
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "archive_project" in names
        assert "end_archived" in names
        assert "end_active" not in names

        assert wf.data.get("project_archived") is True


# ---------------------------------------------------------------------------
# Test 7: Multiple Work Actions Before Retire
# ---------------------------------------------------------------------------

class TestMultipleActionsBeforeRetire:
    """
    Config change loop + phase advance before final retirement.
    Exercises the fact that do_work is the hub of the work phase.
    """

    def test_config_then_phase_then_retire(self):
        wf = load_workflow()

        complete_user_task(wf, "classify_project", {"project_type": "existing"})

        # Config change
        complete_user_task(wf, "do_work", {"action": "config_change"})
        assert "do_work" in ready_task_names(wf)

        # Phase advancement
        complete_user_task(wf, "do_work", {"action": "phase_advance"})
        complete_user_task(wf, "assess_phase", {})
        assert "do_work" in ready_task_names(wf)

        # Retire
        complete_user_task(wf, "do_work", {"action": "retire"})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "update_config_db" in names
        assert "advance_phase" in names
        assert "archive_project" in names
        assert "end_archived" in names
