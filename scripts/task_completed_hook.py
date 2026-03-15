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
        if conn:
            cur = conn.cursor()
            # Mark matching todo as completed if it exists
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
                f"%{task_subject[:50]}%" if task_subject else "%"
            ))
            updated = cur.rowcount
            conn.commit()
            conn.close()

            if updated > 0:
                logger.info(f"Matched and completed todo in DB: {task_subject}")
            else:
                logger.debug(f"No matching todo found for: {task_subject}")
    except Exception as e:
        logger.warning(f"Failed to sync task completion to DB: {e}")

    # Allow completion (exit 0)
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
