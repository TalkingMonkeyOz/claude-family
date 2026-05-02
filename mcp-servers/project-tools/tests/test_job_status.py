"""
Tests for handlers/job_status.py (BT704, F224).

Strategy: all DB interaction is mocked — we inject a fake cursor / connection
so that no real database is needed. This lets tests run even before the new
schema tables (job_templates, task_queue, etc.) are migrated.

Each of the 7 views gets:
  - 1 happy-path test
  - 1 edge-case test

Edge cases:
  board          — empty queue (zeros everywhere)
  queue          — mixed statuses (filtering is correct)
  dead_letter    — ordered by age (oldest first)
  runs           — filtered by template_id/name
  result         — joins all 3 sources (task + agent_session + feedback)
  templates      — pulls from job_template_stats VIEW (with stats present)
  template       — includes versions + origins + recent runs
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import pytest

# Ensure handlers/ is importable
_HANDLERS_DIR = Path(__file__).resolve().parent.parent / "handlers"
if str(_HANDLERS_DIR) not in sys.path:
    sys.path.insert(0, str(_HANDLERS_DIR))

from job_status import handle_job_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cursor(fetchone_returns=None, fetchall_returns=None):
    """
    Build a MagicMock cursor where:
      - fetchone() pops the next value from fetchone_returns (list)
      - fetchall() pops the next value from fetchall_returns (list)
      - execute() is a no-op by default
    """
    cur = MagicMock()
    fo_queue = list(fetchone_returns or [])
    fa_queue = list(fetchall_returns or [])

    def _fetchone():
        return fo_queue.pop(0) if fo_queue else None

    def _fetchall():
        return fa_queue.pop(0) if fa_queue else []

    cur.fetchone.side_effect = _fetchone
    cur.fetchall.side_effect = _fetchall
    return cur


def _patch_db(cur):
    """
    Context-manager patch: replace get_db_connection in job_status with a
    fake connection that yields `cur`.
    """
    conn = MagicMock()
    conn.cursor.return_value = cur
    return patch("job_status.get_db_connection", return_value=conn)


def _ts(s="2026-05-02T10:00:00"):
    """Return a timezone-aware datetime for use in fake rows."""
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helper: _tables_exist responses
# We need the cursor to answer the information_schema query used by
# _tables_exist(). It always uses fetchone() and expects {"cnt": N}.
# For "all tables present" return cnt == len(tables); for "absent" return 0.
# ---------------------------------------------------------------------------

def _exist_row(present: bool, count: int = 1):
    """Return a fetchone row for _tables_exist check."""
    return {"cnt": count if present else 0}


# ---------------------------------------------------------------------------
# VIEW: board
# ---------------------------------------------------------------------------

class TestBoardView:
    """board — system snapshot."""

    def test_board_happy_path(self):
        """board with populated queue, templates, and recent runs.

        Fetchone call sequence in _view_board:
          1. _tables_exist("task_queue")      -> {"cnt": 1}
          2. aggregate queue counts           -> {pending, in_progress, ...}
          3. _tables_exist("job_templates")   -> {"cnt": 1}  (paused check)
          4. paused count                     -> {"cnt": 1}
          5. (recent_runs uses fetchall)
          6. _tables_exist("job_templates")   -> {"cnt": 1}  (active_templates check)
          7. (active_templates uses fetchall)
        """
        cur = MagicMock()

        queue_counts = {
            "pending": 3, "in_progress": 1,
            "completed_24h": 10, "dead_letter": 2,
        }
        run_rows = [
            {"run_id": "r1", "template_name": "daily-digest", "trigger_kind": "cron",
             "status": "completed", "started_at": _ts(), "duration_secs": 12.5, "error": None},
        ]
        active_tpl_rows = [
            {"template_id": "t1", "name": "daily-digest", "kind": "agent",
             "is_paused": False, "current_version": 2},
        ]

        fo_seq = [
            {"cnt": 1},     # 1: _tables_exist("task_queue")
            queue_counts,   # 2: aggregate queue counts
            {"cnt": 1},     # 3: _tables_exist("job_templates") — paused check
            {"cnt": 1},     # 4: paused_templates count
            {"cnt": 1},     # 6: _tables_exist("job_templates") — active_templates check
        ]
        fa_seq = [run_rows, active_tpl_rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="board")

        assert result["success"] is True
        assert result["view"] == "board"
        qs = result["queue_summary"]
        assert qs["pending"] == 3
        assert qs["in_progress"] == 1
        assert qs["completed_24h"] == 10
        assert qs["dead_letter"] == 2
        assert qs["paused_templates"] == 1
        assert len(result["recent_runs"]) == 1
        assert result["recent_runs"][0]["template_name"] == "daily-digest"
        assert len(result["active_templates"]) == 1

    def test_board_empty_queue(self):
        """board on an empty system — all counts are 0.

        Fetchone sequence:
          1. _tables_exist("task_queue")     -> {"cnt": 1}
          2. queue counts (all zeros)
          3. _tables_exist("job_templates")  -> {"cnt": 1} (paused)
          4. paused count                    -> {"cnt": 0}
          5. (recent_runs fetchall -> [])
          6. _tables_exist("job_templates")  -> {"cnt": 1} (active_templates)
          7. (active_templates fetchall -> [])
        """
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},     # 1: task_queue exists
            {"pending": 0, "in_progress": 0, "completed_24h": 0, "dead_letter": 0},  # 2
            {"cnt": 1},     # 3: job_templates exists (paused check)
            {"cnt": 0},     # 4: paused_templates count
            {"cnt": 1},     # 6: job_templates exists (active_templates)
        ]
        fa_seq = [
            [],  # 5: recent_runs (empty)
            [],  # 7: active_templates (empty)
        ]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="board")

        assert result["success"] is True
        qs = result["queue_summary"]
        assert qs["pending"] == 0
        assert qs["in_progress"] == 0
        assert qs["completed_24h"] == 0
        assert qs["dead_letter"] == 0
        assert qs["paused_templates"] == 0
        assert result["recent_runs"] == []
        assert result["active_templates"] == []


# ---------------------------------------------------------------------------
# VIEW: queue
# ---------------------------------------------------------------------------

class TestQueueView:
    """queue — live pending/in_progress."""

    def test_queue_happy_path(self):
        """Returns pending + in_progress tasks correctly."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # task_queue exists
            {"cnt": 5},   # total count
        ]
        task_rows = [
            {"task_id": "t1", "template_name": "summarise", "status": "pending",
             "priority": 3, "attempts": 0, "claimed_by": None,
             "claimed_until": None, "enqueued_at": _ts(), "age_secs": 120},
            {"task_id": "t2", "template_name": "summarise", "status": "in_progress",
             "priority": 2, "attempts": 1, "claimed_by": "worker-1",
             "claimed_until": _ts("2026-05-02T10:05:00"), "enqueued_at": _ts(), "age_secs": 300},
        ]
        fa_seq = [task_rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="queue", limit=50)

        assert result["success"] is True
        assert result["view"] == "queue"
        assert result["total"] == 5
        assert len(result["tasks"]) == 2
        assert result["tasks"][0]["status"] == "pending"
        assert result["tasks"][1]["claimed_by"] == "worker-1"
        assert result["truncated"] is False

    def test_queue_filters_statuses(self):
        """When status_filter is provided, only matching rows are returned."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # task_queue exists
            {"cnt": 1},   # total count (only dead_letter)
        ]
        task_rows = [
            {"task_id": "t3", "template_name": "triage", "status": "dead_letter",
             "priority": 1, "attempts": 5, "claimed_by": None,
             "claimed_until": None, "enqueued_at": _ts(), "age_secs": 9000},
        ]
        fa_seq = [task_rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="queue", status_filter=["dead_letter"])

        assert result["success"] is True
        # Verify the execute was called with the correct status list
        calls_sql = [str(c.args[0]) for c in cur.execute.call_args_list if c.args]
        # The ANY(%s) should have been built with the status_filter
        assert any("ANY" in sql for sql in calls_sql)
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["status"] == "dead_letter"


# ---------------------------------------------------------------------------
# VIEW: dead_letter
# ---------------------------------------------------------------------------

class TestDeadLetterView:
    """dead_letter — unresolved, oldest first."""

    def test_dead_letter_happy_path(self):
        """Returns unresolved dead_letter rows."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # task_queue exists
            {"cnt": 2},   # total
        ]
        rows = [
            {"task_id": "dl1", "template_name": "heavy-job", "last_error": "OOM",
             "age_days": 3.5, "surfaced_as_feedback_id": "fb-uuid-1"},
            {"task_id": "dl2", "template_name": "heavy-job", "last_error": "Timeout",
             "age_days": 1.2, "surfaced_as_feedback_id": None},
        ]
        fa_seq = [rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="dead_letter")

        assert result["success"] is True
        assert result["view"] == "dead_letter"
        assert result["total"] == 2
        assert len(result["tasks"]) == 2

    def test_dead_letter_ordered_oldest_first(self):
        """ORDER BY completed_at ASC so oldest surfaces at index 0."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # task_queue exists
            {"cnt": 2},
        ]
        # Simulate DB returning oldest first (as the SQL specifies)
        rows = [
            {"task_id": "dl-old", "template_name": "old-job", "last_error": "err",
             "age_days": 7.0, "surfaced_as_feedback_id": None},
            {"task_id": "dl-new", "template_name": "new-job", "last_error": "err",
             "age_days": 0.5, "surfaced_as_feedback_id": None},
        ]
        fa_seq = [rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="dead_letter")

        assert result["tasks"][0]["task_id"] == "dl-old"
        assert result["tasks"][0]["age_days"] > result["tasks"][1]["age_days"]
        # Verify the SQL contained ORDER BY … ASC
        calls_sql = [str(c.args[0]) for c in cur.execute.call_args_list if c.args]
        order_calls = [s for s in calls_sql if "ORDER BY" in s]
        assert any("ASC" in s for s in order_calls)


# ---------------------------------------------------------------------------
# VIEW: runs
# ---------------------------------------------------------------------------

class TestRunsView:
    """runs — audit log filtered by template/status/date."""

    def test_runs_happy_path(self):
        """Returns run history for a given template."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # job_templates exists (for has_new_cols)
            {"cnt": 3},   # total
        ]
        run_rows = [
            {"run_id": "r1", "template_name": "daily-digest", "trigger_kind": "cron",
             "status": "completed", "started_at": _ts(), "duration_secs": 14.0, "error": None},
        ]
        fa_seq = [run_rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="runs", template_filter="daily-digest")

        assert result["success"] is True
        assert result["view"] == "runs"
        assert result["total"] == 3
        assert len(result["runs"]) == 1
        assert result["runs"][0]["template_name"] == "daily-digest"

    def test_runs_filtered_by_template_id(self):
        """template_filter is passed into the WHERE clause when job_templates exists."""
        cur = MagicMock()

        tpl_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        fo_seq = [
            {"cnt": 1},   # job_templates exists
            {"cnt": 1},   # total
        ]
        fa_seq = [
            [{"run_id": "r2", "template_name": "my-tpl", "trigger_kind": "ad_hoc",
              "status": "failed", "started_at": _ts(), "duration_secs": None, "error": "boom"}],
        ]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="runs", template_filter=tpl_uuid)

        assert result["success"] is True
        # The template_filter UUID should appear in at least one execute() call args
        all_params = []
        for c in cur.execute.call_args_list:
            if len(c.args) > 1:
                all_params.extend(list(c.args[1]))
        assert tpl_uuid in all_params or any(tpl_uuid in str(p) for p in all_params)


# ---------------------------------------------------------------------------
# VIEW: result
# ---------------------------------------------------------------------------

class TestResultView:
    """result — single task with all joins."""

    def test_result_joins_all_sources(self):
        """Task row + agent_session + feedback all present and merged."""
        cur = MagicMock()

        task_uuid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        session_uuid = "cccccccc-cccc-cccc-cccc-cccccccccccc"
        fb_uuid = "dddddddd-dddd-dddd-dddd-dddddddddddd"

        task_row = {
            "task_id": task_uuid, "task_id_str": task_uuid,
            "template_name": "my-job", "status": "dead_letter",
            "priority": 2, "attempts": 3, "last_error": "crash",
            "result": None, "output_text": None,
            "surfaced_as_feedback_id": fb_uuid,
            "agent_session_id": session_uuid,
            "enqueued_at": _ts(), "started_at": _ts(), "completed_at": _ts(),
        }
        session_row = {
            "session_id": session_uuid, "agent_type": "claude",
            "task_description": "my-job run", "success": False,
            "output_text": "trace...",
        }
        fb_row = {
            "feedback_id": fb_uuid, "feedback_type": "bug",
            "description": "job crashed", "status": "open", "created_at": _ts(),
        }

        fo_seq = [
            {"cnt": 1},   # task_queue exists
            task_row,     # main task fetch
            session_row,  # agent_sessions fetch
            fb_row,       # feedback fetch
        ]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None

        with _patch_db(cur):
            result = handle_job_status(view="result", task_id=task_uuid)

        assert result["success"] is True
        assert result["view"] == "result"
        assert result["task"]["status"] == "dead_letter"
        assert result["agent_session"]["agent_type"] == "claude"
        assert result["feedback"]["feedback_type"] == "bug"

    def test_result_missing_task_id_returns_error(self):
        """view='result' without task_id returns validation error, no DB call."""
        with patch("job_status.get_db_connection") as mock_conn:
            result = handle_job_status(view="result")

        mock_conn.assert_not_called()
        assert result["success"] is False
        assert "task_id" in result["error"]

    def test_result_task_not_found(self):
        """Returns error when task_id doesn't match any row."""
        cur = MagicMock()
        fo_seq = [
            {"cnt": 1},   # task_queue exists
            None,         # task not found
        ]
        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None

        with _patch_db(cur):
            result = handle_job_status(view="result", task_id="00000000-0000-0000-0000-000000000000")

        assert result["success"] is False
        assert "not found" in result["error"].lower()


# ---------------------------------------------------------------------------
# VIEW: templates
# ---------------------------------------------------------------------------

class TestTemplatesView:
    """templates — catalog with stats VIEW."""

    def test_templates_with_stats(self):
        """Returns template rows joined to job_template_stats VIEW."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # job_templates exists
            {"cnt": 1},   # job_template_stats exists
            {"cnt": 2},   # total templates
        ]
        tpl_rows = [
            {"template_id": "t1", "name": "alpha", "kind": "agent",
             "is_paused": False, "current_version": 1,
             "runs_total_30d": 45, "runs_succeeded_30d": 43, "runs_dead_30d": 2,
             "p95_duration_secs": 18.3, "last_run_at": _ts()},
            {"template_id": "t2", "name": "beta", "kind": "script",
             "is_paused": True, "current_version": 3,
             "runs_total_30d": 10, "runs_succeeded_30d": 8, "runs_dead_30d": 0,
             "p95_duration_secs": 4.1, "last_run_at": _ts()},
        ]
        fa_seq = [tpl_rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="templates")

        assert result["success"] is True
        assert result["has_stats"] is True
        assert result["total"] == 2
        assert len(result["templates"]) == 2
        assert result["templates"][0]["runs_total_30d"] == 45

    def test_templates_fallback_without_stats_view(self):
        """Falls back gracefully when job_template_stats VIEW doesn't exist yet."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # job_templates exists
            {"cnt": 0},   # job_template_stats does NOT exist
            {"cnt": 1},   # total templates
        ]
        tpl_rows = [
            {"template_id": "t1", "name": "alpha", "kind": "agent",
             "is_paused": False, "current_version": 1,
             "runs_total_30d": None, "runs_succeeded_30d": None, "runs_dead_30d": None,
             "p95_duration_secs": None, "last_run_at": None},
        ]
        fa_seq = [tpl_rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="templates")

        assert result["success"] is True
        assert result["has_stats"] is False
        assert len(result["templates"]) == 1
        assert result["templates"][0]["runs_total_30d"] is None


# ---------------------------------------------------------------------------
# VIEW: template
# ---------------------------------------------------------------------------

class TestTemplateView:
    """template — single template with versions, origins, recent runs."""

    def test_template_full_detail(self):
        """Returns template + versions + origins + recent_runs."""
        cur = MagicMock()

        tpl_uuid = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
        tpl_row = {
            "template_id": tpl_uuid, "name": "daily-digest",
            "kind": "agent", "is_paused": False, "current_version": 2,
            "owner": "session-x", "created_at": _ts(),
        }
        version_rows = [
            {"version_id": "v1", "version": 2, "created_at": _ts(), "created_by": "me", "notes": "update"},
            {"version_id": "v0", "version": 1, "created_at": _ts(), "created_by": "me", "notes": "init"},
        ]
        origin_rows = [
            {"origin_id": "o1", "origin_kind": "feature", "origin_role": "rationale",
             "note": "F224 scope", "created_at": _ts()},
        ]
        run_rows = [
            {"run_id": "r1", "trigger_kind": "cron", "status": "completed",
             "started_at": _ts(), "duration_secs": 11.0, "error": None},
        ]

        fo_seq = [
            {"cnt": 1},   # job_templates exists (initial check)
            tpl_row,      # template lookup
            {"cnt": 1},   # job_template_versions exists
            {"cnt": 1},   # job_template_origins exists
            {"cnt": 1},   # job_templates exists (for has_new_cols in recent_runs)
        ]
        fa_seq = [version_rows, origin_rows, run_rows]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="template", template_id=tpl_uuid)

        assert result["success"] is True
        assert result["view"] == "template"
        assert result["template"]["name"] == "daily-digest"
        assert len(result["versions"]) == 2
        assert result["versions"][0]["version"] == 2  # latest first
        assert len(result["origins"]) == 1
        assert len(result["recent_runs"]) == 1

    def test_template_not_found(self):
        """Returns error when template UUID doesn't match."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # job_templates exists
            None,         # template not found
        ]
        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None

        with _patch_db(cur):
            result = handle_job_status(view="template", template_id="00000000-0000-0000-0000-000000000000")

        assert result["success"] is False
        assert "not found" in result["error"].lower()


# ---------------------------------------------------------------------------
# Input validation edge cases
# ---------------------------------------------------------------------------

class TestValidation:
    """Input validation — no DB calls made on bad input."""

    def test_unknown_view_returns_error(self):
        with patch("job_status.get_db_connection") as mock_conn:
            result = handle_job_status(view="nonexistent")
        mock_conn.assert_not_called()
        assert result["success"] is False
        assert "nonexistent" in result["error"]

    def test_template_view_without_template_id_returns_error(self):
        with patch("job_status.get_db_connection") as mock_conn:
            result = handle_job_status(view="template")
        mock_conn.assert_not_called()
        assert result["success"] is False
        assert "template_id" in result["error"]

    def test_limit_is_clamped_to_200(self):
        """limit > 200 is silently clamped — no crash."""
        cur = MagicMock()

        fo_seq = [
            {"cnt": 1},   # task_queue exists
            {"cnt": 0},   # total
        ]
        fa_seq = [[]]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="queue", limit=9999)

        assert result["success"] is True
        # Verify the LIMIT in the SQL was not 9999
        calls_sql_params = [c.args for c in cur.execute.call_args_list if c.args and len(c.args) > 1]
        all_params = [p for args in calls_sql_params for p in args[1]]
        # The actual limit passed should be 200+1 = 201 (budget cap probe)
        assert 201 in all_params

    def test_pre_migration_fallback_for_board(self):
        """board view works gracefully when task_queue and job_templates don't exist yet.

        Fetchone sequence (task_queue absent, job_templates absent):
          1. _tables_exist("task_queue")     -> {"cnt": 0}  -> skip queue counts
          2. _tables_exist("job_templates")  -> {"cnt": 0}  -> skip paused count
          3. (recent_runs fetchall — new-col query raises, fallback fetchall used)
          4. _tables_exist("job_templates")  -> {"cnt": 0}  -> skip active_templates
        """
        cur = MagicMock()

        # Make recent_runs new-column query raise (simulate missing column)
        # by raising on the second execute() call (first two are for _tables_exist).
        execute_count = [0]
        original_execute = cur.execute

        def patched_execute(sql, params=None):
            execute_count[0] += 1
            # 3rd execute = recent_runs new-column query — raise to trigger fallback
            if execute_count[0] == 3:
                raise Exception("column template_id does not exist")

        cur.execute.side_effect = patched_execute

        fo_seq = [
            {"cnt": 0},   # 1: task_queue does NOT exist
            {"cnt": 0},   # 2: job_templates does NOT exist (paused check)
            {"cnt": 0},   # 4: job_templates does NOT exist (active_templates)
        ]
        fa_seq = [
            [],  # recent_runs fallback fetchall
            [],  # active_templates fetchall (unreachable since job_templates absent)
        ]

        cur.fetchone.side_effect = lambda: fo_seq.pop(0) if fo_seq else None
        cur.fetchall.side_effect = lambda: fa_seq.pop(0) if fa_seq else []

        with _patch_db(cur):
            result = handle_job_status(view="board")

        assert result["success"] is True
        qs = result["queue_summary"]
        assert qs["pending"] == 0
        assert qs["dead_letter"] == 0
        assert qs["paused_templates"] == 0
