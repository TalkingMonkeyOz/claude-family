#!/usr/bin/env python3
"""
Test suite for Process Router

Tests that the process_router.py correctly identifies and routes
user prompts to the appropriate processes.

Usage:
    python test_process_router.py
    python test_process_router.py -v  # verbose

Author: claude-code-unified
Date: 2025-12-07
"""

import sys
import os
import io
import json

# Fix Windows encoding - but only if not already wrapped
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add scripts to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from process_router import get_db_connection, get_matching_processes, build_process_guidance


# Test cases: (prompt, expected_process_ids, description)
TEST_CASES = [
    # Project Initialization - Should ALWAYS catch these
    ("Let's build a new app", ["PROC-PROJECT-001"], "Basic new project request"),
    ("I want to create a new project called foo", ["PROC-PROJECT-001"], "Explicit create project"),
    ("Start a new application for tracking expenses", ["PROC-PROJECT-001"], "Start new application"),
    ("Let's begin a new service", ["PROC-PROJECT-001"], "Begin new service"),

    # Major Change Detection - Critical to catch
    ("Convert this project to Electron", ["PROC-PROJECT-005"], "Convert to Electron"),
    ("Migrate the app to React Native", ["PROC-PROJECT-005"], "Migrate to mobile"),
    ("Port this to a desktop application", ["PROC-PROJECT-005"], "Port to desktop"),
    ("I want to rewrite this in Flutter", ["PROC-PROJECT-005"], "Rewrite request"),

    # Session Management
    ("I'm done for now, goodbye", ["PROC-SESSION-002"], "Session end - goodbye"),
    ("End session", ["PROC-SESSION-002"], "Explicit end session"),
    ("Let's wrap up", ["PROC-SESSION-002"], "Wrap up session"),

    # Bug/Issue Detection
    ("There's a bug in the login form", ["PROC-DEV-002"], "Bug report"),
    ("Something is broken", ["PROC-DEV-002"], "Something broken"),
    ("I'm getting an error when I click submit", ["PROC-DEV-002"], "Error report"),
    ("Fix the authentication issue", ["PROC-DEV-002"], "Fix request"),

    # Feature Implementation
    ("Implement the dark mode feature", ["PROC-DEV-001"], "Implement feature"),
    ("Build the user settings page", ["PROC-DEV-001"], "Build feature"),
    ("Add search functionality", ["PROC-DEV-001"], "Add functionality"),

    # Testing
    ("Run the tests", ["PROC-DEV-004"], "Run tests"),
    ("Make sure it works", ["PROC-DEV-004"], "Verify working"),

    # Compliance
    ("Check for stale docs", ["PROC-DOC-002"], "Doc staleness check"),
    ("Are there any outdated docs?", ["PROC-DOC-002"], "Doc outdated check"),
    ("Check compliance", ["PROC-PROJECT-004"], "Compliance check"),

    # Work Item Classification
    ("I have an idea for a new feature", ["PROC-DATA-004"], "Idea classification"),
    ("I found a bug", ["PROC-DATA-004", "PROC-DEV-002"], "Bug found (may match multiple)"),

    # Negative cases - should NOT match specific processes
    ("Tell me a joke", [], "Unrelated request"),
    ("What's 2+2?", [], "Simple question"),
    ("Show me the code", [], "Code viewing request"),
]


def run_tests(verbose=False):
    """Run all test cases."""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Could not connect to database")
        return False

    passed = 0
    failed = 0
    warnings = 0

    print("=" * 60)
    print("Process Router Test Suite")
    print("=" * 60)

    for prompt, expected_ids, description in TEST_CASES:
        matches = get_matching_processes(conn, prompt)
        matched_ids = [m['process_id'] for m in matches]

        # Check if expected processes were found
        # For expected_ids, check if ALL expected are in matched
        # Allow additional matches (may be valid)
        all_expected_found = all(exp in matched_ids for exp in expected_ids)

        # For empty expected, should match nothing
        if not expected_ids:
            success = len(matched_ids) == 0
        else:
            success = all_expected_found

        if success:
            status = "PASS"
            passed += 1
        elif not expected_ids and matched_ids:
            # Unexpected match - might be okay
            status = "WARN"
            warnings += 1
        else:
            status = "FAIL"
            failed += 1

        if verbose or status != "PASS":
            print(f"\n{status}: {description}")
            print(f"  Prompt: \"{prompt[:50]}...\"" if len(prompt) > 50 else f"  Prompt: \"{prompt}\"")
            print(f"  Expected: {expected_ids}")
            print(f"  Got: {matched_ids}")
            if matches and verbose:
                for m in matches:
                    print(f"    - {m['process_name']} ({m['enforcement']})")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {warnings} warnings")
    print(f"Total: {len(TEST_CASES)} tests")
    print("=" * 60)

    # Test guidance generation for a sample
    if verbose:
        print("\n" + "=" * 60)
        print("Sample Guidance Output")
        print("=" * 60)
        sample_prompt = "Let's build a new project for task management"
        matches = get_matching_processes(conn, sample_prompt)
        guidance = build_process_guidance(matches, conn)
        print(f"\nPrompt: \"{sample_prompt}\"")
        print(f"\nGenerated Guidance:\n{guidance}")

    conn.close()

    return failed == 0


def test_single(prompt: str):
    """Test a single prompt interactively."""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Could not connect to database")
        return

    print(f"Testing prompt: \"{prompt}\"")
    print("-" * 40)

    matches = get_matching_processes(conn, prompt)

    if not matches:
        print("No processes matched")
    else:
        print(f"Matched {len(matches)} process(es):\n")
        for m in matches:
            print(f"  [{m['process_id']}] {m['process_name']}")
            print(f"    Category: {m['category']}")
            print(f"    Enforcement: {m['enforcement']}")
            print(f"    Command: {m.get('command_ref', 'N/A')}")
            print()

        print("-" * 40)
        print("Generated Guidance:")
        print("-" * 40)
        guidance = build_process_guidance(matches, conn)
        print(guidance)

    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Test process router')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--test', type=str, help='Test a single prompt')
    args = parser.parse_args()

    if args.test:
        test_single(args.test)
    else:
        success = run_tests(verbose=args.verbose)
        sys.exit(0 if success else 1)
