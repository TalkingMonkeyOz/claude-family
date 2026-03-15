"""
Tests for the Config Update BPMN process (config_update).

Models the update_config() MCP tool lifecycle:
  validate → version → update → deploy → audit

Test paths:
  1. Happy path: valid component → version → update → deploy → audit → success
  2. Invalid component: validation fails → end_invalid
  3. All model elements exist
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "config_update.bpmn")
)
PROCESS_ID = "config_update"


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    if initial_data:
        start_tasks = wf.get_tasks(state=TaskState.READY)
        for t in start_tasks:
            t.data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


class TestConfigUpdateHappyPath:
    """Valid component → version → update → deploy → audit → success."""

    def test_valid_skill_update(self):
        wf = load_workflow(initial_data={
            "component_type": "skill",
            "component_found": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "validate_component" in names
        assert "create_version" in names
        assert "update_content" in names
        assert "deploy_file" in names
        assert "log_audit" in names
        assert "end_success" in names
        assert "end_invalid" not in names

        assert wf.data.get("validated") is True
        assert wf.data.get("version_created") is True
        assert wf.data.get("content_updated") is True
        assert wf.data.get("file_deployed") is True
        assert wf.data.get("audit_logged") is True

    def test_valid_rule_update(self):
        wf = load_workflow(initial_data={
            "component_type": "rule",
            "component_found": True,
        })
        assert wf.is_completed()
        assert "end_success" in completed_spec_names(wf)

    def test_valid_instruction_update(self):
        wf = load_workflow(initial_data={
            "component_type": "instruction",
            "component_found": True,
        })
        assert wf.is_completed()
        assert "end_success" in completed_spec_names(wf)

    def test_valid_claude_md_update(self):
        wf = load_workflow(initial_data={
            "component_type": "claude_md",
            "component_found": True,
        })
        assert wf.is_completed()
        assert "end_success" in completed_spec_names(wf)


class TestConfigUpdateInvalid:
    """Invalid component → end_invalid."""

    def test_component_not_found(self):
        wf = load_workflow(initial_data={
            "component_type": "skill",
            "component_found": False,
        })
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_invalid" in names
        assert "create_version" not in names
        assert "end_success" not in names

    def test_invalid_component_type(self):
        wf = load_workflow(initial_data={
            "component_type": "invalid_type",
            "component_found": True,
        })
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_invalid" in names
        assert "end_success" not in names


class TestConfigUpdateModelElements:
    """Verify all expected elements exist."""

    def test_all_elements_present(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())

        assert "validate_component" in names
        assert "create_version" in names
        assert "update_content" in names
        assert "deploy_file" in names
        assert "log_audit" in names
        assert "valid_gw" in names
        assert "end_success" in names
        assert "end_invalid" in names
