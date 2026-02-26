#!/usr/bin/env python3
"""
Full Regression Test for Process Enforcement System

Tests:
1. Pattern matching - do triggers fire correctly?
2. Step definitions - are steps logical and complete?
3. End-to-end workflow - does the full flow make sense?

Author: claude-code-unified
Date: 2025-12-07
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import POSTGRES_CONFIG
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db():
    return psycopg2.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)


def test_pattern_matching():
    """Test that patterns correctly match expected prompts."""
    from process_router import get_matching_processes, get_db_connection

    conn = get_db_connection()

    # Critical test cases - these MUST work
    critical_tests = [
        # (prompt, expected_process_id, description)
        ("Let's build a new app", "PROC-PROJECT-001", "New project detection"),
        ("I want to create a new project", "PROC-PROJECT-001", "Create project"),
        ("Convert this to Electron", "PROC-PROJECT-005", "Major change - Electron"),
        ("Migrate the app to React Native", "PROC-PROJECT-005", "Major change - mobile"),
        ("There's a bug in the login", "PROC-DEV-002", "Bug report"),
        ("Something is broken", "PROC-DEV-002", "Something broken"),
        ("Implement the search feature", "PROC-DEV-001", "Feature implementation"),
        ("Run the tests", "PROC-DEV-004", "Run tests"),
        ("I'm done for now", "PROC-SESSION-002", "Session end"),
        ("Check compliance", "PROC-PROJECT-004", "Compliance check"),
        ("I have an idea for a feature", "PROC-DATA-004", "Idea classification"),
        ("Review this code", "PROC-DEV-003", "Code review"),
        ("Create a new ADR", "PROC-DOC-004", "ADR creation"),
        ("Bring this project up to standard", "PROC-PROJECT-003", "Project retrofit"),
    ]

    print("\n" + "=" * 70)
    print("TEST 1: Pattern Matching")
    print("=" * 70)

    passed = 0
    failed = 0

    for prompt, expected_id, desc in critical_tests:
        matches = get_matching_processes(conn, prompt)
        matched_ids = [m['process_id'] for m in matches]

        if expected_id in matched_ids:
            print(f"  PASS: {desc}")
            print(f"        Prompt: \"{prompt[:50]}\"")
            print(f"        Matched: {matched_ids[0]}")
            passed += 1
        else:
            print(f"  FAIL: {desc}")
            print(f"        Prompt: \"{prompt[:50]}\"")
            print(f"        Expected: {expected_id}")
            print(f"        Got: {matched_ids}")
            failed += 1

    conn.close()
    return passed, failed


def test_step_logic():
    """Test that process steps are logical and follow correct order."""
    conn = get_db()
    cur = conn.cursor()

    print("\n" + "=" * 70)
    print("TEST 2: Step Logic Validation")
    print("=" * 70)

    # Get all processes with steps
    cur.execute("""
        SELECT pr.process_id, pr.process_name, pr.category,
               array_agg(ps.step_name ORDER BY ps.step_number) as steps,
               array_agg(ps.is_blocking ORDER BY ps.step_number) as blocking,
               array_agg(ps.is_user_approval ORDER BY ps.step_number) as approvals
        FROM claude.process_registry pr
        JOIN claude.process_steps ps ON pr.process_id = ps.process_id
        GROUP BY pr.process_id, pr.process_name, pr.category
        ORDER BY pr.category, pr.process_id
    """)

    processes = cur.fetchall()

    passed = 0
    failed = 0
    issues = []

    for proc in processes:
        proc_issues = []

        # Rule 1: User approval steps should be blocking
        for i, (step, blocking, approval) in enumerate(zip(proc['steps'], proc['blocking'], proc['approvals'])):
            if approval and not blocking:
                proc_issues.append(f"Step {i+1} '{step}' has user_approval but is not blocking")

        # Rule 2: First step should typically be blocking (establishes context)
        if proc['steps'] and not proc['blocking'][0]:
            # Exception for simple processes
            if len(proc['steps']) > 2:
                proc_issues.append(f"First step '{proc['steps'][0]}' should probably be blocking")

        # Rule 3: PROC-PROJECT-001 must have user approval on first step
        if proc['process_id'] == 'PROC-PROJECT-001':
            if not proc['approvals'][0]:
                proc_issues.append("Project Init MUST have user approval on first step")

        # Rule 4: PROC-PROJECT-005 must have user approval step
        if proc['process_id'] == 'PROC-PROJECT-005':
            if True not in proc['approvals']:
                proc_issues.append("Major Change MUST have user approval somewhere")

        if proc_issues:
            print(f"  ISSUES: {proc['process_id']} - {proc['process_name']}")
            for issue in proc_issues:
                print(f"          - {issue}")
            issues.extend(proc_issues)
            failed += 1
        else:
            print(f"  OK: {proc['process_id']} - {proc['process_name']} ({len(proc['steps'])} steps)")
            passed += 1

    conn.close()
    return passed, failed, issues


def test_end_to_end_workflow():
    """Test that critical workflows make logical sense end-to-end."""
    conn = get_db()
    cur = conn.cursor()

    print("\n" + "=" * 70)
    print("TEST 3: End-to-End Workflow Logic")
    print("=" * 70)

    passed = 0
    failed = 0

    # Test 1: New Project Workflow
    print("\n  Workflow: NEW PROJECT (PROC-PROJECT-001)")
    cur.execute("""
        SELECT step_number, step_name, is_blocking, is_user_approval
        FROM claude.process_steps
        WHERE process_id = 'PROC-PROJECT-001'
        ORDER BY step_number
    """)
    steps = cur.fetchall()

    expected_flow = [
        ("Confirm", True),  # First must confirm with user
        ("Validate", True),  # Then validate name
        ("Create", True),   # Create directory
        ("Generate", True), # Generate docs
        ("Register", True), # Register in DB
    ]

    workflow_ok = True

    # Check first step is confirmation with user approval
    if not steps[0]['is_user_approval']:
        print(f"    FAIL: First step must require user approval")
        workflow_ok = False
    else:
        print(f"    OK: First step requires user approval")

    # Check critical steps are blocking
    blocking_steps = [s for s in steps if s['is_blocking']]
    if len(blocking_steps) < 5:
        print(f"    FAIL: Need at least 5 blocking steps, got {len(blocking_steps)}")
        workflow_ok = False
    else:
        print(f"    OK: Has {len(blocking_steps)} blocking steps")

    if workflow_ok:
        passed += 1
    else:
        failed += 1

    # Test 2: Major Change Workflow
    print("\n  Workflow: MAJOR CHANGE (PROC-PROJECT-005)")
    cur.execute("""
        SELECT step_number, step_name, is_blocking, is_user_approval
        FROM claude.process_steps
        WHERE process_id = 'PROC-PROJECT-005'
        ORDER BY step_number
    """)
    steps = cur.fetchall()

    workflow_ok = True

    # Must have user approval somewhere
    has_approval = any(s['is_user_approval'] for s in steps)
    if not has_approval:
        print(f"    FAIL: Must have user approval step")
        workflow_ok = False
    else:
        print(f"    OK: Has user approval step")

    # First step should recognize it's a major change
    if 'recognize' not in steps[0]['step_name'].lower() and 'stop' not in steps[0]['step_name'].lower():
        print(f"    WARN: First step should recognize/stop ({steps[0]['step_name']})")
    else:
        print(f"    OK: First step recognizes major change")

    if workflow_ok:
        passed += 1
    else:
        failed += 1

    # Test 3: Bug Fix Workflow
    print("\n  Workflow: BUG FIX (PROC-DEV-002)")
    cur.execute("""
        SELECT step_number, step_name, is_blocking
        FROM claude.process_steps
        WHERE process_id = 'PROC-DEV-002'
        ORDER BY step_number
    """)
    steps = cur.fetchall()

    workflow_ok = True
    step_names = [s['step_name'].lower() for s in steps]

    # Must include: create feedback, investigate, fix, test
    required = ['feedback', 'investigate', 'fix', 'test']
    for req in required:
        if not any(req in name for name in step_names):
            print(f"    FAIL: Missing step containing '{req}'")
            workflow_ok = False

    if workflow_ok:
        print(f"    OK: Has all required steps (feedback, investigate, fix, test)")
        passed += 1
    else:
        failed += 1

    # Test 4: Session End Workflow
    print("\n  Workflow: SESSION END (PROC-SESSION-002)")
    cur.execute("""
        SELECT step_number, step_name, is_blocking
        FROM claude.process_steps
        WHERE process_id = 'PROC-SESSION-002'
        ORDER BY step_number
    """)
    steps = cur.fetchall()

    workflow_ok = True
    step_names = [s['step_name'].lower() for s in steps]

    # Must include: summarize, update record
    if not any('summar' in name for name in step_names):
        print(f"    FAIL: Missing summarize step")
        workflow_ok = False
    if not any('update' in name and 'record' in name for name in step_names):
        print(f"    FAIL: Missing update record step")
        workflow_ok = False

    if workflow_ok:
        print(f"    OK: Has summarize and update record steps")
        passed += 1
    else:
        failed += 1

    conn.close()
    return passed, failed


def test_coverage():
    """Test that all categories have adequate coverage."""
    conn = get_db()
    cur = conn.cursor()

    print("\n" + "=" * 70)
    print("TEST 4: Category Coverage")
    print("=" * 70)

    cur.execute("""
        SELECT category,
               COUNT(*) as total_processes,
               COUNT(CASE WHEN (SELECT COUNT(*) FROM claude.process_triggers pt WHERE pt.process_id = pr.process_id) > 0 THEN 1 END) as with_triggers,
               COUNT(CASE WHEN (SELECT COUNT(*) FROM claude.process_steps ps WHERE ps.process_id = pr.process_id) > 0 THEN 1 END) as with_steps
        FROM claude.process_registry pr
        GROUP BY category
        ORDER BY category
    """)

    categories = cur.fetchall()

    passed = 0
    failed = 0

    for cat in categories:
        trigger_pct = (cat['with_triggers'] / cat['total_processes']) * 100
        step_pct = (cat['with_steps'] / cat['total_processes']) * 100

        status = "OK" if trigger_pct >= 50 and step_pct >= 50 else "WARN"

        print(f"  {status}: {cat['category'].upper():10} - {cat['total_processes']} processes, {trigger_pct:.0f}% triggers, {step_pct:.0f}% steps")

        if trigger_pct >= 50 and step_pct >= 50:
            passed += 1
        else:
            failed += 1

    conn.close()
    return passed, failed


def main():
    """Run all regression tests."""
    print("=" * 70)
    print("PROCESS ENFORCEMENT SYSTEM - FULL REGRESSION TEST")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    # Test 1: Pattern Matching
    p, f = test_pattern_matching()
    total_passed += p
    total_failed += f
    print(f"\n  Pattern Matching: {p} passed, {f} failed")

    # Test 2: Step Logic
    p, f, issues = test_step_logic()
    total_passed += p
    total_failed += f
    print(f"\n  Step Logic: {p} passed, {f} failed")

    # Test 3: End-to-End Workflows
    p, f = test_end_to_end_workflow()
    total_passed += p
    total_failed += f
    print(f"\n  End-to-End Workflows: {p} passed, {f} failed")

    # Test 4: Coverage
    p, f = test_coverage()
    total_passed += p
    total_failed += f
    print(f"\n  Category Coverage: {p} passed, {f} failed")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Total: {total_passed} passed, {total_failed} failed")

    if total_failed == 0:
        print("\n  *** ALL TESTS PASSED - System is logically sound ***")
        return 0
    else:
        print(f"\n  *** {total_failed} TESTS FAILED - Review issues above ***")
        return 1


if __name__ == "__main__":
    sys.exit(main())
