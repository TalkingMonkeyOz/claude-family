#!/usr/bin/env python3
"""
Vault Librarian — Entity catalog gap detection and vault health coordinator.

Focuses on checks that existing scripts DON'T cover:
1. Uncataloged vault files (vault .md files not in entity catalog)
2. Orphaned catalog entries (entity source_file points to missing vault file)
3. Missing/malformed YAML frontmatter
4. Missing embeddings (vault files not in vault_embeddings)

Existing scripts handle:
- Staleness: reviewer_doc_staleness.py
- Link checking: link_checker.py
- Orphan documents: orphan_report.py
- Quality: reviewer_doc_quality.py
- Indexing: scan_documents.py
- CLAUDE.md audit: audit_docs.py

Usage:
    python vault_librarian.py              # Run all checks, print report
    python vault_librarian.py --json       # Output JSON for /skills-librarian
    python vault_librarian.py --fix        # Auto-file feedback for violations
    python vault_librarian.py --check catalog  # Run only catalog gap check

Author: Claude Family
Date: 2026-03-17
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Setup
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "vault_librarian.log", encoding="utf-8")],
)
logger = logging.getLogger("vault_librarian")

# Database connection
DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    for env_path in [
        Path.home() / ".claude" / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if DB_URL:
            break

VAULT_ROOT = Path("C:/Projects/claude-family/knowledge-vault")
SKIP_DIRS = {"_templates", "_archive", ".obsidian", "attachments"}
SKIP_FILES = {"README.md"}  # Root README is not a design doc


def get_db_connection():
    """Get database connection."""
    try:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error("DB connection failed: %s", e)
        return None


def get_vault_files() -> list[Path]:
    """Get all .md files in the vault, excluding skipped dirs."""
    files = []
    for md_file in VAULT_ROOT.rglob("*.md"):
        # Skip excluded directories
        parts = md_file.relative_to(VAULT_ROOT).parts
        if any(p in SKIP_DIRS for p in parts):
            continue
        if md_file.name in SKIP_FILES and md_file.parent == VAULT_ROOT:
            continue
        files.append(md_file)
    return files


def check_uncataloged_files(conn) -> list[dict]:
    """Find vault .md files not registered in entity catalog."""
    findings = []
    cur = conn.cursor()

    # Get all cataloged source_files
    cur.execute("""
        SELECT e.properties->>'source_file' as source_file, e.display_name, et.type_name
        FROM claude.entities e
        JOIN claude.entity_types et ON e.entity_type_id = et.type_id
        WHERE et.type_name IN ('design_document', 'gate_deliverable', 'knowledge_pattern', 'decision')
        AND e.properties->>'source_file' IS NOT NULL
    """)
    cataloged = {row[0] for row in cur.fetchall()}

    # Check each vault file
    for vault_file in get_vault_files():
        rel_path = str(vault_file.relative_to(VAULT_ROOT)).replace("\\", "/")
        # Check various path formats the catalog might use
        if rel_path not in cataloged and vault_file.name not in cataloged:
            # Also check without leading folder
            parts = rel_path.split("/")
            partial_matches = [c for c in cataloged if any(p in c for p in parts[-2:])]
            if not partial_matches:
                findings.append({
                    "type": "uncataloged_file",
                    "severity": "medium",
                    "file": rel_path,
                    "message": f"Vault file not in entity catalog: {rel_path}",
                    "fix": f"catalog(entity_type='design_document', properties={{title: '...', source_file: '{rel_path}'}}, project='...')",
                })

    return findings


def check_orphaned_entries(conn) -> list[dict]:
    """Find catalog entries pointing to vault files that don't exist."""
    findings = []
    cur = conn.cursor()

    cur.execute("""
        SELECT e.entity_id, e.display_name, e.properties->>'source_file' as source_file, et.type_name
        FROM claude.entities e
        JOIN claude.entity_types et ON e.entity_type_id = et.type_id
        WHERE e.properties->>'source_file' IS NOT NULL
        AND et.type_name IN ('design_document', 'gate_deliverable', 'knowledge_pattern')
    """)

    for row in cur.fetchall():
        entity_id, display_name, source_file, type_name = row
        # Try to find the file
        full_path = VAULT_ROOT / source_file
        if not full_path.exists():
            # Also check by filename only
            matches = list(VAULT_ROOT.rglob(Path(source_file).name))
            if not matches:
                findings.append({
                    "type": "orphaned_entry",
                    "severity": "high",
                    "entity_id": str(entity_id),
                    "display_name": display_name,
                    "source_file": source_file,
                    "message": f"Catalog entry '{display_name}' points to missing file: {source_file}",
                    "fix": "Update source_file property or archive the entity",
                })
            elif len(matches) == 1:
                new_path = str(matches[0].relative_to(VAULT_ROOT)).replace("\\", "/")
                findings.append({
                    "type": "moved_file",
                    "severity": "low",
                    "entity_id": str(entity_id),
                    "display_name": display_name,
                    "old_path": source_file,
                    "new_path": new_path,
                    "message": f"File moved: '{display_name}' now at {new_path} (was {source_file})",
                    "fix": f"Update entity source_file to '{new_path}'",
                })

    return findings


