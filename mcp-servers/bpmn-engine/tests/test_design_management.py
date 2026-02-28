"""
Tests for two Design Management BPMN processes.

Each process lives in its own BPMN file under processes/lifecycle/.
This module covers all execution paths for:

  1. design_document_lifecycle      - 7 paths
  2. design_structural_validation   - 4 paths

NOTE: SpiffWorkflow evaluates ALL gateway conditions even on non-taken paths.
All condition variables MUST be present in DEFAULT_DATA to prevent NameError.

Implementation files:
  processes/lifecycle/design_document_lifecycle.bpmn
  processes/lifecycle/design_structural_validation.bpmn
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


# ===========================================================================
# 1. DESIGN DOCUMENT LIFECYCLE
# ===========================================================================

_LIFECYCLE_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "design_document_lifecycle.bpmn"
    )
)
_VALIDATION_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "design_structural_validation.bpmn"
    )
)
_LIFECYCLE_PROCESS_ID = "design_document_lifecycle"

# All gateway condition variables with safe defaults:
# - phase_gw default → brainstorm (when phase is not consolidation/validation/handoff)
# - consolidation_needed_gw default → not needed (areas_complete < 3 OR unindexed_files < 5)
# - all_extracted_gw default → loop back (unindexed_files != 0)
# - human_decision_gw default → accept (when decision != "resolve" and findings_count != 0)
# - post_consolidation_gw default → iteration_complete (ready_for_validation != True)
_LIFECYCLE_DEFAULT_DATA = {
    "phase": "brainstorm",              # phase_gw: default path
    "areas_complete": 0,                # consolidation_needed_gw: condition requires >= 3
    "unindexed_files": 0,               # consolidation_needed_gw + all_extracted_gw
    "decision": "accept",               # human_decision_gw: default path
    "findings_count": 1,                # human_decision_gw: clean path requires == 0
    "ready_for_validation": False,      # post_consolidation_gw: default (iteration_complete)
    # Variables needed by the called design_structural_validation subprocess:
    "concept_index_count": 0,           # index_exists_gw: condition requires > 0
    "error_count": 0,                   # severity_gw: condition requires > 0
}


def _load_lifecycle(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh design_document_lifecycle workflow with default data applied.

    Loads both the lifecycle and validation BPMN files because lifecycle
    contains callActivity elements that reference the validation process.
    """
    parser = BpmnParser()
    parser.add_bpmn_file(_LIFECYCLE_BPMN)
    parser.add_bpmn_file(_VALIDATION_BPMN)
    spec = parser.get_spec(_LIFECYCLE_PROCESS_ID)
    subspecs = parser.get_subprocess_specs(_LIFECYCLE_PROCESS_ID)
    wf = BpmnWorkflow(spec, subspecs)
    initial_data = dict(_LIFECYCLE_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _get_ready_user_tasks_lifecycle(wf: BpmnWorkflow) -> list:
    return wf.get_tasks(state=TaskState.READY, manual=True)


def _ready_task_names_lifecycle(wf: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in _get_ready_user_tasks_lifecycle(wf)]


def _complete_user_task_lifecycle(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    ready = _get_ready_user_tasks_lifecycle(wf)
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


def _completed_lifecycle_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


def _end_event_names(wf: BpmnWorkflow) -> set:
    """Return set of end event names that were reached."""
    end_events = {"end_continue_brainstorm", "end_iteration_complete", "end_complete"}
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)
            if t.task_spec.name in end_events}


# ---------------------------------------------------------------------------
# Test 1: Brainstorm — no consolidation (insufficient content)
# ---------------------------------------------------------------------------

