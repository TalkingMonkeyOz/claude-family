"""
Tests for four Cognitive Memory BPMN processes.

Each process lives in its own BPMN file under processes/lifecycle/.
This module covers all execution paths across the four processes:

  1. cognitive_memory_capture      - 6 paths (P1-P6)
  2. cognitive_memory_retrieval    - 2 paths (P1-P2, all script tasks, auto-completes)
  3. cognitive_memory_consolidation - 5 paths (P1-P5)
  4. cognitive_memory_contradiction - 8 paths (P1-P8)

NOTE: SpiffWorkflow evaluates ALL gateway conditions even on non-taken paths.
All condition variables MUST be present in DEFAULT_DATA to prevent NameError.

Implementation files:
  processes/lifecycle/cognitive_memory_capture.bpmn
  processes/lifecycle/cognitive_memory_retrieval.bpmn
  processes/lifecycle/cognitive_memory_consolidation.bpmn
  processes/lifecycle/cognitive_memory_contradiction.bpmn
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


# ===========================================================================
# 1. COGNITIVE MEMORY CAPTURE
# ===========================================================================

_CAPTURE_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "cognitive_memory_capture.bpmn"
    )
)
_CAPTURE_PROCESS_ID = "cognitive_memory_capture"

# All gateway condition variables initialised to default (non-matching) values.
# - source_gw default → flow_session_harvest (when source is not "explicit"/"auto_detect")
# - significance_gw default → flow_not_significant (significance_score < 0.5)
# - dedup_gw default → flow_not_dup (is_duplicate == False)
# - relation_gw default → flow_no_relations (has_nearby_knowledge == False)
_CAPTURE_DEFAULT_DATA = {
    "source": "session_harvest",    # source_gw: no condition matches → default (harvest)
    "significance_score": 0.0,      # significance_gw: < 0.8 → default (discard)
    "is_duplicate": False,          # dedup_gw: not True → default (not dup)
    "has_nearby_knowledge": False,  # relation_gw: not True → default (no relations)
}


def _load_capture(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh cognitive_memory_capture workflow with default data applied."""
    parser = BpmnParser()
    parser.add_bpmn_file(_CAPTURE_BPMN)
    spec = parser.get_spec(_CAPTURE_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_CAPTURE_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _get_ready_user_tasks_capture(wf: BpmnWorkflow) -> list:
    return wf.get_tasks(state=TaskState.READY, manual=True)


def _ready_task_names_capture(wf: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in _get_ready_user_tasks_capture(wf)]


def _complete_user_task_capture(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    ready = _get_ready_user_tasks_capture(wf)
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


def _completed_capture_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Capture P1: Explicit source, not duplicate, has nearby knowledge (link)
# ---------------------------------------------------------------------------

class TestCaptureExplicitWithRelations:
    """Explicit memory with no duplicate found and nearby knowledge to link."""

    def test_explicit_not_dup_with_relations(self):
        wf = _load_capture(data_overrides={
            "source": "explicit",
            "is_duplicate": False,
            "has_nearby_knowledge": True,
        })

        # formulate_memory is the only userTask; it sits on the explicit path
        assert "formulate_memory" in _ready_task_names_capture(wf)
        _complete_user_task_capture(wf, "formulate_memory")

        assert wf.is_completed()
        names = _completed_capture_names(wf)

        assert "formulate_memory" in names
        assert "classify_tier" in names
        assert "dedup_check" in names
        assert "generate_embedding" in names
        assert "store_memory" in names
        assert "link_relations" in names
        assert "merge_existing" not in names
        assert "auto_extract" not in names
        assert "harvest_session" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Capture P2: Explicit source, duplicate found (merge path)
# ---------------------------------------------------------------------------

class TestCaptureExplicitDuplicate:
    """Explicit memory that turns out to be a duplicate – merges into existing."""

    def test_explicit_duplicate_merge(self):
        wf = _load_capture(data_overrides={
            "source": "explicit",
            "is_duplicate": True,
            "has_nearby_knowledge": False,
        })

        assert "formulate_memory" in _ready_task_names_capture(wf)
        _complete_user_task_capture(wf, "formulate_memory")

        assert wf.is_completed()
        names = _completed_capture_names(wf)

        assert "formulate_memory" in names
        assert "classify_tier" in names
        assert "dedup_check" in names
        assert "merge_existing" in names
        assert "generate_embedding" not in names
        assert "store_memory" not in names
        assert "link_relations" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Capture P3: Auto-detect, significance >= 0.5 (significant, stored)
# ---------------------------------------------------------------------------

class TestCaptureAutoSignificant:
    """Auto-detected candidate above significance threshold is captured."""

    def test_auto_detect_significant_stored(self):
        wf = _load_capture(data_overrides={
            "source": "auto_detect",
            "significance_score": 0.9,
            "is_duplicate": False,
            "has_nearby_knowledge": False,
        })

        # No userTask on this path – workflow should run to completion
        assert wf.is_completed()
        names = _completed_capture_names(wf)

        assert "auto_extract" in names
        assert "classify_tier" in names
        assert "dedup_check" in names
        assert "generate_embedding" in names
        assert "store_memory" in names
        assert "formulate_memory" not in names
        assert "harvest_session" not in names
        assert "end_discard" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Capture P4: Auto-detect, significance < 0.5 (discarded)
# ---------------------------------------------------------------------------

class TestCaptureAutoNotSignificant:
    """Auto-detected candidate below significance threshold is discarded."""

    def test_auto_detect_not_significant_discarded(self):
        wf = _load_capture(data_overrides={
            "source": "auto_detect",
            "significance_score": 0.5,
        })

        assert wf.is_completed()
        names = _completed_capture_names(wf)

        assert "auto_extract" in names
        assert "end_discard" in names
        assert "classify_tier" not in names
        assert "store_memory" not in names
        assert "end" not in names


# ---------------------------------------------------------------------------
# Capture P5: Session harvest (default source path)
# ---------------------------------------------------------------------------

class TestCaptureSessionHarvest:
    """Session-end harvest path (default when source is neither explicit nor auto_detect)."""

    def test_session_harvest_stored(self):
        # Default data: source="session_harvest" → hits default flow → harvest_session
        wf = _load_capture()

        assert wf.is_completed()
        names = _completed_capture_names(wf)

        assert "harvest_session" in names
        assert "classify_tier" in names
        assert "dedup_check" in names
        assert "generate_embedding" in names
        assert "store_memory" in names
        assert "formulate_memory" not in names
        assert "auto_extract" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Capture P6: Sanity – workflow loads and produces the expected first task
# ---------------------------------------------------------------------------

class TestCaptureWorkflowValidation:
    """Basic structural checks for the capture workflow."""

    def test_workflow_loads_successfully(self):
        wf = _load_capture(data_overrides={"source": "explicit"})
        assert wf is not None
        assert wf.spec is not None

    def test_explicit_path_first_ready_task_is_formulate_memory(self):
        wf = _load_capture(data_overrides={"source": "explicit"})
        assert "formulate_memory" in _ready_task_names_capture(wf)

    def test_harvest_path_runs_to_completion_without_user_tasks(self):
        wf = _load_capture()
        # No manual tasks on the harvest path
        assert _ready_task_names_capture(wf) == []
        assert wf.is_completed()


# ===========================================================================
# 2. COGNITIVE MEMORY RETRIEVAL
# ===========================================================================

_RETRIEVAL_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "cognitive_memory_retrieval.bpmn"
    )
)
_RETRIEVAL_PROCESS_ID = "cognitive_memory_retrieval"

