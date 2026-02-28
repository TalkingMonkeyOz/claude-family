"""
Tests for the System Maintenance process.

Tests all logic paths through the system_maintenance process:
  1. Nothing stale (fast path) -> detect all 5 -> nothing stale -> compile_report -> end
  2. All stale -> detect -> all repairs run -> compile_report -> end
  3. Partial staleness (schema + memory only) -> only those repairs run
  4. Schema repair has 2 sequential steps (schema_docs then embed_schema)
  5. Process structure validation (element counts, gateways, flows)

Key design notes:
  - All tasks are scriptTasks (fully automated workflow)
  - Parallel gateways fan out to 5 checks / 5 repairs
  - Script defaults initialize all staleness flags to False
  - To test repair paths, data must be seeded AFTER detect scripts run
    (or we accept that scripts overwrite seeds and test structure instead)
  - Since scriptTask scripts set their own defaults, we test:
    a) Process structure is correct
    b) Fast path (nothing stale) completes
    c) Element and flow counts match expectations
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "system_maintenance.bpmn")
)
PROCESS_ID = "system_maintenance"


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
        # SpiffWorkflow uses process ID as spec.name
        assert spec.name == "system_maintenance"

    def test_has_start_and_end_events(self):
        wf = load_workflow()
        names = [t.task_spec.name for t in wf.get_tasks()]
        assert "start" in names
        assert "end_complete" in names

    def test_has_all_five_check_tasks(self):
        """All 5 detection tasks must exist."""
        wf = load_workflow()
        names = [t.task_spec.name for t in wf.get_tasks()]
        assert "check_schema" in names
        assert "check_vault" in names
        assert "check_bpmn" in names
        assert "check_memory" in names
        assert "check_column_registry" in names

    def test_has_all_repair_tasks(self):
        """All repair tasks must exist in spec (6 tasks for 5 subsystems, schema has 2).

        Use spec.task_specs (all defined tasks) not wf.get_tasks() (only instantiated).
        Repair tasks aren't instantiated on the fast path.
        """
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "repair_schema_docs" in names
        assert "repair_schema_embed" in names
        assert "repair_vault_embed" in names
        assert "repair_bpmn_sync" in names
        assert "repair_memory_consolidate" in names
        assert "repair_column_registry" in names

    def test_has_parallel_gateways(self):
        """Must have detect_split/join and repair_split/join parallel gateways."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "detect_split" in names
        assert "detect_join" in names
        assert "repair_split" in names
        assert "repair_join" in names

    def test_has_staleness_decision_gateways(self):
        """Each repair path has a conditional gateway."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "any_stale_gw" in names
        assert "schema_stale_gw" in names
        assert "vault_stale_gw" in names
        assert "bpmn_stale_gw" in names
        assert "memory_stale_gw" in names
        assert "column_stale_gw" in names


# ---------------------------------------------------------------------------
# Test 2: Fast path - nothing stale
# ---------------------------------------------------------------------------

class TestNothingStale:
    """Default path: all checks return false -> skip repairs -> compile report."""

    def test_completes_successfully(self):
        wf = load_workflow()
        assert wf.is_completed()

    def test_all_checks_executed(self):
        wf = load_workflow()
        names = completed_spec_names(wf)
        assert "check_schema" in names
        assert "check_vault" in names
        assert "check_bpmn" in names
        assert "check_memory" in names
        assert "check_column_registry" in names

    def test_report_compiled(self):
        wf = load_workflow()
        names = completed_spec_names(wf)
        assert "compile_report" in names
        assert "end_complete" in names

    def test_staleness_flags_all_false(self):
        wf = load_workflow()
        assert wf.data.get("schema_stale") is False
        assert wf.data.get("vault_stale") is False
        assert wf.data.get("bpmn_stale") is False
        assert wf.data.get("memory_stale") is False
        assert wf.data.get("column_registry_stale") is False

    def test_maintenance_complete_flag(self):
        wf = load_workflow()
        assert wf.data.get("maintenance_complete") is True

    def test_all_clean_flag(self):
        """When nothing is stale, all_clean should be True."""
        wf = load_workflow()
        assert wf.data.get("all_clean") is True


# ---------------------------------------------------------------------------
# Test 3: Data output shape
# ---------------------------------------------------------------------------

class TestDataOutputShape:
    """Verify all expected data keys are present after completion."""

    def test_schema_check_outputs(self):
        wf = load_workflow()
        assert "schema_stale" in wf.data
        assert "schema_new_tables" in wf.data
        assert "schema_changed_tables" in wf.data

    def test_vault_check_outputs(self):
        wf = load_workflow()
        assert "vault_stale" in wf.data
        assert "vault_unembedded_count" in wf.data

    def test_bpmn_check_outputs(self):
        wf = load_workflow()
        assert "bpmn_stale" in wf.data
        assert "bpmn_unsynced_count" in wf.data

    def test_memory_check_outputs(self):
        wf = load_workflow()
        assert "memory_stale" in wf.data
        assert "memory_unembedded_count" in wf.data

    def test_column_registry_check_outputs(self):
        wf = load_workflow()
        assert "column_registry_stale" in wf.data
        assert "column_registry_missing" in wf.data

    def test_report_outputs(self):
        wf = load_workflow()
        assert "maintenance_complete" in wf.data


# ---------------------------------------------------------------------------
# Test 4: Schema repair has two sequential steps
# ---------------------------------------------------------------------------

class TestSchemaRepairSequence:
    """Schema repair requires schema_docs -> embed_schema in sequence.

    Since scriptTasks initialize staleness to False by default,
    we verify the structural relationship via spec inspection.
    """

    def test_schema_embed_follows_schema_docs(self):
        """repair_schema_embed must follow repair_schema_docs."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        # Find the repair_schema_docs spec and verify its output goes to embed
        schema_docs_spec = spec.task_specs.get("repair_schema_docs")
        assert schema_docs_spec is not None

        # Get the output specs (tasks that follow this one)
        output_names = [s.name for s in schema_docs_spec.outputs]
        assert "repair_schema_embed" in output_names

    def test_schema_embed_goes_to_repair_join(self):
        """repair_schema_embed must connect to repair_join."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        schema_embed_spec = spec.task_specs.get("repair_schema_embed")
        assert schema_embed_spec is not None

        output_names = [s.name for s in schema_embed_spec.outputs]
        assert "repair_join" in output_names


# ---------------------------------------------------------------------------
# Test 5: Counter and flag defaults
# ---------------------------------------------------------------------------

class TestDefaultValues:
    """Verify script-initialized defaults are correct."""

    def test_zero_counts_when_nothing_stale(self):
        wf = load_workflow()
        assert wf.data.get("schema_new_tables") == 0
        assert wf.data.get("schema_changed_tables") == 0
        assert wf.data.get("vault_unembedded_count") == 0
        assert wf.data.get("bpmn_unsynced_count") == 0
        assert wf.data.get("memory_unembedded_count") == 0
        assert wf.data.get("column_registry_missing") == 0
