#!/usr/bin/env python3
"""
TaskCompleted Hook — fires when a task is marked complete.

Syncs completed task to claude.todos for cross-session history.
Can enforce quality gates (exit 2 to block completion).

Hook event: TaskCompleted
Matchers: none (fires on all task completions)
"""

import json
import sys
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher

try:
    from config import setup_hook_logging
    setup_hook_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("task_completed")


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        hook_input = {}

    task_id = hook_input.get("task_id", "")
    task_subject = hook_input.get("task_subject", "")
    session_id = hook_input.get("session_id", "")

    logger.info(f"TaskCompleted: {task_subject} (id={task_id})")

    # Sync to claude.todos for history
    try:
        from config import get_db_connection
        conn = get_db_connection()
        if conn and task_subject:
            cur = conn.cursor()

            # Step 1: Try exact match first, fall back to ILIKE
            cur.execute("""
                UPDATE claude.todos
                SET status = 'completed',
                    completed_at = NOW(),
                    completed_session_id = %s
                WHERE content = %s
                  AND status IN ('pending', 'in_progress')
                LIMIT 1
            """, (
                session_id if session_id else None,
                task_subject,
            ))
            updated = cur.rowcount

            if updated == 0:
                # Fall back to ILIKE pattern match
                cur.execute("""
                    UPDATE claude.todos
                    SET status = 'completed',
                        completed_at = NOW(),
                        completed_session_id = %s
                    WHERE content ILIKE %s
                      AND status IN ('pending', 'in_progress')
                    LIMIT 1
                """, (
                    session_id if session_id else None,
                    f"%{task_subject[:50]}%",
                ))
                updated = cur.rowcount

            if updated > 0:
                logger.info(f"Matched and completed todo in DB: {task_subject}")
            else:
                logger.debug(f"No matching todo found for: {task_subject}")

            # Step 2: Build task reconciliation
            # If a build_task was just completed (via complete_work), find and
            # close the matching todo so both systems stay in sync.
            try:
                cur.execute("""
                    SELECT bt.id, bt.task_name
                    FROM claude.build_tasks bt
                    WHERE bt.status = 'completed'
                    ORDER BY bt.updated_at DESC
                    LIMIT 20
                """)
                recent_tasks = cur.fetchall()

                for bt_id, bt_name in recent_tasks:
                    ratio = SequenceMatcher(None, task_subject.lower(), bt_name.lower()).ratio()
                    if ratio >= 0.8:
                        cur.execute("""
                            UPDATE claude.todos
                            SET status = 'completed',
                                completed_at = NOW(),
                                completed_session_id = %s
                            WHERE content ILIKE %s
                              AND status IN ('pending', 'in_progress')
                            LIMIT 1
                        """, (
                            session_id if session_id else None,
                            f"%{bt_name[:50]}%",
                        ))
                        if cur.rowcount > 0:
                            logger.info(f"Reconciled: task '{task_subject}' -> todo completed (matched BT '{bt_name}', similarity={ratio:.2f})")
                        break
            except Exception as e:
                logger.warning(f"Build task reconciliation failed (non-fatal): {e}")

            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to sync task completion to DB: {e}")

    # Allow completion (exit 0)
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
