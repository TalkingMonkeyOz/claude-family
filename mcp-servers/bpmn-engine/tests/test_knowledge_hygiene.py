"""
Tests for the Knowledge Hygiene BPMN process.

The knowledge_hygiene process is a single executable process with 5 phases
controlled by a ``gw_phase`` gateway routed via a ``phase`` data variable:

  1. CAPTURE   (default) - 6 storage routes + maintenance hint check
  2. RETRIEVE  (phase="retrieve") - active or passive retrieval
  3. MAINTAIN  (phase="maintain") - 11 maintenance actions (7 Claude + 4 User)
  4. PROMOTE   (phase="promote") - 3 promotion/decay triggers
  5. CURATE    (phase="curate") - 6-stage background curation pipeline

NOTE: SpiffWorkflow evaluates ALL gateway conditions even on non-taken paths.
All condition variables MUST be present in DEFAULT_DATA to prevent NameError.

Implementation file:
  processes/maintenance/knowledge_hygiene.bpmn
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


# ---------------------------------------------------------------------------
# Constants & Default Data
# ---------------------------------------------------------------------------

_BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "maintenance",
        "knowledge_hygiene.bpmn"
    )
)
_PROCESS_ID = "knowledge_hygiene"

# All gateway condition variables initialised to default (non-matching) values.
# - gw_phase default -> f_phase_capture (no condition matches)
# - gw_storage_route default -> f_route_memory (no condition matches)
# - gw_maint_hint default -> f_no_hint (no condition matches)
# - gw_retrieve_type default -> f_ret_active (no condition matches)
# - gw_maintain_action default -> f_maint_list (no condition matches)
# - gw_promote_trigger default -> f_trig_session_end (no condition matches)
_DEFAULT_DATA = {
    # Phase router (gw_phase)
    "phase": "",                           # default -> capture

    # Capture: storage route (gw_storage_route)
    "storage_target": "",                  # default -> remember()

    # Capture: maintenance hint (gw_maint_hint)
    "maintenance_hint_present": False,     # default -> no hint

    # Retrieve: type (gw_retrieve_type)
    "retrieval_type": "",                  # default -> active

    # Maintain: action (gw_maintain_action)
    "action": "",                          # default -> list

    # Promote: trigger (gw_promote_trigger)
    "trigger": "",                         # default -> session_end
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh knowledge_hygiene workflow with default data applied."""
    parser = BpmnParser()
    parser.add_bpmn_file(_BPMN_FILE)
    spec = parser.get_spec(_PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(_DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def _ready_names(wf: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.READY, manual=True)]


def _complete(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    ready = wf.get_tasks(state=TaskState.READY, manual=True)
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


def _completed_names(wf: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ===========================================================================
# PHASE 1: CAPTURE
# ===========================================================================

# ---------------------------------------------------------------------------
# P1: Capture via remember() (default), no maintenance hint
# ---------------------------------------------------------------------------

class TestCaptureRememberNoHint:
    """Default capture path: remember() with no maintenance hint returned."""

    def test_remember_no_hint_happy_path(self):
        wf = _load()  # defaults: phase="" -> capture, storage_target="" -> remember

        assert "capture_remember" in _ready_names(wf)
        _complete(wf, "capture_remember")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "capture_remember" in names
        assert "gw_capture_merge" in names
        assert "end_capture" in names
        # No hint path
        assert "act_on_hint" not in names
        # Other capture routes NOT taken
        assert "capture_fact" not in names
        assert "capture_stash" not in names
        assert "capture_catalog" not in names
        assert "capture_secret" not in names
        assert "capture_automemory" not in names


# ---------------------------------------------------------------------------
# P2: Capture via remember(), maintenance hint present -> act_on_hint
# ---------------------------------------------------------------------------

class TestCaptureRememberWithHint:
    """remember() returns a maintenance hint, Claude acts on it."""

    def test_remember_with_maintenance_hint(self):
        wf = _load(data_overrides={
            "maintenance_hint_present": True,
        })

        assert "capture_remember" in _ready_names(wf)
        _complete(wf, "capture_remember")

        # After capture_remember, gw_maint_hint routes to act_on_hint
        assert "act_on_hint" in _ready_names(wf)
        _complete(wf, "act_on_hint")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "capture_remember" in names
        assert "act_on_hint" in names
        assert "end_capture" in names


# ---------------------------------------------------------------------------
# P3: Capture via store_session_fact()
# ---------------------------------------------------------------------------

class TestCaptureSessionFact:
    """Capture route to store_session_fact (session-scoped notepad)."""

    def test_capture_session_fact(self):
        wf = _load(data_overrides={
            "storage_target": "session_fact",
        })

        assert "capture_fact" in _ready_names(wf)
        _complete(wf, "capture_fact")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "capture_fact" in names
        assert "end_capture" in names
        assert "capture_remember" not in names


# ---------------------------------------------------------------------------
# P4: Capture via stash()
# ---------------------------------------------------------------------------

class TestCaptureStash:
    """Capture route to stash (filing cabinet workfile)."""

    def test_capture_stash(self):
        wf = _load(data_overrides={
            "storage_target": "workfile",
        })

        assert "capture_stash" in _ready_names(wf)
        _complete(wf, "capture_stash")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "capture_stash" in names
        assert "end_capture" in names
        assert "capture_remember" not in names


# ---------------------------------------------------------------------------
# P5: Capture via catalog()
# ---------------------------------------------------------------------------

class TestCaptureCatalog:
    """Capture route to catalog (entity reference library)."""

    def test_capture_catalog(self):
        wf = _load(data_overrides={
            "storage_target": "entity_catalog",
        })

        assert "capture_catalog" in _ready_names(wf)
        _complete(wf, "capture_catalog")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "capture_catalog" in names
        assert "end_capture" in names
        assert "capture_remember" not in names


# ---------------------------------------------------------------------------
# P6: Capture via set_secret()
# ---------------------------------------------------------------------------

class TestCaptureSecret:
    """Capture route to set_secret (credential vault)."""

    def test_capture_secret(self):
        wf = _load(data_overrides={
            "storage_target": "credential",
        })

        assert "capture_secret" in _ready_names(wf)
        _complete(wf, "capture_secret")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "capture_secret" in names
        assert "end_capture" in names
        assert "capture_remember" not in names


# ---------------------------------------------------------------------------
# P7: Capture via auto-memory write
# ---------------------------------------------------------------------------

class TestCaptureAutoMemory:
    """Capture route to auto-memory (MEMORY.md file system)."""

    def test_capture_automemory(self):
        wf = _load(data_overrides={
            "storage_target": "auto_memory",
        })

        # capture_automemory is a scriptTask, should auto-complete
        assert wf.is_completed()
        names = _completed_names(wf)

        assert "capture_automemory" in names
        assert "end_capture" in names
        assert "capture_remember" not in names


# ===========================================================================
# PHASE 2: RETRIEVE
# ===========================================================================

# ---------------------------------------------------------------------------
# P8: Active retrieval (default retrieve type)
# ---------------------------------------------------------------------------

class TestRetrieveActive:
    """Active retrieval: Claude calls recall_memories/recall_entities/etc."""

    def test_active_retrieval(self):
        wf = _load(data_overrides={
            "phase": "retrieve",
        })

        # retrieve_active is a userTask (default path)
        assert "retrieve_active" in _ready_names(wf)
        _complete(wf, "retrieve_active")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "retrieve_active" in names
        assert "end_retrieve" in names
        # Passive path NOT taken
        assert "retrieve_passive_protocol" not in names
        assert "retrieve_passive_rag" not in names
        assert "retrieve_implicit_feedback" not in names


# ---------------------------------------------------------------------------
# P9: Passive retrieval (protocol_inject -> rag_query -> implicit_feedback)
# ---------------------------------------------------------------------------

class TestRetrievePassive:
    """Passive retrieval: hooks inject context automatically."""

    def test_passive_retrieval_pipeline(self):
        wf = _load(data_overrides={
            "phase": "retrieve",
            "retrieval_type": "passive",
        })

        # All scriptTasks, should auto-complete
        assert wf.is_completed()
        names = _completed_names(wf)

        assert "retrieve_passive_protocol" in names
        assert "retrieve_passive_rag" in names
        assert "retrieve_implicit_feedback" in names
        assert "end_retrieve" in names
        # Active path NOT taken
        assert "retrieve_active" not in names


# ===========================================================================
# PHASE 3: MAINTAIN
# ===========================================================================

# ---------------------------------------------------------------------------
# P10: list_memories (default maintain action)
# ---------------------------------------------------------------------------

class TestMaintainListMemories:
    """Default maintain action: list_memories for browsing."""

    def test_maintain_list_memories(self):
        wf = _load(data_overrides={
            "phase": "maintain",
        })

        assert "maint_list" in _ready_names(wf)
        _complete(wf, "maint_list")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_list" in names
        assert "end_maintain" in names
        # Other actions NOT taken
        assert "maint_update" not in names
        assert "maint_archive" not in names
        assert "maint_merge" not in names
        assert "maint_link" not in names
        assert "maint_arch_workfile" not in names
        assert "maint_pickup_flags" not in names
        assert "maint_user_remember" not in names
        assert "maint_user_forget" not in names
        assert "maint_user_correct" not in names
        assert "maint_user_review" not in names


# ---------------------------------------------------------------------------
# P11: update_memory
# ---------------------------------------------------------------------------

class TestMaintainUpdateMemory:
    """Maintain action: update_memory to fix incorrect content."""

    def test_maintain_update_memory(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "update",
        })

        assert "maint_update" in _ready_names(wf)
        _complete(wf, "maint_update")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_update" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P12: archive_memory
# ---------------------------------------------------------------------------

class TestMaintainArchiveMemory:
    """Maintain action: archive_memory (soft-delete)."""

    def test_maintain_archive_memory(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "archive",
        })

        assert "maint_archive" in _ready_names(wf)
        _complete(wf, "maint_archive")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_archive" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P13: merge_memories
# ---------------------------------------------------------------------------

class TestMaintainMergeMemories:
    """Maintain action: merge_memories (keep better, archive other)."""

    def test_maintain_merge_memories(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "merge",
        })

        assert "maint_merge" in _ready_names(wf)
        _complete(wf, "maint_merge")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_merge" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P14: link_knowledge
