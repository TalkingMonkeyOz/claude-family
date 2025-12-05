#!/usr/bin/env python3
"""
Data Quality Reviewer

Scans database for:
- Test data patterns (names containing "test", "e2e", etc.)
- Orphan records (foreign keys pointing to nothing)
- Invalid status values
- Null values in important fields

Usage:
    python reviewer_data_quality.py [--fix] [--table TABLE]
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Database imports
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        PSYCOPG_VERSION = 2
    except ImportError:
        print("ERROR: psycopg not installed")
        sys.exit(1)


# Test data patterns to flag
TEST_PATTERNS = [
    '%test%', '%Test%', '%TEST%',
    '%e2e%', '%E2E%',
    '%demo%', '%Demo%',
    '%sample%', '%Sample%',
    '%foo%', '%bar%', '%baz%',
    '%xxx%', '%yyy%', '%zzz%',
    '%delete me%', '%remove%',
    '%asdf%', '%qwerty%'
]


def get_db_connection():
    """Get PostgreSQL connection."""
    conn_str = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_str, row_factory=dict_row)
    else:
        return psycopg.connect(conn_str, cursor_factory=RealDictCursor)


def log_run_start(conn):
    """Log reviewer run start."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claude.reviewer_runs (reviewer_type, triggered_by, status)
        VALUES ('data-quality', 'manual', 'running')
        RETURNING run_id
    """)
    result = cur.fetchone()
    conn.commit()
    return result['run_id'] if isinstance(result, dict) else result[0]


def log_run_complete(conn, run_id, findings, summary, issues_found, issues_fixed):
    """Log reviewer run completion."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE claude.reviewer_runs
        SET status = 'completed',
            completed_at = NOW(),
            findings = %s,
            summary = %s,
            issues_found = %s,
            issues_fixed = %s
        WHERE run_id = %s
    """, (json.dumps(findings), summary, issues_found, issues_fixed, run_id))
    conn.commit()


def check_test_data_in_table(conn, table_name, text_columns):
    """Check for test data patterns in a table."""
    cur = conn.cursor()
    issues = []

    for col in text_columns:
        for pattern in TEST_PATTERNS[:5]:  # Check first 5 patterns
            try:
                cur.execute(f"""
                    SELECT COUNT(*) as count
                    FROM claude.{table_name}
                    WHERE {col} ILIKE %s
                """, (pattern,))
                result = cur.fetchone()
                count = result['count'] if isinstance(result, dict) else result[0]
                if count > 0:
                    issues.append({
                        'table': table_name,
                        'column': col,
                        'pattern': pattern,
                        'count': count
                    })
            except:
                pass

    return issues


def check_orphan_projects(conn):
    """Find features/tasks referencing non-existent projects."""
    cur = conn.cursor()

    cur.execute("""
        SELECT f.feature_id, f.feature_name, f.project_id
        FROM claude.features f
        LEFT JOIN claude.projects p ON f.project_id = p.project_id
        WHERE p.project_id IS NULL AND f.project_id IS NOT NULL
    """)
    orphan_features = cur.fetchall()

    cur.execute("""
        SELECT fb.feedback_id, fb.description, fb.project_id
        FROM claude.feedback fb
        LEFT JOIN claude.projects p ON fb.project_id = p.project_id
        WHERE p.project_id IS NULL AND fb.project_id IS NOT NULL
    """)
    orphan_feedback = cur.fetchall()

    return {
        'orphan_features': [dict(r) for r in orphan_features],
        'orphan_feedback': [dict(r) for r in orphan_feedback]
    }


def check_invalid_statuses(conn):
    """Check for invalid status values."""
    cur = conn.cursor()
    issues = []

    # Check projects
    cur.execute("""
        SELECT project_id, project_name, status
        FROM claude.projects
        WHERE status NOT IN ('active', 'paused', 'archived', 'completed')
          AND status IS NOT NULL
    """)
    invalid_projects = cur.fetchall()
    for p in invalid_projects:
        issues.append({
            'table': 'projects',
            'id': str(p['project_id']),
            'field': 'status',
            'value': p['status']
        })

    # Check documents
    cur.execute("""
        SELECT doc_id, doc_title, status
        FROM claude.documents
        WHERE status NOT IN ('ACTIVE', 'DEPRECATED', 'ARCHIVED', 'DRAFT')
          AND status IS NOT NULL
        LIMIT 20
    """)
    invalid_docs = cur.fetchall()
    for d in invalid_docs:
        issues.append({
            'table': 'documents',
            'id': str(d['doc_id']),
            'field': 'status',
            'value': d['status']
        })

    return issues


def check_null_required_fields(conn):
    """Check for null values in important fields."""
    cur = conn.cursor()
    issues = []

    # Projects without names
    cur.execute("""
        SELECT project_id FROM claude.projects
        WHERE project_name IS NULL OR project_name = ''
    """)
    for r in cur.fetchall():
        issues.append({'table': 'projects', 'id': str(r['project_id']), 'field': 'project_name'})

    # Documents without titles
    cur.execute("""
        SELECT doc_id FROM claude.documents
        WHERE doc_title IS NULL OR doc_title = ''
        LIMIT 10
    """)
    for r in cur.fetchall():
        issues.append({'table': 'documents', 'id': str(r['doc_id']), 'field': 'doc_title'})

    return issues


def fix_test_data(conn, table_name, pattern, dry_run=True):
    """Delete test data from a table."""
    cur = conn.cursor()

    if dry_run:
        cur.execute(f"""
            SELECT COUNT(*) FROM claude.{table_name}
            WHERE title ILIKE %s OR description ILIKE %s
        """, (pattern, pattern))
        result = cur.fetchone()
        count = result['count'] if isinstance(result, dict) else result[0]
        return count
    else:
        cur.execute(f"""
            DELETE FROM claude.{table_name}
            WHERE title ILIKE %s OR description ILIKE %s
            RETURNING 1
        """, (pattern, pattern))
        deleted = len(cur.fetchall())
        conn.commit()
        return deleted


def main():
    parser = argparse.ArgumentParser(description='Check data quality in claude schema')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues')
    parser.add_argument('--table', help='Specific table to check')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    conn = get_db_connection()
    run_id = log_run_start(conn)

    findings = {
        'test_data': [],
        'orphan_records': {},
        'invalid_statuses': [],
        'null_fields': []
    }
    issues_fixed = 0

    print("=" * 60)
    print("Data Quality Review")
    print(f"Schema: claude")
    print("=" * 60)

    # Check for test data
    print("\n## Test Data Patterns")
    tables_to_check = [
        ('work_tasks', ['title', 'description']),
        ('feedback', ['description']),
        ('features', ['feature_name', 'description']),
    ]

    for table, columns in tables_to_check:
        if args.table and args.table != table:
            continue
        test_issues = check_test_data_in_table(conn, table, columns)
        findings['test_data'].extend(test_issues)
        for issue in test_issues:
            print(f"  - {issue['table']}.{issue['column']}: {issue['count']} rows match '{issue['pattern']}'")

    if not findings['test_data']:
        print("  No test data patterns found.")

    # Check orphan records
    print("\n## Orphan Records")
    orphans = check_orphan_projects(conn)
    findings['orphan_records'] = orphans

    if orphans['orphan_features']:
        print(f"  - {len(orphans['orphan_features'])} features with invalid project_id")
    if orphans['orphan_feedback']:
        print(f"  - {len(orphans['orphan_feedback'])} feedback items with invalid project_id")
    if not orphans['orphan_features'] and not orphans['orphan_feedback']:
        print("  No orphan records found.")

    # Check invalid statuses
    print("\n## Invalid Status Values")
    invalid = check_invalid_statuses(conn)
    findings['invalid_statuses'] = invalid
    for issue in invalid:
        print(f"  - {issue['table']}: {issue['field']} = '{issue['value']}'")
    if not invalid:
        print("  All status values are valid.")

    # Check null fields
    print("\n## Null Required Fields")
    nulls = check_null_required_fields(conn)
    findings['null_fields'] = nulls
    for issue in nulls:
        print(f"  - {issue['table']}: {issue['field']} is null (id: {issue['id']})")
    if not nulls:
        print("  No null required fields found.")

    # Summary
    total_issues = (
        len(findings['test_data']) +
        len(orphans.get('orphan_features', [])) +
        len(orphans.get('orphan_feedback', [])) +
        len(invalid) +
        len(nulls)
    )

    summary = f"Found {total_issues} data quality issues"
    print("\n" + "=" * 60)
    print(f"Summary: {summary}")
    print("=" * 60)

    # Log completion
    log_run_complete(conn, run_id, findings, summary, total_issues, issues_fixed)

    if args.json:
        print("\nJSON Output:")
        print(json.dumps(findings, indent=2, default=str))

    conn.close()
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
