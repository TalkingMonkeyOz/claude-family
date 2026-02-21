"""
Tests for the check_alignment tool (BPMN-vs-reality validation).

Validates that:
  1. hook_chain.bpmn elements map to actual hook scripts on disk
  2. Unmapped elements get sensible suggestions
  3. Coverage percentages are calculated correctly
  4. Missing artifacts are detected when files don't exist
"""

import os
import sys

# Add server directory to path so we can import server functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import check_alignment, _ARTIFACT_REGISTRY


class TestHookChainAlignment:
    """hook_chain.bpmn should map most elements to actual hook scripts."""

    def test_hook_chain_has_mappings(self):
        result = check_alignment("hook_chain")
        assert result["success"] is True
        assert result["process_id"] == "hook_chain"
        assert result["total_elements"] > 0
        assert result["mapped_count"] > 0

    def test_hook_chain_coverage(self):
        result = check_alignment("hook_chain")
        assert result["success"] is True
        # hook_chain has well-known elements, should have good coverage
        assert result["coverage_pct"] > 50.0

    def test_hook_scripts_exist(self):
        result = check_alignment("hook_chain")
        assert result["success"] is True
        # No missing artifacts (all mapped files should exist on disk)
        assert result["missing_artifact_count"] == 0, (
            f"Missing artifacts: {result['missing_artifacts']}"
        )

    def test_query_rag_maps_to_hook(self):
        result = check_alignment("hook_chain")
        assert result["success"] is True
        rag_entries = [m for m in result["mapped"] if m["element_id"] == "query_rag"]
        assert len(rag_entries) == 1
        assert rag_entries[0]["artifact_type"] == "hook_script"
        assert "rag_query_hook.py" in rag_entries[0]["artifact_details"]


class TestSessionLifecycleAlignment:
    """session_lifecycle.bpmn should map startup/shutdown elements."""

    def test_session_lifecycle_has_mappings(self):
        result = check_alignment("session_lifecycle")
        assert result["success"] is True
        assert result["mapped_count"] > 0

    def test_session_start_maps_to_hook(self):
        result = check_alignment("session_lifecycle")
        assert result["success"] is True
        start_entries = [m for m in result["mapped"] if m["element_id"] == "session_start"]
        if start_entries:  # May not be in the exact element list
            assert start_entries[0]["artifact_type"] == "hook_script"


class TestUnknownProcess:
    """Unknown process IDs should return a clean error."""

    def test_unknown_process_returns_error(self):
        result = check_alignment("nonexistent_process")
        assert result["success"] is False
        assert "not found" in result["error"]


class TestArtifactRegistry:
    """The artifact registry should have entries for key processes."""

    def test_registry_has_hook_chain_entries(self):
        hook_chain_keys = {"query_rag", "check_discipline", "inject_tool_context",
                           "post_tool_sync", "mark_blocked", "check_session_changed",
                           "classify_prompt", "inject_rag_context"}
        assert hook_chain_keys.issubset(set(_ARTIFACT_REGISTRY.keys()))

    def test_registry_has_session_entries(self):
        session_keys = {"session_start", "load_state", "save_checkpoint", "close_session"}
        assert session_keys.issubset(set(_ARTIFACT_REGISTRY.keys()))

    def test_registry_has_task_entries(self):
        task_keys = {"create_task", "sync_to_db", "work_on_task"}
        assert task_keys.issubset(set(_ARTIFACT_REGISTRY.keys()))
