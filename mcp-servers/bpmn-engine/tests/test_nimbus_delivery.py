"""
Tests for the Nimbus Client Delivery BPMN process.

Uses SpiffWorkflow 3.x API directly against the nimbus_delivery.bpmn definition.
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
  start → onboard_client → setup_environment → ingest_knowledge → knowledge_ready
       → gather_requirements → validate_requirements → requirements_complete_gateway
           [requirements_valid==True] → generate_config → review_config
                                     → config_approved_gateway
               [config_action=="revise"] → generate_config (loop)
               [default/approved]        → deploy_uat → run_tests
                                         → tests_pass_gateway
               [tests_passed==True] → deploy_production → generate_docs
                                    → handoff_client → set_delivered → end_delivered
               [default/fail]       → fix_config → deploy_uat (loop)
           [default/gaps]           → fill_gaps → gather_requirements (loop)
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "nimbus", "nimbus_delivery.bpmn")
)
PROCESS_ID = "nimbus_delivery"


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
    Full delivery: onboard → environment setup → ingest → gather requirements
    (valid on first pass) → generate config → review (approved) → UAT →
    run tests (pass) → deploy production → docs → handoff → delivered.

    Verifies: status == "delivered", all key script tasks completed.
    """

    def test_happy_path(self):
        workflow = load_workflow()

        # --- Onboard Client -----------------------------------------------
        complete_user_task(workflow, "onboard_client", {})

        # Engine auto-runs setup_environment (scriptTask: environment_ready = True)
        # and stops at ingest_knowledge (userTask)

        # --- Ingest Knowledge ---------------------------------------------
        complete_user_task(workflow, "ingest_knowledge", {})

        # Engine auto-runs knowledge_ready (scriptTask: knowledge_ingested = True)
        # and stops at gather_requirements (userTask)

        # --- Gather Requirements ------------------------------------------
        # Pass requirements_valid=True so requirements_complete_gateway takes
        # the conditional branch to generate_config (not the default fill_gaps).
        complete_user_task(workflow, "gather_requirements", {"requirements_valid": True})

        # --- Validate Requirements ----------------------------------------
        # requirements_valid already in task.data from gather_requirements output.
        complete_user_task(workflow, "validate_requirements", {})

        # Engine routes through requirements_complete_gateway [requirements_valid==True]
        # and stops at generate_config (userTask)

        # --- Generate Config ----------------------------------------------
        # Pass config_action="approved" so config_approved_gateway takes the
        # default (approved) branch to deploy_uat.
        complete_user_task(workflow, "generate_config", {"config_action": "approved"})

        # --- Review Config ------------------------------------------------
        # config_action already in task.data.
        complete_user_task(workflow, "review_config", {})

        # Engine routes through config_approved_gateway [default/approved]
        # and auto-runs deploy_uat (scriptTask: deployed_to_uat = True),
        # then stops at run_tests (userTask)

        # --- Run Tests (pass) --------------------------------------------
        # Pass tests_passed=True so tests_pass_gateway takes the conditional
        # branch to deploy_production.
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # Engine auto-runs deploy_production (scriptTask: deployed_to_prod = True),
        # generate_docs (scriptTask: docs_generated = True), stops at handoff_client

        # --- Handoff Client -----------------------------------------------
        complete_user_task(workflow, "handoff_client", {})

        # Engine auto-runs set_delivered (scriptTask: status = "delivered"),
        # then reaches end_delivered

        # --- Assertions ---------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "setup_environment" in names, "setup_environment script must have run"
        assert "knowledge_ready" in names, "knowledge_ready script must have run"
        assert "deploy_uat" in names, "deploy_uat script must have run"
        assert "deploy_production" in names, "deploy_production script must have run"
        assert "generate_docs" in names, "generate_docs script must have run"
        assert "set_delivered" in names, "set_delivered script must have run"
        assert "end_delivered" in names, "end_delivered end event must be reached"
        assert "fill_gaps" not in names, "fill_gaps must NOT run on happy path"
        assert "fix_config" not in names, "fix_config must NOT run on happy path"

        assert workflow.data.get("environment_ready") is True, (
            "setup_environment should have set environment_ready=True"
        )
        assert workflow.data.get("knowledge_ingested") is True, (
            "knowledge_ready should have set knowledge_ingested=True"
        )
        assert workflow.data.get("deployed_to_uat") is True, (
            "deploy_uat should have set deployed_to_uat=True"
        )
        assert workflow.data.get("deployed_to_prod") is True, (
            "deploy_production should have set deployed_to_prod=True"
        )
        assert workflow.data.get("docs_generated") is True, (
            "generate_docs should have set docs_generated=True"
        )
        assert workflow.data.get("status") == "delivered", (
            "set_delivered should have set status='delivered'"
        )


