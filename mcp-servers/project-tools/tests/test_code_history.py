"""
test_code_history.py — F226 / BT714 sidecar table validation.

Verifies claude.work_item_code_history + claude.work_item_resolve_legacy()
after the migration scripts/migrations/2026-05-02-f226-bt714-code-history-sidecar.sql
has been applied.

Tests cover the BT714 verification criteria:
  - work_item_resolve_legacy('FB316') returns the work_item_id
  - UNIQUE(short_code) prevents collision
  - pytest covers happy path + collision + multi-history
"""
from __future__ import annotations

from pathlib import Path

import pytest


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts" / "migrations" / "2026-05-02-f226-bt714-code-history-sidecar.sql"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_id(cur) -> str:
    cur.execute(
        "SELECT project_id FROM claude.projects WHERE project_name='claude-family'"
    )
    row = cur.fetchone()
    assert row is not None
    return row["project_id"]


def _create_work_item(cur, project_id, *, kind="task", stage="planned",
                      title="bt714-fixture") -> str:
    cur.execute(
        "INSERT INTO claude.work_items "
        "(title, kind, stage, priority, project_id) "
        "VALUES (%s, %s, %s, 3, %s) "
        "RETURNING work_item_id",
        (title, kind, stage, project_id),
    )
    return cur.fetchone()["work_item_id"]


# ---------------------------------------------------------------------------
# Schema shape
# ---------------------------------------------------------------------------

