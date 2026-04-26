"""Tests for scripts/moc_promise_check.py.

Covers:
  - extract_promises() pattern matching and noise filtering
  - is_fulfilled() trigram + ILIKE fallback paths
  - already_filed() dedupe predicate
  - run(--dry-run) end-to-end against the live DB (no inserts performed)

Live-DB tests require DATABASE_URI / DATABASE_URL to be reachable. They are
skipped (not failed) when the connection cannot be opened.
"""
import os
import sys

import pytest

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, SCRIPT_DIR)

import moc_promise_check as mpc


# ---------------------------------------------------------------------------
# Pure-function tests (no DB)
# ---------------------------------------------------------------------------


class TestExtractPromises:
    def test_see_article_colon(self):
        text = "For implementation details see article: Embedding System Internals."
        assert mpc.extract_promises(text) == ["Embedding System Internals"]

    def test_see_article_no_colon(self):
        text = "Refer to see article Hook Architecture for the wiring."
        assert mpc.extract_promises(text) == ["Hook Architecture"]

    def test_parenthesised_promise(self):
        text = "The cache is shared across instances (see the Embedding System article)."
        assert mpc.extract_promises(text) == ["Embedding System"]

    def test_see_the_X_article(self):
        text = "see the BPMN Engine article for runtime semantics"
        out = mpc.extract_promises(text)
        assert "BPMN Engine" in out

    def test_noise_words_filtered(self):
        text = "see article: This"
        assert mpc.extract_promises(text) == []

    def test_dedupes_identical_promises(self):
        text = "see article: Foo Bar. Then again, see article: foo bar."
        out = mpc.extract_promises(text)
        assert len(out) == 1

    def test_empty_input(self):
        assert mpc.extract_promises("") == []
        assert mpc.extract_promises(None) == []

    def test_short_promise_skipped(self):
        # < 3 char names are noise
        assert mpc.extract_promises("see article: Ab") == []


# ---------------------------------------------------------------------------
# DB-backed tests (skipped if DB unreachable)
# ---------------------------------------------------------------------------


def _live_conn():
    try:
        return mpc._connect()
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


class TestIsFulfilled:
    def test_known_article_matches_itself(self, conn):
        # "Claude Family" should fuzzy-match an existing system architecture article.
        assert mpc.is_fulfilled(conn, "Claude Family System Architecture") is True

    def test_nonsense_does_not_match(self, conn):
        assert mpc.is_fulfilled(conn, "ZZZ Definitely Not An Article QQQ") is False


class TestAlreadyFiled:
    def test_unknown_promise_not_filed(self, conn):
        assert mpc.already_filed(conn, "ZZZ Sentinel Promise QQQ {}".format(os.getpid())) is False


class TestRunDryRun:
    def test_dry_run_does_not_insert(self, conn):
        # Snapshot feedback count
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS n FROM claude.feedback "
            "WHERE title ILIKE 'MOC promise unfulfilled:%'"
        )
        before = cur.fetchone()["n"]
        cur.close()

        summary = mpc.run(dry_run=True, verbose=False)
        assert "checked" in summary
        assert "unfulfilled" in summary
        assert "feedback_filed" in summary
        assert summary["feedback_filed"] == 0
        assert summary["dry_run"] is True

        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS n FROM claude.feedback "
            "WHERE title ILIKE 'MOC promise unfulfilled:%'"
        )
        after = cur.fetchone()["n"]
        cur.close()
        assert before == after, "dry-run must not insert feedback"

    def test_idempotent_dry_run(self, conn):
        # Running twice yields the same numbers.
        s1 = mpc.run(dry_run=True, verbose=False)
        s2 = mpc.run(dry_run=True, verbose=False)
        assert s1["checked"] == s2["checked"]
        assert s1["unfulfilled"] == s2["unfulfilled"]
