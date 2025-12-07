#!/usr/bin/env python3
"""
Documentation Staleness Reviewer

Finds documents that may be outdated based on:
- Last modified date > 30 days
- References to files that no longer exist
- Version numbers that don't match current

Usage:
    python reviewer_doc_staleness.py [--project PROJECT] [--fix]
"""

import os
import sys
import io
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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


STALENESS_THRESHOLD_DAYS = 30
CRITICAL_DOC_TYPES = ['CLAUDE_CONFIG', 'ARCHITECTURE', 'SOP']


def get_db_connection():
    """Get PostgreSQL connection."""
    conn_str = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_str, row_factory=dict_row)
    else:
        return psycopg.connect(conn_str, cursor_factory=RealDictCursor)


def log_run_start(conn, project_name):
    """Log reviewer run start."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claude.reviewer_runs (reviewer_type, project_name, triggered_by, status)
        VALUES ('doc-staleness', %s, 'manual', 'running')
        RETURNING run_id
    """, (project_name,))
    result = cur.fetchone()
    conn.commit()
    return result['run_id'] if isinstance(result, dict) else result[0]


def log_run_complete(conn, run_id, findings, summary, issues_found):
    """Log reviewer run completion."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE claude.reviewer_runs
        SET status = 'completed',
            completed_at = NOW(),
            findings = %s,
            summary = %s,
            issues_found = %s
        WHERE run_id = %s
    """, (json.dumps(findings), summary, issues_found, run_id))
    conn.commit()


def check_stale_documents(conn, project_name=None):
    """Find documents that haven't been updated recently."""
    cur = conn.cursor()

    query = """
        SELECT
            d.doc_id,
            d.doc_title,
            d.doc_type,
            d.file_path,
            d.updated_at,
            d.status,
            EXTRACT(DAY FROM NOW() - d.updated_at) as days_since_update,
            p.project_name
        FROM claude.documents d
        LEFT JOIN claude.document_projects dp ON d.doc_id = dp.doc_id
        LEFT JOIN claude.projects p ON dp.project_id = p.project_id
        WHERE d.status = 'ACTIVE'
          AND d.updated_at < NOW() - INTERVAL '%s days'
    """

    params = [STALENESS_THRESHOLD_DAYS]

    if project_name:
        query += " AND p.project_name = %s"
        params.append(project_name)

    query += " ORDER BY d.updated_at ASC LIMIT 50"

    cur.execute(query, params)
    return cur.fetchall()


def check_missing_file_references(conn, project_name=None):
    """Find documents that reference files that no longer exist."""
    cur = conn.cursor()

    query = """
        SELECT doc_id, doc_title, file_path, doc_type
        FROM claude.documents
        WHERE status = 'ACTIVE'
    """

    if project_name:
        query += f" AND file_path ILIKE '%{project_name}%'"

    cur.execute(query)
    docs = cur.fetchall()

    missing = []
    for doc in docs:
        file_path = doc['file_path']
        if file_path and not Path(file_path).exists():
            missing.append(doc)

    return missing


def check_critical_doc_staleness(conn, project_name=None):
    """Check if critical docs (CLAUDE.md, ARCHITECTURE) are stale."""
    cur = conn.cursor()

    query = """
        SELECT
            d.doc_id,
            d.doc_title,
            d.doc_type,
            d.file_path,
            d.updated_at,
            EXTRACT(DAY FROM NOW() - d.updated_at) as days_since_update,
            p.project_name
        FROM claude.documents d
        LEFT JOIN claude.document_projects dp ON d.doc_id = dp.doc_id
        LEFT JOIN claude.projects p ON dp.project_id = p.project_id
        WHERE d.status = 'ACTIVE'
          AND d.doc_type IN ('CLAUDE_CONFIG', 'ARCHITECTURE', 'SOP')
          AND d.updated_at < NOW() - INTERVAL '14 days'
    """

    if project_name:
        query += f" AND p.project_name = '{project_name}'"

    query += " ORDER BY d.updated_at ASC"

    cur.execute(query)
    return cur.fetchall()


def main():
    parser = argparse.ArgumentParser(description='Check for stale documentation')
    parser.add_argument('--project', '-p', help='Specific project to check')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    conn = get_db_connection()
    run_id = log_run_start(conn, args.project)

    findings = {
        'stale_documents': [],
        'missing_files': [],
        'critical_stale': []
    }

    print("=" * 60)
    print("Documentation Staleness Review")
    print(f"Project: {args.project or 'ALL'}")
    print(f"Threshold: {STALENESS_THRESHOLD_DAYS} days")
    print("=" * 60)

    # Check stale documents
    print("\n## Stale Documents (not updated in 30+ days)")
    stale = check_stale_documents(conn, args.project)
    for doc in stale:
        days = int(doc['days_since_update'])
        findings['stale_documents'].append({
            'doc_id': str(doc['doc_id']),
            'title': doc['doc_title'],
            'type': doc['doc_type'],
            'days_stale': days,
            'project': doc['project_name']
        })
        print(f"  - [{doc['doc_type']}] {doc['doc_title']} ({days} days)")

    if not stale:
        print("  No stale documents found.")

    # Check missing files
    print("\n## Missing Files (document exists but file doesn't)")
    missing = check_missing_file_references(conn, args.project)
    for doc in missing:
        findings['missing_files'].append({
            'doc_id': str(doc['doc_id']),
            'title': doc['doc_title'],
            'file_path': doc['file_path']
        })
        print(f"  - {doc['doc_title']}")
        print(f"    Path: {doc['file_path']}")

    if not missing:
        print("  All document files exist.")

    # Check critical docs
    print("\n## Critical Documents Needing Review (14+ days)")
    critical = check_critical_doc_staleness(conn, args.project)
    for doc in critical:
        days = int(doc['days_since_update'])
        findings['critical_stale'].append({
            'doc_id': str(doc['doc_id']),
            'title': doc['doc_title'],
            'type': doc['doc_type'],
            'days_stale': days,
            'project': doc['project_name']
        })
        print(f"  - [{doc['doc_type']}] {doc['doc_title']} ({days} days) - {doc['project_name']}")

    if not critical:
        print("  All critical documents are up to date.")

    # Apply fixes if requested
    fixed_count = 0
    if args.fix and missing:
        print("\n## Applying Fixes")
        print("  Archiving documents with missing files...")
        cur = conn.cursor()
        for doc in missing:
            cur.execute("""
                UPDATE claude.documents
                SET status = 'ARCHIVED',
                    updated_at = NOW()
                WHERE doc_id = %s AND status = 'ACTIVE'
                RETURNING doc_id
            """, (doc['doc_id'],))
            if cur.fetchone():
                fixed_count += 1
                print(f"    ✓ Archived: {doc['doc_title']}")
        conn.commit()
        print(f"  Archived {fixed_count} documents with missing files")

    # Summary
    total_issues = len(stale) + len(missing) + len(critical)
    summary = f"Found {total_issues} issues: {len(stale)} stale, {len(missing)} missing, {len(critical)} critical"
    if args.fix:
        summary += f", {fixed_count} fixed"

    print("\n" + "=" * 60)
    print(f"Summary: {summary}")
    print("=" * 60)

    # Log completion
    log_run_complete(conn, run_id, findings, summary, total_issues - fixed_count)

    if args.json:
        print("\nJSON Output:")
        print(json.dumps(findings, indent=2))

    conn.close()
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
