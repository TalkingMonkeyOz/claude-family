"""
Tests for the Cross-System Linking BPMN processes.

Two processes in one file:
  1. cross_system_linking: Manual resource linking (link, query, unlink)
  2. wcc_context_assembly: Auto context assembly via resource links

Implementation file:
  processes/infrastructure/cross_system_linking.bpmn
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


_BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "infrastructure",
        "cross_system_linking.bpmn"
    )
)


def _load(process_id, data_overrides: dict = None) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(_BPMN_FILE)
    spec = parser.get_spec(process_id)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_DEFAULTS.get(process_id, {}))
    if data_overrides:
        initial_data.update(data_overrides)
    start_events = {"start", "wcc_start"}
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name in start_events]
    assert start_tasks, f"Could not find start event for {process_id}"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _ready_names(wf):
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.READY, manual=True)]


def _complete(wf, task_name, data=None):
    ready = wf.get_tasks(state=TaskState.READY, manual=True)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    if data:
        matches[0].data.update(data)
    matches[0].run()
    wf.do_engine_steps()


def _completed_names(wf):
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# Default data for each process
_DEFAULTS = {
    "cross_system_linking": {
        "action": "",              # default -> link
        "force_invalid_resource": False,
        "force_link_exists": False,
        "force_no_links": False,
        "resources_valid": True,
        "link_exists": False,
        "links_found": True,
        "link_count": 3,
        "link_action": "",
    },
    "wcc_context_assembly": {
        "force_no_activity": False,
        "activity_found": True,
        "activity_id": "test_uuid",
        "budget": 1000,
    },
}


# ===========================================================================
# PROCESS 1: cross_system_linking
# ===========================================================================

class TestLinkNewResource:
    """Default action: create a new link between two resources."""

    def test_link_happy_path(self):
        wf = _load("cross_system_linking")

        assert "identify_resources" in _ready_names(wf)
        _complete(wf, "identify_resources")

        # scriptTasks auto-run: validate, check_existing, create_new_link
        assert wf.is_completed()
        names = _completed_names(wf)
        assert "validate_resources" in names
        assert "check_existing_link" in names
        assert "create_new_link" in names
        assert "end_linked" in names
        assert "update_existing_link" not in names


class TestLinkExistingUpdate:
    """When link already exists, update it instead of creating."""

    def test_existing_link_updates(self):
        wf = _load("cross_system_linking", {"force_link_exists": True})
        _complete(wf, "identify_resources")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "update_existing_link" in names
        assert "create_new_link" not in names
        assert "end_linked" in names


class TestLinkInvalidResource:
    """When a resource doesn't exist, end with error."""

    def test_invalid_resource_blocked(self):
        wf = _load("cross_system_linking", {"force_invalid_resource": True})
        _complete(wf, "identify_resources")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "end_invalid" in names
        assert "check_existing_link" not in names


class TestQueryLinks:
    """Query action returns linked resources."""

    def test_query_with_results(self):
        wf = _load("cross_system_linking", {"action": "query"})

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "query_links" in names
        assert "end_query_results" in names
        assert "identify_resources" not in names

    def test_query_no_results(self):
        wf = _load("cross_system_linking", {"action": "query", "force_no_links": True})

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "query_links" in names
        assert "end_no_links" in names


class TestUnlink:
    """Unlink action removes a link."""

    def test_unlink(self):
        wf = _load("cross_system_linking", {"action": "unlink"})

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "remove_link" in names
        assert "end_unlinked" in names
        assert "identify_resources" not in names


# ===========================================================================
# PROCESS 2: wcc_context_assembly
# ===========================================================================

class TestWccHappyPath:
    """Activity detected, context assembled from linked resources."""

    def test_context_assembly_happy_path(self):
        wf = _load("wcc_context_assembly")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "detect_activity" in names
        assert "query_resource_links" in names
        assert "allocate_budget" in names
        assert "fetch_linked_content" in names
        assert "assemble_context" in names
        assert "end_context_ready" in names


class TestWccNoActivity:
    """No activity matched, early exit."""

    def test_no_activity_exits_early(self):
        wf = _load("wcc_context_assembly", {"force_no_activity": True})

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "detect_activity" in names
        assert "end_no_activity" in names
        assert "query_resource_links" not in names


class TestProcessStructure:
    """Both processes have expected elements."""

    def test_cross_system_linking_has_three_actions(self):
        parser = BpmnParser()
        parser.add_bpmn_file(_BPMN_FILE)
        spec = parser.get_spec("cross_system_linking")
        task_names = set(spec.task_specs)
        assert "identify_resources" in task_names
        assert "query_links" in task_names
        assert "remove_link" in task_names

    def test_wcc_has_six_sources_pipeline(self):
        parser = BpmnParser()
        parser.add_bpmn_file(_BPMN_FILE)
        spec = parser.get_spec("wcc_context_assembly")
        task_names = set(spec.task_specs)
        assert "detect_activity" in task_names
        assert "query_resource_links" in task_names
        assert "allocate_budget" in task_names
        assert "fetch_linked_content" in task_names
        assert "assemble_context" in task_names