def check_frontmatter(conn) -> list[dict]:
    """Find vault files missing YAML frontmatter."""
    findings = []
    required_fields = {"tags", "projects"}

    for vault_file in get_vault_files():
        rel_path = str(vault_file.relative_to(VAULT_ROOT)).replace("\\", "/")
        try:
            content = vault_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Check for YAML frontmatter
        if not content.startswith("---"):
            findings.append({
                "type": "missing_frontmatter",
                "severity": "medium",
                "file": rel_path,
                "message": f"No YAML frontmatter: {rel_path}",
                "fix": "Add --- delimited YAML frontmatter with projects and tags fields",
            })
            continue

        # Parse frontmatter
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            findings.append({
                "type": "malformed_frontmatter",
                "severity": "medium",
                "file": rel_path,
                "message": f"Malformed YAML frontmatter (no closing ---): {rel_path}",
                "fix": "Fix YAML frontmatter — ensure closing --- delimiter",
            })
            continue

        # Check required fields (simple check — not full YAML parse to avoid dependency)
        fm_text = match.group(1)
        for field in required_fields:
            if f"{field}:" not in fm_text and f"{field} :" not in fm_text:
                findings.append({
                    "type": "missing_field",
                    "severity": "low",
                    "file": rel_path,
                    "field": field,
                    "message": f"Missing frontmatter field '{field}' in {rel_path}",
                    "fix": f"Add '{field}:' to YAML frontmatter",
                })

    return findings


def check_missing_embeddings(conn) -> list[dict]:
    """Find vault files not in vault_embeddings table."""
    findings = []
    cur = conn.cursor()

    cur.execute("""
        SELECT file_path FROM claude.vault_embeddings
        WHERE file_path IS NOT NULL
    """)
    embedded = {row[0].replace("\\", "/") for row in cur.fetchall()}

    for vault_file in get_vault_files():
        # vault_embeddings stores full or relative paths — check both patterns
        rel_path = str(vault_file.relative_to(VAULT_ROOT)).replace("\\", "/")
        full_path = str(vault_file).replace("\\", "/")

        found = False
        for emb_path in embedded:
            if rel_path in emb_path or full_path in emb_path or vault_file.name in emb_path:
                found = True
                break

        if not found:
            findings.append({
                "type": "missing_embedding",
                "severity": "low",
                "file": rel_path,
                "message": f"No RAG embedding for: {rel_path}",
                "fix": "Run: python scripts/embed_vault_documents.py",
            })

    return findings


