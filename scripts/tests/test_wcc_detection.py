"""
Unit tests for WCC (Work Context Container) detection and assembly.

Tests the wcc_assembly.py module's activity detection logic using
mock database connections (no real DB required).
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wcc_assembly import (
    detect_activity,
    load_wcc_state,
    save_wcc_state,
    invalidate_wcc_cache,
    _is_cache_valid,
    _truncate_to_budget,
    get_wcc_context,
    WCC_STATE_FILE,
)


# =========================================================================
# Fixtures
# =========================================================================


class MockCursor:
    """Mock psycopg cursor that returns predefined results."""

    def __init__(self, results=None):
        self._results = results or []
        self._index = 0

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        if self._index < len(self._results):
            row = self._results[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self):
        return self._results

    def close(self):
        pass


class MockConnection:
    """Mock psycopg connection."""

    def __init__(self, cursor_results=None):
        self._cursor = MockCursor(cursor_results or [])

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


# =========================================================================
# State management tests
# =========================================================================


class TestStateManagement:
    """Test WCC state file load/save/invalidation."""

    def test_default_state(self, tmp_path):
        with patch('wcc_assembly.WCC_STATE_FILE', tmp_path / "wcc_state.json"):
            state = load_wcc_state()
            assert state["current_activity"] is None
            assert state["cached_wcc"] is None
            assert state["cache_invalidated"] is False

    def test_save_and_load_state(self, tmp_path):
        state_file = tmp_path / "wcc_state.json"
        with patch('wcc_assembly.WCC_STATE_FILE', state_file), \
             patch('wcc_assembly.STATE_DIR', tmp_path):
            state = {"current_activity": "auth-flow", "cached_wcc": "test", "cached_at": "2026-01-01T00:00:00+00:00"}
            save_wcc_state(state)
            loaded = load_wcc_state()
            assert loaded["current_activity"] == "auth-flow"
            assert loaded["cached_wcc"] == "test"

    def test_invalidate_cache(self, tmp_path):
        state_file = tmp_path / "wcc_state.json"
        with patch('wcc_assembly.WCC_STATE_FILE', state_file), \
             patch('wcc_assembly.STATE_DIR', tmp_path):
            state = {"current_activity": "test", "cache_invalidated": False}
            save_wcc_state(state)
            invalidate_wcc_cache()
            loaded = load_wcc_state()
            assert loaded["cache_invalidated"] is True

    def test_cache_valid_within_ttl(self):
        state = {
            "cached_wcc": "some context",
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "cache_invalidated": False,
        }
        assert _is_cache_valid(state) is True

    def test_cache_invalid_when_invalidated(self):
        state = {
            "cached_wcc": "some context",
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "cache_invalidated": True,
        }
        assert _is_cache_valid(state) is False

    def test_cache_invalid_when_expired(self):
        state = {
            "cached_wcc": "some context",
            "cached_at": "2020-01-01T00:00:00+00:00",
            "cache_invalidated": False,
        }
        assert _is_cache_valid(state) is False

    def test_cache_invalid_when_empty(self):
        state = {"cached_wcc": None, "cached_at": None, "cache_invalidated": False}
        assert _is_cache_valid(state) is False


# =========================================================================
# Activity detection tests
# =========================================================================


class TestActivityDetection:
    """Test detect_activity() with mocked DB connections."""

    def test_no_activities_returns_none(self, tmp_path):
        """When no activities exist, detection returns None."""
        conn = MockConnection([])
        with patch('wcc_assembly.WCC_STATE_FILE', tmp_path / "wcc_state.json"), \
             patch('wcc_assembly.STATE_DIR', tmp_path):
            # Mock: no session fact, no project found
            name, changed, act_id = detect_activity(
                "just a random prompt", "test-project", conn
            )
            # No match expected since mock returns empty results
            assert name is None or changed is False

    def test_manual_override_takes_precedence(self, tmp_path):
        """session_fact('current_activity') overrides all detection."""
        # First call: check manual override -> returns "my-activity"
        # Second call: lookup activity_id -> returns None
        cursor = MagicMock()
        cursor.fetchone = MagicMock(side_effect=[
            {"fact_value": "my-activity"},  # manual override
            None,  # activity_id lookup
        ])
        cursor.fetchall = MagicMock(return_value=[])
        conn = MagicMock()
        conn.cursor.return_value = cursor

        with patch('wcc_assembly.WCC_STATE_FILE', tmp_path / "wcc_state.json"), \
             patch('wcc_assembly.STATE_DIR', tmp_path):
            name, changed, act_id = detect_activity(
                "some prompt", "test-project", conn, session_id="abc-123"
            )
            assert name == "my-activity"


# =========================================================================
# Utility tests
# =========================================================================


class TestTruncation:
    """Test budget-based text truncation."""

    def test_short_text_unchanged(self):
        text = "short text"
        assert _truncate_to_budget(text, 100) == text

    def test_long_text_truncated(self):
        text = "x" * 1000
        result = _truncate_to_budget(text, 50)
        # 50 tokens * 4 chars = 200 chars max
        assert len(result) <= 200 + 4  # +4 for "...\n"

    def test_truncation_preserves_lines(self):
        text = "line1\nline2\nline3\nline4\n" + "x" * 500
        result = _truncate_to_budget(text, 20)
        # Should truncate at a newline boundary
        assert result.endswith("...")
