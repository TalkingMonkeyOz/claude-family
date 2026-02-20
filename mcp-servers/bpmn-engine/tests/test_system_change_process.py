"""
Tests for the System Change Process BPMN.

Validates the BPMN-first enforcement meta-process:
  1. Identify change -> search existing models -> decide modeled/not
  2. Update or create BPMN model -> test -> fix loop if tests fail
  3. Implement code -> validate alignment -> fix loop if misaligned
  4. Commit model + code together

This process governs how Claude modifies its own systems.
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "development", "system_change_process.bpmn")
)
PROCESS_ID = "system_change_process"


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    wf.do_engine_steps()
    return wf


def complete_user_task(workflow, task_name, data=None):
    """Complete a named user task with optional data."""
    tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
    target = [t for t in tasks if t.task_spec.name == task_name]
    assert target, f"No READY manual task named '{task_name}'. Ready: {[t.task_spec.name for t in tasks]}"
    task = target[0]
    if data:
        task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_names(workflow):
    """Return set of completed task spec names."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


class TestUpdateExistingModel:
    """System already modeled: update model -> test passes -> implement -> aligned -> commit."""

    def test_update_existing_model(self):
        wf = load_workflow()

        # Phase 1: Identify and search
        complete_user_task(wf, "identify_change", {
            "system_name": "task_discipline_hook",
            "is_modeled": True,
            "model_tests_passed": True,
            "alignment_valid": True,
        })
        # search_existing_model runs as script
        complete_user_task(wf, "review_search_results")

        # Phase 2: Already modeled path
        complete_user_task(wf, "analyze_model_gap")
        complete_user_task(wf, "update_bpmn_model")

        # Phase 3: Test model
        complete_user_task(wf, "write_model_tests")
        # run_model_tests runs as script

        # Phase 4: Implement
        complete_user_task(wf, "implement_code")
        # validate_alignment runs as script

        # Phase 6: Commit
        complete_user_task(wf, "commit_together")

        names = completed_names(wf)
        assert "analyze_model_gap" in names
        assert "update_bpmn_model" in names
        assert "create_bpmn_model" not in names
        assert wf.is_completed()


class TestCreateNewModel:
    """System not modeled: create new model -> test -> implement -> commit."""

    def test_create_new_model(self):
        wf = load_workflow()

        # Phase 1: Identify and search
        complete_user_task(wf, "identify_change", {
            "system_name": "new_mcp_server",
            "is_modeled": False,
            "model_tests_passed": True,
            "alignment_valid": True,
        })
        complete_user_task(wf, "review_search_results")

        # Phase 2: Not modeled - create new
        complete_user_task(wf, "create_bpmn_model")

        # Phase 3: Test
        complete_user_task(wf, "write_model_tests")

        # Phase 4: Implement
        complete_user_task(wf, "implement_code")

        # Phase 6: Commit
        complete_user_task(wf, "commit_together")

        names = completed_names(wf)
        assert "create_bpmn_model" in names
        assert "analyze_model_gap" not in names
        assert wf.is_completed()


class TestModelTestFailRetry:
    """Model tests fail -> loop back to fix model -> re-test -> pass -> continue."""

    def test_model_test_fail_retry(self):
        wf = load_workflow()

        # Phase 1
        complete_user_task(wf, "identify_change", {
            "system_name": "hook_chain",
            "is_modeled": True,
            "model_tests_passed": False,  # Will fail first time
            "alignment_valid": True,
        })
        complete_user_task(wf, "review_search_results")

        # Phase 2: Update model
        complete_user_task(wf, "analyze_model_gap")
        complete_user_task(wf, "update_bpmn_model")

        # Phase 3: Tests fail -> loops back to update_bpmn_model
        complete_user_task(wf, "write_model_tests")

        # Now fix: update model again with passing tests
        complete_user_task(wf, "update_bpmn_model", {"model_tests_passed": True})
        complete_user_task(wf, "write_model_tests")

        # Phase 4: Implement
        complete_user_task(wf, "implement_code")

        # Phase 6: Commit
        complete_user_task(wf, "commit_together")

        assert wf.is_completed()


class TestAlignmentFailRetry:
    """Code implemented but model/code misaligned -> fix -> re-validate -> commit."""

    def test_alignment_fail_retry(self):
        wf = load_workflow()

        # Phase 1-3: Standard flow
        complete_user_task(wf, "identify_change", {
            "system_name": "rag_pipeline",
            "is_modeled": True,
            "model_tests_passed": True,
            "alignment_valid": False,  # Will fail first time
        })
        complete_user_task(wf, "review_search_results")
        complete_user_task(wf, "analyze_model_gap")
        complete_user_task(wf, "update_bpmn_model")
        complete_user_task(wf, "write_model_tests")

        # Phase 4: Implement
        complete_user_task(wf, "implement_code")
        # validate_alignment runs - alignment_valid is False -> misaligned

        # Fix alignment and re-validate
        complete_user_task(wf, "fix_alignment", {"alignment_valid": True})
        # validate_alignment runs again - now aligned

        # Phase 6: Commit
        complete_user_task(wf, "commit_together")

        names = completed_names(wf)
        assert "fix_alignment" in names
        assert wf.is_completed()
