#!/usr/bin/env python3
"""
Schema Documentation and Governance Tool

Introspects the PostgreSQL database (claude schema in ai_company_foundation) and:
1. Introspects all tables from information_schema + pg_catalog
2. Generates COMMENT ON statements for tables/columns that are missing descriptions
3. Syncs column_registry from CHECK constraints
4. Updates schema_registry to cover all tables (100 of 100 as of 2026-02-28)
5. Reports coverage gaps

Usage:
    python schema_docs.py --report [--json]
    python schema_docs.py --generate-comments [--output FILE]
    python schema_docs.py --apply-comments [--output FILE]
    python schema_docs.py --sync-registry
    python schema_docs.py --sync-column-registry
    python schema_docs.py --all [--output FILE]

Examples:
    # Show coverage report
    python schema_docs.py --report

    # Generate SQL comments without applying
    python schema_docs.py --generate-comments --output schema_comments.sql

    # Apply comments to database
    python schema_docs.py --apply-comments

    # Run full audit + sync
    python schema_docs.py --all --output schema_updates.sql
"""

import sys
import os
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict

# Add scripts directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class TableInfo:
    """Represents a table in the schema."""
    name: str
    has_comment: bool
    column_count: int
    in_schema_registry: bool
    in_column_registry: int  # Number of columns in registry
    has_check_constraints: int  # Number of CHECK constraints


@dataclass
class ColumnInfo:
    """Represents a column in the schema."""
    table_name: str
    column_name: str
    data_type: str
    is_nullable: bool
    has_comment: bool
    is_fk: bool
    fk_table: Optional[str] = None
    fk_column: Optional[str] = None
    check_constraint: Optional[str] = None


# ============================================================================
# Heuristic Descriptions
# ============================================================================

COLUMN_DESCRIPTIONS = {
    'created_at': 'Timestamp when the record was created',
    'updated_at': 'Timestamp when the record was last updated',
    'project_id': 'Foreign key to claude.projects',
    'session_id': 'Foreign key to claude.sessions',
    'feature_id': 'Foreign key to claude.features',
    'feedback_id': 'Foreign key to claude.feedback',
    'identity_id': 'Foreign key to claude.identities',
    'is_active': 'Whether this record is currently active',
    'is_archived': 'Whether this record has been archived',
    'status': 'Current status (see column_registry for valid values)',
    'priority': 'Priority level (1=critical, 5=low)',
    'description': 'Human-readable description',
    'embedding': 'Voyage AI vector embedding (1024 dimensions)',
    'id': 'Unique identifier for this record',
    'name': 'Name or title',
    'title': 'Title or heading',
    'content': 'Main content or body text',
    'data': 'JSON or structured data',
    'config': 'Configuration data',
    'metadata': 'Additional metadata',
    'type': 'Type or category classification',
    'owner': 'Owner or creator identifier',
}


# ============================================================================
# Query Functions
# ============================================================================

