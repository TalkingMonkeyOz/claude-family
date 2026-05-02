#!/usr/bin/env python3
"""Detect embedding service crash loops and auto-file feedback (F208.5).

Now uses cf_circuit_breaker.CircuitBreaker for generic state management.
Scans ~/.claude/logs/embedding-service.log for error patterns, records failures
to the circuit breaker. On breaker trip, auto-files feedback via capture_failure().

Designed to run via scheduled_jobs (cron-style). Safe to run frequently:
circuit breaker prevents duplicate filings for same incident.

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
from cf_circuit_breaker import CircuitBreaker
from failure_capture import capture_failure

LOG_FILE = Path.home() / ".claude" / "logs" / "embedding-service.log"
# Matches log lines like "2026-04-18 11:11:02 - ERROR - Failed to load model: ..."
LINE_RX = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (ERROR|WARNING) - "
    r"(?P<msg>.*(?:Failed to load model|NO_SUCHFILE|Model load failed).*)$"
)


def parse_failures(log_path: Path):
    """Parse log file and return list of (timestamp, message) tuples."""
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


def on_breaker_trip():
    """Callback: invoked when circuit breaker trips. Files feedback."""
    failures = parse_failures(LOG_FILE)
    if not failures:
        return

    failures.sort(key=lambda x: x[0])
    recent = failures[-5:] if len(failures) >= 5 else failures

    summary = "\n".join(f"  {ts:%Y-%m-%d %H:%M:%S} - {msg}" for ts, msg in recent)
    error = (
        f"Embedding service crash loop detected (circuit breaker tripped).\n\n"
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
        print(f"[embedding-crashloop-detector] circuit breaker tripped, filed feedback {result['feedback_id']}")
    else:
        print(f"[embedding-crashloop-detector] circuit breaker trip callback result: {result}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-minutes", type=int, default=90)
    ap.add_argument("--threshold", type=int, default=3)
    args = ap.parse_args()

    # Window in seconds
    window_secs = args.window_minutes * 60

    # Create circuit breaker with callback
    cb = CircuitBreaker(
        name="embedding-service",
        threshold_fails=args.threshold,
        window_secs=window_secs,
        on_trip=on_breaker_trip,
    )

    failures = parse_failures(LOG_FILE)
    if not failures:
        print("[embedding-crashloop-detector] no failures found")
        return 0

    # Record each failure to the circuit breaker
    failures.sort(key=lambda x: x[0])
    for ts, msg in failures:
        # Only record recent failures (within window)
        if ts >= datetime.utcnow() - timedelta(seconds=window_secs):
            cb.record_failure(error_class="LogError", error_message=msg)

    state = cb.state()
    print(
        f"[embedding-crashloop-detector] {state['fail_count_in_window']} failures in window, "
        f"tripped={state['tripped']}"
    )

    if state["tripped"]:
        print(f"[embedding-crashloop-detector] circuit breaker is TRIPPED (reason: {state['tripped_reason']})")
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
