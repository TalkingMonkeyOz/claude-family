#!/usr/bin/env python3
"""
Orphan Report - Reports documents not linked to any project

Identifies:
- Documents without project_id set
- Documents without entries in document_projects junction table
- High percentage of "OTHER" type documents

Usage:
    python orphan_report.py              # Generate report
    python orphan_report.py --verbose    # Include file paths
    python orphan_report.py --json       # Output as JSON
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


def get_orphan_stats(conn):
    """Get statistics about orphaned documents."""
    cur = conn.cursor()

    stats = {}

    # Total documents
    cur.execute("SELECT COUNT(*) as count FROM claude.documents WHERE status = 'ACTIVE'")
    stats['total_documents'] = cur.fetchone()['count']

    # Documents without project_id
    cur.execute("""
        SELECT COUNT(*) as count FROM claude.documents
        WHERE status = 'ACTIVE' AND project_id IS NULL
    """)
    stats['no_project_id'] = cur.fetchone()['count']

    # Documents without junction table link
    cur.execute("""
        SELECT COUNT(*) as count FROM claude.documents d
        WHERE d.status = 'ACTIVE'
          AND NOT EXISTS (
              SELECT 1 FROM claude.document_projects dp
              WHERE dp.doc_id = d.doc_id
          )
    """)
    stats['no_project_link'] = cur.fetchone()['count']

    # Documents with "OTHER" type
    cur.execute("""
        SELECT COUNT(*) as count FROM claude.documents
        WHERE status = 'ACTIVE' AND doc_type = 'OTHER'
    """)
    stats['other_type'] = cur.fetchone()['count']

    # Documents by type
    cur.execute("""
        SELECT doc_type, COUNT(*) as count
        FROM claude.documents
        WHERE status = 'ACTIVE'
        GROUP BY doc_type
        ORDER BY count DESC
    """)
    stats['by_type'] = [dict(row) for row in cur.fetchall()]

    # Core documents count
    cur.execute("""
        SELECT COUNT(*) as count FROM claude.documents
        WHERE status = 'ACTIVE' AND is_core = true
    """)
    stats['core_documents'] = cur.fetchone()['count']

    cur.close()
    return stats


def get_orphaned_documents(conn, limit: int = 50):
    """Get list of orphaned documents (no project link)."""
    cur = conn.cursor()

    cur.execute("""
        SELECT d.doc_id, d.doc_title, d.doc_type, d.file_path, d.is_core
        FROM claude.documents d
        WHERE d.status = 'ACTIVE'
          AND NOT EXISTS (
              SELECT 1 FROM claude.document_projects dp
              WHERE dp.doc_id = d.doc_id
          )
        ORDER BY d.doc_title
        LIMIT %s
    """, (limit,))

    docs = [dict(row) for row in cur.fetchall()]
    cur.close()
    return docs


def print_report(stats, orphans, verbose: bool = False):
    """Print the orphan report."""
    total = stats['total_documents']

    print("=" * 60)
    print("DOCUMENT ORPHAN REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    print(f"\nTotal Active Documents: {total}")
    print("-" * 40)

    # Orphan statistics
    no_id_pct = (stats['no_project_id'] / total * 100) if total > 0 else 0
    no_link_pct = (stats['no_project_link'] / total * 100) if total > 0 else 0
    other_pct = (stats['other_type'] / total * 100) if total > 0 else 0

    print(f"Without project_id:     {stats['no_project_id']:>5} ({no_id_pct:.1f}%)")
    print(f"Without project link:   {stats['no_project_link']:>5} ({no_link_pct:.1f}%)")
    print(f"Classified as OTHER:    {stats['other_type']:>5} ({other_pct:.1f}%)")
    print(f"Core documents:         {stats['core_documents']:>5}")

    # Health indicators
    print("\n" + "-" * 40)
    print("Health Indicators:")

    if no_link_pct < 10:
        print("  [OK] Orphan rate < 10%")
    elif no_link_pct < 30:
        print("  [WARNING] Orphan rate 10-30%")
    else:
        print("  [CRITICAL] Orphan rate > 30%")

    if other_pct < 20:
        print("  [OK] OTHER type < 20%")
    elif other_pct < 50:
        print("  [WARNING] OTHER type 20-50%")
    else:
        print("  [CRITICAL] OTHER type > 50%")

    # Type breakdown
    print("\n" + "-" * 40)
    print("Documents by Type:")
    for item in stats['by_type'][:15]:
        pct = item['count'] / total * 100 if total > 0 else 0
        safe_print(f"  {item['doc_type']:<20} {item['count']:>5} ({pct:.1f}%)")

    # Orphan list
    if orphans and verbose:
        print("\n" + "-" * 40)
        print(f"Orphaned Documents (showing {len(orphans)}):")
        for doc in orphans:
            core_label = " [CORE]" if doc.get('is_core') else ""
            safe_print(f"  - {doc['doc_title']} ({doc['doc_type']}){core_label}")
            if verbose:
                safe_print(f"    {doc['file_path']}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Report orphaned documents')
    parser.add_argument('--verbose', '-v', action='store_true', help='Include file paths')
    parser.add_argument('--json', '-j', action='store_true', help='Output as JSON')
    parser.add_argument('--limit', '-l', type=int, default=50, help='Max orphans to list')
    args = parser.parse_args()

    conn = get_db_connection()

    stats = get_orphan_stats(conn)
    orphans = get_orphaned_documents(conn, args.limit)

    conn.close()

    if args.json:
        output = {
            'generated': datetime.now().isoformat(),
            'stats': stats,
            'orphans': orphans[:args.limit]
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print_report(stats, orphans, verbose=args.verbose)

    # Exit with non-zero if orphan rate is high
    total = stats['total_documents']
    orphan_pct = (stats['no_project_link'] / total * 100) if total > 0 else 0

    if orphan_pct > 30:
        sys.exit(2)  # Critical
    elif orphan_pct > 10:
        sys.exit(1)  # Warning
    sys.exit(0)


if __name__ == "__main__":
    main()
