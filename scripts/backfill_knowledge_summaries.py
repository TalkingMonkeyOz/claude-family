#!/usr/bin/env python3
"""Backfill claude.knowledge.summary using first-sentence heuristic.

Idempotent: only writes rows where summary IS NULL. Re-running is safe.
Non-destructive: never overwrites existing summaries.

Heuristic: first sentence of description, capped at 200 chars. If first
sentence < 30 chars, take first 200 chars of the body. Strips markdown
headers, code-fence lines, and collapses whitespace.

Usage:
    python backfill_knowledge_summaries.py [--dry-run] [--limit N]
"""
import argparse
import os
import re
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri

import psycopg2

MAX_LEN = 200
MIN_FIRST_SENTENCE = 30


def first_sentence_summary(description: str) -> Optional[str]:
    if not description:
        return None
    text = description.strip()
    # Strip markdown headers + code fences from prefix
    lines = [ln for ln in text.split("\n")
             if not ln.lstrip().startswith(("#", "```", "---"))]
    text = " ".join(lines).strip()
    if not text:
        return None
    text = re.sub(r"\s+", " ", text)
    # First sentence: ". " or end of text
    m = re.search(r"(.+?[.!?])\s", text)
    if m and len(m.group(1)) >= MIN_FIRST_SENTENCE:
        candidate = m.group(1)
    else:
        candidate = text
    if len(candidate) > MAX_LEN:
        candidate = candidate[:MAX_LEN].rsplit(" ", 1)[0] + "…"
    return candidate.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    conn = psycopg2.connect(get_database_uri())
    cur = conn.cursor()
    cur.execute(
        """
        SELECT knowledge_id, description
        FROM claude.knowledge
        WHERE summary IS NULL
          AND description IS NOT NULL
          AND length(description) > 0
        """ + (f" LIMIT {args.limit}" if args.limit else "")
    )
    rows = cur.fetchall()
    print(f"Found {len(rows)} knowledge rows needing summary")
    if not rows:
        return 0

    written = 0
    skipped = 0
    samples: list[tuple[str, str]] = []
    for kid, desc in rows:
        summary = first_sentence_summary(desc)
        if not summary or len(summary) < 20:
            skipped += 1
            continue
        if not args.dry_run:
            cur.execute(
                "UPDATE claude.knowledge SET summary = %s "
                "WHERE knowledge_id = %s AND summary IS NULL",  # idempotency guard
                (summary, kid),
            )
        if len(samples) < 5:
            samples.append((str(kid)[:8], summary))
        written += 1

    if not args.dry_run:
        conn.commit()
    cur.close()
    conn.close()

    print(f"{'WOULD WRITE' if args.dry_run else 'Wrote'} {written} summaries; skipped {skipped}")
    print("Samples:")
    for kid, s in samples:
        print(f"  {kid}: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