def get_all_tables(conn) -> List[str]:
    """Get all tables in claude schema."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute("""
                SELECT c.relname as table_name
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'claude' AND c.relkind = 'r'
                ORDER BY c.relname
            """)
            return [row['table_name'] for row in cur.fetchall()]
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute("""
                SELECT c.relname as table_name
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'claude' AND c.relkind = 'r'
                ORDER BY c.relname
            """)
            return [row['table_name'] for row in cur.fetchall()]


def get_tables_with_comments(conn) -> set:
    """Get set of tables that have COMMENT ON."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute("""
                SELECT c.relname as table_name
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_catalog.pg_description d ON d.objoid = c.oid AND d.objsubid = 0
                WHERE n.nspname = 'claude' AND c.relkind = 'r'
                ORDER BY c.relname
            """)
            return {row['table_name'] for row in cur.fetchall()}
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute("""
                SELECT c.relname as table_name
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_catalog.pg_description d ON d.objoid = c.oid AND d.objsubid = 0
                WHERE n.nspname = 'claude' AND c.relkind = 'r'
                ORDER BY c.relname
            """)
            return {row['table_name'] for row in cur.fetchall()}


def get_column_info(conn) -> Dict[str, List[ColumnInfo]]:
    """Get detailed info about all columns."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    query = """
        SELECT
            c.table_name, c.column_name, c.data_type, c.is_nullable,
            ccu.table_name as fk_table, ccu.column_name as fk_column
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON c.table_schema = kcu.table_schema
            AND c.table_name = kcu.table_name
            AND c.column_name = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name
            AND kcu.constraint_schema = tc.constraint_schema
            AND tc.constraint_type = 'FOREIGN KEY'
        LEFT JOIN information_schema.referential_constraints rc
            ON tc.constraint_name = rc.constraint_name
            AND tc.constraint_schema = rc.constraint_schema
        LEFT JOIN information_schema.constraint_column_usage ccu
            ON rc.unique_constraint_name = ccu.constraint_name
            AND rc.unique_constraint_schema = ccu.constraint_schema
        WHERE c.table_schema = 'claude'
        ORDER BY c.table_name, c.ordinal_position
    """

    columns_by_table = {}

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                table_name = row['table_name']
                if table_name not in columns_by_table:
                    columns_by_table[table_name] = []

                col_info = ColumnInfo(
                    table_name=table_name,
                    column_name=row['column_name'],
                    data_type=row['data_type'],
                    is_nullable=row['is_nullable'] == 'YES',
                    has_comment=False,  # Will be filled in later
                    is_fk=row['fk_table'] is not None,
                    fk_table=row['fk_table'],
                    fk_column=row['fk_column']
                )
                columns_by_table[table_name].append(col_info)
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                table_name = row['table_name']
                if table_name not in columns_by_table:
                    columns_by_table[table_name] = []

                col_info = ColumnInfo(
                    table_name=table_name,
                    column_name=row['column_name'],
                    data_type=row['data_type'],
                    is_nullable=row['is_nullable'] == 'YES',
                    has_comment=False,  # Will be filled in later
                    is_fk=row['fk_table'] is not None,
                    fk_table=row['fk_table'],
                    fk_column=row['fk_column']
                )
                columns_by_table[table_name].append(col_info)

    return columns_by_table


def get_columns_with_comments(conn) -> Dict[Tuple[str, str], str]:
    """Get set of (table, column) pairs that have COMMENT ON."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    query = """
        SELECT a.attname as column_name, c.relname as table_name, d.description
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
        JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid
        JOIN pg_catalog.pg_description d ON d.objoid = c.oid AND d.objsubid = a.attnum
        WHERE n.nspname = 'claude' AND c.relkind = 'r'
        AND a.attnum > 0 AND NOT a.attisdropped
    """

    comments = {}

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                key = (row['table_name'], row['column_name'])
                comments[key] = row['description']
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                key = (row['table_name'], row['column_name'])
                comments[key] = row['description']

    return comments


def get_check_constraints(conn) -> Dict[Tuple[str, str], str]:
    """Get CHECK constraints for column_registry extraction."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    query = """
        SELECT
            tc.table_name,
            kcu.column_name,
            cc.check_clause
        FROM information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc
            ON tc.constraint_name = cc.constraint_name
            AND tc.constraint_schema = cc.constraint_schema
        JOIN information_schema.constraint_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.constraint_schema = kcu.constraint_schema
        WHERE tc.table_schema = 'claude'
            AND tc.constraint_type = 'CHECK'
        ORDER BY tc.table_name, kcu.column_name
    """

    constraints = {}

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                key = (row['table_name'], row['column_name'])
                constraints[key] = row['check_clause']
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query)
            for row in cur.fetchall():
                key = (row['table_name'], row['column_name'])
                constraints[key] = row['check_clause']

    return constraints


def get_schema_registry_tables(conn) -> set:
    """Get tables already in schema_registry."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    query = "SELECT table_name FROM claude.schema_registry"

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query)
            return {row['table_name'] for row in cur.fetchall()}
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query)
            return {row['table_name'] for row in cur.fetchall()}