def run_audit(checks: list[str] | None = None) -> dict:
    """Run all or selected checks and return findings."""
    conn = get_db_connection()
    if not conn:
        return {"success": False, "error": "Database connection failed"}

    all_checks = {
        "catalog": check_uncataloged_files,
        "orphaned": check_orphaned_entries,
        "frontmatter": check_frontmatter,
        "embeddings": check_missing_embeddings,
    }

    checks_to_run = checks or list(all_checks.keys())
    all_findings = []

    for check_name in checks_to_run:
        if check_name in all_checks:
            try:
                findings = all_checks[check_name](conn)
                all_findings.extend(findings)
                logger.info("Check '%s': %d findings", check_name, len(findings))
            except Exception as e:
                logger.error("Check '%s' failed: %s", check_name, e)
                all_findings.append({
                    "type": "check_error",
                    "severity": "high",
                    "check": check_name,
                    "message": f"Check '{check_name}' failed: {e}",
                })

    conn.close()

    # Summarize
    by_severity = {}
    by_type = {}
    for f in all_findings:
        sev = f.get("severity", "unknown")
        typ = f.get("type", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[typ] = by_type.get(typ, 0) + 1

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "vault_files_scanned": len(get_vault_files()),
        "total_findings": len(all_findings),
        "by_severity": by_severity,
        "by_type": by_type,
        "findings": all_findings,
    }


def file_feedback(findings: list[dict]):
    """Auto-file feedback for critical/high findings."""
    conn = get_db_connection()
    if not conn:
        return

    cur = conn.cursor()
    filed = 0
    project_id = "20b5627c-e72c-4501-8537-95b559731b59"  # claude-family

    for f in findings:
        if f.get("severity") not in ("critical", "high"):
            continue

        title = f"Vault librarian: {f.get('type', 'unknown')} — {f.get('display_name', f.get('file', 'unknown'))}"
        if len(title) > 200:
            title = title[:197] + "..."

        try:
            cur.execute("""
                INSERT INTO claude.feedback (project_id, feedback_type, title, description, status, priority)
                VALUES (%s, 'bug', %s, %s, 'new', 'medium')
                ON CONFLICT DO NOTHING
            """, (project_id, title, json.dumps(f, indent=2)))
            filed += 1
        except Exception as e:
            logger.error("Failed to file feedback: %s", e)

    conn.close()
    logger.info("Filed %d feedback items for critical/high findings", filed)


def main():
    parser = argparse.ArgumentParser(description="Vault Librarian — health audit")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--fix", action="store_true", help="Auto-file feedback for violations")
    parser.add_argument("--check", choices=["catalog", "orphaned", "frontmatter", "embeddings"],
                        help="Run only a specific check")
    args = parser.parse_args()

    checks = [args.check] if args.check else None
    report = run_audit(checks)

    if not report["success"]:
        print(f"ERROR: {report.get('error', 'Unknown error')}")
        sys.exit(1)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  VAULT LIBRARIAN REPORT — {report['timestamp'][:10]}")
        print(f"{'='*60}")
        print(f"  Files scanned: {report['vault_files_scanned']}")
        print(f"  Total findings: {report['total_findings']}")
        print()
        if report["by_severity"]:
            print("  By Severity:")
            for sev in ["critical", "high", "medium", "low"]:
                if sev in report["by_severity"]:
                    print(f"    {sev.upper():10s} {report['by_severity'][sev]}")
        if report["by_type"]:
            print("\n  By Type:")
            for typ, cnt in sorted(report["by_type"].items(), key=lambda x: -x[1]):
                print(f"    {typ:25s} {cnt}")
        print(f"\n{'='*60}")

        if report["total_findings"] > 0 and not args.fix:
            print("\n  Run with --fix to auto-file feedback for high/critical issues")
            print("  Run with --json for machine-readable output")

    if args.fix and report.get("findings"):
        file_feedback(report["findings"])
        print(f"\n  Feedback filed for critical/high findings.")

    sys.exit(0 if report["total_findings"] == 0 else 0)


if __name__ == "__main__":
    main()