# ---------------------------------------------------------------------------

class TestMaintainLinkKnowledge:
    """Maintain action: link_knowledge (create typed relation)."""

    def test_maintain_link_knowledge(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "link",
        })

        assert "maint_link" in _ready_names(wf)
        _complete(wf, "maint_link")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_link" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P15: archive_workfile
# ---------------------------------------------------------------------------

class TestMaintainArchiveWorkfile:
    """Maintain action: archive_workfile (mark inactive)."""

    def test_maintain_archive_workfile(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "archive_workfile",
        })

        assert "maint_arch_workfile" in _ready_names(wf)
        _complete(wf, "maint_arch_workfile")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_arch_workfile" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P16: pickup_curator_flags
# ---------------------------------------------------------------------------

class TestMaintainPickupCuratorFlags:
    """Maintain action: review curator feedback items from previous run."""

    def test_maintain_pickup_curator_flags(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "pickup_curator_flags",
        })

        assert "maint_pickup_flags" in _ready_names(wf)
        _complete(wf, "maint_pickup_flags")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_pickup_flags" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P17a: user_remember (User requests knowledge capture)
# ---------------------------------------------------------------------------

class TestMaintainUserRemember:
    """User says 'remember X' — Claude captures via remember()."""

    def test_maintain_user_remember(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "user_remember",
        })

        assert "maint_user_remember" in _ready_names(wf)
        _complete(wf, "maint_user_remember")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_user_remember" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P17b: user_forget (User requests knowledge removal)
