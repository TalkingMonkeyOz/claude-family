#!/usr/bin/env python3
"""Shape-Parity Check (task #873).

Scheduled job (daily) implementing knowledge_construction_process.bpmn Rule 1.

Compares the column sets of the three atomic knowledge stores:

    claude.knowledge
    claude.entities
    claude.article_sections

For every column that appears in exactly 2 of the 3 stores, files a feedback
row of type='bug' priority='medium' titled
"Shape drift: column <col> on <stores>, missing on <store>".

Rerun-safe: an open feedback row covering the same column+missing-store is
not duplicated.

Run output is logged to `claude.scheduled_jobs.last_output` as JSON:
    {"checked": N_columns, "drifts": M, "feedback_filed": K}

Fail-open: any error is captured to ~/.claude/logs/shape_parity_check.jsonl
and the script exits 0 so the job runner stays green.

Usage:
    python shape_parity_check.py [--dry-run] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
FAIL_LOG = LOG_DIR / "shape_parity_check.jsonl"

# Atomic stores being compared
STORES = ("knowledge", "entities", "article_sections")

# Columns that are intrinsically per-store (PK, FK, store-specific) and
# therefore should NOT be flagged as shape drift even when only present in
# some of the stores.
INTRINSIC_PER_STORE = {
    # Primary keys
    "knowledge_id", "entity_id", "section_id",
    # Store-specific FKs / structural columns
    "article_id", "section_order",
    "entity_type_id", "search_vector",
    "linked_entity_ids",
    "learned_by_identity_id",
    "consolidated_into",
    "knowledge_type", "knowledge_category",
    "applies_to_projects", "applies_to_platforms",
    "code_example", "related_knowledge",
    "times_applied", "times_failed", "last_applied_at",
    "confidence_level",  # knowledge-only — entities uses 'confidence'
    "tier", "source",
    "archived_at", "archived_reason", "archived_by",
    "display_name",  # entities-only — knowledge/sections use 'title'
    "properties",  # entities-only structured payload
    "is_archived",  # entities-only — knowledge uses 'status' enum
    "version",  # article_sections only
    # Display/title fields differ by name across stores
    "title",
}


def _capture_failure(stage, exc):
    """Write a fail-open JSONL log entry."""
    try:
        with FAIL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "script": "shape_parity_check",
                "stage": stage,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=5),
            }) + "\n")
    except Exception:
        pass


def _connect():
    """Return a psycopg2 connection (RealDictCursor)."""
    import psycopg2
    import psycopg2.extras
    try:
        from config import get_database_uri
        uri = get_database_uri()
    except Exception:
        uri = os.environ.get("DATABASE_URI") or os.environ.get("DATABASE_URL")
    if not uri:
        raise RuntimeError("No DATABASE_URI/DATABASE_URL configured")
    conn = psycopg2.connect(uri, connect_timeout=10)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


def gather_columns(conn):
    """Return {table_name: set(column_names)} for the three atomic stores."""
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'claude'
          AND table_name = ANY(%s)
    """, (list(STORES),))
    out = {t: set() for t in STORES}
    for row in cur.fetchall():
        t = row["table_name"]
        c = row["column_name"]
        if t in out:
            out[t].add(c)
    cur.close()
    return out


def find_drifts(cols_by_table):
    """Return list of dicts: {column, present_on: [..], missing_on: store}.

    Only flags columns present in exactly 2 of the 3 stores AND not in the
    intrinsic-per-store ignore list.
    """
    all_cols = set()
    for cols in cols_by_table.values():
        all_cols |= cols

    drifts = []
    for col in sorted(all_cols):
        if col in INTRINSIC_PER_STORE:
            continue
        present = [t for t in STORES if col in cols_by_table.get(t, set())]
        if len(present) == 2:
            missing = [t for t in STORES if t not in present][0]
            drifts.append({
                "column": col,
                "present_on": present,
                "missing_on": missing,
            })
    return drifts


