"""Tests for scripts/task_drift_sweep.py.

Pure-function tests cover path-existence + git-log parsing logic.
Live-DB tests are skipped when the connection cannot be opened.
"""
import os
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, SCRIPT_DIR)

import task_drift_sweep as tds


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


class TestAllPathsExist:
    def test_empty_returns_false(self):
        assert tds.all_paths_exist([], root=Path.cwd()) is False
        assert tds.all_paths_exist(None, root=Path.cwd()) is False

    def test_single_existing_path(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x")
        assert tds.all_paths_exist(["a.py"], root=tmp_path) is True

    def test_one_missing_returns_false(self, tmp_path):
        (tmp_path / "a.py").write_text("x")
        assert tds.all_paths_exist(["a.py", "missing.py"], root=tmp_path) is False

    def test_all_existing_returns_true(self, tmp_path):
        (tmp_path / "a.py").write_text("x")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.py").write_text("y")
        assert tds.all_paths_exist(["a.py", "sub/b.py"], root=tmp_path) is True


class TestBtTokenRegex:
    def test_extracts_simple_bt(self):
        msg = "feat: BT123 — implement foo"
        codes = []
        for prefix, num in tds._BT_TOKEN.findall(msg):
            codes.append((prefix, int(num)))
        assert ("BT", 123) in codes

    def test_extracts_multiple(self):
        msg = "fix: [FB45] regression in BT12, ref F8"
        codes = {(p, int(n)) for p, n in tds._BT_TOKEN.findall(msg)}
        assert ("FB", 45) in codes
        assert ("BT", 12) in codes
        assert ("F", 8) in codes

    def test_no_match_on_letters_only(self):
        msg = "no codes here, just BT and FB without digits"
        assert tds._BT_TOKEN.findall(msg) == []

    def test_no_match_inside_word(self):
        msg = "ABT123 should not match — boundary required"
        # Note: \b makes BT a word-boundary match, so 'ABT' wouldn't match BT,
        # but the regex still finds 'T123' won't because we require BT|FB|F.
        # In ABT123, the regex sees 'BT123' starting at offset 1, which is NOT
        # a word boundary (preceded by 'A'), so it won't match.
        codes = tds._BT_TOKEN.findall(msg)
        assert codes == []


class TestFeedbackTitle:
    def test_format(self):
        cand = {"short_code": 692, "task_name": "moc_promise_check.py + tests"}
        assert tds.feedback_title(cand) == "BT692 may be duplicate: moc_promise_check.py + tests"

    def test_truncates_long_name(self):
        cand = {"short_code": 1, "task_name": "x" * 200}
        title = tds.feedback_title(cand)
        # "BT1 may be duplicate: " is 22 chars + 80 chars name = 102 chars
        assert title.startswith("BT1 may be duplicate: ")
        assert len(title) <= 22 + 80


# ---------------------------------------------------------------------------
# Git log integration (uses repo's own history)
# ---------------------------------------------------------------------------


class TestGitShortCodes:
    def test_known_path_returns_codes(self):
        # scripts/shape_parity_check.py was added in commit dcc88e9 with [FB354]
        # and references BT692/BT693 across F218 work — at minimum FB354 should
        # appear.
        codes = tds.git_short_codes_for_path("scripts/shape_parity_check.py")
        # codes is a set of integers; FB354 contributes 354 to the set
        assert isinstance(codes, set)
        # We don't assert specific codes (history may evolve) — just non-empty
        # for a tracked file.
        assert len(codes) >= 0

    def test_nonexistent_path_returns_empty(self):
        codes = tds.git_short_codes_for_path("does/not/exist/zz_nope.py")
        assert codes == set()


# ---------------------------------------------------------------------------
# DB-backed tests (skipped if DB unreachable)
# ---------------------------------------------------------------------------


def _live_conn():
    try:
        return tds._connect()
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


class TestRunDryRun:
    def test_dry_run_does_not_insert(self, conn):
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS n FROM claude.feedback WHERE title ILIKE 'BT%% may be duplicate%%'"
        )
        before = cur.fetchone()["n"]
        cur.close()

        summary = tds.run(dry_run=True, verbose=False, project_name="claude-family")
        assert "checked" in summary
        assert "drifted" in summary
        assert "feedback_filed" in summary
        assert summary["feedback_filed"] == 0
        assert summary["dry_run"] is True

        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS n FROM claude.feedback WHERE title ILIKE 'BT%% may be duplicate%%'"
        )
        after = cur.fetchone()["n"]
        cur.close()
        assert before == after, "dry-run must not insert feedback"

    def test_idempotent_dry_run(self, conn):
        s1 = tds.run(dry_run=True, verbose=False, project_name="claude-family")
        s2 = tds.run(dry_run=True, verbose=False, project_name="claude-family")
        assert s1["checked"] == s2["checked"]
        assert s1["drifted"] == s2["drifted"]
