"""
job_template handler — F224 BT700

Implements handle_job_template(action, **kwargs) with 10 actions:
    create, update, publish_version, add_origin, remove_origin,
    list, read, pause, unpause, resolve_dead_letter

Mirrors the work_create / work_status action-parameter dispatch pattern.
Writes to claude.audit_log on every mutating action.

NOT wired into server_v2.py here — wiring is a separate step.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Origin kind → column mapping
# The CHECK (num_nonnulls(...) = 1) in job_template_origins enforces the
# exclusive arc at the DB level. We set exactly one column per origin_kind.
# ---------------------------------------------------------------------------

_ORIGIN_KIND_COLUMN = {
    "memory":   "origin_memory_id",
    "article":  "origin_article_id",
    "feedback": "origin_feedback_id",
    "feature":  "origin_feature_id",
    "workfile": "origin_workfile_id",
    "url":      "origin_url",
}

_VALID_ORIGIN_KINDS = set(_ORIGIN_KIND_COLUMN.keys())
_VALID_ORIGIN_ROLES = {"rationale", "spec", "reference", "superseded_by"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audit(cur, *, table_name: str, operation: str, entity_id: Optional[str],
           before: Optional[dict], after: Optional[dict],
           changed_by: Optional[str]) -> None:
    """Insert a row into claude.audit_log for every mutating action."""
    cur.execute(
        """
        INSERT INTO claude.audit_log
            (entity_type, entity_id, entity_code, from_status, to_status,
             changed_by, change_source, metadata, event_type)
        VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            table_name,
            entity_id,
            None,                               # entity_code — not applicable here
            before.get("status") if before else None,
            after.get("status") if after else None,
            changed_by,
            "mcp_tool",
            json.dumps({
                "operation": operation,
                "before": before,
                "after": after,
            }),
            operation,
        ),
    )


def _err(msg: str) -> dict:
    return {"success": False, "error": msg}


def _ok(**kwargs) -> dict:
    return {"success": True, **kwargs}


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------

def handle_job_template(action: str, **kwargs) -> dict:
    """Dispatch to the correct action handler.

    Args:
        action: One of create | update | publish_version | add_origin |
                remove_origin | list | read | pause | unpause |
                resolve_dead_letter
        **kwargs: Action-specific parameters (see individual handlers below).

    Returns:
        {"success": True, ...} on success or {"success": False, "error": "..."}.
    """
    # Import here so the module can be loaded without a live DB (for tests).
    from server_v2 import get_db_connection  # noqa: PLC0415 — runtime import

    handlers = {
        "create":             _create,
        "update":             _update,
        "publish_version":    _publish_version,
        "add_origin":         _add_origin,
        "remove_origin":      _remove_origin,
        "list":               _list,
        "read":               _read,
        "pause":              _pause,
        "unpause":            _unpause,
        "resolve_dead_letter": _resolve_dead_letter,
    }

    handler = handlers.get(action)
    if handler is None:
        return _err(
            f"Unknown action '{action}'. "
            f"Valid actions: {', '.join(sorted(handlers.keys()))}"
        )

    session_id = os.environ.get("CLAUDE_SESSION_ID")
    conn = get_db_connection()
    try:
        result = handler(conn, session_id=session_id, **kwargs)
        return result
    except Exception as exc:  # noqa: BLE001 — intentional catch-all, mirroring server_v2
        try:
            conn.rollback()
        except Exception:
            pass
        return _err(str(exc))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Action: create
# ---------------------------------------------------------------------------