class TestSchemaShape:
    """Table + columns + constraints + indexes + function."""

    def test_table_exists(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='claude' AND table_name='work_item_code_history')"
            )
            assert cur.fetchone()["exists"] is True

    def test_required_columns_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='claude' AND table_name='work_item_code_history'"
            )
            cols = {row["column_name"] for row in cur.fetchall()}
        expected = {"history_id", "work_item_id", "short_code",
                    "code_kind", "valid_from", "valid_to", "notes"}
        assert expected <= cols, f"missing columns: {expected - cols}"

    def test_unique_short_code_constraint(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT con.conname, pg_get_constraintdef(con.oid) AS def "
                "FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "WHERE ns.nspname='claude' AND rel.relname='work_item_code_history' "
                "AND con.contype='u'"
            )
            uniques = [(r["conname"], r["def"]) for r in cur.fetchall()]
        assert any("(short_code)" in d for _, d in uniques), (
            f"expected UNIQUE on short_code; got {uniques}"
        )

    def test_check_constraints_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT con.conname FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "WHERE ns.nspname='claude' AND rel.relname='work_item_code_history' "
                "AND con.contype='c'"
            )
            names = {r["conname"] for r in cur.fetchall()}
        assert {"chk_wich_code_kind", "chk_wich_validity_window"} <= names

    def test_cascade_fk_on_work_item_id(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT pg_get_constraintdef(con.oid) AS def "
                "FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "WHERE ns.nspname='claude' AND rel.relname='work_item_code_history' "
                "AND con.contype='f'"
            )
            defs = [r["def"] for r in cur.fetchall()]
        assert any("ON DELETE CASCADE" in d and "claude.work_items(work_item_id)" in d
                   for d in defs)

    def test_required_indexes_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname='claude' AND tablename='work_item_code_history'"
            )
            names = {r["indexname"] for r in cur.fetchall()}
        for required in ("idx_wich_work_item", "idx_wich_code_kind", "idx_wich_active"):
            assert required in names, f"missing index {required}"

    def test_resolver_function_exists(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS("
                "  SELECT 1 FROM pg_proc p "
                "  JOIN pg_namespace n ON n.oid=p.pronamespace "
                "  WHERE n.nspname='claude' AND p.proname='work_item_resolve_legacy'"
                ")"
            )
            assert cur.fetchone()["exists"] is True


# ---------------------------------------------------------------------------
# column_registry row
# ---------------------------------------------------------------------------

class TestColumnRegistryRow:

    def test_code_kind_registered(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT valid_values FROM claude.column_registry "
                "WHERE table_name='work_item_code_history' AND column_name='code_kind'"
            )
            row = cur.fetchone()
        assert row is not None
        assert set(row["valid_values"]) == {"canonical", "legacy", "historical_promotion"}


# ---------------------------------------------------------------------------
# Resolver function — happy path, collision, multi-history, NULL
# ---------------------------------------------------------------------------

class TestResolverHappyPath:
    """Verification criterion: work_item_resolve_legacy('FB###') returns the work_item_id."""

    def test_resolve_legacy_returns_work_item_id(self, db_conn):
        # Use a fixture-only legacy code to avoid colliding with the F226 backfill
        # which now owns real FB### / F### / BT### / TODO-### codes.
        FIXTURE_CODE = "FB-FIXTURE-LEGACY-RESOLVE-TEST"
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid = _create_work_item(cur, pid, kind="bug", stage="triaged",
                                    title="legacy-resolve-test")
            cur.execute(
                "INSERT INTO claude.work_item_code_history "
                "(work_item_id, short_code, code_kind) VALUES (%s, %s, 'legacy')",
                (wid, FIXTURE_CODE),
            )
            cur.execute(
                "SELECT claude.work_item_resolve_legacy(%s) AS resolved",
                (FIXTURE_CODE,),
            )
            assert cur.fetchone()["resolved"] == wid
        db_conn.rollback()

    def test_resolve_canonical_w_code(self, db_conn):
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid = _create_work_item(cur, pid)
            cur.execute(
                "INSERT INTO claude.work_item_code_history "
                "(work_item_id, short_code, code_kind) VALUES (%s, %s, 'canonical')",
                (wid, "W9999"),
            )
            cur.execute(
                "SELECT claude.work_item_resolve_legacy('W9999') AS resolved"
            )
            assert cur.fetchone()["resolved"] == wid
        db_conn.rollback()

    def test_resolve_unknown_returns_null(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT claude.work_item_resolve_legacy('NEVER_EXISTED_999') AS resolved"
            )
            assert cur.fetchone()["resolved"] is None
        db_conn.rollback()

    def test_retired_code_does_not_resolve(self, db_conn):
        """Codes with valid_to set are not returned by the resolver."""
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid = _create_work_item(cur, pid)
            cur.execute(
                "INSERT INTO claude.work_item_code_history "
                "(work_item_id, short_code, code_kind, valid_to) "
                "VALUES (%s, %s, 'legacy', now())",
                (wid, "RETIRED1"),
            )
            cur.execute(
                "SELECT claude.work_item_resolve_legacy('RETIRED1') AS resolved"
            )
            assert cur.fetchone()["resolved"] is None
        db_conn.rollback()


class TestUniquenessGuard:
    """UNIQUE(short_code) prevents collision across the namespace."""

    def test_duplicate_short_code_rejected(self, db_conn):
        import psycopg
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            w1 = _create_work_item(cur, pid, title="collision-1")
            w2 = _create_work_item(cur, pid, title="collision-2")
            cur.execute(
                "INSERT INTO claude.work_item_code_history "
                "(work_item_id, short_code, code_kind) VALUES (%s, %s, 'canonical')",
                (w1, "DUP1"),
            )
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute(
                    "INSERT INTO claude.work_item_code_history "
                    "(work_item_id, short_code, code_kind) VALUES (%s, %s, 'canonical')",
                    (w2, "DUP1"),
                )
        db_conn.rollback()


class TestMultiHistory:
    """One work_item_id can carry multiple short_codes (canonical + legacy + promotion)."""

    def test_multiple_codes_resolve_to_same_work_item(self, db_conn):
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid = _create_work_item(cur, pid, kind="feature", stage="planned",
                                    title="multi-history-test")
            for code, kind in [
                ("W12345",       "canonical"),
                ("FB12345",      "legacy"),
                ("F12345",       "historical_promotion"),
            ]:
                cur.execute(
                    "INSERT INTO claude.work_item_code_history "
                    "(work_item_id, short_code, code_kind) VALUES (%s, %s, %s)",
                    (wid, code, kind),
                )
            for code in ("W12345", "FB12345", "F12345"):
                cur.execute(
                    "SELECT claude.work_item_resolve_legacy(%s) AS resolved", (code,)
                )
                assert cur.fetchone()["resolved"] == wid, f"{code} did not resolve"
        db_conn.rollback()


class TestInvalidCodeKindRejected:

    def test_bad_code_kind_rejected(self, db_conn):
        import psycopg
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid = _create_work_item(cur, pid)
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO claude.work_item_code_history "
                    "(work_item_id, short_code, code_kind) VALUES (%s, %s, 'bogus')",
                    (wid, "BADKIND1"),
                )
        db_conn.rollback()


class TestCascadeDelete:

    def test_deleting_work_item_cascades_to_history(self, db_conn):
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid = _create_work_item(cur, pid, title="cascade-test")
            cur.execute(
                "INSERT INTO claude.work_item_code_history "
                "(work_item_id, short_code, code_kind) VALUES (%s, %s, 'canonical')",
                (wid, "CASCADE1"),
            )
            cur.execute("DELETE FROM claude.work_items WHERE work_item_id=%s", (wid,))
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.work_item_code_history "
                "WHERE short_code='CASCADE1'"
            )
            assert cur.fetchone()["c"] == 0
        db_conn.rollback()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestMigrationIdempotency:

    def test_sql_file_exists(self):
        assert MIGRATION_PATH.exists()

    def test_reapplying_migration_is_noop(self, db_conn):
        sql = MIGRATION_PATH.read_text(encoding="utf-8")
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.column_registry "
                "WHERE table_name='work_item_code_history'"
            )
            before = cur.fetchone()["c"]

            cur.execute(sql)

            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.column_registry "
                "WHERE table_name='work_item_code_history'"
            )
            after = cur.fetchone()["c"]
        assert before == after == 1
        db_conn.rollback()
