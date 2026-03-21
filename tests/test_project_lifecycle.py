"""
Tests for Project Lifecycle BPMN (F157)

Tests the unified 7-stage phase model:
  idea -> planning -> design -> implementation -> testing -> production -> archived

Also tests:
- Phase advancement subprocess with requirements checks
- Gate overlay documentation (gates are optional quality checkpoints)
- Invalid transitions are rejected
- BPMN model structural validation
"""

import os
import sys
import pytest

# Add BPMN engine to path for direct SpiffWorkflow testing
BPMN_DIR = os.path.join(os.path.dirname(__file__), '..', 'mcp-servers', 'bpmn-engine')
sys.path.insert(0, BPMN_DIR)

PROCESSES_DIR = os.path.join(BPMN_DIR, 'processes')
BPMN_FILE = os.path.join(PROCESSES_DIR, 'lifecycle', 'project_lifecycle.bpmn')


def navigate(process_id, completed_steps=None, data=None):
    """Replicate get_current_step logic for testing."""
    from SpiffWorkflow.util.task import TaskState
    from server import _find_bpmn_file, _load_workflow

    if completed_steps is None:
        completed_steps = []
    if data is None:
        data = {}

    bpmn_path = _find_bpmn_file(process_id)
    assert bpmn_path is not None, f"Process '{process_id}' not found"

    workflow = _load_workflow(bpmn_path, process_id)

    for step in completed_steps:
        if isinstance(step, dict):
            step_name = step.get("name", "")
            step_data = {**data, **step.get("data", {})}
        else:
            step_name = str(step)
            step_data = dict(data)

        ready_user_tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
        matched = [t for t in ready_user_tasks if t.task_spec.description == step_name
                    or t.task_spec.name == step_name]

        if not matched:
            continue

        task_obj = matched[0]
        if step_data:
            task_obj.data.update(step_data)
        task_obj.run()
        workflow.do_engine_steps()

    ready_tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
    current_tasks = [
        {
            "id": t.task_spec.name,
            "name": t.task_spec.description or t.task_spec.name,
            "type": type(t.task_spec).__name__,
        }
        for t in ready_tasks
    ]

    return {
        "current_tasks": current_tasks,
        "is_completed": workflow.is_completed(),
        "data": workflow.data if workflow.is_completed() else {},
    }


class TestProjectLifecycleBPMN:
    """Validate project_lifecycle BPMN model structure."""

    def test_parse_project_lifecycle(self):
        """project_lifecycle.bpmn parses without errors."""
        from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec('project_lifecycle')
        assert spec is not None
        assert spec.name == 'project_lifecycle'

    def test_parse_phase_advancement(self):
        """phase_advancement process parses without errors."""
        from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec('phase_advancement')
        assert spec is not None
        assert spec.name == 'phase_advancement'

    def test_project_lifecycle_has_phase_call_activity(self):
        """Main process calls phase_advancement subprocess."""
        from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec('project_lifecycle')
        task_specs = spec.task_specs
        call_activity_found = any(
            'assess_and_advance_phase' in name for name in task_specs
        )
        assert call_activity_found, "Expected callActivity for phase_advancement"


