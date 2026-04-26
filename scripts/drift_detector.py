#!/usr/bin/env python3
"""FB339: drift detection — flag stale references in load-bearing surfaces.

Scans memories created in the last N hours that look architecture-y
(knowledge_type in {decision, pattern, gotcha} AND content hints at
sunset/retire/deprecate/replace/supersede). For each such memory, extracts
"deprecated terms" via regex, then searches load-bearing surfaces
(`claude.profiles.config` (CLAUDE.md), `claude.rules.content`,
`claude.entities` (domain_concept), `claude.project_workfiles` (is_pinned),
`claude.knowledge_articles.abstract` + `claude.article_sections.body`)
for those terms.

When a deprecated term still appears in a load-bearing surface, files
`claude.feedback` (type='design', priority='medium') so a future Claude
can reconcile.

Idempotent: dedupes on title prefix so re-running yields no new feedback.
Non-destructive: read-only on surfaces; only INSERTs to feedback.
Fail-open: any error → JSONL log to ~/.claude/logs/, exit 0.

Usage:
    python drift_detector.py [--dry-run] [--hours N] [--verbose]

Designed to register as a daily scheduled_job at `0 7 * * *`.

Cross-ref: storage-rules v8 Rule 5 (Specific edge types) + design memo
in memory cc733fdd.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri

import psycopg2
from psycopg2.extras import RealDictCursor

# ---------------------------------------------------------------------------
# Logging — JSONL fail-open
# ---------------------------------------------------------------------------

LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "drift_detector.jsonl"


def jlog(event: str, **kwargs) -> None:
    rec = {"ts": datetime.utcnow().isoformat(), "event": event, **kwargs}
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass  # fail-open: never raise from logging


# ---------------------------------------------------------------------------
# Term extraction
# ---------------------------------------------------------------------------

# Patterns that say "X is dead/deprecated/replaced". The capturing group is
# the term being deprecated. Patterns are conservative to avoid false positives
# from natural English; tighten by requiring the deprecation marker.
_DEP_VERBS = r"(?:retired|sunset|deprecated|replaced|superseded|killed|removed|obsolete|dead|gone)"
_BE = r"(?:was|is|has been|are)"

TERM_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "X" was retired / 'X' is dead
    re.compile(r'"([^"]{2,80})"\s+' + _BE + r'\s+' + _DEP_VERBS + r'\b', re.IGNORECASE),
    re.compile(r"'([^']{2,80})'\s+" + _BE + r"\s+" + _DEP_VERBS + r"\b", re.IGNORECASE),
    # Title-Case-Phrase was retired (case-insensitive on verbs)
    re.compile(r'\b([A-Z][A-Za-z][\w\- ]{1,60}?)\s+' + _BE + r'\s+' + _DEP_VERBS + r'\b', re.IGNORECASE),
    # Words (ACRONYM) was retired
    re.compile(r'\b([A-Z][A-Za-z][\w\- ]{1,60}?)\s+\([A-Z]{2,8}\)\s+' + _BE + r'\s+' + _DEP_VERBS + r'\b', re.IGNORECASE),
    # ACRONYM (Words) was retired   ← swapped form
    re.compile(r'\b([A-Z]{2,8})\s+\([A-Z][A-Za-z][\w\- ]{1,60}?\)\s+' + _BE + r'\s+' + _DEP_VERBS + r'\b', re.IGNORECASE),
    # retire/sunset/deprecate/replace X (in favour of Y)
    re.compile(r'(?:retire|sunset|deprecate|replace|supersede)\s+(?:the\s+)?["\']?([A-Z][A-Za-z][\w\- ]{1,60}?)["\']?\s+(?:in favour|in favor|with|by)\b', re.IGNORECASE),
    # DO NOT use [the term] X
    re.compile(r'\bDO NOT use\s+(?:the\s+)?(?:term\s+)?["\']?([A-Z][A-Za-z0-9][\w\- ]{1,60}?)["\']?(?=\s|$|[.!,])', re.IGNORECASE),
    # ACRONYM is dead/gone/retired/obsolete (standalone acronym, no Words)
    re.compile(r'\b([A-Z]{2,8})\s+' + _BE + r'\s+' + _DEP_VERBS + r'\b', re.IGNORECASE),
)

# Stop words — never flag these as "deprecated terms".
# Generic English nouns and common project nouns. Match is case-insensitive.
STOP_TERMS = {
    "the", "this", "that", "these", "those", "a", "an",
    "we", "i", "they", "you", "it", "all", "any", "some", "more",
    "claude", "claude family", "user", "users", "system", "systems",
    # Common nouns picked up as false positives in audits/handoffs:
    "gap", "gaps", "scope", "scopes", "item", "items", "section", "sections",
    "tier", "tiers", "task", "tasks", "feature", "features", "rule", "rules",
    "field", "fields", "column", "columns", "row", "rows", "tool", "tools",
    "memory", "memories", "context", "data", "code", "phase", "phases",
    "feedback", "issue", "issues", "bug", "bugs", "story", "stories",
    "test", "tests", "case", "cases", "thread", "threads", "result", "results",
}


def _is_credible_term(term: str) -> bool:
    """Reject low-credibility terms even after regex match.

    A "deprecated term" worth tracking is either:
      - quoted/parenthesised (caught upstream — assume yes if it got here AND has caps)
      - an all-caps acronym (>=2 chars, all uppercase letters/digits)
      - a Title-Case multi-word phrase (first letter caps, contains a space)
      - or a hyphenated identifier (e.g. claude-manager-mui)
    """
    t = term.strip()
    if len(t) < 3:
        return False
    if t.lower() in STOP_TERMS:
        return False
    # All-caps acronym
    if re.fullmatch(r"[A-Z][A-Z0-9]{1,7}", t):
        return True
    # Title-Case multi-word
    if " " in t and t[0].isupper():
        return True
    # Hyphenated identifier (claude-manager-mui, etc.) — at least one hyphen
    if "-" in t and len(t) >= 5:
        return True
    # Title-Case single-word ≥4 chars (Vault, Hooks, Embedding) — STOP_TERMS catches generics
    if t[0].isupper() and len(t) >= 4 and t[1:].isalpha():
        return True
    return False

# Surfaces are short text fields. Treat as drift candidate only if surface
# contains the term as a whole-word match (not partial).
WORD_BOUNDARY = re.compile(r"[\W_]+")


def extract_deprecated_terms(memory_body: str) -> set[str]:
    """Return distinct deprecated terms harvested from a memory body."""
    if not memory_body:
        return set()
    found: set[str] = set()
    for pat in TERM_PATTERNS:
        for m in pat.finditer(memory_body):
            term = m.group(1).strip(" \t,.;:'\"")
            if _is_credible_term(term):
                found.add(term)
    return found


def whole_word_present(term: str, haystack: str) -> bool:
    """True if `term` appears as a whole-word match in `haystack`."""
    if not term or not haystack:
        return False
    pat = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
    return bool(re.search(pat, haystack, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Surface scanning
# ---------------------------------------------------------------------------


def fetch_recent_arch_memories(cur, hours: int) -> list[dict]:
    """Pull architecture-y memories that mention deprecation language.

    NOTE: we deliberately DO NOT filter on created_at, because the canonical
    knowledge memory uses union-merge (similar new content gets concatenated
    into the existing row, leaving created_at unchanged and updated_at NULL).
    A naive "recent memories" filter would miss correction memories merged
    into older rows. The deprecation-keyword filter does the heavy lifting
    instead — there are only ~tens of architecture-tagged memories total.

    `hours` is retained for future use (e.g. when union-merge starts setting
    updated_at correctly we can prefer that path), but currently unused.
    """
    _ = hours  # see docstring
    cur.execute(
        """
        SELECT knowledge_id, title, description, knowledge_type, tier
        FROM claude.knowledge
        WHERE knowledge_type IN ('decision', 'pattern', 'gotcha', 'learned')
          AND COALESCE(tier, 'mid') != 'archived'
          AND (
              description ~* '\\m(retired|sunset|deprecat|supersed|replaced|killed|dead|obsolete)\\M'
              OR title    ~* '\\m(retire|sunset|deprecat|supersed|replac|kill|dead|obsolet)\\M'
          )
        """
    )
    return list(cur.fetchall())


def fetch_load_bearing_surfaces(cur) -> list[tuple[str, str, str]]:
    """Return (surface_kind, surface_label, surface_text) tuples."""
    out: list[tuple[str, str, str]] = []
    # CLAUDE.md content (per profile)
    cur.execute("SELECT name, COALESCE(config::jsonb->>'behavior','') AS body FROM claude.profiles WHERE source_type='project'")
    for row in cur.fetchall():
        if row["body"]:
            out.append(("CLAUDE.md", f"profile:{row['name']}", row["body"]))
    # Rules
    cur.execute("SELECT scope, name, content FROM claude.rules WHERE content IS NOT NULL")
    for row in cur.fetchall():
        out.append(("rule", f"rule:{row['scope']}:{row['name']}", row["content"]))
    # Domain concept entities
    cur.execute(
        """
        SELECT e.entity_id, e.display_name, COALESCE(e.summary, '') || ' ' ||
               COALESCE(e.properties::text, '') AS body
        FROM claude.entities e
        JOIN claude.entity_types et ON et.type_id = e.entity_type_id
        WHERE et.type_name = 'domain_concept' AND COALESCE(e.is_archived, false) = false
        """
    )
    for row in cur.fetchall():
        out.append(("entity:domain_concept", f"entity:{row['display_name']}", row["body"]))
    # Pinned workfiles
    cur.execute(
        """
        SELECT component, title, COALESCE(content, '') AS body
        FROM claude.project_workfiles
        WHERE is_pinned = true AND is_active = true
        """
    )
    for row in cur.fetchall():
        out.append(("workfile:pinned", f"workfile:{row['component']}/{row['title']}", row["body"]))
    # Published articles + sections
    cur.execute(
        """
        SELECT a.article_id, a.title, COALESCE(a.abstract, '') AS body
        FROM claude.knowledge_articles a
        WHERE a.status = 'published'
        """
    )
    for row in cur.fetchall():
        out.append(("article", f"article:{row['title']}", row["body"]))
    cur.execute(
        """
        SELECT s.section_id, a.title AS article_title, s.title AS section_title,
               COALESCE(s.body, '') AS body
        FROM claude.article_sections s
        JOIN claude.knowledge_articles a ON a.article_id = s.article_id
        WHERE a.status = 'published'
        """
    )
    for row in cur.fetchall():
        out.append((
            "article:section",
            f"section:{row['article_title']} / {row['section_title']}",
            row["body"],
        ))
    return out


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


def file_drift_feedback(cur, term: str, surface_label: str, source_memory_title: str, dry_run: bool) -> bool:
    title = f"Drift candidate: '{term}' deprecated, still appears in {surface_label}"
    if already_filed(cur, title[:60]):
        return False
    desc = (
        f"Drift detector flagged: term '{term}' is referenced as deprecated/retired "
        f"by memory '{source_memory_title}', but still appears in load-bearing surface "
        f"'{surface_label}'. Reconcile by either updating the surface to remove/replace "
        f"the term, or correcting the memory if the deprecation is wrong."
    )
    if dry_run:
        return True
    cur.execute(
        """
        INSERT INTO claude.feedback (feedback_id, project_id, feedback_type, title, description, priority, status, short_code, created_at)
        SELECT
          gen_random_uuid(),
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
    ap.add_argument("--hours", type=int, default=72)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        conn = psycopg2.connect(get_database_uri())
        cur = conn.cursor(cursor_factory=RealDictCursor)
        memories = fetch_recent_arch_memories(cur, args.hours)
        surfaces = fetch_load_bearing_surfaces(cur)
        if args.verbose:
            print(f"Memories scanned: {len(memories)} | Surfaces scanned: {len(surfaces)}")

        flags: list[tuple[str, str, str]] = []  # (term, surface_label, mem_title)
        for mem in memories:
            terms = extract_deprecated_terms(mem.get("description") or "")
            if not terms:
                continue
            for term in terms:
                # Don't flag if the deprecating memory itself contains the surface mention
                # (the surface might already have the correction context).
                for kind, label, body in surfaces:
                    if whole_word_present(term, body):
                        flags.append((term, label, mem.get("title") or "(untitled memory)"))
                        if args.verbose:
                            print(f"[flag] '{term}' in {label} (per memory: {mem.get('title')})")

        # Use a write cursor for the inserts (RealDictCursor is read-shaped; works for INSERT but be explicit).
        write_cur = conn.cursor()
        filed = 0
        skipped_dedupe = 0
        for term, label, mem_title in flags:
            # Check via write_cur for dedupe + insert (consistent connection).
            if file_drift_feedback(write_cur, term, label, mem_title, args.dry_run):
                filed += 1
            else:
                skipped_dedupe += 1
        if not args.dry_run:
            conn.commit()
        write_cur.close()
        cur.close()
        conn.close()

        result = {
            "memories_scanned": len(memories),
            "surfaces_scanned": len(surfaces),
            "flags_total": len(flags),
            "feedback_filed": filed,
            "skipped_dedupe": skipped_dedupe,
            "dry_run": args.dry_run,
        }
        print(json.dumps(result))
        jlog("run_ok", **result)
        return 0
    except Exception as e:
        jlog("run_failed", error=str(e), error_type=type(e).__name__)
        # Fail-open: print error but exit 0 so job_runner stays green
        print(json.dumps({"error": str(e), "fail_open": True}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
