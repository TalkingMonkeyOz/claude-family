#!/usr/bin/env python3
"""F232.P3 — One-off backfill: populate claude.knowledge.kg_links from
description / code_example text.

Scans rows where kg_links = '[]'::jsonb (non-destructive: never touches
already-populated rows). For each row, extracts file-path mentions from
description + code_example using three regex families:

  1. Absolute Windows paths      — C:\\Projects\\..., C:/Projects/...
  2. Project-relative paths      — scripts/foo.py, mcp-servers/bar/, etc.
  3. claude.<table> references   — claude.knowledge, claude.workspaces, ...

Each unique path is added to kg_links as
    {"kind": "file", "path": "<absolute-windows-path>"}
or for table references
    {"kind": "table", "path": "claude.<table>"}

Idempotent — re-running produces no diffs because the WHERE clause filters
out non-empty kg_links (and the script never updates a row whose existing
kg_links is non-empty).

Run:
    DATABASE_URL=... python scripts/backfill_kg_links.py [--dry-run] [--limit N]

Use --dry-run first to preview. The actual UPDATE statements include the
'-- OVERRIDE: F232.P3 kg_links backfill from description text' comment so
the SQL governance hook does not flag this as a bypass.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import detect_psycopg, get_db_connection  # noqa: E402


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Absolute Windows paths — both backslash and forward-slash, drive-letter rooted.
# Stops at whitespace, quote chars, or markdown punctuation. Allows file/folder
# segments that include letters, digits, _, -, ., +.
RE_WINDOWS_ABS = re.compile(
    r"([A-Za-z]:[\\/](?:[\w.+-]+[\\/])*[\w.+-]+)",
    flags=re.UNICODE,
)

# Project-relative paths anchored on a known top-level directory in the
# claude-family project. Mentions inside prose like "scripts/foo.py" or
# "mcp-servers/project-tools/server_v2.py" or trailing slashes for dirs.
PROJECT_ROOTS = (
    "scripts",
    "mcp-servers",
    "knowledge-vault",
    "templates",
    "docs",
    "tests",
    ".claude",
    "archive",
    "tools",
    "src",
    "benchmarks",
    "processes",
)
RE_PROJECT_REL = re.compile(
    r"(?<![\w/\\])((?:" + "|".join(re.escape(r) for r in PROJECT_ROOTS) +
    r")[/\\][\w./\\+-]+)",
    flags=re.UNICODE,
)

# claude.<table> references (and a few other useful schema hits).
# Restricted to schemas that are actually PostgreSQL schemas in this DB
# (avoids matching things like "nimbus.cloud" which is a domain name).
RE_TABLE_REF = re.compile(
    r"\b(claude(?:_pm|_family)?|hal|public)\.([a-z_][a-z0-9_]*)\b",
    flags=re.UNICODE,
)

# File suffixes that indicate "this is actually a file, not a stray word"
LIKELY_FILE_SUFFIXES = {
    ".py", ".sql", ".md", ".json", ".yaml", ".yml", ".toml", ".bpmn",
    ".sh", ".ps1", ".bat", ".cmd", ".js", ".ts", ".tsx", ".jsx",
    ".rs", ".go", ".java", ".kt", ".html", ".css", ".txt", ".log",
    ".csv", ".env", ".cfg", ".ini", ".xml",
}

# Paths we want to skip — these are noise more than signal.
SKIP_PREFIXES = {
    "C:\\Users\\", "C:/Users/",
    "C:\\Windows\\", "C:/Windows/",
}
SKIP_SUFFIXES = {
    ".pyc", ".so", ".dll", ".exe",
}

CF_ROOT = Path(os.environ.get("CLAUDE_PROJECT_PATH", r"C:\Projects\claude-family"))


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------

def to_windows_abs(raw: str) -> str:
    """Best-effort canonicalisation to absolute Windows form (backslash)."""
    raw = raw.strip().rstrip(".,;:)\"'")
    if not raw:
        return ""
    # Already absolute (Windows drive letter)?
    if len(raw) > 2 and raw[1] == ":" and raw[2] in ("/", "\\"):
        return raw.replace("/", "\\")
    # Project-relative?
    return str(CF_ROOT / raw.replace("\\", "/")).replace("/", "\\")


def looks_like_file(path: str) -> bool:
    """Heuristic: keep paths that have a known suffix OR live under a project root."""
    lower = path.lower()
    if any(lower.endswith(s) for s in LIKELY_FILE_SUFFIXES):
        return True
    # Directory-style mention (trailing slash or dir-only) — keep it.
    if path.endswith(("/", "\\")):
        return True
    # If at least 3 segments deep and lacks suffix, treat as plausible dir.
    return path.count("\\") + path.count("/") >= 3


def is_skip(path: str) -> bool:
    if not path:
        return True
    if any(path.startswith(p) for p in SKIP_PREFIXES):
        return True
    lower = path.lower()
    if any(lower.endswith(s) for s in SKIP_SUFFIXES):
        return True
    return False


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_paths(text: str) -> Set[str]:
    """Return the canonical-form paths and table refs extracted from text."""
    if not text:
        return set()
    out: Set[str] = set()

    for m in RE_WINDOWS_ABS.findall(text):
        norm = to_windows_abs(m)
        if not is_skip(norm) and looks_like_file(norm):
            out.add(("file", norm))

    for m in RE_PROJECT_REL.findall(text):
        # Filter false positives (URLs, doc-path examples, etc.)
        if "://" in m:
            continue
        norm = to_windows_abs(m)
        if not is_skip(norm) and looks_like_file(norm):
            out.add(("file", norm))

    # Words that look like table refs but are really file extensions
    # (claude.bat, claude.md, etc.) — skip.
    EXT_WORDS = {
        "bat", "cmd", "md", "py", "sql", "json", "yaml", "yml", "toml",
        "sh", "ps1", "js", "ts", "tsx", "jsx", "rs", "go", "java",
        "html", "css", "txt", "log", "csv", "env", "cfg", "ini", "xml",
        "exe", "dll", "so", "pyc",
    }
    for schema, table in RE_TABLE_REF.findall(text):
        if schema in ("claude", "claude_pm", "claude_family", "hal", "public"):
            if table in EXT_WORDS:
                continue  # claude.bat, claude.md — these are filenames, not tables
            out.add(("table", f"{schema}.{table}"))

    return out  # type: ignore[return-value]


def to_link(kind: str, path: str) -> Dict[str, str]:
    return {"kind": kind, "path": path}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan + report only; no UPDATE issued.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap rows processed (0 = no cap).")
    parser.add_argument("--batch", type=int, default=200,
                        help="Commit every N rows (default 200).")
    args = parser.parse_args()

    detect_psycopg()  # priming
    conn = get_db_connection()

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT knowledge_id, description, code_example "
            "FROM   claude.knowledge "
            "WHERE  kg_links = '[]'::jsonb "
            "  AND  status IS DISTINCT FROM 'archived' "
            "ORDER  BY created_at"
        )
        rows = cur.fetchall()
        if args.limit:
            rows = rows[: args.limit]

        scanned = len(rows)
        updated = 0
        all_paths: Counter[str] = Counter()
        path_kinds: Counter[Tuple[str, str]] = Counter()

        update_cur = conn.cursor()
        update_sql = (
            "UPDATE claude.knowledge "
            "SET    kg_links = %s::jsonb "
            "WHERE  knowledge_id = %s "
            "  AND  kg_links = '[]'::jsonb "
            "-- OVERRIDE: F232.P3 kg_links backfill from description text"
        )

        for i, row in enumerate(rows):
            # psycopg2 returns tuple/dict-row depending on cursor; normalise.
            if isinstance(row, dict):
                kid = row["knowledge_id"]
                desc = row.get("description") or ""
                code = row.get("code_example") or ""
            else:
                kid, desc, code = row[0], row[1] or "", row[2] or ""

            paths = extract_paths(desc) | extract_paths(code)
            if not paths:
                continue

            links: List[Dict[str, str]] = []
            for kind, path in sorted(paths):
                links.append(to_link(kind, path))
                all_paths[path] += 1
                path_kinds[(kind, path)] += 1

            if args.dry_run:
                if i < 5:  # show sample
                    print(f"  [{kid}] -> {len(links)} links: "
                          f"{[l['path'] for l in links[:3]]}{' ...' if len(links) > 3 else ''}")
            else:
                update_cur.execute(update_sql, (json.dumps(links), kid))
                updated += 1
                if updated % args.batch == 0:
                    conn.commit()
                    print(f"  committed {updated}/{scanned}")

        if not args.dry_run:
            conn.commit()

        # Summary
        print()
        print("=" * 60)
        print(f"F232.P3 kg_links backfill {'[DRY RUN]' if args.dry_run else '[APPLIED]'}")
        print("=" * 60)
        print(f"Rows scanned (kg_links = '[]'): {scanned}")
        print(f"Rows updated (got >=1 link)  : {updated if not args.dry_run else '(would update) ' + str(sum(1 for _ in []))}")
        # Compute would-update count for dry-run
        if args.dry_run:
            would = 0
            for row in rows:
                if isinstance(row, dict):
                    desc = row.get("description") or ""
                    code = row.get("code_example") or ""
                else:
                    desc, code = row[1] or "", row[2] or ""
                if extract_paths(desc) | extract_paths(code):
                    would += 1
            print(f"Rows that WOULD update      : {would}")
        print(f"Distinct paths surfaced     : {len(all_paths)}")

        print()
        print("Top 10 paths by frequency:")
        for path, count in all_paths.most_common(10):
            # Compute kind from the most-common (kind, path) bucket
            kinds_for_path = [k for (k, p), _ in path_kinds.items() if p == path]
            kind = kinds_for_path[0] if kinds_for_path else "?"
            print(f"  {count:4d}  [{kind:5s}]  {path}")

        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
