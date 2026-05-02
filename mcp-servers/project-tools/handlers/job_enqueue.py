"""
job_enqueue.py — Hot-path atomic job enqueue handler.

BT702: Atomic, single-purpose MCP handler for enqueueing tasks into the
task_queue. Handles template resolution, payload merging, idempotency key
derivation, and atomic INSERT with dedup detection.

Key behaviors:
- Resolves template by ID or name (error if missing/paused)
- Merges payload_override with template payload (deep merge, override wins)
- Auto-derives idempotency_key if not provided
- Detects duplicate idempotency_key; returns existing task_id if active
- Atomic INSERT with unique constraint on idx_task_queue_idem_active
- Audits to claude.audit_log

No action discrimination; single entry point: handle_job_enqueue().
"""

import json
import hashlib
import os
from typing import Any, Optional
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

# Try to import cf_idempotency_key from BT696 (parallel agent).
# If not available, use inline fallback.
try:
    from scripts.cf_constants import cf_idempotency_key
except ImportError:
    # BT696 fallback — inline SHA256 hash
    def cf_idempotency_key(template_id: str, version: int, payload: Any) -> str:
        """Fallback idempotency key derivation (BT696 parallel agent delay)."""
        if payload is not None:
            payload_canonical = json.dumps(payload, sort_keys=True, default=str)
        else:
            payload_canonical = "null"
        raw = f"{template_id}|{version}|{payload_canonical}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_db_connection():
    """Get PostgreSQL connection for task queue operations."""
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')
    if not conn_string:
        raise RuntimeError("DATABASE_URI or POSTGRES_CONNECTION_STRING env var required")
    return psycopg.connect(conn_string, row_factory=dict_row)


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Deep merge override dict into base dict.
    Override values win at all levels.
    """
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override if override is not None else base

    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def handle_job_enqueue(
    template_id: Optional[str] = None,
    template_name: Optional[str] = None,
    template_version: Optional[int] = None,
    payload_override: Optional[dict] = None,
    priority: int = 3,
    idempotency_key: Optional[str] = None,
    parent_session_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> dict:
    """
    Atomic hot-path job enqueue handler.

    Resolves template, merges payload, derives idempotency key, and atomically
    inserts task into task_queue. Returns existing task_id on idempotency key
    collision with active task.

    Args:
        template_id: Template UUID (one of template_id or template_name required).
        template_name: Template name (case-sensitive lookup).
        template_version: Specific version to use. If None, use template.current_version.
        payload_override: Merged with template payload (override wins).
        priority: 1-5 (1=critical, 2=high, 3=normal, 4=low, 5=backlog). Default 3.
        idempotency_key: Explicit key for dedup. If None, auto-derived from template_id, version, payload.
        parent_session_id: Session ID that enqueued this task (for audit trail).
        project_id: Project UUID (for filtering, dashboards).

    Returns:
        {
            "success": bool,
            "task_id": str (UUID),
            "idempotency_key": str,
            "action": "enqueued" | "already_active",
            "message": str
        }

    Raises:
        ValueError: template_id/template_name both missing, template paused, priority out of range.
        RuntimeError: DB connection failure, template not found.
    """
    # Validate inputs
    if not template_id and not template_name:
        raise ValueError("One of template_id or template_name is required")

    if priority < 1 or priority > 5:
        raise ValueError(f"priority must be 1-5, got {priority}")

    payload_override = payload_override or {}
    parent_session_id = parent_session_id or None
    project_id = project_id or None

    conn = get_db_connection()
    cur = None

    try:
        cur = conn.cursor()

        # 1. Resolve template by ID or name
        if template_id:
            cur.execute("""
                SELECT t.template_id, t.name, t.current_version, t.is_paused, t.paused_reason,
                       v.payload FROM claude.job_templates t
                LEFT JOIN claude.job_template_versions v ON (t.template_id = v.template_id AND v.version = t.current_version)
                WHERE t.template_id = %s::uuid
            """, (template_id,))
        else:
            cur.execute("""
                SELECT t.template_id, t.name, t.current_version, t.is_paused, t.paused_reason,
                       v.payload FROM claude.job_templates t
                LEFT JOIN claude.job_template_versions v ON (t.template_id = v.template_id AND v.version = t.current_version)
                WHERE t.name = %s
            """, (template_name,))

        template_row = cur.fetchone()
        if not template_row:
            raise RuntimeError(
                f"Template not found: {template_id or template_name}"
            )

        template_id = template_row['template_id']
        template_name = template_row['name']
        is_paused = template_row['is_paused']
        paused_reason = template_row['paused_reason']

        if is_paused:
            raise ValueError(
                f"Template '{template_name}' is paused: {paused_reason}"
            )

        # 2. Resolve version
        if template_version is None:
            template_version = template_row['current_version']

        # If explicit version differs from current, fetch that version's payload
        template_payload = template_row['payload'] or {}
        if template_version != template_row['current_version']:
            cur.execute("""
                SELECT payload FROM claude.job_template_versions
                WHERE template_id = %s::uuid AND version = %s
            """, (template_id, template_version))
            version_row = cur.fetchone()
            if not version_row:
                raise RuntimeError(
                    f"Template {template_name} version {template_version} not found"
                )
            template_payload = version_row['payload'] or {}

        # 3. Deep merge payload: template baseline + override
        effective_payload = _deep_merge(template_payload, payload_override)

        # 4. Derive or use provided idempotency key
        if idempotency_key is None:
            idempotency_key = cf_idempotency_key(str(template_id), template_version, effective_payload)

        # 5. Attempt INSERT; catch unique constraint violation on idx_task_queue_idem_active
        try:
            cur.execute("""
                INSERT INTO claude.task_queue (
                    template_id, template_version, payload_override, status, priority,
                    project_id, parent_session_id, idempotency_key, enqueued_at
                ) VALUES (
                    %s::uuid, %s, %s, 'pending', %s,
                    %s::uuid, %s::uuid, %s, NOW()
                )
                RETURNING task_id::text
            """, (
                template_id, template_version,
                json.dumps(effective_payload) if effective_payload else None,
                priority,
                project_id, parent_session_id, idempotency_key
            ))
            new_task_id = cur.fetchone()['task_id']
            action = "enqueued"

            # Audit log the enqueue
            cur.execute("""
                INSERT INTO claude.audit_log
                    (entity_type, entity_id, from_status, to_status,
                     change_source, metadata, event_type)
                VALUES (%s, %s::uuid, %s, %s, %s, %s, %s)
            """, (
                'task_queue',
                new_task_id,
                None,
                'pending',
                'job_enqueue_handler',
                json.dumps({
                    'template_id': str(template_id),
                    'template_version': template_version,
                    'priority': priority,
                    'idempotency_key': idempotency_key,
                    'parent_session_id': parent_session_id,
                }),
                'enqueue',
            ))

            conn.commit()

            return {
                "success": True,
                "task_id": new_task_id,
                "idempotency_key": idempotency_key,
                "action": action,
                "message": f"Task {new_task_id} enqueued for template '{template_name}' v{template_version}"
            }

        except psycopg.IntegrityError as e:
            # Unique constraint violation on idx_task_queue_idem_active
            # Check if active task exists (status in pending, in_progress)
            if "idx_task_queue_idem_active" in str(e):
                conn.rollback()

                # Fetch existing active task with this idempotency_key
                cur.execute("""
                    SELECT task_id::text FROM claude.task_queue
                    WHERE idempotency_key = %s AND status IN ('pending', 'in_progress')
                    LIMIT 1
                """, (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    return {
                        "success": True,
                        "task_id": existing['task_id'],
                        "idempotency_key": idempotency_key,
                        "action": "already_active",
                        "message": f"Task {existing['task_id']} already active with this idempotency key"
                    }
                else:
                    # Constraint violation but no active task found?
                    # This shouldn't happen; re-raise the original error.
                    raise RuntimeError(
                        f"Idempotency constraint violation but no active task found: {e}"
                    )
            else:
                # Some other constraint violation
                raise

    finally:
        if cur:
            cur.close()
        conn.close()
