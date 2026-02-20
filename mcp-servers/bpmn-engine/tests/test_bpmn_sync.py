"""
Tests for the BPMN Process Registry Sync workflow.

Tests all logic paths through the bpmn_sync process:
  1. No files found -> end_empty
  2. Single file changed + parse OK -> full sync -> end_synced
  3. Single file unchanged (hash match) -> skip -> end_synced
  4. Single file changed + parse error -> log error + continue -> end_synced
  5. Two changed files -> loop processes both -> end_synced
  6. Mixed: two files, one changed one unchanged -> partial sync -> end_synced

Key design notes:
  - All tasks are scriptTasks (fully automated workflow)
  - Seed workflow.data before do_engine_steps() to drive scenarios
  - Scripts use exec() with task.data as namespace
  - Gateway conditions eval against task.data
  - _force_parse_fail flag enables testing the parse error path
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "bpmn_sync.bpmn")
)
PROCESS_ID = "bpmn_sync"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow with optional seeded data.

    In SpiffWorkflow 3.1.x, wf.data is separate from task.data.
    Data must be seeded on the BPMN start event task so it propagates
    to child tasks as they execute. After do_engine_steps(), wf.data
    contains the final workflow data.

    Since all tasks are scriptTasks, do_engine_steps() runs the entire
    workflow to completion (or until it gets stuck).
    """
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    if initial_data:
        # Seed data on the BPMN start event (not wf.data or root task)
        start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
        assert start_tasks, "Could not find BPMN start event"
        start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return spec names of all COMPLETED tasks."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Test 1: No files found
# ---------------------------------------------------------------------------

class TestNoFilesFound:
    """Path: Discover -> no files -> end_empty."""

    def test_empty_file_list(self):
        wf = load_workflow({"file_list": []})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "discover_files" in names
        assert "end_empty" in names
        # Should NOT enter the processing loop
        assert "pick_file" not in names
        assert "check_hash" not in names
        assert "summarize" not in names

        assert wf.data.get("file_count") == 0

    def test_none_file_list(self):
        """file_list=None should also trigger the empty path."""
        wf = load_workflow({"file_list": None})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_empty" in names
        assert wf.data.get("file_count") == 0


# ---------------------------------------------------------------------------
# Test 2: Single file, changed, parse OK (happy path)
# ---------------------------------------------------------------------------

class TestSingleChangedFile:
    """Path: Discover -> Pick -> Hash(changed) -> Parse(ok) -> Upsert -> Embed -> Summarize."""

    def test_changed_file_synced(self):
        wf = load_workflow({
            "file_list": ["process_a.bpmn"],
            "new_hash": "abc123",
            "existing_hash": "old456",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Full happy path executed
        assert "discover_files" in names
        assert "pick_file" in names
        assert "check_hash" in names
        assert "parse_bpmn" in names
        assert "upsert_db" in names
        assert "generate_embedding" in names
        assert "summarize" in names
        assert "end_synced" in names

        # Error/skip paths NOT taken
        assert "log_parse_error" not in names
        assert "skip_unchanged" not in names
        assert "end_empty" not in names

        # Counters
        assert wf.data.get("synced_count") == 1
        assert wf.data.get("skipped_count") == 0
        assert wf.data.get("parse_errors") == 0
        assert wf.data.get("sync_complete") is True
        assert wf.data.get("file_count") == 1
        assert wf.data.get("current_index") == 1


# ---------------------------------------------------------------------------
# Test 3: Single file, unchanged (incremental skip)
# ---------------------------------------------------------------------------

class TestSingleUnchangedFile:
    """Path: Discover -> Pick -> Hash(unchanged) -> Skip -> Summarize."""

    def test_unchanged_file_skipped(self):
        wf = load_workflow({
            "file_list": ["process_a.bpmn"],
            "new_hash": "same_hash",
            "existing_hash": "same_hash",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Skip path executed
        assert "skip_unchanged" in names
        assert "summarize" in names
        assert "end_synced" in names

        # Parse/upsert NOT executed
        assert "parse_bpmn" not in names
        assert "upsert_db" not in names
        assert "generate_embedding" not in names

        # Counters
        assert wf.data.get("skipped_count") == 1
        assert wf.data.get("synced_count") == 0
        assert wf.data.get("parse_errors") == 0
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 4: Single file, changed, parse failure
# ---------------------------------------------------------------------------

class TestParseError:
    """Path: Discover -> Pick -> Hash(changed) -> Parse(fail) -> Log Error -> Summarize."""

    def test_parse_error_logged_and_skipped(self):
        wf = load_workflow({
            "file_list": ["bad_file.bpmn"],
            "new_hash": "new_hash",
            "existing_hash": "old_hash",
            "_force_parse_fail": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Parse attempted, failed, error logged
        assert "parse_bpmn" in names
        assert "log_parse_error" in names
        assert "summarize" in names
        assert "end_synced" in names

        # Upsert/embed NOT executed (parse failed)
        assert "upsert_db" not in names
        assert "generate_embedding" not in names

        # Counters
        assert wf.data.get("parse_errors") == 1
        assert wf.data.get("synced_count") == 0
        assert wf.data.get("skipped_count") == 0
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 5: Two changed files (loop test)
# ---------------------------------------------------------------------------

class TestTwoChangedFiles:
    """Path: Loop processes both files through the full happy path."""

    def test_loop_processes_both_files(self):
        wf = load_workflow({
            "file_list": ["a.bpmn", "b.bpmn"],
            "new_hash": "new",
            "existing_hash": "old",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Both files synced
        assert "end_synced" in names
        assert wf.data.get("synced_count") == 2
        assert wf.data.get("skipped_count") == 0
        assert wf.data.get("current_index") == 2
        assert wf.data.get("file_count") == 2
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 6: Two files - one changed, one unchanged (mixed)
# ---------------------------------------------------------------------------

class TestMixedFiles:
    """Two files with same hash values - both take the same path.

    Note: Since hash values are global (not per-file), we can't test
    mixed changed/unchanged in a single run. This test verifies the
    loop terminates correctly with 2 unchanged files.
    """

    def test_two_unchanged_files(self):
        wf = load_workflow({
            "file_list": ["a.bpmn", "b.bpmn"],
            "new_hash": "same",
            "existing_hash": "same",
        })

        assert wf.is_completed()
        assert wf.data.get("skipped_count") == 2
        assert wf.data.get("synced_count") == 0
        assert wf.data.get("current_index") == 2
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 7: Three files - all parse errors
# ---------------------------------------------------------------------------

class TestMultipleParseErrors:
    """Three files, all changed, all fail parse -> 3 errors logged."""

    def test_three_parse_errors(self):
        wf = load_workflow({
            "file_list": ["bad1.bpmn", "bad2.bpmn", "bad3.bpmn"],
            "new_hash": "new",
            "existing_hash": "old",
            "_force_parse_fail": True,
        })

        assert wf.is_completed()
        assert wf.data.get("parse_errors") == 3
        assert wf.data.get("synced_count") == 0
        assert wf.data.get("current_index") == 3
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 8: Counter initialization
# ---------------------------------------------------------------------------

class TestCounterInitialization:
    """Verify all counters are properly initialized even with files."""

    def test_counters_initialized(self):
        wf = load_workflow({
            "file_list": ["test.bpmn"],
            "new_hash": "same",
            "existing_hash": "same",
        })

        assert wf.is_completed()
        # All counters should be explicitly set (not relying on defaults)
        assert "synced_count" in wf.data
        assert "skipped_count" in wf.data
        assert "parse_errors" in wf.data
        assert "current_index" in wf.data
        assert "file_count" in wf.data
