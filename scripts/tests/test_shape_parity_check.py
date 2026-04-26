"""Tests for scripts/shape_parity_check.py.

Covers:
  - find_drifts() pure logic with crafted column sets
  - INTRINSIC_PER_STORE filtering
  - run(--dry-run) end-to-end against the live DB (no inserts performed)

Live-DB tests require DATABASE_URI / DATABASE_URL to be reachable. They are
skipped (not failed) when the connection cannot be opened.
"""
import os
import sys

import pytest

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, SCRIPT_DIR)

import shape_parity_check as spc


# ---------------------------------------------------------------------------
# Pure-function tests (no DB)
# ---------------------------------------------------------------------------


class TestFindDrifts:
    def test_no_drift_when_all_match(self):
        cols = {
            "knowledge": {"summary", "embedding"},
            "entities": {"summary", "embedding"},
            "article_sections": {"summary", "embedding"},
        }
        assert spc.find_drifts(cols) == []

    def test_drift_two_of_three(self):
        cols = {
            "knowledge": {"new_col"},
            "entities": {"new_col"},
            "article_sections": set(),
        }
        drifts = spc.find_drifts(cols)
        assert len(drifts) == 1
        assert drifts[0]["column"] == "new_col"
        assert drifts[0]["missing_on"] == "article_sections"
        assert set(drifts[0]["present_on"]) == {"knowledge", "entities"}

    def test_drift_only_one_store_no_flag(self):
        # Column on exactly 1 store is NOT a drift (per spec — only 2/3 flagged)
        cols = {
            "knowledge": {"only_here"},
            "entities": set(),
            "article_sections": set(),
        }
        assert spc.find_drifts(cols) == []

    def test_intrinsic_columns_skipped(self):
        # 'title' is intrinsic-per-store (entities uses display_name)
        cols = {
            "knowledge": {"title"},
            "entities": set(),
            "article_sections": {"title"},
        }
        assert spc.find_drifts(cols) == []

    def test_multiple_drifts(self):
        cols = {
            "knowledge": {"alpha", "beta"},
            "entities": {"alpha"},
            "article_sections": {"beta"},
        }
        drifts = spc.find_drifts(cols)
        assert len(drifts) == 2
        cols_flagged = {d["column"]: d["missing_on"] for d in drifts}
        assert cols_flagged["alpha"] == "article_sections"
        assert cols_flagged["beta"] == "entities"

    def test_feedback_title_format(self):
        drift = {
            "column": "foo",
            "present_on": ["knowledge", "entities"],
            "missing_on": "article_sections",
        }
        title = spc._feedback_title(drift)
        assert title == "Shape drift: column foo on knowledge+entities, missing on article_sections"


# ---------------------------------------------------------------------------
# DB-backed tests (skipped if DB unreachable)
# ---------------------------------------------------------------------------


def _live_conn():
    try:
        return spc._connect()
    except Exception as e:
        pytest.skip("DB unreachable: {}".format(e))


@pytest.fixture(scope="module")
def conn():
    c = _live_conn()
    yield c
    try:
        c.close()
    except Exception:
        pass


class TestGatherColumns:
    def test_three_stores_present(self, conn):
        cols = spc.gather_columns(conn)
        assert set(cols.keys()) == set(spc.STORES)
        for table, col_set in cols.items():
            assert isinstance(col_set, set)
            assert len(col_set) > 0, "store {} returned no columns".format(table)


class TestRunDryRun:
    def test_dry_run_does_not_insert(self, conn):
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS n FROM claude.feedback WHERE title ILIKE 'Shape drift:%'"
        )
        before = cur.fetchone()["n"]
        cur.close()

        summary = spc.run(dry_run=True, verbose=False)
        assert "checked_columns" in summary
        assert "drifts" in summary
        assert "feedback_filed" in summary
        assert summary["feedback_filed"] == 0
        assert summary["dry_run"] is True

        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS n FROM claude.feedback WHERE title ILIKE 'Shape drift:%'"
        )
        after = cur.fetchone()["n"]
        cur.close()
        assert before == after, "dry-run must not insert feedback"

    def test_dedupe_idempotent(self, conn):
        # Two consecutive dry-runs see the same drift count.
        s1 = spc.run(dry_run=True, verbose=False)
        s2 = spc.run(dry_run=True, verbose=False)
        assert s1["checked_columns"] == s2["checked_columns"]
        assert s1["drifts"] == s2["drifts"]
