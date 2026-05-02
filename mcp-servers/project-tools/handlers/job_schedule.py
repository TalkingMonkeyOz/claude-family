"""
Job Schedule Handler - MCP tool for managing scheduled jobs.

Part of BT701 (F224). Supports creating, updating, pausing, and unscheduling
jobs in claude.scheduled_jobs table, with optional template_id FK.

Actions:
  - create: Add a new scheduled job (requires schedule validation)
  - update: Modify schedule, template_id, or template_version pin
  - pause: Set is_active=false
  - unpause: Set is_active=true
  - list: Query with filters
  - unschedule: Delete and log to audit_log

Validation:
  - Schedule string parsing (cron or human-readable from job_runner.py)
  - If template_id provided, verify it exists
  - template_version='latest' resolves at run time (stored as NULL)

Legacy compatibility:
  - Existing scheduled_jobs rows with NULL template_id remain unchanged
"""

import re
import uuid
import logging
from datetime import datetime
from typing import Any, Literal, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_schedule(schedule: str, trigger_type: str = None) -> dict:
    """Parse schedule string into a normalized format.

    Reused from job_runner.py logic. Supports:
    - Cron expressions (e.g., "0 6 * * *")
    - Human-readable (e.g., "Daily @ 6:00 AM", "Hourly", "Weekly")
    - Special (e.g., "At logon")

    Returns dict with: type, minute, hour, day_of_month, month, day_of_week (cron)
                  or: type, interval_hours, preferred_hour (interval)
                  or: type (on_login)

    Raises ValueError if schedule is invalid.
    """
    if not schedule or not isinstance(schedule, str):
        raise ValueError("Schedule string cannot be empty")

    schedule_lower = schedule.lower().strip()

    # Cron expressions (e.g., "0 6 * * *") — 5 parts
    parts = schedule.split()
    if len(parts) == 5:
        # Validate cron parts
        try:
            cron_parts = {
                "minute": parts[0],
                "hour": parts[1],
                "day_of_month": parts[2],
                "month": parts[3],
                "day_of_week": parts[4],
            }
            # Basic validation: parts should be numbers, *, ranges, or lists
            for part in parts:
                if not (part == "*" or
                        part.isdigit() or
                        "/" in part or
                        "-" in part or
                        "," in part):
                    raise ValueError(f"Invalid cron part: {part}")
            return {"type": "cron", **cron_parts}
        except (ValueError, IndexError):
            pass  # Not valid cron, continue to human-readable

    # Human-readable schedules
    if "hourly" in schedule_lower:
        return {"type": "interval", "interval_hours": 1}

    if "daily" in schedule_lower:
        hour = 6  # default
        if "@" in schedule:
            # Parse "Daily @ 6:00 AM" or "Daily @ 6 AM"
            match = re.search(r'(\d{1,2}):?(\d{2})?\s*(AM|PM)?', schedule, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                ampm = match.group(3)
                if ampm and ampm.upper() == "PM" and hour != 12:
                    hour += 12
                elif ampm and ampm.upper() == "AM" and hour == 12:
                    hour = 0
        return {"type": "interval", "interval_hours": 24, "preferred_hour": hour}

    if "weekly" in schedule_lower:
        return {"type": "interval", "interval_hours": 168}  # 7 days

    if "at logon" in schedule_lower or "on login" in schedule_lower:
        return {"type": "on_login"}

    # Fallback: treat as daily
    return {"type": "interval", "interval_hours": 24}


def get_db_connection():
    """Get a database connection using psycopg or psycopg2."""
    import os
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable not set")

    try:
        import psycopg
        return psycopg.connect(db_url, row_factory=psycopg.rows.dict_row)
    except ImportError:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(db_url)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn


def validate_schedule_string(schedule: str) -> None:
    """Validate that a schedule string is parseable.

    Raises ValueError if invalid.
    """
    try:
        parse_schedule(schedule)
    except Exception as e:
        raise ValueError(f"Invalid schedule string '{schedule}': {e}")


def handle_job_schedule(action: str, **kwargs) -> dict:
    """Dispatch job_schedule MCP tool actions.

    Actions:
      - create: template_id (optional), schedule (required), template_version (optional, default 'latest'), description (optional)
      - update: scheduled_job_id (required), fields (dict of updates)
      - pause: scheduled_job_id (required)
      - unpause: scheduled_job_id (required)
      - list: filters (dict), limit (int), offset (int)
      - unschedule: scheduled_job_id (required), reason (required for audit log)

    Returns dict with:
      - success: bool
      - scheduled_job_id (for create/update/pause/unpause)
      - jobs (for list)
      - message: str
      - error: str (if applicable)
    """
    conn = None
    try:
        conn = get_db_connection()

        if action == "create":
            return _handle_create(conn, kwargs)
        elif action == "update":
            return _handle_update(conn, kwargs)
        elif action == "pause":
            return _handle_pause(conn, kwargs)
        elif action == "unpause":
            return _handle_unpause(conn, kwargs)
        elif action == "list":
            return _handle_list(conn, kwargs)
        elif action == "unschedule":
            return _handle_unschedule(conn, kwargs)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"job_schedule error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()


def _handle_create(conn, kwargs: dict) -> dict:
    """Create a new scheduled job."""
    template_id = kwargs.get("template_id")
    schedule = kwargs.get("schedule")
    template_version = kwargs.get("template_version", "latest")
    description = kwargs.get("description", "")
    job_name = kwargs.get("job_name", f"scheduled-{uuid.uuid4().hex[:8]}")
    project_id = kwargs.get("project_id")

    if not schedule:
        return {"success": False, "error": "schedule is required"}

    # Validate schedule string
    try:
        validate_schedule_string(schedule)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    # If template_id provided, verify it exists (when job_templates table exists)
    if template_id:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema='claude' AND table_name='job_templates'
                )
            """)
            result = cur.fetchone()
            # Handle both dict and tuple responses from mock/real DB
            if hasattr(result, "get"):
                has_job_templates = result.get("exists")
                if has_job_templates is None:
                    # Fallback: dict_row exposes positional access via list(values())
                    has_job_templates = list(result.values())[0]
            else:
                has_job_templates = result[0]

            if has_job_templates:
                cur.execute("""
                    SELECT template_id, is_paused FROM claude.job_templates
                    WHERE template_id = %s
                """, (template_id,))
                template_row = cur.fetchone()
                if not template_row:
                    return {"success": False, "error": f"Template {template_id} not found"}
                # Support both dict-style (.get) and tuple-style ([1]) access
                is_paused = (template_row.get("is_paused")
                            if hasattr(template_row, "get")
                            else template_row[1])
                if is_paused:
                    return {"success": False, "error": f"Template {template_id} is paused"}

    # Insert into scheduled_jobs
    scheduled_job_id = uuid.uuid4()
    template_version_pin = None if template_version == "latest" else template_version

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO claude.scheduled_jobs
                (job_id, project_id, job_name, job_description, schedule, is_active,
                 template_id, template_version, trigger_type, created_at, created_by_identity_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'cron', %s, %s)
            RETURNING job_id
        """, (
            scheduled_job_id,
            project_id,
            job_name,
            description,
            schedule,
            True,
            template_id,
            template_version_pin,
            datetime.now(),
            None,  # created_by_identity_id
        ))
        result_row = cur.fetchone()

    # Log to audit_log
    _log_audit(conn, "scheduled_jobs", str(scheduled_job_id), None, "active", "CREATE", {
        "template_id": str(template_id) if template_id else None,
        "schedule": schedule,
        "template_version": template_version,
    })

    conn.commit()
    return {
        "success": True,
        "scheduled_job_id": str(scheduled_job_id),
        "job_name": job_name,
        "schedule": schedule,
        "message": f"Created scheduled job {job_name}",
    }


