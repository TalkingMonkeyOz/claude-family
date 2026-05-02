"""
f226_backfill_reminders.py — F226 / BT720.

Idempotent backfill of claude.scheduled_reminders into claude.work_items
with kind='reminder'. Each row gets:
  - work_items row: kind='reminder', stage='done' if surfaced_at IS NOT NULL
                    else 'planned', task_scope='persistent', due_at populated
                    from typed column
  - code_history rows: canonical W### + legacy RM###

The actual create_reminder() / list_reminders() / snooze_reminder() handlers
keep using claude.scheduled_reminders as primary in Phase 1 — the legacy-side
swap to work_items is F228 dual-write work. For now we just ensure RM###
codes resolve via work_item_resolve_legacy().

Usage:
    python scripts/f226_backfill_reminders.py --dry-run
    python scripts/f226_backfill_reminders.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


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
    return psycopg.connect(url, row_factory=dict_row, autocommit=False)


def already_backfilled_codes(cur) -> set[str]:
    cur.execute(
        "SELECT short_code FROM claude.work_item_code_history "
        "WHERE valid_to IS NULL AND short_code LIKE 'RM%'"
    )
    return {r['short_code'] for r in cur.fetchall()}


def _project_id_for(cur, project_name: str | None) -> str:
    """Resolve a project_name to its UUID, falling back to claude-family for global rows."""
    cur.execute(
        "SELECT project_id FROM claude.projects WHERE project_name=%s",
        (project_name or 'claude-family',),
    )
    row = cur.fetchone()
    if row:
        return row['project_id']
    # Last-resort: claude-family
    cur.execute(
        "SELECT project_id FROM claude.projects WHERE project_name='claude-family'"
    )
    return cur.fetchone()['project_id']


def backfill(cur, *, dry_run: bool) -> dict:
    seen = already_backfilled_codes(cur)
    cur.execute("SELECT * FROM claude.scheduled_reminders")
    rows = cur.fetchall()
    inserted = 0
    skipped = 0
    for r in rows:
        legacy = r['short_code']  # already 'RM<n>'
        if not legacy or not legacy.startswith('RM'):
            skipped += 1
            continue
        if legacy in seen:
            skipped += 1
            continue
        if dry_run:
            inserted += 1
            continue

        pid = _project_id_for(cur, r.get('project_name'))
        stage = 'done' if r.get('surfaced_at') else 'planned'
        title = (r['body'] or 'Untitled reminder')[:500]
        attributes = {
            'legacy_table': 'scheduled_reminders',
            'rationale': r.get('rationale') or '',
            'snooze_count': 0,
            'original_legacy_status': 'surfaced' if r.get('surfaced_at') else 'pending',
        }
        for k in ('linked_todo_id', 'linked_workfile_component',
                  'linked_workfile_title', 'linked_feature_code'):
            if r.get(k):
                attributes[k] = str(r[k])

        cur.execute(
            "INSERT INTO claude.work_items "
            "(title, description, kind, stage, priority, project_id, "
            " task_scope, due_at, completed_at, created_at, updated_at, "
            " created_session_id, attributes) "
            "VALUES (%s, %s, 'reminder', %s, 3, %s, "
            "        'persistent', %s, %s, %s, %s, %s, %s) "
            "RETURNING work_item_id, short_code",
            (
                title,
                r.get('body'),
                stage,
                pid,
                r.get('due_at'),
                r.get('surfaced_at'),
                r.get('created_at') or 'now()',
                r.get('created_at') or 'now()',
                r.get('created_by_session_id'),
                json.dumps(attributes),
            ),
        )
        wi = cur.fetchone()

        note = "backfilled from scheduled_reminders"
        cur.execute(
            "INSERT INTO claude.work_item_code_history "
            "(work_item_id, short_code, code_kind, notes) "
            "VALUES (%s, %s, 'canonical', %s), "
            "       (%s, %s, 'legacy',    %s)",
            (wi['work_item_id'], f"W{wi['short_code']}", note,
             wi['work_item_id'], legacy,                  note),
        )
        inserted += 1
    return {'inserted': inserted, 'skipped': skipped, 'total_rows': len(rows)}


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = p.parse_args()

    _load_dotenv()
    conn = connect()
    try:
        cur = conn.cursor()
        r = backfill(cur, dry_run=args.dry_run)
        print(f"[scheduled_reminders] inserted={r['inserted']} "
              f"skipped={r['skipped']} total={r['total_rows']}")
        if args.apply:
            conn.commit()
            print("Applied — committed.")
        else:
            conn.rollback()
            print("Dry run — rolled back.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
