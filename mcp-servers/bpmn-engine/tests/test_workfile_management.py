"""
Tests for workfile_management.bpmn — Workfile Management Process.

Workfiles are cross-session, component-scoped working context documents.
The filing cabinet metaphor: project = cabinet, component = drawer, title = file folder.

Paths tested:
  1. Stash (default): identify(stash) → validate_type → resolve_project → upsert_workfile
                      → generate_embedding → link_session → end
  2. Unstash: identify(unstash) → resolve_project_unstash → query_workfiles
              → update_access_stats → end
  3. List: identify(list) → resolve_project_list → query_components → end
  4. Search: identify(search) → generate_query_embedding → search_embeddings → end

Key notes:
  - action_gw default (no condition) routes to validate_type (stash path)
  - action == "unstash" → resolve_project_unstash
  - action == "list"    → resolve_project_list
  - action == "search"  → generate_query_embedding
  - All paths converge at end_merge → end

Implementation: mcp-servers/project-tools/server_v2.py + claude.project_workfiles table
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "workfile_management.bpmn")
)
PROCESS_ID = "workfile_management"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    if initial_data:
        start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
        assert start_tasks, "Could not find BPMN start event"
        start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


def get_ready_user_tasks(wf: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return wf.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """Find named READY user task, merge data, run it, advance engine."""
    ready = get_ready_user_tasks(wf)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    wf.do_engine_steps()


# ---------------------------------------------------------------------------
# Test 1: Stash Path (default)
# ---------------------------------------------------------------------------

class TestStashPath:
    """
    Stash path — default gateway branch (action_gw has no condition on flow_stash):
    identify(stash) → validate_type → resolve_project → upsert_workfile
    → generate_embedding → link_session → end_merge → end.
    """

    def test_stash_new_workfile(self):
        wf = load_workflow()

        # identify_action is the first userTask after start
        assert "identify_action" in [t.task_spec.name for t in get_ready_user_tasks(wf)]

        # action="stash" routes via the default gateway branch
        complete_user_task(wf, "identify_action", {"action": "stash"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # All stash steps must have run
        assert "validate_type" in names
        assert "resolve_project" in names
        assert "upsert_workfile" in names
        assert "generate_embedding" in names
        assert "link_session" in names
        assert "end_merge" in names
        assert "end" in names

        # No steps from other paths
        assert "resolve_project_unstash" not in names
        assert "query_workfiles" not in names
        assert "update_access_stats" not in names
        assert "resolve_project_list" not in names
        assert "query_components" not in names
        assert "generate_query_embedding" not in names
        assert "search_embeddings" not in names

    def test_stash_data_flow(self):
        """Script tasks must set their sentinel flags in workflow.data."""
        wf = load_workflow()
        complete_user_task(wf, "identify_action", {"action": "stash"})

        assert wf.is_completed()
        assert wf.data.get("type_valid") is True
        assert wf.data.get("workfile_upserted") is True
        assert wf.data.get("embedding_generated") is True
        assert wf.data.get("session_linked") is True


# ---------------------------------------------------------------------------
# Test 2: Unstash Path
# ---------------------------------------------------------------------------

class TestUnstashPath:
    """
    Unstash path (action == "unstash"):
    identify(unstash) → resolve_project_unstash → query_workfiles
    → update_access_stats → end_merge → end.
    """

    def test_unstash_by_component(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "unstash"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # All unstash steps must have run
        assert "resolve_project_unstash" in names
        assert "query_workfiles" in names
        assert "update_access_stats" in names
        assert "end_merge" in names
        assert "end" in names

        # No steps from other paths
        assert "validate_type" not in names
        assert "upsert_workfile" not in names
        assert "generate_embedding" not in names
        assert "link_session" not in names
        assert "query_components" not in names
        assert "generate_query_embedding" not in names
        assert "search_embeddings" not in names

    def test_unstash_data_flow(self):
        """update_access_stats script task must set access_updated=True."""
        wf = load_workflow()
        complete_user_task(wf, "identify_action", {"action": "unstash"})

        assert wf.is_completed()
        assert wf.data.get("access_updated") is True
        assert wf.data.get("workfiles_retrieved") is True


# ---------------------------------------------------------------------------
# Test 3: List Path
# ---------------------------------------------------------------------------

class TestListPath:
    """
    List path (action == "list"):
    identify(list) → resolve_project_list → query_components → end_merge → end.
    """

    def test_list_components(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "list"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # All list steps must have run
        assert "resolve_project_list" in names
        assert "query_components" in names
        assert "end_merge" in names
        assert "end" in names

        # No steps from other paths
        assert "validate_type" not in names
        assert "upsert_workfile" not in names
        assert "generate_embedding" not in names
        assert "link_session" not in names
        assert "resolve_project_unstash" not in names
        assert "query_workfiles" not in names
        assert "update_access_stats" not in names
        assert "generate_query_embedding" not in names
        assert "search_embeddings" not in names

        # Script task sentinel
        assert wf.data.get("components_listed") is True


# ---------------------------------------------------------------------------
# Test 4: Search Path
# ---------------------------------------------------------------------------

class TestSearchPath:
    """
    Search path (action == "search"):
    identify(search) → generate_query_embedding → search_embeddings → end_merge → end.
    """

    def test_search_workfiles(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "search"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # All search steps must have run
        assert "generate_query_embedding" in names
        assert "search_embeddings" in names
        assert "end_merge" in names
        assert "end" in names

        # No steps from other paths
        assert "validate_type" not in names
        assert "upsert_workfile" not in names
        assert "link_session" not in names
        assert "resolve_project_unstash" not in names
        assert "query_workfiles" not in names
        assert "update_access_stats" not in names
        assert "resolve_project_list" not in names
        assert "query_components" not in names

        # Script task sentinels
        assert wf.data.get("query_embedding_generated") is True
        assert wf.data.get("search_results_found") is True
