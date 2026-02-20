"""
Tests for the Feedback to Feature BPMN process.

Uses SpiffWorkflow 3.x API directly against the feedback_to_feature.bpmn definition.
No external database required - all assertions are on task data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions evaluated against task.data
  - CRITICAL: SpiffWorkflow evaluates ALL branch conditions (not short-circuit), so ALL
    variables referenced in ANY condition must be present in task.data before the gateway.

Flow summary:
  start -> triage_feedback (inject: triage_action)
        -> triage_action_gateway
               [triage_action=="duplicate"]   -> mark_duplicate -> end_duplicate
               [triage_action=="wont_fix"]    -> mark_wont_fix -> end_wont_fix
               [triage_action=="fix_directly"]-> implement_fix -> mark_resolved -> end_resolved
               [default/create_feature]       -> plan_feature -> create_feature_record
                                              -> create_build_tasks -> link_feedback
                                              -> end_feature_created
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "feedback_to_feature.bpmn")
)
PROCESS_ID = "feedback_to_feature"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    wf.do_engine_steps()
    return wf


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() so the engine advances through any subsequent automated
    tasks (script tasks, gateways) until the next user task or end event.

    Raises AssertionError if the task is not currently READY.
    """
    tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
    target = [t for t in tasks if t.task_spec.name == task_name]
    assert target, (
        f"No READY manual task named '{task_name}'. "
        f"Ready: {[t.task_spec.name for t in tasks]}"
    )
    task = target[0]
    if data:
        task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_names(workflow: BpmnWorkflow) -> set:
    """Return the spec names of all COMPLETED tasks in the workflow."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateFeature:
    """
    Default (create_feature) path: triage -> plan_feature -> create_feature_record
    -> create_build_tasks -> link_feedback -> end_feature_created.

    Verifies:
        - plan_feature completed
        - feature_created, tasks_created, feedback_linked all True in workflow.data
        - feedback_status == "in_progress"
        - mark_duplicate NOT in completed (short-circuit check)
        - mark_wont_fix NOT in completed
        - mark_resolved NOT in completed
        - end_feature_created reached
    """

    def test_create_feature(self):
        workflow = load_workflow()

        # triage_action="create_feature" triggers the default gateway branch.
        # The default flow has no conditionExpression, so it fires when no
        # other condition matches. Since SpiffWorkflow evaluates ALL conditions,
        # triage_action must be present to prevent KeyError on other branches.
        complete_user_task(workflow, "triage_feedback", {"triage_action": "create_feature"})

        # Engine stops at plan_feature (user task on the default path).
        tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
        ready_names = [t.task_spec.name for t in tasks]
        assert "plan_feature" in ready_names, (
            f"plan_feature should be READY after triage on create_feature path, got: {ready_names}"
        )

        complete_user_task(workflow, "plan_feature", {})

        assert workflow.is_completed(), "Workflow should be completed after plan_feature"

        names = completed_names(workflow)
        assert "plan_feature" in names, "plan_feature must have been completed"
        assert "create_feature_record" in names, "create_feature_record script must have run"
        assert "create_build_tasks" in names, "create_build_tasks script must have run"
        assert "link_feedback" in names, "link_feedback script must have run"
        assert "end_feature_created" in names, "end_feature_created end event must be reached"

        assert "mark_duplicate" not in names, (
            "mark_duplicate must NOT execute on create_feature path"
        )
        assert "mark_wont_fix" not in names, (
            "mark_wont_fix must NOT execute on create_feature path"
        )
        assert "mark_resolved" not in names, (
            "mark_resolved must NOT execute on create_feature path"
        )

        assert workflow.data.get("feature_created") is True, (
            "create_feature_record should have set feature_created=True"
        )
        assert workflow.data.get("tasks_created") is True, (
            "create_build_tasks should have set tasks_created=True"
        )
        assert workflow.data.get("feedback_linked") is True, (
            "link_feedback should have set feedback_linked=True"
        )
        assert workflow.data.get("feedback_status") == "in_progress", (
            "link_feedback should have set feedback_status='in_progress'"
        )


class TestDirectFix:
    """
    Fix Directly path: triage -> implement_fix -> mark_resolved -> end_resolved.

    Verifies:
        - implement_fix completed (user task)
        - mark_resolved completed (script task)
        - fix_applied True in workflow.data
        - feedback_status == "resolved"
        - plan_feature NOT in completed
        - end_resolved reached
    """

    def test_direct_fix(self):
        workflow = load_workflow()

        complete_user_task(workflow, "triage_feedback", {"triage_action": "fix_directly"})

        # Engine stops at implement_fix (user task).
        tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
        ready_names = [t.task_spec.name for t in tasks]
        assert "implement_fix" in ready_names, (
            f"implement_fix should be READY after fix_directly triage, got: {ready_names}"
        )

        complete_user_task(workflow, "implement_fix", {})

        assert workflow.is_completed(), "Workflow should be completed after implement_fix"

        names = completed_names(workflow)
        assert "implement_fix" in names, "implement_fix must have been completed"
        assert "mark_resolved" in names, "mark_resolved script must have run"
        assert "end_resolved" in names, "end_resolved end event must be reached"

        assert "plan_feature" not in names, (
            "plan_feature must NOT execute on fix_directly path"
        )
        assert "mark_duplicate" not in names, (
            "mark_duplicate must NOT execute on fix_directly path"
        )
        assert "mark_wont_fix" not in names, (
            "mark_wont_fix must NOT execute on fix_directly path"
        )

        assert workflow.data.get("fix_applied") is True, (
            "mark_resolved should have set fix_applied=True"
        )
        assert workflow.data.get("feedback_status") == "resolved", (
            "mark_resolved should have set feedback_status='resolved'"
        )


class TestWontFix:
    """
    Won't Fix path: triage -> mark_wont_fix -> end_wont_fix.

    Verifies:
        - mark_wont_fix completed (script task, no user interaction needed)
        - wont_fix_marked True in workflow.data
        - feedback_status == "wont_fix"
        - end_wont_fix reached
        - plan_feature, implement_fix, mark_duplicate all NOT in completed
    """

    def test_wont_fix(self):
        workflow = load_workflow()

        complete_user_task(workflow, "triage_feedback", {"triage_action": "wont_fix"})

        assert workflow.is_completed(), (
            "Workflow should be completed immediately after triage on wont_fix path "
            "(mark_wont_fix is a script task with no user interaction)"
        )

        names = completed_names(workflow)
        assert "mark_wont_fix" in names, "mark_wont_fix script must have run"
        assert "end_wont_fix" in names, "end_wont_fix end event must be reached"

        assert "plan_feature" not in names, (
            "plan_feature must NOT execute on wont_fix path"
        )
        assert "implement_fix" not in names, (
            "implement_fix must NOT execute on wont_fix path"
        )
        assert "mark_duplicate" not in names, (
            "mark_duplicate must NOT execute on wont_fix path"
        )

        assert workflow.data.get("wont_fix_marked") is True, (
            "mark_wont_fix should have set wont_fix_marked=True"
        )
        assert workflow.data.get("feedback_status") == "wont_fix", (
            "mark_wont_fix should have set feedback_status='wont_fix'"
        )


class TestDuplicate:
    """
    Duplicate path: triage -> mark_duplicate -> end_duplicate.

    Verifies:
        - mark_duplicate completed (script task, no user interaction needed)
        - duplicate_marked True in workflow.data
        - feedback_status == "duplicate"
        - end_duplicate reached
        - plan_feature, implement_fix, mark_wont_fix all NOT in completed
    """

    def test_duplicate(self):
        workflow = load_workflow()

        complete_user_task(workflow, "triage_feedback", {"triage_action": "duplicate"})

        assert workflow.is_completed(), (
            "Workflow should be completed immediately after triage on duplicate path "
            "(mark_duplicate is a script task with no user interaction)"
        )

        names = completed_names(workflow)
        assert "mark_duplicate" in names, "mark_duplicate script must have run"
        assert "end_duplicate" in names, "end_duplicate end event must be reached"

        assert "plan_feature" not in names, (
            "plan_feature must NOT execute on duplicate path"
        )
        assert "implement_fix" not in names, (
            "implement_fix must NOT execute on duplicate path"
        )
        assert "mark_wont_fix" not in names, (
            "mark_wont_fix must NOT execute on duplicate path"
        )

        assert workflow.data.get("duplicate_marked") is True, (
            "mark_duplicate should have set duplicate_marked=True"
        )
        assert workflow.data.get("feedback_status") == "duplicate", (
            "mark_duplicate should have set feedback_status='duplicate'"
        )