class TestLifecycleBrainstormNoConsolidation:
    """
    Brainstorm phase with areas_complete < 3 or unindexed_files < 5.
    Flow: load_design_map (auto) → brainstorm_work → capture_concepts → write_vault_files
          → session_handoff → post_brainstorm_validate (callActivity, auto)
          → consolidation_needed_gw (default) → end_continue_brainstorm
    """

    def test_brainstorm_no_consolidation(self):
        wf = _load_lifecycle(data_overrides={
            "phase": "brainstorm",
            "areas_complete": 1,      # < 3: not enough
            "unindexed_files": 2,     # < 5: not enough
        })

        # load_design_map is a scriptTask — auto-completed by do_engine_steps()
        # First ready task should be brainstorm_work (userTask)
        ready = _ready_task_names_lifecycle(wf)
        assert "brainstorm_work" in ready, \
            f"Expected brainstorm_work ready, got: {ready}"

        # Step through: brainstorm_work → capture_concepts → write_vault_files → session_handoff
        _complete_user_task_lifecycle(wf, "brainstorm_work")
        ready = _ready_task_names_lifecycle(wf)
        assert "capture_concepts" in ready

        _complete_user_task_lifecycle(wf, "capture_concepts")
        ready = _ready_task_names_lifecycle(wf)
        assert "write_vault_files" in ready

        _complete_user_task_lifecycle(wf, "write_vault_files")
        ready = _ready_task_names_lifecycle(wf)
        assert "session_handoff" in ready

        _complete_user_task_lifecycle(wf, "session_handoff")

        # post_brainstorm_validate is a callActivity to design_structural_validation
        # The called process has all scriptTasks → auto-completes
        # After callActivity completes, consolidation_needed_gw evaluates
        # areas_complete < 3 OR unindexed_files < 5 → condition False → default path

        assert wf.is_completed(), "Workflow should complete"
        end_events = _end_event_names(wf)
        assert "end_continue_brainstorm" in end_events, \
            f"Expected end_continue_brainstorm, got: {end_events}"


# ---------------------------------------------------------------------------
# Test 2: Consolidation — accept findings (default decision)
# ---------------------------------------------------------------------------

class TestLifecycleConsolidationAcceptDefault:
    """
    Consolidation phase with findings_count != 0 and decision="accept" (default).
    Flow: extract_concepts (unindexed_files=0 to skip loop) → all_extracted_gw
          → map_concepts → check_conflicts → report_findings
          → human_decision_gw (default "accept") → accept_findings (script, auto)
          → generate_design_map → post_consolidation_gw (default) → end_iteration_complete
    """

    def test_consolidation_accept_findings(self):
        wf = _load_lifecycle(data_overrides={
            "phase": "consolidation",
            "unindexed_files": 0,     # Exit extract loop immediately
            "decision": "accept",     # Default decision
            "findings_count": 2,      # Non-zero (won't trigger clean path)
            "ready_for_validation": False,
        })

        # First ready task: extract_concepts
        ready = _ready_task_names_lifecycle(wf)
        assert "extract_concepts" in ready

        # Complete extract_concepts → all_extracted_gw checks unindexed_files == 0 → True
        _complete_user_task_lifecycle(wf, "extract_concepts")
        ready = _ready_task_names_lifecycle(wf)
        assert "map_concepts" in ready

        # map_concepts → check_conflicts
        _complete_user_task_lifecycle(wf, "map_concepts")
        ready = _ready_task_names_lifecycle(wf)
        assert "check_conflicts" in ready

        # check_conflicts → report_findings
        _complete_user_task_lifecycle(wf, "check_conflicts")
        ready = _ready_task_names_lifecycle(wf)
        assert "report_findings" in ready

        # report_findings → human_decision_gw
        # decision="accept" (default) → accept_findings (scriptTask, auto)
        _complete_user_task_lifecycle(wf, "report_findings")

        # accept_findings and generate_design_map are scriptTasks → auto-complete
        # post_consolidation_gw checks ready_for_validation == True → False (default) → end_iteration_complete

        assert wf.is_completed()
        end_events = _end_event_names(wf)
        assert "end_iteration_complete" in end_events, \
            f"Expected end_iteration_complete, got: {end_events}"


# ---------------------------------------------------------------------------
# Test 3: Consolidation — clean findings (zero findings)
# ---------------------------------------------------------------------------

