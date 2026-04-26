#!/usr/bin/env python3
"""MOC Promise-Fulfilment Check (task #872).

Scheduled job (daily) implementing knowledge_construction_process.bpmn Rule 3.

Scans `claude.knowledge_articles.abstract` and `claude.article_sections.body`
for prose patterns that promise the existence of another article (e.g.
"see article: X", "see X article", "(see Y article)"). For each promised
article name:

  1. Search `claude.knowledge_articles` by title (trigram, threshold 0.5).
  2. If no fuzzy match -> file `claude.feedback` row of type='design'
     priority='medium' titled
     "MOC promise unfulfilled: <X> referenced by <parent>".
  3. Dedupe on title prefix so re-runs do not stack feedback.

Run output is logged to `claude.scheduled_jobs.last_output` as JSON:
    {"checked": N, "unfulfilled": M, "feedback_filed": K}

Fail-open: any error is captured to ~/.claude/logs/moc_promise_check.jsonl
and the script exits 0 so the job runner stays green.

Usage:
    python moc_promise_check.py [--dry-run] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
FAIL_LOG = LOG_DIR / "moc_promise_check.jsonl"

# Patterns that look like MOC promises in prose. Each pattern's first capture
# group is the promised article name. We deliberately avoid greedy matches that
# span sentences; promised names are at most ~80 chars and stop at common
# delimiters.
# Title-Case-ish word stream: a Capitalized word possibly followed by more
# Capitalized words / hyphenated tokens / em-dashes / digits. Stops at the
# first lowercase-leading word so "Hook Architecture for the wiring"
# captures only "Hook Architecture". MUST be case-sensitive in the title
# portion (the wrapping (?-i:...) disables IGNORECASE inside the group).
_TITLE_WORDS = (
    r"(?-i:([A-Z][A-Za-z0-9][A-Za-z0-9\-]*"
    r"(?:\s+(?:[A-Z][A-Za-z0-9\-]*|[—\-+&/]|\d+))*"
    r"))"
)
# Greedy variant for "see article: ..." where colon makes intent clear.
_NAME_AFTER_COLON = r"([^\n\.;]{3,120})"
# Explicit-boundary capture: anchored on the 'article' keyword that follows.
_NAME_BEFORE_ARTICLE = r"(?-i:([A-Z][A-Za-z0-9][^\.,;:\n\)\]\"]{2,80}?))"
PROMISE_PATTERNS = [
    # "see article: Foo Bar" — colon delimits intent, take rest of clause.
    re.compile(r"see\s+article\s*:\s*" + _NAME_AFTER_COLON, re.IGNORECASE),
    # "see article Foo Bar" (no colon) — take Title Case run.
    re.compile(r"see\s+article\s+" + _TITLE_WORDS, re.IGNORECASE),
    # "(see Foo Bar article)" / "(see the Foo Bar article)" — explicit boundary on 'article'.
    re.compile(r"\(\s*see\s+(?:the\s+)?" + _NAME_BEFORE_ARTICLE + r"\s+article\s*\)", re.IGNORECASE),
    # "see the Foo Bar article" — explicit boundary on 'article'.
    re.compile(r"see\s+the\s+" + _NAME_BEFORE_ARTICLE + r"\s+article\b", re.IGNORECASE),
]

# Words/strings that are clearly not real article titles -- used to filter
# false positives the regex picks up.
NOISE = {
    "this", "that", "the", "above", "below", "previous", "next", "main",
    "linked", "any", "another", "each", "earlier", "later", "related",
}


def _capture_failure(stage, exc):
    """Write a fail-open JSONL log entry."""
    try:
        with FAIL_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "script": "moc_promise_check",
                "stage": stage,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=5),
            }) + "\n")
    except Exception:
        pass  # last resort -- never raise from logging


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


def extract_promises(text):
    """Return distinct promised article names from a prose blob."""
    if not text:
        return []
    out = []
    seen = set()
    for pat in PROMISE_PATTERNS:
        for m in pat.finditer(text):
            raw = (m.group(1) or "").strip().rstrip(".,;:!?\"'")
            # Trim trailing helper words
            raw = re.sub(r"\s+(article|articles|doc|document|docs)$", "", raw, flags=re.IGNORECASE)
            if not raw or len(raw) < 3:
                continue
            if raw.lower() in NOISE:
                continue
            key = raw.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(raw)
    return out


def gather_promises(conn):
    """Scan abstracts and section bodies for promises.

    Returns list of dicts: {parent_title, promise, source}.
    """
    promises = []
    cur = conn.cursor()

    cur.execute("""
        SELECT article_id, title, abstract
        FROM claude.knowledge_articles
        WHERE abstract IS NOT NULL AND abstract <> ''
    """)
    for row in cur.fetchall():
        for name in extract_promises(row["abstract"]):
            promises.append({
                "parent_title": row["title"],
                "promise": name,
                "source": "abstract",
                "article_id": str(row["article_id"]),
            })

    cur.execute("""
        SELECT s.section_id, s.title AS section_title, s.body,
               a.title AS article_title, a.article_id
        FROM claude.article_sections s
        JOIN claude.knowledge_articles a USING (article_id)
        WHERE s.body IS NOT NULL AND s.body <> ''
    """)
    for row in cur.fetchall():
        parent = "{} / {}".format(row["article_title"], row["section_title"])
        for name in extract_promises(row["body"]):
            promises.append({
                "parent_title": parent,
                "promise": name,
                "source": "section",
                "article_id": str(row["article_id"]),
            })

    cur.close()
    return promises


def is_fulfilled(conn, promised_name, threshold=0.5):
    """Trigram fuzzy match the promise against existing article titles.

    Falls back to ILIKE substring match if pg_trgm operator is unavailable.
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT title, similarity(LOWER(title), LOWER(%s)) AS sim
            FROM claude.knowledge_articles
            WHERE LOWER(title) %% LOWER(%s)
            ORDER BY sim DESC
            LIMIT 1
        """, (promised_name, promised_name))
        hit = cur.fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        cur.execute("""
            SELECT title FROM claude.knowledge_articles
            WHERE title ILIKE %s OR %s ILIKE '%%' || title || '%%'
            LIMIT 1
        """, ("%{}%".format(promised_name), promised_name))
        hit = cur.fetchone()
        cur.close()
        return hit is not None
    cur.close()
    if not hit:
        return False
    sim = hit.get("sim") if isinstance(hit, dict) else None
    if sim is None:
        return True
    return float(sim) >= threshold


def already_filed(conn, promise):
    """Check for an existing OPEN feedback row covering this promise."""
    cur = conn.cursor()
    title_prefix = "MOC promise unfulfilled: {}".format(promise)
    cur.execute("""
        SELECT 1 FROM claude.feedback
        WHERE title ILIKE %s
          AND (status IS NULL OR status NOT IN ('resolved', 'wont_fix', 'duplicate'))
        LIMIT 1
    """, (title_prefix + "%",))
    found = cur.fetchone() is not None
    cur.close()
    return found


def file_feedback(conn, project_id, promise, parent, source):
    """Insert a single feedback row. Returns True if inserted."""
    cur = conn.cursor()
    title = "MOC promise unfulfilled: {} referenced by {}".format(promise, parent)
    description = (
        "The article/section '{}' references a promised article '{}' "
        "(matched in {}), but no article with a similar title exists in "
        "claude.knowledge_articles.\n\n"
        "Source: {}\n"
        "Detected by: scripts/moc_promise_check.py "
        "(BPMN rule 3, MOC promise-fulfilment)\n\n"
        "Action: either create the promised article via article_write(), "
        "or edit the parent prose to remove/rephrase the reference."
    ).format(parent, promise, source, source)
    try:
        cur.execute("""
            INSERT INTO claude.feedback
                (feedback_id, project_id, feedback_type, priority, status,
                 title, description, created_at, updated_at, assigned_to)
            VALUES (gen_random_uuid(), %s, 'design', 'medium', 'new',
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
    summary = {"checked": 0, "unfulfilled": 0, "feedback_filed": 0, "dry_run": dry_run}
    conn = _connect()
    try:
        project_id = _resolve_project_id(conn)
        promises = gather_promises(conn)
        summary["checked"] = len(promises)

        for p in promises:
            promise = p["promise"]
            parent = p["parent_title"]
            source = p["source"]

            if is_fulfilled(conn, promise):
                if verbose:
                    print("[ok] '{}' fulfilled (parent: {})".format(promise, parent))
                continue

            summary["unfulfilled"] += 1

            if already_filed(conn, promise):
                if verbose:
                    print("[dup] feedback already exists for '{}'".format(promise))
                continue

            if dry_run:
                if verbose:
                    print("[dry-run] would file: '{}' (parent: {})".format(promise, parent))
                continue

            if file_feedback(conn, project_id, promise, parent, source):
                summary["feedback_filed"] += 1
                if verbose:
                    print("[filed] '{}' (parent: {})".format(promise, parent))

        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Do not insert feedback")
    ap.add_argument("--verbose", action="store_true", help="Print per-promise log")
    args = ap.parse_args()

    try:
        summary = run(dry_run=args.dry_run, verbose=args.verbose)
        print(json.dumps(summary))
        return 0
    except Exception as exc:
        _capture_failure("main", exc)
        print(json.dumps({
            "checked": 0, "unfulfilled": 0, "feedback_filed": 0,
            "error": str(exc),
        }))
        return 0


if __name__ == "__main__":
    sys.exit(main())