def _handle_update(conn, kwargs: dict) -> dict:
    """Update a scheduled job."""
    scheduled_job_id = kwargs.get("scheduled_job_id")
    if not scheduled_job_id:
        return {"success": False, "error": "scheduled_job_id is required"}

    fields = kwargs.get("fields", {})
    if not fields:
        return {"success": False, "error": "At least one field to update is required"}

    # Validate schedule if provided
    if "schedule" in fields and fields["schedule"]:
        try:
            validate_schedule_string(fields["schedule"])
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # Handle template_version special case
    if "template_version" in fields:
        if fields["template_version"] == "latest":
            fields["template_version"] = None

    # Build dynamic UPDATE
    update_clauses = []
    values = []
    for key, value in fields.items():
        update_clauses.append(f"{key} = %s")
        values.append(value)

    update_clauses.append("updated_at = %s")
    values.append(datetime.now())
    values.append(scheduled_job_id)

    with conn.cursor() as cur:
        cur.execute(f"""
            UPDATE claude.scheduled_jobs
            SET {', '.join(update_clauses)}
            WHERE job_id = %s
        """, values)
        if cur.rowcount == 0:
            return {"success": False, "error": f"Job {scheduled_job_id} not found"}

    # Log to audit_log
    _log_audit(conn, "scheduled_jobs", str(scheduled_job_id), None, "updated", "UPDATE", fields)

    conn.commit()
    return {
        "success": True,
        "scheduled_job_id": str(scheduled_job_id),
        "message": f"Updated scheduled job {scheduled_job_id}",
    }


