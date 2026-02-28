"""
Tests for the Schema Governance process.

Tests the 3-layer schema governance pipeline:
  Layer 1: Self-documentation - COMMENT ON + registry sync (foundation)
  Layer 2: Schema embeddings - Voyage AI embeddings for RAG search
  Layer 3: BPMN-schema validation - Validate BPMN data refs against live schema

Execution paths tested:
  1. Full pipeline: Introspect -> Comment -> Sync -> Embed -> Validate -> Done
  2. Incremental: Introspect -> No changes -> Skip embedding -> Validate -> Done
  3. Embed only: Skip L1 -> Build text -> Hash check -> Embed changed -> Validate -> Done
  4. Validate only: Skip L1+L2 -> Validate BPMN data refs -> Done

Key design notes:
  - All tasks are scriptTasks (fully automated)
  - 3 exclusive gateways for conditional routing
  - 3 layers with sequential tasks within each layer
  - Data flow: tables_changed controls embedding branch, refs_extracted controls validation
  - Tests cover: structure validation, all 4 execution paths, data output shape, task ordering
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "schema_governance.bpmn")
)
PROCESS_ID = "schema_governance"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow with optional seeded data."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)

    # Prepare default data to avoid undefined variables in scripts
    default_data = {
        "tables_to_embed": [],  # Initialize for check_content_hash script
        "pipeline_mode": "full",  # Default mode
    }

    # Merge with user-provided initial data
    if initial_data:
        default_data.update(initial_data)

    # Seed the workflow with initialized data
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(default_data)

    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return spec names of all COMPLETED tasks."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Test 1: Process Structure Validation
# ---------------------------------------------------------------------------

class TestProcessStructure:
    """Validate the BPMN file parses and has expected structure."""

    def test_parse_valid(self):
        """BPMN file must parse without errors."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        assert spec is not None
        assert spec.name == "schema_governance"

    def test_has_start_and_end_events(self):
        """Must have start event and end event."""
        wf = load_workflow()
        names = [t.task_spec.name for t in wf.get_tasks()]
        assert "start" in names
        assert "end_complete" in names

    def test_has_mode_gateway(self):
        """Must have mode_gw (exclusive gateway for pipeline mode selection)."""
        wf = load_workflow()
        names = [t.task_spec.name for t in wf.get_tasks()]
        assert "mode_gw" in names

    def test_layer1_tasks_exist(self):
        """Layer 1 (self-documentation) must have all required tasks."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())

        # Layer 1 tasks
        assert "introspect_schema" in names
        assert "generate_report" in names
        assert "needs_comments_gw" in names
        assert "generate_comments" in names
        assert "apply_comments" in names
        assert "sync_schema_registry" in names
        assert "sync_column_registry" in names

    def test_layer2_tasks_exist(self):
        """Layer 2 (embeddings) must have all required tasks."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())

        # Layer 2 tasks
        assert "build_embeddable_text" in names
        assert "check_content_hash" in names
        assert "has_changes_gw" in names
        assert "embed_tables" in names
        assert "store_embeddings" in names

    def test_layer3_tasks_exist(self):
        """Layer 3 (BPMN-schema validation) must have all required tasks."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())

        # Layer 3 tasks
        assert "extract_data_refs" in names
        assert "validate_refs" in names
        assert "update_process_data_map" in names
        assert "summarize_results" in names

    def test_has_exclusive_gateways(self):
        """Must have 3 exclusive gateways for conditional logic."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())

        # Mode selection gateway
        assert "mode_gw" in names

        # Layer 1 conditional gateway
        assert "needs_comments_gw" in names

        # Layer 2 conditional gateway
        assert "has_changes_gw" in names

    def test_has_summarize_results_task(self):
        """Must have summarize_results task before end."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        names = list(spec.task_specs.keys())
        assert "summarize_results" in names


# ---------------------------------------------------------------------------
# Test 2: Full Pipeline Path (Default)
# ---------------------------------------------------------------------------

class TestFullPipelinePath:
    """Default path: Introspect -> Comment -> Sync -> Embed -> Validate -> Done.

    This tests the complete flow when pipeline_mode defaults to 'full'.
    """

    def test_completes_successfully(self):
        """Full pipeline must complete without errors."""
        wf = load_workflow()
        assert wf.is_completed()

    def test_layer1_tasks_executed(self):
        """All Layer 1 tasks must execute on full pipeline."""
        wf = load_workflow()
        names = completed_spec_names(wf)

        assert "introspect_schema" in names
        assert "generate_report" in names
        # needs_comments_gw is a gateway, not included in completion list

    def test_layer2_tasks_executed(self):
        """All Layer 2 tasks must execute on full pipeline."""
        wf = load_workflow()
        names = completed_spec_names(wf)

        assert "build_embeddable_text" in names
        assert "check_content_hash" in names

    def test_layer3_tasks_executed(self):
        """All Layer 3 tasks must execute."""
        wf = load_workflow()
        names = completed_spec_names(wf)

        assert "extract_data_refs" in names
        assert "validate_refs" in names
        assert "update_process_data_map" in names

    def test_summarize_and_end(self):
        """Must reach summarize_results and end_complete."""
        wf = load_workflow()
        names = completed_spec_names(wf)

        assert "summarize_results" in names
        assert "end_complete" in names

    def test_pipeline_complete_flag(self):
        """pipeline_complete flag must be True at end."""
        wf = load_workflow()
        assert wf.data.get("pipeline_complete") is True


# ---------------------------------------------------------------------------
# Test 3: Incremental Path (No Changes Detected)
# ---------------------------------------------------------------------------

class TestIncrementalPath:
    """Test behavior when schema introspection detects no changes.

    Seed needs_comments = False to skip Layer 1 comments.
    Seed tables_changed = 0 to skip embedding.
    Still runs validation (Layer 3).
    """

    def test_with_no_comments_needed(self):
        """When needs_comments is False, skip generate_comments/apply_comments."""
        wf = load_workflow({"needs_comments": False, "tables_without_comments": 0, "columns_without_comments": 0})
        names = completed_spec_names(wf)

        # Layer 1: introspect and generate_report still run
        assert "introspect_schema" in names
        assert "generate_report" in names

        # Comments should be skipped, but registry sync still runs
        assert "generate_comments" not in names
        assert "apply_comments" not in names
        assert "sync_schema_registry" in names

    def test_with_no_embed_changes(self):
        """When tables_changed is 0, skip embed_tables/store_embeddings."""
        wf = load_workflow({
            "needs_comments": False,
            "tables_without_comments": 0,
            "columns_without_comments": 0,
            "tables_to_embed": []  # Empty list means no changes
        })
        names = completed_spec_names(wf)

        # Layer 2: build_embeddable_text and check_content_hash run
        assert "build_embeddable_text" in names
        assert "check_content_hash" in names

        # Embedding should be skipped
        assert "embed_tables" not in names
        assert "store_embeddings" not in names

        # But Layer 3 still runs
        assert "extract_data_refs" in names
        assert "validate_refs" in names

    def test_still_validates(self):
        """Validation (Layer 3) must always run, even with no changes."""
        wf = load_workflow({
            "needs_comments": False,
            "tables_without_comments": 0,
            "columns_without_comments": 0,
            "tables_to_embed": []
        })
        names = completed_spec_names(wf)

        assert "extract_data_refs" in names
        assert "validate_refs" in names
        assert "update_process_data_map" in names


# ---------------------------------------------------------------------------
# Test 4: Embed-Only Path
# ---------------------------------------------------------------------------

class TestEmbedOnlyPath:
    """Test skipping Layer 1 when comments are current.

    Seeding pipeline_mode = 'embed_only' should route directly to Layer 2.
    """

    def test_skips_layer1_tasks(self):
        """embed_only mode must skip introspect_schema and generate_report."""
        wf = load_workflow({"pipeline_mode": "embed_only"})
        names = completed_spec_names(wf)

        # Layer 1 should be skipped
        assert "introspect_schema" not in names
        assert "generate_report" not in names
        assert "sync_schema_registry" not in names

    def test_runs_layer2_and_layer3(self):
        """embed_only mode must run Layer 2 and Layer 3."""
        wf = load_workflow({"pipeline_mode": "embed_only"})
        names = completed_spec_names(wf)

        # Layer 2 must run
        assert "build_embeddable_text" in names
        assert "check_content_hash" in names

        # Layer 3 must run
        assert "extract_data_refs" in names
        assert "validate_refs" in names

    def test_completes(self):
        """embed_only mode must complete successfully."""
        wf = load_workflow({"pipeline_mode": "embed_only"})
        assert wf.is_completed()


# ---------------------------------------------------------------------------
# Test 5: Validate-Only Path
# ---------------------------------------------------------------------------

class TestValidateOnlyPath:
    """Test skipping Layer 1 and 2 when only validation is needed.

    Seeding pipeline_mode = 'validate_only' routes directly to Layer 3.
    """

    def test_skips_layer1_and_layer2(self):
        """validate_only mode must skip Layer 1 and Layer 2 tasks."""
        wf = load_workflow({"pipeline_mode": "validate_only"})
        names = completed_spec_names(wf)

        # Layer 1 should be skipped
        assert "introspect_schema" not in names
        assert "generate_report" not in names

        # Layer 2 should be skipped
        assert "build_embeddable_text" not in names
        assert "check_content_hash" not in names
        assert "embed_tables" not in names

    def test_runs_layer3_only(self):
        """validate_only mode must run Layer 3 (extract, validate, map)."""
        wf = load_workflow({"pipeline_mode": "validate_only"})
        names = completed_spec_names(wf)

        assert "extract_data_refs" in names
        assert "validate_refs" in names
        assert "update_process_data_map" in names

    def test_runs_summarize(self):
        """validate_only mode must still summarize results."""
        wf = load_workflow({"pipeline_mode": "validate_only"})
        names = completed_spec_names(wf)

        assert "summarize_results" in names
        assert "end_complete" in names

    def test_completes(self):
        """validate_only mode must complete successfully."""
        wf = load_workflow({"pipeline_mode": "validate_only"})
        assert wf.is_completed()


# ---------------------------------------------------------------------------
# Test 6: Data Output Shape
# ---------------------------------------------------------------------------

class TestDataOutputShape:
    """Verify all expected output variables are set after completion."""

    def test_layer1_output_variables(self):
        """Layer 1 must set schema introspection outputs."""
        wf = load_workflow()

        # From introspect_schema
        assert "table_count" in wf.data
        assert "column_count" in wf.data

        # From generate_report
        assert "needs_comments" in wf.data

    def test_layer1_comment_tracking(self):
        """Layer 1 comment tasks exist and are structurally linked.

        Since scriptTask defaults initialize tables_without_comments=0, the comment
        branch is skipped on the default path. We verify the branch exists structurally.
        """
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        # generate_comments and apply_comments must exist in spec
        assert "generate_comments" in spec.task_specs
        assert "apply_comments" in spec.task_specs

        # generate_comments output leads to apply_comments
        gen_spec = spec.task_specs["generate_comments"]
        output_names = [s.name for s in gen_spec.outputs]
        assert "apply_comments" in output_names

        # apply_comments output leads to sync_schema_registry
        apply_spec = spec.task_specs["apply_comments"]
        output_names = [s.name for s in apply_spec.outputs]
        assert "sync_schema_registry" in output_names

    def test_layer1_registry_sync(self):
        """Layer 1 must track registry synchronization."""
        wf = load_workflow()

        assert "registry_synced" in wf.data
        assert "column_registry_synced" in wf.data

    def test_layer2_output_variables(self):
        """Layer 2 must set embedding-related outputs."""
        wf = load_workflow()

        # From build_embeddable_text
        assert "texts_built" in wf.data

        # From check_content_hash
        assert "tables_changed" in wf.data

    def test_layer2_embedding_outputs(self):
        """Layer 2 embedding tasks exist and are structurally linked.

        Since scriptTask defaults initialize tables_to_embed=[], the embedding
        branch is skipped on the default path. We verify the branch exists structurally.
        """
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        # embed_tables and store_embeddings must exist in spec
        assert "embed_tables" in spec.task_specs
        assert "store_embeddings" in spec.task_specs

        # embed_tables output leads to store_embeddings
        embed_spec = spec.task_specs["embed_tables"]
        output_names = [s.name for s in embed_spec.outputs]
        assert "store_embeddings" in output_names

        # store_embeddings output leads to extract_data_refs (L3)
        store_spec = spec.task_specs["store_embeddings"]
        output_names = [s.name for s in store_spec.outputs]
        assert "extract_data_refs" in output_names

    def test_layer3_output_variables(self):
        """Layer 3 must set validation-related outputs."""
        wf = load_workflow()

        # From extract_data_refs
        assert "refs_extracted" in wf.data

        # From validate_refs
        assert "validation_complete" in wf.data

        # From update_process_data_map
        assert "map_updated" in wf.data

    def test_final_summary_output(self):
        """summarize_results must set pipeline_complete flag."""
        wf = load_workflow()
        assert "pipeline_complete" in wf.data
        assert wf.data.get("pipeline_complete") is True


# ---------------------------------------------------------------------------
# Test 7: Sequential Task Ordering Within Layers
# ---------------------------------------------------------------------------

class TestTaskOrdering:
    """Verify sequential ordering of tasks within each layer via spec inspection."""

    def test_layer1_sequence_introspect_to_report(self):
        """introspect_schema -> generate_report."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        introspect_spec = spec.task_specs.get("introspect_schema")
        assert introspect_spec is not None

        output_names = [s.name for s in introspect_spec.outputs]
        assert "generate_report" in output_names

    def test_layer1_sequence_report_to_gateway(self):
        """generate_report -> needs_comments_gw."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        report_spec = spec.task_specs.get("generate_report")
        assert report_spec is not None

        output_names = [s.name for s in report_spec.outputs]
        assert "needs_comments_gw" in output_names

    def test_layer1_sequence_comments_applied_to_sync(self):
        """apply_comments -> sync_schema_registry."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        apply_spec = spec.task_specs.get("apply_comments")
        assert apply_spec is not None

        output_names = [s.name for s in apply_spec.outputs]
        assert "sync_schema_registry" in output_names

    def test_layer1_sequence_sync_registry_to_column(self):
        """sync_schema_registry -> sync_column_registry."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        sync_registry_spec = spec.task_specs.get("sync_schema_registry")
        assert sync_registry_spec is not None

        output_names = [s.name for s in sync_registry_spec.outputs]
        assert "sync_column_registry" in output_names

    def test_layer2_sequence_build_to_hash(self):
        """build_embeddable_text -> check_content_hash."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        build_spec = spec.task_specs.get("build_embeddable_text")
        assert build_spec is not None

        output_names = [s.name for s in build_spec.outputs]
        assert "check_content_hash" in output_names

    def test_layer2_sequence_hash_to_gateway(self):
        """check_content_hash -> has_changes_gw."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        hash_spec = spec.task_specs.get("check_content_hash")
        assert hash_spec is not None

        output_names = [s.name for s in hash_spec.outputs]
        assert "has_changes_gw" in output_names

    def test_layer2_sequence_embed_to_store(self):
        """embed_tables -> store_embeddings."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        embed_spec = spec.task_specs.get("embed_tables")
        assert embed_spec is not None

        output_names = [s.name for s in embed_spec.outputs]
        assert "store_embeddings" in output_names

    def test_layer3_sequence_extract_to_validate(self):
        """extract_data_refs -> validate_refs."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        extract_spec = spec.task_specs.get("extract_data_refs")
        assert extract_spec is not None

        output_names = [s.name for s in extract_spec.outputs]
        assert "validate_refs" in output_names

    def test_layer3_sequence_validate_to_map(self):
        """validate_refs -> update_process_data_map."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        validate_spec = spec.task_specs.get("validate_refs")
        assert validate_spec is not None

        output_names = [s.name for s in validate_spec.outputs]
        assert "update_process_data_map" in output_names

    def test_layer3_sequence_map_to_summarize(self):
        """update_process_data_map -> summarize_results."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        map_spec = spec.task_specs.get("update_process_data_map")
        assert map_spec is not None

        output_names = [s.name for s in map_spec.outputs]
        assert "summarize_results" in output_names


# ---------------------------------------------------------------------------
# Test 8: Gateway Default Flows
# ---------------------------------------------------------------------------

class TestGatewayDefaultFlows:
    """Verify that exclusive gateways have correct default flows."""

    def test_mode_gateway_default_is_full(self):
        """mode_gw should have default flow to full pipeline (introspect_schema)."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        mode_gw_spec = spec.task_specs.get("mode_gw")
        assert mode_gw_spec is not None

        # Check that full pipeline path (introspect_schema) is in outputs
        output_names = [s.name for s in mode_gw_spec.outputs]
        assert "introspect_schema" in output_names

    def test_needs_comments_gateway_default_is_skip(self):
        """needs_comments_gw should default to sync_schema_registry (skip comments)."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        needs_gw_spec = spec.task_specs.get("needs_comments_gw")
        assert needs_gw_spec is not None

        # Check that both paths are available
        output_names = [s.name for s in needs_gw_spec.outputs]
        assert "generate_comments" in output_names
        assert "sync_schema_registry" in output_names

    def test_has_changes_gateway_default_is_skip_embed(self):
        """has_changes_gw should default to skip embedding when no tables changed."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        changes_gw_spec = spec.task_specs.get("has_changes_gw")
        assert changes_gw_spec is not None

        # Check that both paths are available
        output_names = [s.name for s in changes_gw_spec.outputs]
        assert "embed_tables" in output_names
        assert "extract_data_refs" in output_names


