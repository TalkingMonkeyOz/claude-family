"""
Tests for the Secret Vault BPMN processes.

Three processes covering the full credential lifecycle:

Process 1: secret_vault_store — Store credential in Windows Credential Manager
  Path 1 - Happy path: validate → keyring ok → new secret → write WCM → session fact → success
  Path 2 - Invalid input: validate fails → end_invalid_input
  Path 3 - No keyring: keyring unavailable → fallback to session fact only
  Path 4 - Rotation: secret already exists → log rotation → overwrite → success
  Path 5 - Write failure: WCM write fails → fallback to session fact only

Process 2: secret_vault_retrieve — Retrieve credential from WCM
  Path 1 - Happy path: keyring ok → found in WCM → cache as session fact → success
  Path 2 - Not in WCM, in session: WCM miss → session fact hit → success
  Path 3 - Not in WCM, not in session: WCM miss → session miss → prompt user
  Path 4 - No keyring, in session: no keyring → session fact hit → success
  Path 5 - No keyring, not in session: no keyring → session miss → prompt user

Process 3: secret_vault_bulk_load — Load all project secrets at session start
  Path 1 - Happy path: keyring ok → registry has entries → all loaded
  Path 2 - No keyring: skip silently
  Path 3 - Empty registry: no secrets registered
  Path 4 - Partial load: some secrets missing from WCM

NOTE: SpiffWorkflow evaluates ALL gateway conditions even on non-taken paths.
All condition variables MUST be present in DEFAULT_DATA to prevent NameError.

Implementation: mcp-servers/bpmn-engine/processes/infrastructure/secret_vault.bpmn
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "processes", "infrastructure",
        "secret_vault.bpmn"
    )
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def load_workflow(process_id: str, data_overrides: dict = None, default_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(process_id)
    wf = BpmnWorkflow(spec)
    initial_data = dict(default_data or {})
    if data_overrides:
        initial_data.update(data_overrides)
    # Find start event and inject data
    start_events = {
        "secret_vault_store": "store_start",
        "secret_vault_retrieve": "retrieve_start",
        "secret_vault_bulk_load": "bulk_start",
    }
    start_name = start_events[process_id]
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == start_name]
    assert start_tasks, f"Could not find BPMN start event '{start_name}'"
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Process 1: secret_vault_store
# ---------------------------------------------------------------------------

STORE_DEFAULTS = {
    "secret_key": "test_api_key",
    "secret_value": "sk-test-12345",
    "project_name": "nimbus-mui",
    "input_valid": True,
    "keyring_available": True,
    "secret_exists": False,
    "write_success": True,
    "force_invalid_input": False,
    "force_no_keyring": False,
    "force_existing_secret": False,
    "force_write_fail": False,
}


def load_store(overrides: dict = None) -> BpmnWorkflow:
    return load_workflow("secret_vault_store", overrides, STORE_DEFAULTS)


class TestStoreHappyPath:
    """New secret stored successfully in WCM + session fact."""

    def test_reaches_end_store_success(self):
        wf = load_store()
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "validate_input" in names
        assert "check_keyring" in names
        assert "check_existing" in names
        assert "write_to_wcm" in names
        assert "store_session_fact" in names
        assert "end_store_success" in names

    def test_sets_stored_location_wcm(self):
        wf = load_store()
        assert wf.data.get("stored_location") == "windows_credential_manager"
        assert wf.data.get("persist_across_sessions") == True

    def test_no_rotation_logged(self):
        wf = load_store()
        names = completed_spec_names(wf)
        assert "log_rotation" not in names


class TestStoreInvalidInput:
    """Missing key or value rejects immediately."""

    def test_ends_at_invalid_input(self):
        wf = load_store({"force_invalid_input": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_invalid_input" in names
        assert "check_keyring" not in names
        assert "write_to_wcm" not in names


class TestStoreNoKeyring:
    """No keyring backend — falls back to session fact only."""

    def test_ends_at_fallback(self):
        wf = load_store({"force_no_keyring": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "fallback_session_fact" in names
        assert "end_fallback" in names
        assert "write_to_wcm" not in names

    def test_sets_no_persistence(self):
        wf = load_store({"force_no_keyring": True})
        assert wf.data.get("persist_across_sessions") == False


class TestStoreRotation:
    """Secret already exists — overwrites (rotation)."""

    def test_rotation_path_reaches_success(self):
        wf = load_store({"force_existing_secret": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "check_existing" in names
        assert "log_rotation" in names
        assert "write_to_wcm" in names
        assert "end_store_success" in names

    def test_rotation_flag_set(self):
        wf = load_store({"force_existing_secret": True})
        assert wf.data.get("is_rotation") == True


class TestStoreWriteFailure:
    """WCM write fails — falls back to session fact only."""

    def test_ends_at_write_fail(self):
        wf = load_store({"force_write_fail": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "write_to_wcm" in names
        assert "handle_write_fail" in names
        assert "end_write_fail" in names
        assert "store_session_fact" not in names

    def test_sets_no_persistence(self):
        wf = load_store({"force_write_fail": True})
        assert wf.data.get("persist_across_sessions") == False


# ---------------------------------------------------------------------------
# Process 2: secret_vault_retrieve
# ---------------------------------------------------------------------------

RETRIEVE_DEFAULTS = {
    "secret_key": "monash_auth_token",
    "project_name": "nimbus-mui",
    "keyring_available": True,
    "secret_found": True,
    "session_fact_found": False,
    "force_no_keyring": False,
    "force_not_found": False,
    "force_no_session_fact": True,  # Default: nothing in session facts
}


def load_retrieve(overrides: dict = None) -> BpmnWorkflow:
    return load_workflow("secret_vault_retrieve", overrides, RETRIEVE_DEFAULTS)


class TestRetrieveHappyPath:
    """Secret found in WCM, cached as session fact."""

    def test_reaches_retrieve_success(self):
        wf = load_retrieve()
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "r_check_keyring" in names
        assert "read_from_wcm" in names
        assert "cache_as_session_fact" in names
        assert "end_retrieve_success" in names

    def test_source_is_wcm(self):
        wf = load_retrieve()
        assert wf.data.get("source") == "windows_credential_manager"


class TestRetrieveNotInWcmButInSession:
    """Not in WCM, but found in session facts."""

    def test_falls_back_to_session_facts(self):
        wf = load_retrieve({"force_not_found": True, "force_no_session_fact": False})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "read_from_wcm" in names
        assert "check_session_facts" in names
        assert "end_retrieve_from_session" in names
        assert "handle_not_found" not in names

    def test_source_is_session_fact(self):
        wf = load_retrieve({"force_not_found": True, "force_no_session_fact": False})
        assert wf.data.get("source") == "session_fact"


class TestRetrieveNotFoundAnywhere:
    """Not in WCM, not in session facts — prompt user."""

    def test_prompts_user(self):
        wf = load_retrieve({"force_not_found": True, "force_no_session_fact": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "check_session_facts" in names
        assert "handle_not_found" in names
        assert "end_not_found" in names

    def test_prompt_user_flag(self):
        wf = load_retrieve({"force_not_found": True, "force_no_session_fact": True})
        assert wf.data.get("prompt_user") == True


class TestRetrieveNoKeyringWithSession:
    """No keyring, but credential in session facts."""

    def test_falls_back_to_session(self):
        wf = load_retrieve({"force_no_keyring": True, "force_no_session_fact": False})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "read_from_wcm" not in names
        assert "check_session_facts" in names
        assert "end_retrieve_from_session" in names


class TestRetrieveNoKeyringNoSession:
    """No keyring, no session fact — prompt user."""

    def test_prompts_user(self):
        wf = load_retrieve({"force_no_keyring": True, "force_no_session_fact": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "read_from_wcm" not in names
        assert "check_session_facts" in names
        assert "handle_not_found" in names
        assert "end_not_found" in names


# ---------------------------------------------------------------------------
# Process 3: secret_vault_bulk_load
# ---------------------------------------------------------------------------

BULK_DEFAULTS = {
    "project_name": "nimbus-mui",
    "keyring_available": True,
    "registry_count": 3,
    "has_missing": False,
    "force_no_keyring": False,
    "force_empty_registry": False,
    "force_partial_load": False,
}


def load_bulk(overrides: dict = None) -> BpmnWorkflow:
    return load_workflow("secret_vault_bulk_load", overrides, BULK_DEFAULTS)


class TestBulkLoadHappyPath:
    """All secrets loaded from WCM."""

    def test_reaches_bulk_success(self):
        wf = load_bulk()
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "b_check_keyring" in names
        assert "query_registry" in names
        assert "load_all_secrets" in names
        assert "end_bulk_success" in names

    def test_no_missing(self):
        wf = load_bulk()
        assert wf.data.get("missing_count") == 0
        names = completed_spec_names(wf)
        assert "warn_missing" not in names


class TestBulkLoadNoKeyring:
    """No keyring — skip silently."""

    def test_skips_silently(self):
        wf = load_bulk({"force_no_keyring": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_bulk_no_keyring" in names
        assert "query_registry" not in names
        assert "load_all_secrets" not in names


class TestBulkLoadEmptyRegistry:
    """No secrets registered for project."""

    def test_skips_with_empty(self):
        wf = load_bulk({"force_empty_registry": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "query_registry" in names
        assert "end_bulk_empty" in names
        assert "load_all_secrets" not in names


class TestBulkLoadPartial:
    """Some secrets missing from WCM."""

    def test_warns_about_missing(self):
        wf = load_bulk({"force_partial_load": True})
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "load_all_secrets" in names
        assert "warn_missing" in names
        assert "end_bulk_partial" in names

    def test_missing_count(self):
        wf = load_bulk({"force_partial_load": True})
        assert wf.data.get("missing_count") == 1
        assert wf.data.get("loaded_count") == 2


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------

class TestStructuralValidation:
    """Basic checks across all three processes."""

    @pytest.mark.parametrize("process_id,defaults", [
        ("secret_vault_store", STORE_DEFAULTS),
        ("secret_vault_retrieve", RETRIEVE_DEFAULTS),
        ("secret_vault_bulk_load", BULK_DEFAULTS),
    ])
    def test_workflow_loads_and_completes(self, process_id, defaults):
        wf = load_workflow(process_id, default_data=defaults)
        assert wf is not None
        assert wf.is_completed()

    def test_store_all_failure_paths_reachable(self):
        """Verify each force flag in store process routes to expected handler."""
        cases = [
            ({"force_invalid_input": True}, "end_invalid_input"),
            ({"force_no_keyring": True}, "end_fallback"),
            ({"force_existing_secret": True}, "log_rotation"),
            ({"force_write_fail": True}, "end_write_fail"),
        ]
        for overrides, expected in cases:
            wf = load_store(overrides)
            names = completed_spec_names(wf)
            assert expected in names, (
                f"overrides={overrides!r} should reach '{expected}', "
                f"but completed: {sorted(names)}"
            )

    def test_retrieve_all_paths_reachable(self):
        """Verify retrieve paths."""
        cases = [
            ({}, "end_retrieve_success"),
            ({"force_not_found": True, "force_no_session_fact": False}, "end_retrieve_from_session"),
            ({"force_not_found": True, "force_no_session_fact": True}, "end_not_found"),
            ({"force_no_keyring": True, "force_no_session_fact": False}, "end_retrieve_from_session"),
            ({"force_no_keyring": True, "force_no_session_fact": True}, "end_not_found"),
        ]
        for overrides, expected in cases:
            wf = load_retrieve(overrides)
            names = completed_spec_names(wf)
            assert expected in names, (
                f"overrides={overrides!r} should reach '{expected}', "
                f"but completed: {sorted(names)}"
            )

    def test_bulk_all_paths_reachable(self):
        """Verify bulk load paths."""
        cases = [
            ({}, "end_bulk_success"),
            ({"force_no_keyring": True}, "end_bulk_no_keyring"),
            ({"force_empty_registry": True}, "end_bulk_empty"),
            ({"force_partial_load": True}, "end_bulk_partial"),
        ]
        for overrides, expected in cases:
            wf = load_bulk(overrides)
            names = completed_spec_names(wf)
            assert expected in names, (
                f"overrides={overrides!r} should reach '{expected}', "
                f"but completed: {sorted(names)}"
            )
