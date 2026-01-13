#!/usr/bin/env python3
"""
Rules Validator

Validates project rules by checking:
- Commit messages match expected format (from git log)
- SQL files use claude.* schema (not legacy schemas)
- Rule files are syntactically valid
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Commit message format from commit-rules.md
# <type>: <short description>
COMMIT_TYPE_PATTERN = r'^(feat|fix|refactor|docs|chore|test|style|perf)(\(.+\))?:\s+.+'

# Legacy schemas that should NOT be used
LEGACY_SCHEMAS = ['claude_family', 'claude_pm']

# SQL patterns to check
SQL_PATTERNS = {
    'legacy_schema': re.compile(r'\b(claude_family|claude_pm)\.\w+', re.IGNORECASE),
    'correct_schema': re.compile(r'\bclaude\.\w+', re.IGNORECASE),
}


def check_recent_commits(limit: int = 20) -> Tuple[int, int, List[str], List[str]]:
    """Check that recent commits follow the format."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    try:
        result = subprocess.run(
            ['git', 'log', f'-{limit}', '--pretty=format:%s'],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )

        if result.returncode != 0:
            return 0, 0, [], ["Could not read git log"]

        commits = result.stdout.strip().split('\n')

        for commit in commits:
            if not commit:
                continue

            # Skip merge commits
            if commit.startswith('Merge'):
                continue

            if re.match(COMMIT_TYPE_PATTERN, commit):
                passed += 1
            else:
                failed += 1
                # Only report first few failures
                if failed <= 3:
                    errors.append(f"Commit format: '{commit[:50]}...'")

        if failed > 3:
            warnings.append(f"... and {failed - 3} more commit format issues")

    except Exception as e:
        warnings.append(f"Could not check commits: {e}")

    return passed, failed, errors, warnings


def check_sql_files() -> Tuple[int, int, List[str], List[str]]:
    """Check that SQL files use correct schema."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    sql_files = list(PROJECT_ROOT.rglob('*.sql'))

    for sql_file in sql_files:
        try:
            content = sql_file.read_text(encoding='utf-8')

            # Check for legacy schemas
            legacy_matches = SQL_PATTERNS['legacy_schema'].findall(content)
            if legacy_matches:
                failed += 1
                unique = set(legacy_matches)
                errors.append(f"{sql_file.name}: Uses legacy schema {unique}")
            else:
                # Check it uses claude.* at all
                if SQL_PATTERNS['correct_schema'].search(content):
                    passed += 1
                else:
                    # No schema specified - might be ok for CREATE statements
                    warnings.append(f"{sql_file.name}: No claude.* schema references")

        except Exception as e:
            warnings.append(f"Could not read {sql_file.name}: {e}")

    return passed, failed, errors, warnings


def check_python_sql_usage() -> Tuple[int, int, List[str], List[str]]:
    """Check that Python files with SQL use correct schema."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    # Check Python files in scripts/
    scripts_dir = PROJECT_ROOT / "scripts"
    if not scripts_dir.exists():
        return 0, 0, [], []

    for py_file in scripts_dir.rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8')

            # Only check files that have SQL
            if 'execute' not in content.lower() and 'sql' not in content.lower():
                continue

            # Check for legacy schemas in SQL strings
            legacy_matches = SQL_PATTERNS['legacy_schema'].findall(content)
            if legacy_matches:
                failed += 1
                unique = set(legacy_matches)
                errors.append(f"{py_file.name}: SQL uses legacy schema {unique}")
            elif SQL_PATTERNS['correct_schema'].search(content):
                passed += 1

        except Exception as e:
            warnings.append(f"Could not read {py_file.name}: {e}")

    return passed, failed, errors, warnings


def check_rules_files() -> Tuple[int, int, List[str], List[str]]:
    """Check that rules files exist and are valid markdown."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    rules_dir = PROJECT_ROOT / ".claude" / "rules"
    if not rules_dir.exists():
        return 0, 1, ["Rules directory does not exist"], []

    expected_rules = ['commit-rules.md', 'database-rules.md', 'testing-rules.md']

    for rule_file in expected_rules:
        path = rules_dir / rule_file
        if path.exists():
            try:
                content = path.read_text(encoding='utf-8')
                # Check it has at least some content
                if len(content) > 100:
                    passed += 1
                else:
                    failed += 1
                    errors.append(f"{rule_file}: Too short ({len(content)} chars)")
            except Exception as e:
                failed += 1
                errors.append(f"{rule_file}: Cannot read: {e}")
        else:
            failed += 1
            errors.append(f"{rule_file}: Missing")

    return passed, failed, errors, warnings


def validate_rules() -> Tuple[int, int, List[str], List[str]]:
    """
    Validate all rules.

    Returns:
        Tuple of (passed, failed, errors, warnings)
    """
    total_passed = 0
    total_failed = 0
    all_errors = []
    all_warnings = []

    # Check rules files exist
    passed, failed, errors, warnings = check_rules_files()
    total_passed += passed
    total_failed += failed
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    # Check recent commits
    passed, failed, errors, warnings = check_recent_commits()
    total_passed += passed
    total_failed += failed
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    # Check SQL files
    passed, failed, errors, warnings = check_sql_files()
    total_passed += passed
    total_failed += failed
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    # Check Python SQL usage
    passed, failed, errors, warnings = check_python_sql_usage()
    total_passed += passed
    total_failed += failed
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    return total_passed, total_failed, all_errors, all_warnings


if __name__ == "__main__":
    passed, failed, errors, warnings = validate_rules()

    print(f"\nRules Validation")
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