def _create(conn, *, session_id: Optional[str],
            name: str,
            description: str,
            kind: str,
            owner: Optional[str] = None,
            max_concurrent_runs: int = 1,
            max_attempts: int = 3,
            lease_duration_secs: int = 300,
            is_idempotent: bool = False,
            payload: Optional[dict] = None,
            **_extra) -> dict:
    """INSERT into claude.job_templates; optionally create v1 version row."""
    if not name or not name.strip():
        return _err("name is required")
    if not description or not description.strip():
        return _err("description is required")
    if kind not in ("agent", "script"):
        return _err("kind must be 'agent' or 'script'")

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO claude.job_templates
                (name, description, kind, owner,
                 max_concurrent_runs, max_attempts,
                 lease_duration_secs, is_idempotent,
                 current_version, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, now(), now())
            RETURNING template_id::text, name, current_version
            """,
            (
                name.strip(), description.strip(), kind,
                owner or session_id,
                max_concurrent_runs, max_attempts,
                lease_duration_secs, is_idempotent,
            ),
        )
        row = cur.fetchone()
        template_id = row["template_id"]
        current_version = row["current_version"]

        version_id: Optional[str] = None
        if payload is not None:
            cur.execute(
                """
                INSERT INTO claude.job_template_versions
                    (template_id, version, payload, created_by, notes)
                VALUES (%s::uuid, 1, %s::jsonb, %s, %s)
                RETURNING version_id::text
                """,
                (
                    template_id,
                    json.dumps(payload),
                    session_id,
                    "Initial version created with template",
                ),
            )
            version_id = cur.fetchone()["version_id"]

        _audit(
            cur,
            table_name="job_templates",
            operation="create",
            entity_id=template_id,
            before=None,
            after={"name": name, "kind": kind, "current_version": current_version},
            changed_by=session_id,
        )
        conn.commit()

        result = _ok(
            template_id=template_id,
            name=row["name"],
            current_version=current_version,
        )
        if version_id:
            result["version_id"] = version_id
        return result
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: update
# ---------------------------------------------------------------------------

# Columns that may be updated via this action.
# Payload changes MUST go through publish_version.
_UPDATABLE_COLUMNS = {
    "description",
    "owner",
    "max_concurrent_runs",
    "max_attempts",
    "lease_duration_secs",
    "is_idempotent",
    "retry_backoff_base",
    "retry_backoff_max",
    "retry_jitter_pct",
    "pause_threshold_fails",
    "pause_threshold_window_secs",
    "transient_error_classes",
}


def _update(conn, *, session_id: Optional[str],
            template_id: str,
            **fields) -> dict:
    """UPDATE metadata columns on claude.job_templates (NOT payload)."""
    if not template_id:
        return _err("template_id is required")

    updates = {k: v for k, v in fields.items() if k in _UPDATABLE_COLUMNS}
    rejected = {k for k in fields if k not in _UPDATABLE_COLUMNS and k not in (
        "session_id",  # consumed by dispatcher
    )}
    if not updates:
        if rejected:
            return _err(
                f"No updatable fields provided. Unrecognised fields: {rejected}. "
                f"Payload changes go through publish_version."
            )
        return _err("No updatable fields provided.")

    cur = conn.cursor()
    try:
        # Fetch before-state for audit
        cur.execute(
            "SELECT * FROM claude.job_templates WHERE template_id = %s::uuid",
            (template_id,),
        )
        before = cur.fetchone()
        if not before:
            return _err(f"Template '{template_id}' not found")
        before_dict = dict(before)

        # Build dynamic SET clause
        set_parts = ", ".join(f"{col} = %s" for col in updates)
        set_parts += ", updated_at = now()"
        values = list(updates.values()) + [template_id]

        cur.execute(
            f"UPDATE claude.job_templates SET {set_parts} WHERE template_id = %s::uuid "
            "RETURNING template_id::text",
            values,
        )
        if cur.fetchone() is None:
            return _err(f"Template '{template_id}' not found (UPDATE returned nothing)")

        _audit(
            cur,
            table_name="job_templates",
            operation="update",
            entity_id=template_id,
            before={k: before_dict.get(k) for k in updates},
            after=updates,
            changed_by=session_id,
        )
        conn.commit()

        return _ok(
            template_id=template_id,
            updated_fields=list(updates.keys()),
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: publish_version
# ---------------------------------------------------------------------------

def _publish_version(conn, *, session_id: Optional[str],
                     template_id: str,
                     payload: dict,
                     notes: Optional[str] = None,
                     **_extra) -> dict:
    """INSERT a new version row and bump current_version on the template."""
    if not template_id:
        return _err("template_id is required")
    if not payload:
        return _err("payload is required")

    cur = conn.cursor()
    try:
        # Lock the template row to avoid concurrent version races
        cur.execute(
            "SELECT current_version FROM claude.job_templates "
            "WHERE template_id = %s::uuid FOR UPDATE",
            (template_id,),
        )
        row = cur.fetchone()
        if not row:
            return _err(f"Template '{template_id}' not found")

        new_version = row["current_version"] + 1

        cur.execute(
            """
            INSERT INTO claude.job_template_versions
                (template_id, version, payload, created_by, notes)
            VALUES (%s::uuid, %s, %s::jsonb, %s, %s)
            RETURNING version_id::text
            """,
            (
                template_id, new_version,
                json.dumps(payload),
                session_id, notes,
            ),
        )
        version_id = cur.fetchone()["version_id"]

        cur.execute(
            "UPDATE claude.job_templates "
            "SET current_version = %s, updated_at = now() "
            "WHERE template_id = %s::uuid",
            (new_version, template_id),
        )

        _audit(
            cur,
            table_name="job_template_versions",
            operation="publish_version",
            entity_id=template_id,
            before={"current_version": new_version - 1},
            after={"current_version": new_version, "version_id": version_id},
            changed_by=session_id,
        )
        conn.commit()

        return _ok(
            version_id=version_id,
            template_id=template_id,
            version=new_version,
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: add_origin
# ---------------------------------------------------------------------------

def _add_origin(conn, *, session_id: Optional[str],
                template_id: str,
                origin_kind: str,
                origin_ref: str,
                origin_role: str,
                note: Optional[str] = None,
                **_extra) -> dict:
    """INSERT into claude.job_template_origins, resolving origin_ref to the right FK column."""
    if not template_id:
        return _err("template_id is required")
    if origin_kind not in _VALID_ORIGIN_KINDS:
        return _err(
            f"origin_kind '{origin_kind}' is invalid. "
            f"Valid kinds: {', '.join(sorted(_VALID_ORIGIN_KINDS))}"
        )
    if origin_role not in _VALID_ORIGIN_ROLES:
        return _err(
            f"origin_role '{origin_role}' is invalid. "
            f"Valid roles: {', '.join(sorted(_VALID_ORIGIN_ROLES))}"
        )
    if not origin_ref:
        return _err("origin_ref is required")

    # Resolve the ref to the correct exclusive-arc column.
    # For all kinds except 'url', origin_ref is a UUID (cast at DB level).
    # For 'url', origin_ref is a text URL.
    col = _ORIGIN_KIND_COLUMN[origin_kind]

    # Build the INSERT with exactly the right column set.
    # All other origin_* columns remain NULL (enforcing the CHECK constraint).
    if origin_kind == "url":
        cur_sql = """
            INSERT INTO claude.job_template_origins
                (template_id, origin_kind, origin_url, origin_role, note, created_at)
            VALUES (%s::uuid, %s, %s, %s, %s, now())
            RETURNING origin_id::text
        """
        params = (template_id, origin_kind, origin_ref, origin_role, note)
    else:
        cur_sql = f"""
            INSERT INTO claude.job_template_origins
                (template_id, origin_kind, {col}, origin_role, note, created_at)
            VALUES (%s::uuid, %s, %s::uuid, %s, %s, now())
            RETURNING origin_id::text
        """
        params = (template_id, origin_kind, origin_ref, origin_role, note)

    cur = conn.cursor()
    try:
        cur.execute(cur_sql, params)
        origin_id = cur.fetchone()["origin_id"]

        _audit(
            cur,
            table_name="job_template_origins",
            operation="add_origin",
            entity_id=template_id,
            before=None,
            after={
                "origin_id": origin_id,
                "origin_kind": origin_kind,
                col: origin_ref,
                "origin_role": origin_role,
            },
            changed_by=session_id,
        )
        conn.commit()

        return _ok(
            origin_id=origin_id,
            template_id=template_id,
            origin_kind=origin_kind,
            origin_role=origin_role,
            resolved_column=col,
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: remove_origin
# ---------------------------------------------------------------------------

def _remove_origin(conn, *, session_id: Optional[str],
                   origin_id: str,
                   **_extra) -> dict:
    """DELETE from claude.job_template_origins."""
    if not origin_id:
        return _err("origin_id is required")

    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT origin_id::text, template_id::text, origin_kind, origin_role "
            "FROM claude.job_template_origins WHERE origin_id = %s::uuid",
            (origin_id,),
        )
        row = cur.fetchone()
        if not row:
            return _err(f"Origin '{origin_id}' not found")
        template_id = row["template_id"]

        cur.execute(
            "DELETE FROM claude.job_template_origins WHERE origin_id = %s::uuid",
            (origin_id,),
        )

        _audit(
            cur,
            table_name="job_template_origins",
            operation="remove_origin",
            entity_id=template_id,
            before={"origin_id": origin_id, "origin_kind": row["origin_kind"],
                    "origin_role": row["origin_role"]},
            after=None,
            changed_by=session_id,
        )
        conn.commit()

        return _ok(
            deleted_origin_id=origin_id,
            template_id=template_id,
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: list
# ---------------------------------------------------------------------------

def _list(conn, *, session_id: Optional[str],
          kind: Optional[str] = None,
          is_paused: Optional[bool] = None,
          is_active: Optional[bool] = None,
          limit: int = 50,
          offset: int = 0,
          **_extra) -> dict:
    """SELECT from claude.job_templates with optional filters + stats join."""
    conditions: list[str] = []
    params: list[Any] = []

    if kind is not None:
        if kind not in ("agent", "script"):
            return _err("kind must be 'agent' or 'script'")
        conditions.append("jt.kind = %s")
        params.append(kind)

    if is_paused is not None:
        conditions.append("jt.is_paused = %s")
        params.append(is_paused)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    params += [limit, offset]

    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT
                jt.template_id::text,
                jt.name,
                jt.description,
                jt.kind,
                jt.current_version,
                jt.owner,
                jt.is_paused,
                jt.paused_at,
                jt.paused_reason,
                jt.is_idempotent,
                jt.max_concurrent_runs,
                jt.max_attempts,
                jt.lease_duration_secs,
                jt.created_at,
                jt.updated_at,
                -- Stats (may be NULL if no runs in last 30d)
                s.runs_total_30d,
                s.runs_succeeded_30d,
                s.runs_dead_30d,
                s.avg_duration_secs,
                s.last_run_at
            FROM claude.job_templates jt
            LEFT JOIN claude.job_template_stats s USING (template_id)
            {where_clause}
            ORDER BY jt.name
            LIMIT %s OFFSET %s
            """,
            params,
        )
        rows = cur.fetchall()

        # Count total (without limit/offset)
        cur.execute(
            f"SELECT COUNT(*) as cnt FROM claude.job_templates jt {where_clause}",
            params[:-2],  # strip limit+offset
        )
        total = cur.fetchone()["cnt"]

        return _ok(
            templates=[dict(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: read
# ---------------------------------------------------------------------------

def _read(conn, *, session_id: Optional[str],
          template_id: str,
          **_extra) -> dict:
    """Fetch single template: row + all versions + all origins + recent runs."""
    if not template_id:
        return _err("template_id is required")

    cur = conn.cursor()
    try:
        # Main row
        cur.execute(
            """
            SELECT
                jt.*,
                jt.template_id::text as template_id_str,
                s.runs_total_30d,
                s.runs_succeeded_30d,
                s.runs_dead_30d,
                s.avg_duration_secs,
                s.p95_duration_secs,
                s.last_run_at
            FROM claude.job_templates jt
            LEFT JOIN claude.job_template_stats s USING (template_id)
            WHERE jt.template_id = %s::uuid
            """,
            (template_id,),
        )
        template = cur.fetchone()
        if not template:
            return _err(f"Template '{template_id}' not found")
        template_dict = dict(template)
        # Normalise the uuid column to string
        template_dict["template_id"] = template_dict.pop("template_id_str", template_id)

        # Versions (all, ordered oldest → newest)
        cur.execute(
            """
            SELECT version_id::text, template_id::text, version, payload,
                   created_at, created_by, notes
            FROM claude.job_template_versions
            WHERE template_id = %s::uuid
            ORDER BY version
            """,
            (template_id,),
        )
        versions = [dict(r) for r in cur.fetchall()]

        # Origins
        cur.execute(
            """
            SELECT
                origin_id::text,
                template_id::text,
                origin_kind,
                origin_memory_id::text,
                origin_article_id::text,
                origin_feedback_id::text,
                origin_feature_id::text,
                origin_workfile_id::text,
                origin_url,
                origin_role,
                note,
                created_at
            FROM claude.job_template_origins
            WHERE template_id = %s::uuid
            ORDER BY created_at
            """,
            (template_id,),
        )
        origins = [dict(r) for r in cur.fetchall()]

        # Recent runs (last 10 from job_run_history)
        cur.execute(
            """
            SELECT
                run_id::text,
                template_id::text,
                trigger_kind,
                trigger_id::text,
                status,
                started_at,
                completed_at,
                agent_session_id::text
            FROM claude.job_run_history
            WHERE template_id = %s::uuid
            ORDER BY started_at DESC
            LIMIT 10
            """,
            (template_id,),
        )
        recent_runs = [dict(r) for r in cur.fetchall()]

        return _ok(
            template=template_dict,
            versions=versions,
            origins=origins,
            recent_runs=recent_runs,
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: pause
# ---------------------------------------------------------------------------

def _pause(conn, *, session_id: Optional[str],
           template_id: str,
           reason: str,
           **_extra) -> dict:
    """Set is_paused=true on a job template."""
    if not template_id:
        return _err("template_id is required")
    if not reason or not reason.strip():
        return _err("reason is required when pausing a template")

    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT is_paused, name FROM claude.job_templates WHERE template_id = %s::uuid",
            (template_id,),
        )
        row = cur.fetchone()
        if not row:
            return _err(f"Template '{template_id}' not found")
        if row["is_paused"]:
            return _err(f"Template '{row['name']}' is already paused")

        cur.execute(
            """
            UPDATE claude.job_templates
            SET is_paused = true, paused_at = now(), paused_reason = %s, updated_at = now()
            WHERE template_id = %s::uuid
            """,
            (reason.strip(), template_id),
        )

        _audit(
            cur,
            table_name="job_templates",
            operation="pause",
            entity_id=template_id,
            before={"is_paused": False},
            after={"is_paused": True, "paused_reason": reason.strip()},
            changed_by=session_id,
        )
        conn.commit()

        return _ok(
            template_id=template_id,
            name=row["name"],
            is_paused=True,
            paused_reason=reason.strip(),
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: unpause
# ---------------------------------------------------------------------------

def _unpause(conn, *, session_id: Optional[str],
             template_id: str,
             reason: Optional[str] = None,
             **_extra) -> dict:
    """Clear is_paused on a job template; record reason in audit_log."""
    if not template_id:
        return _err("template_id is required")

    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT is_paused, name, paused_reason FROM claude.job_templates "
            "WHERE template_id = %s::uuid",
            (template_id,),
        )
        row = cur.fetchone()
        if not row:
            return _err(f"Template '{template_id}' not found")
        if not row["is_paused"]:
            return _err(f"Template '{row['name']}' is not paused")

        cur.execute(
            """
            UPDATE claude.job_templates
            SET is_paused = false, paused_at = null, paused_reason = null, updated_at = now()
            WHERE template_id = %s::uuid
            """,
            (template_id,),
        )

        _audit(
            cur,
            table_name="job_templates",
            operation="unpause",
            entity_id=template_id,
            before={"is_paused": True, "paused_reason": row["paused_reason"]},
            after={"is_paused": False, "unpause_reason": reason},
            changed_by=session_id,
        )
        conn.commit()

        return _ok(
            template_id=template_id,
            name=row["name"],
            is_paused=False,
            unpause_reason=reason,
        )
    finally:
        cur.close()


# ---------------------------------------------------------------------------
# Action: resolve_dead_letter
# ---------------------------------------------------------------------------

def _resolve_dead_letter(conn, *, session_id: Optional[str],
                         task_id: str,
                         resolution: str,
                         notes: Optional[str] = None,
                         **_extra) -> dict:
    """Update a dead_letter task's resolution_status.

    resolution='rerun': creates a fresh task_queue row with the same template +
    payload and marks the original row as superseded.
    """
    if not task_id:
        return _err("task_id is required")

    valid_resolutions = ("fixed", "wont_fix", "rerun", "superseded")
    if resolution not in valid_resolutions:
        return _err(
            f"resolution '{resolution}' is invalid. "
            f"Valid values: {', '.join(valid_resolutions)}"
        )

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT task_id::text, template_id::text, template_version,
                   payload_override, status, priority, project_id::text,
                   parent_session_id::text
            FROM claude.task_queue
            WHERE task_id = %s::uuid
            """,
            (task_id,),
        )
        row = cur.fetchone()
        if not row:
            return _err(f"Task '{task_id}' not found in task_queue")
        if row["status"] != "dead_letter":
            return _err(
                f"Task '{task_id}' has status '{row['status']}' — "
                "only 'dead_letter' tasks can be resolved here"
            )

        new_task_id: Optional[str] = None

        if resolution == "rerun":
            # Insert a fresh pending row with the same template + payload
            cur.execute(
                """
                INSERT INTO claude.task_queue
                    (template_id, template_version, payload_override,
                     status, priority, project_id, parent_session_id,
                     enqueued_at)
                VALUES (%s::uuid, %s, %s::jsonb, 'pending', %s,
                        %s::uuid, %s::uuid, now())
                RETURNING task_id::text
                """,
                (
                    row["template_id"],
                    row["template_version"],
                    json.dumps(row["payload_override"]) if row["payload_override"] else None,
                    row["priority"],
                    row["project_id"],
                    row["parent_session_id"],
                ),
            )
            new_task_id = cur.fetchone()["task_id"]

            # Mark original as superseded
            cur.execute(
                """
                UPDATE claude.task_queue
                SET resolution_status = 'superseded',
                    superseded_by_task_id = %s::uuid,
                    resolved_at = now(),
                    resolved_by = %s,
                    resolution_notes = %s
                WHERE task_id = %s::uuid
                """,
                (new_task_id, session_id, notes, task_id),
            )
        else:
            cur.execute(
                """
                UPDATE claude.task_queue
                SET resolution_status = %s,
                    resolved_at = now(),
                    resolved_by = %s,
                    resolution_notes = %s
                WHERE task_id = %s::uuid
                """,
                (resolution, session_id, notes, task_id),
            )

        _audit(
            cur,
            table_name="task_queue",
            operation="resolve_dead_letter",
            entity_id=task_id,
            before={"status": "dead_letter", "resolution_status": None},
            after={
                "resolution_status": resolution,
                "new_task_id": new_task_id,
            },
            changed_by=session_id,
        )
        conn.commit()

        result = _ok(
            task_id=task_id,
            resolution=resolution,
            notes=notes,
        )
        if new_task_id:
            result["new_task_id"] = new_task_id
        return result
    finally:
        cur.close()