# ---------------------------------------------------------------------------

class TestMaintainUserForget:
    """User says 'forget that' — Claude archives the memory."""

    def test_maintain_user_forget(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "user_forget",
        })

        assert "maint_user_forget" in _ready_names(wf)
        _complete(wf, "maint_user_forget")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_user_forget" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P17c: user_correct (User requests knowledge correction)
# ---------------------------------------------------------------------------

class TestMaintainUserCorrect:
    """User says 'that's wrong, it should be Y' — Claude updates the memory."""

    def test_maintain_user_correct(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "user_correct",
        })

        assert "maint_user_correct" in _ready_names(wf)
        _complete(wf, "maint_user_correct")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_user_correct" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ---------------------------------------------------------------------------
# P17d: user_review (User requests knowledge review)
# ---------------------------------------------------------------------------

class TestMaintainUserReview:
    """User wants to review what Claude knows — collaborative review loop."""

    def test_maintain_user_review(self):
        wf = _load(data_overrides={
            "phase": "maintain",
            "action": "user_review",
        })

        assert "maint_user_review" in _ready_names(wf)
        _complete(wf, "maint_user_review")

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "maint_user_review" in names
        assert "end_maintain" in names
        assert "maint_list" not in names


# ===========================================================================
# PHASE 4: PROMOTE + DECAY
# ===========================================================================

# ---------------------------------------------------------------------------
# P17: Session end trigger -> hook promotes -> embed batch -> end
# ---------------------------------------------------------------------------

