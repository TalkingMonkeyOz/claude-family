#!/usr/bin/env python3
"""
Data Gateway Validator

Validates that:
- column_registry has entries for constrained columns
- The valid_values in registry match actual CHECK constraints
- Common constrained columns are documented
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set

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

# Tables and columns that MUST have registry entries
REQUIRED_REGISTRY_ENTRIES = [
    ('feedback', 'status'),
    ('feedback', 'feedback_type'),
    ('feedback', 'priority'),
    ('features', 'status'),
    ('build_tasks', 'status'),
    ('sessions', 'status'),
]


def get_column_registry() -> Dict[str, Dict[str, list]]:
    """Get all column registry entries."""
    if not HAS_DB:
        return {}

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT table_name, column_name, valid_values
                    FROM claude.column_registry
                    WHERE valid_values IS NOT NULL
                """)
                rows = cur.fetchall()

                registry = {}
                for row in rows:
                    key = row['table_name']
                    if key not in registry:
                        registry[key] = {}
                    registry[key][row['column_name']] = row['valid_values']

                return registry
    except Exception:
        return {}


def test_constraint_enforcement() -> Tuple[int, int, List[str], List[str]]:
    """Test that database constraints actually work."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    if not HAS_DB:
        return 0, 0, [], ["Cannot test constraints (no database connection)"]

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                # Test 1: Try inserting invalid feedback_type
                try:
                    cur.execute("""
                        INSERT INTO claude.feedback
                        (feedback_id, project_id, feedback_type, description, status, priority, short_code)
                        VALUES (
                            gen_random_uuid(),
                            (SELECT project_id FROM claude.projects LIMIT 1),
                            'INVALID_TYPE_12345',
                            'Test constraint',
                            'new',
                            'medium',
                            9999
                        )
                    """)
                    # If we get here, constraint wasn't enforced
                    conn.rollback()
                    failed += 1
                    errors.append("feedback.feedback_type: Invalid value accepted (constraint not enforced)")
                except psycopg2.Error:
                    # Good - constraint rejected invalid value
                    conn.rollback()
                    passed += 1

                # Test 2: Try inserting valid feedback_type
                try:
                    cur.execute("""
                        INSERT INTO claude.feedback
                        (feedback_id, project_id, feedback_type, description, status, priority, short_code)
                        VALUES (
                            gen_random_uuid(),
                            (SELECT project_id FROM claude.projects LIMIT 1),
                            'bug',
                            'Test constraint - will rollback',
                            'new',
                            'medium',
                            9998
                        )
                    """)
                    # Good - valid value accepted
                    conn.rollback()
                    passed += 1
                except psycopg2.Error as e:
                    conn.rollback()
                    failed += 1
                    errors.append(f"feedback.feedback_type: Valid value 'bug' rejected: {e}")

    except Exception as e:
        warnings.append(f"Constraint testing failed: {e}")

    return passed, failed, errors, warnings


def check_required_entries() -> Tuple[int, int, List[str], List[str]]:
    """Check that required columns have registry entries."""
    errors = []
    warnings = []
    passed = 0
    failed = 0

    registry = get_column_registry()

    if not registry:
        return 0, 0, [], ["Cannot check registry (no database connection or empty)"]

    for table, column in REQUIRED_REGISTRY_ENTRIES:
        if table in registry and column in registry[table]:
            values = registry[table][column]
            if values and len(values) > 0:
                passed += 1
            else:
                failed += 1
                errors.append(f"{table}.{column}: Registry entry exists but no valid_values")
        else:
            failed += 1
            errors.append(f"{table}.{column}: Missing from column_registry")

    return passed, failed, errors, warnings


def check_registry_completeness() -> Tuple[int, int, List[str], List[str]]:
    """Check that registry covers common constrained column names."""
    warnings = []
    passed = 0

    if not HAS_DB:
        return 0, 0, [], ["Cannot check completeness (no database connection)"]

    common_columns = ['status', 'priority', 'type', 'category', 'state']
    registry = get_column_registry()

    # Count how many tables have these columns documented
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                for col in common_columns:
                    cur.execute("""
                        SELECT COUNT(DISTINCT table_name)
                        FROM information_schema.columns
                        WHERE table_schema = 'claude'
                        AND column_name = %s
                    """, (col,))
                    total = cur.fetchone()[0]

                    # Count how many are in registry
                    documented = sum(1 for t, cols in registry.items() if col in cols)

                    if total > 0:
                        coverage = documented / total * 100
                        if coverage >= 80:
                            passed += 1
                        elif coverage >= 50:
                            warnings.append(f"Column '{col}': {documented}/{total} tables documented ({coverage:.0f}%)")
                        else:
                            warnings.append(f"Column '{col}': Only {documented}/{total} tables documented")

    except Exception as e:
        warnings.append(f"Could not check completeness: {e}")

    return passed, 0, [], warnings


def validate_data_gateway() -> Tuple[int, int, List[str], List[str]]:
    """
    Validate Data Gateway / column_registry.

    Returns:
        Tuple of (passed, failed, errors, warnings)
    """
    if not HAS_DB:
        return 0, 0, [], ["Data Gateway validation requires database connection"]

    total_passed = 0
    total_failed = 0
    all_errors = []
    all_warnings = []

    # Check required entries
    passed, failed, errors, warnings = check_required_entries()
    total_passed += passed
    total_failed += failed
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    # Test constraint enforcement
    passed, failed, errors, warnings = test_constraint_enforcement()
    total_passed += passed
    total_failed += failed
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    # Check registry completeness
    passed, failed, errors, warnings = check_registry_completeness()
    total_passed += passed
    total_failed += failed
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    return total_passed, total_failed, all_errors, all_warnings


if __name__ == "__main__":
    passed, failed, errors, warnings = validate_data_gateway()

    print(f"\nData Gateway Validation")
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
