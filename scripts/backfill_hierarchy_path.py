#!/usr/bin/env python3
"""Back-fill claude.knowledge.path and claude.entities.path.

Conservative two-level taxonomy: `{project}.{type}`. Leaves parent_id NULL
because we don't have project entities materialised yet — that's a follow-up.

Idempotent: only writes rows where path IS NULL.
Non-destructive: never overwrites existing paths.

Path rules:
  knowledge.path = "{project_slug}.{knowledge_type}" or "{project_slug}.knowledge"
  entities.path  = "{project_slug}.{entity_type_name}"

Project slug derivation:
  - knowledge.applies_to_projects: if cardinality==1, use that. If contains 'all',
    use 'global'. If multi, use the FIRST project (deterministic). If NULL, 'orphan'.
  - entities.project_id: lookup claude.projects.project_name.

Usage:
    python backfill_hierarchy_path.py [--dry-run] [--limit N] [--store knowledge|entities|both]
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri

import psycopg2

PROJECT_NAME_RE = re.compile(r"[^a-z0-9]+")


def slug(s: str) -> str:
    return PROJECT_NAME_RE.sub("-", (s or "unknown").lower()).strip("-")


def backfill_knowledge(cur, dry_run: bool, limit: int) -> int:
    sql = """
        SELECT knowledge_id, applies_to_projects, knowledge_type
        FROM claude.knowledge
        WHERE path IS NULL
    """ + (f" LIMIT {limit}" if limit else "")
    cur.execute(sql)
    rows = cur.fetchall()
    print(f"[knowledge] {len(rows)} rows need path")
    if not rows:
        return 0
    written = 0
    for kid, projects, ktype in rows:
        if not projects:
            project_slug = "orphan"
        elif "all" in projects:
            project_slug = "global"
        elif len(projects) == 1:
            project_slug = slug(projects[0])
        else:
            project_slug = slug(projects[0])  # deterministic first
        type_slug = slug(ktype) if ktype else "knowledge"
        path = f"{project_slug}.{type_slug}"
        if not dry_run:
            cur.execute(
                "UPDATE claude.knowledge SET path = %s WHERE knowledge_id = %s AND path IS NULL",
                (path, kid),
            )
        written += 1
    print(f"[knowledge] {'WOULD WRITE' if dry_run else 'wrote'} {written} paths")
    return written


def backfill_entities(cur, dry_run: bool, limit: int) -> int:
    sql = """
        SELECT e.entity_id, p.project_name, et.type_name
        FROM claude.entities e
        LEFT JOIN claude.projects p ON p.project_id = e.project_id
        LEFT JOIN claude.entity_types et ON et.type_id = e.entity_type_id
        WHERE e.path IS NULL
    """ + (f" LIMIT {limit}" if limit else "")
    cur.execute(sql)
    rows = cur.fetchall()
    print(f"[entities] {len(rows)} rows need path")
    if not rows:
        return 0
    written = 0
    for eid, project, etype in rows:
        project_slug = slug(project) if project else "orphan"
        type_slug = slug(etype) if etype else "entity"
        path = f"{project_slug}.{type_slug}"
        if not dry_run:
            cur.execute(
                "UPDATE claude.entities SET path = %s WHERE entity_id = %s AND path IS NULL",
                (path, eid),
            )
        written += 1
    print(f"[entities] {'WOULD WRITE' if dry_run else 'wrote'} {written} paths")
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--store", choices=["knowledge", "entities", "both"], default="both")
    args = ap.parse_args()

    conn = psycopg2.connect(get_database_uri())
    cur = conn.cursor()
    total = 0
    if args.store in ("knowledge", "both"):
        total += backfill_knowledge(cur, args.dry_run, args.limit)
    if args.store in ("entities", "both"):
        total += backfill_entities(cur, args.dry_run, args.limit)
    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()

    print(f"\nTotal: {total} rows back-filled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