class TestLifecycleConsolidationClean:
    """
    Consolidation phase with findings_count == 0 (clean path).
    Flow: extract_concepts → all_extracted_gw → map_concepts → check_conflicts
          → report_findings → human_decision_gw (condition: findings_count == 0)
          → generate_design_map (direct, skips accept_findings) → post_consolidation_gw → end_iteration_complete
    """

    def test_consolidation_clean_findings(self):
        wf = _load_lifecycle(data_overrides={
            "phase": "consolidation",
            "unindexed_files": 0,
            "findings_count": 0,      # Clean: no findings
            "ready_for_validation": False,
        })

        ready = _ready_task_names_lifecycle(wf)
        assert "extract_concepts" in ready

        _complete_user_task_lifecycle(wf, "extract_concepts")
        ready = _ready_task_names_lifecycle(wf)
        assert "map_concepts" in ready

        _complete_user_task_lifecycle(wf, "map_concepts")
        ready = _ready_task_names_lifecycle(wf)
        assert "check_conflicts" in ready

        _complete_user_task_lifecycle(wf, "check_conflicts")
        ready = _ready_task_names_lifecycle(wf)
        assert "report_findings" in ready

        # report_findings → human_decision_gw
        # findings_count == 0 → flow_clean → generate_design_map (direct)
        # Skips accept_findings
        _complete_user_task_lifecycle(wf, "report_findings")

        # generate_design_map auto-completes → post_consolidation_gw (default) → end_iteration_complete

        assert wf.is_completed()
        completed = _completed_lifecycle_names(wf)
        # accept_findings should NOT be in completed (clean path skips it)
        assert "accept_findings" not in completed
        # But generate_design_map should be
        assert "generate_design_map" in completed

        end_events = _end_event_names(wf)
        assert "end_iteration_complete" in end_events


# ---------------------------------------------------------------------------
# Test 4: Consolidation — resolve findings (loop)
# ---------------------------------------------------------------------------

class TestLifecycleConsolidationResolveLoop:
    """
    Consolidation with decision="resolve": creates a loop back to check_conflicts.
    Flow: extract_concepts → ... → report_findings → human_decision_gw (decision="resolve")
          → resolve_findings (userTask) → flow_recheck → check_conflicts (loop back)
          → report_findings (again, with decision="accept") → accept_findings → generate_design_map
    """

    def test_consolidation_resolve_loop(self):
        wf = _load_lifecycle(data_overrides={
            "phase": "consolidation",
            "unindexed_files": 0,
            "decision": "resolve",    # Triggers resolve path
            "findings_count": 1,
            "ready_for_validation": False,
        })

        # Fast-forward through extract → map → check
        ready = _ready_task_names_lifecycle(wf)
        _complete_user_task_lifecycle(wf, "extract_concepts")
        ready = _ready_task_names_lifecycle(wf)
        _complete_user_task_lifecycle(wf, "map_concepts")
        ready = _ready_task_names_lifecycle(wf)
        _complete_user_task_lifecycle(wf, "check_conflicts")
        ready = _ready_task_names_lifecycle(wf)
        _complete_user_task_lifecycle(wf, "report_findings")

        # Now human_decision_gw evaluates decision="resolve" → resolve_findings
        ready = _ready_task_names_lifecycle(wf)
        assert "resolve_findings" in ready, \
            f"Expected resolve_findings after report_findings with decision='resolve', got: {ready}"

        # Complete resolve_findings → flow_recheck → check_conflicts (loop back)
        _complete_user_task_lifecycle(wf, "resolve_findings")
        ready = _ready_task_names_lifecycle(wf)
        assert "check_conflicts" in ready, \
            f"Expected loop back to check_conflicts after resolve_findings, got: {ready}"

        # Complete loop: check_conflicts → report_findings (again)
        _complete_user_task_lifecycle(wf, "check_conflicts")
        ready = _ready_task_names_lifecycle(wf)
        # Change decision to "accept" so we exit the loop this time
        _complete_user_task_lifecycle(wf, "report_findings", data={"decision": "accept"})

        # Second iteration: decision="accept" → accept_findings → generate_design_map

        assert wf.is_completed()
        completed = _completed_lifecycle_names(wf)
        # check_conflicts should be in completed twice (once per iteration)
        check_count = sum(1 for t in wf.get_tasks(state=TaskState.COMPLETED)
                         if t.task_spec.name == "check_conflicts")
        assert check_count == 2, f"Expected check_conflicts to execute 2 times (loop), got {check_count}"


# ---------------------------------------------------------------------------
# Test 5: Consolidation to validation
# ---------------------------------------------------------------------------

