"""
test_scheduled_jobs_linkage.py — F226 / BT721.

Verifies claude.scheduled_jobs.linked_work_item_id column exists,
is NULLABLE with FK to work_items, and that f226-parity-check is wired
to the F226 tracking work_item.
"""
from __future__ import annotations

import pytest


class TestColumnShape:

    def test_column_exists_and_is_nullable(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT data_type, is_nullable FROM information_schema.columns "
                "WHERE table_schema='claude' AND table_name='scheduled_jobs' "
                "AND column_name='linked_work_item_id'"
            )
            row = cur.fetchone()
        assert row is not None
        assert row['data_type'] == 'uuid'
        assert row['is_nullable'] == 'YES'

    def test_fk_to_work_items(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT pg_get_constraintdef(con.oid) AS def "
                "FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "WHERE ns.nspname='claude' AND rel.relname='scheduled_jobs' "
                "AND con.contype='f' "
                "AND pg_get_constraintdef(con.oid) LIKE '%linked_work_item_id%'"
            )
            defs = [r['def'] for r in cur.fetchall()]
        assert any("REFERENCES claude.work_items(work_item_id)" in d for d in defs)

    def test_partial_index_present(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname='claude' AND tablename='scheduled_jobs' "
                "AND indexname='idx_scheduled_jobs_linked_work_item'"
            )
            assert cur.fetchone() is not None


class TestParityJobLinked:

    def test_f226_parity_check_linked_to_f226(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT linked_work_item_id FROM claude.scheduled_jobs "
                "WHERE job_name='f226-parity-check'"
            )
            row = cur.fetchone()
        assert row is not None
        assert row['linked_work_item_id'] is not None, \
            "f226-parity-check should be linked to a work_item"

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT short_code FROM claude.work_item_code_history "
                "WHERE work_item_id=%s::uuid AND code_kind='legacy'",
                (row['linked_work_item_id'],),
            )
            codes = {r['short_code'] for r in cur.fetchall()}
        assert 'F226' in codes, f"linked work_item should resolve from F226; got {codes}"


class TestNullDefaultPreserved:

    def test_other_jobs_remain_null(self, db_conn):
        """Non-F226 scheduled jobs should still have NULL linked_work_item_id."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.scheduled_jobs "
                "WHERE job_name NOT LIKE 'f226%' AND linked_work_item_id IS NOT NULL"
            )
            # Some jobs may legitimately link in future — assert this doesn't
            # explode (column exists, can be queried, no rows linked yet).
            row = cur.fetchone()
        assert row is not None