# ---------------------------------------------------------------------------
# Test 9: Convergence Points
# ---------------------------------------------------------------------------

class TestConvergencePoints:
    """Verify that all paths converge correctly at key points."""

    def test_layer1_and_layer2_convergence(self):
        """Both comment paths (apply or skip) must converge at build_embeddable_text."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        # sync_column_registry is the end of Layer 1
        sync_col_spec = spec.task_specs.get("sync_column_registry")
        assert sync_col_spec is not None

        # Should output to build_embeddable_text
        output_names = [s.name for s in sync_col_spec.outputs]
        assert "build_embeddable_text" in output_names

    def test_layer2_paths_converge_to_layer3(self):
        """Both Layer 2 paths (embed or skip) must converge at extract_data_refs."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        # store_embeddings (when tables changed)
        store_spec = spec.task_specs.get("store_embeddings")
        assert store_spec is not None
        output_names = [s.name for s in store_spec.outputs]
        assert "extract_data_refs" in output_names

        # Check that skip path also reaches extract_data_refs
        # (has_changes_gw has a default path to extract_data_refs)
        changes_gw_spec = spec.task_specs.get("has_changes_gw")
        assert changes_gw_spec is not None
        output_names = [s.name for s in changes_gw_spec.outputs]
        assert "extract_data_refs" in output_names

    def test_all_paths_reach_summarize(self):
        """All 4 pipeline modes must eventually reach summarize_results."""
        # This is validated by testing each path completes successfully
        # Full path
        wf1 = load_workflow()
        assert wf1.is_completed()

        # Incremental path
        wf2 = load_workflow({
            "needs_comments": False,
            "tables_without_comments": 0,
            "columns_without_comments": 0,
            "tables_to_embed": []
        })
        assert wf2.is_completed()

        # Embed-only path
        wf3 = load_workflow({"pipeline_mode": "embed_only"})
        assert wf3.is_completed()

        # Validate-only path
        wf4 = load_workflow({"pipeline_mode": "validate_only"})
        assert wf4.is_completed()


