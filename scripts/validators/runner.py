#!/usr/bin/env python3
"""
Validator Runner - Run all or specific config validators.

Usage:
    python scripts/validators/runner.py              # Run all validators
    python scripts/validators/runner.py claude_md    # Run specific validator
    python scripts/validators/runner.py rules skills # Run multiple validators
    python scripts/validators/runner.py --help       # Show help
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add scripts directory to path for validator imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class ValidationResult:
    """Result from a validation check."""
    validator: str
    passed: int
    failed: int
    warnings: int
    errors: List[str]
    warnings_list: List[str]


def run_validator(name: str) -> ValidationResult:
    """Run a specific validator and return results."""
    errors = []
    warnings = []

    try:
        if name == 'claude_md':
            from validators.claude_md import validate_claude_md
            passed, failed, errs, warns = validate_claude_md()
        elif name == 'rules':
            from validators.rules import validate_rules
            passed, failed, errs, warns = validate_rules()
        elif name == 'skills':
            from validators.skills import validate_skills
            passed, failed, errs, warns = validate_skills()
        elif name == 'data_gateway':
            from validators.data_gateway import validate_data_gateway
            passed, failed, errs, warns = validate_data_gateway()
        else:
            return ValidationResult(name, 0, 1, 0, [f"Unknown validator: {name}"], [])

        return ValidationResult(name, passed, failed, len(warns), errs, warns)

    except ImportError as e:
        return ValidationResult(name, 0, 1, 0, [f"Import error: {e}"], [])
    except Exception as e:
        return ValidationResult(name, 0, 1, 0, [f"Error: {e}"], [])


def print_result(result: ValidationResult, verbose: bool = False):
    """Print validation result."""
    status = "PASS" if result.failed == 0 else "FAIL"
    status_color = "\033[92m" if status == "PASS" else "\033[91m"
    reset = "\033[0m"

    print(f"\n{status_color}[{status}]{reset} {result.validator}")
    print(f"      Passed: {result.passed}, Failed: {result.failed}, Warnings: {result.warnings}")

    if result.errors and (verbose or result.failed > 0):
        for err in result.errors:
            print(f"      ERROR: {err}")

    if result.warnings_list and verbose:
        for warn in result.warnings_list:
            print(f"      WARN: {warn}")


def main():
    parser = argparse.ArgumentParser(description="Run config validators")
    parser.add_argument(
        'validators',
        nargs='*',
        default=['claude_md', 'rules', 'skills', 'data_gateway'],
        help='Validators to run (default: all)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available validators'
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable validators:")
        print("  claude_md    - Validate CLAUDE.md files (required sections, version footer)")
        print("  rules        - Validate rules (commit format, SQL schema usage)")
        print("  skills       - Validate skills (links, DB references)")
        print("  data_gateway - Validate Data Gateway constraints")
        return 0

    print("=" * 60)
    print("CONFIG VALIDATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []
    for validator in args.validators:
        result = run_validator(validator)
        results.append(result)
        print_result(result, args.verbose)

    # Summary
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    total_warnings = sum(r.warnings for r in results)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Passed:   {total_passed}")
    print(f"Total Failed:   {total_failed}")
    print(f"Total Warnings: {total_warnings}")

    overall = "PASS" if total_failed == 0 else "FAIL"
    color = "\033[92m" if overall == "PASS" else "\033[91m"
    reset = "\033[0m"
    print(f"\nOverall: {color}{overall}{reset}")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
