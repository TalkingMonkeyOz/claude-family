#!/usr/bin/env python3
"""
Schema Validation Script

Validates that database views and tables have expected columns.
Prevents breaking changes to shared schema objects.

Usage:
    python validate_schema.py [--view VIEW_NAME] [--table TABLE_NAME] [--all]

Exit codes:
    0 = All validations passed
    1 = Validation failures found
"""

import json
import sys
import argparse
from datetime import datetime

# Database imports
DB_AVAILABLE = False
try:
    import psycopg
    from psycopg.rows import dict_row
    DB_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        DB_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        DB_AVAILABLE = False

CONN_STR = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'

# Expected columns for critical views/tables
# Add entries here when views are created or modified
EXPECTED_SCHEMAS = {
    'v_core_documents': {
        'type': 'view',
        'required_columns': [
            'doc_id', 'doc_title', 'doc_type', 'file_path', 'status',
            'project_id', 'project_name', 'is_core', 'updated_at'
        ],
        'consumers': ['mission-control-web']
    },
    'project_governance': {
        'type': 'view',
        'required_columns': [
            'project_id', 'project_name', 'status', 'phase',
            'has_claude_md', 'has_problem_statement', 'has_architecture',
            'feature_count', 'open_task_count'
        ],
        'consumers': ['mission-control-web', 'claude-family']
    },
    'projects': {
        'type': 'table',
        'required_columns': [
            'project_id', 'project_name', 'status', 'phase', 'description',
            'is_archived', 'created_at', 'updated_at'
        ],
        'consumers': ['mission-control-web', 'claude-family', 'all']
    },
    'sessions': {
        'type': 'table',
        'required_columns': [
            'session_id', 'identity_id', 'project_name', 'session_start',
            'session_end', 'session_summary'
        ],
        'consumers': ['mission-control-web', 'claude-family']
    },
    'feedback': {
        'type': 'table',
        'required_columns': [
            'feedback_id', 'project_id', 'feedback_type', 'description',
            'status', 'priority', 'created_at'
        ],
        'consumers': ['mission-control-web']
    },
    'features': {
        'type': 'table',
        'required_columns': [
            'feature_id', 'project_id', 'feature_name', 'status', 'priority'
        ],
        'consumers': ['mission-control-web']
    },
    'build_tasks': {
        'type': 'table',
        'required_columns': [
            'task_id', 'feature_id', 'task_name', 'status', 'priority'
        ],
        'consumers': ['mission-control-web']
    },
    'documents': {
        'type': 'table',
        'required_columns': [
            'doc_id', 'doc_title', 'doc_type', 'file_path', 'status',
            'is_core', 'is_current_version'
        ],
        'consumers': ['mission-control-web']
    }
}


def get_db_connection():
    """Get PostgreSQL connection."""
    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(CONN_STR, row_factory=dict_row)
        else:
            return psycopg.connect(CONN_STR, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Database connection failed: {e}", file=sys.stderr)
        return None


def get_actual_columns(conn, object_name: str, object_type: str) -> list:
    """Get actual columns from a table or view."""
    cur = conn.cursor()

    # Determine if it's a view or table
    if object_type == 'view':
        # Check in views
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'claude'
              AND table_name = %s
            ORDER BY ordinal_position
        """, (object_name,))
    else:
        # Check in tables
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'claude'
              AND table_name = %s
            ORDER BY ordinal_position
        """, (object_name,))

    results = cur.fetchall()
    cur.close()

    return [r['column_name'] if isinstance(r, dict) else r[0] for r in results]


def validate_object(conn, object_name: str, expected: dict, verbose: bool = False) -> dict:
    """Validate a single table or view."""
    result = {
        'object': object_name,
        'type': expected['type'],
        'passed': True,
        'missing_columns': [],
        'extra_columns': [],
        'consumers': expected.get('consumers', [])
    }

    actual_columns = get_actual_columns(conn, object_name, expected['type'])

    if not actual_columns:
        result['passed'] = False
        result['error'] = f"Object '{object_name}' not found in claude schema"
        return result

    required_columns = set(expected['required_columns'])
    actual_set = set(actual_columns)

    # Find missing required columns
    missing = required_columns - actual_set
    if missing:
        result['passed'] = False
        result['missing_columns'] = list(missing)

    # Find extra columns (informational only)
    extra = actual_set - required_columns
    if extra and verbose:
        result['extra_columns'] = list(extra)

    return result


def validate_all(conn, verbose: bool = False) -> dict:
    """Validate all registered objects."""
    results = {
        'validated_at': datetime.now().isoformat(),
        'total': len(EXPECTED_SCHEMAS),
        'passed': 0,
        'failed': 0,
        'objects': []
    }

    for object_name, expected in EXPECTED_SCHEMAS.items():
        result = validate_object(conn, object_name, expected, verbose)
        results['objects'].append(result)

        if result['passed']:
            results['passed'] += 1
        else:
            results['failed'] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description='Validate database schema objects')
    parser.add_argument('--view', help='Validate specific view')
    parser.add_argument('--table', help='Validate specific table')
    parser.add_argument('--all', action='store_true', help='Validate all registered objects')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show extra columns')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    if not DB_AVAILABLE:
        print("ERROR: psycopg not available", file=sys.stderr)
        return 1

    conn = get_db_connection()
    if not conn:
        return 1

    try:
        if args.view:
            if args.view not in EXPECTED_SCHEMAS:
                print(f"WARNING: View '{args.view}' not in registry, checking database...")
                actual = get_actual_columns(conn, args.view, 'view')
                if actual:
                    print(f"Columns in {args.view}: {', '.join(actual)}")
                    return 0
                else:
                    print(f"ERROR: View '{args.view}' not found")
                    return 1

            result = validate_object(conn, args.view, EXPECTED_SCHEMAS[args.view], args.verbose)
            results = {'objects': [result]}

        elif args.table:
            if args.table not in EXPECTED_SCHEMAS:
                print(f"WARNING: Table '{args.table}' not in registry, checking database...")
                actual = get_actual_columns(conn, args.table, 'table')
                if actual:
                    print(f"Columns in {args.table}: {', '.join(actual)}")
                    return 0
                else:
                    print(f"ERROR: Table '{args.table}' not found")
                    return 1

            result = validate_object(conn, args.table, EXPECTED_SCHEMAS[args.table], args.verbose)
            results = {'objects': [result]}

        else:
            # Default: validate all
            results = validate_all(conn, args.verbose)

        # Output
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("=" * 60)
            print("Schema Validation Results")
            print("=" * 60)

            for obj in results['objects']:
                status = "[PASS]" if obj['passed'] else "[FAIL]"
                print(f"\n{status} {obj['type']}: {obj['object']}")

                if obj.get('error'):
                    print(f"  Error: {obj['error']}")

                if obj.get('missing_columns'):
                    print(f"  Missing columns: {', '.join(obj['missing_columns'])}")
                    print(f"  Affected consumers: {', '.join(obj['consumers'])}")

                if obj.get('extra_columns') and args.verbose:
                    print(f"  Extra columns: {', '.join(obj['extra_columns'])}")

            if 'total' in results:
                print("\n" + "=" * 60)
                print(f"Summary: {results['passed']}/{results['total']} passed")
                if results['failed'] > 0:
                    print(f"         {results['failed']} FAILED - fix before committing!")
                print("=" * 60)

        # Exit code
        failed = sum(1 for obj in results['objects'] if not obj['passed'])
        return 1 if failed > 0 else 0

    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
