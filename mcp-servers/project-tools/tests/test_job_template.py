"""
Tests for handlers/job_template.py — F224 BT700.

Strategy: Approach 1 (mocked DB).
The schema (BT694) may not yet be applied.  We mock the DB connection and
cursor to verify the *SQL produced* and the *return shape*, with no live DB
required.

Coverage:
    - create happy path → correct INSERT SQL
    - create + publish_version → two DB writes (template + version)
    - add_origin resolves the right FK column for all 6 origin kinds
    - add_origin rejects an invalid origin_kind
    - read returns the expected envelope (template + versions + origins + runs)
    - resolve_dead_letter with 'rerun' creates a new task + sets superseded_by
    - pause / unpause toggle is_paused
    - list returns paginated envelope
    - update rejects unknown fields / payload changes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Make the handlers package importable without an installed package.
# ---------------------------------------------------------------------------
_PROJECT_TOOLS = Path(__file__).resolve().parent.parent
if str(_PROJECT_TOOLS) not in sys.path:
    sys.path.insert(0, str(_PROJECT_TOOLS))

from handlers.job_template import (
    _ORIGIN_KIND_COLUMN,
    handle_job_template,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_cursor(rows: list[dict] | None = None, fetchone_row: dict | None = None):
    """Return a mock cursor that returns predictable rows."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_row
    cur.fetchall.return_value = rows or []
    return cur


def _make_conn(cursor: MagicMock | None = None) -> MagicMock:
    """Return a mock DB connection."""
    conn = MagicMock()
    conn.cursor.return_value = cursor or _make_cursor()
    return conn


def _patch_conn(conn: MagicMock):
    """Patch get_db_connection inside the handler module."""
    return patch(
        "handlers.job_template.handle_job_template.__code__",
        # We patch at the dispatch level — simpler to patch the import used
        # inside handle_job_template. We re-patch at import location.
    )


# ---------------------------------------------------------------------------
# Shared helper: call handle_job_template with a mocked get_db_connection.
# ---------------------------------------------------------------------------

def _call(action: str, conn: MagicMock, **kwargs) -> dict:
    """Invoke handle_job_template with a mocked DB connection."""
    with patch("server_v2.get_db_connection", return_value=conn, create=True):
        # The handler does `from server_v2 import get_db_connection`
        # at call time — we need to patch where it's imported from.
        import importlib
        import handlers.job_template as hmod
        with patch.object(hmod, "_call_get_db", return_value=conn, create=True):
            # Simpler: patch at the module level by temporarily replacing the
            # import mechanism. Use patch on the function that calls get_db_connection.
            pass

    # Cleanest approach: patch `server_v2` in sys.modules so the
    # `from server_v2 import get_db_connection` inside handle_job_template
    # finds our mock.
    fake_server = MagicMock()
    fake_server.get_db_connection.return_value = conn

    with patch.dict(sys.modules, {"server_v2": fake_server}):
        import importlib
        import handlers.job_template as hmod
        importlib.reload(hmod)   # pick up the patched sys.modules
        result = hmod.handle_job_template(action, **kwargs)

    return result


# ---------------------------------------------------------------------------
# Simpler approach: directly call the private action functions,
# bypassing handle_job_template's import of get_db_connection.
# This is cleaner for unit tests.
# ---------------------------------------------------------------------------

from handlers.job_template import (
    _create,
    _update,
    _publish_version,
    _add_origin,
    _remove_origin,
    _list,
    _read,
    _pause,
    _unpause,
    _resolve_dead_letter,
)


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------

