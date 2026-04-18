#!/usr/bin/env python3
"""Detect embedding service crash loops and auto-file feedback (F208.5).

Scans ~/.claude/logs/embedding-service.log for consecutive `Failed to load model:`
or `NO_SUCHFILE` lines within a rolling 90-minute window. 3+ failures in that
window triggers a feedback filing via capture_failure().

Designed to run via scheduled_jobs (cron-style). Safe to run frequently: uses
a marker file to avoid duplicate filings for the same incident.

Usage:
    python embedding_crashloop_detector.py [--window-minutes N] [--threshold N]
"""
import argparse
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from failure_capture import capture_failure

LOG_FILE = Path.home() / ".claude" / "logs" / "embedding-service.log"
MARKER_FILE = Path.home() / ".claude" / "embedding-crashloop-last-filed.txt"
# Matches log lines like "2026-04-18 11:11:02 - ERROR - Failed to load model: ..."
LINE_RX = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (ERROR|WARNING) - "
    r"(?P<msg>.*(?:Failed to load model|NO_SUCHFILE|Model load failed).*)$"
)


def parse_failures(log_path: Path):
    if not log_path.exists():
        return []
    failures = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = LINE_RX.match(line.rstrip())
                if not m:
                    continue
                try:
                    ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                failures.append((ts, m.group("msg")[:200]))
    except Exception as exc:
        print(f"Failed to read {log_path}: {exc}", file=sys.stderr)
    return failures


def window_has_crashloop(failures, window_minutes: int, threshold: int):
    """Return the latest window-end timestamp with >= threshold failures, or None."""
    if len(failures) < threshold:
        return None
    window = timedelta(minutes=window_minutes)
    # Sliding window over sorted timestamps
    failures.sort(key=lambda x: x[0])
    for i in range(len(failures) - threshold + 1):
        start = failures[i][0]
        end_idx = i + threshold - 1
        if failures[end_idx][0] - start <= window:
            return failures[end_idx][0]
    return None


def already_filed_for(ts: datetime) -> bool:
    """Check the marker file to see if we already filed for this incident window."""
    if not MARKER_FILE.exists():
        return False
    try:
        last = datetime.fromisoformat(MARKER_FILE.read_text().strip())
        # Same incident = within 2 hours of last-filed timestamp
        return abs((ts - last).total_seconds()) < 2 * 3600
    except Exception:
        return False


def mark_filed(ts: datetime):
    try:
        MARKER_FILE.parent.mkdir(exist_ok=True)
        MARKER_FILE.write_text(ts.isoformat())
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-minutes", type=int, default=90)
    ap.add_argument("--threshold", type=int, default=3)
    args = ap.parse_args()

    failures = parse_failures(LOG_FILE)
    if not failures:
        print("[embedding-crashloop-detector] no failures found")
        return 0

    hit = window_has_crashloop(failures, args.window_minutes, args.threshold)
    if not hit:
        print(f"[embedding-crashloop-detector] {len(failures)} total failures, no crashloop in last {args.window_minutes}min")
        return 0

    if already_filed_for(hit):
        print(f"[embedding-crashloop-detector] crashloop at {hit} already filed, skipping")
        return 0

    recent = [f for f in failures if f[0] >= hit - timedelta(minutes=args.window_minutes)]
    summary = "\n".join(f"  {ts:%Y-%m-%d %H:%M:%S} - {msg}" for ts, msg in recent[-5:])
    error = (
        f"Embedding service crash loop: {len(recent)} failures within "
        f"{args.window_minutes}min window ending {hit:%Y-%m-%d %H:%M:%S}.\n\n"
        f"Recent failures:\n{summary}\n\n"
        f"Check {LOG_FILE} for full context. Likely causes: "
        f"missing snapshot files (run scripts/fix_embedding_cache.py), "
        f"corrupted cache, HF_HUB_OFFLINE blocking recovery."
    )
    result = capture_failure(
        system_name="embedding_service",
        error_message=error,
        source_file=str(LOG_FILE),
        project_name="claude-family",
        auto_file_feedback=True,
    )
    if result.get("feedback_id"):
        mark_filed(hit)
        print(f"[embedding-crashloop-detector] filed feedback {result['feedback_id']}")
    else:
        print(f"[embedding-crashloop-detector] capture_failure result: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
