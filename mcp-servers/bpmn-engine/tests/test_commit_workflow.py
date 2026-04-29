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
        assert "auto_resolve_feedback" in names, "auto_resolve_feedback (FB397) must run after create_commit"
        assert "end_committed_local" in names, "end_committed_local must be reached (no push)"

        assert "fix_issues" not in names, "fix_issues must NOT run when checks pass first time"
        assert "address_review_feedback" not in names, "address_review_feedback must NOT run on approved path"
        assert "push_to_remote" not in names, "push_to_remote task must NOT run when push_to_remote=False"
        assert "end_committed_pushed" not in names, "end_committed_pushed must NOT be reached without push"

        assert workflow.data.get("commit_created") is True, (
            "create_commit should have set commit_created=True"
        )
        assert workflow.data.get("auto_resolve_ran") is True, (
            "auto_resolve_feedback should have set auto_resolve_ran=True (FB397)"
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
        assert "auto_resolve_feedback" in names, "auto_resolve_feedback (FB397) must run before push"
        assert "push_to_remote" in names, "push_to_remote script must have run"
        assert "end_committed_pushed" in names, "end_committed_pushed must be reached"

        assert "fix_issues" not in names, "fix_issues must NOT run"
        assert "address_review_feedback" not in names, "address_review_feedback must NOT run"
        assert "end_committed_local" not in names, "end_committed_local must NOT be reached (push happened)"

        assert workflow.data.get("commit_created") is True, (
            "create_commit should have set commit_created=True"
        )
        assert workflow.data.get("auto_resolve_ran") is True, (
            "auto_resolve_feedback should have set auto_resolve_ran=True (FB397)"
        )
        assert workflow.data.get("pushed") is True, (
            "push_to_remote script should have set pushed=True"
        )


# ---------------------------------------------------------------------------
# FB397: Auto-resolve [FB#] References — model-level coverage
# ---------------------------------------------------------------------------
# These tests assert the auto_resolve_feedback step is present on every path
# from create_commit. The FB#-parsing semantics live in the hook
# (scripts/commit_fb_resolve_hook.py) and are tested separately.


class TestAutoResolveFeedbackPresence:
    """
    The auto_resolve_feedback scriptTask MUST appear between create_commit and
    push_gateway on every path that reaches a commit. This guards against
    regressions where someone re-wires create_commit straight to push_gateway
    and silently drops the FB# auto-resolve step.
    """

    def test_auto_resolve_runs_on_no_push_path(self):
        workflow = load_workflow()
        complete_user_task(workflow, "stage_changes", {})
        complete_user_task(
            workflow,
            "run_pre_commit_checks",
            {"checks_passed": True, "review": "approved", "push_to_remote": False},
        )
        complete_user_task(workflow, "write_commit_message", {})

        names = completed_spec_names(workflow)
        assert "create_commit" in names
        assert "auto_resolve_feedback" in names
        # Ordering: auto_resolve_feedback must come after create_commit
        assert names.index("auto_resolve_feedback") > names.index("create_commit"), (
            "auto_resolve_feedback must run AFTER create_commit, not before"
        )
        assert workflow.data.get("auto_resolve_ran") is True

    def test_auto_resolve_runs_on_push_path(self):
        workflow = load_workflow()
        complete_user_task(workflow, "stage_changes", {})
        complete_user_task(
            workflow,
            "run_pre_commit_checks",
            {"checks_passed": True, "review": "approved"},
        )
        complete_user_task(workflow, "write_commit_message", {"push_to_remote": True})

        names = completed_spec_names(workflow)
        assert "create_commit" in names
        assert "auto_resolve_feedback" in names
        assert "push_to_remote" in names
        # Ordering: auto_resolve_feedback must come AFTER create_commit and BEFORE push_to_remote
        assert names.index("auto_resolve_feedback") > names.index("create_commit")
        assert names.index("auto_resolve_feedback") < names.index("push_to_remote"), (
            "auto_resolve_feedback must run BEFORE push, so resolution happens "
            "even on commits that are never pushed"
        )
        assert workflow.data.get("auto_resolve_ran") is True

    def test_auto_resolve_skipped_when_workflow_terminates_early(self):
        """
        If checks fail forever (workflow doesn't reach create_commit), the
        auto_resolve_feedback step must NOT run. Sanity check that we haven't
        accidentally moved it onto a pre-commit branch.
        """
        workflow = load_workflow()
        complete_user_task(workflow, "stage_changes", {})
        complete_user_task(workflow, "run_pre_commit_checks", {"checks_passed": False})

        # Workflow is now stalled at fix_issues; auto_resolve_feedback must not
        # appear in completed task names.
        names = completed_spec_names(workflow)
        assert "create_commit" not in names, "create_commit must NOT run when checks fail"
        assert "auto_resolve_feedback" not in names, (
            "auto_resolve_feedback must NOT run on the pre-commit failure path"
        )
