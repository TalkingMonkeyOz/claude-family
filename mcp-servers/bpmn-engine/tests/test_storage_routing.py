"""
Tests for the Storage Routing BPMN process.

The storage_routing process classifies content and routes it to the correct
storage system. 5 phases:

  1. CLASSIFY  - Determine content_type (or use pre-classified)
  2. ANTI-PATTERN - Check for storage anti-patterns (block or redirect)
  3. CHECK-FIRST - Dedup/exists check before storing
  4. ROUTE - Send to correct storage system (7 routes)
  5. VALIDATE - Confirm storage succeeded

7 storage routes:
  credential -> set_secret
  config/endpoint/decision_short -> store_session_fact
  pattern/gotcha/learned/decision_long -> remember (default)
  working_notes -> stash
  structured_data -> catalog
  procedure -> skill/BPMN
  auto_memory -> .md file

NOTE: SpiffWorkflow evaluates ALL gateway conditions even on non-taken paths.
All condition variables MUST be present in DEFAULT_DATA.

Implementation file:
  processes/infrastructure/storage_routing.bpmn
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


_BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "infrastructure",
        "storage_routing.bpmn"
    )
)
_PROCESS_ID = "storage_routing"

# All gateway condition variables with safe defaults.
# Gateways and their defaults:
#   gw_pre_classified: default -> f_needs_classification (content_type empty)
#   gw_antipattern: default -> f_no_antipattern
#   gw_already_exists: default -> f_not_exists
#   gw_update_decision: default -> f_skip_exists
#   gw_route: default -> f_route_memory (pattern/gotcha/learned)
#   gw_success: default -> f_store_failed
_DEFAULT_DATA = {
    # Phase 1: Classification
    "content_type": "",               # empty -> needs classification
    # Phase 2: Anti-pattern
    "antipattern_detected": False,
    "corrected_content_type": "",     # set by anti-pattern check
    "force_antipattern": False,
    "force_antipattern_type": "",
    "force_corrected_type": "",
    # Phase 3: Check-first
    "already_exists": False,
    "update_existing": False,
    # Phase 5: Validate
    "store_success": True,
    "storage_target": "",
    "storage_tool": "",
}


def _load(data_overrides: dict = None) -> BpmnWorkflow:
    """Return a fresh storage_routing workflow with default data applied."""
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
# ROUTE 1: CREDENTIAL -> set_secret (pre-classified)
# ===========================================================================

class TestRouteCredential:
    """Credential content routes to set_secret."""

    def test_credential_happy_path(self):
        wf = _load({"content_type": "credential"})

        # Phase 1: classify_content (userTask) should be ready
        assert "classify_content" in _ready_names(wf)
        _complete(wf, "classify_content")
        # Pre-classified -> skips auto_classify, goes through anti-pattern check

        # Phase 3: check_first (userTask)
        assert "check_first" in _ready_names(wf)
        _complete(wf, "check_first")

        # Workflow should complete (store_credential is scriptTask, auto-runs)
        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_credential" in names
        assert "end_success" in names
        # Other routes NOT taken
        assert "store_notepad" not in names
        assert "store_memory" not in names
        assert "store_workfile" not in names
        assert "store_entity" not in names


# ===========================================================================
# ROUTE 2: CONFIG -> store_session_fact
# ===========================================================================

class TestRouteNotepad:
    """Config/endpoint/decision_short content routes to store_session_fact."""

    def test_config_routes_to_notepad(self):
        wf = _load({"content_type": "config"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_notepad" in names
        assert "store_credential" not in names

    def test_endpoint_routes_to_notepad(self):
        wf = _load({"content_type": "endpoint"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        assert "store_notepad" in _completed_names(wf)

    def test_decision_short_routes_to_notepad(self):
        wf = _load({"content_type": "decision_short"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        assert "store_notepad" in _completed_names(wf)


# ===========================================================================
# ROUTE 3: PATTERN -> remember (default route)
# ===========================================================================

class TestRouteMemory:
    """Pattern/gotcha/learned content routes to remember (default)."""

    def test_pattern_default_route(self):
        """Empty content_type -> auto_classify -> defaults to pattern -> memory."""
        wf = _load()  # content_type="" -> needs classification
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "auto_classify" in names  # went through classification
        assert "store_memory" in names
        assert "end_success" in names


# ===========================================================================
# ROUTE 4: WORKING_NOTES -> stash
# ===========================================================================

class TestRouteWorkfile:
    """Working notes route to stash."""

    def test_working_notes_routes_to_stash(self):
        wf = _load({"content_type": "working_notes"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_workfile" in names
        assert "store_memory" not in names


# ===========================================================================
# ROUTE 5: STRUCTURED_DATA -> catalog
# ===========================================================================

class TestRouteEntity:
    """Structured data routes to catalog."""

    def test_structured_data_routes_to_catalog(self):
        wf = _load({"content_type": "structured_data"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_entity" in names
        assert "store_memory" not in names


# ===========================================================================
# ROUTE 6: PROCEDURE -> skill/BPMN (userTask)
# ===========================================================================

class TestRouteProcedure:
    """Procedure content routes to skill/BPMN creation (userTask)."""

    def test_procedure_routes_to_skill_bpmn(self):
        wf = _load({"content_type": "procedure"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        # store_procedure is a userTask, so it should be READY
        assert "store_procedure" in _ready_names(wf)
        _complete(wf, "store_procedure")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_procedure" in names
        assert "end_success" in names


# ===========================================================================
# ROUTE 7: AUTO_MEMORY -> .md file
# ===========================================================================

class TestRouteAutoMemory:
    """Auto memory routes to .md file write."""

    def test_auto_memory_routes_to_md_file(self):
        wf = _load({"content_type": "auto_memory"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_automemory" in names
        assert "store_memory" not in names


# ===========================================================================
# ANTI-PATTERN: BLOCK (secret in memory)
# ===========================================================================

class TestAntiPatternBlock:
    """Anti-pattern detection blocks forbidden storage combinations."""

    def test_blocked_antipattern_ends_at_blocked(self):
        wf = _load({
            "content_type": "pattern",  # pre-classified
            "force_antipattern": True,
            "force_antipattern_type": "secret_in_memory",
            "force_corrected_type": "BLOCK",
        })
        _complete(wf, "classify_content")

        # Should end at end_blocked, not continue to check_first
        assert wf.is_completed()
        names = _completed_names(wf)
        assert "end_blocked" in names
        assert "check_first" not in names
        assert "store_memory" not in names


# ===========================================================================
# ANTI-PATTERN: REDIRECT (credential misclassified as config)
# ===========================================================================

class TestAntiPatternRedirect:
    """Anti-pattern detection redirects to correct storage system."""

    def test_redirect_config_to_credential(self):
        wf = _load({
            "content_type": "config",  # misclassified
            "force_antipattern": True,
            "force_antipattern_type": "credential_as_session_fact",
            "force_corrected_type": "credential",  # redirected
        })
        _complete(wf, "classify_content")
        _complete(wf, "check_first")

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_credential" in names
        assert "store_notepad" not in names


# ===========================================================================
# CHECK-FIRST: ALREADY EXISTS -> skip
# ===========================================================================

class TestCheckFirstSkip:
    """When content already exists and user skips, ends at end_skipped."""

    def test_already_exists_skip(self):
        wf = _load({"content_type": "pattern"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first", {"already_exists": True})

        # decide_update userTask should be ready
        assert "decide_update" in _ready_names(wf)
        _complete(wf, "decide_update")  # update_existing=False (default)

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "end_skipped" in names
        assert "store_memory" not in names


# ===========================================================================
# CHECK-FIRST: ALREADY EXISTS -> update
# ===========================================================================

class TestCheckFirstUpdate:
    """When content already exists and user updates, routes to storage."""

    def test_already_exists_update(self):
        wf = _load({"content_type": "pattern"})
        _complete(wf, "classify_content")
        _complete(wf, "check_first", {"already_exists": True})

        assert "decide_update" in _ready_names(wf)
        _complete(wf, "decide_update", {"update_existing": True})

        assert wf.is_completed()
        names = _completed_names(wf)
        assert "store_memory" in names
        assert "end_success" in names
        assert "end_skipped" not in names


# ===========================================================================
# STRUCTURAL: Process parses and has expected elements
# ===========================================================================

class TestProcessStructure:
    """Verify the process has all expected elements."""

    def test_all_seven_store_tasks_exist(self):
        """All 7 storage route tasks must be present in the process."""
        parser = BpmnParser()
        parser.add_bpmn_file(_BPMN_FILE)
        spec = parser.get_spec(_PROCESS_ID)
        task_names = {name for name in spec.task_specs}
        expected_stores = {
            "store_credential", "store_notepad", "store_memory",
            "store_workfile", "store_entity", "store_procedure",
            "store_automemory",
        }
        assert expected_stores.issubset(task_names), (
            f"Missing store tasks: {expected_stores - task_names}"
        )
