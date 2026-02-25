"""
Tests for the Credential Loading BPMN process.

Models the PostgreSQL connection bootstrap used by MCP servers and hook scripts.
Seven execution paths across three failure points:

Path 1 - Happy path (default):
  start_load → load_env_files → detect_psycopg →
  gw_driver_available(driver_available==True) → resolve_uri →
  gw_uri_found(uri_resolved==True) → attempt_connection →
  gw_connected(connection_success==True) → end_success

Path 2 - No driver, graceful:
  detect_psycopg(force_no_driver) → gw_driver_available(default) →
  handle_no_driver → gw_strict_no_driver(default) → end_no_driver_graceful

Path 3 - No driver, strict:
  detect_psycopg(force_no_driver) → gw_driver_available(default) →
  handle_no_driver → gw_strict_no_driver(strict_mode==True) → end_no_driver_strict

Path 4 - No URI, graceful:
  detect_psycopg(ok) → resolve_uri(force_no_uri) → gw_uri_found(default) →
  handle_no_uri → gw_strict_no_uri(default) → end_no_uri_graceful

Path 5 - No URI, strict:
  resolve_uri(force_no_uri) → gw_uri_found(default) →
  handle_no_uri → gw_strict_no_uri(strict_mode==True) → end_no_uri_strict

Path 6 - Connection failed, graceful:
  attempt_connection(force_connection_fail) → gw_connected(default) →
  handle_connection_fail → gw_strict_conn_fail(default) → end_conn_fail_graceful

Path 7 - Connection failed, strict:
  attempt_connection(force_connection_fail) → gw_connected(default) →
  handle_connection_fail → gw_strict_conn_fail(strict_mode==True) → end_conn_fail_strict

NOTE: SpiffWorkflow evaluates ALL gateway conditions even on non-taken paths.
All condition variables MUST be present in DEFAULT_DATA to prevent NameError.

Implementation: mcp-servers/bpmn-engine/processes/infrastructure/credential_loading.bpmn
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "infrastructure",
        "credential_loading.bpmn"
    )
)
PROCESS_ID = "credential_loading"

# Default data: all gateway condition variables set to take the happy path.
# - gw_driver_available: driver_available==True → flow_driver_ok (not default)
# - gw_strict_no_driver: strict_mode==False → default (graceful)
# - gw_uri_found: uri_resolved==True → flow_uri_ok (not default)
# - gw_strict_no_uri: strict_mode==False → default (graceful)
# - gw_connected: connection_success==True → flow_conn_ok (not default)
# - gw_strict_conn_fail: strict_mode==False → default (graceful)
# force_* flags default to False so script tasks take their normal path
DEFAULT_DATA = {
    "driver_available": True,
    "uri_resolved": True,
    "connection_success": True,
    "strict_mode": False,
    "force_no_driver": False,
    "force_no_uri": False,
    "force_connection_fail": False,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(data_overrides: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance with default data applied."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    initial_data = dict(DEFAULT_DATA)
    if data_overrides:
        initial_data.update(data_overrides)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start_load"]
    assert start_tasks, "Could not find BPMN start event 'start_load'"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Path 1: Happy path — driver found, URI resolved, connection succeeds
# ---------------------------------------------------------------------------

class TestHappyPath:
    """All three phases succeed: driver, URI, and connection."""

    def test_happy_path_reaches_end_success(self):
        wf = load_workflow()  # all defaults: happy path throughout

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "load_env_files" in names
        assert "detect_psycopg" in names
        assert "resolve_uri" in names
        assert "attempt_connection" in names
        assert "end_success" in names

        # No failure handlers should have run
        assert "handle_no_driver" not in names
        assert "handle_no_uri" not in names
        assert "handle_connection_fail" not in names

    def test_happy_path_sets_expected_variables(self):
        wf = load_workflow()

        assert wf.is_completed()
        # Happy path script tasks set these variables
        assert wf.data.get("driver_available") == True
        assert wf.data.get("uri_resolved") == True
        assert wf.data.get("connection_success") == True


# ---------------------------------------------------------------------------
# Path 2: No driver, graceful (strict_mode=False)
# ---------------------------------------------------------------------------

class TestNoDriverGraceful:
    """psycopg driver unavailable, graceful mode returns None (no exception)."""

    def test_no_driver_graceful_ends_at_graceful_end_event(self):
        wf = load_workflow(data_overrides={
            "force_no_driver": True,
            "strict_mode": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "load_env_files" in names
        assert "detect_psycopg" in names
        assert "handle_no_driver" in names
        assert "end_no_driver_graceful" in names

        # URI and connection tasks must not have run
        assert "resolve_uri" not in names
        assert "attempt_connection" not in names
        assert "end_success" not in names
        assert "end_no_driver_strict" not in names

    def test_no_driver_graceful_sets_driver_available_false(self):
        wf = load_workflow(data_overrides={"force_no_driver": True})

        assert wf.is_completed()
        assert wf.data.get("driver_available") == False


# ---------------------------------------------------------------------------
# Path 3: No driver, strict (strict_mode=True)
# ---------------------------------------------------------------------------

class TestNoDriverStrict:
    """psycopg driver unavailable, strict mode ends at error event."""

    def test_no_driver_strict_ends_at_strict_end_event(self):
        wf = load_workflow(data_overrides={
            "force_no_driver": True,
            "strict_mode": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "handle_no_driver" in names
        assert "end_no_driver_strict" in names

        assert "end_no_driver_graceful" not in names
        assert "resolve_uri" not in names
        assert "end_success" not in names

    def test_no_driver_strict_sets_driver_available_false(self):
        wf = load_workflow(data_overrides={
            "force_no_driver": True,
            "strict_mode": True,
        })

        assert wf.is_completed()
        assert wf.data.get("driver_available") == False


# ---------------------------------------------------------------------------
# Path 4: No URI, graceful (strict_mode=False)
# ---------------------------------------------------------------------------

class TestNoUriGraceful:
    """Driver available but no URI resolved, graceful mode returns None."""

    def test_no_uri_graceful_ends_at_graceful_end_event(self):
        wf = load_workflow(data_overrides={
            "force_no_uri": True,
            "strict_mode": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "load_env_files" in names
        assert "detect_psycopg" in names
        assert "resolve_uri" in names
        assert "handle_no_uri" in names
        assert "end_no_uri_graceful" in names

        # Driver was found; connection must not have been attempted
        assert "handle_no_driver" not in names
        assert "attempt_connection" not in names
        assert "end_success" not in names
        assert "end_no_uri_strict" not in names

    def test_no_uri_graceful_sets_uri_resolved_false(self):
        wf = load_workflow(data_overrides={"force_no_uri": True})

        assert wf.is_completed()
        assert wf.data.get("uri_resolved") == False


# ---------------------------------------------------------------------------
# Path 5: No URI, strict (strict_mode=True)
# ---------------------------------------------------------------------------

class TestNoUriStrict:
    """Driver available but no URI resolved, strict mode ends at error event."""

    def test_no_uri_strict_ends_at_strict_end_event(self):
        wf = load_workflow(data_overrides={
            "force_no_uri": True,
            "strict_mode": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "resolve_uri" in names
        assert "handle_no_uri" in names
        assert "end_no_uri_strict" in names

        assert "end_no_uri_graceful" not in names
        assert "attempt_connection" not in names
        assert "end_success" not in names

    def test_no_uri_strict_sets_uri_resolved_false(self):
        wf = load_workflow(data_overrides={
            "force_no_uri": True,
            "strict_mode": True,
        })

        assert wf.is_completed()
        assert wf.data.get("uri_resolved") == False


# ---------------------------------------------------------------------------
# Path 6: Connection failed, graceful (strict_mode=False)
# ---------------------------------------------------------------------------

class TestConnectionFailGraceful:
    """Driver and URI available, connection fails, graceful mode returns None."""

    def test_conn_fail_graceful_ends_at_graceful_end_event(self):
        wf = load_workflow(data_overrides={
            "force_connection_fail": True,
            "strict_mode": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "load_env_files" in names
        assert "detect_psycopg" in names
        assert "resolve_uri" in names
        assert "attempt_connection" in names
        assert "handle_connection_fail" in names
        assert "end_conn_fail_graceful" in names

        # No prior failures
        assert "handle_no_driver" not in names
        assert "handle_no_uri" not in names
        assert "end_success" not in names
        assert "end_conn_fail_strict" not in names

    def test_conn_fail_graceful_sets_connection_success_false(self):
        wf = load_workflow(data_overrides={"force_connection_fail": True})

        assert wf.is_completed()
        assert wf.data.get("connection_success") == False


# ---------------------------------------------------------------------------
# Path 7: Connection failed, strict (strict_mode=True)
# ---------------------------------------------------------------------------

class TestConnectionFailStrict:
    """Driver and URI available, connection fails, strict mode ends at error event."""

    def test_conn_fail_strict_ends_at_strict_end_event(self):
        wf = load_workflow(data_overrides={
            "force_connection_fail": True,
            "strict_mode": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "attempt_connection" in names
        assert "handle_connection_fail" in names
        assert "end_conn_fail_strict" in names

        assert "end_conn_fail_graceful" not in names
        assert "end_success" not in names

    def test_conn_fail_strict_sets_connection_success_false(self):
        wf = load_workflow(data_overrides={
            "force_connection_fail": True,
            "strict_mode": True,
        })

        assert wf.is_completed()
        assert wf.data.get("connection_success") == False


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

class TestWorkflowValidation:
    """Basic structural checks for the credential_loading workflow."""

    def test_workflow_loads_successfully(self):
        wf = load_workflow()
        assert wf is not None
        assert wf.spec is not None

    def test_no_user_tasks_required(self):
        """Pure script workflow — no manual intervention needed."""
        wf = load_workflow()
        assert wf.get_tasks(state=TaskState.READY, manual=True) == []

    def test_workflow_completes_without_intervention(self):
        wf = load_workflow()
        assert wf.is_completed()

    def test_all_failure_paths_reachable(self):
        """Verify each force_* flag routes to the expected failure handler."""
        cases = [
            ({"force_no_driver": True},       "handle_no_driver"),
            ({"force_no_uri": True},           "handle_no_uri"),
            ({"force_connection_fail": True},  "handle_connection_fail"),
        ]
        for overrides, expected_task in cases:
            wf = load_workflow(data_overrides=overrides)
            names = completed_spec_names(wf)
            assert expected_task in names, (
                f"overrides={overrides!r} should reach '{expected_task}', "
                f"but completed tasks were: {sorted(names)}"
            )

    def test_graceful_vs_strict_routing(self):
        """Verify strict_mode routes each failure to the correct end event."""
        cases = [
            ({"force_no_driver": True, "strict_mode": False}, "end_no_driver_graceful"),
            ({"force_no_driver": True, "strict_mode": True},  "end_no_driver_strict"),
            ({"force_no_uri": True,    "strict_mode": False}, "end_no_uri_graceful"),
            ({"force_no_uri": True,    "strict_mode": True},  "end_no_uri_strict"),
            ({"force_connection_fail": True, "strict_mode": False}, "end_conn_fail_graceful"),
            ({"force_connection_fail": True, "strict_mode": True},  "end_conn_fail_strict"),
        ]
        for overrides, expected_end in cases:
            wf = load_workflow(data_overrides=overrides)
            names = completed_spec_names(wf)
            assert expected_end in names, (
                f"overrides={overrides!r} should end at '{expected_end}', "
                f"but completed tasks were: {sorted(names)}"
            )
