"""
Tests for the Knowledge Graph Lifecycle BPMN process.

Manages the Apache AGE graph layer sitting on top of pgvector knowledge.
Four sub-processes with 9 total execution paths:

Path 1 - Sync (default, AGE already installed):
  identify_action(action="sync") → action_gw(default) → check_age_extension →
  age_installed_gw(default) → ensure_graph → load_knowledge_nodes →
  load_relations_edges → end_merge → end

Path 1b - Sync (AGE not installed):
  identify_action(action="sync") → action_gw(default) → check_age_extension →
  age_installed_gw(age_installed==False) → install_age → ensure_graph →
  load_knowledge_nodes → load_relations_edges → end_merge → end

Path 2 - Query (hits found):
  identify_action(action="query") → pgvector_search →
  hits_found_gw(hits_count > 0) → graph_walk → assemble_context →
  update_access_stats → end_merge → end

Path 2b - Query (no hits):
  identify_action(action="query") → pgvector_search →
  hits_found_gw(default) → end_merge → end

Path 3 - Decay (stale found):
  identify_action(action="decay") → calculate_decay → apply_decay →
  find_stale_subgraphs → stale_found_gw(stale_count > 0) →
  archive_stale → flag_contradictions → end_merge → end

Path 3b - Decay (clean):
  identify_action(action="decay") → calculate_decay → apply_decay →
  find_stale_subgraphs → stale_found_gw(default) → end_merge → end

Path 4 - Review (keep, default):
  identify_action(action="review") → review_flagged →
  review_decision_gw(default) → keep_and_strengthen → end_merge → end

Path 4b - Review (merge):
  identify_action(action="review") → review_flagged(decision="merge") →
  review_decision_gw → merge_duplicates → end_merge → end

Path 4c - Review (delete):
  identify_action(action="review") → review_flagged(decision="delete") →
  review_decision_gw → delete_knowledge → end_merge → end

NOTE: SpiffWorkflow evaluates ALL gateway conditions, so all condition
variables must be defined in the data context. We use DEFAULT_DATA to
ensure this, then override specific values per test.

Implementation: mcp-servers/bpmn-engine/processes/lifecycle/knowledge_graph_lifecycle.bpmn
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "knowledge_graph_lifecycle.bpmn")
)
PROCESS_ID = "knowledge_graph_lifecycle"

# Default data that satisfies all gateway conditions (takes all default paths)
DEFAULT_DATA = {
    "action": "sync",           # action_gw: non-matching → default (sync)
    "age_installed": True,      # age_installed_gw: not False → default (ensure_graph)
    "hits_count": 0,            # hits_found_gw: not > 0 → default (no hits)
    "stale_count": 0,           # stale_found_gw: not > 0 → default (clean)
    "decision": "keep",         # review_decision_gw: non-matching → default (keep)
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(data_overrides: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance with default data."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(wf: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return wf.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(wf: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(wf)]


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


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Path 1: Sync - Default (AGE already installed)
# ---------------------------------------------------------------------------

class TestSyncDefault:
    """Sync path with AGE already installed (all defaults)."""

    def test_sync_default_path(self):
        wf = load_workflow()  # defaults: action="sync", age_installed=True

        complete_user_task(wf, "identify_action", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "check_age_extension" in names
        assert "ensure_graph" in names
        assert "load_knowledge_nodes" in names
        assert "load_relations_edges" in names
        assert "install_age" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 1b: Sync - With AGE Installation
# ---------------------------------------------------------------------------

class TestSyncWithInstall:
    """Sync path where AGE needs to be installed first."""

    def test_sync_with_age_install(self):
        wf = load_workflow(data_overrides={"age_installed": False})

        complete_user_task(wf, "identify_action", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "check_age_extension" in names
        assert "install_age" in names
        assert "ensure_graph" in names
        assert "load_knowledge_nodes" in names
        assert "load_relations_edges" in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 2: Query - Hits Found
# ---------------------------------------------------------------------------

class TestQueryWithHits:
    """Query path with pgvector hits triggering graph walk."""

    def test_query_with_hits(self):
        wf = load_workflow(data_overrides={"hits_count": 5})

        complete_user_task(wf, "identify_action", {"action": "query"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "pgvector_search" in names
        assert "graph_walk" in names
        assert "assemble_context" in names
        assert "update_access_stats" in names
        assert "calculate_decay" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 2b: Query - No Hits
# ---------------------------------------------------------------------------

class TestQueryNoHits:
    """Query path with no pgvector hits (early exit)."""

    def test_query_no_hits(self):
        wf = load_workflow()  # hits_count=0 by default

        complete_user_task(wf, "identify_action", {"action": "query"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "pgvector_search" in names
        assert "graph_walk" not in names
        assert "assemble_context" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 3: Decay - Stale Items Found
# ---------------------------------------------------------------------------

class TestDecayWithStale:
    """Decay path finding stale subgraphs to archive."""

    def test_decay_with_stale_items(self):
        wf = load_workflow(data_overrides={"stale_count": 3})

        complete_user_task(wf, "identify_action", {"action": "decay"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "calculate_decay" in names
        assert "apply_decay" in names
        assert "find_stale_subgraphs" in names
        assert "archive_stale" in names
        assert "flag_contradictions" in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 3b: Decay - Clean
# ---------------------------------------------------------------------------

class TestDecayClean:
    """Decay path with no stale items (clean exit)."""

    def test_decay_no_stale_items(self):
        wf = load_workflow()  # stale_count=0 by default

        complete_user_task(wf, "identify_action", {"action": "decay"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "calculate_decay" in names
        assert "apply_decay" in names
        assert "find_stale_subgraphs" in names
        assert "archive_stale" not in names
        assert "flag_contradictions" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 4: Review - Keep (Default)
# ---------------------------------------------------------------------------

class TestReviewKeep:
    """Review path with default keep decision."""

    def test_review_keep_default(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "review"})

        assert "review_flagged" in ready_task_names(wf)
        complete_user_task(wf, "review_flagged", {})  # decision defaults to "keep"

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "review_flagged" in names
        assert "keep_and_strengthen" in names
        assert "merge_duplicates" not in names
        assert "delete_knowledge" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 4b: Review - Merge Duplicates
# ---------------------------------------------------------------------------

class TestReviewMerge:
    """Review path merging duplicate knowledge nodes."""

    def test_review_merge_duplicates(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "review"})

        assert "review_flagged" in ready_task_names(wf)
        complete_user_task(wf, "review_flagged", {"decision": "merge"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "review_flagged" in names
        assert "merge_duplicates" in names
        assert "keep_and_strengthen" not in names
        assert "delete_knowledge" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Path 4c: Review - Delete Knowledge
# ---------------------------------------------------------------------------

class TestReviewDelete:
    """Review path deleting stale knowledge."""

    def test_review_delete_knowledge(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "review"})

        assert "review_flagged" in ready_task_names(wf)
        complete_user_task(wf, "review_flagged", {"decision": "delete"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "review_flagged" in names
        assert "delete_knowledge" in names
        assert "keep_and_strengthen" not in names
        assert "merge_duplicates" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Sanity Checks
# ---------------------------------------------------------------------------

class TestWorkflowValidation:
    """Verify basic workflow structure."""

    def test_workflow_loads_successfully(self):
        wf = load_workflow()
        assert wf is not None
        assert wf.spec is not None

    def test_identify_action_is_first_ready_task(self):
        wf = load_workflow()
        ready = ready_task_names(wf)
        assert ready == ["identify_action"]

    def test_all_four_paths_reachable(self):
        """Verify each action routes to distinct tasks."""
        actions_and_expected = {
            "sync": "check_age_extension",
            "query": "pgvector_search",
            "decay": "calculate_decay",
            "review": "review_flagged",
        }
        for action, expected_task in actions_and_expected.items():
            wf = load_workflow(data_overrides={"action": action} if action != "sync" else None)
            complete_user_task(wf, "identify_action", {"action": action} if action != "sync" else {})
            names = completed_spec_names(wf)
            # review_flagged is a userTask, check ready instead
            if expected_task == "review_flagged":
                assert expected_task in ready_task_names(wf), (
                    f"action='{action}' should reach '{expected_task}'"
                )
            else:
                assert expected_task in names, (
                    f"action='{action}' should reach '{expected_task}'"
                )