class TestRequirementsGapLoop:
    """
    Requirements are incomplete on first pass → fill_gaps → gather_requirements
    again (valid on second pass) → continue to config and delivery.

    Verifies: fill_gaps completed, final status == "delivered".
    """

    def test_requirements_gap_loop(self):
        workflow = load_workflow()

        # --- Onboard and Ingest -------------------------------------------
        complete_user_task(workflow, "onboard_client", {})
        complete_user_task(workflow, "ingest_knowledge", {})

        # --- Gather Requirements (first pass - gaps found) ----------------
        # Do NOT set requirements_valid=True; gateway defaults to fill_gaps.
        complete_user_task(workflow, "gather_requirements", {"requirements_valid": False})

        # --- Validate Requirements (first pass) ---------------------------
        complete_user_task(workflow, "validate_requirements", {})

        # Engine routes through requirements_complete_gateway [default/gaps_found]
        # and stops at fill_gaps (userTask)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "fill_gaps" in ready_names, (
            f"fill_gaps should be READY after gaps found, got: {ready_names}"
        )

        # --- Fill Gaps ----------------------------------------------------
        complete_user_task(workflow, "fill_gaps", {})

        # Engine loops back to gather_requirements
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "gather_requirements" in ready_names, (
            f"gather_requirements should be READY after fill_gaps, got: {ready_names}"
        )

        # --- Gather Requirements (second pass - now valid) ----------------
        complete_user_task(workflow, "gather_requirements", {"requirements_valid": True})

        # --- Validate Requirements (second pass) -------------------------
        complete_user_task(workflow, "validate_requirements", {})

        # Engine routes through requirements_complete_gateway [requirements_valid==True]
        # and stops at generate_config
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "generate_config" in ready_names, (
            f"generate_config should be READY after valid requirements, got: {ready_names}"
        )

        # --- Continue to delivery (approved config, tests pass) -----------
        complete_user_task(workflow, "generate_config", {"config_action": "approved"})
        complete_user_task(workflow, "review_config", {})
        complete_user_task(workflow, "run_tests", {"tests_passed": True})
        complete_user_task(workflow, "handoff_client", {})

        # --- Assertions ---------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "fill_gaps" in names, "fill_gaps must have been completed"
        assert "deploy_production" in names, "deploy_production must have run"
        assert "set_delivered" in names, "set_delivered must have run"
        assert "end_delivered" in names, "end_delivered end event must be reached"

        assert workflow.data.get("status") == "delivered", (
            "Final status should be 'delivered'"
        )


