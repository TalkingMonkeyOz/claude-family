"""
Tests for the Feature Workflow BPMN process.

Uses SpiffWorkflow 3.x API directly against the feature_workflow.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Flow summary:
  start → create_feature → set_draft → plan_feature → set_planned
       → complexity_gateway
           [complexity=="high"] → spawn_agents → implementation_merge
           [default]            → implement_directly → implementation_merge
       → run_tests
       → tests_pass_gateway
           [tests_passed==True] → review_code → review_result_gateway
               [review=="changes_requested"] → fix_issues_review → run_tests (loop)
               [default/approved]            → set_completed → end_completed
           [default/fail]       → fix_issues → run_tests (loop)
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "feature_workflow.bpmn")
)
PROCESS_ID = "feature_workflow"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past the start event and any initial automated steps
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() so the engine advances through any subsequent automated
    tasks (script tasks, gateways) until the next user task or end event.

    Raises AssertionError if the task is not currently READY.
    """
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected user task '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return the spec names of all COMPLETED tasks in the workflow."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSimpleFeatureHappyPath:
    """
    Simple (default) path: create → plan → implement_directly → run_tests
    (tests pass) → review_code (approved) → set_completed → end_completed.

    Verifies: status == "completed", implement_directly completed,
              spawn_agents NOT completed.
    """

    def test_simple_feature_happy_path(self):
        workflow = load_workflow()

        # --- Create Feature ------------------------------------------------
        complete_user_task(workflow, "create_feature", {})

        # --- Plan Feature --------------------------------------------------
        # complexity is not "high", so complexity_gateway takes the default
        # (flow_simple) branch to implement_directly.
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})

        # --- Implement Directly --------------------------------------------
        complete_user_task(workflow, "implement_directly", {})

        # --- Run Tests (pass) ----------------------------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # --- Review Code (approved) -----------------------------------------
        complete_user_task(workflow, "review_code", {"review": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "set_draft" in names, "set_draft script must have run"
        assert "set_planned" in names, "set_planned script must have run"
        assert "implement_directly" in names, "implement_directly must have been completed"
        assert "spawn_agents" not in names, "spawn_agents must NOT be executed on simple path"
        assert "set_completed" in names, "set_completed script must have run"
        assert "end_completed" in names, "end_completed end event must be reached"

        assert workflow.data.get("status") == "completed", (
            "set_completed should have set status='completed'"
        )


class TestHighComplexityFeature:
    """
    High-complexity path: complexity == "high" routes through spawn_agents
    instead of implement_directly.

    Verifies: spawn_agents completed, implement_directly NOT completed.
    """

    def test_high_complexity_feature(self):
        workflow = load_workflow()

        # --- Create Feature ------------------------------------------------
        complete_user_task(workflow, "create_feature", {})

        # --- Plan Feature (high complexity) --------------------------------
        complete_user_task(workflow, "plan_feature", {"complexity": "high"})

        # --- Spawn Agents --------------------------------------------------
        complete_user_task(workflow, "spawn_agents", {})

        # --- Run Tests (pass) ----------------------------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # --- Review Code (approved) -----------------------------------------
        complete_user_task(workflow, "review_code", {"review": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "spawn_agents" in names, "spawn_agents must have been completed on high-complexity path"
        assert "implement_directly" not in names, (
            "implement_directly must NOT be executed on high-complexity path"
        )
        assert "set_completed" in names, "set_completed script must have run"
        assert "end_completed" in names, "end_completed end event must be reached"

        assert workflow.data.get("status") == "completed", (
            "Final status should be 'completed'"
        )


class TestTestFailRetry:
    """
    Tests fail on first attempt → fix_issues → run_tests again (pass)
    → review_code (approved) → end_completed.

    Verifies: fix_issues completed, final status == "completed".
    """

    def test_test_fail_retry(self):
        workflow = load_workflow()

        # --- Create Feature ------------------------------------------------
        complete_user_task(workflow, "create_feature", {})

        # --- Plan Feature (simple) -----------------------------------------
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})

        # --- Implement Directly --------------------------------------------
        complete_user_task(workflow, "implement_directly", {})

        # --- Run Tests: FAIL (default branch, tests_passed not True) --------
        # Do NOT set tests_passed=True so the default (fail) branch fires.
        complete_user_task(workflow, "run_tests", {"tests_passed": False})

        # Engine should stop at fix_issues (user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "fix_issues" in ready_names, (
            f"fix_issues should be READY after test failure, got: {ready_names}"
        )

        # --- Fix Issues ----------------------------------------------------
        complete_user_task(workflow, "fix_issues", {})

        # Should loop back to run_tests
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "run_tests" in ready_names, (
            f"run_tests should be READY after fix_issues, got: {ready_names}"
        )

        # --- Run Tests: PASS -----------------------------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # --- Review Code (approved) ----------------------------------------
        complete_user_task(workflow, "review_code", {"review": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after retry"

        names = completed_spec_names(workflow)
        assert "fix_issues" in names, "fix_issues must have been completed"
        assert "set_completed" in names, "set_completed script must have run"
        assert "end_completed" in names, "end_completed must be reached"

        assert workflow.data.get("status") == "completed", (
            "Final status should be 'completed'"
        )


class TestReviewChangesRequested:
    """
    Review requests changes → fix_issues_review → run_tests (pass)
    → review_code (approved) → end_completed.

    Verifies: fix_issues_review completed, final status == "completed".
    """

    def test_review_changes_requested(self):
        workflow = load_workflow()

        # --- Create Feature ------------------------------------------------
        complete_user_task(workflow, "create_feature", {})

        # --- Plan Feature (simple) -----------------------------------------
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})

        # --- Implement Directly --------------------------------------------
        complete_user_task(workflow, "implement_directly", {})

        # --- Run Tests: PASS -----------------------------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # --- Review Code: changes requested --------------------------------
        complete_user_task(workflow, "review_code", {"review": "changes_requested"})

        # Engine should stop at fix_issues_review (user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "fix_issues_review" in ready_names, (
            f"fix_issues_review should be READY after changes_requested, got: {ready_names}"
        )

        # --- Fix Issues (Review) ------------------------------------------
        complete_user_task(workflow, "fix_issues_review", {})

        # Should loop back to run_tests
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "run_tests" in ready_names, (
            f"run_tests should be READY after fix_issues_review, got: {ready_names}"
        )

        # --- Run Tests: PASS -----------------------------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # --- Review Code: approved (default) --------------------------------
        # Override review to avoid triggering changes_requested again
        complete_user_task(workflow, "review_code", {"review": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after review fix"

        names = completed_spec_names(workflow)
        assert "fix_issues_review" in names, "fix_issues_review must have been completed"
        assert "set_completed" in names, "set_completed script must have run"
        assert "end_completed" in names, "end_completed must be reached"

        assert workflow.data.get("status") == "completed", (
            "Final status should be 'completed'"
        )
