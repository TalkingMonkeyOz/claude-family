"""
Tests for Entity Management BPMN process.

Process: entity_management (processes/lifecycle/entity_management.bpmn)
4 paths via exclusive gateway:
  P1: catalog (new entity) - lookup_type → validate → dedup → embed → insert
  P2: catalog (existing, upsert) - lookup_type → validate → dedup → upsert
  P3: recall - generate query embedding → RRF search → update access
  P4: link - validate entities → insert relationship
  P5: register_type - validate name → insert type

SpiffWorkflow evaluates ALL gateway conditions. All condition variables
MUST be present in DEFAULT_DATA.
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


_ENTITY_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "entity_management.bpmn"
    )
)
_ENTITY_PROCESS_ID = "entity_management"

# Default data: operation='catalog', new entity path (no existing)
_ENTITY_DEFAULT_DATA = {
    "operation": "catalog",
    "existing_entity": False,
    "entity_type_row": {"type_id": "uuid", "json_schema": {}, "embedding_template": "{name}"},
    "validation_passed": True,
    "entities_valid": True,
    "name_valid": True,
}


def _load_entity(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh entity_management workflow with default data."""
    parser = BpmnParser()
    parser.add_bpmn_file(_ENTITY_BPMN)
    spec = parser.get_spec(_ENTITY_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_ENTITY_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _completed_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# P1: Catalog new entity (no dedup match)
# ---------------------------------------------------------------------------

class TestCatalogNewEntity:
    """Catalog path: lookup → validate → dedup (no match) → embed → insert."""

    def test_catalog_new_entity_completes(self):
        wf = _load_entity({"operation": "catalog", "existing_entity": False})
        assert wf.is_completed()

    def test_catalog_new_entity_runs_expected_tasks(self):
        wf = _load_entity({"operation": "catalog", "existing_entity": False})
        names = _completed_names(wf)
        assert "lookup_type" in names
        assert "validate_schema" in names
        assert "check_dedup" in names
        assert "generate_embedding" in names
        assert "insert_entity" in names
        assert "catalog_end" in names

    def test_catalog_new_entity_skips_upsert(self):
        wf = _load_entity({"operation": "catalog", "existing_entity": False})
        names = _completed_names(wf)
        assert "upsert_existing" not in names


# ---------------------------------------------------------------------------
# P2: Catalog existing entity (upsert)
# ---------------------------------------------------------------------------

class TestCatalogUpsertEntity:
    """Catalog path: lookup → validate → dedup (match) → upsert."""

    def test_catalog_upsert_completes(self):
        wf = _load_entity({"operation": "catalog", "existing_entity": True})
        assert wf.is_completed()

    def test_catalog_upsert_runs_upsert_task(self):
        wf = _load_entity({"operation": "catalog", "existing_entity": True})
        names = _completed_names(wf)
        assert "upsert_existing" in names
        assert "catalog_end" in names

    def test_catalog_upsert_skips_insert(self):
        wf = _load_entity({"operation": "catalog", "existing_entity": True})
        names = _completed_names(wf)
        assert "generate_embedding" not in names
        assert "insert_entity" not in names


# ---------------------------------------------------------------------------
# P3: Recall entities
# ---------------------------------------------------------------------------

class TestRecallEntities:
    """Recall path: generate embedding → RRF search → update access."""

    def test_recall_completes(self):
        wf = _load_entity({"operation": "recall"})
        assert wf.is_completed()

    def test_recall_runs_expected_tasks(self):
        wf = _load_entity({"operation": "recall"})
        names = _completed_names(wf)
        assert "recall_generate_embedding" in names
        assert "recall_rrf" in names
        assert "recall_access" in names
        assert "recall_end" in names

    def test_recall_does_not_run_catalog_tasks(self):
        wf = _load_entity({"operation": "recall"})
        names = _completed_names(wf)
        assert "lookup_type" not in names
        assert "insert_entity" not in names


# ---------------------------------------------------------------------------
# P4: Link entities
# ---------------------------------------------------------------------------

class TestLinkEntities:
    """Link path: validate → insert relationship."""

    def test_link_completes(self):
        wf = _load_entity({"operation": "link"})
        assert wf.is_completed()

    def test_link_runs_expected_tasks(self):
        wf = _load_entity({"operation": "link"})
        names = _completed_names(wf)
        assert "validate_link" in names
        assert "insert_link" in names
        assert "link_end" in names


# ---------------------------------------------------------------------------
# P5: Register new entity type
# ---------------------------------------------------------------------------

class TestRegisterType:
    """Register path: validate type name → insert type."""

    def test_register_type_completes(self):
        wf = _load_entity({"operation": "register_type"})
        assert wf.is_completed()

    def test_register_type_runs_expected_tasks(self):
        wf = _load_entity({"operation": "register_type"})
        names = _completed_names(wf)
        assert "validate_type_name" in names
        assert "insert_type" in names
        assert "register_end" in names


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------

class TestEntityWorkflowStructure:
    """Basic structural checks."""

    def test_workflow_loads(self):
        wf = _load_entity()
        assert wf is not None
        assert wf.spec is not None

    def test_no_manual_tasks(self):
        """All tasks are script tasks — no user intervention needed."""
        wf = _load_entity()
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []
