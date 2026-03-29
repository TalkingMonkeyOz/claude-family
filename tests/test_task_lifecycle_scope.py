"""
Integration tests for F182 — Task Lifecycle Scope Classification.

Tests:
  1. parse_scope_prefix (unit) — [S]/[P] prefix parsing from todo_sync_hook.py
  2. DB scope column — CHECK constraint, column_registry entry
  3. Session cleanup SQL — close_session_scoped_todos only affects session-scoped rows

Requires:
  - PostgreSQL connection (claude schema)
  - scripts/todo_sync_hook.py importable
"""

import sys
import os
import uuid
import pytest

# Make scripts/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from todo_sync_hook import parse_scope_prefix

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_ID = "20b5627c-e72c-4501-8537-95b559731b59"


@pytest.fixture(scope="module")
def db_conn():
    """Provide a shared DB connection for the module, rolled back at end."""
    from config import get_db_connection
    conn = get_db_connection()
    if conn is None:
        pytest.skip("No database connection available")
    yield conn
    try:
        conn.rollback()
    except Exception:
        pass
    conn.close()


@pytest.fixture()
def db_cursor(db_conn):
    """Provide a cursor wrapped in a SAVEPOINT so each test rolls back cleanly."""
    cur = db_conn.cursor()
    cur.execute("SAVEPOINT test_sp")
    yield cur
    # Rollback to savepoint — works even if the transaction is in error state
    try:
        cur.execute("ROLLBACK TO SAVEPOINT test_sp")
    except Exception:
        db_conn.rollback()


# ---------------------------------------------------------------------------
# 1. parse_scope_prefix — unit tests
# ---------------------------------------------------------------------------


class TestParseScopePrefix:
    """Unit tests for parse_scope_prefix in todo_sync_hook.py."""

    def test_session_prefix_uppercase(self):
        scope, content = parse_scope_prefix("[S] Task name")
        assert scope == "session"
        assert content == "Task name"

    def test_persistent_prefix_uppercase(self):
        scope, content = parse_scope_prefix("[P] Task name")
        assert scope == "persistent"
        assert content == "Task name"

    def test_session_prefix_lowercase(self):
        scope, content = parse_scope_prefix("[s] lowercase")
        assert scope == "session"
        assert content == "lowercase"

    def test_persistent_prefix_lowercase(self):
        scope, content = parse_scope_prefix("[p] lowercase")
        assert scope == "persistent"
        assert content == "lowercase"

    def test_no_prefix_defaults_to_session(self):
        scope, content = parse_scope_prefix("No prefix")
        assert scope == "session"
        assert content == "No prefix"

    def test_no_space_after_prefix(self):
        scope, content = parse_scope_prefix("[S]No space")
        assert scope == "session"
        assert content == "No space"

    def test_unrecognised_prefix_treated_as_no_prefix(self):
        scope, content = parse_scope_prefix("[Special] Not a scope")
        assert scope == "session"
        assert content == "[Special] Not a scope"

    def test_empty_content_after_strip_returns_original(self):
        scope, content = parse_scope_prefix("[S] ")
        assert scope == "session"
        assert content == "[S] "


# ---------------------------------------------------------------------------
# 2. DB scope column — constraint and registry tests
# ---------------------------------------------------------------------------


class TestDbScopeColumn:
    """Integration tests for task_scope column on claude.todos."""

    def _insert_todo(self, cur, task_scope, suffix=""):
        """Helper: INSERT a todo with given task_scope, return todo_id or raise."""
        todo_id = str(uuid.uuid4())
        content = f"test-scope-{task_scope}{suffix}"
        cur.execute(
            """
            INSERT INTO claude.todos
                (todo_id, project_id, content, active_form, status, priority, task_scope)
            VALUES
                (%s::uuid, %s::uuid, %s, %s, 'pending', 3, %s)
            RETURNING todo_id::text
            """,
            (todo_id, PROJECT_ID, content, content, task_scope),
        )
        return cur.fetchone()["todo_id"]

    def test_insert_session_scope_succeeds(self, db_cursor):
        tid = self._insert_todo(db_cursor, "session")
        assert tid is not None

    def test_insert_persistent_scope_succeeds(self, db_cursor):
        tid = self._insert_todo(db_cursor, "persistent")
        assert tid is not None

    def test_insert_invalid_scope_fails(self, db_cursor):
        with pytest.raises(Exception) as exc_info:
            self._insert_todo(db_cursor, "invalid")
        # Should be a CHECK constraint violation
        assert "chk_todos_task_scope" in str(exc_info.value).lower() or "check" in str(
            exc_info.value
        ).lower()

    def test_column_registry_entry_exists(self, db_cursor):
        db_cursor.execute(
            """
            SELECT valid_values
            FROM claude.column_registry
            WHERE table_name = 'todos' AND column_name = 'task_scope'
            """
        )
        row = db_cursor.fetchone()
        assert row is not None, "column_registry entry for todos.task_scope is missing"
        valid = row["valid_values"]
        assert "session" in valid
        assert "persistent" in valid

    def test_default_value_is_session(self, db_cursor):
        """Inserting without explicit task_scope should default to 'session'."""
        todo_id = str(uuid.uuid4())
        db_cursor.execute(
            """
            INSERT INTO claude.todos
                (todo_id, project_id, content, active_form, status, priority)
            VALUES
                (%s::uuid, %s::uuid, 'test-default-scope', 'test-default-scope', 'pending', 3)
            RETURNING task_scope
            """,
            (todo_id, PROJECT_ID),
        )
        row = db_cursor.fetchone()
        assert row["task_scope"] == "session"


