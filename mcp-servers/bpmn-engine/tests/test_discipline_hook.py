"""
Tests for task_discipline_hook.py - FB108 fix validation.

Tests the 3-way discipline gateway logic:
  - allowed: session match + tasks exist
  - continuation: session mismatch but map fresh (< 2h)
  - blocked: no tasks or truly stale map (> 2h)

These tests validate the hook's decision logic WITHOUT running the hook
as a subprocess, making them fast and deterministic.
"""

import json
import os
import sys
import time
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts dir to path for importing the hook
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import after path setup
import task_discipline_hook as hook


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_map_dir(tmp_path, monkeypatch):
    """Redirect task map files to a temp directory."""
    def _get_map_path(project_name):
        return tmp_path / f"claude_task_map_{project_name}.json"
    monkeypatch.setattr(hook, "get_task_map_path", _get_map_path)
    return tmp_path


def write_map(tmp_path, project_name, session_id, tasks=None):
    """Write a task map file with given session and tasks."""
    data = {"_session_id": session_id}
    if tasks:
        data.update(tasks)
    path = tmp_path / f"claude_task_map_{project_name}.json"
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def age_file(path, seconds):
    """Artificially age a file by setting mtime in the past."""
    old_time = time.time() - seconds
    os.utime(path, (old_time, old_time))


# ---------------------------------------------------------------------------
# Decision logic simulation
# ---------------------------------------------------------------------------

def simulate_hook_decision(
    task_entries: dict,
    map_session_id: str,
    current_session_id: str,
    map_age_seconds: float = 0,
    continuation_max_age: int = 7200,
    race_max_age: int = 30,
) -> str:
    """Simulate the hook's cascading decision logic.

    Returns: "allow", "continuation", "race_allow", or "deny"
    This mirrors the actual hook logic after FB108 fix.
    """
    if task_entries and map_session_id == current_session_id:
        return "allow"  # Exact session match
    elif task_entries and not current_session_id:
        return "allow"  # No session_id available
    elif task_entries and map_session_id != current_session_id:
        # FB108 fix: check recency before denying
        if map_age_seconds < continuation_max_age:
            return "continuation"  # Fresh enough, allow with warning
        else:
            return "deny"  # Truly stale
    elif not task_entries and map_age_seconds < race_max_age:
        return "race_allow"  # Race condition fallback
    else:
        return "deny"  # No tasks, not a race


# ---------------------------------------------------------------------------
# TestDisciplineHookDecision: Pure logic tests
# ---------------------------------------------------------------------------

class TestDisciplineHookDecision:
    """Test the cascading decision logic of the discipline hook."""

    def test_exact_session_match_allows(self):
        """Tasks exist + session match = allow."""
        result = simulate_hook_decision(
            task_entries={"1": "todo-1", "2": "todo-2"},
            map_session_id="session-abc",
            current_session_id="session-abc",
        )
        assert result == "allow"

    def test_no_session_id_allows(self):
        """Tasks exist + no current session_id = allow (edge case)."""
        result = simulate_hook_decision(
            task_entries={"1": "todo-1"},
            map_session_id="session-abc",
            current_session_id="",
        )
        assert result == "allow"

    def test_continuation_session_fresh_map(self):
        """Session mismatch + map fresh (< 2h) = continuation (FB108 fix)."""
        result = simulate_hook_decision(
            task_entries={"1": "todo-1"},
            map_session_id="old-session",
            current_session_id="new-session",
            map_age_seconds=300,  # 5 minutes old
        )
        assert result == "continuation"

    def test_continuation_at_boundary(self):
        """Session mismatch + map at exactly 2h boundary = continuation."""
        result = simulate_hook_decision(
            task_entries={"1": "todo-1"},
            map_session_id="old-session",
            current_session_id="new-session",
            map_age_seconds=7199,  # Just under 2h
        )
        assert result == "continuation"

    def test_stale_session_denied(self):
        """Session mismatch + map older than 2h = deny (truly stale)."""
        result = simulate_hook_decision(
            task_entries={"1": "todo-1"},
            map_session_id="old-session",
            current_session_id="new-session",
            map_age_seconds=7201,  # Just over 2h
        )
        assert result == "deny"

    def test_truly_stale_map_denied(self):
        """Session mismatch + map many hours old = deny."""
        result = simulate_hook_decision(
            task_entries={"1": "todo-1"},
            map_session_id="yesterday-session",
            current_session_id="today-session",
            map_age_seconds=86400,  # 24 hours
        )
        assert result == "deny"

    def test_no_tasks_denied(self):
        """No tasks + no race condition = deny."""
        result = simulate_hook_decision(
            task_entries={},
            map_session_id="session-abc",
            current_session_id="session-abc",
            map_age_seconds=60,  # Not a race (> 30s)
        )
        assert result == "deny"

    def test_race_condition_allows(self):
        """No tasks + recently modified (< 30s) = race condition allow."""
        result = simulate_hook_decision(
            task_entries={},
            map_session_id="session-abc",
            current_session_id="session-abc",
            map_age_seconds=5,  # Very fresh
        )
        assert result == "race_allow"

    def test_ungated_tools_skipped(self):
        """Ungated tools (Read, Grep, Glob) should never reach decision logic."""
        for tool in ["Read", "Grep", "Glob", "WebSearch", "AskUserQuestion"]:
            assert tool not in hook.GATED_TOOLS

    def test_all_gated_tools_present(self):
        """All expected gated tools are registered."""
        expected = {"Write", "Edit", "Task", "Bash"}
        assert hook.GATED_TOOLS == expected