class TestConfigRevisionLoop:
    """
    Config needs revision after first review → loop back to generate_config →
    review approved on second pass → continue to delivery.

    Verifies: review_config completed at least twice (by checking generate_config
    ran more than once or verifying config_action transitions), fix_config NOT run.
    """

    def test_config_revision_loop(self):
        workflow = load_workflow()

        # --- Onboard, Ingest, Gather (valid), Validate -------------------
        complete_user_task(workflow, "onboard_client", {})
        complete_user_task(workflow, "ingest_knowledge", {})
        complete_user_task(workflow, "gather_requirements", {"requirements_valid": True})
        complete_user_task(workflow, "validate_requirements", {})

        # --- Generate Config (first pass) ---------------------------------
        # Set config_action="revise" so config_approved_gateway loops back.
        complete_user_task(workflow, "generate_config", {"config_action": "revise"})

        # --- Review Config (first pass - revision requested) --------------
        complete_user_task(workflow, "review_config", {})

        # Engine routes through config_approved_gateway [config_action=="revise"]
        # and loops back to generate_config
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "generate_config" in ready_names, (
            f"generate_config should be READY after revision request, got: {ready_names}"
        )

        # --- Generate Config (second pass) --------------------------------
        # Now set config_action="approved" so the gateway takes the default branch.
        complete_user_task(workflow, "generate_config", {"config_action": "approved"})

        # --- Review Config (second pass - approved) -----------------------
        complete_user_task(workflow, "review_config", {})

        # Engine routes through config_approved_gateway [default/approved]
        # auto-runs deploy_uat, stops at run_tests
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "run_tests" in ready_names, (
            f"run_tests should be READY after config approved, got: {ready_names}"
        )

        # --- Continue to delivery -----------------------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})
        complete_user_task(workflow, "handoff_client", {})

        # --- Assertions ---------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        # review_config appears twice in completed tasks (second pass completed it again)
        review_completions = [n for n in names if n == "review_config"]
        assert len(review_completions) >= 2, (
            f"review_config should have been completed at least twice (revision loop), "
            f"found {len(review_completions)} times"
        )
        assert "deploy_uat" in names, "deploy_uat must have run after approval"
        assert "fix_config" not in names, "fix_config must NOT run in config revision loop"
        assert "set_delivered" in names, "set_delivered must have run"

        assert workflow.data.get("status") == "delivered", (
            "Final status should be 'delivered'"
        )


class TestTestFailRetry:
    """
    Tests fail on first UAT pass → fix_config → redeploy UAT → tests pass →
    deploy production → delivered.

    Verifies: fix_config completed, deployed_to_prod=True, status=="delivered".
    """

    def test_test_fail_retry(self):
        workflow = load_workflow()

        # --- Onboard, Ingest, Gather (valid), Validate -------------------
        complete_user_task(workflow, "onboard_client", {})
        complete_user_task(workflow, "ingest_knowledge", {})
        complete_user_task(workflow, "gather_requirements", {"requirements_valid": True})
        complete_user_task(workflow, "validate_requirements", {})

        # --- Generate Config and Review (approved) -----------------------
        complete_user_task(workflow, "generate_config", {"config_action": "approved"})
        complete_user_task(workflow, "review_config", {})

        # Engine auto-runs deploy_uat, stops at run_tests

        # --- Run Tests: FAIL (default branch) ----------------------------
        # Do NOT set tests_passed=True so gateway defaults to fix_config.
        complete_user_task(workflow, "run_tests", {"tests_passed": False})

        # Engine routes through tests_pass_gateway [default/fail]
        # and stops at fix_config (userTask)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "fix_config" in ready_names, (
            f"fix_config should be READY after test failure, got: {ready_names}"
        )

        # --- Fix Config ---------------------------------------------------
        complete_user_task(workflow, "fix_config", {})

        # Engine loops back through deploy_uat (scriptTask), stops at run_tests
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "run_tests" in ready_names, (
            f"run_tests should be READY after fix_config and re-deploy, got: {ready_names}"
        )

        # --- Run Tests: PASS (second attempt) ----------------------------
        complete_user_task(workflow, "run_tests", {"tests_passed": True})

        # Engine auto-runs deploy_production, generate_docs, stops at handoff_client

        # --- Handoff Client -----------------------------------------------
        complete_user_task(workflow, "handoff_client", {})

        # --- Assertions ---------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after retry"

        names = completed_spec_names(workflow)
        assert "fix_config" in names, "fix_config must have been completed"
        assert "deploy_production" in names, "deploy_production must have run after tests passed"
        assert "generate_docs" in names, "generate_docs must have run"
        assert "set_delivered" in names, "set_delivered must have run"
        assert "end_delivered" in names, "end_delivered end event must be reached"

        assert workflow.data.get("deployed_to_prod") is True, (
            "deploy_production should have set deployed_to_prod=True"
        )
        assert workflow.data.get("status") == "delivered", (
            "Final status should be 'delivered'"
        )