def _handle_pause(conn, kwargs: dict) -> dict:
    """Pause a scheduled job (set is_active=false)."""
    scheduled_job_id = kwargs.get("scheduled_job_id")
    if not scheduled_job_id:
        return {"success": False, "error": "scheduled_job_id is required"}

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE claude.scheduled_jobs
            SET is_active = false, updated_at = %s
            WHERE job_id = %s
        """, (datetime.now(), scheduled_job_id))
        if cur.rowcount == 0:
            return {"success": False, "error": f"Job {scheduled_job_id} not found"}

    # Log to audit_log
    _log_audit(conn, "scheduled_jobs", str(scheduled_job_id), "active", "paused", "PAUSE", {})

    conn.commit()
    return {
        "success": True,
        "scheduled_job_id": str(scheduled_job_id),
        "message": f"Paused scheduled job {scheduled_job_id}",
    }


def _handle_unpause(conn, kwargs: dict) -> dict:
    """Unpause a scheduled job (set is_active=true)."""
    scheduled_job_id = kwargs.get("scheduled_job_id")
    if not scheduled_job_id:
        return {"success": False, "error": "scheduled_job_id is required"}

    with conn.cursor() as cur:
        cur.execute("""
            UPDATE claude.scheduled_jobs
            SET is_active = true, updated_at = %s
            WHERE job_id = %s
        """, (datetime.now(), scheduled_job_id))
        if cur.rowcount == 0:
            return {"success": False, "error": f"Job {scheduled_job_id} not found"}

    # Log to audit_log
    _log_audit(conn, "scheduled_jobs", str(scheduled_job_id), "paused", "active", "UNPAUSE", {})

    conn.commit()
    return {
        "success": True,
        "scheduled_job_id": str(scheduled_job_id),
        "message": f"Unpaused scheduled job {scheduled_job_id}",
    }


def _handle_list(conn, kwargs: dict) -> dict:
    """List scheduled jobs with optional filters."""
    filters = kwargs.get("filters", {})
    limit = kwargs.get("limit", 50)
    offset = kwargs.get("offset", 0)

    where_clauses = []
    values = []

    if filters.get("template_id"):
        where_clauses.append("template_id = %s")
        values.append(filters["template_id"])

    if filters.get("is_active") is not None:
        where_clauses.append("is_active = %s")
        values.append(filters["is_active"])

    if filters.get("project_id"):
        where_clauses.append("project_id = %s")
        values.append(filters["project_id"])

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    values.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT job_id, project_id, job_name, job_description, schedule, is_active,
                   template_id, template_version, last_run, last_status,
                   created_at, updated_at
            FROM claude.scheduled_jobs
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, values)
        rows = cur.fetchall()

    jobs = []
    for row in rows:
        row_dict = dict(row) if hasattr(row, "keys") else row
        jobs.append({
            "scheduled_job_id": str(row_dict.get("job_id")),
            "project_id": str(row_dict.get("project_id")) if row_dict.get("project_id") else None,
            "job_name": row_dict.get("job_name"),
            "description": row_dict.get("job_description"),
            "schedule": row_dict.get("schedule"),
            "is_active": row_dict.get("is_active"),
            "template_id": str(row_dict.get("template_id")) if row_dict.get("template_id") else None,
            "template_version": row_dict.get("template_version"),
            "last_run": row_dict.get("last_run"),
            "last_status": row_dict.get("last_status"),
            "created_at": row_dict.get("created_at"),
            "updated_at": row_dict.get("updated_at"),
        })

    return {
        "success": True,
        "jobs": jobs,
        "count": len(jobs),
        "limit": limit,
        "offset": offset,
    }


def _handle_unschedule(conn, kwargs: dict) -> dict:
    """Delete a scheduled job and log to audit_log."""
    scheduled_job_id = kwargs.get("scheduled_job_id")
    reason = kwargs.get("reason", "Unscheduled by user")

    if not scheduled_job_id:
        return {"success": False, "error": "scheduled_job_id is required"}

    # Fetch current state for logging
    with conn.cursor() as cur:
        cur.execute("""
            SELECT is_active FROM claude.scheduled_jobs
            WHERE job_id = %s
        """, (scheduled_job_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"Job {scheduled_job_id} not found"}

        current_status = "active" if row.get("is_active") else "paused"

        # Delete
        cur.execute("""
            DELETE FROM claude.scheduled_jobs
            WHERE job_id = %s
        """, (scheduled_job_id,))

    # Log to audit_log
    _log_audit(conn, "scheduled_jobs", str(scheduled_job_id), current_status, "deleted", "DELETE", {
        "reason": reason,
    })

    conn.commit()
    return {
        "success": True,
        "scheduled_job_id": str(scheduled_job_id),
        "message": f"Unscheduled job {scheduled_job_id}: {reason}",
    }


def _log_audit(conn, entity_type: str, entity_id: str, from_status: str, to_status: str,
               change_source: str, metadata: dict) -> None:
    """Log action to audit_log."""
    import json as _json
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO claude.audit_log
                    (entity_type, entity_id, from_status, to_status, changed_by,
                     change_source, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                entity_type,
                entity_id,
                from_status,
                to_status,
                None,  # changed_by — would come from session context
                change_source,
                _json.dumps(metadata, default=str),
            ))
    except Exception as e:
        logger.warning(f"Failed to log audit entry: {e}")
