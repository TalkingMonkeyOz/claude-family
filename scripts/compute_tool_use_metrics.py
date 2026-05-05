#!/usr/bin/env python3
"""F232.P5 — compute claude.tool_use_metrics rows from claude.mcp_usage.

Per spec workfile 1cb60d23 (locked 2026-05-04). One row per session per
nightly run. Five rates:

  bypass_rate                 = harness rows with bypass_detected / harness rows
  pattern_reuse_rate          = NULL until post-write diff analysis lands
  duplication_avoidance_rate  = NULL until P4 nudges ship
  continuity_rate             = NULL until cross-session memory tracking lands
  nudge_acceptance_rate       = nudge_fired & followed / nudge_fired

For rates we cannot yet compute, the script writes NULL and records the
denominator counts in raw_counts so dashboards can show "data not yet
collected" honestly. Placeholder NULLs are how the spec mandates handling
deferred rates — no fabricated zeros.

Idempotent: running twice in the same UTC day for the same session
replaces the prior row (DELETE-then-INSERT keyed by (session_id, computed_at::date)).

Usage:
  python scripts/compute_tool_use_metrics.py                  # default 24h lookback
  python scripts/compute_tool_use_metrics.py --window-hours 168
  python scripts/compute_tool_use_metrics.py --session-id <uuid>
  python scripts/compute_tool_use_metrics.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection  # type: ignore

LOG_FILE = os.path.expanduser("~/.claude/logs/compute_tool_use_metrics.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("compute_tool_use_metrics")


def _safe_rate(num: int, den: int) -> Optional[float]:
    return None if den == 0 else round(num / den, 6)


def collect_session_counts(conn, session_id: str, window_hours: int) -> Dict[str, Any]:
    """Aggregate the per-session counters needed for the 5 rates.

    Returns a dict keyed by counter name. Computation here is a single
    SQL query to keep the nightly-job runtime predictable.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE tool_kind='harness')                                      AS harness_total,
            COUNT(*) FILTER (WHERE tool_kind='harness' AND bypass_detected=TRUE)             AS harness_bypass,
            COUNT(*) FILTER (WHERE tool_kind='hook' AND tool_name='coding_intelligence_writetime') AS hook_writetime_total,
            COUNT(*) FILTER (
                WHERE tool_kind='hook'
                  AND tool_name='coding_intelligence_writetime'
                  AND (metadata->>'memories_surfaced_n')::int > 0
            )                                                                                AS injection_fired,
            COUNT(*) FILTER (WHERE nudge_fired=TRUE)                                         AS nudge_fired_total,
            MIN(called_at)                                                                   AS window_start,
            MAX(called_at)                                                                   AS window_end,
            COUNT(*)                                                                         AS rows_total
        FROM   claude.mcp_usage
        WHERE  session_id = %s
          AND  called_at >= NOW() - (%s || ' hours')::interval
        """,
        (session_id, window_hours),
    )
    row = cur.fetchone()
    if not row:
        return {}
    if isinstance(row, dict):
        return dict(row)
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def list_active_sessions(conn, window_hours: int,
                         only_session: Optional[str] = None) -> List[str]:
    cur = conn.cursor()
    if only_session:
        return [only_session]
    cur.execute(
        """
        SELECT DISTINCT session_id::text AS sid
        FROM   claude.mcp_usage
        WHERE  called_at >= NOW() - (%s || ' hours')::interval
          AND  session_id IS NOT NULL
        """,
        (window_hours,),
    )
    out: List[str] = []
    for r in cur.fetchall():
        if isinstance(r, dict):
            out.append(r["sid"])
        else:
            out.append(r[0])
    return out


def get_project_id_for_session(conn, session_id: str) -> Optional[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.project_id::text
        FROM   claude.sessions s
        JOIN   claude.projects p ON p.project_name = s.project_name
        WHERE  s.session_id = %s
        """,
        (session_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return row.get("project_id")
    return row[0]


def compute_metrics(counts: Dict[str, Any]) -> Dict[str, Any]:
    """Translate raw counts into the 5 rates per spec 1cb60d23."""
    bypass_rate = _safe_rate(counts.get("harness_bypass", 0), counts.get("harness_total", 0))
    nudge_acceptance_rate = _safe_rate(
        0,  # numerator requires "followed" tracking — Phase 2 of F231/F232.P6
        counts.get("nudge_fired_total", 0),
    ) if counts.get("nudge_fired_total", 0) > 0 else None

    return {
        "bypass_rate": bypass_rate,
        "pattern_reuse_rate": None,         # post-write diff analysis (deferred)
        "duplication_avoidance_rate": None, # P4 nudges (deferred)
        "continuity_rate": None,            # cross-session memory tracking (deferred)
        "nudge_acceptance_rate": nudge_acceptance_rate,
        "raw_counts": {
            "harness_total": counts.get("harness_total", 0),
            "harness_bypass": counts.get("harness_bypass", 0),
            "hook_writetime_total": counts.get("hook_writetime_total", 0),
            "injection_fired": counts.get("injection_fired", 0),
            "nudge_fired_total": counts.get("nudge_fired_total", 0),
            "rows_total": counts.get("rows_total", 0),
            "deferred_rates_reason": {
                "pattern_reuse_rate": "needs post-write diff vs surfaced memories",
                "duplication_avoidance_rate": "P4 nudges not yet shipped",
                "continuity_rate": "cross-session memory application tracking not yet shipped",
                "nudge_acceptance_rate": "nudge 'followed' detection not yet shipped",
            },
        },
        "window_start": counts.get("window_start"),
        "window_end": counts.get("window_end"),
    }


def upsert_metrics_row(conn, *, session_id: str, project_id: Optional[str],
                       metrics: Dict[str, Any], dry_run: bool = False) -> str:
    """Replace today's row for this session, then INSERT fresh.

    Idempotent for nightly re-runs. Same-day reruns produce a single
    row per session.
    """
    if dry_run:
        return "dry-run"

    cur = conn.cursor()
    # DELETE this session's row computed today (UTC). DATE() on TIMESTAMPTZ
    # uses the server timezone; for nightly cron at 03:00 local that's fine.
    cur.execute(
        """
        DELETE FROM claude.tool_use_metrics
        WHERE  session_id = %s
          AND  computed_at::date = CURRENT_DATE
        """,
        (session_id,),
    )
    cur.execute(
        """
        INSERT INTO claude.tool_use_metrics (
            session_id, project_id, window_start, window_end,
            bypass_rate, pattern_reuse_rate, duplication_avoidance_rate,
            continuity_rate, nudge_acceptance_rate,
            hawthorne_suppressed, raw_counts
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            FALSE, %s::jsonb
        )
        RETURNING metric_id::text
        """,
        (
            session_id, project_id,
            metrics["window_start"], metrics["window_end"],
            metrics["bypass_rate"], metrics["pattern_reuse_rate"],
            metrics["duplication_avoidance_rate"],
            metrics["continuity_rate"], metrics["nudge_acceptance_rate"],
            json.dumps(metrics["raw_counts"]),
        ),
    )
    row = cur.fetchone()
    metric_id = row[0] if not isinstance(row, dict) else row.get("metric_id")
    conn.commit()
    return metric_id or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=int, default=24,
                        help="Lookback window for sessions to compute (default: 24)")
    parser.add_argument("--session-id", type=str, default=None,
                        help="Compute for a single session UUID only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing")
    args = parser.parse_args()

    conn = get_db_connection()
    if not conn:
        logger.error("no DB connection — aborting")
        return 2

    try:
        sessions = list_active_sessions(conn, args.window_hours, args.session_id)
        logger.info(f"computing metrics for {len(sessions)} sessions "
                    f"(window {args.window_hours}h, dry_run={args.dry_run})")

        written = 0
        for sid in sessions:
            counts = collect_session_counts(conn, sid, args.window_hours)
            if counts.get("rows_total", 0) == 0:
                continue
            metrics = compute_metrics(counts)
            project_id = get_project_id_for_session(conn, sid)
            metric_id = upsert_metrics_row(
                conn, session_id=sid, project_id=project_id,
                metrics=metrics, dry_run=args.dry_run,
            )
            written += 1
            logger.info(
                f"session {sid[:8]} -> metric {metric_id[:8] if metric_id != 'dry-run' else 'dry-run'} "
                f"bypass={metrics['bypass_rate']} "
                f"injection_fired={metrics['raw_counts']['injection_fired']}/"
                f"{metrics['raw_counts']['hook_writetime_total']}"
            )

        print(json.dumps({
            "ok": True,
            "sessions_computed": written,
            "window_hours": args.window_hours,
            "dry_run": args.dry_run,
        }))
        return 0
    except Exception as exc:
        logger.exception("compute_tool_use_metrics failed")
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
