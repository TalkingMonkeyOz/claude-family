"""
f226_parity_check.py — F226 / BT719.

Periodic parity job comparing legacy tables (claude.features, build_tasks,
feedback, todos) with their compat views (v_*_compat) over claude.work_items.

Detects: row-count drift, status-distribution drift, missing legacy
short_codes (rows that exist legacy-side but not in code_history).

On drift: writes a SEV2 feedback row via work_create() so the next session
sees it, and exits non-zero so the scheduler logs the failure.

Usage:
    python scripts/f226_parity_check.py
    python scripts/f226_parity_check.py --json   # machine-readable output

Designed to be safe under the existing strangler-fig pattern: parity is
expected to drift while code is mid-cutover during F228, so this job
becomes more useful the closer we get to Phase 3.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


SOURCES = [
    ('features',    'v_features_compat',    'F'),
    ('build_tasks', 'v_build_tasks_compat', 'BT'),
    ('feedback',    'v_feedback_compat',    'FB'),
    ('todos',       'v_todos_compat',       'TODO-'),
]


def _load_dotenv() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    if "DATABASE_URI" not in os.environ and os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URI"] = os.environ["DATABASE_URL"]


def connect():
    url = os.environ.get("DATABASE_URI") or os.environ.get("POSTGRES_CONNECTION_STRING")
    if not url:
        raise SystemExit("DATABASE_URI not set")
    return psycopg.connect(url, row_factory=dict_row, autocommit=True)


def check_row_counts(cur) -> list[dict]:
    """One row per source: legacy_count, compat_count, delta."""
    out = []
    for legacy, compat, _prefix in SOURCES:
        cur.execute(f"SELECT COUNT(*) AS c FROM claude.{legacy}")
        legacy_n = cur.fetchone()['c']
        cur.execute(f"SELECT COUNT(*) AS c FROM claude.{compat}")
        compat_n = cur.fetchone()['c']
        out.append({
            'source':       legacy,
            'legacy_count': legacy_n,
            'compat_count': compat_n,
            'delta':        legacy_n - compat_n,
        })
    return out


def check_status_distribution(cur) -> list[dict]:
    """Compare COUNT(*) GROUP BY status between each pair."""
    out = []
    for legacy_name, compat, _prefix in SOURCES:
        cur.execute(
            f"SELECT status, COUNT(*) AS c FROM claude.{legacy_name} GROUP BY status"
        )
        legacy_d = {r['status']: r['c'] for r in cur.fetchall()}
        cur.execute(
            f"SELECT status, COUNT(*) AS c FROM claude.{compat} GROUP BY status"
        )
        compat_d = {r['status']: r['c'] for r in cur.fetchall()}
        all_statuses = set(legacy_d.keys()) | set(compat_d.keys())
        diffs = {
            s: {'legacy': legacy_d.get(s, 0), 'compat': compat_d.get(s, 0)}
            for s in all_statuses
            if legacy_d.get(s, 0) != compat_d.get(s, 0)
        }
        out.append({'source': legacy_name, 'diff': diffs})
    return out


def check_missing_codes(cur) -> list[dict]:
    """Legacy short_codes that have no entry in work_item_code_history."""
    out = []
    for legacy, _compat, prefix in SOURCES:
        if legacy == 'todos':
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.todos t "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM claude.work_item_code_history h "
                "  WHERE h.short_code = 'TODO-' || t.todo_id::text "
                "    AND h.code_kind = 'legacy'"
                ")"
            )
        else:
            pk = {'features': 'feature_id', 'build_tasks': 'task_id',
                  'feedback': 'feedback_id'}[legacy]
            cur.execute(
                f"SELECT COUNT(*) AS c FROM claude.{legacy} src "
                f"WHERE NOT EXISTS ("
                f"  SELECT 1 FROM claude.work_item_code_history h "
                f"  WHERE h.short_code = '{prefix}' || src.short_code "
                f"    AND h.code_kind = 'legacy'"
                f")"
            )
        out.append({'source': legacy, 'missing_count': cur.fetchone()['c']})
    return out


def file_drift_feedback(cur, summary: dict) -> str | None:
    """Write a SEV2 feedback row when drift is detected. Returns the FB### code."""
    body = json.dumps(summary, default=str, indent=2)
    cur.execute(
        """
        INSERT INTO claude.feedback (feedback_id, project_id, feedback_type, title,
                                     description, status, priority,
                                     created_at, updated_at)
        SELECT gen_random_uuid(), project_id, 'bug',
               'F226 parity check drift detected',
               %s, 'new', 'high', NOW(), NOW()
          FROM claude.projects WHERE project_name='claude-family'
        RETURNING short_code
        """,
        (body,),
    )
    row = cur.fetchone()
    return f"FB{row['short_code']}" if row else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true",
                   help="Emit JSON to stdout instead of human report.")
    p.add_argument("--no-feedback", action="store_true",
                   help="Skip writing a feedback row on drift (for tests).")
    args = p.parse_args()

    _load_dotenv()
    conn = connect()
    try:
        cur = conn.cursor()
        row_counts = check_row_counts(cur)
        status_dist = check_status_distribution(cur)
        missing = check_missing_codes(cur)

        drift = (
            any(r['delta'] != 0 for r in row_counts)
            or any(s['diff'] for s in status_dist)
            or any(m['missing_count'] > 0 for m in missing)
        )

        summary = {
            'drift_detected':       drift,
            'row_counts':           row_counts,
            'status_distribution':  status_dist,
            'missing_legacy_codes': missing,
        }

        if args.json:
            print(json.dumps(summary, default=str, indent=2))
        else:
            print(f"F226 parity check — drift_detected={drift}")
            for r in row_counts:
                print(f"  [{r['source']}] legacy={r['legacy_count']} compat={r['compat_count']} delta={r['delta']}")
            for s in status_dist:
                if s['diff']:
                    print(f"  [{s['source']}] status diffs: {s['diff']}")
            for m in missing:
                if m['missing_count'] > 0:
                    print(f"  [{m['source']}] {m['missing_count']} missing legacy codes")

        if drift and not args.no_feedback:
            fb_code = file_drift_feedback(cur, summary)
            print(f"Filed {fb_code} (SEV2)")

        sys.exit(1 if drift else 0)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
