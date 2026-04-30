"""FB408: Backfill claude.workfile_sections for existing workfiles.

Splits each active workfile's content on `^## ` H2 headers and writes one
section row per part with its own body-weighted embedding. Body-shaped queries
(e.g. literal phrases buried in long workfiles) can then surface the right
workfile + section_id without being drowned out by the title-prefixed
project_workfiles.embedding.

Idempotent: per-workfile delete-then-insert. Safe to re-run. Skips workfiles
with fewer than 2 H2 headers (no body-weighted gain over the title embedding).

Usage:
    python scripts/backfill_workfile_sections.py
    python scripts/backfill_workfile_sections.py --project nimbus-mui
    python scripts/backfill_workfile_sections.py --workfile-id 0c1bf9aa-...
    python scripts/backfill_workfile_sections.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri
from embedding_provider import embed_batch, get_provider_info

import psycopg
from psycopg.rows import dict_row


H2_PATTERN = re.compile(r'(?m)^##\s')


def split_on_h2(content: str, target_lines: int = 400) -> List[Tuple[str, str]]:
    """Mirror of server._split_on_h2 (kept in sync — see server.py:1214).

    Returns list of (slug, body) pairs. Falls back to size-based part-N slugs
    when fewer than 2 H2 headers are present.
    """
    lines = content.split('\n')
    h2_indices = [i for i, ln in enumerate(lines) if re.match(r'^##\s', ln)]
    if len(h2_indices) >= 2:
        parts: List[Tuple[str, str]] = []
        if h2_indices[0] > 0:
            preamble = '\n'.join(lines[:h2_indices[0]]).strip()
            if preamble:
                parts.append(("intro", preamble))
        for idx, start in enumerate(h2_indices):
            end = h2_indices[idx + 1] if idx + 1 < len(h2_indices) else len(lines)
            section_lines = lines[start:end]
            header = section_lines[0].lstrip('#').strip()
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', header).strip().lower()
            slug = re.sub(r'\s+', '-', slug)[:50] or f"section-{idx + 1}"
            body = '\n'.join(section_lines).strip()
            parts.append((slug, body))
        return parts
    parts = []
    for idx in range(0, len(lines), target_lines):
        chunk = '\n'.join(lines[idx:idx + target_lines]).strip()
        if chunk:
            parts.append((f"part-{len(parts) + 1}", chunk))
    return parts


def fetch_workfiles(conn, project: str | None, workfile_id: str | None) -> List[dict]:
    sql = """
        SELECT w.workfile_id::text AS workfile_id,
               w.title, w.content, p.project_name
        FROM claude.project_workfiles w
        JOIN claude.projects p ON p.project_id = w.project_id
        WHERE w.is_active = true
    """
    params: list = []
    if project:
        sql += " AND p.project_name = %s"
        params.append(project)
    if workfile_id:
        sql += " AND w.workfile_id = %s::uuid"
        params.append(workfile_id)
    sql += " ORDER BY p.project_name, w.component, w.title"
    return conn.execute(sql, params).fetchall()


def backfill(project: str | None, workfile_id: str | None, dry_run: bool, batch_size: int = 32) -> None:
    pinfo = get_provider_info()
    embed_model = f"{pinfo.get('provider', '')}:{pinfo.get('model', '')}"
    print(f"[backfill] Embedding provider: {embed_model}")

    db_uri = get_database_uri()
    with psycopg.connect(db_uri, row_factory=dict_row) as conn:
        rows = fetch_workfiles(conn, project, workfile_id)
        print(f"[backfill] {len(rows)} active workfiles to process")

        total_sections = 0
        total_skipped = 0
        for i, w in enumerate(rows, 1):
            content = w['content'] or ''
            wf_id = w['workfile_id']
            h2_count = len(H2_PATTERN.findall(content))

            if h2_count < 2:
                # Still purge any stale section rows so re-running this
                # backfill always converges to a clean state.
                if not dry_run:
                    conn.execute(
                        "DELETE FROM claude.workfile_sections WHERE workfile_id = %s::uuid",
                        (wf_id,),
                    )
                    conn.commit()
                total_skipped += 1
                if i % 50 == 0:
                    print(f"[backfill] processed {i}/{len(rows)} (skipped {total_skipped})")
                continue

            parts = split_on_h2(content)
            if len(parts) < 2:
                total_skipped += 1
                continue

            if dry_run:
                # Skip the (expensive) embedding call entirely on dry runs.
                print(
                    f"[dry-run] {w['project_name']}/{w['title']} -> "
                    f"{len(parts)} sections (slugs={[p[0] for p in parts]})"
                )
                total_sections += len(parts)
                continue

            # Embed bodies in a batch for efficiency
            bodies = [body[:2000] for _, body in parts]
            embeddings = embed_batch(bodies)

            try:
                # Idempotent: delete-then-insert per workfile
                conn.execute(
                    "DELETE FROM claude.workfile_sections WHERE workfile_id = %s::uuid",
                    (wf_id,),
                )
                for idx, ((slug, body), emb) in enumerate(zip(parts, embeddings)):
                    title = slug.replace('-', ' ').strip()
                    first_line = body.split('\n', 1)[0].strip() if body else ''
                    if first_line.startswith('##'):
                        title = first_line.lstrip('#').strip()
                    conn.execute(
                        """
                        INSERT INTO claude.workfile_sections
                            (workfile_id, section_order, section_slug, section_title,
                             section_body, embedding, embedding_model, updated_at)
                        VALUES (%s::uuid, %s, %s, %s, %s, %s::vector, %s, NOW())
                        """,
                        (wf_id, idx, slug, title, body, emb, embed_model),
                    )
                conn.commit()
                total_sections += len(parts)
            except Exception as e:
                conn.rollback()
                print(f"[backfill] FAILED workfile_id={wf_id}: {e}", file=sys.stderr)

            if i % 25 == 0:
                print(f"[backfill] processed {i}/{len(rows)} (+{total_sections} sections)")

        action = "would insert" if dry_run else "inserted"
        print(
            f"[backfill] DONE: {action} {total_sections} section rows; "
            f"skipped {total_skipped} workfiles (<2 H2 headers)."
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", default=None, help="Limit to a single project (e.g. nimbus-mui).")
    ap.add_argument("--workfile-id", default=None, help="Limit to a single workfile_id.")
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen, don't write.")
    args = ap.parse_args()
    backfill(args.project, args.workfile_id, args.dry_run)