# No exclusive gateways with conditions – parallel gateway auto-joins.
# No variables needed, but we provide an empty dict for clarity.
_RETRIEVAL_DEFAULT_DATA: dict = {}


def _load_retrieval(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh cognitive_memory_retrieval workflow."""
    parser = BpmnParser()
    parser.add_bpmn_file(_RETRIEVAL_BPMN)
    spec = parser.get_spec(_RETRIEVAL_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_RETRIEVAL_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _completed_retrieval_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Retrieval P1: Full retrieval – all tasks execute, workflow completes
# ---------------------------------------------------------------------------

class TestRetrievalFullCycle:
    """All script tasks execute via the parallel search pattern."""

    def test_full_retrieval_runs_all_tasks(self):
        wf = _load_retrieval()

        # No userTasks – should be complete immediately after do_engine_steps
        assert wf.is_completed()
        names = _completed_retrieval_names(wf)

        assert "parse_context" in names
        assert "allocate_budget" in names
        assert "search_short" in names
        assert "search_mid" in names
        assert "search_long" in names
        assert "rank_results" in names
        assert "trim_to_budget" in names
        assert "format_output" in names
        assert "update_access" in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Retrieval P2: Sanity – workflow loads and has no pending user tasks
# ---------------------------------------------------------------------------

class TestRetrievalWorkflowValidation:
    """Basic structural checks for the retrieval workflow."""

    def test_workflow_loads_successfully(self):
        wf = _load_retrieval()
        assert wf is not None
        assert wf.spec is not None

    def test_no_user_tasks_required(self):
        wf = _load_retrieval()
        # Pure script workflow – no manual intervention needed
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []

    def test_workflow_completes_without_intervention(self):
        wf = _load_retrieval()
        assert wf.is_completed()


# ===========================================================================
# 3. COGNITIVE MEMORY CONSOLIDATION
# ===========================================================================

_CONSOLIDATION_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "cognitive_memory_consolidation.bpmn"
    )
)
_CONSOLIDATION_PROCESS_ID = "cognitive_memory_consolidation"

# All gateway condition variables with values that take default paths:
# - trigger_gw default → flow_manual (collect_short)
# - promote_short_gw default → flow_skip_promote_short (no promotions)
# - check_continues default → flow_stop_after_short (session_end trigger)
# - promote_mid_gw default → flow_skip_promote_long (no long promotions)
# - stale_gw default → flow_no_stale (no stale entries)
_CONSOLIDATION_DEFAULT_DATA = {
    "trigger": "session_end",       # trigger_gw: "session_end" → flow_session_end
    "has_promotions": False,        # promote_short_gw: not True → skip → default
    "has_long_promotions": False,   # promote_mid_gw: not True → skip → default
    "has_stale": False,             # stale_gw: not True → no_stale → default
}


def _load_consolidation(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh cognitive_memory_consolidation workflow."""
    parser = BpmnParser()
    parser.add_bpmn_file(_CONSOLIDATION_BPMN)
    spec = parser.get_spec(_CONSOLIDATION_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_CONSOLIDATION_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _completed_consolidation_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Consolidation P1: Session end, has promotions, stops after Phase 1
# ---------------------------------------------------------------------------

class TestConsolidationSessionEndWithPromotions:
    """Session-end trigger promotes short→mid then stops (no Phase 2)."""

    def test_session_end_promotes_short_then_stops(self):
        wf = _load_consolidation(data_overrides={
            "trigger": "session_end",
            "has_promotions": True,
        })

        assert wf.is_completed()
        names = _completed_consolidation_names(wf)

        assert "collect_short" in names
        assert "evaluate_short" in names
        assert "promote_to_mid" in names
        # check_continues gate takes default (stop) for session_end
        assert "scan_mid" not in names
        assert "evaluate_mid" not in names
        assert "promote_to_long" not in names
        assert "run_decay" not in names
        assert "find_stale" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Consolidation P2: Session end, no promotions (skip Phase 1, stop)
# ---------------------------------------------------------------------------

class TestConsolidationSessionEndNoPromotions:
    """Session-end trigger with nothing worth promoting exits early."""

    def test_session_end_no_promotions_exits_early(self):
        wf = _load_consolidation(data_overrides={
            "trigger": "session_end",
            "has_promotions": False,
        })

        assert wf.is_completed()
        names = _completed_consolidation_names(wf)

        assert "collect_short" in names
        assert "evaluate_short" in names
        assert "promote_to_mid" not in names
        assert "scan_mid" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Consolidation P3: Periodic – Phase 2 only (promote long + archive stale)
# ---------------------------------------------------------------------------

class TestConsolidationPeriodicFullPhase2:
    """Periodic trigger skips Phase 1 and runs full Phase 2 + Phase 3."""

    def test_periodic_promote_long_and_archive_stale(self):
        wf = _load_consolidation(data_overrides={
            "trigger": "periodic",
            "has_long_promotions": True,
            "has_stale": True,
        })

        assert wf.is_completed()
        names = _completed_consolidation_names(wf)

        # Periodic skips short-term collection
        assert "collect_short" not in names
        assert "evaluate_short" not in names
        assert "promote_to_mid" not in names

        # Phase 2 should run fully
        assert "scan_mid" in names
        assert "evaluate_mid" in names
        assert "promote_to_long" in names
        assert "run_decay" in names
        assert "find_stale" in names
        assert "archive_stale" in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Consolidation P4: Manual – full cycle (Phase 1 → Phase 2 → Phase 3)
# ---------------------------------------------------------------------------

class TestConsolidationManualFullCycle:
    """Manual trigger runs Phase 1, continues to Phase 2 (via check_continues), then Phase 3."""

    def test_manual_full_cycle_no_long_promotions_no_stale(self):
        wf = _load_consolidation(data_overrides={
            "trigger": "manual",
            "has_promotions": True,
            "has_long_promotions": False,
            "has_stale": False,
        })

        assert wf.is_completed()
        names = _completed_consolidation_names(wf)

        # Phase 1 runs
        assert "collect_short" in names
        assert "evaluate_short" in names
        assert "promote_to_mid" in names

        # check_continues: trigger=="manual" matches condition → continues to Phase 2
        assert "scan_mid" in names
        assert "evaluate_mid" in names
        assert "promote_to_long" not in names    # has_long_promotions=False

        # Phase 3 runs (decay + stale check)
        assert "run_decay" in names
        assert "find_stale" in names
        assert "archive_stale" not in names      # has_stale=False
        assert "end" in names


# ---------------------------------------------------------------------------
# Consolidation P5: Sanity – workflow loads
# ---------------------------------------------------------------------------

class TestConsolidationWorkflowValidation:
    """Basic structural checks for the consolidation workflow."""

    def test_workflow_loads_successfully(self):
        wf = _load_consolidation()
        assert wf is not None
        assert wf.spec is not None

    def test_no_user_tasks_in_consolidation(self):
        wf = _load_consolidation()
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []

    def test_workflow_completes_without_intervention(self):
        wf = _load_consolidation()
        assert wf.is_completed()


# ===========================================================================
# 4. COGNITIVE MEMORY CONTRADICTION
# ===========================================================================

_CONTRADICTION_BPMN = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "lifecycle",
        "cognitive_memory_contradiction.bpmn"
    )
)
_CONTRADICTION_PROCESS_ID = "cognitive_memory_contradiction"

