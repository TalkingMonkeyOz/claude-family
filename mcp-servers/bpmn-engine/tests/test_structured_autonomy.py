"""
Tests for the Structured Autonomy BPMN process.

Validates the full Plan-Generate-Implement-Review-Complete workflow:
  1. Happy path (SA): assess(complex) → plan → approve → generate → implement(2 tasks) → review(ok) → tests(pass) → commit
  2. Simple path: assess(simple) → implement directly → done
  3. Plan revision loop: plan rejected → revise → re-review → approved
  4. Step verification failure: step fails → fix → re-verify → pass → continue
  5. Review changes requested: reviewer → changes → fix → re-review → approved
  6. Final test failure: tests fail → fix → re-run → pass → commit
  7. Multi-task loop: 3 tasks with mixed agent types (haiku + sonnet)
  8. Double review rejection: review fails twice before passing

Key API notes (SpiffWorkflow 3.1.x):
  - userTasks need manual=True to find them
  - Gateway conditions evaluate against task.data
  - scriptTasks set variables in task.data that propagate to children
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "development", "structured_autonomy.bpmn")
)
PROCESS_ID = "structured_autonomy"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(workflow: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(workflow)]


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """Find named READY user task, merge data, run it, advance engine."""
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Helper: run through a standard SA flow up to Phase 3 (implement loop)
# ---------------------------------------------------------------------------

def run_through_plan_and_generate(wf, task_count=2):
    """Run through assessment, planning, and generation phases.
    Returns with pick_next_task ready (first task in implement loop).
    """
    # Phase 0: Assess as complex → use SA
    complete_user_task(wf, "assess_complexity", {
        "use_sa": True,
        "plan_approved": True,
        "task_count": task_count,
        "task_complexity": "low",
        "step_verified": True,
        "review_result": "approved",
        "all_tests_pass": True,
    })

    # Phase 1: Research + plan + user approves
    complete_user_task(wf, "research_codebase")
    complete_user_task(wf, "create_plan")
    complete_user_task(wf, "user_reviews_plan")

    # Phase 2: Generate specs → creates build tasks
    complete_user_task(wf, "generate_specs")

    # After create_build_tasks script and advance_to_in_progress script,
    # pick_next_task should be ready
    # But pick_next_task is a scriptTask, so it auto-runs.
    # The next ready task depends on agent_type_gw...


# ---------------------------------------------------------------------------
# Test 1: Happy Path - Full SA workflow
# ---------------------------------------------------------------------------

class TestHappyPath:
    """Full SA: assess → plan → approve → generate → implement(2) → review → test → commit."""

    def test_full_sa_happy_path(self):
        wf = load_workflow()

        # Phase 0: Complex feature → SA
        complete_user_task(wf, "assess_complexity", {
            "use_sa": True,
            "plan_approved": True,
            "task_count": 2,
            "task_complexity": "low",
            "step_verified": True,
            "review_result": "approved",
            "all_tests_pass": True,
        })

        # Phase 1: Plan
        complete_user_task(wf, "research_codebase")
        complete_user_task(wf, "create_plan")
        complete_user_task(wf, "user_reviews_plan")
        # plan_approved=True → advance_to_planned script runs

        # Phase 2: Generate
        complete_user_task(wf, "generate_specs")
        # create_build_tasks + advance_to_in_progress scripts run
        # pick_next_task script runs → agent_type_gw → spawn_haiku (default)

        # Phase 3: Implement - Task 1
        complete_user_task(wf, "spawn_haiku")
        # agent_merge → verify_step
        complete_user_task(wf, "verify_step")
        # step_verified=True → complete_task script (current_task_index=1, tasks_remaining=True)
        # → more_tasks_gw → pick_next_task → spawn_haiku

        # Phase 3: Implement - Task 2
        complete_user_task(wf, "spawn_haiku")
        complete_user_task(wf, "verify_step")
        # complete_task: current_task_index=2, tasks_remaining=False
        # → more_tasks_gw → spawn_reviewer

        # Phase 4: Review
        complete_user_task(wf, "spawn_reviewer")
        # review_result=approved → run_all_tests

        # Phase 5: Complete
        complete_user_task(wf, "run_all_tests")
        # all_tests_pass=True → commit_feature
        complete_user_task(wf, "commit_feature")
        # mark_feature_complete script → end

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "create_feature_record" in names
        assert "advance_to_planned" in names
        assert "create_build_tasks" in names
        assert "advance_to_in_progress" in names
        assert "mark_feature_complete" in names
        assert "end_complete" in names
        assert "implement_simple" not in names
        assert wf.data.get("status") == "completed"
        assert wf.data.get("completed_tasks") == 2


# ---------------------------------------------------------------------------
# Test 2: Simple Path - Skip SA
# ---------------------------------------------------------------------------

class TestSimplePath:
    """Simple feature: assess(simple) → implement directly → done."""

    def test_simple_feature_skips_sa(self):
        wf = load_workflow()

        # Assess as simple → skip SA
        complete_user_task(wf, "assess_complexity", {"use_sa": False})
        complete_user_task(wf, "implement_simple")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "implement_simple" in names
        assert "end_simple" in names
        assert "create_feature_record" not in names
        assert "research_codebase" not in names


# ---------------------------------------------------------------------------
# Test 3: Plan Revision Loop
# ---------------------------------------------------------------------------

class TestPlanRevision:
    """Plan rejected → revise → re-review → approved → continue."""

    def test_plan_rejected_then_approved(self):
        wf = load_workflow()

        complete_user_task(wf, "assess_complexity", {
            "use_sa": True,
            "plan_approved": False,  # First review rejects
            "task_count": 1,
            "task_complexity": "low",
            "step_verified": True,
            "review_result": "approved",
            "all_tests_pass": True,
        })

        complete_user_task(wf, "research_codebase")
        complete_user_task(wf, "create_plan")
        complete_user_task(wf, "user_reviews_plan")
        # plan_approved=False → revise_plan

        assert "revise_plan" in ready_task_names(wf)
        complete_user_task(wf, "revise_plan")

        # Back to user_reviews_plan
        assert "user_reviews_plan" in ready_task_names(wf)
        complete_user_task(wf, "user_reviews_plan", {"plan_approved": True})

        # Now proceeds to Phase 2
        complete_user_task(wf, "generate_specs")

        # Implement single task
        complete_user_task(wf, "spawn_haiku")
        complete_user_task(wf, "verify_step")

        # Review + Complete
        complete_user_task(wf, "spawn_reviewer")
        complete_user_task(wf, "run_all_tests")
        complete_user_task(wf, "commit_feature")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "revise_plan" in names
        assert "end_complete" in names


# ---------------------------------------------------------------------------
# Test 4: Step Verification Failure
# ---------------------------------------------------------------------------

class TestStepVerificationFailure:
    """Step fails → fix → re-verify → pass → continue."""

    def test_step_fails_then_fixed(self):
        wf = load_workflow()

        complete_user_task(wf, "assess_complexity", {
            "use_sa": True,
            "plan_approved": True,
            "task_count": 1,
            "task_complexity": "low",
            "step_verified": False,  # First verify fails
            "review_result": "approved",
            "all_tests_pass": True,
        })

        complete_user_task(wf, "research_codebase")
        complete_user_task(wf, "create_plan")
        complete_user_task(wf, "user_reviews_plan")
        complete_user_task(wf, "generate_specs")

        # Task 1: agent completes
        complete_user_task(wf, "spawn_haiku")

        # Verify fails → fix_step
        complete_user_task(wf, "verify_step")
        assert "fix_step" in ready_task_names(wf)

        complete_user_task(wf, "fix_step")

        # Back to verify_step → now passes
        assert "verify_step" in ready_task_names(wf)
        complete_user_task(wf, "verify_step", {"step_verified": True})

        # Continue to review + complete
        complete_user_task(wf, "spawn_reviewer")
        complete_user_task(wf, "run_all_tests")
        complete_user_task(wf, "commit_feature")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "fix_step" in names


# ---------------------------------------------------------------------------
# Test 5: Review Changes Requested
# ---------------------------------------------------------------------------

class TestReviewChangesRequested:
    """Reviewer requests changes → fix → re-review → approved."""

    def test_review_changes_then_approved(self):
        wf = load_workflow()

        complete_user_task(wf, "assess_complexity", {
            "use_sa": True,
            "plan_approved": True,
            "task_count": 1,
            "task_complexity": "low",
            "step_verified": True,
            "review_result": "changes_requested",  # First review rejects
            "all_tests_pass": True,
        })

        complete_user_task(wf, "research_codebase")
        complete_user_task(wf, "create_plan")
        complete_user_task(wf, "user_reviews_plan")
        complete_user_task(wf, "generate_specs")

        # Implement single task
        complete_user_task(wf, "spawn_haiku")
        complete_user_task(wf, "verify_step")

        # Review → changes requested
        complete_user_task(wf, "spawn_reviewer")
        assert "fix_review_issues" in ready_task_names(wf)

        complete_user_task(wf, "fix_review_issues")
        # → re_review
        assert "re_review" in ready_task_names(wf)

        complete_user_task(wf, "re_review", {"review_result": "approved"})
        # → run_all_tests

        complete_user_task(wf, "run_all_tests")
        complete_user_task(wf, "commit_feature")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "fix_review_issues" in names
        assert "re_review" in names


# ---------------------------------------------------------------------------
# Test 6: Final Test Failure
# ---------------------------------------------------------------------------

class TestFinalTestFailure:
    """Tests fail → fix → re-run → pass → commit."""

    def test_final_tests_fail_then_pass(self):
        wf = load_workflow()

        complete_user_task(wf, "assess_complexity", {
            "use_sa": True,
            "plan_approved": True,
            "task_count": 1,
            "task_complexity": "low",
            "step_verified": True,
            "review_result": "approved",
            "all_tests_pass": False,  # First run fails
        })

        complete_user_task(wf, "research_codebase")
        complete_user_task(wf, "create_plan")
        complete_user_task(wf, "user_reviews_plan")
        complete_user_task(wf, "generate_specs")
        complete_user_task(wf, "spawn_haiku")
        complete_user_task(wf, "verify_step")
        complete_user_task(wf, "spawn_reviewer")

        # Tests fail
        complete_user_task(wf, "run_all_tests")
        assert "fix_test_failures" in ready_task_names(wf)

        complete_user_task(wf, "fix_test_failures")

        # Re-run tests → pass
        assert "run_all_tests" in ready_task_names(wf)
        complete_user_task(wf, "run_all_tests", {"all_tests_pass": True})

        complete_user_task(wf, "commit_feature")

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "fix_test_failures" in names


# ---------------------------------------------------------------------------
# Test 7: Multi-task with Mixed Agent Types
# ---------------------------------------------------------------------------

class TestMultiTaskMixedAgents:
    """3 tasks: 2 haiku (simple) + 1 sonnet (complex)."""

    def test_three_tasks_mixed_agents(self):
        wf = load_workflow()

        complete_user_task(wf, "assess_complexity", {
            "use_sa": True,
            "plan_approved": True,
            "task_count": 3,
            "task_complexity": "low",  # Start with low
            "step_verified": True,
            "review_result": "approved",
            "all_tests_pass": True,
        })

        # Plan + Generate
        complete_user_task(wf, "research_codebase")
        complete_user_task(wf, "create_plan")
        complete_user_task(wf, "user_reviews_plan")
        complete_user_task(wf, "generate_specs")

        # Task 1: haiku (default, low complexity)
        complete_user_task(wf, "spawn_haiku")
        complete_user_task(wf, "verify_step")

        # Task 2: sonnet (high complexity)
        # After complete_task, pick_next_task re-runs. Change complexity.
        complete_user_task(wf, "spawn_haiku", {"task_complexity": "high"})
        complete_user_task(wf, "verify_step")

        # Task 3: sonnet (still high from previous data)
        complete_user_task(wf, "spawn_sonnet")
        complete_user_task(wf, "verify_step")

        # Review + Complete
        complete_user_task(wf, "spawn_reviewer")
        complete_user_task(wf, "run_all_tests")
        complete_user_task(wf, "commit_feature")

        assert wf.is_completed()
        assert wf.data.get("completed_tasks") == 3
        assert wf.data.get("current_task_index") == 3


# ---------------------------------------------------------------------------
# Test 8: Double Review Rejection
# ---------------------------------------------------------------------------

class TestDoubleReviewRejection:
    """Review fails twice before passing on third review."""

    def test_two_review_rejections(self):
        wf = load_workflow()

        complete_user_task(wf, "assess_complexity", {
            "use_sa": True,
            "plan_approved": True,
            "task_count": 1,
            "task_complexity": "low",
            "step_verified": True,
            "review_result": "changes_requested",  # Always reject initially
            "all_tests_pass": True,
        })

        # Plan + Generate + Implement
        complete_user_task(wf, "research_codebase")
        complete_user_task(wf, "create_plan")
        complete_user_task(wf, "user_reviews_plan")
        complete_user_task(wf, "generate_specs")
        complete_user_task(wf, "spawn_haiku")
        complete_user_task(wf, "verify_step")

        # First review → changes requested
        complete_user_task(wf, "spawn_reviewer")
        complete_user_task(wf, "fix_review_issues")
        complete_user_task(wf, "re_review")  # Still changes_requested

        # Second rejection → fix again
        assert "fix_review_issues" in ready_task_names(wf)
        complete_user_task(wf, "fix_review_issues")
        complete_user_task(wf, "re_review", {"review_result": "approved"})

        # Now proceed to tests + commit
        complete_user_task(wf, "run_all_tests")
        complete_user_task(wf, "commit_feature")

        assert wf.is_completed()
        assert wf.data.get("status") == "completed"
