"""
Tests for the Database Cleanup BPMN process.

Models the safety-first approach to dropping empty tables:
  - Verify tables are empty (don't trust stale audit data)
  - Check FK dependencies (internal vs external)
  - Order drops correctly (leaf tables first)
  - Execute and verify

3 paths:
  1. All empty, no FK blockers -> straight to drop
  2. Some non-empty -> filter out, then continue
  3. External FK blockers -> remove blocked tables, then continue
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "database_cleanup.bpmn")
)
PROCESS_ID = "database_cleanup"


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
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


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


def get_task_data(workflow: BpmnWorkflow, spec_name: str) -> dict:
    for t in workflow.get_tasks(state=TaskState.COMPLETED):
        if t.task_spec.name == spec_name:
            return dict(t.data)
    return {}


# ---------------------------------------------------------------------------
# PATH A: Happy Path - All Empty, No Blockers
# ---------------------------------------------------------------------------

class TestHappyPath:
    """All tables empty, no FK blockers -> drop all."""

    def test_full_path_completes(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks", "work_tasks"],
            "non_empty_tables": [],
            "external_fk_blockers": [],
        })
        completed = completed_spec_names(wf)
        assert "load_table_list" in completed
        assert "verify_empty" in completed
        assert "check_fk_deps" in completed
        assert "order_drops" in completed
        assert "execute_drops" in completed
        assert "verify_drops" in completed
        assert wf.is_completed()

    def test_skips_filter_and_remove(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks"],
            "non_empty_tables": [],
            "external_fk_blockers": [],
        })
        completed = completed_spec_names(wf)
        assert "filter_nonempty" not in completed
        assert "remove_blocked" not in completed

    def test_drop_count_matches(self):
        tables = ["ideas", "pm_tasks", "work_tasks", "requirements", "actions"]
        wf = load_workflow({
            "table_list": tables,
            "non_empty_tables": [],
            "external_fk_blockers": [],
        })
        data = get_task_data(wf, "execute_drops")
        assert data.get("tables_dropped") == 5
        assert data.get("drops_executed") is True

    def test_cleanup_verified(self):
        wf = load_workflow({
            "table_list": ["ideas"],
            "non_empty_tables": [],
            "external_fk_blockers": [],
        })
        data = get_task_data(wf, "verify_drops")
        assert data.get("cleanup_verified") is True


# ---------------------------------------------------------------------------
# PATH B: Non-Empty Tables Found
# ---------------------------------------------------------------------------

class TestNonEmptyFilter:
    """Some tables have data -> filter them out, continue with rest."""

    def test_filter_path_triggered(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks", "messages"],
            "non_empty_tables": ["messages"],
            "external_fk_blockers": [],
        })
        completed = completed_spec_names(wf)
        assert "filter_nonempty" in completed
        assert wf.is_completed()

    def test_non_empty_removed_from_list(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks", "messages"],
            "non_empty_tables": ["messages"],
            "external_fk_blockers": [],
        })
        data = get_task_data(wf, "filter_nonempty")
        assert "messages" not in data.get("verified_empty", [])
        assert "ideas" in data.get("verified_empty", [])
        assert "pm_tasks" in data.get("verified_empty", [])

    def test_still_drops_remaining(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks", "messages"],
            "non_empty_tables": ["messages"],
            "external_fk_blockers": [],
        })
        completed = completed_spec_names(wf)
        assert "execute_drops" in completed
        assert "verify_drops" in completed


# ---------------------------------------------------------------------------
# PATH C: External FK Blockers
# ---------------------------------------------------------------------------

class TestFKBlockers:
    """External FK dependencies -> remove blocked tables."""

    def test_blocker_path_triggered(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks", "workflow_state"],
            "non_empty_tables": [],
            "external_fk_blockers": ["workflow_state"],
        })
        completed = completed_spec_names(wf)
        assert "remove_blocked" in completed
        assert wf.is_completed()

    def test_blocked_tables_removed(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks", "workflow_state"],
            "non_empty_tables": [],
            "external_fk_blockers": ["workflow_state"],
        })
        data = get_task_data(wf, "remove_blocked")
        assert "workflow_state" not in data.get("verified_empty", [])
        assert data.get("blockers_removed") is True

    def test_still_drops_unblocked(self):
        wf = load_workflow({
            "table_list": ["ideas", "pm_tasks", "workflow_state"],
            "non_empty_tables": [],
            "external_fk_blockers": ["workflow_state"],
        })
        completed = completed_spec_names(wf)
        assert "execute_drops" in completed


# ---------------------------------------------------------------------------
# COMBINED: Non-Empty + FK Blockers
# ---------------------------------------------------------------------------

class TestCombinedFilters:
    """Both non-empty tables and FK blockers in same run."""

    def test_both_filters_applied(self):
        wf = load_workflow({
            "table_list": ["ideas", "messages", "workflow_state", "pm_tasks"],
            "non_empty_tables": ["messages"],
            "external_fk_blockers": ["workflow_state"],
        })
        completed = completed_spec_names(wf)
        assert "filter_nonempty" in completed
        assert "remove_blocked" in completed
        assert "execute_drops" in completed
        assert wf.is_completed()


# ---------------------------------------------------------------------------
# CROSS-CUTTING: Always verify and order
# ---------------------------------------------------------------------------

class TestAlwaysVerifiesAndOrders:
    """All paths must verify empty and order drops."""

    def test_verify_on_happy_path(self):
        wf = load_workflow({"table_list": ["ideas"], "non_empty_tables": [], "external_fk_blockers": []})
        assert "verify_empty" in completed_spec_names(wf)
        assert "order_drops" in completed_spec_names(wf)

    def test_verify_on_filter_path(self):
        wf = load_workflow({"table_list": ["ideas", "messages"], "non_empty_tables": ["messages"], "external_fk_blockers": []})
        assert "verify_empty" in completed_spec_names(wf)
        assert "order_drops" in completed_spec_names(wf)

    def test_verify_on_blocker_path(self):
        wf = load_workflow({"table_list": ["ideas", "x"], "non_empty_tables": [], "external_fk_blockers": ["x"]})
        assert "verify_empty" in completed_spec_names(wf)
        assert "order_drops" in completed_spec_names(wf)


# ---------------------------------------------------------------------------
# EDGE CASES
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary conditions."""

    def test_empty_table_list(self):
        wf = load_workflow({"table_list": [], "non_empty_tables": [], "external_fk_blockers": []})
        assert wf.is_completed()
        data = get_task_data(wf, "execute_drops")
        assert data.get("tables_dropped") == 0

    def test_no_initial_data(self):
        wf = load_workflow()
        assert wf.is_completed()
        data = get_task_data(wf, "load_table_list")
        assert data.get("table_count") == 0

    def test_single_table(self):
        wf = load_workflow({"table_list": ["ideas"], "non_empty_tables": [], "external_fk_blockers": []})
        assert wf.is_completed()
        data = get_task_data(wf, "execute_drops")
        assert data.get("tables_dropped") == 1

    def test_all_tables_non_empty(self):
        """If every table has data, we still complete (just drop 0)."""
        wf = load_workflow({
            "table_list": ["a", "b", "c"],
            "non_empty_tables": ["a", "b", "c"],
            "external_fk_blockers": [],
        })
        assert wf.is_completed()
        data = get_task_data(wf, "execute_drops")
        assert data.get("tables_dropped") == 0