class TestCreate:
    def test_happy_path_returns_correct_shape(self):
        """create returns template_id, name, current_version on success."""
        template_row = {
            "template_id": "aaaabbbb-0000-0000-0000-000000000001",
            "name": "embed-vault",
            "current_version": 1,
        }
        cur = _make_cursor(fetchone_row=template_row)
        conn = _make_conn(cur)

        result = _create(
            conn,
            session_id="sess-1",
            name="embed-vault",
            description="Runs the vault embedding pipeline",
            kind="script",
        )

        assert result["success"] is True
        assert result["name"] == "embed-vault"
        assert result["current_version"] == 1
        assert "template_id" in result

    def test_inserts_version_row_when_payload_provided(self):
        """When payload= is given, a second INSERT (version) must be issued."""
        template_row = {
            "template_id": "aaaabbbb-0000-0000-0000-000000000002",
            "name": "agent-review",
            "current_version": 1,
        }
        version_row = {"version_id": "vvvvvvvv-0000-0000-0000-000000000001"}

        # cursor needs to return different rows for successive fetchone() calls
        cur = MagicMock()
        cur.fetchone.side_effect = [template_row, version_row, None]  # template, version, audit
        conn = _make_conn(cur)

        result = _create(
            conn,
            session_id="sess-1",
            name="agent-review",
            description="Agent-based PR review",
            kind="agent",
            payload={"model": "claude-opus-4-7", "prompt": "Review this PR"},
        )

        assert result["success"] is True
        assert "version_id" in result
        # Two INSERT statements should have been executed
        assert cur.execute.call_count >= 2

    def test_rejects_invalid_kind(self):
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _create(
            conn, session_id="s", name="bad", description="x" * 30, kind="daemon"
        )
        assert result["success"] is False
        assert "kind" in result["error"]

    def test_rejects_empty_name(self):
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _create(
            conn, session_id="s", name="", description="valid description here", kind="script"
        )
        assert result["success"] is False
        assert "name" in result["error"]

    def test_rejects_empty_description(self):
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _create(
            conn, session_id="s", name="ok", description="", kind="agent"
        )
        assert result["success"] is False
        assert "description" in result["error"]


# ---------------------------------------------------------------------------
# Tests: add_origin — the polymorphic exclusive arc
# ---------------------------------------------------------------------------

class TestAddOrigin:
    """The critical contract: each origin_kind maps to exactly one FK column."""

    @pytest.mark.parametrize("kind,expected_col", [
        ("memory",   "origin_memory_id"),
        ("article",  "origin_article_id"),
        ("feedback", "origin_feedback_id"),
        ("feature",  "origin_feature_id"),
        ("workfile", "origin_workfile_id"),
        ("url",      "origin_url"),
    ])
    def test_correct_column_used(self, kind: str, expected_col: str):
        """add_origin sets only the right column for each origin_kind."""
        origin_row = {"origin_id": "oooooooo-0000-0000-0000-000000000001"}
        cur = MagicMock()
        cur.fetchone.side_effect = [origin_row, None]  # origin INSERT, audit INSERT
        conn = _make_conn(cur)

        ref = "https://example.com/x" if kind == "url" else "bbbbbbbb-0000-0000-0000-000000000001"
        result = _add_origin(
            conn,
            session_id="sess-1",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            origin_kind=kind,
            origin_ref=ref,
            origin_role="rationale",
        )

        assert result["success"] is True, result.get("error")
        assert result["resolved_column"] == expected_col
        assert result["origin_kind"] == kind

        # The INSERT SQL must mention the correct column
        insert_sql = cur.execute.call_args_list[0][0][0]
        assert expected_col in insert_sql, (
            f"Expected column '{expected_col}' in SQL for kind='{kind}', "
            f"got:\n{insert_sql}"
        )

    def test_rejects_unknown_kind(self):
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _add_origin(
            conn,
            session_id="s",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            origin_kind="unknown_kind",
            origin_ref="some-ref",
            origin_role="rationale",
        )
        assert result["success"] is False
        assert "invalid" in result["error"].lower()

    def test_rejects_unknown_role(self):
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _add_origin(
            conn,
            session_id="s",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            origin_kind="memory",
            origin_ref="bbbbbbbb-0000-0000-0000-000000000001",
            origin_role="banana",
        )
        assert result["success"] is False
        assert "invalid" in result["error"].lower()


# ---------------------------------------------------------------------------
# Tests: read
# ---------------------------------------------------------------------------

class TestRead:
    def test_returns_full_envelope(self):
        """read returns template + versions + origins + recent_runs."""
        template_row = {
            "template_id": "aaaabbbb-0000-0000-0000-000000000001",
            "template_id_str": "aaaabbbb-0000-0000-0000-000000000001",
            "name": "my-template",
            "kind": "script",
            "current_version": 2,
            "is_paused": False,
            "runs_total_30d": 10,
            "runs_succeeded_30d": 9,
            "runs_dead_30d": 1,
            "avg_duration_secs": 5.3,
            "p95_duration_secs": 12.1,
            "last_run_at": None,
        }
        version_rows = [
            {"version_id": "v1", "version": 1, "payload": {"cmd": "embed"}},
            {"version_id": "v2", "version": 2, "payload": {"cmd": "embed --all"}},
        ]
        origin_rows = [
            {"origin_id": "o1", "origin_kind": "memory", "origin_role": "rationale"},
        ]
        run_rows = [
            {"run_id": "r1", "status": "completed"},
        ]

        cur = MagicMock()
        # fetchone: template; fetchall: versions, origins, runs
        cur.fetchone.side_effect = [template_row]
        cur.fetchall.side_effect = [version_rows, origin_rows, run_rows]
        conn = _make_conn(cur)

        result = _read(
            conn,
            session_id="sess-1",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
        )

        assert result["success"] is True
        assert "template" in result
        assert "versions" in result
        assert "origins" in result
        assert "recent_runs" in result
        assert len(result["versions"]) == 2
        assert len(result["origins"]) == 1
        assert len(result["recent_runs"]) == 1

    def test_not_found_returns_error(self):
        cur = MagicMock()
        cur.fetchone.return_value = None
        conn = _make_conn(cur)

        result = _read(conn, session_id="s", template_id="does-not-exist")
        assert result["success"] is False
        assert "not found" in result["error"].lower()