class TestPromoteSessionEnd:
    """Session end: hook promotes facts, then embed_knowledge backfills vectors."""

    def test_session_end_promote_and_embed(self):
        wf = _load(data_overrides={
            "phase": "promote",
        })

        # Both are scriptTasks, should auto-complete
        assert wf.is_completed()
        names = _completed_names(wf)

        assert "promote_session_end_hook" in names
        assert "promote_embed_batch" in names
        assert "end_promote" in names
        # Other trigger paths NOT taken
        assert "promote_mid_to_long" not in names
        assert "promote_decay" not in names
        assert "promote_manual" not in names


# ---------------------------------------------------------------------------
# P18: Periodic trigger -> mid_to_long -> decay -> end
# ---------------------------------------------------------------------------

class TestPromotePeriodic:
    """Periodic: consolidate_memories phases 2+3 (mid->long, decay+archive)."""

    def test_periodic_promote_and_decay(self):
        wf = _load(data_overrides={
            "phase": "promote",
            "trigger": "periodic",
        })

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "promote_mid_to_long" in names
        assert "promote_decay" in names
        assert "end_promote" in names
        # Other trigger paths NOT taken
        assert "promote_session_end_hook" not in names
        assert "promote_embed_batch" not in names
        assert "promote_manual" not in names


# ---------------------------------------------------------------------------
# P19: Manual trigger -> all 3 phases -> end
# ---------------------------------------------------------------------------

class TestPromoteManual:
    """Manual: runs all 3 consolidation phases in one pass."""

    def test_manual_full_cycle(self):
        wf = _load(data_overrides={
            "phase": "promote",
            "trigger": "manual",
        })

        assert wf.is_completed()
        names = _completed_names(wf)

        assert "promote_manual" in names
        assert "end_promote" in names
        # Other trigger paths NOT taken
        assert "promote_session_end_hook" not in names
        assert "promote_mid_to_long" not in names


# ===========================================================================
# PHASE 5: CURATE
# ===========================================================================

# ---------------------------------------------------------------------------
# P20: Full curation pipeline
# ---------------------------------------------------------------------------

class TestCurateFullPipeline:
    """Full curation pipeline: scan -> cluster -> classify -> act -> report -> domain_concepts."""

    def test_curate_full_pipeline(self):
        wf = _load(data_overrides={
            "phase": "curate",
        })

        # All scriptTasks, should auto-complete
        assert wf.is_completed()
        names = _completed_names(wf)

        assert "curate_scan" in names
        assert "curate_cluster" in names
        assert "curate_classify" in names
        assert "curate_act" in names
        assert "curate_report" in names
        assert "curate_domain_concepts" in names
        assert "end_curate" in names
        # No other phases taken
        assert "capture_remember" not in names
        assert "retrieve_active" not in names
        assert "maint_list" not in names
        assert "promote_session_end_hook" not in names


# ===========================================================================
# STRUCTURAL VALIDATION
# ===========================================================================

class TestWorkflowValidation:
    """Basic structural checks for the knowledge_hygiene workflow."""

    def test_workflow_loads_successfully(self):
        wf = _load()
        assert wf is not None
        assert wf.spec is not None

    def test_default_phase_is_capture(self):
        """Default phase (empty) routes to capture with remember() as first user task."""
        wf = _load()
        assert "capture_remember" in _ready_names(wf)

    def test_automemory_path_runs_without_user_tasks(self):
        """Auto-memory capture is a scriptTask, no manual intervention needed."""
        wf = _load(data_overrides={"storage_target": "auto_memory"})
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []
        assert wf.is_completed()

    def test_passive_retrieval_runs_without_user_tasks(self):
        """Passive retrieval is all scriptTasks, auto-completes."""
        wf = _load(data_overrides={"phase": "retrieve", "retrieval_type": "passive"})
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []
        assert wf.is_completed()

    def test_curate_runs_without_user_tasks(self):
        """Curation pipeline is all scriptTasks, auto-completes."""
        wf = _load(data_overrides={"phase": "curate"})
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []
        assert wf.is_completed()

    def test_promote_runs_without_user_tasks(self):
        """All promote paths are scriptTasks, auto-complete."""
        for trigger_val in ["", "periodic", "manual"]:
            wf = _load(data_overrides={"phase": "promote", "trigger": trigger_val})
            assert wf.get_tasks(state=TaskState.READY, manual=True) == [], (
                f"trigger='{trigger_val}' should have no user tasks"
            )
            assert wf.is_completed(), (
                f"trigger='{trigger_val}' should auto-complete"
            )