class TestLifecycleConsolidationToValidation:
    """
    Consolidation with ready_for_validation=True routes to validation flow.
    Flow: consolidation → generate_design_map → post_consolidation_gw (ready_for_validation=True)
          → structural_validation → semantic_validation → ... → end_complete
    """

    def test_consolidation_to_validation(self):
        wf = _load_lifecycle(data_overrides={
            "phase": "consolidation",
            "unindexed_files": 0,
            "findings_count": 0,
            "ready_for_validation": True,  # Routes to validation after consolidation
        })

        # Fast-forward through consolidation
        _complete_user_task_lifecycle(wf, "extract_concepts")
        _complete_user_task_lifecycle(wf, "map_concepts")
        _complete_user_task_lifecycle(wf, "check_conflicts")
        _complete_user_task_lifecycle(wf, "report_findings")

        # report_findings → human_decision_gw (findings_count=0) → generate_design_map
        # generate_design_map → post_consolidation_gw (ready_for_validation=True) → structural_validation

        # After consolidation, should reach validation phase
        ready = _ready_task_names_lifecycle(wf)
        # After callActivity completes, next ready task should be semantic_validation (userTask)
        assert "semantic_validation" in ready, \
            f"Expected semantic_validation after callActivity, got: {ready}"

        # Complete semantic_validation → bpmn_schema_validate (auto) → validation_report
        _complete_user_task_lifecycle(wf, "semantic_validation")
        ready = _ready_task_names_lifecycle(wf)
        assert "validation_report" in ready

        # validation_report → package_deliverables → end_complete
        _complete_user_task_lifecycle(wf, "validation_report")
        ready = _ready_task_names_lifecycle(wf)
        assert "package_deliverables" in ready

        _complete_user_task_lifecycle(wf, "package_deliverables")

        assert wf.is_completed()
        end_events = _end_event_names(wf)
        assert "end_complete" in end_events


# ---------------------------------------------------------------------------
# Test 6: Direct validation phase
# ---------------------------------------------------------------------------

class TestLifecycleValidationDirect:
    """
    Direct validation phase: phase="validation".
    Flow: structural_validation (callActivity, auto) → semantic_validation → bpmn_schema_validate
          → validation_report → package_deliverables → end_complete
    """

    def test_validation_direct(self):
        wf = _load_lifecycle(data_overrides={
            "phase": "validation",
        })

        # structural_validation is a callActivity with all scriptTasks in called process → auto-completes
        ready = _ready_task_names_lifecycle(wf)
        assert "semantic_validation" in ready, \
            f"Expected semantic_validation after structural_validation callActivity, got: {ready}"

        _complete_user_task_lifecycle(wf, "semantic_validation")
        ready = _ready_task_names_lifecycle(wf)
        assert "validation_report" in ready

        _complete_user_task_lifecycle(wf, "validation_report")
        ready = _ready_task_names_lifecycle(wf)
        assert "package_deliverables" in ready

        _complete_user_task_lifecycle(wf, "package_deliverables")

        assert wf.is_completed()
        end_events = _end_event_names(wf)
        assert "end_complete" in end_events


# ---------------------------------------------------------------------------
# Test 7: Direct handoff phase
# ---------------------------------------------------------------------------

class TestLifecycleHandoffDirect:
    """
    Direct handoff phase: phase="handoff".
    Flow: final_design_map (scriptTask, auto) → package_deliverables → end_complete
    """

    def test_handoff_direct(self):
        wf = _load_lifecycle(data_overrides={
            "phase": "handoff",
        })

        # final_design_map auto-completes → package_deliverables
        ready = _ready_task_names_lifecycle(wf)
        assert "package_deliverables" in ready, \
            f"Expected package_deliverables after final_design_map, got: {ready}"

        _complete_user_task_lifecycle(wf, "package_deliverables")

        assert wf.is_completed()
        end_events = _end_event_names(wf)
        assert "end_complete" in end_events


# ---------------------------------------------------------------------------
# Sanity Tests
# ---------------------------------------------------------------------------

class TestLifecycleWorkflowValidation:
    """Basic structural checks for the lifecycle workflow."""

    def test_workflow_loads_successfully(self):
        """Workflow should load both BPMN files without error."""
        wf = _load_lifecycle()
        assert wf is not None
        assert wf.spec is not None

    def test_default_phase_is_brainstorm(self):
        """Default phase='brainstorm' should have brainstorm tasks ready."""
        wf = _load_lifecycle()
        ready = _ready_task_names_lifecycle(wf)
        # load_design_map is scriptTask (auto-completes), so first ready is brainstorm_work
        assert "brainstorm_work" in ready, \
            f"Expected brainstorm_work ready in default phase, got: {ready}"

    def test_phase_gateway_routes_all_phases(self):
        """Verify all 4 phases are reachable without error."""
        phases = ["brainstorm", "consolidation", "validation", "handoff"]
        for phase in phases:
            wf = _load_lifecycle(data_overrides={
                "phase": phase,
                "unindexed_files": 0,
                "findings_count": 0,
            })
            assert wf is not None, f"Failed to load phase={phase}"
            # Verify at least one task is ready or workflow completes (for all-scriptTask paths)
            if not wf.is_completed():
                ready = _ready_task_names_lifecycle(wf)
                assert len(ready) > 0, f"No ready tasks for phase={phase}"


