"""
test_schema_work_items.py — F226 / BT713 schema validation.

Verifies the unified `claude.work_items` table has the expected shape
after the migration `scripts/migrations/2026-05-02-f226-bt713-work-items-table.sql`
has been applied. Designed to be run against the live development DB
(via the conftest `db_conn` rollback fixture); these are read-only
introspection queries plus one inside-rollback INSERT smoke test that
exercises the CHECK constraints and IDENTITY sequence.

Tests cover the BT713 verification criteria:
  - psql shows table exists
  - column_registry has rows for new constrained cols (kind/stage/priority/task_scope)
  - migration is idempotent (re-application is no-op)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts" / "migrations" / "2026-05-02-f226-bt713-work-items-table.sql"
)


# ---------------------------------------------------------------------------
# Table existence + column shape
# ---------------------------------------------------------------------------

class TestWorkItemsTableExists:
    """Table is in claude schema with the expected column set."""

    def test_table_exists(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='claude' AND table_name='work_items')"
            )
            assert cur.fetchone()["exists"] is True

    def test_required_columns_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='claude' AND table_name='work_items'"
            )
            cols = {row["column_name"] for row in cur.fetchall()}

        expected = {
            "work_item_id", "short_code",
            "title", "description", "kind", "stage", "priority",
            "project_id", "owner_identity_id", "task_scope",
            "parent_id", "source_id", "blocked_by_id",
            "created_session_id", "completed_session_id",
            "created_at", "updated_at", "started_at", "completed_at",
            "verification", "files_affected", "plan_data",
            "due_at", "estimated_hours", "actual_hours", "completion_percentage",
            "attributes", "is_deleted", "deleted_at",
        }
        missing = expected - cols
        assert not missing, f"work_items missing columns: {missing}"

    def test_short_code_is_identity(self, db_conn):
        """short_code must be a GENERATED IDENTITY column (auto W-sequence)."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT is_identity, identity_generation "
                "FROM information_schema.columns "
                "WHERE table_schema='claude' AND table_name='work_items' "
                "AND column_name='short_code'"
            )
            row = cur.fetchone()
            assert row is not None
            assert row["is_identity"] == "YES"
            assert row["identity_generation"] in ("BY DEFAULT", "ALWAYS")


# ---------------------------------------------------------------------------
# CHECK constraints & FKs
# ---------------------------------------------------------------------------

class TestWorkItemsConstraints:
    """All five CHECK constraints + the three self-FKs are present."""

    def test_check_constraints_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT con.conname "
                "FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "WHERE ns.nspname='claude' AND rel.relname='work_items' "
                "AND con.contype='c'"
            )
            names = {row["conname"] for row in cur.fetchall()}
        for required in (
            "chk_kind", "chk_stage", "chk_priority",
            "chk_task_scope", "chk_completion_percentage",
        ):
            assert required in names, f"missing CHECK constraint {required}"

    def test_foreign_keys_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT con.conname, pg_get_constraintdef(con.oid) AS def "
                "FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "WHERE ns.nspname='claude' AND rel.relname='work_items' "
                "AND con.contype='f'"
            )
            fks = [(row["conname"], row["def"]) for row in cur.fetchall()]
        defs = " ".join(d for _, d in fks)
        assert "claude.projects(project_id)" in defs
        assert "claude.identities(identity_id)" in defs
        # Three self-references: parent_id, source_id, blocked_by_id
        self_fk_count = sum(1 for _, d in fks if "claude.work_items(work_item_id)" in d)
        assert self_fk_count == 3, f"expected 3 self-FKs, got {self_fk_count}"


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

class TestWorkItemsIndexes:
    """Required indexes from the migration are all present."""

    def test_required_indexes_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname='claude' AND tablename='work_items'"
            )
            names = {row["indexname"] for row in cur.fetchall()}
        for required in (
            "idx_wi_project_stage",
            "idx_wi_kind",
            "idx_wi_parent",
            "idx_wi_source",
            "idx_wi_blocked_by",
            "idx_wi_due_at",
            "idx_wi_attributes_gin",
            "idx_wi_short_code",
        ):
            assert required in names, f"missing index {required}"


# ---------------------------------------------------------------------------
# column_registry rows
# ---------------------------------------------------------------------------

