#!/usr/bin/env python3
"""F224 dead_letter_sweep.py — Tier 3 surfacing.

Scheduled daily. For each task_queue row where:
  status='dead_letter' AND completed_at < now() - 24 hours
  AND surfaced_as_feedback_id IS NULL
  AND resolution_status IS NULL
... creates a feedback row (type='bug', priority='medium') and links it
via surfaced_as_feedback_id.

Findings emitted as JSON for the worker D2 routing system. When run manually,
also creates feedback rows directly via SQL.

Non-destructive + idempotent: re-running produces zero changes on already-surfaced rows.
"""
import json
import os
import sys
from datetime import datetime
from typing import Optional
from uuid import uuid4

# Config module (shared with other scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
try:
    from config import DATABASE_URI as _db_uri
    DB_URI = _db_uri or os.environ.get("DATABASE_URI", "")
except Exception:
    DB_URI = os.environ.get("DATABASE_URI", "")


def main():
    """Sweep stuck dead_letter rows and surface as feedback."""
    if not DB_URI:
        print(json.dumps({"success": False, "error": "DATABASE_URI not set"}))
        return 1

    import psycopg2
    try:
        conn = psycopg2.connect(DB_URI, connect_timeout=5)
        cur = conn.cursor()

        # Step 1: Find stuck dead_letter rows (>24h, unsurfaced, unresolved).
        cur.execute("""
            SELECT task_id, template_id, completed_at, last_error, attempts
            FROM claude.task_queue
            WHERE status = 'dead_letter'
              AND completed_at < now() - interval '24 hours'
              AND surfaced_as_feedback_id IS NULL
              AND resolution_status IS NULL
            ORDER BY completed_at ASC
        """)
        rows = cur.fetchall()

        if not rows:
            result = {"success": True, "stuck_count": 0}
            print(json.dumps(result))
            cur.close()
            conn.close()
            return 0

        # Step 2: Create feedback row for each stuck task + update task_queue.
        findings = []
        for task_id, template_id, completed_at, last_error, attempts in rows:
            days_stuck = (datetime.now(completed_at.tzinfo) - completed_at).days

            # Build feedback description
            error_preview = (last_error or "No error recorded")[:200]
            description = (
                f"F224 dead_letter task stuck for {days_stuck} days.\n"
                f"Task ID: {task_id}\n"
                f"Template ID: {template_id}\n"
                f"Attempts: {attempts}\n"
                f"Last error: {error_preview}"
            )

            # Create feedback row (use SQL — standard INSERT path)
            # Generate feedback_id since feedback table requires it
            feedback_id = str(uuid4())
            cur.execute("""
                INSERT INTO claude.feedback (
                    feedback_id, project_id, feedback_type, title, description, priority, status
                ) VALUES (
                    %s, NULL, 'bug', 'Dead-letter task stuck >24h', %s, 2, 'new'
                )
            """, (feedback_id, description))


            # OVERRIDE: worker_daemon — Tier 3 surfacing link
            cur.execute("""
                UPDATE claude.task_queue
                SET surfaced_as_feedback_id = %s
                WHERE task_id = %s
            """, (feedback_id, task_id))

            findings.append({
                "task_id": str(task_id),
                "template_id": str(template_id) if template_id else None,
                "days_stuck": days_stuck,
                "feedback_id": str(feedback_id),
                "error_preview": error_preview,
            })

        # Commit all updates together
        conn.commit()

        result = {
            "success": True,
            "stuck_count": len(findings),
            "findings": findings,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        print(json.dumps(result, default=str))

        cur.close()
        conn.close()
        return 0

    except Exception as e:
        error_msg = str(e)
        print(json.dumps({"success": False, "error": error_msg}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