# ===========================================================================
# 2. DESIGN STRUCTURAL VALIDATION
# ===========================================================================

_STRUCT_VALIDATION_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "design_structural_validation.bpmn"
    )
)
_STRUCT_VALIDATION_PROCESS_ID = "design_structural_validation"

# All gateway condition variables with safe defaults:
# - index_exists_gw default → no index (concept_index_count <= 0)
# - severity_gw default → passed (error_count <= 0)
_STRUCT_VALIDATION_DEFAULT_DATA = {
    "concept_index_count": 0,   # index_exists_gw: condition requires > 0
    "error_count": 0,           # severity_gw: condition requires > 0
}


def _load_struct_validation(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh design_structural_validation workflow."""
    parser = BpmnParser()
    parser.add_bpmn_file(_STRUCT_VALIDATION_BPMN)
    spec = parser.get_spec(_STRUCT_VALIDATION_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_STRUCT_VALIDATION_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _completed_struct_validation_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


def _struct_validation_end_events(wf: BpmnWorkflow) -> set:
    """Return set of end event names that were reached."""
    end_events = {"end_with_errors", "end_passed"}
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)
            if t.task_spec.name in end_events}


# ---------------------------------------------------------------------------
# Validation P1: No index, no errors → passed
# ---------------------------------------------------------------------------

class TestStructValidationNoIndexNoErrors:
    """No concept index, no validation errors → ends at end_passed."""

    def test_validation_no_index_no_errors_passes(self):
        wf = _load_struct_validation(data_overrides={
            "concept_index_count": 0,
            "error_count": 0,
        })

        # All tasks are scriptTasks (no userTasks) — should auto-complete
        assert wf.is_completed(), "Workflow should complete without user intervention"

        completed = _completed_struct_validation_names(wf)

        # Should execute all 5 parallel checks
        assert "discover_files" in completed
        assert "check_links" in completed
        assert "check_frontmatter" in completed
        assert "check_footers" in completed
        assert "check_orphans" in completed
        assert "check_terminology" in completed

        # Should skip index checks (index_exists_gw default path)
        assert "index_checks" not in completed

        # Should generate report
        assert "generate_report" in completed

        # Should end at passed (severity_gw default path)
        assert "file_feedback" not in completed
        end_events = _struct_validation_end_events(wf)
        assert "end_passed" in end_events


# ---------------------------------------------------------------------------
# Validation P2: With index, no errors → passed
# ---------------------------------------------------------------------------

class TestStructValidationWithIndexNoErrors:
    """Concept index exists (count > 0), no errors → runs index checks, ends at passed."""

    def test_validation_with_index_no_errors_passes(self):
        wf = _load_struct_validation(data_overrides={
            "concept_index_count": 10,
            "error_count": 0,
        })

        assert wf.is_completed()
        completed = _completed_struct_validation_names(wf)

        # Should execute all 5 parallel checks
        assert "discover_files" in completed
        assert "check_links" in completed
        assert "check_frontmatter" in completed
        assert "check_footers" in completed
        assert "check_orphans" in completed
        assert "check_terminology" in completed

        # Should run index checks (index_exists_gw condition True)
        assert "index_checks" in completed

        # Should generate report
        assert "generate_report" in completed

        # Should NOT file feedback (severity_gw default path)
        assert "file_feedback" not in completed
        end_events = _struct_validation_end_events(wf)
        assert "end_passed" in end_events


# ---------------------------------------------------------------------------
# Validation P3: No index, with errors → errors filed
# ---------------------------------------------------------------------------

class TestStructValidationNoIndexWithErrors:
    """No concept index, but validation errors found → files feedback, ends with errors."""

    def test_validation_no_index_with_errors_files_feedback(self):
        wf = _load_struct_validation(data_overrides={
            "concept_index_count": 0,
            "error_count": 5,
        })

        assert wf.is_completed()
        completed = _completed_struct_validation_names(wf)

        # Should execute all 5 parallel checks
        assert "discover_files" in completed
        assert "check_links" in completed
        assert "check_frontmatter" in completed
        assert "check_footers" in completed
        assert "check_orphans" in completed
        assert "check_terminology" in completed

        # Should skip index checks
        assert "index_checks" not in completed

        # Should generate report
        assert "generate_report" in completed

        # Should file feedback (severity_gw condition True)
        assert "file_feedback" in completed
        end_events = _struct_validation_end_events(wf)
        assert "end_with_errors" in end_events


# ---------------------------------------------------------------------------
# Validation P4: With index and errors → index checks + feedback + errors
# ---------------------------------------------------------------------------

class TestStructValidationWithIndexAndErrors:
    """Concept index exists, validation errors found → runs index checks, files feedback."""

    def test_validation_with_index_and_errors_files_feedback(self):
        wf = _load_struct_validation(data_overrides={
            "concept_index_count": 10,
            "error_count": 3,
        })

        assert wf.is_completed()
        completed = _completed_struct_validation_names(wf)

        # Should execute all 5 parallel checks
        assert "discover_files" in completed
        assert "check_links" in completed
        assert "check_frontmatter" in completed
        assert "check_footers" in completed
        assert "check_orphans" in completed
        assert "check_terminology" in completed

        # Should run index checks
        assert "index_checks" in completed

        # Should generate report
        assert "generate_report" in completed

        # Should file feedback
        assert "file_feedback" in completed
        end_events = _struct_validation_end_events(wf)
        assert "end_with_errors" in end_events


# ---------------------------------------------------------------------------
# Validation Sanity Tests
# ---------------------------------------------------------------------------

class TestStructValidationWorkflowValidation:
    """Basic structural checks for the validation workflow."""

    def test_workflow_loads_successfully(self):
        wf = _load_struct_validation()
        assert wf is not None
        assert wf.spec is not None

    def test_no_user_tasks_in_validation(self):
        """All tasks are scriptTasks — no manual intervention needed."""
        wf = _load_struct_validation()
        user_tasks = wf.get_tasks(state=TaskState.READY, manual=True)
        assert user_tasks == [], "Validation should have no manual userTasks"

    def test_workflow_completes_without_intervention(self):
        """Workflow should auto-complete without user interaction."""
        wf = _load_struct_validation()
        assert wf.is_completed()

    def test_parallel_checks_all_execute(self):
        """Verify all 5 parallel checks execute regardless of conditions."""
        wf = _load_struct_validation()
        completed = _completed_struct_validation_names(wf)

        checks = ["check_links", "check_frontmatter", "check_footers",
                  "check_orphans", "check_terminology"]
        for check in checks:
            assert check in completed, f"Expected {check} to execute"

    def test_severity_gateway_routes_correctly(self):
        """Verify severity_gw correctly routes based on error_count."""
        # With errors: should file_feedback
        wf_errors = _load_struct_validation(data_overrides={"error_count": 5})
        assert wf_errors.is_completed()
        completed_errors = _completed_struct_validation_names(wf_errors)
        assert "file_feedback" in completed_errors

        # Without errors: should NOT file_feedback
        wf_no_errors = _load_struct_validation(data_overrides={"error_count": 0})
        assert wf_no_errors.is_completed()
        completed_no_errors = _completed_struct_validation_names(wf_no_errors)
        assert "file_feedback" not in completed_no_errors

    def test_index_gateway_routes_correctly(self):
        """Verify index_exists_gw correctly routes based on concept_index_count."""
        # With index: should run index_checks
        wf_with_index = _load_struct_validation(data_overrides={"concept_index_count": 10})
        assert wf_with_index.is_completed()
        completed_with_index = _completed_struct_validation_names(wf_with_index)
        assert "index_checks" in completed_with_index

        # Without index: should skip index_checks
        wf_no_index = _load_struct_validation(data_overrides={"concept_index_count": 0})
        assert wf_no_index.is_completed()
        completed_no_index = _completed_struct_validation_names(wf_no_index)
        assert "index_checks" not in completed_no_index
