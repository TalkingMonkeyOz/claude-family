"""
Tests for the Skill Lifecycle BPMN process (skill_lifecycle).

Models create and update paths for skills:
  CREATE: scope → permission → insert → version 1 → deploy → validate
  UPDATE: lookup → snapshot → increment → update → deploy → validate

Test paths:
  1. Process parses correctly with all expected elements
  2. Happy path: create a new skill
  3. Happy path: update an existing skill
  4. Permission denied: non-claude-family project blocked from creating global skills
  5. Update path: skill not found
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "skill_lifecycle.bpmn")
)
PROCESS_ID = "skill_lifecycle"


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


class TestSkillLifecycleModelElements:
    """Verify the process parses and all expected elements exist."""

    def test_process_parses(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        assert spec is not None
        assert spec.name == "skill_lifecycle"

    def test_all_elements_present(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())

        # Gateways
        assert "action_gw" in names
        assert "permission_gw" in names
        assert "found_gw" in names
        assert "merge_to_deploy" in names

        # Create path
        assert "determine_scope" in names
        assert "permission_check" in names
        assert "insert_skill" in names
        assert "create_initial_version" in names

        # Update path
        assert "lookup_skill" in names
        assert "snapshot_version" in names
        assert "increment_version" in names
        assert "update_content" in names

        # Common tail
        assert "deploy_file" in names
        assert "validate_deployment" in names

        # End events
        assert "end_success" in names
        assert "end_permission_denied" in names
        assert "end_not_found" in names


class TestSkillLifecycleCreateHappyPath:
    """Create a new skill: scope → permission → insert → version → deploy → validate."""

    def test_create_project_skill(self):
        wf = load_workflow(initial_data={
            "action": "create",
            "scope": "project",
            "requesting_project": "some-project",
            "skill_name": "my-skill",
            "skill_id": None,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Create path executed
        assert "determine_scope" in names
        assert "permission_check" in names
        assert "insert_skill" in names
        assert "create_initial_version" in names

        # Common tail executed
        assert "deploy_file" in names
        assert "validate_deployment" in names
        assert "end_success" in names

        # Update path NOT executed
        assert "lookup_skill" not in names
        assert "snapshot_version" not in names

        # Data assertions
        assert wf.data.get("scope_determined") is True
        assert wf.data.get("permission_granted") is True
        assert wf.data.get("skill_inserted") is True
        assert wf.data.get("version_created") is True
        assert wf.data.get("version_number") == 1
        assert wf.data.get("file_deployed") is True
        assert wf.data.get("deployment_valid") is True

    def test_create_global_skill_by_claude_family(self):
        wf = load_workflow(initial_data={
            "action": "create",
            "scope": "global",
            "requesting_project": "claude-family",
            "skill_name": "global-skill",
            "skill_id": None,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_success" in names
        assert "end_permission_denied" not in names
        assert wf.data.get("permission_granted") is True

    def test_create_command_skill(self):
        wf = load_workflow(initial_data={
            "action": "create",
            "scope": "command",
            "requesting_project": "any-project",
            "skill_name": "cmd-skill",
            "skill_id": None,
        })

        assert wf.is_completed()
        assert "end_success" in completed_spec_names(wf)

    def test_create_agent_skill(self):
        wf = load_workflow(initial_data={
            "action": "create",
            "scope": "agent",
            "requesting_project": "any-project",
            "skill_name": "agent-skill",
            "skill_id": None,
        })

        assert wf.is_completed()
        assert "end_success" in completed_spec_names(wf)


class TestSkillLifecycleUpdateHappyPath:
    """Update an existing skill: lookup → snapshot → increment → update → deploy → validate."""

    def test_update_existing_skill(self):
        wf = load_workflow(initial_data={
            "action": "update",
            "scope": "project",
            "skill_name": "existing-skill",
            "skill_id": "some-uuid",
            "current_version": 2,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Update path executed
        assert "lookup_skill" in names
        assert "snapshot_version" in names
        assert "increment_version" in names
        assert "update_content" in names

        # Common tail executed
        assert "deploy_file" in names
        assert "validate_deployment" in names
        assert "end_success" in names

        # Create path NOT executed
        assert "determine_scope" not in names
        assert "insert_skill" not in names

        # Data assertions
        assert wf.data.get("skill_found") is True
        assert wf.data.get("version_snapshot_created") is True
        assert wf.data.get("version_incremented") is True
        assert wf.data.get("content_updated") is True
        assert wf.data.get("file_deployed") is True
        assert wf.data.get("deployment_valid") is True


class TestSkillLifecyclePermissionDenied:
    """Non-claude-family project blocked from creating global skills."""

    def test_non_claude_family_cannot_create_global(self):
        wf = load_workflow(initial_data={
            "action": "create",
            "scope": "global",
            "requesting_project": "some-other-project",
            "skill_name": "sneaky-global-skill",
            "skill_id": None,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Permission denied path
        assert "determine_scope" in names
        assert "permission_check" in names
        assert "end_permission_denied" in names

        # Should NOT proceed to insert or deploy
        assert "insert_skill" not in names
        assert "deploy_file" not in names
        assert "end_success" not in names

        assert wf.data.get("permission_granted") is False


class TestSkillLifecycleUpdateNotFound:
    """Update path when skill does not exist."""

    def test_skill_not_found(self):
        wf = load_workflow(initial_data={
            "action": "update",
            "scope": "project",
            "skill_name": "nonexistent-skill",
            "skill_id": None,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "lookup_skill" in names
        assert "end_not_found" in names

        # Should NOT proceed to snapshot or deploy
        assert "snapshot_version" not in names
        assert "deploy_file" not in names
        assert "end_success" not in names

        assert wf.data.get("skill_found") is False