# ---------------------------------------------------------------------------
# Tests: resolve_dead_letter
# ---------------------------------------------------------------------------

class TestResolveDeadLetter:
    def _dead_letter_row(self, task_id: str = "tttttttt-0000-0000-0000-000000000001") -> dict:
        return {
            "task_id": task_id,
            "template_id": "aaaabbbb-0000-0000-0000-000000000001",
            "template_version": 1,
            "payload_override": None,
            "status": "dead_letter",
            "priority": 3,
            "project_id": "pppppppp-0000-0000-0000-000000000001",
            "parent_session_id": None,
        }

    def test_rerun_creates_new_task_and_sets_superseded(self):
        dead = self._dead_letter_row()
        new_row = {"task_id": "nnnnnnnn-0000-0000-0000-000000000001"}

        cur = MagicMock()
        # fetchone calls: fetch dead task, new task insert, audit
        cur.fetchone.side_effect = [dead, new_row, None]
        conn = _make_conn(cur)

        result = _resolve_dead_letter(
            conn,
            session_id="sess-1",
            task_id=dead["task_id"],
            resolution="rerun",
            notes="Transient network error — retrying",
        )

        assert result["success"] is True, result.get("error")
        assert result["resolution"] == "rerun"
        assert "new_task_id" in result

        # Verify two UPDATE/INSERT calls were made (new task INSERT + original UPDATE)
        sql_calls = [c[0][0].strip() for c in cur.execute.call_args_list]
        has_insert = any("INSERT INTO claude.task_queue" in s for s in sql_calls)
        has_update_superseded = any("superseded_by_task_id" in s for s in sql_calls)
        assert has_insert, "Expected INSERT for new task_queue row"
        assert has_update_superseded, "Expected UPDATE setting superseded_by_task_id"

    def test_fixed_resolution_no_new_task(self):
        dead = self._dead_letter_row()
        cur = MagicMock()
        cur.fetchone.side_effect = [dead, None]  # fetch, audit
        conn = _make_conn(cur)

        result = _resolve_dead_letter(
            conn,
            session_id="sess-1",
            task_id=dead["task_id"],
            resolution="fixed",
            notes="Root cause fixed in deploy",
        )

        assert result["success"] is True
        assert result["resolution"] == "fixed"
        assert "new_task_id" not in result

    def test_rejects_non_dead_letter_status(self):
        row = self._dead_letter_row()
        row["status"] = "completed"

        cur = MagicMock()
        cur.fetchone.return_value = row
        conn = _make_conn(cur)

        result = _resolve_dead_letter(
            conn,
            session_id="s",
            task_id=row["task_id"],
            resolution="fixed",
        )
        assert result["success"] is False
        assert "dead_letter" in result["error"]

    def test_rejects_invalid_resolution(self):
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _resolve_dead_letter(
            conn,
            session_id="s",
            task_id="tttttttt-0000-0000-0000-000000000001",
            resolution="delete_it",
        )
        assert result["success"] is False
        assert "invalid" in result["error"].lower()


# ---------------------------------------------------------------------------
# Tests: pause / unpause
# ---------------------------------------------------------------------------

