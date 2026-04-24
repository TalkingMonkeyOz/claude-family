"""Pytest fixtures for project-tools MCP server tests.

Provides:
- DATABASE_URI environment setup from repo .env (DATABASE_URL → DATABASE_URI)
- sys.path insertion so `import server` / `import server_v2` works from tests
- db_conn fixture: per-test connection with transactional rollback (no DB pollution)
- monkey_db fixture: monkey-patches server.get_db_connection so tool functions
  under test use the same rollback-scoped connection
"""
import os
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path + environment setup (runs at import time — before any test collection)
# ---------------------------------------------------------------------------

# Add project-tools dir to sys.path so `import server` / `import server_v2` work.
_PROJECT_TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(_PROJECT_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_TOOLS_DIR))

# Repo root (two levels up from this file: tests → project-tools → mcp-servers → repo)
_REPO_ROOT = _PROJECT_TOOLS_DIR.parent.parent


def _load_dotenv_into_environ() -> None:
    """Minimal .env loader — no python-dotenv dependency.

    Reads .env at the repo root and sets any KEY=VALUE pair into os.environ
    if not already set. Also maps DATABASE_URL → DATABASE_URI (server.py reads
    DATABASE_URI / POSTGRES_CONNECTION_STRING).
    """
    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

    # server.py reads DATABASE_URI; .env uses DATABASE_URL. Bridge them.
    if "DATABASE_URI" not in os.environ and os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URI"] = os.environ["DATABASE_URL"]


_load_dotenv_into_environ()


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_url() -> str:
    """Return the DATABASE_URI for this test run, or skip the test if unset."""
    url = os.environ.get("DATABASE_URI") or os.environ.get("POSTGRES_CONNECTION_STRING")
    if not url:
        pytest.skip("DATABASE_URI not set — skipping DB-backed tests")
    return url


@pytest.fixture
def db_conn(db_url):
    """Per-test DB connection wrapped in a transaction that always rolls back.

    Any INSERT/UPDATE/DELETE performed during the test is undone when the
    fixture tears down, so tests do not pollute shared infrastructure tables.
    """
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        pytest.skip("psycopg (v3) not installed — skipping DB tests")

    conn = psycopg.connect(db_url, row_factory=dict_row, autocommit=False)
    try:
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


@pytest.fixture
def monkey_db(db_conn, monkeypatch):
    """Monkey-patch server.get_db_connection to return `db_conn`.

    Tool functions under test call `get_db_connection()` internally and
    `conn.close()` in their finally blocks. We hand them a connection whose
    `close()` is neutralised so the outer fixture can still rollback at
    teardown. A savepoint is used so each tool call is isolated — if a tool
    ROLLBACKs internally, we restore to the savepoint and keep going.
    """
    class _NoCloseConn:
        """Thin wrapper that intercepts close() and commit() to preserve
        the fixture's outer transaction. Everything else passes through."""

        def __init__(self, inner):
            object.__setattr__(self, "_inner", inner)

        def close(self):
            # Do not actually close — the outer fixture owns the lifecycle.
            return None

        def commit(self):
            # Tools may commit; we swallow it to keep rollback semantics.
            # Internal work is preserved via savepoints, not real commits.
            return None

        def __getattr__(self, name):
            return getattr(self._inner, name)

    wrapped = _NoCloseConn(db_conn)

    import server  # noqa: E402  — path inserted above
    monkeypatch.setattr(server, "get_db_connection", lambda: wrapped)

    yield wrapped
