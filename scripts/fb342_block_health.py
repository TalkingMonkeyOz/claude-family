#!/usr/bin/env python3
"""FB342 block health monitor — daily check on the RECENT CHANGES injection.

Pipes a synthetic prompt through protocol_inject_hook.py, extracts the
RECENT CHANGES block, and records:
  - block_present (bool)
  - block_chars / block_tokens_est (int — token estimate is chars/4)
  - row_count (int — lines starting with "  [")
  - candidate_pool (int — total knowledge rows that COULD be surfaced today)

Logs to ~/.claude/logs/fb342_block_health.jsonl. If thresholds are breached
on N consecutive runs, files claude.feedback (type='design', priority='medium')
so a future Claude tunes the LIMIT / type filter / confidence floor.

Thresholds (configurable via CLI):
  --max-tokens N        block-tokens budget (default 500)
  --max-rows N          row count ceiling (default 12)
  --max-pool N          candidate pool ceiling — firehose growth alarm (default 500;
                        baseline ~229 on 2026-04-26 with 7d of heavy work)
  --consecutive-days N  require N runs in a row before filing (default 3)

Idempotent: dedupes feedback on title prefix. Fail-open: errors → JSONL, exit 0.

Usage:
    python fb342_block_health.py [--dry-run] [--verbose]

Designed to register as a daily scheduled_job at `0 8 * * *`.
Tracks: FB342 (Phase 4b — change-log injection surface).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri

import psycopg2
from psycopg2.extras import RealDictCursor

# ---------------------------------------------------------------------------
# Logging — JSONL fail-open
# ---------------------------------------------------------------------------

LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "fb342_block_health.jsonl"

HOOK_PATH = Path(__file__).parent / "protocol_inject_hook.py"
PROJECT_ROOT = Path(__file__).parent.parent
SYNTHETIC_PROMPT = "fb342 daily health probe"
BLOCK_HEADER = "RECENT CHANGES (last 7 days"


def jlog(event: str, **kwargs) -> None:
    rec = {"ts": datetime.now().isoformat(), "event": event, **kwargs}
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass  # fail-open: never raise from logging


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------


def probe_hook() -> dict:
    """Run the hook with a synthetic prompt; extract block stats.

    Returns dict with: block_present, block_chars, block_tokens_est, row_count,
    raw_block (str). On hook error, returns block_present=False with reason.
    """
    payload = json.dumps({"prompt": SYNTHETIC_PROMPT})
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(PROJECT_ROOT),
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        return {"block_present": False, "reason": "hook_timeout"}
    except Exception as e:
        return {"block_present": False, "reason": f"hook_failed:{type(e).__name__}"}

    if result.returncode != 0:
        return {"block_present": False, "reason": f"hook_exit_{result.returncode}"}

    try:
        hook_output = json.loads(result.stdout)
        ctx = hook_output["hookSpecificOutput"]["additionalContext"]
    except (json.JSONDecodeError, KeyError):
        return {"block_present": False, "reason": "hook_output_unparseable"}

    idx = ctx.find(BLOCK_HEADER)
    if idx < 0:
        return {"block_present": False, "reason": "block_not_in_context"}

    end = ctx.find("\n\n", idx)
    block = ctx[idx:end if end > 0 else len(ctx)]
    rows = [ln for ln in block.split("\n") if ln.startswith("  [")]
    return {
        "block_present": True,
        "block_chars": len(block),
        "block_tokens_est": len(block) // 4,
        "row_count": len(rows),
        "raw_block": block,
    }


def candidate_pool_size(cur) -> int:
    """How many rows COULD have surfaced today (independent of LIMIT 6)?"""
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM claude.knowledge
        WHERE status = 'active'
          AND knowledge_type IN ('decision','pattern','gotcha','learned')
          AND created_at > NOW() - INTERVAL '7 days'
        """
    )
    row = cur.fetchone()
    return int(row["n"]) if row else 0


# ---------------------------------------------------------------------------
# Threshold + feedback
# ---------------------------------------------------------------------------