# ===========================================================================
# CROSS-PHASE ISOLATION
# ===========================================================================

class TestPhaseIsolation:
    """Each phase should only activate its own tasks, never crossing into others."""

    def test_capture_does_not_reach_other_phases(self):
        wf = _load()
        _complete(wf, "capture_remember")
        names = _completed_names(wf)
        assert "retrieve_active" not in names
        assert "maint_list" not in names
        assert "promote_session_end_hook" not in names
        assert "curate_scan" not in names

    def test_retrieve_does_not_reach_other_phases(self):
        wf = _load(data_overrides={"phase": "retrieve"})
        _complete(wf, "retrieve_active")
        names = _completed_names(wf)
        assert "capture_remember" not in names
        assert "maint_list" not in names
        assert "promote_session_end_hook" not in names
        assert "curate_scan" not in names

    def test_maintain_does_not_reach_other_phases(self):
        wf = _load(data_overrides={"phase": "maintain"})
        _complete(wf, "maint_list")
        names = _completed_names(wf)
        assert "capture_remember" not in names
        assert "retrieve_active" not in names
        assert "promote_session_end_hook" not in names
        assert "curate_scan" not in names

    def test_promote_does_not_reach_other_phases(self):
        wf = _load(data_overrides={"phase": "promote"})
        names = _completed_names(wf)
        assert "capture_remember" not in names
        assert "retrieve_active" not in names
        assert "maint_list" not in names
        assert "curate_scan" not in names

    def test_curate_does_not_reach_other_phases(self):
        wf = _load(data_overrides={"phase": "curate"})
        names = _completed_names(wf)
        assert "capture_remember" not in names
        assert "retrieve_active" not in names
        assert "maint_list" not in names
        assert "promote_session_end_hook" not in names


# ===========================================================================
# ALL MAINTAIN ACTIONS REACHABLE
# ===========================================================================

class TestAllMaintainActionsReachable:
    """Verify each maintain action routes to its distinct handler task."""

    def test_all_maintain_actions(self):
        cases = [
            ("",                    "maint_list"),          # default
            ("update",              "maint_update"),
            ("archive",             "maint_archive"),
            ("merge",               "maint_merge"),
            ("link",                "maint_link"),
            ("archive_workfile",    "maint_arch_workfile"),
            ("pickup_curator_flags", "maint_pickup_flags"),
            ("user_remember",       "maint_user_remember"),
            ("user_forget",         "maint_user_forget"),
            ("user_correct",        "maint_user_correct"),
            ("user_review",         "maint_user_review"),
        ]
        for action_val, expected_task in cases:
            wf = _load(data_overrides={
                "phase": "maintain",
                "action": action_val,
            })
            assert expected_task in _ready_names(wf), (
                f"action='{action_val}' should make '{expected_task}' READY"
            )
            _complete(wf, expected_task)
            assert wf.is_completed(), (
                f"action='{action_val}' should complete after '{expected_task}'"
            )
            names = _completed_names(wf)
            assert "end_maintain" in names, (
                f"action='{action_val}' should reach end_maintain"
            )


# ===========================================================================
# ALL CAPTURE ROUTES REACHABLE
# ===========================================================================

class TestAllCaptureRoutesReachable:
    """Verify each storage target routes to its correct capture task."""

    def test_all_capture_routes(self):
        # userTask routes (require manual completion)
        user_task_cases = [
            ("",                "capture_remember"),   # default
            ("session_fact",    "capture_fact"),
            ("workfile",        "capture_stash"),
            ("entity_catalog",  "capture_catalog"),
            ("credential",      "capture_secret"),
        ]
        for target_val, expected_task in user_task_cases:
            wf = _load(data_overrides={"storage_target": target_val})
            assert expected_task in _ready_names(wf), (
                f"storage_target='{target_val}' should make '{expected_task}' READY"
            )
            _complete(wf, expected_task)
            assert wf.is_completed(), (
                f"storage_target='{target_val}' should complete"
            )
            names = _completed_names(wf)
            assert "end_capture" in names, (
                f"storage_target='{target_val}' should reach end_capture"
            )

    def test_automemory_route(self):
        """Auto-memory is a scriptTask, auto-completes without user interaction."""
        wf = _load(data_overrides={"storage_target": "auto_memory"})
        assert wf.is_completed()
        names = _completed_names(wf)
        assert "capture_automemory" in names
        assert "end_capture" in names