class TestColumnRegistryRows:
    """The constrained columns have column_registry entries with valid_values."""

    @pytest.mark.parametrize("column_name,expected_values", [
        ("kind", {
            "bug", "idea", "improvement", "design", "change", "question",
            "feature", "refactor", "infrastructure", "documentation", "stream",
            "task", "reminder",
        }),
        ("stage", {
            "raw", "triaged", "planned", "in_progress", "blocked",
            "done", "dropped", "parked",
        }),
        ("priority", {1, 2, 3, 4, 5}),
        ("task_scope", {"session", "persistent"}),
    ])
    def test_registry_row_present(self, db_conn, column_name, expected_values):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT valid_values FROM claude.column_registry "
                "WHERE table_name='work_items' AND column_name=%s",
                (column_name,),
            )
            row = cur.fetchone()
        assert row is not None, f"column_registry missing work_items.{column_name}"
        valid = row["valid_values"]
        # JSONB returns as list/dict already
        assert set(valid) == expected_values


# ---------------------------------------------------------------------------
# CHECK enforcement smoke (rolled back by db_conn fixture)
# ---------------------------------------------------------------------------

class TestCheckConstraintEnforcement:
    """Verify constraints actually reject bad values."""

    def _project_id(self, cur):
        cur.execute(
            "SELECT project_id FROM claude.projects WHERE project_name='claude-family'"
        )
        row = cur.fetchone()
        assert row is not None, "claude-family project must exist for this test"
        return row["project_id"]

    def test_invalid_kind_rejected(self, db_conn):
        import psycopg
        with db_conn.cursor() as cur:
            pid = self._project_id(cur)
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO claude.work_items "
                    "(title, kind, stage, priority, project_id) "
                    "VALUES ('test', 'not_a_kind', 'raw', 3, %s)",
                    (pid,),
                )
        db_conn.rollback()

    def test_invalid_stage_rejected(self, db_conn):
        import psycopg
        with db_conn.cursor() as cur:
            pid = self._project_id(cur)
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO claude.work_items "
                    "(title, kind, stage, priority, project_id) "
                    "VALUES ('test', 'bug', 'completed', 3, %s)",
                    (pid,),
                )
        db_conn.rollback()

    def test_priority_out_of_range_rejected(self, db_conn):
        import psycopg
        with db_conn.cursor() as cur:
            pid = self._project_id(cur)
            with pytest.raises(psycopg.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO claude.work_items "
                    "(title, kind, stage, priority, project_id) "
                    "VALUES ('test', 'bug', 'raw', 6, %s)",
                    (pid,),
                )
        db_conn.rollback()

    def test_valid_insert_succeeds_and_short_code_assigned(self, db_conn):
        with db_conn.cursor() as cur:
            pid = self._project_id(cur)
            cur.execute(
                "INSERT INTO claude.work_items "
                "(title, kind, stage, priority, project_id) "
                "VALUES ('bt713-smoke', 'task', 'planned', 3, %s) "
                "RETURNING work_item_id, short_code, created_at, updated_at, attributes",
                (pid,),
            )
            row = cur.fetchone()
        assert row["work_item_id"] is not None
        assert isinstance(row["short_code"], int) and row["short_code"] > 0
        assert row["created_at"] is not None
        assert row["updated_at"] is not None
        assert row["attributes"] == {}


# ---------------------------------------------------------------------------
# Idempotency — re-running the SQL must not error or duplicate registry rows
# ---------------------------------------------------------------------------

class TestMigrationIdempotency:
    """Re-applying the migration produces no diffs."""

    def test_sql_file_exists(self):
        assert MIGRATION_PATH.exists(), f"migration file not found: {MIGRATION_PATH}"

    def test_reapplying_migration_is_noop(self, db_conn):
        """Run the entire migration SQL again — should not raise, no dup registry rows."""
        sql = MIGRATION_PATH.read_text(encoding="utf-8")

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.column_registry WHERE table_name='work_items'"
            )
            before = cur.fetchone()["c"]

            cur.execute(sql)

            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.column_registry WHERE table_name='work_items'"
            )
            after = cur.fetchone()["c"]
        assert before == after == 4
        db_conn.rollback()