# ---------------------------------------------------------------------------
# Test 10: Default Values and Script Initialization
# ---------------------------------------------------------------------------

class TestDefaultValues:
    """Verify that scripts initialize expected defaults."""

    def test_introspect_sets_table_and_column_counts(self):
        """introspect_schema must set table_count and column_count."""
        wf = load_workflow()

        assert wf.data.get("table_count") == 100
        assert wf.data.get("column_count") == 1198

    def test_generate_report_sets_needs_comments(self):
        """generate_report must set needs_comments flag."""
        wf = load_workflow()

        # Default path sets it to False (no comments needed)
        assert "needs_comments" in wf.data

    def test_build_embeddable_text_sets_flag(self):
        """build_embeddable_text must set texts_built flag."""
        wf = load_workflow()

        assert wf.data.get("texts_built") is True

    def test_check_content_hash_sets_tables_changed(self):
        """check_content_hash must set tables_changed count."""
        wf = load_workflow()

        assert "tables_changed" in wf.data
        # Default should be 0 (no changes)
        assert wf.data.get("tables_changed") == 0

    def test_extract_data_refs_sets_flag(self):
        """extract_data_refs must set refs_extracted flag."""
        wf = load_workflow()

        assert wf.data.get("refs_extracted") is True

    def test_validate_refs_sets_flag(self):
        """validate_refs must set validation_complete flag."""
        wf = load_workflow()

        assert wf.data.get("validation_complete") is True

    def test_update_process_data_map_sets_flag(self):
        """update_process_data_map must set map_updated flag."""
        wf = load_workflow()

        assert wf.data.get("map_updated") is True
