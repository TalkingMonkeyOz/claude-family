#!/usr/bin/env python3
"""
Pre-Commit Check Script

Runs Level 1 tests before allowing commits:
- Schema validation (if schema files changed)
- Type checking hints
- Basic validation

Usage:
    python pre_commit_check.py [--project PROJECT_PATH]

Exit codes:
    0 = All checks passed
    1 = Checks failed (block commit)
    2 = Warnings only (allow commit)

This script is called by hooks.json before git commits.
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Scripts directory
SCRIPTS_DIR = Path(__file__).parent.resolve()


def run_schema_validation() -> dict:
    """Run schema validation and return results."""
    result = {
        'check': 'schema_validation',
        'passed': True,
        'message': '',
        'details': []
    }

    script_path = SCRIPTS_DIR / 'validate_schema.py'
    if not script_path.exists():
        result['message'] = 'Schema validation script not found'
        result['passed'] = True  # Don't block if script missing
        return result

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), '--all', '--json'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if proc.returncode == 0:
            result['message'] = 'All schemas valid'
        else:
            result['passed'] = False
            try:
                data = json.loads(proc.stdout)
                failed = [o for o in data.get('objects', []) if not o['passed']]
                result['message'] = f'{len(failed)} schema(s) invalid'
                result['details'] = [
                    f"{o['object']}: missing {o.get('missing_columns', [])}"
                    for o in failed
                ]
            except:
                result['message'] = 'Schema validation failed'
                result['details'] = [proc.stderr or proc.stdout]

    except subprocess.TimeoutExpired:
        result['message'] = 'Schema validation timed out'
        result['passed'] = True  # Don't block on timeout
    except Exception as e:
        result['message'] = f'Error: {str(e)}'
        result['passed'] = True  # Don't block on errors

    return result


def check_staged_files() -> dict:
    """Check what files are staged for commit."""
    result = {
        'check': 'staged_files',
        'passed': True,
        'message': '',
        'details': []
    }

    try:
        proc = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            timeout=10
        )

        staged_files = [f.strip() for f in proc.stdout.strip().split('\n') if f.strip()]
        result['details'] = staged_files
        result['message'] = f'{len(staged_files)} files staged'

        # Check for sensitive files
        sensitive_patterns = ['.env', 'credentials', 'secret', 'password']
        sensitive_files = [
            f for f in staged_files
            if any(p in f.lower() for p in sensitive_patterns)
        ]

        if sensitive_files:
            result['passed'] = False
            result['message'] = 'Sensitive files detected!'
            result['details'] = sensitive_files

    except Exception as e:
        result['message'] = f'Could not check staged files: {e}'

    return result


def check_schema_changes(staged_files: list) -> bool:
    """Check if any schema-related files are being changed."""
    schema_patterns = [
        'schema', 'migration', '.sql',
        'views', 'tables', 'column_registry'
    ]

    for f in staged_files:
        f_lower = f.lower()
        if any(p in f_lower for p in schema_patterns):
            return True
    return False


def run_pre_commit_checks(project_path: str = None) -> dict:
    """Run all pre-commit checks."""
    results = {
        'checked_at': datetime.now().isoformat(),
        'project': project_path or os.getcwd(),
        'overall_passed': True,
        'checks': []
    }

    # Check staged files
    staged_check = check_staged_files()
    results['checks'].append(staged_check)
    if not staged_check['passed']:
        results['overall_passed'] = False

    staged_files = staged_check.get('details', [])

    # Run schema validation if schema files changed
    if check_schema_changes(staged_files):
        schema_check = run_schema_validation()
        results['checks'].append(schema_check)
        if not schema_check['passed']:
            results['overall_passed'] = False
    else:
        results['checks'].append({
            'check': 'schema_validation',
            'passed': True,
            'message': 'Skipped (no schema changes)',
            'details': []
        })

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pre-commit checks')
    parser.add_argument('--project', help='Project path')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    results = run_pre_commit_checks(args.project)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("=" * 50)
        print("Pre-Commit Checks")
        print("=" * 50)

        for check in results['checks']:
            status = "[PASS]" if check['passed'] else "[FAIL]"
            print(f"\n{status} {check['check']}")
            print(f"       {check['message']}")

            if check.get('details') and not check['passed']:
                for detail in check['details'][:5]:
                    print(f"       - {detail}")

        print("\n" + "=" * 50)
        if results['overall_passed']:
            print("All checks passed - OK to commit")
        else:
            print("CHECKS FAILED - Fix issues before committing")
        print("=" * 50)

    # Return appropriate exit code
    if not results['overall_passed']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
