"""
Tests for the Commit Workflow BPMN process.

Uses SpiffWorkflow 3.x API directly against the commit_workflow.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Variable seeding rules:
  - checks_passed: set during run_pre_commit_checks (userTask immediately before checks_pass_gateway)
  - review: set during run_pre_commit_checks so it flows through code_review (scriptTask) into
            review_result_gateway. When looping (fix_issues -> run_pre_commit_checks again),
            re-set review during the repeated run_pre_commit_checks completion.
  - push_to_remote: set during write_commit_message (userTask immediately before create_commit
            scriptTask and then push_gateway).
  NOTE: push_to_remote is also a scriptTask ID; the data variable and task ID are separate
        namespaces in SpiffWorkflow and do not conflict.

Flow summary:
  start → stage_changes → run_pre_commit_checks → checks_pass_gateway
      [checks_passed==True]  → code_review (script) → review_result_gateway
          [review=="changes_requested"] → address_review_feedback → code_review (loop)
          [default/approved]            → write_commit_message → create_commit (script)
                                        → push_gateway
                                            [push_to_remote==True] → push_to_remote (script) → end_committed_pushed
                                            [default/no push]      → end_committed_local
      [default/fail]         → fix_issues → run_pre_commit_checks (loop)
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "development", "commit_workflow.bpmn")
)
PROCESS_ID = "commit_workflow"


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


class TestHappyPath:
    """
    Checks pass first time, review approved, no push -> ends at end_committed_local.

    Flow:
        start → stage_changes
        → run_pre_commit_checks [checks_passed=True, review="approved", push_to_remote=False]
        → checks_pass_gateway [pass] → code_review (script)
        → review_result_gateway [default/approved] → write_commit_message
        → create_commit (script) → push_gateway [default/no push] → end_committed_local
    """

    def test_happy_path(self):
        workflow = load_workflow()

        # --- Stage Changes -------------------------------------------------
        complete_user_task(workflow, "stage_changes", {})

        # --- Run Pre-commit Checks -----------------------------------------
        # Seed all downstream gateway variables here so they flow through
        # the subsequent scriptTasks (code_review, create_commit) intact.
        # checks_passed=True  -> checks_pass_gateway takes flow_checks_pass
        # review="approved"   -> review_result_gateway takes default (flow_approved)
        # push_to_remote=False -> push_gateway takes default (flow_no_push)
        complete_user_task(
            workflow,
            "run_pre_commit_checks",
            {"checks_passed": True, "review": "approved", "push_to_remote": False},
        )

        # --- Write Commit Message ------------------------------------------
        complete_user_task(workflow, "write_commit_message", {})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "stage_changes" in names, "stage_changes must have been completed"
        assert "run_pre_commit_checks" in names, "run_pre_commit_checks must have been completed"
        assert "code_review" in names, "code_review script must have run"
        assert "write_commit_message" in names, "write_commit_message must have been completed"
        assert "create_commit" in names, "create_commit script must have run"
        assert "end_committed_local" in names, "end_committed_local must be reached (no push)"

        assert "fix_issues" not in names, "fix_issues must NOT run when checks pass first time"
        assert "address_review_feedback" not in names, "address_review_feedback must NOT run on approved path"
        assert "push_to_remote" not in names, "push_to_remote task must NOT run when push_to_remote=False"
        assert "end_committed_pushed" not in names, "end_committed_pushed must NOT be reached without push"

        assert workflow.data.get("commit_created") is True, (
            "create_commit should have set commit_created=True"
        )


class TestChecksFailThenPass:
    """
    Checks fail on first attempt, fix issues, checks pass, review approved -> commit.

    Flow:
        start → stage_changes
        → run_pre_commit_checks [checks_passed=False] → checks_pass_gateway [fail]
        → fix_issues → run_pre_commit_checks (loop) [checks_passed=True, review="approved", push_to_remote=False]
        → checks_pass_gateway [pass] → code_review (script)
        → review_result_gateway [default/approved] → write_commit_message
        → create_commit (script) → push_gateway [default/no push] → end_committed_local
    """

    def test_checks_fail_then_pass(self):
        workflow = load_workflow()

        # --- Stage Changes -------------------------------------------------
        complete_user_task(workflow, "stage_changes", {})

        # --- Run Pre-commit Checks: FAIL -----------------------------------
        # checks_passed=False -> default branch (flow_checks_fail) fires -> fix_issues
        complete_user_task(
            workflow,
            "run_pre_commit_checks",
            {"checks_passed": False},
        )

        # Engine should stop at fix_issues (user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "fix_issues" in ready_names, (
            f"fix_issues should be READY after checks fail, got: {ready_names}"
        )

        # --- Fix Issues ----------------------------------------------------
        complete_user_task(workflow, "fix_issues", {})

        # Should loop back to run_pre_commit_checks
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "run_pre_commit_checks" in ready_names, (
            f"run_pre_commit_checks should be READY after fix_issues, got: {ready_names}"
        )

        # --- Run Pre-commit Checks: PASS -----------------------------------
        # Now seed all downstream gateway variables for the passing run
        complete_user_task(
            workflow,
            "run_pre_commit_checks",
            {"checks_passed": True, "review": "approved", "push_to_remote": False},
        )

        # --- Write Commit Message ------------------------------------------
        complete_user_task(workflow, "write_commit_message", {})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after checks retry"

        names = completed_spec_names(workflow)
        assert "fix_issues" in names, "fix_issues must have been completed"
        assert "code_review" in names, "code_review script must have run"
        assert "create_commit" in names, "create_commit script must have run"
        assert "end_committed_local" in names, "end_committed_local must be reached"

        assert "address_review_feedback" not in names, (
            "address_review_feedback must NOT run when review is approved"
        )
        assert "end_committed_pushed" not in names, "end_committed_pushed must NOT be reached"

        assert workflow.data.get("commit_created") is True, (
            "create_commit should have set commit_created=True"
        )


class TestReviewChangesRequested:
    """
    Checks pass, review requests changes, fix feedback, review approved -> commit.

    Flow:
        start → stage_changes
        → run_pre_commit_checks [checks_passed=True, review="changes_requested", push_to_remote=False]
        → checks_pass_gateway [pass] → code_review (script)
        → review_result_gateway [changes_requested] → address_review_feedback
        → code_review (script, loop)
        → review_result_gateway [default/approved]  → write_commit_message
        → create_commit (script) → push_gateway [default/no push] → end_committed_local
    """

    def test_review_changes_requested(self):
        workflow = load_workflow()

        # --- Stage Changes -------------------------------------------------
        complete_user_task(workflow, "stage_changes", {})

        # --- Run Pre-commit Checks: pass, but review will request changes --
        # review="changes_requested" -> review_result_gateway takes flow_changes_requested
        complete_user_task(
            workflow,
            "run_pre_commit_checks",
            {"checks_passed": True, "review": "changes_requested", "push_to_remote": False},
        )

        # Engine should stop at address_review_feedback (user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "address_review_feedback" in ready_names, (
            f"address_review_feedback should be READY after changes_requested, got: {ready_names}"
        )

        # --- Address Review Feedback --------------------------------------
        # Update review to "approved" so the next pass through review_result_gateway
        # takes the default (approved) branch.
        complete_user_task(workflow, "address_review_feedback", {"review": "approved"})

        # code_review scriptTask auto-completes; review_result_gateway takes default (approved);
        # engine should stop at write_commit_message
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "write_commit_message" in ready_names, (
            f"write_commit_message should be READY after approved review, got: {ready_names}"
        )

        # --- Write Commit Message ------------------------------------------
        complete_user_task(workflow, "write_commit_message", {})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after review fix"

        names = completed_spec_names(workflow)
        assert "address_review_feedback" in names, "address_review_feedback must have been completed"
        assert "create_commit" in names, "create_commit script must have run"
        assert "end_committed_local" in names, "end_committed_local must be reached"

        assert "fix_issues" not in names, "fix_issues must NOT run (checks passed)"
        assert "end_committed_pushed" not in names, "end_committed_pushed must NOT be reached"

        assert workflow.data.get("commit_created") is True, (
            "create_commit should have set commit_created=True"
        )


class TestPushToRemote:
    """
    Full flow with push=True at the end -> ends at end_committed_pushed.

    Flow:
        start → stage_changes
        → run_pre_commit_checks [checks_passed=True, review="approved"]
        → checks_pass_gateway [pass] → code_review (script)
        → review_result_gateway [default/approved] → write_commit_message [push_to_remote=True]
        → create_commit (script) → push_gateway [push_to_remote==True]
        → push_to_remote (script) → end_committed_pushed
    """

    def test_push_to_remote(self):
        workflow = load_workflow()

        # --- Stage Changes -------------------------------------------------
        complete_user_task(workflow, "stage_changes", {})

        # --- Run Pre-commit Checks: pass -----------------------------------
        # Seed checks_passed and review; push_to_remote will be set later at
        # write_commit_message to demonstrate that it can be set at that point too.
        complete_user_task(
            workflow,
            "run_pre_commit_checks",
            {"checks_passed": True, "review": "approved"},
        )

        # --- Write Commit Message (with push=True) -------------------------
        # push_to_remote=True -> push_gateway takes flow_push_yes
        complete_user_task(workflow, "write_commit_message", {"push_to_remote": True})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after push"

        names = completed_spec_names(workflow)
        assert "code_review" in names, "code_review script must have run"
        assert "write_commit_message" in names, "write_commit_message must have been completed"
        assert "create_commit" in names, "create_commit script must have run"
        assert "push_to_remote" in names, "push_to_remote script must have run"
        assert "end_committed_pushed" in names, "end_committed_pushed must be reached"

        assert "fix_issues" not in names, "fix_issues must NOT run"
        assert "address_review_feedback" not in names, "address_review_feedback must NOT run"
        assert "end_committed_local" not in names, "end_committed_local must NOT be reached (push happened)"

        assert workflow.data.get("commit_created") is True, (
            "create_commit should have set commit_created=True"
        )
        assert workflow.data.get("pushed") is True, (
            "push_to_remote script should have set pushed=True"
        )
