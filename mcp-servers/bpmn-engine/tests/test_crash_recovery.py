"""
Tests for the Crash Recovery BPMN process.

Crash Recovery (crash_recovery):
  Trigger: User invokes /crash-recovery or recover_session() MCP tool
  Input: project_name, unclosed_sessions (list), filtered_sessions (list)

  Key behaviors:
    1. Load session facts from recent sessions
    2. Find unclosed sessions and filter continuation re-fires
    3. If crashes found: parse transcript for crash signals
    4. If no crashes: skip transcript parsing
    5. Get last completed session summary
    6. Get in-progress work items
    7. Get git status
    8. Format structured recovery context

  Test paths:
    1. Crashes found → full path with transcript parsing
    2. No crashes → skip transcript, still collect work context
    3. Common path → facts, sessions, work, git always execute
    4. Re-fire filtering → reduces unclosed session count

Implementation: mcp-servers/project-tools/server_v2.py (recover_session)
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "crash_recovery.bpmn")
)
PROCESS_ID = "crash_recovery"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
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
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Crashes Found - Full Recovery Path
# ---------------------------------------------------------------------------

class TestCrashesFound:
    """
    Unclosed sessions found after filtering → parse transcript → full recovery.

    Expected path:
      start → load_session_facts → find_unclosed_sessions → filter_refires →
      has_crashes_gw (True) → parse_transcript → crash_merge →
      get_last_completed → get_in_progress_work → get_git_status →
      format_recovery → end_recovered
    """

    def test_full_recovery_with_crashes(self):
        wf = load_workflow({
            "unclosed_sessions": [
                {"session_id": "abc-123", "hours_ago": 0.5},
                {"session_id": "def-456", "hours_ago": 2.0},
            ],
            "filtered_sessions": [
                {"session_id": "abc-123", "hours_ago": 0.5},
                {"session_id": "def-456", "hours_ago": 2.0},
            ],
            "facts_count": 5,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # All steps should execute
        assert "load_session_facts" in names
        assert "find_unclosed_sessions" in names
        assert "filter_refires" in names
        assert "parse_transcript" in names
        assert "get_last_completed" in names
        assert "get_in_progress_work" in names
        assert "get_git_status" in names
        assert "format_recovery" in names
        assert "end_recovered" in names

        # Should NOT hit the no-crash path
        assert "no_crash_report" not in names

        # Data checks
        assert wf.data.get("transcript_parsed") is True
        assert wf.data.get("recovery_complete") is True
        assert wf.data.get("facts_loaded") is True


# ---------------------------------------------------------------------------
# Test 2: No Crashes - Context-Only Recovery
# ---------------------------------------------------------------------------

class TestNoCrashes:
    """
    No unclosed sessions after filtering → skip transcript → still collect context.

    Expected path:
      start → load_session_facts → find_unclosed_sessions → filter_refires →
      has_crashes_gw (False) → no_crash_report → crash_merge →
      get_last_completed → get_in_progress_work → get_git_status →
      format_recovery → end_recovered
    """

    def test_recovery_without_crashes(self):
        wf = load_workflow({
            "unclosed_sessions": [],
            "filtered_sessions": [],
            "facts_count": 2,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Should hit no-crash path
        assert "no_crash_report" in names
        assert "parse_transcript" not in names

        # Context collection should still happen
        assert "get_last_completed" in names
        assert "get_in_progress_work" in names
        assert "get_git_status" in names
        assert "format_recovery" in names

        # Data checks
        assert wf.data.get("transcript_parsed") is False
        assert wf.data.get("crash_type") == "none"
        assert wf.data.get("recovery_complete") is True


# ---------------------------------------------------------------------------
# Test 3: Re-fire Filtering
# ---------------------------------------------------------------------------

class TestRefireFiltering:
    """
    Multiple unclosed sessions where some are re-fires (< 60s apart).
    Filtering should reduce the count.
    """

    def test_refires_filtered_out(self):
        wf = load_workflow({
            "unclosed_sessions": [
                {"session_id": "a", "hours_ago": 0.1},
                {"session_id": "b", "hours_ago": 0.1001},  # <60s from 'a' → re-fire
                {"session_id": "c", "hours_ago": 2.0},
            ],
            "filtered_sessions": [
                {"session_id": "a", "hours_ago": 0.1},
                {"session_id": "c", "hours_ago": 2.0},
            ],
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Should parse transcript since filtered_sessions is non-empty
        assert "parse_transcript" in names
        assert wf.data.get("refires_filtered") == 1


# ---------------------------------------------------------------------------
# Test 4: Common Path - Always Collects Context
# ---------------------------------------------------------------------------

class TestCommonPath:
    """Both crash and no-crash paths execute facts, sessions, work, git."""

    def test_crash_path_collects_all_context(self):
        wf = load_workflow({
            "filtered_sessions": [{"session_id": "x", "hours_ago": 1.0}],
            "unclosed_sessions": [{"session_id": "x", "hours_ago": 1.0}],
        })
        names = completed_spec_names(wf)
        assert "load_session_facts" in names
        assert "find_unclosed_sessions" in names
        assert "get_last_completed" in names
        assert "get_in_progress_work" in names
        assert "get_git_status" in names

    def test_no_crash_path_collects_all_context(self):
        wf = load_workflow({
            "filtered_sessions": [],
            "unclosed_sessions": [],
        })
        names = completed_spec_names(wf)
        assert "load_session_facts" in names
        assert "find_unclosed_sessions" in names
        assert "get_last_completed" in names
        assert "get_in_progress_work" in names
        assert "get_git_status" in names


# ---------------------------------------------------------------------------
# Test 5: Crash Type Detection
# ---------------------------------------------------------------------------

class TestCrashTypeDetection:
    """Transcript parsing sets crash_type based on signals found."""

    def test_crash_type_set_when_transcript_parsed(self):
        wf = load_workflow({
            "filtered_sessions": [{"session_id": "x"}],
            "unclosed_sessions": [{"session_id": "x"}],
            "crash_type": "cli_process_crash",
        })
        names = completed_spec_names(wf)
        assert "parse_transcript" in names
        assert wf.data.get("crash_type") == "cli_process_crash"

    def test_crash_type_none_when_no_crashes(self):
        wf = load_workflow({
            "filtered_sessions": [],
            "unclosed_sessions": [],
        })
        assert wf.data.get("crash_type") == "none"


# ---------------------------------------------------------------------------
# Test 6: Data Flow Integrity
# ---------------------------------------------------------------------------

class TestDataFlow:
    """All steps contribute data to the final recovery context."""

    def test_all_data_keys_present(self):
        wf = load_workflow({
            "filtered_sessions": [{"session_id": "crash-1"}],
            "unclosed_sessions": [{"session_id": "crash-1"}],
            "facts_count": 3,
        })
        assert wf.is_completed()

        # Check key data flags
        assert "facts_loaded" in wf.data
        assert "filtered_sessions" in wf.data
        assert "crash_type" in wf.data
        assert "recovery_complete" in wf.data
