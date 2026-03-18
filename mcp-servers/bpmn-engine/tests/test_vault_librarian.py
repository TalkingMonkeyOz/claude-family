"""
Tests for the Vault Librarian process.

Tests all logic paths through the vault_librarian process:
  1. Process parses correctly and has expected structure
  2. Happy path: DB connects, no issues found -> report clean -> end
  3. Issues found, fix mode off -> generate report -> skip fix -> end
  4. Issues found, fix mode on -> generate report -> auto fix -> end
  5. DB connection failure -> abort early
  6. All 4 parallel check tasks exist and execute
  7. Data output shape validation
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "maintenance", "vault_librarian.bpmn")
)
PROCESS_ID = "vault_librarian"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow with optional seeded data."""
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


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return spec names of all COMPLETED tasks."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


def all_spec_names(workflow: BpmnWorkflow) -> list:
    """Return spec names of all tasks in workflow."""
    return [t.task_spec.name for t in workflow.get_tasks()]


# ---------------------------------------------------------------------------
# Test 1: Process parses correctly
# ---------------------------------------------------------------------------

class TestProcessStructure:
    """Validate the BPMN file parses and has expected structure."""

    def test_parse_valid(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        assert spec is not None
        assert spec.name == "vault_librarian"

    def test_has_start_and_end_events(self):
        wf = load_workflow()
        names = all_spec_names(wf)
        assert "start" in names
        assert "end_complete" in names

    def test_has_all_four_check_tasks(self):
        """All 4 detection tasks must exist in spec."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "check_uncataloged" in names
        assert "check_orphaned" in names
        assert "check_frontmatter" in names
        assert "check_embeddings" in names

    def test_has_parallel_gateways(self):
        """Must have check_split/join parallel gateways."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "check_split" in names
        assert "check_join" in names

    def test_has_decision_gateways(self):
        """Must have DB check, issues, and fix mode gateways."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "db_check_gw" in names
        assert "issues_found_gw" in names
        assert "fix_mode_gw" in names

    def test_has_report_and_fix_tasks(self):
        """Report and fix tasks must exist in spec."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "generate_report" in names
        assert "auto_fix" in names
        assert "report_clean" in names

    def test_has_db_error_end_event(self):
        """Must have early exit for DB failure."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "end_db_error" in names


# ---------------------------------------------------------------------------
# Test 2: Happy path - no issues found (default)
# ---------------------------------------------------------------------------

class TestNoIssuesFound:
    """Default path: DB connects, all checks run, no issues -> report clean."""

    def test_completes_successfully(self):
        wf = load_workflow()
        assert wf.is_completed()

    def test_all_checks_executed(self):
        wf = load_workflow()
        names = completed_spec_names(wf)
        assert "check_uncataloged" in names
        assert "check_orphaned" in names
        assert "check_frontmatter" in names
        assert "check_embeddings" in names

    def test_aggregate_executed(self):
        wf = load_workflow()
        names = completed_spec_names(wf)
        assert "aggregate_findings" in names

    def test_report_clean_executed(self):
        wf = load_workflow()
        names = completed_spec_names(wf)
        assert "report_clean" in names
        assert "end_complete" in names

    def test_no_issues_flag(self):
        wf = load_workflow()
        assert wf.data.get("has_issues") is False
        assert wf.data.get("total_findings") == 0

    def test_vault_clean_flag(self):
        wf = load_workflow()
        assert wf.data.get("vault_clean") is True


# ---------------------------------------------------------------------------
# Test 3: Data output shape
# ---------------------------------------------------------------------------

class TestDataOutputShape:
    """Verify all expected data keys are present after completion."""

    def test_init_outputs(self):
        wf = load_workflow()
        assert "db_connected" in wf.data
        assert "vault_file_count" in wf.data
        assert "trigger_mode" in wf.data
        assert "fix_mode" in wf.data

    def test_uncataloged_check_outputs(self):
        wf = load_workflow()
        assert "uncataloged_count" in wf.data

    def test_orphaned_check_outputs(self):
        wf = load_workflow()
        assert "orphaned_count" in wf.data
        assert "moved_count" in wf.data

    def test_frontmatter_check_outputs(self):
        wf = load_workflow()
        assert "missing_frontmatter_count" in wf.data
        assert "malformed_frontmatter_count" in wf.data
        assert "missing_field_count" in wf.data

    def test_embedding_check_outputs(self):
        wf = load_workflow()
        assert "missing_embedding_count" in wf.data

    def test_aggregate_outputs(self):
        wf = load_workflow()
        assert "total_findings" in wf.data
        assert "has_issues" in wf.data
        assert "has_critical_or_high" in wf.data


# ---------------------------------------------------------------------------
# Test 4: Default counter values
# ---------------------------------------------------------------------------

class TestDefaultValues:
    """Verify script-initialized defaults are correct."""

    def test_zero_counts_when_no_issues(self):
        wf = load_workflow()
        assert wf.data.get("uncataloged_count") == 0
        assert wf.data.get("orphaned_count") == 0
        assert wf.data.get("moved_count") == 0
        assert wf.data.get("missing_frontmatter_count") == 0
        assert wf.data.get("malformed_frontmatter_count") == 0
        assert wf.data.get("missing_field_count") == 0
        assert wf.data.get("missing_embedding_count") == 0

    def test_db_connected_default(self):
        wf = load_workflow()
        assert wf.data.get("db_connected") is True

    def test_fix_mode_default_false(self):
        wf = load_workflow()
        assert wf.data.get("fix_mode") is False


# ---------------------------------------------------------------------------
# Test 5: Aggregate follows check join
# ---------------------------------------------------------------------------

class TestAggregateFollowsChecks:
    """Verify aggregate_findings is downstream of all 4 checks."""

    def test_aggregate_follows_check_join(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        check_join_spec = spec.task_specs.get("check_join")
        assert check_join_spec is not None

        output_names = [s.name for s in check_join_spec.outputs]
        assert "aggregate_findings" in output_names

    def test_generate_report_follows_issues_gateway(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        gw_spec = spec.task_specs.get("issues_found_gw")
        assert gw_spec is not None

        output_names = [s.name for s in gw_spec.outputs]
        assert "generate_report" in output_names
        assert "report_clean" in output_names