def get_column_registry_count(conn, table_name: str) -> int:
    """Count how many columns of a table are in column_registry."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    query = """
        SELECT COUNT(*) as cnt FROM claude.column_registry
        WHERE table_name = %s
    """

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query, (table_name,))
            result = cur.fetchone()
            return result['cnt'] if result else 0
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query, (table_name,))
            result = cur.fetchone()
            return result['cnt'] if result else 0


def get_check_constraint_count(conn, table_name: str) -> int:
    """Count CHECK constraints for a table."""
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    query = """
        SELECT COUNT(DISTINCT tc.constraint_name) as cnt
        FROM information_schema.table_constraints tc
        WHERE tc.table_schema = 'claude'
            AND tc.table_name = %s
            AND tc.constraint_type = 'CHECK'
    """

    if version == 3:
        with conn.cursor(row_factory=dict_row_factory) as cur:
            cur.execute(query, (table_name,))
            result = cur.fetchone()
            return result['cnt'] if result else 0
    else:
        with conn.cursor(cursor_factory=cursor_class) as cur:
            cur.execute(query, (table_name,))
            result = cur.fetchone()
            return result['cnt'] if result else 0


# ============================================================================
# Report Generation
# ============================================================================

def generate_report(conn) -> Dict[str, Any]:
    """Generate comprehensive schema coverage report."""
    logger.info("Collecting schema information...")

    all_tables = get_all_tables(conn)
    tables_with_comments = get_tables_with_comments(conn)
    schema_registry_tables = get_schema_registry_tables(conn)

    tables_info = []
    total_columns = 0
    columns_with_comments = 0
    total_col_registry = 0
    total_check_constraints = 0

    for table in all_tables:
        col_count = len([c for c in get_column_info(conn).get(table, [])])
        has_comment = table in tables_with_comments
        in_schema_registry = table in schema_registry_tables
        col_registry_count = get_column_registry_count(conn, table)
        check_constraint_count = get_check_constraint_count(conn, table)

        tables_info.append(TableInfo(
            name=table,
            has_comment=has_comment,
            column_count=col_count,
            in_schema_registry=in_schema_registry,
            in_column_registry=col_registry_count,
            has_check_constraints=check_constraint_count
        ))

        total_columns += col_count
        total_col_registry += col_registry_count
        total_check_constraints += check_constraint_count

    # Count columns with comments
    col_comments = get_columns_with_comments(conn)
    columns_with_comments = len(col_comments)

    # Calculate coverage
    tables_with_comments_count = len(tables_with_comments)
    schema_registry_count = len(schema_registry_tables)

    report = {
        'timestamp': str(Path(sys.argv[0]).stat().st_mtime),
        'summary': {
            'total_tables': len(all_tables),
            'total_columns': total_columns,
            'tables_with_comments': {
                'count': tables_with_comments_count,
                'percentage': round(100 * tables_with_comments_count / len(all_tables), 1) if all_tables else 0
            },
            'columns_with_comments': {
                'count': columns_with_comments,
                'percentage': round(100 * columns_with_comments / total_columns, 1) if total_columns else 0
            },
            'schema_registry': {
                'count': schema_registry_count,
                'percentage': round(100 * schema_registry_count / len(all_tables), 1) if all_tables else 0
            },
            'column_registry': {
                'count': total_col_registry,
                'percentage': round(100 * total_col_registry / total_columns, 1) if total_columns else 0
            },
            'check_constraints': {
                'count': total_check_constraints,
                'tables_with_constraints': len([t for t in tables_info if t.has_check_constraints > 0])
            }
        },
        'tables': [asdict(t) for t in tables_info],
        'gaps': {
            'missing_comments': [t.name for t in tables_info if not t.has_comment],
            'missing_schema_registry': [t.name for t in tables_info if not t.in_schema_registry],
            'missing_column_registry': [t.name for t in tables_info if t.in_column_registry == 0]
        }
    }

    return report


def print_report(report: Dict[str, Any], json_output: bool = False):
    """Print formatted report."""
    if json_output:
        print(json.dumps(report, indent=2))
        return

    summary = report['summary']
    gaps = report['gaps']

    print("\nSchema Governance Report - claude.*")
    print("=" * 70)
    print(f"Tables: {summary['total_tables']} | Columns: {summary['total_columns']}")
    print("-" * 70)
    print(f"Table Comments:    {summary['tables_with_comments']['count']}/{summary['total_tables']:3d} ({summary['tables_with_comments']['percentage']:5.1f}%)")
    print(f"Column Comments:   {summary['columns_with_comments']['count']}/{summary['total_columns']:3d} ({summary['columns_with_comments']['percentage']:5.1f}%)")
    print(f"schema_registry:   {summary['schema_registry']['count']}/{summary['total_tables']:3d} ({summary['schema_registry']['percentage']:5.1f}%)")
    print(f"column_registry:   {summary['column_registry']['count']}/{summary['total_columns']:3d} ({summary['column_registry']['percentage']:5.1f}%)")
    print(f"CHECK constraints: {summary['check_constraints']['count']} (in {summary['check_constraints']['tables_with_constraints']} tables)")
    print("-" * 70)

    if gaps['missing_comments']:
        print(f"\nMissing COMMENT ON ({len(gaps['missing_comments'])} tables):")
        for table in gaps['missing_comments'][:10]:
            print(f"  - {table}")
        if len(gaps['missing_comments']) > 10:
            print(f"  ... and {len(gaps['missing_comments']) - 10} more")

    if gaps['missing_schema_registry']:
        print(f"\nMissing from schema_registry ({len(gaps['missing_schema_registry'])} tables):")
        for table in gaps['missing_schema_registry'][:10]:
            print(f"  - {table}")
        if len(gaps['missing_schema_registry']) > 10:
            print(f"  ... and {len(gaps['missing_schema_registry']) - 10} more")

    if gaps['missing_column_registry']:
        print(f"\nMissing from column_registry ({len(gaps['missing_column_registry'])} tables):")
        for table in gaps['missing_column_registry'][:10]:
            print(f"  - {table}")
        if len(gaps['missing_column_registry']) > 10:
            print(f"  ... and {len(gaps['missing_column_registry']) - 10} more")

    print()


# ============================================================================
# Comment Generation
# ============================================================================

def infer_column_description(column_name: str, data_type: str, is_fk: bool = False,
                            fk_table: Optional[str] = None) -> str:
    """Infer column description from name and type."""
    # Check heuristics first
    if column_name.lower() in COLUMN_DESCRIPTIONS:
        return COLUMN_DESCRIPTIONS[column_name.lower()]

    # FK hint
    if is_fk and fk_table:
        return f'Foreign key to claude.{fk_table}'

    # Type-based hints
    if data_type.startswith('boolean') or data_type.startswith('bool'):
        if 'active' in column_name.lower():
            return 'Whether this record is currently active'
        elif 'archive' in column_name.lower():
            return 'Whether this record has been archived'
        else:
            return 'Boolean flag'

    if 'uuid' in data_type.lower():
        return 'Unique identifier (UUID)'

    if 'timestamp' in data_type.lower() or 'time' in data_type.lower():
        return 'Timestamp'

    if 'integer' in data_type.lower() or 'int' in data_type.lower():
        if 'count' in column_name.lower():
            return 'Count'
        else:
            return 'Integer value'

    if 'text' in data_type.lower() or 'varchar' in data_type.lower():
        if 'description' in column_name.lower() or 'comment' in column_name.lower():
            return 'Text description'
        else:
            return 'Text value'

    if 'json' in data_type.lower():
        return 'JSON data'

    # Default fallback
    return f'Column of type {data_type}'


def infer_table_description(table_name: str, columns: List[ColumnInfo]) -> str:
    """Infer table description from name and columns."""
    # Convert snake_case to readable format
    readable_name = table_name.replace('_', ' ').title()

    # Check for known patterns
    if table_name.startswith('v_'):
        return f'View of {readable_name[2:]}'

    if table_name.endswith('_history'):
        return f'Audit history for {readable_name[:-8]}'

    if table_name.endswith('_registry'):
        return f'Registry of {readable_name[:-9]}'

    # Build description from columns
    col_names = [c.column_name for c in columns[:3]]

    return f'{readable_name} (contains: {", ".join(col_names)})'


def generate_comment_sql(conn) -> Tuple[List[str], List[str]]:
    """Generate COMMENT ON SQL statements for missing comments."""
    logger.info("Generating COMMENT ON statements...")

    all_tables = get_all_tables(conn)
    tables_with_comments = get_tables_with_comments(conn)
    col_comments = get_columns_with_comments(conn)
    columns_by_table = get_column_info(conn)

    table_comments = []
    column_comments = []

    for table_name in all_tables:
        # Generate table comment if missing
        if table_name not in tables_with_comments:
            columns = columns_by_table.get(table_name, [])
            description = infer_table_description(table_name, columns)
            escaped_desc = description.replace("'", "''")
            table_comments.append(
                f"COMMENT ON TABLE claude.{table_name} IS '{escaped_desc}';"
            )

        # Generate column comments if missing
        columns = columns_by_table.get(table_name, [])
        for col in columns:
            col_key = (table_name, col.column_name)
            if col_key not in col_comments:
                description = infer_column_description(
                    col.column_name,
                    col.data_type,
                    col.is_fk,
                    col.fk_table
                )
                escaped_desc = description.replace("'", "''")
                column_comments.append(
                    f"COMMENT ON COLUMN claude.{table_name}.{col.column_name} IS '{escaped_desc}';"
                )

    return table_comments, column_comments


# ============================================================================
# Apply Comments
# ============================================================================

def apply_comments(conn, table_comments: List[str], column_comments: List[str]):
    """Apply COMMENT ON statements to database."""
    mod, version, _, _ = detect_psycopg()

    total = len(table_comments) + len(column_comments)
    logger.info(f"Applying {total} COMMENT ON statements...")

    all_statements = table_comments + column_comments

    try:
        if version == 3:
            with conn.cursor() as cur:
                for i, statement in enumerate(all_statements, 1):
                    cur.execute(statement)
                    if i % 50 == 0:
                        logger.info(f"Applied {i}/{total} comments")
            conn.commit()
        else:
            with conn.cursor() as cur:
                for i, statement in enumerate(all_statements, 1):
                    cur.execute(statement)
                    if i % 50 == 0:
                        logger.info(f"Applied {i}/{total} comments")
            conn.commit()

        logger.info(f"Successfully applied all {total} COMMENT ON statements")
    except Exception as e:
        logger.error(f"Error applying comments: {e}")
        conn.rollback()
        raise


# ============================================================================
# Sync Registry
# ============================================================================

def sync_schema_registry(conn):
    """Insert missing tables into schema_registry."""
    logger.info("Syncing schema_registry...")

    all_tables = get_all_tables(conn)
    schema_registry_tables = get_schema_registry_tables(conn)
    columns_by_table = get_column_info(conn)

    missing_tables = [t for t in all_tables if t not in schema_registry_tables]
    logger.info(f"Found {len(missing_tables)} tables missing from schema_registry")

    if not missing_tables:
        logger.info("No tables to sync")
        return

    mod, version, _, _ = detect_psycopg()

    try:
        if version == 3:
            with conn.cursor() as cur:
                for table_name in missing_tables:
                    columns = columns_by_table.get(table_name, [])
                    purpose = infer_table_description(table_name, columns)

                    cur.execute("""
                        INSERT INTO claude.schema_registry (table_name, purpose, owner, category, created_by)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (table_name) DO NOTHING
                    """, (table_name, purpose, 'claude-family', 'auto-synced', 'schema_docs.py'))
                    logger.info(f"Synced {table_name}")
            conn.commit()
        else:
            with conn.cursor() as cur:
                for table_name in missing_tables:
                    columns = columns_by_table.get(table_name, [])
                    purpose = infer_table_description(table_name, columns)

                    cur.execute("""
                        INSERT INTO claude.schema_registry (table_name, purpose, owner, category, created_by)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (table_name) DO NOTHING
                    """, (table_name, purpose, 'claude-family', 'auto-synced', 'schema_docs.py'))
                    logger.info(f"Synced {table_name}")
            conn.commit()

        logger.info(f"Successfully synced {len(missing_tables)} tables to schema_registry")
    except Exception as e:
        logger.error(f"Error syncing schema_registry: {e}")
        conn.rollback()
        raise


def sync_column_registry(conn):
    """Sync column_registry from CHECK constraints."""
    logger.info("Syncing column_registry from CHECK constraints...")

    check_constraints = get_check_constraints(conn)
    logger.info(f"Found {len(check_constraints)} constrained columns")

    if not check_constraints:
        logger.info("No CHECK constraints found")
        return

    mod, version, _, _ = detect_psycopg()

    # Parse constraint expressions to extract valid values
    # Example: "status = ANY (ARRAY['new'::text, 'triaged'::text, 'in_progress'::text])"

    try:
        import json as _json
        with conn.cursor() as cur:
            for (table_name, column_name), constraint_expr in check_constraints.items():
                valid_values = extract_valid_values(constraint_expr)

                if valid_values:
                    # valid_values is JSONB, constraints is TEXT
                    # data_type is NOT NULL so provide a default
                    cur.execute("""
                        INSERT INTO claude.column_registry
                        (table_name, column_name, data_type, valid_values, constraints)
                        VALUES (%s, %s, 'character varying', %s::jsonb, %s)
                        ON CONFLICT (table_name, column_name) DO UPDATE
                        SET valid_values = EXCLUDED.valid_values,
                            constraints = EXCLUDED.constraints
                    """, (table_name, column_name, _json.dumps(valid_values), constraint_expr))
                    logger.info(f"Synced {table_name}.{column_name}: {len(valid_values)} values")
        conn.commit()

        logger.info(f"Successfully synced column_registry from CHECK constraints")
    except Exception as e:
        logger.error(f"Error syncing column_registry: {e}")
        conn.rollback()
        raise


def extract_valid_values(constraint_expr: str) -> Optional[List[str]]:
    """Extract valid values from CHECK constraint expression.

    Examples:
    - "status = ANY (ARRAY['new'::text, 'triaged'::text])" → ['new', 'triaged']
    - "priority >= 1 AND priority <= 5" → None (numeric range)
    """
    import re

    # Pattern: status = ANY (ARRAY['val1'::text, 'val2'::text, ...])
    pattern = r"ARRAY\[(.*?)\]"
    match = re.search(pattern, constraint_expr, re.IGNORECASE)

    if match:
        values_str = match.group(1)
        # Extract quoted strings
        values = re.findall(r"'([^']*)'", values_str)
        return values if values else None

    return None


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Schema documentation and governance tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--report', action='store_true',
                      help='Show coverage report only')
    parser.add_argument('--generate-comments', action='store_true',
                      help='Generate COMMENT ON SQL')
    parser.add_argument('--apply-comments', action='store_true',
                      help='Apply COMMENT ON to database')
    parser.add_argument('--sync-registry', action='store_true',
                      help='Sync schema_registry for missing tables')
    parser.add_argument('--sync-column-registry', action='store_true',
                      help='Derive column_registry from CHECK constraints')
    parser.add_argument('--all', action='store_true',
                      help='Run full audit + sync')
    parser.add_argument('--output', help='Output SQL file for --generate-comments')
    parser.add_argument('--json', action='store_true',
                      help='JSON output for --report')

    args = parser.parse_args()

    # Default to report if no action specified
    if not any([args.report, args.generate_comments, args.apply_comments,
                args.sync_registry, args.sync_column_registry, args.all]):
        args.report = True

    # Connect to database
    logger.info("Connecting to PostgreSQL...")
    conn = get_db_connection(strict=True)

    try:
        if args.all:
            # Run full audit + sync
            report = generate_report(conn)
            print_report(report, args.json)

            table_comments, column_comments = generate_comment_sql(conn)
            apply_comments(conn, table_comments, column_comments)
            sync_schema_registry(conn)
            sync_column_registry(conn)

        elif args.report:
            report = generate_report(conn)
            print_report(report, args.json)

        elif args.generate_comments:
            table_comments, column_comments = generate_comment_sql(conn)

            all_comments = table_comments + column_comments

            if args.output:
                logger.info(f"Writing {len(all_comments)} comments to {args.output}")
                with open(args.output, 'w') as f:
                    f.write("-- Schema Comments (Generated)\n")
                    f.write("-- Auto-generated by schema_docs.py\n\n")
                    for stmt in all_comments:
                        f.write(stmt + "\n")
                logger.info(f"Wrote {len(all_comments)} statements to {args.output}")
            else:
                for stmt in all_comments:
                    print(stmt)

        elif args.apply_comments:
            table_comments, column_comments = generate_comment_sql(conn)
            apply_comments(conn, table_comments, column_comments)

        elif args.sync_registry:
            sync_schema_registry(conn)

        elif args.sync_column_registry:
            sync_column_registry(conn)

    finally:
        conn.close()
        logger.info("Database connection closed")


if __name__ == '__main__':
    main()