# ---------------------------------------------------------------------------
# 3. Session cleanup logic — close_session_scoped_todos SQL behaviour
# ---------------------------------------------------------------------------


class TestSessionCleanupLogic:
    """Verify the cleanup SQL only cancels session-scoped pending/in_progress todos."""

    def _seed_todos(self, cur):
        """Insert test todos with different scopes and statuses. Returns dict of ids."""
        ids = {}
        cases = [
            ("sess-pending", "session", "pending"),
            ("sess-inprog", "session", "in_progress"),
            ("sess-completed", "session", "completed"),
            ("pers-pending", "persistent", "pending"),
            ("pers-inprog", "persistent", "in_progress"),
        ]
        for label, scope, status in cases:
            tid = str(uuid.uuid4())
            content = f"cleanup-test-{label}"
            cur.execute(
                """
                INSERT INTO claude.todos
                    (todo_id, project_id, content, active_form, status, priority, task_scope)
                VALUES
                    (%s::uuid, %s::uuid, %s, %s, %s, 3, %s)
                """,
                (tid, PROJECT_ID, content, content, status, scope),
            )
            ids[label] = tid
        return ids

    def _run_cleanup_sql(self, cur, project_name="claude-family"):
        """Run the same SQL as close_session_scoped_todos."""
        cur.execute(
            """
            UPDATE claude.todos t
            SET status = 'cancelled', completed_at = NOW(), updated_at = NOW()
            FROM claude.projects p
            WHERE t.project_id = p.project_id
              AND p.project_name = %s
              AND t.task_scope = 'session'
              AND t.status IN ('pending', 'in_progress')
              AND NOT t.is_deleted
            RETURNING t.todo_id::text
            """,
            (project_name,),
        )
        return {r["todo_id"] for r in cur.fetchall()}

    def _get_status(self, cur, todo_id):
        cur.execute(
            "SELECT status FROM claude.todos WHERE todo_id = %s::uuid", (todo_id,)
        )
        row = cur.fetchone()
        return row["status"] if row else None

    def test_session_pending_cancelled(self, db_cursor):
        ids = self._seed_todos(db_cursor)
        cancelled = self._run_cleanup_sql(db_cursor)
        assert ids["sess-pending"] in cancelled

    def test_session_in_progress_cancelled(self, db_cursor):
        ids = self._seed_todos(db_cursor)
        cancelled = self._run_cleanup_sql(db_cursor)
        assert ids["sess-inprog"] in cancelled

    def test_session_completed_untouched(self, db_cursor):
        ids = self._seed_todos(db_cursor)
        self._run_cleanup_sql(db_cursor)
        assert self._get_status(db_cursor, ids["sess-completed"]) == "completed"

    def test_persistent_pending_untouched(self, db_cursor):
        ids = self._seed_todos(db_cursor)
        self._run_cleanup_sql(db_cursor)
        assert self._get_status(db_cursor, ids["pers-pending"]) == "pending"

    def test_persistent_in_progress_untouched(self, db_cursor):
        ids = self._seed_todos(db_cursor)
        self._run_cleanup_sql(db_cursor)
        assert self._get_status(db_cursor, ids["pers-inprog"]) == "in_progress"

    def test_only_session_active_rows_cancelled(self, db_cursor):
        """Of the 5 seeded rows, only the 2 session-scoped active ones are cancelled."""
        ids = self._seed_todos(db_cursor)
        cancelled = self._run_cleanup_sql(db_cursor)
        # Our seeded session-scoped active todos must both be in the cancelled set
        assert ids["sess-pending"] in cancelled
        assert ids["sess-inprog"] in cancelled
        # And the other 3 seeded rows must NOT be in the cancelled set
        assert ids["sess-completed"] not in cancelled
        assert ids["pers-pending"] not in cancelled
        assert ids["pers-inprog"] not in cancelled