def _feedback_title(drift):
    return "Shape drift: column {} on {}, missing on {}".format(
        drift["column"],
        "+".join(drift["present_on"]),
        drift["missing_on"],
    )


def already_filed(conn, drift):
    """Return True if an OPEN feedback row already covers this exact drift."""
    cur = conn.cursor()
    # Match on the unique signature: column name + missing-store. We don't
    # require the present_on order to match because that's noise.
    title_pattern = "Shape drift: column {} on %, missing on {}".format(
        drift["column"], drift["missing_on"]
    )
    cur.execute("""
        SELECT 1 FROM claude.feedback
        WHERE title ILIKE %s
          AND (status IS NULL OR status NOT IN ('resolved', 'wont_fix', 'duplicate'))
        LIMIT 1
    """, (title_pattern,))
    found = cur.fetchone() is not None
    cur.close()
    return found


def file_feedback(conn, project_id, drift):
    """Insert a single feedback row. Returns True if inserted."""
    cur = conn.cursor()
    title = _feedback_title(drift)
    description = (
        "Column '{col}' is present on {present} but missing on "
        "claude.{missing}. This violates shape parity (BPMN rule 1) for the "
        "atomic knowledge stores.\n\n"
        "Detected by: scripts/shape_parity_check.py\n\n"
        "Action: either add the column to claude.{missing} (preferred — "
        "narrows the gap) or remove it from {present} (only if the column "
        "was added by mistake)."
    ).format(
        col=drift["column"],
        present=", ".join("claude." + t for t in drift["present_on"]),
        missing=drift["missing_on"],
    )
    try:
        cur.execute("""
            INSERT INTO claude.feedback
                (feedback_id, project_id, feedback_type, priority, status,
                 title, description, created_at, updated_at, assigned_to)
            VALUES (gen_random_uuid(), %s, 'bug', 'medium', 'new',
                    %s, %s, NOW(), NOW(), 'claude-family')
            RETURNING feedback_id
        """, (project_id, title[:500], description))
        cur.fetchone()
        cur.close()
        return True
    except Exception as exc:
        cur.close()
        _capture_failure("file_feedback", exc)
        return False


def _resolve_project_id(conn):
    cur = conn.cursor()
    cur.execute("SELECT project_id FROM claude.projects WHERE project_name = 'claude-family'")
    row = cur.fetchone()
    cur.close()
    if not row:
        raise RuntimeError("project 'claude-family' not found")
    return str(row["project_id"])


def run(dry_run=False, verbose=False):
    """Main entry point. Returns the summary dict."""
    summary = {"checked_columns": 0, "drifts": 0, "feedback_filed": 0, "dry_run": dry_run}
    conn = _connect()
    try:
        project_id = _resolve_project_id(conn)
        cols_by_table = gather_columns(conn)

        all_cols = set()
        for cols in cols_by_table.values():
            all_cols |= cols
        summary["checked_columns"] = len(all_cols)

        drifts = find_drifts(cols_by_table)
        summary["drifts"] = len(drifts)

        for drift in drifts:
            if already_filed(conn, drift):
                if verbose:
                    print("[dup] feedback exists for column '{}' missing on {}".format(
                        drift["column"], drift["missing_on"]))
                continue
            if dry_run:
                if verbose:
                    print("[dry-run] would file:", _feedback_title(drift))
                continue
            if file_feedback(conn, project_id, drift):
                summary["feedback_filed"] += 1
                if verbose:
                    print("[filed]", _feedback_title(drift))

        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Do not insert feedback")
    ap.add_argument("--verbose", action="store_true", help="Print per-drift log")
    args = ap.parse_args()

    try:
        summary = run(dry_run=args.dry_run, verbose=args.verbose)
        print(json.dumps(summary))
        return 0
    except Exception as exc:
        _capture_failure("main", exc)
        print(json.dumps({
            "checked_columns": 0, "drifts": 0, "feedback_filed": 0,
            "error": str(exc),
        }))
        return 0


if __name__ == "__main__":
    sys.exit(main())