def consecutive_breaches(thresholds: dict, days: int) -> tuple[int, list[dict]]:
    """Count consecutive days (most recent first) the run breached any threshold.

    Reads jsonl tail; skips probes where block_present=False (those signal
    a different problem — not noise). Returns (count, [breach_records]).
    """
    if not LOG_FILE.exists():
        return 0, []
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-200:]
    except Exception:
        return 0, []

    recs = []
    for ln in reversed(lines):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("event") != "run_ok" or not r.get("block_present"):
            continue
        recs.append(r)
        if len(recs) >= days * 3:  # over-fetch in case of multi-runs/day
            break

    # Group by date, take latest run per date
    by_date: dict[str, dict] = {}
    for r in recs:
        d = r.get("ts", "")[:10]
        if d and d not in by_date:
            by_date[d] = r

    sorted_days = sorted(by_date.keys(), reverse=True)
    breaches = []
    for d in sorted_days:
        r = by_date[d]
        breach = (
            r.get("block_tokens_est", 0) > thresholds["max_tokens"]
            or r.get("row_count", 0) > thresholds["max_rows"]
            or r.get("candidate_pool", 0) > thresholds["max_pool"]
        )
        if not breach:
            break
        breaches.append({"date": d, **{k: r.get(k) for k in
            ("block_tokens_est", "row_count", "candidate_pool")}})

    return len(breaches), breaches


def already_filed(cur, title_prefix: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM claude.feedback
        WHERE title ILIKE %s
          AND status NOT IN ('resolved', 'cancelled', 'rejected')
        LIMIT 1
        """,
        (title_prefix + "%",),
    )
    return cur.fetchone() is not None


def file_health_feedback(cur, breaches: list[dict], thresholds: dict, dry_run: bool) -> bool:
    title = "FB342 RECENT CHANGES block exceeding thresholds — tune LIMIT / type filter"
    if already_filed(cur, title[:60]):
        return False
    desc = (
        f"FB342 block health monitor flagged {len(breaches)} consecutive days of "
        f"threshold breaches.\n\nThresholds: max_tokens={thresholds['max_tokens']}, "
        f"max_rows={thresholds['max_rows']}, max_pool={thresholds['max_pool']}.\n\n"
        f"Recent breach records (most recent first):\n"
        + "\n".join(f"  - {b['date']}: tokens={b.get('block_tokens_est')}, "
                    f"rows={b.get('row_count')}, pool={b.get('candidate_pool')}" for b in breaches)
        + "\n\nKnobs to tune (in scripts/protocol_inject_hook.py _query_recent_changes):\n"
          "  - Lower LIMIT 6 → 4\n"
          "  - Raise type filter — drop 'gotcha' or 'learned'\n"
          "  - Add WHERE confidence_level >= 70\n"
          "  - Or kill the block via CLAUDE_DISABLE_CHANGE_LOG=1 if it's not influencing behavior."
    )
    if dry_run:
        return True
    cur.execute(
        """
        INSERT INTO claude.feedback (feedback_id, project_id, feedback_type, title,
                                     description, priority, status, short_code, created_at)
        SELECT gen_random_uuid(),
               (SELECT project_id FROM claude.projects WHERE project_name='claude-family'),
               'design', %s, %s, 'medium', 'new',
               (SELECT COALESCE(MAX(short_code), 0) + 1 FROM claude.feedback),
               NOW()
        """,
        (title, desc),
    )
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=500)
    ap.add_argument("--max-rows", type=int, default=12)
    ap.add_argument("--max-pool", type=int, default=500)
    ap.add_argument("--consecutive-days", type=int, default=3)
    args = ap.parse_args()

    thresholds = {
        "max_tokens": args.max_tokens,
        "max_rows": args.max_rows,
        "max_pool": args.max_pool,
    }

    try:
        # 1. Probe the hook
        probe = probe_hook()

        # 2. Pool size from DB (independent of probe)
        conn = psycopg2.connect(get_database_uri())
        cur = conn.cursor(cursor_factory=RealDictCursor)
        pool = candidate_pool_size(cur)

        # 3. Build run record + log
        rec = {
            **{k: v for k, v in probe.items() if k != "raw_block"},
            "candidate_pool": pool,
            "thresholds": thresholds,
        }
        if args.verbose:
            print(json.dumps(rec, indent=2))
        jlog("run_ok", **rec)

        # 4. Threshold check (only if block_present)
        filed = False
        if probe.get("block_present"):
            count, breaches = consecutive_breaches(thresholds, args.consecutive_days)
            if count >= args.consecutive_days:
                write_cur = conn.cursor()
                filed = file_health_feedback(write_cur, breaches, thresholds, args.dry_run)
                if not args.dry_run and filed:
                    conn.commit()
                write_cur.close()
                jlog("feedback_filed" if filed else "feedback_skipped_dedupe",
                     consecutive_days=count, breaches=breaches)

        cur.close()
        conn.close()

        result = {**rec, "feedback_filed": filed, "dry_run": args.dry_run}
        print(json.dumps(result))
        return 0
    except Exception as e:
        jlog("run_failed", error=str(e), error_type=type(e).__name__)
        print(json.dumps({"error": str(e), "fail_open": True}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
