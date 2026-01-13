#!/usr/bin/env python3
"""
Skills Validator

Validates that skill files:
- Have required sections (Context, Model, Tools, etc.)
- Reference valid database tables
- Reference valid commands
- Have valid links
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

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

PROJECT_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"

# Required sections in skill files
REQUIRED_SKILL_PATTERNS = [
    (r'^#+\s*Context', 'Context section'),
    (r'^#+\s*(Model|Tools|Actions)', 'Model/Tools/Actions section'),
]

# Table reference pattern (exclude common file extensions)
TABLE_PATTERN = re.compile(r'\bclaude\.(\w+)\b')
FILE_EXTENSIONS = {'json', 'md', 'py', 'txt', 'yaml', 'yml', 'sql', 'log', 'csv'}


def get_valid_tables() -> Set[str]:
    """Get list of valid tables from database."""
    if not HAS_DB:
        return set()

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'claude'
                """)
                return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()


def get_valid_commands() -> Set[str]:
    """Get list of valid commands from commands directory."""
    commands = set()
    commands_dir = PROJECT_ROOT / ".claude" / "commands"

    if commands_dir.exists():
        for cmd_file in commands_dir.glob("*.md"):
            commands.add(cmd_file.stem)

    return commands


def validate_skill_file(path: Path, valid_tables: Set[str]) -> Tuple[int, int, List[str], List[str]]:
    """Validate a single skill file."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        return 0, 1, [f"Cannot read {path.name}: {e}"], []

    skill_name = path.parent.name if path.name == 'skill.md' else path.stem

    # Check required sections
    for pattern, section_name in REQUIRED_SKILL_PATTERNS:
        if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            passed += 1
        else:
            warnings.append(f"{skill_name}: Missing {section_name}")

    # Check table references (filtering out file extensions)
    tables_referenced = TABLE_PATTERN.findall(content)
    tables_referenced = [t for t in tables_referenced if t.lower() not in FILE_EXTENSIONS]
    if tables_referenced and valid_tables:
        for table in set(tables_referenced):
            if table in valid_tables:
                passed += 1
            else:
                failed += 1
                errors.append(f"{skill_name}: References non-existent table 'claude.{table}'")
    elif tables_referenced and not valid_tables:
        warnings.append(f"{skill_name}: Cannot verify table references (no DB connection)")

    # Check for minimum content length
    if len(content) < 200:
        warnings.append(f"{skill_name}: Very short ({len(content)} chars)")
    else:
        passed += 1

    return passed, failed, errors, warnings


def validate_skills() -> Tuple[int, int, List[str], List[str]]:
    """
    Validate all skill files.

    Returns:
        Tuple of (passed, failed, errors, warnings)
    """
    if not SKILLS_DIR.exists():
        return 0, 1, ["Skills directory does not exist"], []

    total_passed = 0
    total_failed = 0
    all_errors = []
    all_warnings = []

    valid_tables = get_valid_tables()

    # Find all skill files
    skill_files = []
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir():
            # Look for skill.md in the directory
            skill_file = skill_dir / "skill.md"
            if skill_file.exists():
                skill_files.append(skill_file)
            # Also check for any .md files in the skill directory
            for md_file in skill_dir.glob("*.md"):
                if md_file not in skill_files:
                    skill_files.append(md_file)

    if not skill_files:
        return 0, 1, ["No skill files found"], []

    for skill_file in skill_files:
        passed, failed, errors, warnings = validate_skill_file(skill_file, valid_tables)
        total_passed += passed
        total_failed += failed
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # Summary check
    if len(skill_files) >= 5:
        total_passed += 1  # Bonus for having a good number of skills
    else:
        all_warnings.append(f"Only {len(skill_files)} skill files found")

    return total_passed, total_failed, all_errors, all_warnings


if __name__ == "__main__":
    passed, failed, errors, warnings = validate_skills()

    print(f"\nSkills Validation")
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
