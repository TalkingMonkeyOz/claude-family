"""
f226_backfill_work_items.py — F226 / BT717.

Idempotent backfill of features + build_tasks + feedback + todos into the
unified claude.work_items table + claude.work_item_code_history sidecar.

Usage:
    python scripts/f226_backfill_work_items.py --dry-run
    python scripts/f226_backfill_work_items.py --apply

Idempotency:
    Each source row is keyed by its legacy short_code (e.g. 'F12', 'BT45',
    'FB99', 'TODO-<uuid>'). If that code already exists in
    claude.work_item_code_history (active, valid_to IS NULL), the row is
    skipped. So re-running is a no-op once complete.

Pass strategy:
    Pass 1: insert all new work_items rows + emit code_history rows
            (canonical W### + legacy short code).
    Pass 2: UPDATE work_items.parent_id from
            features.parent_feature_id and build_tasks.feature_id
            using the source_id → work_item_id map built in pass 1.

Reminders are not backfilled here (BT720 owns reminder migration).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

STAGE_MAP = {
    # features
    ('features', 'draft'):       'raw',
    ('features', 'planned'):     'planned',
    ('features', 'not_started'): 'planned',
    ('features', 'in_progress'): 'in_progress',
    ('features', 'blocked'):     'blocked',
    ('features', 'completed'):   'done',
    ('features', 'cancelled'):   'dropped',
    # build_tasks
    ('build_tasks', 'todo'):        'planned',
    ('build_tasks', 'in_progress'): 'in_progress',
    ('build_tasks', 'blocked'):     'blocked',
    ('build_tasks', 'completed'):   'done',
    ('build_tasks', 'cancelled'):   'dropped',
    # feedback
    ('feedback', 'new'):         'raw',
    ('feedback', 'triaged'):     'triaged',
    ('feedback', 'in_progress'): 'in_progress',
    ('feedback', 'resolved'):    'done',
    ('feedback', 'wont_fix'):    'dropped',
    ('feedback', 'duplicate'):   'dropped',
    # todos
    ('todos', 'pending'):     'planned',
    ('todos', 'in_progress'): 'in_progress',
    ('todos', 'completed'):   'done',
    ('todos', 'cancelled'):   'dropped',
    ('todos', 'archived'):    'dropped',
}

# feedback uses varchar priority — coerce to int 1-5.
FB_PRIORITY_MAP = {'high': 2, 'medium': 3, 'low': 4}

DROPPED_REASON = {
    ('feedback', 'duplicate'): 'duplicate',
    ('todos', 'archived'):     'archived',
}

# features.feature_type has legacy values not in F226 vocab. Remap to a
# valid F226 kind; original value preserved in attributes.feature_type_legacy.
FEATURE_KIND_REMAP = {
    'feature':        'feature',
    'enhancement':    'feature',         # legacy "enhancement" folds into feature
    'ui':             'feature',         # legacy "ui" folds into feature
    'system':         'infrastructure',
    'integration':    'infrastructure',
    'infrastructure': 'infrastructure',
    'refactor':       'refactor',
    'documentation':  'documentation',
    'stream':         'stream',
    None:             'feature',
}


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Backfill — generic per-source logic
# ---------------------------------------------------------------------------

def _legacy_code(source_table: str, row: dict) -> str:
    if source_table == 'features':
        return f"F{row['short_code']}"
    if source_table == 'build_tasks':
        return f"BT{row['short_code']}"
    if source_table == 'feedback':
        return f"FB{row['short_code']}"
    if source_table == 'todos':
        return f"TODO-{row['todo_id']}"
    raise ValueError(f"unknown source table {source_table}")


def _row_to_work_item_payload(source_table: str, row: dict) -> dict:
    """Build the INSERT payload for claude.work_items from a source row."""
    stage = STAGE_MAP.get((source_table, row.get('status')))
    if stage is None:
        # Unknown legacy status — park it for later inspection rather than dropping.
        stage = 'parked'

    base = {
        'project_id':           row.get('project_id'),
        'created_at':           row.get('created_at'),
        'updated_at':           row.get('updated_at'),
        'created_session_id':   row.get('created_session_id'),
        'attributes':           {},
        'priority':             3,
    }

    # source-specific projection
    if source_table == 'features':
        legacy_ftype = row.get('feature_type')
        kind = FEATURE_KIND_REMAP.get(legacy_ftype, 'feature')
        base.update({
            'title':                 row['feature_name'],
            'description':           row.get('description'),
            'kind':                  kind,
            'stage':                 stage,
            'priority':              row.get('priority') or 3,
            'plan_data':             row.get('plan_data'),
            'completion_percentage': row.get('completion_percentage'),
            'started_at':            row.get('started_date'),
            'completed_at':          row.get('completed_date'),
            'attributes': {
                **({'feature_type_legacy': legacy_ftype} if legacy_ftype else {}),
                **({'design_doc_path': row['design_doc_path']} if row.get('design_doc_path') else {}),
                **({'implementation_notes': row['implementation_notes']}
                   if row.get('implementation_notes') else {}),
            },
        })
    elif source_table == 'build_tasks':
        base.update({
            'title':           row['task_name'],
            'description':     row.get('task_description'),
            'kind':            'task',
            'stage':           stage,
            'priority':        row.get('priority') or 3,
            'verification':    row.get('verification'),
            'files_affected':  row.get('files_affected'),
            'estimated_hours': row.get('estimated_hours'),
            'actual_hours':    row.get('actual_hours'),
            'started_at':      row.get('started_at'),
            'completed_at':    row.get('completed_at'),
            'attributes': {
                **({'task_type': row['task_type']} if row.get('task_type') else {}),
                **({'step_order': row['step_order']} if row.get('step_order') is not None else {}),
                **({'blocked_reason': row['blocked_reason']} if row.get('blocked_reason') else {}),
            },
        })
    elif source_table == 'feedback':
        prio_int = 3
        raw_prio = row.get('priority')
        if isinstance(raw_prio, str):
            prio_int = FB_PRIORITY_MAP.get(raw_prio.lower(), 3)
        elif isinstance(raw_prio, int):
            prio_int = raw_prio if 1 <= raw_prio <= 5 else 3
        base.update({
            'title':       row.get('title') or (row.get('description') or '')[:200] or 'Untitled feedback',
            'description': row.get('description'),
            'kind':        row.get('feedback_type') or 'idea',
            'stage':       stage,
            'priority':    prio_int,
            'completed_at': row.get('resolved_at'),
            'attributes': {
                **({'screenshot_path': row['screenshot_path']} if row.get('screenshot_path') else {}),
                **({'resolution_note': row['notes']} if row.get('notes') else {}),
                **({'feedback_priority_legacy': raw_prio} if raw_prio else {}),
            },
        })
    elif source_table == 'todos':
        base.update({
            'title':                row['content'][:500] if row.get('content') else 'Untitled todo',
            'description':          row.get('content'),
            'kind':                 'task',
            'stage':                stage,
            'priority':             row.get('priority') or 3,
            'task_scope':           row.get('task_scope') or 'session',
            'completed_at':         row.get('completed_at'),
            'completed_session_id': row.get('completed_session_id'),
            'is_deleted':           row.get('is_deleted', False),
            'deleted_at':           row.get('deleted_at'),
            'attributes': {
                **({'active_form': row['active_form']} if row.get('active_form') else {}),
                **({'restore_count': row['restore_count']} if row.get('restore_count') else {}),
                **({'source_message_id': str(row['source_message_id'])}
                   if row.get('source_message_id') else {}),
            },
        })

    # Drop reason for legacy duplicate / archived
    drop_reason = DROPPED_REASON.get((source_table, row.get('status')))
    if drop_reason:
        base['attributes']['dropped_reason'] = drop_reason

    base['attributes']['legacy_table'] = source_table
    if row.get('status'):
        # Preserve original legacy status so compat views can reverse-map exactly.
        base['attributes']['original_legacy_status'] = row['status']
    return base


SOURCE_QUERIES = {
    'features':    "SELECT * FROM claude.features",
    'build_tasks': "SELECT * FROM claude.build_tasks",
    'feedback':    "SELECT * FROM claude.feedback",
    'todos':       "SELECT * FROM claude.todos",
}

PARENT_LINK_QUERIES = {
    # source_table → (legacy parent column, parent legacy prefix, parent source_table)
    'features':    ('parent_feature_id', 'F',  'features'),
    'build_tasks': ('feature_id',         'F',  'features'),
}


def already_backfilled_codes(cur) -> set[str]:
    cur.execute(
        "SELECT short_code FROM claude.work_item_code_history WHERE valid_to IS NULL"
    )
    return {r['short_code'] for r in cur.fetchall()}


def backfill(cur, *, dry_run: bool, source: str) -> dict:
    """Backfill rows from one source table. Returns counts."""
    inserted = 0
    skipped = 0
    legacy_codes_seen = already_backfilled_codes(cur)

    cur.execute(SOURCE_QUERIES[source])
    rows = cur.fetchall()

    for row in rows:
        legacy = _legacy_code(source, row)
        if legacy in legacy_codes_seen:
            skipped += 1
            continue
        if dry_run:
            inserted += 1
            continue

        payload = _row_to_work_item_payload(source, row)

        # Drop NULL values for NOT NULL DEFAULT columns so the DB default fires.
        # created_at + updated_at have NOT NULL DEFAULT now() — passing NULL violates.
        for nndef_col in ('created_at', 'updated_at'):
            if payload.get(nndef_col) is None:
                payload.pop(nndef_col, None)

        # INSERT into work_items, return the new (work_item_id, short_code).
        cols = list(payload.keys())
        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)
        values = []
        for c in cols:
            v = payload[c]
            if c == 'attributes' or c == 'plan_data':
                v = json.dumps(v) if v is not None else None
            values.append(v)

        cur.execute(
            f"INSERT INTO claude.work_items ({col_list}) "
            f"VALUES ({placeholders}) RETURNING work_item_id, short_code",
            values,
        )
        wi = cur.fetchone()

        # code_history: canonical W### + legacy
        note = f"backfilled from {source}"
        cur.execute(
            "INSERT INTO claude.work_item_code_history "
            "(work_item_id, short_code, code_kind, notes) "
            "VALUES (%s, %s, 'canonical', %s), "
            "       (%s, %s, 'legacy',    %s)",
            (wi['work_item_id'], f"W{wi['short_code']}", note,
             wi['work_item_id'], legacy,                  note),
        )
        inserted += 1

    return {'source': source, 'inserted': inserted, 'skipped': skipped, 'total_rows': len(rows)}


def link_parents(cur, *, dry_run: bool) -> dict:
    """Pass 2: set work_items.parent_id from legacy parent_feature_id / feature_id."""
    relinked = 0
    for source, (parent_col, parent_prefix, _parent_source) in PARENT_LINK_QUERIES.items():
        cur.execute(
            f"""
            SELECT src.{ {'features': 'feature_id', 'build_tasks': 'task_id'}[source] }::text AS old_self_id,
                   src.{parent_col}::text AS old_parent_id,
                   wi_self.work_item_id::text  AS new_self_id,
                   wi_parent.work_item_id::text AS new_parent_id
              FROM claude.{source}                       AS src
              JOIN claude.work_item_code_history AS h_self
                ON h_self.short_code = '{ {'features': 'F', 'build_tasks': 'BT'}[source] }' || src.short_code
                AND h_self.code_kind = 'legacy'
              JOIN claude.work_items AS wi_self
                ON wi_self.work_item_id = h_self.work_item_id
              LEFT JOIN claude.features AS pfeat ON pfeat.feature_id = src.{parent_col}
              LEFT JOIN claude.work_item_code_history AS h_parent
                ON h_parent.short_code = 'F' || pfeat.short_code AND h_parent.code_kind = 'legacy'
              LEFT JOIN claude.work_items AS wi_parent
                ON wi_parent.work_item_id = h_parent.work_item_id
             WHERE src.{parent_col} IS NOT NULL
            """
        )
        rows = cur.fetchall()
        for r in rows:
            if not r['new_parent_id']:
                continue
            if dry_run:
                relinked += 1
                continue
            cur.execute(
                "UPDATE claude.work_items SET parent_id=%s::uuid "
                "WHERE work_item_id=%s::uuid AND (parent_id IS NULL OR parent_id <> %s::uuid)",
                (r['new_parent_id'], r['new_self_id'], r['new_parent_id']),
            )
            if cur.rowcount > 0:
                relinked += 1
    return {'relinked': relinked}


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true",
                   help="Count what would be backfilled, do not write.")
    g.add_argument("--apply", action="store_true",
                   help="Apply the backfill.")
    p.add_argument("--source", choices=list(SOURCE_QUERIES.keys()) + ['all'],
                   default='all', help="Limit to one source table.")
    args = p.parse_args()

    _load_dotenv()
    conn = connect()
    try:
        cur = conn.cursor()
        sources = list(SOURCE_QUERIES.keys()) if args.source == 'all' else [args.source]

        results = []
        for src in sources:
            r = backfill(cur, dry_run=args.dry_run, source=src)
            results.append(r)
            print(f"[{src}] inserted={r['inserted']} skipped={r['skipped']} total={r['total_rows']}")

        link = link_parents(cur, dry_run=args.dry_run)
        print(f"[parents] relinked={link['relinked']}")

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