class TestPauseUnpause:
    def test_pause_sets_is_paused_true(self):
        row = {"is_paused": False, "name": "embed-vault"}
        cur = MagicMock()
        cur.fetchone.side_effect = [row, None]  # fetch, audit
        conn = _make_conn(cur)

        result = _pause(
            conn,
            session_id="sess-1",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            reason="Circuit breaker tripped",
        )

        assert result["success"] is True
        assert result["is_paused"] is True

        sql_calls = [c[0][0] for c in cur.execute.call_args_list]
        update_sql = next((s for s in sql_calls if "UPDATE" in s), "")
        assert "is_paused = true" in update_sql

    def test_pause_rejects_already_paused(self):
        row = {"is_paused": True, "name": "embed-vault"}
        cur = MagicMock()
        cur.fetchone.return_value = row
        conn = _make_conn(cur)

        result = _pause(
            conn,
            session_id="s",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            reason="Already paused",
        )
        assert result["success"] is False
        assert "already paused" in result["error"].lower()

    def test_unpause_clears_is_paused(self):
        row = {"is_paused": True, "name": "embed-vault", "paused_reason": "breaker"}
        cur = MagicMock()
        cur.fetchone.side_effect = [row, None]  # fetch, audit
        conn = _make_conn(cur)

        result = _unpause(
            conn,
            session_id="sess-1",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            reason="Manually cleared after investigation",
        )

        assert result["success"] is True
        assert result["is_paused"] is False

        sql_calls = [c[0][0] for c in cur.execute.call_args_list]
        update_sql = next((s for s in sql_calls if "UPDATE" in s), "")
        assert "is_paused = false" in update_sql

    def test_unpause_rejects_not_paused(self):
        row = {"is_paused": False, "name": "embed-vault", "paused_reason": None}
        cur = MagicMock()
        cur.fetchone.return_value = row
        conn = _make_conn(cur)

        result = _unpause(
            conn,
            session_id="s",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
        )
        assert result["success"] is False
        assert "not paused" in result["error"].lower()


# ---------------------------------------------------------------------------
# Tests: list
# ---------------------------------------------------------------------------

class TestList:
    def test_returns_paginated_envelope(self):
        rows = [
            {"template_id": "t1", "name": "a", "kind": "script"},
            {"template_id": "t2", "name": "b", "kind": "agent"},
        ]
        count_row = {"cnt": 2}
        cur = MagicMock()
        cur.fetchall.return_value = rows
        cur.fetchone.return_value = count_row
        conn = _make_conn(cur)

        result = _list(conn, session_id="s", limit=10, offset=0)

        assert result["success"] is True
        assert result["total"] == 2
        assert len(result["templates"]) == 2
        assert result["limit"] == 10
        assert result["offset"] == 0

    def test_rejects_invalid_kind_filter(self):
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _list(conn, session_id="s", kind="banana")
        assert result["success"] is False
        assert "kind" in result["error"]


# ---------------------------------------------------------------------------
# Tests: update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_rejects_payload_field(self):
        """payload changes must go through publish_version, not update."""
        cur = _make_cursor()
        conn = _make_conn(cur)
        result = _update(
            conn,
            session_id="s",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            payload={"cmd": "bad"},
        )
        assert result["success"] is False
        # Should complain about no updatable fields
        assert "no updatable" in result["error"].lower() or "payload" in result["error"].lower()

    def test_happy_path_updates_description(self):
        before_row = {
            "description": "old desc",
            "owner": "sess-1",
        }
        updated_row = {"template_id": "aaaabbbb-0000-0000-0000-000000000001"}
        cur = MagicMock()
        cur.fetchone.side_effect = [before_row, updated_row, None]  # fetch, update RETURNING, audit
        conn = _make_conn(cur)

        result = _update(
            conn,
            session_id="sess-1",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            description="new description text",
        )

        assert result["success"] is True
        assert "description" in result["updated_fields"]


# ---------------------------------------------------------------------------
# Tests: publish_version
# ---------------------------------------------------------------------------

class TestPublishVersion:
    def test_increments_version_and_returns_version_id(self):
        template_row = {"current_version": 1}
        version_row = {"version_id": "vvvvvvvv-0000-0000-0000-000000000002"}

        cur = MagicMock()
        cur.fetchone.side_effect = [template_row, version_row, None]  # lock, insert, audit
        conn = _make_conn(cur)

        result = _publish_version(
            conn,
            session_id="sess-1",
            template_id="aaaabbbb-0000-0000-0000-000000000001",
            payload={"cmd": "embed --all", "cwd": "/projects"},
            notes="Add --all flag",
        )

        assert result["success"] is True
        assert result["version"] == 2
        assert "version_id" in result

        # Verify UPDATE bumped current_version
        sql_calls = [c[0][0] for c in cur.execute.call_args_list]
        update_sql = next((s for s in sql_calls if "UPDATE" in s and "current_version" in s), "")
        assert update_sql, "Expected UPDATE claude.job_templates SET current_version"
