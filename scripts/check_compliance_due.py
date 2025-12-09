#!/usr/bin/env python3
"""
Compliance Audit Checker - Scheduled Job

Checks for due audits and sends messages to projects that need auditing.
Projects pick up these messages on session start and run the appropriate audit.

Usage:
    python check_compliance_due.py

Author: claude-code-unified
Date: 2025-12-08
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

# Add config path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')

try:
    from config import POSTGRES_CONFIG
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_DB = True
except ImportError:
    HAS_DB = False
    CONN_STR = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'


def get_db_connection():
    """Get database connection."""
    if HAS_DB:
        try:
            return psycopg2.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)
        except Exception:
            pass
    # Fallback
    try:
        return psycopg2.connect(CONN_STR, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


def get_due_audits(conn) -> List[Dict]:
    """Get list of audits that are due."""
    cur = conn.cursor()
    cur.execute("""
        SELECT schedule_id, project_name, audit_type, frequency_days,
               last_audit_date, next_audit_date
        FROM claude.audits_due
        WHERE is_due = true
        ORDER BY project_name, audit_type
    """)
    return [dict(row) for row in cur.fetchall()]


def check_existing_message(conn, project_name: str, audit_type: str) -> bool:
    """Check if a pending audit message already exists for this project/type."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as count
        FROM claude.messages
        WHERE to_project = %s
          AND message_type = 'task_request'
          AND subject LIKE %s
          AND is_read = false
          AND created_at > NOW() - INTERVAL '7 days'
    """, (project_name, f'%{audit_type}%audit%'))
    result = cur.fetchone()
    return result['count'] > 0


def send_audit_message(conn, project_name: str, audit_type: str) -> bool:
    """Send message to project about due audit."""
    cur = conn.cursor()

    message_body = f"""A {audit_type} audit is due for {project_name}.

Please run the appropriate audit command:
- For governance: /check-compliance
- For documentation: /review-docs
- For data quality: /review-data
- For standards: Check against docs/standards/

After completing the audit, the results will be stored in claude.compliance_audits.
"""

    try:
        message_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO claude.messages (
                message_id, to_project, message_type, subject, body,
                priority, is_read, created_at
            )
            VALUES (%s, %s, 'task_request', %s, %s, 'normal', false, NOW())
        """, (
            message_id,
            project_name,
            f'{audit_type.title()} Audit Due',
            message_body
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Failed to send message to {project_name}: {e}")
        conn.rollback()
        return False


def create_pending_audit(conn, schedule_id: str, project_name: str, audit_type: str) -> Optional[str]:
    """Create a pending audit record."""
    cur = conn.cursor()
    try:
        audit_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO claude.compliance_audits (
                audit_id, project_name, audit_type, status, triggered_by
            )
            VALUES (%s, %s, %s, 'pending', 'scheduler')
            RETURNING audit_id
        """, (audit_id, project_name, audit_type))
        conn.commit()
        return audit_id
    except Exception as e:
        print(f"Failed to create audit record: {e}")
        conn.rollback()
        return None


def main():
    """Main entry point."""
    print(f"Compliance Audit Check - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    conn = get_db_connection()
    if not conn:
        print("ERROR: Could not connect to database")
        return 1

    # Get due audits
    due_audits = get_due_audits(conn)

    if not due_audits:
        print("No audits are due at this time.")
        conn.close()
        return 0

    print(f"Found {len(due_audits)} due audits:\n")

    messages_sent = 0
    for audit in due_audits:
        project = audit['project_name']
        audit_type = audit['audit_type']

        print(f"  [{project}] {audit_type} audit")

        # Check if message already sent
        if check_existing_message(conn, project, audit_type):
            print(f"    -> Message already pending, skipping")
            continue

        # Create pending audit record
        audit_id = create_pending_audit(conn, audit['schedule_id'], project, audit_type)
        if audit_id:
            print(f"    -> Created audit record: {audit_id[:8]}...")

        # Send message to project
        if send_audit_message(conn, project, audit_type):
            print(f"    -> Sent message to {project}")
            messages_sent += 1
        else:
            print(f"    -> Failed to send message")

    print(f"\n{messages_sent} message(s) sent.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
