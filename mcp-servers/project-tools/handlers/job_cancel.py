"""
job_cancel.py — Atomic job cancellation handler.

BT703: Atomic, single-purpose MCP handler for cancelling tasks in the task_queue.
Implements two cancellation modes:
- Soft (force=False, default): Sets cancel_requested=true for in_progress tasks,
  allowing graceful exit. Immediately cancels pending tasks.
- Hard (force=True): Revokes the lease (claimed_until=now()) for in_progress tasks,
  forcing lease-revoked error on next heartbeat. Immediately cancels pending tasks.

Terminal tasks (completed, failed, cancelled, dead_letter, superseded) cannot be cancelled.

Key behaviors:
- Pending tasks: UPDATE status='cancelled', completed_at=now()
- In-progress + soft: UPDATE cancel_requested=true (worker checks between steps)
- In-progress + force: UPDATE status='cancelled', completed_at=now(), claimed_until=now()
- Terminal tasks: Error (already terminal)
- Audits every cancellation to claude.audit_log with reason

No action discrimination; single entry point: handle_job_cancel().
"""

import json
import os
from typing import Optional
from datetime import datetime
import psycopg
from psycopg.rows import dict_row


def get_db_connection():
    """Get PostgreSQL connection for task queue operations."""
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')
    if not conn_string:
        raise RuntimeError("DATABASE_URI or POSTGRES_CONNECTION_STRING env var required")
    return psycopg.connect(conn_string, row_factory=dict_row)


def handle_job_cancel(
    task_id: str,
    force: bool = False,
    reason: Optional[str] = None,
    cancelling_session_id: Optional[str] = None,
) -> dict:
    """
    Atomic job cancellation handler.

    Cancels a task in the task_queue. Behavior depends on task status:
    - pending: Immediately set to cancelled
    - in_progress + force=False: Set cancel_requested=true (soft cancel)
    - in_progress + force=True: Set status=cancelled, revoke lease (hard cancel)
    - Terminal (completed, failed, cancelled, dead_letter, superseded): Error

    Args:
        task_id: Task UUID (required).
        force: If False (default), soft cancel (cancel_requested for in_progress).
               If True, hard cancel (immediate status change + lease revocation).
        reason: Optional reason for cancellation (audited).
        cancelling_session_id: Session ID requesting the cancellation (for audit trail).

    Returns:
        {
            "success": bool,
            "task_id": str (UUID),
            "previous_status": str,
            "action": "cancelled" | "cancel_requested" | "already_terminal",
            "message": str
        }

    Raises:
        ValueError: task_id missing, task already terminal, DB error.
        RuntimeError: DB connection failure, task not found.
    """
    # Validate inputs
    if not task_id:
        raise ValueError("task_id is required")

    reason = reason or "Cancelled via MCP job_cancel handler"

    conn = get_db_connection()
    cur = None

    try:
        cur = conn.cursor()

        # 1. Fetch current task status
        cur.execute("""
            SELECT task_id::text, status, claimed_until, started_at
            FROM claude.task_queue
            WHERE task_id = %s::uuid
        """, (task_id,))

        task_row = cur.fetchone()
        if not task_row:
            raise RuntimeError(f"Task not found: {task_id}")

        current_status = task_row['status']
        claimed_until = task_row['claimed_until']
        started_at = task_row['started_at']

        # 2. Check if task is already terminal
        terminal_statuses = {'completed', 'failed', 'cancelled', 'dead_letter', 'superseded'}
        if current_status in terminal_statuses:
            return {
                "success": False,
                "task_id": task_id,
                "previous_status": current_status,
                "action": "already_terminal",
                "error": f"Task is already in terminal status: {current_status}. Cannot cancel.",
                "message": f"Cannot cancel task {task_id}: already {current_status}"
            }

        # 3. Handle cancellation based on status and force flag
        if current_status == 'pending':
            # Pending tasks: immediate cancellation
            cur.execute("""
                UPDATE claude.task_queue
                SET status = 'cancelled', completed_at = NOW()
                WHERE task_id = %s::uuid
            """, (task_id,))
            action = "cancelled"

        elif current_status == 'in_progress':
            if force:
                # Hard cancel: revoke lease + change status
                cur.execute("""
                    UPDATE claude.task_queue
                    SET status = 'cancelled', completed_at = NOW(), claimed_until = NOW()
                    WHERE task_id = %s::uuid
                """, (task_id,))
                action = "cancelled"
            else:
                # Soft cancel: set cancel_requested flag
                # Note: cancel_requested column needs to exist (BT694 schema migration)
                # If column doesn't exist yet, this will fail gracefully
                cur.execute("""
                    UPDATE claude.task_queue
                    SET cancel_requested = true
                    WHERE task_id = %s::uuid
                """, (task_id,))
                action = "cancel_requested"

        # 4. Audit the cancellation
        cur.execute("""
            INSERT INTO claude.audit_log
                (entity_type, entity_id, from_status, to_status,
                 change_source, metadata, event_type)
            VALUES (%s, %s::uuid, %s, %s, %s, %s, %s)
        """, (
            'task_queue',
            task_id,
            current_status,
            'cancelled' if action == 'cancelled' else current_status,
            'job_cancel_handler',
            json.dumps({
                'previous_status': current_status,
                'action': action,
                'force': force,
                'reason': reason,
                'cancelling_session_id': cancelling_session_id,
            }),
            'cancel',
        ))

        conn.commit()

        result = {
            "success": True,
            "task_id": task_id,
            "previous_status": current_status,
            "action": action,
            "force_applied": force if current_status == 'in_progress' else None,
        }

        if action == "cancel_requested":
            result["message"] = f"Task {task_id} cancel requested (soft). Worker will exit gracefully."
        elif action == "cancelled":
            if force and current_status == 'in_progress':
                result["message"] = f"Task {task_id} cancelled with force (lease revoked). Worker will hit lease-revoked on next heartbeat."
            else:
                result["message"] = f"Task {task_id} cancelled."

        return result

    except psycopg.Error as e:
        conn.rollback()
        # Check if this is the "column doesn't exist" error for cancel_requested
        if "cancel_requested" in str(e) and "does not exist" in str(e):
            raise RuntimeError(
                f"Schema migration BT694 not yet applied: cancel_requested column missing from task_queue. "
                f"Cannot perform soft cancel. {e}"
            )
        else:
            raise RuntimeError(f"Database error during cancellation: {e}")

    finally:
        if cur:
            cur.close()
        conn.close()
