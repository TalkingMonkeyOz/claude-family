#!/usr/bin/env python3
"""
CLAUDE.md Validator

Validates that CLAUDE.md files have:
- Required sections (Problem Statement, Architecture, Status)
- Version footer with date
- Valid Project ID that exists in database
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_DB = True
except ImportError:
    HAS_DB = False

DB_CONFIG = {
    "host": os.environ.get("PGHOST", "localhost"),
    "port": int(os.environ.get("PGPORT", 5432)),
    "database": os.environ.get("PGDATABASE", "ai_company_foundation"),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", "")
}

# Required sections (at least one of these headers should exist)
REQUIRED_SECTIONS = [
    r'^##?\s*Problem\s*Statement',
    r'^##?\s*Architecture',
    r'^##?\s*Current\s*Phase',
    r'^##?\s*Status',
]

# Version footer pattern
VERSION_FOOTER_PATTERN = r'\*\*Version\*\*:\s*[\d.]+\s*\n.*\*\*Updated\*\*:\s*\d{4}-\d{2}-\d{2}'

# Project ID pattern
PROJECT_ID_PATTERN = r'\*\*Project\s*ID\*\*:\s*`?([a-f0-9-]{36})`?'


def find_claude_md_files() -> List[Path]:
    """Find all CLAUDE.md files in known project locations."""
    files = []

    # Check current project
    project_root = Path(__file__).parent.parent.parent
    if (project_root / "CLAUDE.md").exists():
        files.append(project_root / "CLAUDE.md")

    # Check global
    global_claude_md = Path.home() / ".claude" / "CLAUDE.md"
    if global_claude_md.exists():
        files.append(global_claude_md)

    # Check other known project locations
    projects_dir = Path("C:/Projects")
    if projects_dir.exists():
        for project in projects_dir.iterdir():
            if project.is_dir():
                claude_md = project / "CLAUDE.md"
                if claude_md.exists() and claude_md not in files:
                    files.append(claude_md)

    return files


def check_required_sections(content: str) -> Tuple[bool, List[str]]:
    """Check that CLAUDE.md has required sections."""
    missing = []
    found = 0

    for pattern in REQUIRED_SECTIONS:
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            found += 1

    # Need at least 2 of the required sections
    if found < 2:
        missing.append(f"Only {found}/4 required sections found (need at least 2)")

    return len(missing) == 0, missing


def check_version_footer(content: str) -> Tuple[bool, List[str]]:
    """Check that CLAUDE.md has a version footer."""
    if re.search(VERSION_FOOTER_PATTERN, content, re.IGNORECASE):
        return True, []
    return False, ["Missing version footer (Version + Updated date)"]


def check_project_id(content: str) -> Tuple[bool, List[str], Optional[str]]:
    """Check that Project ID exists in database."""
    match = re.search(PROJECT_ID_PATTERN, content, re.IGNORECASE)

    if not match:
        return True, [], None  # Project ID is optional, not an error if missing

    project_id = match.group(1)

    if not HAS_DB:
        return True, ["Cannot verify Project ID (no database connection)"], project_id

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT project_name FROM claude.projects WHERE project_id = %s",
                    (project_id,)
                )
                result = cur.fetchone()

                if result:
                    return True, [], project_id
                else:
                    return False, [f"Project ID {project_id} not found in database"], project_id

    except Exception as e:
        return True, [f"Could not verify Project ID: {e}"], project_id


def validate_file(path: Path) -> Tuple[int, int, List[str], List[str]]:
    """Validate a single CLAUDE.md file."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        return 0, 1, [f"Cannot read {path}: {e}"], []

    # Check required sections
    ok, msgs = check_required_sections(content)
    if ok:
        passed += 1
    else:
        failed += 1
        errors.extend([f"{path.name}: {m}" for m in msgs])

    # Check version footer
    ok, msgs = check_version_footer(content)
    if ok:
        passed += 1
    else:
        failed += 1
        errors.extend([f"{path.name}: {m}" for m in msgs])

    # Check project ID
    ok, msgs, project_id = check_project_id(content)
    if ok:
        passed += 1
    else:
        failed += 1
        errors.extend([f"{path.name}: {m}" for m in msgs])

    # Add any warnings from project ID check
    warnings.extend([f"{path.name}: {m}" for m in msgs if "Cannot verify" in m or "Could not" in m])

    return passed, failed, errors, warnings


def validate_claude_md() -> Tuple[int, int, List[str], List[str]]:
    """
    Validate all CLAUDE.md files.

    Returns:
        Tuple of (passed, failed, errors, warnings)
    """
    files = find_claude_md_files()

    if not files:
        return 0, 1, ["No CLAUDE.md files found"], []

    total_passed = 0
    total_failed = 0
    all_errors = []
    all_warnings = []

    for path in files:
        passed, failed, errors, warnings = validate_file(path)
        total_passed += passed
        total_failed += failed
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    return total_passed, total_failed, all_errors, all_warnings


if __name__ == "__main__":
    passed, failed, errors, warnings = validate_claude_md()

    print(f"\nCLAUDE.md Validation")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  - {e}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    sys.exit(0 if failed == 0 else 1)
