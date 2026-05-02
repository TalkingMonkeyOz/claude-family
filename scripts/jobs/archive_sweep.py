#!/usr/bin/env python3
"""F224 archive_sweep.py — Nightly retention policy.

Move resolved task_queue rows to task_queue_archive.

Eligible for archival:
- status='completed' AND completed_at < now() - 90 days
- status='cancelled' AND completed_at < now() - 30 days
- status='dead_letter' AND resolution_status IS NOT NULL AND resolved_at < now() - 30 days

NEVER archives unresolved dead_letter (sticky-until-triaged per design Q5 lock).

Idempotent: re-running produces zero changes on already-archived rows.
Non-destructive: wraps both INSERT + DELETE in a transaction.
"""
import json
import os
import sys
from datetime import datetime

# Config module (shared with other scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
try:
    from config import DATABASE_URI as _db_uri
    DB_URI = _db_uri or os.environ.get("DATABASE_URI", "")
except Exception:
    DB_URI = os.environ.get("DATABASE_URI", "")


def main():
    """Archive eligible task_queue rows to task_queue_archive."""
    if not DB_URI:
        print(json.dumps({"success": False, "error": "DATABASE_URI not set"}))
        return 1

    import psycopg2
    try:
        conn = psycopg2.connect(DB_URI, connect_timeout=5)
        cur = conn.cursor()

        # Step 1: Identify eligible rows (don't delete yet — just count).
        cur.execute("""
            SELECT COUNT(*) FROM claude.task_queue
            WHERE (
                (status = 'completed' AND completed_at < now() - interval '90 days')
                OR
                (status = 'cancelled' AND completed_at < now() - interval '30 days')
                OR
                (status = 'dead_letter'
                 AND resolution_status IS NOT NULL
                 AND resolved_at < now() - interval '30 days')
            )
        """)
        eligible_count = cur.fetchone()[0]

        if eligible_count == 0:
            result = {"success": True, "archived_count": 0}
            print(json.dumps(result))
            cur.close()
            conn.close()
            return 0

        # Step 2: Begin transaction.
        # Insert eligible rows into archive (SELECT from current table).
        # OVERRIDE: worker_daemon — nightly archive retention.
        cur.execute("""
            INSERT INTO claude.task_queue_archive
            SELECT * FROM claude.task_queue
            WHERE (
                (status = 'completed' AND completed_at < now() - interval '90 days')
                OR
                (status = 'cancelled' AND completed_at < now() - interval '30 days')
                OR
                (status = 'dead_letter'
                 AND resolution_status IS NOT NULL
                 AND resolved_at < now() - interval '30 days')
            )
        """)

        # Step 3: Delete from live table (only rows we just archived).
        # OVERRIDE: worker_daemon — nightly archive retention.
        cur.execute("""
            DELETE FROM claude.task_queue
            WHERE task_id IN (
                SELECT task_id FROM claude.task_queue_archive
                WHERE (
                    (status = 'completed' AND completed_at < now() - interval '90 days')
                    OR
                    (status = 'cancelled' AND completed_at < now() - interval '30 days')
                    OR
                    (status = 'dead_letter'
                     AND resolution_status IS NOT NULL
                     AND resolved_at < now() - interval '30 days')
                )
            )
        """)

        # Commit transaction.
        conn.commit()

        result = {
            "success": True,
            "archived_count": eligible_count,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        print(json.dumps(result, default=str))

        cur.close()
        conn.close()
        return 0

    except Exception as e:
        # Rollback on any error (transaction safety).
        try:
            conn.rollback()
        except Exception:
            pass
        error_msg = str(e)
        print(json.dumps({"success": False, "error": error_msg}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
