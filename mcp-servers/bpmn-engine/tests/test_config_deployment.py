"""
Tests for the Config Deployment BPMN process.

Uses SpiffWorkflow 3.x API directly against the config_deployment.bpmn definition.
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
  start → identify_config_change → scope_gateway
      ["global"]          → update_global_template → scope_merge
      [default/"project"] → update_workspace_config → scope_merge
  → generate_settings → deploy_components → validate_deployment
  → validation_gateway
      ["invalid"]        → rollback → end_rolled_back
      [default/"valid"]  → end_deployed
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "config_deployment.bpmn")
)
PROCESS_ID = "config_deployment"


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


class TestProjectConfigValid:
    """
    Project-scope config change: identify (scope=project) -> update_workspace_config
    -> generate_settings -> deploy_components -> validate (valid) -> end_deployed.

    Verifies: workspace_updated, settings_generated, components_deployed,
              update_global_template NOT executed, end_deployed reached.
    """

    def test_project_config_valid(self):
        workflow = load_workflow()

        # --- Identify Config Change (project scope) -------------------------
        # config_scope="project" routes scope_gateway to its default branch
        # (flow_project -> update_workspace_config).
        # validation_result="valid" is pre-loaded so the validation gateway
        # takes its default branch (flow_valid -> end_deployed).
        complete_user_task(
            workflow,
            "identify_config_change",
            {"config_scope": "project", "validation_result": "valid"},
        )

        # Engine should advance through update_workspace_config, scope_merge,
        # generate_settings, deploy_components, then stop at validate_deployment.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "validate_deployment" in ready_names, (
            f"validate_deployment should be READY after deployment, got: {ready_names}"
        )

        # --- Validate Deployment (valid) ------------------------------------
        complete_user_task(workflow, "validate_deployment", {"validation_result": "valid"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "update_workspace_config" in names, (
            "update_workspace_config must have run on the project path"
        )
        assert "update_global_template" not in names, (
            "update_global_template must NOT run on the project path"
        )
        assert "generate_settings" in names, "generate_settings script must have run"
        assert "deploy_components" in names, "deploy_components script must have run"
        assert "end_deployed" in names, "end_deployed end event must be reached"
        assert "end_rolled_back" not in names, "end_rolled_back must NOT be reached"
        assert "rollback" not in names, "rollback must NOT run on the valid path"

        assert workflow.data.get("db_updated") is True, (
            "update_workspace_config should have set db_updated=True"
        )
        assert workflow.data.get("workspace_updated") is True, (
            "update_workspace_config should have set workspace_updated=True"
        )
        assert workflow.data.get("settings_generated") is True, (
            "generate_settings should have set settings_generated=True"
        )
        assert workflow.data.get("components_deployed") is True, (
            "deploy_components should have set components_deployed=True"
        )


class TestGlobalConfigValid:
    """
    Global-scope config change: identify (scope=global) -> update_global_template
    -> generate_settings -> deploy_components -> validate (valid) -> end_deployed.

    Verifies: template_updated, settings_generated, components_deployed,
              update_workspace_config NOT executed, end_deployed reached.
    """

    def test_global_config_valid(self):
        workflow = load_workflow()

        # --- Identify Config Change (global scope) --------------------------
        # config_scope="global" routes scope_gateway to flow_global
        # (conditioned: config_scope == "global") -> update_global_template.
        complete_user_task(
            workflow,
            "identify_config_change",
            {"config_scope": "global", "validation_result": "valid"},
        )

        # Engine should advance through update_global_template, scope_merge,
        # generate_settings, deploy_components, then stop at validate_deployment.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "validate_deployment" in ready_names, (
            f"validate_deployment should be READY after deployment, got: {ready_names}"
        )

        # --- Validate Deployment (valid) ------------------------------------
        complete_user_task(workflow, "validate_deployment", {"validation_result": "valid"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "update_global_template" in names, (
            "update_global_template must have run on the global path"
        )
        assert "update_workspace_config" not in names, (
            "update_workspace_config must NOT run on the global path"
        )
        assert "generate_settings" in names, "generate_settings script must have run"
        assert "deploy_components" in names, "deploy_components script must have run"
        assert "end_deployed" in names, "end_deployed end event must be reached"
        assert "end_rolled_back" not in names, "end_rolled_back must NOT be reached"
        assert "rollback" not in names, "rollback must NOT run on the valid path"

        assert workflow.data.get("db_updated") is True, (
            "update_global_template should have set db_updated=True"
        )
        assert workflow.data.get("template_updated") is True, (
            "update_global_template should have set template_updated=True"
        )
        assert workflow.data.get("settings_generated") is True, (
            "generate_settings should have set settings_generated=True"
        )
        assert workflow.data.get("components_deployed") is True, (
            "deploy_components should have set components_deployed=True"
        )


class TestConfigInvalidRollback:
    """
    Deployment validation fails: identify (scope=project) -> update_workspace_config
    -> generate_settings -> deploy_components -> validate (invalid)
    -> rollback -> end_rolled_back.

    Verifies: rollback_executed, end_rolled_back reached, end_deployed NOT reached.
    """

    def test_config_invalid_rollback(self):
        workflow = load_workflow()

        # --- Identify Config Change (project scope) -------------------------
        # Use project scope (default path) to keep the test focused on the
        # validation failure, not the scope branch.
        complete_user_task(
            workflow,
            "identify_config_change",
            {"config_scope": "project"},
        )

        # Engine should stop at validate_deployment.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "validate_deployment" in ready_names, (
            f"validate_deployment should be READY after deployment, got: {ready_names}"
        )

        # Intermediate state: generate and deploy should have already run.
        names_before_validate = completed_spec_names(workflow)
        assert "generate_settings" in names_before_validate, (
            "generate_settings should have already completed before validation"
        )
        assert "deploy_components" in names_before_validate, (
            "deploy_components should have already completed before validation"
        )

        # --- Validate Deployment (invalid) ---------------------------------
        # validation_result="invalid" routes validation_gateway to flow_invalid
        # (conditioned: validation_result == "invalid") -> rollback.
        complete_user_task(workflow, "validate_deployment", {"validation_result": "invalid"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after rollback"

        names = completed_spec_names(workflow)
        assert "rollback" in names, "rollback script must have run on the invalid path"
        assert "end_rolled_back" in names, "end_rolled_back end event must be reached"
        assert "end_deployed" not in names, "end_deployed must NOT be reached after rollback"

        assert workflow.data.get("rollback_executed") is True, (
            "rollback should have set rollback_executed=True"
        )
        # Rollback script resets these flags to False
        assert workflow.data.get("settings_generated") is False, (
            "rollback should have reset settings_generated to False"
        )
        assert workflow.data.get("components_deployed") is False, (
            "rollback should have reset components_deployed to False"
        )