# All gateway condition variables with values that take default paths:
# - overlap_gw default → flow_no_overlap (has_overlap == False)
# - relationship_gw default → flow_supersedes (relationship_type not in extends/reinforces/contradicts)
# - resolution_gw default → flow_unclear (resolution not in newer_wins/older_wins)
_CONTRADICTION_DEFAULT_DATA = {
    "has_overlap": False,               # overlap_gw: not True → default (no overlap → end_clean)
    "relationship_type": "supersedes",  # relationship_gw: default path
    "resolution": "unclear",            # resolution_gw: default path
}


def _load_contradiction(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh cognitive_memory_contradiction workflow."""
    parser = BpmnParser()
    parser.add_bpmn_file(_CONTRADICTION_BPMN)
    spec = parser.get_spec(_CONTRADICTION_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_CONTRADICTION_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _completed_contradiction_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Contradiction P1: No overlap – clean exit (end_clean)
# ---------------------------------------------------------------------------

class TestContradictionNoOverlap:
    """No semantic overlap found: process ends at end_clean immediately."""

    def test_no_overlap_ends_clean(self):
        wf = _load_contradiction()  # defaults: has_overlap=False

        assert wf.is_completed()
        names = _completed_contradiction_names(wf)

        assert "search_overlap" in names
        assert "classify_relationship" not in names
        assert "end_clean" in names
        assert "end" not in names


# ---------------------------------------------------------------------------
# Contradiction P2: Overlap found, relationship = extends
# ---------------------------------------------------------------------------

class TestContradictionExtends:
    """Overlap found and new memory extends (adds detail to) existing."""

    def test_overlap_extends_links_both(self):
        wf = _load_contradiction(data_overrides={
            "has_overlap": True,
            "relationship_type": "extends",
        })

        assert wf.is_completed()
        names = _completed_contradiction_names(wf)

        assert "search_overlap" in names
        assert "classify_relationship" in names
        assert "handle_extends" in names
        assert "handle_reinforces" not in names
        assert "compare_contradicting" not in names
        assert "handle_supersedes" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Contradiction P3: Overlap found, relationship = reinforces
# ---------------------------------------------------------------------------

class TestContradictionReinforces:
    """Overlap found and new memory reinforces (confirms) existing."""

    def test_overlap_reinforces_boosts_confidence(self):
        wf = _load_contradiction(data_overrides={
            "has_overlap": True,
            "relationship_type": "reinforces",
        })

        assert wf.is_completed()
        names = _completed_contradiction_names(wf)

        assert "classify_relationship" in names
        assert "handle_reinforces" in names
        assert "handle_extends" not in names
        assert "compare_contradicting" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Contradiction P4: Contradicts, newer wins
# ---------------------------------------------------------------------------

class TestContradictionContradictsNewerWins:
    """Contradiction resolved: newer memory is more authoritative."""

    def test_contradicts_newer_wins_archives_old(self):
        wf = _load_contradiction(data_overrides={
            "has_overlap": True,
            "relationship_type": "contradicts",
            "resolution": "newer_wins",
        })

        assert wf.is_completed()
        names = _completed_contradiction_names(wf)

        assert "classify_relationship" in names
        assert "compare_contradicting" in names
        assert "newer_wins" in names
        assert "older_wins" not in names
        assert "flag_review" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Contradiction P5: Contradicts, older wins
# ---------------------------------------------------------------------------

class TestContradictionContradictsOlderWins:
    """Contradiction resolved: existing memory is more authoritative."""

    def test_contradicts_older_wins_reduces_new_confidence(self):
        wf = _load_contradiction(data_overrides={
            "has_overlap": True,
            "relationship_type": "contradicts",
            "resolution": "older_wins",
        })

        assert wf.is_completed()
        names = _completed_contradiction_names(wf)

        assert "compare_contradicting" in names
        assert "older_wins" in names
        assert "newer_wins" not in names
        assert "flag_review" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Contradiction P6: Contradicts, unclear (default resolution → flag review)
# ---------------------------------------------------------------------------

class TestContradictionContradictsUnclear:
    """Contradiction unresolvable: both flagged for human review."""

    def test_contradicts_unclear_flags_for_review(self):
        wf = _load_contradiction(data_overrides={
            "has_overlap": True,
            "relationship_type": "contradicts",
            "resolution": "unclear",
        })

        assert wf.is_completed()
        names = _completed_contradiction_names(wf)

        assert "compare_contradicting" in names
        assert "flag_review" in names
        assert "newer_wins" not in names
        assert "older_wins" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Contradiction P7: Overlap found, relationship = supersedes (default)
# ---------------------------------------------------------------------------

class TestContradictionSupersedes:
    """Overlap found and new memory supersedes (replaces) existing – the default path."""

    def test_overlap_supersedes_archives_old(self):
        wf = _load_contradiction(data_overrides={
            "has_overlap": True,
            "relationship_type": "supersedes",  # default path on relationship_gw
        })

        assert wf.is_completed()
        names = _completed_contradiction_names(wf)

        assert "classify_relationship" in names
        assert "handle_supersedes" in names
        assert "handle_extends" not in names
        assert "handle_reinforces" not in names
        assert "compare_contradicting" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Contradiction P8: Sanity
# ---------------------------------------------------------------------------

class TestContradictionWorkflowValidation:
    """Basic structural checks for the contradiction workflow."""

    def test_workflow_loads_successfully(self):
        wf = _load_contradiction()
        assert wf is not None
        assert wf.spec is not None

    def test_no_user_tasks_in_contradiction(self):
        wf = _load_contradiction()
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []

    def test_no_overlap_default_path_completes(self):
        wf = _load_contradiction()
        assert wf.is_completed()

    def test_all_relationship_types_reachable(self):
        """Verify each relationship type routes to its distinct handler task."""
        cases = [
            ("extends",     "handle_extends"),
            ("reinforces",  "handle_reinforces"),
            ("supersedes",  "handle_supersedes"),
        ]
        for rel_type, expected_task in cases:
            wf = _load_contradiction(data_overrides={
                "has_overlap": True,
                "relationship_type": rel_type,
            })
            names = _completed_contradiction_names(wf)
            assert expected_task in names, (
                f"relationship_type='{rel_type}' should reach '{expected_task}'"
            )
