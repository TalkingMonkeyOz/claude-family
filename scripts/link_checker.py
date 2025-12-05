#!/usr/bin/env python3
"""
Link Checker - Verifies document file paths exist

Checks all documents in claude.documents and reports:
- Files that no longer exist on disk
- Broken project links

Usage:
    python link_checker.py              # Check all documents
    python link_checker.py --fix        # Remove broken entries
    python link_checker.py --dry-run    # Preview without fixing
"""

import os
import sys
import argparse
from pathlib import Path
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


def get_db_connection():
    """Get PostgreSQL connection."""
    conn_str = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_str, row_factory=dict_row)
    else:
        return psycopg.connect(conn_str, cursor_factory=RealDictCursor)


def safe_print(msg: str):
    """Print with ASCII fallback for Windows console."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))


def check_documents(conn, fix: bool = False, dry_run: bool = False):
    """Check all document file paths."""
    cur = conn.cursor()

    cur.execute("""
        SELECT doc_id, doc_title, file_path, doc_type
        FROM claude.documents
        WHERE status = 'ACTIVE'
        ORDER BY file_path
    """)

    docs = cur.fetchall()
    cur.close()

    missing_files = []
    valid_count = 0

    print(f"\nChecking {len(docs)} documents...")
    print("-" * 60)

    for doc in docs:
        file_path = Path(doc['file_path'])

        if file_path.exists():
            valid_count += 1
        else:
            missing_files.append(doc)
            safe_print(f"  [MISSING] {doc['doc_title']}")
            safe_print(f"            {doc['file_path']}")

    print("-" * 60)
    print(f"Valid: {valid_count}")
    print(f"Missing: {len(missing_files)}")

    if missing_files and fix:
        print("\nFixing broken entries...")

        if dry_run:
            print("[DRY-RUN] Would mark as DELETED:")
            for doc in missing_files:
                safe_print(f"  - {doc['doc_title']}")
        else:
            cur = conn.cursor()
            for doc in missing_files:
                # Mark as deleted rather than actually deleting
                cur.execute("""
                    UPDATE claude.documents
                    SET status = 'DELETED', updated_at = NOW()
                    WHERE doc_id = %s
                """, (doc['doc_id'],))
                safe_print(f"  [MARKED DELETED] {doc['doc_title']}")

            conn.commit()
            cur.close()

    return missing_files


def check_project_links(conn):
    """Check document-project links for orphaned entries."""
    cur = conn.cursor()

    # Find links where document doesn't exist
    cur.execute("""
        SELECT dp.document_project_id, dp.doc_id, dp.project_id,
               d.doc_title, p.project_name
        FROM claude.document_projects dp
        LEFT JOIN claude.documents d ON dp.doc_id = d.doc_id
        LEFT JOIN claude.projects p ON dp.project_id = p.project_id
        WHERE d.doc_id IS NULL OR p.project_id IS NULL
    """)

    orphaned = cur.fetchall()
    cur.close()

    if orphaned:
        print(f"\nFound {len(orphaned)} orphaned document-project links:")
        for link in orphaned:
            doc_name = link.get('doc_title') or f"[missing doc: {link['doc_id']}]"
            proj_name = link.get('project_name') or f"[missing project: {link['project_id']}]"
            safe_print(f"  - {doc_name} -> {proj_name}")
    else:
        print("\nNo orphaned project links found.")

    return orphaned


def main():
    parser = argparse.ArgumentParser(description='Verify document file paths exist')
    parser.add_argument('--fix', '-f', action='store_true', help='Mark missing files as DELETED')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Preview without making changes')
    args = parser.parse_args()

    print("=" * 60)
    print("Link Checker - Verifying document file paths")
    print("=" * 60)

    conn = get_db_connection()

    # Check document file paths
    missing = check_documents(conn, fix=args.fix, dry_run=args.dry_run)

    # Check project links
    orphaned_links = check_project_links(conn)

    conn.close()

    print("\n" + "=" * 60)
    print("Link check complete")
    print("=" * 60)

    # Return exit code based on issues found
    if missing or orphaned_links:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