# ---------------------------------------------------------------------------
# TestDisciplineHookIntegration: File-based tests using actual hook functions
# ---------------------------------------------------------------------------

class TestDisciplineHookIntegration:
    """Test with actual file I/O using the hook's load/check functions."""

    def test_real_file_continuation_allows(self, temp_map_dir):
        """Write a map file, check it reads correctly for continuation."""
        project = "test-project"
        path = write_map(temp_map_dir, project, "old-session", {"1": "t1", "2": "t2"})

        # File is fresh (just written)
        task_map = hook.load_task_map(project)
        task_entries = {k: v for k, v in task_map.items() if not k.startswith("_")}
        map_session_id = task_map.get("_session_id", "")

        assert len(task_entries) == 2
        assert map_session_id == "old-session"

        # map_recently_modified with 2h window should return True for fresh file
        assert hook.map_recently_modified(project, max_age_seconds=7200) is True

    def test_real_file_stale_denied(self, temp_map_dir):
        """Write a map file, age it, verify staleness detection."""
        project = "test-project"
        path = write_map(temp_map_dir, project, "old-session", {"1": "t1"})

        # Age the file to 3 hours old
        age_file(path, 10800)

        # Short recency check (30s) should fail
        assert hook.map_recently_modified(project, max_age_seconds=30) is False

        # Even 2h window should fail for 3h-old file
        assert hook.map_recently_modified(project, max_age_seconds=7200) is False

    def test_missing_map_file(self, temp_map_dir):
        """No map file at all returns empty dict."""
        task_map = hook.load_task_map("nonexistent-project")
        assert task_map == {}

    def test_empty_map_file(self, temp_map_dir):
        """Map with only _session_id has no task entries."""
        project = "empty-project"
        write_map(temp_map_dir, project, "session-123", tasks=None)

        task_map = hook.load_task_map(project)
        task_entries = {k: v for k, v in task_map.items() if not k.startswith("_")}
        assert len(task_entries) == 0
        assert task_map.get("_session_id") == "session-123"

    def test_map_recently_modified_boundary(self, temp_map_dir):
        """Verify boundary behavior of map_recently_modified."""
        project = "boundary-test"
        path = write_map(temp_map_dir, project, "s1", {"1": "t1"})

        # Fresh file (just written) - should pass any reasonable window
        assert hook.map_recently_modified(project, max_age_seconds=1) is True

        # Age file to 60 seconds
        age_file(path, 60)

        # 30s window should fail, 120s window should pass
        assert hook.map_recently_modified(project, max_age_seconds=30) is False
        assert hook.map_recently_modified(project, max_age_seconds=120) is True