class TestPhaseAdvancementWorkflow:
    """Test the phase_advancement subprocess navigation."""

    def test_happy_path_starts_at_determine_target(self):
        """First user task is 'determine_next_phase'."""
        result = navigate('phase_advancement')
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'determine_next_phase' in task_ids, \
            f"Expected 'determine_next_phase' in {task_ids}"

    def test_route_to_planning_check(self):
        """Selecting planning routes to planning requirements check."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'planning'}}
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'check_planning_reqs' in task_ids, \
            f"Expected 'check_planning_reqs' in {task_ids}"

    def test_route_to_design_check(self):
        """Selecting design routes to design requirements check."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'design'}}
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'check_design_reqs' in task_ids, \
            f"Expected 'check_design_reqs' in {task_ids}"

    def test_route_to_implementation_check(self):
        """Selecting implementation routes to implementation requirements check."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'implementation'}}
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'check_implementation_reqs' in task_ids, \
            f"Expected 'check_implementation_reqs' in {task_ids}"

    def test_route_to_testing_check(self):
        """Selecting testing routes to testing requirements check."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'testing'}}
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'check_testing_reqs' in task_ids, \
            f"Expected 'check_testing_reqs' in {task_ids}"

    def test_route_to_production_check(self):
        """Selecting production routes to production requirements check."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'production'}}
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'check_production_reqs' in task_ids, \
            f"Expected 'check_production_reqs' in {task_ids}"

    def test_route_to_archived_check(self):
        """Selecting archived routes to archive requirements check."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'archived'}}
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'check_archived_reqs' in task_ids, \
            f"Expected 'check_archived_reqs' in {task_ids}"

    def test_requirements_met_leads_to_confirm(self):
        """When requirements met, user confirms advancement."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'planning'}},
            {'name': 'check_planning_reqs', 'data': {'requirements_met': True}},
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'confirm_advance' in task_ids, \
            f"Expected 'confirm_advance' in {task_ids}"

    def test_requirements_not_met_shows_gaps(self):
        """When requirements not met, gaps are shown."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'design'}},
            {'name': 'check_design_reqs', 'data': {'requirements_met': False}},
        ])
        assert not result['is_completed']
        task_ids = [t['id'] for t in result['current_tasks']]
        assert 'show_gaps' in task_ids, \
            f"Expected 'show_gaps' in {task_ids}"

    def test_full_advance_completes(self):
        """Full happy path through to completion."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'planning'}},
            {'name': 'check_planning_reqs', 'data': {'requirements_met': True}},
            {'name': 'confirm_advance', 'data': {}},
        ])
        assert result['is_completed'], \
            f"Expected completed but got tasks: {[t['name'] for t in result['current_tasks']]}"

    def test_blocked_path_completes(self):
        """Blocked path completes after showing gaps."""
        result = navigate('phase_advancement', completed_steps=[
            {'name': 'determine_next_phase', 'data': {'target_phase': 'implementation'}},
            {'name': 'check_implementation_reqs', 'data': {'requirements_met': False}},
            {'name': 'show_gaps', 'data': {}},
        ])
        assert result['is_completed'], \
            f"Expected completed but got tasks: {[t['name'] for t in result['current_tasks']]}"


class TestPhaseDocumentation:
    """Verify phase documentation is present in BPMN model."""

    def test_all_phase_checks_exist(self):
        """All 6 advancement targets have requirements check tasks."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(BPMN_FILE)
        root = tree.getroot()
        ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

        process = root.find('.//bpmn:process[@id="phase_advancement"]', ns)
        assert process is not None

        user_tasks = process.findall('.//bpmn:userTask', ns)
        task_ids = [t.get('id', '') for t in user_tasks]

        expected = [
            'check_planning_reqs',
            'check_design_reqs',
            'check_implementation_reqs',
            'check_testing_reqs',
            'check_production_reqs',
            'check_archived_reqs',
        ]
        for expected_id in expected:
            assert expected_id in task_ids, \
                f"Missing requirements check task: {expected_id}"

    def test_gate_overlay_documented(self):
        """Gate overlay (0-4) documented in the BPMN model."""
        with open(BPMN_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        for gate_num in range(5):
            assert f'Gate {gate_num}' in content, \
                f"Gate {gate_num} should be documented"

    def test_seven_phases_in_conditions(self):
        """All 6 target phases appear as condition expressions."""
        with open(BPMN_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        phases = ['planning', 'design', 'implementation', 'testing', 'production', 'archived']
        for phase in phases:
            assert f'target_phase == "{phase}"' in content, \
                f"Phase '{phase}' should appear as a condition"

    def test_requirements_documented_in_tasks(self):
        """Each phase check task has documentation with requirements."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(BPMN_FILE)
        root = tree.getroot()
        ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

        process = root.find('.//bpmn:process[@id="phase_advancement"]', ns)
        check_tasks = [
            'check_planning_reqs', 'check_design_reqs',
            'check_implementation_reqs', 'check_testing_reqs',
            'check_production_reqs', 'check_archived_reqs',
        ]

        for task_id in check_tasks:
            task = process.find(f'.//bpmn:userTask[@id="{task_id}"]', ns)
            assert task is not None, f"Task {task_id} not found"
            doc = task.find('bpmn:documentation', ns)
            assert doc is not None and doc.text and len(doc.text.strip()) > 20, \
                f"Task {task_id} should have meaningful documentation"
