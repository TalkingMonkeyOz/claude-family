"""
Tests for the Feature Workflow BPMN process (v3 - build tasks, per-task loop, enforcement notes).

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

Flow summary (v3):
  start → create_feature → set_draft → plan_feature → set_planned
       → create_build_tasks [CLAUDE] → set_in_progress [DB]
       → complexity_gateway
           [complexity=="high"] → spawn_agents → implementation_merge
           [default/simple]     → implement_directly
               → next_task_gw → start_task [MCP] → implement_task [CLAUDE]
               → complete_task [MCP] → next_task_gw (loop)
               → [no more tasks] → implementation_merge
       → run_tests [SHOULD BE ENFORCED]
       → tests_pass_gateway
           [tests_passed==True] → review_code [SHOULD BE ENFORCED]
               → review_result_gateway
                   [review=="changes_requested"] → fix_issues_review → run_tests (loop)
                   [default/approved]            → set_completed → end_completed
           [default/fail]       → fix_issues → run_tests (loop)

Changes from v2:
  - create_build_tasks userTask added before complexity_gateway
  - set_in_progress scriptTask added after create_build_tasks
  - Per-task loop: next_task_gw → start_task → implement_task → complete_task → loop
  - implement_directly now leads into the per-task loop (not directly to implementation_merge)
  - plan_feature has plan_data JSONB documentation
  - run_tests and review_code have enforcement notes in documentation
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


def run_simple_feature_to_implementation(workflow: BpmnWorkflow) -> None:
    """Helper: navigate from start through to implement_directly for simple features."""
    complete_user_task(workflow, "create_feature", {})
    complete_user_task(workflow, "plan_feature", {"complexity": "simple"})
    # set_planned auto-runs, then create_build_tasks is the next userTask
    complete_user_task(workflow, "create_build_tasks", {})
    # set_in_progress auto-runs, then complexity_gateway → implement_directly
    complete_user_task(workflow, "implement_directly", {})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSimpleFeatureHappyPath:
    """
    Simple (default) path: create → plan → create_build_tasks → implement_directly
    → per-task loop → run_tests (pass) → review_code (approved)
    → set_completed → end_completed.
    """

    def test_simple_feature_happy_path_setup_steps(self):
        """Verify create_build_tasks and set_in_progress appear before complexity_gateway."""
        workflow = load_workflow()

        # --- Create Feature ------------------------------------------------
        complete_user_task(workflow, "create_feature", {})

        # --- Plan Feature --------------------------------------------------
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})

        # set_planned auto-runs, stops at create_build_tasks
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "create_build_tasks" in ready_names, (
            f"create_build_tasks should be READY after set_planned, got: {ready_names}"
        )

        # --- Create Build Tasks --------------------------------------------
        complete_user_task(workflow, "create_build_tasks", {})

        # set_in_progress auto-runs, complexity_gateway fires → implement_directly
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "implement_directly" in ready_names, (
            f"implement_directly should be READY after set_in_progress, got: {ready_names}"
        )

        # Verify set_in_progress ran (scriptTask auto-completes, data set by real implementation)
        names = completed_spec_names(workflow)
        assert "set_in_progress" in names, "set_in_progress must run after create_build_tasks"

    def test_simple_feature_no_tasks_in_loop(self):
        """
        Simple path with no tasks in the per-task loop (has_next_task=False immediately).
        This exercises the full path without an infinite loop risk.
        """
        workflow = load_workflow()

        complete_user_task(workflow, "create_feature", {})
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})
        complete_user_task(workflow, "create_build_tasks", {})

        # implement_directly enters loop with has_next_task=False immediately
        # next_task_gw default → implementation_merge → run_tests
        complete_user_task(workflow, "implement_directly", {"has_next_task": False})

        # next_task_gw should fire the default (flow_no_next_task) → run_tests
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "run_tests" in ready_names, (
            f"run_tests should be READY when no tasks in loop, got: {ready_names}"
        )

        complete_user_task(workflow, "run_tests", {"tests_passed": True})
        complete_user_task(workflow, "review_code", {"review": "approved"})

        assert workflow.is_completed(), "Workflow should be completed"
        names = completed_spec_names(workflow)
        assert "set_draft" in names, "set_draft script must have run"
        assert "set_planned" in names, "set_planned script must have run"
        assert "create_build_tasks" in names, "create_build_tasks must have been completed"
        assert "set_in_progress" in names, "set_in_progress must have run"
        assert "implement_directly" in names, "implement_directly must have been completed"
        assert "implement_task" not in names, "implement_task must NOT run when no tasks in loop"
        assert "spawn_agents" not in names, "spawn_agents must NOT be executed on simple path"
        assert "set_completed" in names, "set_completed script must have run"
        assert "end_completed" in names, "end_completed end event must be reached"

        assert workflow.data.get("status") == "completed", (
            "set_completed should have set status='completed'"
        )

    def test_simple_feature_with_one_task_in_loop(self):
        """
        Simple path with a single task in the per-task loop.
        First call to next_task_gw: has_next_task=True → execute task.
        Second call (after complete_task): has_next_task=False → exit loop.
        """
        workflow = load_workflow()

        complete_user_task(workflow, "create_feature", {})
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})
        complete_user_task(workflow, "create_build_tasks", {})

        # Enter loop: first iteration has a task
        # implement_directly data has_next_task=True → start_task runs → implement_task ready
        complete_user_task(workflow, "implement_directly", {"has_next_task": True})

        # start_task auto-runs (scriptTask), stops at implement_task (userTask)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "implement_task" in ready_names, (
            f"implement_task should be READY after start_task, got: {ready_names}"
        )

        names = completed_spec_names(workflow)
        assert "start_task" in names, "start_task must auto-run after next_task_gw"

        # Complete the task: set has_next_task=False to exit loop on next iteration
        complete_user_task(workflow, "implement_task", {"has_next_task": False})

        # complete_task auto-runs, loops to next_task_gw, has_next_task=False → exit
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "run_tests" in ready_names, (
            f"run_tests should be READY after single-task loop exits, got: {ready_names}"
        )

        names = completed_spec_names(workflow)
        assert "complete_task" in names, "complete_task must run after implement_task"

        complete_user_task(workflow, "run_tests", {"tests_passed": True})
        complete_user_task(workflow, "review_code", {"review": "approved"})

        assert workflow.is_completed()
        names = completed_spec_names(workflow)
        assert "start_task" in names
        assert "complete_task" in names
        assert "set_completed" in names
        assert workflow.data.get("status") == "completed"


class TestHighComplexityFeature:
    """
    High-complexity path: create_build_tasks → set_in_progress → complexity=="high"
    → spawn_agents → implementation_merge (agents handle their own per-task loop).

    Verifies: spawn_agents completed, implement_directly NOT completed.
    """

    def test_high_complexity_feature(self):
        workflow = load_workflow()

        # --- Create Feature ------------------------------------------------
        complete_user_task(workflow, "create_feature", {})

        # --- Plan Feature (high complexity) --------------------------------
        complete_user_task(workflow, "plan_feature", {"complexity": "high"})

        # --- Create Build Tasks --------------------------------------------
        complete_user_task(workflow, "create_build_tasks", {})

        # --- Spawn Agents (high complexity path) ---------------------------
        complete_user_task(workflow, "spawn_agents", {})

        # --- Run Tests (pass) ----------------------------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # --- Review Code (approved) -----------------------------------------
        complete_user_task(workflow, "review_code", {"review": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "create_build_tasks" in names, "create_build_tasks must have been completed"
        assert "set_in_progress" in names, "set_in_progress must have run"
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
    """

    def test_test_fail_retry(self):
        workflow = load_workflow()

        # --- Setup ---------------------------------------------------------
        complete_user_task(workflow, "create_feature", {})
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})
        complete_user_task(workflow, "create_build_tasks", {})
        complete_user_task(workflow, "implement_directly", {"has_next_task": False})

        # --- Run Tests: FAIL (default branch, tests_passed not True) --------
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
    """

    def test_review_changes_requested(self):
        workflow = load_workflow()

        # --- Setup ---------------------------------------------------------
        complete_user_task(workflow, "create_feature", {})
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})
        complete_user_task(workflow, "create_build_tasks", {})
        complete_user_task(workflow, "implement_directly", {"has_next_task": False})

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


class TestNewModelElements:
    """Verify all v3 elements exist in the BPMN model spec."""

    def test_new_elements_in_spec(self):
        """create_build_tasks, set_in_progress, next_task_gw, start_task, implement_task, complete_task present."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        task_spec_names = list(spec.task_specs.keys())

        assert "create_build_tasks" in task_spec_names, (
            "create_build_tasks userTask must exist"
        )
        assert "set_in_progress" in task_spec_names, (
            "set_in_progress scriptTask must exist"
        )
        assert "next_task_gw" in task_spec_names, (
            "next_task_gw gateway must exist"
        )
        assert "start_task" in task_spec_names, (
            "start_task scriptTask must exist"
        )
        assert "implement_task" in task_spec_names, (
            "implement_task userTask must exist"
        )
        assert "complete_task" in task_spec_names, (
            "complete_task scriptTask must exist"
        )

    def test_enforcement_notes_in_bpmn_xml(self):
        """run_tests and review_code should have SHOULD BE ENFORCED in their documentation XML."""
        with open(BPMN_FILE, 'r', encoding='utf-8') as f:
            bpmn_content = f.read()
        # Both run_tests and review_code should have enforcement documentation
        assert "SHOULD BE ENFORCED" in bpmn_content, (
            "BPMN file should contain 'SHOULD BE ENFORCED' documentation for run_tests and review_code"
        )
        assert "reviewer-sonnet" in bpmn_content, (
            "BPMN file should reference 'reviewer-sonnet' in review_code documentation"
        )

    def test_set_in_progress_runs_before_complexity_gateway(self):
        """set_in_progress should auto-run between create_build_tasks and complexity_gateway."""
        workflow = load_workflow()
        complete_user_task(workflow, "create_feature", {})
        complete_user_task(workflow, "plan_feature", {"complexity": "simple"})
        complete_user_task(workflow, "create_build_tasks", {})

        # set_in_progress should have auto-run after create_build_tasks
        names = completed_spec_names(workflow)
        assert "set_in_progress" in names, (
            "set_in_progress must auto-run after create_build_tasks"
        )
