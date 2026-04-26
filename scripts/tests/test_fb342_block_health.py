"""Tests for FB342 block health monitor.

Pure-function tests for probe parsing + threshold logic. End-to-end probe
test runs against the live hook (fail-open if DB unreachable).
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import fb342_block_health as bh


# ---------------------------------------------------------------------------
# probe_hook — output parsing
# ---------------------------------------------------------------------------


def _fake_run(stdout: str, returncode: int = 0):
    class R:
        pass
    r = R()
    r.stdout = stdout
    r.returncode = returncode
    return r


def test_probe_block_present():
    block = (
        "RECENT CHANGES (last 7 days — decisions/patterns/learnings/gotchas remembered):\n"
        "  [2026-04-26|decision|c65] FB342 shipped: blah blah\n"
        "  [2026-04-25|pattern|c75] Some pattern: text\n"
        "  Use recall_memories(\"...\") to load any of these in full."
    )
    full_ctx = "Some preamble\n\n" + block + "\n\nMore stuff after"
    fake_output = json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": full_ctx,
    }})
    with patch("fb342_block_health.subprocess.run",
               return_value=_fake_run(fake_output)):
        r = bh.probe_hook()
    assert r["block_present"] is True
    assert r["row_count"] == 2  # only the [...] lines
    assert r["block_chars"] > 0
    assert r["block_tokens_est"] == r["block_chars"] // 4


def test_probe_block_absent():
    fake_output = json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": "no block here",
    }})
    with patch("fb342_block_health.subprocess.run",
               return_value=_fake_run(fake_output)):
        r = bh.probe_hook()
    assert r["block_present"] is False
    assert r["reason"] == "block_not_in_context"


def test_probe_hook_exit_nonzero():
    with patch("fb342_block_health.subprocess.run",
               return_value=_fake_run("", returncode=1)):
        r = bh.probe_hook()
    assert r["block_present"] is False
    assert "hook_exit_" in r["reason"]


def test_probe_hook_unparseable_output():
    with patch("fb342_block_health.subprocess.run",
               return_value=_fake_run("not json")):
        r = bh.probe_hook()
    assert r["block_present"] is False
    assert r["reason"] == "hook_output_unparseable"


# ---------------------------------------------------------------------------
# consecutive_breaches — threshold logic
# ---------------------------------------------------------------------------


def _write_log(records: list[dict]) -> Path:
    """Write records to a temp jsonl, point bh.LOG_FILE at it, return path."""
    tmp = Path(tempfile.mkdtemp()) / "fb342_block_health.jsonl"
    with tmp.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return tmp


def test_breaches_zero_when_log_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(bh, "LOG_FILE", tmp_path / "nope.jsonl")
    count, breaches = bh.consecutive_breaches(
        {"max_tokens": 500, "max_rows": 12, "max_pool": 25}, 3)
    assert count == 0
    assert breaches == []


def test_breaches_three_in_a_row(monkeypatch):
    records = [
        {"event": "run_ok", "ts": "2026-05-01T08:00:00", "block_present": True,
         "block_tokens_est": 600, "row_count": 5, "candidate_pool": 10},
        {"event": "run_ok", "ts": "2026-05-02T08:00:00", "block_present": True,
         "block_tokens_est": 700, "row_count": 5, "candidate_pool": 10},
        {"event": "run_ok", "ts": "2026-05-03T08:00:00", "block_present": True,
         "block_tokens_est": 800, "row_count": 5, "candidate_pool": 10},
    ]
    log = _write_log(records)
    monkeypatch.setattr(bh, "LOG_FILE", log)
    count, breaches = bh.consecutive_breaches(
        {"max_tokens": 500, "max_rows": 12, "max_pool": 25}, 3)
    assert count == 3
    assert breaches[0]["date"] == "2026-05-03"  # most recent first


def test_breaches_streak_broken(monkeypatch):
    records = [
        {"event": "run_ok", "ts": "2026-05-01T08:00:00", "block_present": True,
         "block_tokens_est": 600, "row_count": 5, "candidate_pool": 10},
        {"event": "run_ok", "ts": "2026-05-02T08:00:00", "block_present": True,
         "block_tokens_est": 200, "row_count": 5, "candidate_pool": 10},  # OK
        {"event": "run_ok", "ts": "2026-05-03T08:00:00", "block_present": True,
         "block_tokens_est": 800, "row_count": 5, "candidate_pool": 10},
    ]
    log = _write_log(records)
    monkeypatch.setattr(bh, "LOG_FILE", log)
    count, breaches = bh.consecutive_breaches(
        {"max_tokens": 500, "max_rows": 12, "max_pool": 25}, 3)
    assert count == 1  # only 05-03 breaches; 05-02 broke the streak
    assert breaches[0]["date"] == "2026-05-03"


def test_breaches_skips_failed_probes(monkeypatch):
    records = [
        {"event": "run_ok", "ts": "2026-05-01T08:00:00", "block_present": False,
         "reason": "hook_timeout"},
        {"event": "run_ok", "ts": "2026-05-02T08:00:00", "block_present": True,
         "block_tokens_est": 800, "row_count": 5, "candidate_pool": 10},
    ]
    log = _write_log(records)
    monkeypatch.setattr(bh, "LOG_FILE", log)
    count, _ = bh.consecutive_breaches(
        {"max_tokens": 500, "max_rows": 12, "max_pool": 25}, 3)
    assert count == 1  # only 05-02 counts (failed probe ignored)


def test_breaches_no_breach_under_threshold(monkeypatch):
    records = [
        {"event": "run_ok", "ts": "2026-05-01T08:00:00", "block_present": True,
         "block_tokens_est": 200, "row_count": 5, "candidate_pool": 10},
        {"event": "run_ok", "ts": "2026-05-02T08:00:00", "block_present": True,
         "block_tokens_est": 300, "row_count": 6, "candidate_pool": 12},
    ]
    log = _write_log(records)
    monkeypatch.setattr(bh, "LOG_FILE", log)
    count, _ = bh.consecutive_breaches(
        {"max_tokens": 500, "max_rows": 12, "max_pool": 25}, 3)
    assert count == 0
