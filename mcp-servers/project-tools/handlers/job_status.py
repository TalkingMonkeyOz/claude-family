"""
job_status.py — Read-only visibility handler for the task queue system.

BT704 (F224): 7 read views mirroring the work_board(view=...) pattern.

Views:
  board        — System snapshot: queue counts + recent runs + active templates
  queue        — Live pending/in_progress tasks with lease info
  dead_letter  — Unresolved dead_letter rows ordered by age (oldest first)
  runs         — Filtered job_run_history rows (audit log)
  result       — Single task: full row + agent_session join + linked feedback
  templates    — Template catalog with stats from job_template_stats VIEW
  template     — Single template: row + versions + origins + recent runs

All views are budget-capped (limit/offset). Oversized results include
truncated=True in the response envelope.

Graceful fallback: if new tables (job_templates, task_queue, etc.) do not
yet exist (pre-migration), views return empty datasets rather than errors.
The BT694 job_template_stats VIEW falls back similarly.

Read-only. No INSERT/UPDATE/DELETE.
"""

import os
from typing import Optional
import psycopg
from psycopg.rows import dict_row


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    """Get a PostgreSQL connection for read-only status queries."""
    conn_string = (
        os.environ.get("DATABASE_URI")
        or os.environ.get("POSTGRES_CONNECTION_STRING")
    )
    if not conn_string:
        raise RuntimeError(
            "DATABASE_URI or POSTGRES_CONNECTION_STRING env var required"
        )
    return psycopg.connect(conn_string, row_factory=dict_row)


def _tables_exist(cur, *table_names: str) -> bool:
    """Return True only if ALL named tables/views exist in the claude schema."""
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = 'claude'
          AND table_name = ANY(%s)
        """,
        (list(table_names),),
    )
    row = cur.fetchone()
    if row is None:
        return False
    return row["cnt"] == len(table_names)


def _rows_to_list(cur) -> list:
    """Fetch all remaining rows as plain dicts."""
    return [dict(r) for r in cur.fetchall()]


def _serialize(rows: list) -> list:
    """Convert datetime/Decimal objects in rows to JSON-safe types."""
    import decimal
    from datetime import datetime, date, timezone

    result = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, datetime):
                clean[k] = v.isoformat()
            elif isinstance(v, date):
                clean[k] = v.isoformat()
            elif isinstance(v, decimal.Decimal):
                clean[k] = float(v)
            else:
                clean[k] = v
        result.append(clean)
    return result


# ---------------------------------------------------------------------------
# View implementations
# ---------------------------------------------------------------------------

def _view_board(cur, project: Optional[str]) -> dict:
    """
    System snapshot: queue counts + recent runs (24h) + active templates.

    Returns:
        {
            queue_summary: {pending, in_progress, completed_24h,
                            dead_letter, paused_templates},
            recent_runs: [...],   # last 20 from job_run_history
            active_templates: [...],
        }
    """
    # Queue counts — only possible if task_queue exists
    queue_summary = {
        "pending": 0,
        "in_progress": 0,
        "completed_24h": 0,
        "dead_letter": 0,
        "paused_templates": 0,
    }
    recent_runs = []
    active_templates = []

    # --- Queue counts ---
    if _tables_exist(cur, "task_queue"):
        project_filter = "AND project_id = %s::uuid" if project else ""
        params = (project,) if project else ()
        cur.execute(
            f"""
            SELECT
              COUNT(*) FILTER (WHERE status = 'pending')                              AS pending,
              COUNT(*) FILTER (WHERE status = 'in_progress')                          AS in_progress,
              COUNT(*) FILTER (WHERE status = 'completed'
                                AND completed_at >= NOW() - INTERVAL '24 hours')      AS completed_24h,
              COUNT(*) FILTER (WHERE status = 'dead_letter')                          AS dead_letter
            FROM claude.task_queue
            WHERE 1=1 {project_filter}
            """,
            params,
        )
        row = cur.fetchone()
        if row:
            queue_summary["pending"] = row["pending"] or 0
            queue_summary["in_progress"] = row["in_progress"] or 0
            queue_summary["completed_24h"] = row["completed_24h"] or 0
            queue_summary["dead_letter"] = row["dead_letter"] or 0

    # --- Paused templates ---
    if _tables_exist(cur, "job_templates"):
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM claude.job_templates WHERE is_paused = TRUE"
        )
        row = cur.fetchone()
        queue_summary["paused_templates"] = row["cnt"] if row else 0

    # --- Recent runs (job_run_history always exists; uses new columns if present) ---
    #     Fall back to the pre-migration column set if template_id not present.
    try:
        cur.execute(
            """
            SELECT
              h.id::text                      AS run_id,
              COALESCE(t.name, 'unknown')     AS template_name,
              h.trigger_kind,
              h.status,
              h.started_at,
              EXTRACT(EPOCH FROM (h.completed_at - h.started_at))::numeric(10,1)
                                              AS duration_secs,
              h.error_message                 AS error
            FROM claude.job_run_history h
            LEFT JOIN claude.job_templates t ON t.template_id = h.template_id
            WHERE h.started_at >= NOW() - INTERVAL '24 hours'
            ORDER BY h.started_at DESC
            LIMIT 20
            """
        )
        recent_runs = _serialize(_rows_to_list(cur))
    except Exception:
        # Pre-migration fallback: template_id column may not yet exist
        try:
            cur.execute(
                """
                SELECT
                  id::text   AS run_id,
                  NULL        AS template_name,
                  NULL        AS trigger_kind,
                  status,
                  started_at,
                  EXTRACT(EPOCH FROM (completed_at - started_at))::numeric(10,1)
                              AS duration_secs,
                  error_message AS error
                FROM claude.job_run_history
                WHERE started_at >= NOW() - INTERVAL '24 hours'
                ORDER BY started_at DESC
                LIMIT 20
                """
            )
            recent_runs = _serialize(_rows_to_list(cur))
        except Exception:
            recent_runs = []

    # --- Active templates ---
    if _tables_exist(cur, "job_templates"):
        cur.execute(
            """
            SELECT
              template_id::text AS template_id,
              name,
              kind,
              is_paused,
              current_version
            FROM claude.job_templates
            WHERE is_paused = FALSE
            ORDER BY name
            LIMIT 50
            """
        )
        active_templates = _serialize(_rows_to_list(cur))

    return {
        "success": True,
        "view": "board",
        "queue_summary": queue_summary,
        "recent_runs": recent_runs,
        "active_templates": active_templates,
    }


def _view_queue(
    cur,
    project: Optional[str],
    template_filter: Optional[str],
    status_filter: Optional[list],
    limit: int,
    offset: int,
) -> dict:
    """
    Live queue: pending + in_progress tasks with lease info.

    Returns:
        {tasks: [...], total, truncated}
    """
    if not _tables_exist(cur, "task_queue"):
        return {
            "success": True, "view": "queue",
            "tasks": [], "total": 0, "truncated": False,
            "_note": "task_queue table not yet created (pre-migration)",
        }

    # Build status filter
    statuses = status_filter if status_filter else ["pending", "in_progress"]
    params: list = [statuses]
    where_clauses = ["tq.status = ANY(%s)"]

    if project:
        where_clauses.append("tq.project_id = %s::uuid")
        params.append(project)
    if template_filter:
        where_clauses.append("t.template_id = %s::uuid OR t.name = %s")
        params.extend([template_filter, template_filter])

    where_sql = " AND ".join(where_clauses)

    # Total count
    cur.execute(
        f"""
        SELECT COUNT(*) AS cnt
        FROM claude.task_queue tq
        LEFT JOIN claude.job_templates t ON t.template_id = tq.template_id
        WHERE {where_sql}
        """,
        params,
    )
    total = cur.fetchone()["cnt"] or 0

    # Data rows
    data_params = params + [limit + 1, offset]
    cur.execute(
        f"""
        SELECT
          tq.task_id::text                                                AS task_id,
          COALESCE(t.name, 'unknown')                                     AS template_name,
          tq.status,
          tq.priority,
          tq.attempts,
          tq.claimed_by,
          tq.claimed_until,
          tq.enqueued_at,
          EXTRACT(EPOCH FROM (NOW() - tq.enqueued_at))::int               AS age_secs
        FROM claude.task_queue tq
        LEFT JOIN claude.job_templates t ON t.template_id = tq.template_id
        WHERE {where_sql}
        ORDER BY tq.priority ASC, tq.enqueued_at ASC
        LIMIT %s OFFSET %s
        """,
        data_params,
    )
    rows = _serialize(_rows_to_list(cur))
    truncated = len(rows) > limit
    tasks = rows[:limit]

    return {
        "success": True, "view": "queue",
        "tasks": tasks, "total": total,
        "truncated": truncated,
        "limit": limit, "offset": offset,
    }


def _view_dead_letter(
    cur,
    project: Optional[str],
    limit: int,
    offset: int,
) -> dict:
    """
    Triage queue: unresolved dead_letter rows ordered oldest-first.

    Returns:
        {tasks: [...], total, truncated}
    """
    if not _tables_exist(cur, "task_queue"):
        return {
            "success": True, "view": "dead_letter",
            "tasks": [], "total": 0, "truncated": False,
            "_note": "task_queue table not yet created (pre-migration)",
        }

    params: list = []
    where_clauses = ["tq.status = 'dead_letter'", "tq.resolution_status IS NULL"]

    if project:
        where_clauses.append("tq.project_id = %s::uuid")
        params.append(project)

    where_sql = " AND ".join(where_clauses)

    cur.execute(
        f"SELECT COUNT(*) AS cnt FROM claude.task_queue tq WHERE {where_sql}",
        params,
    )
    total = cur.fetchone()["cnt"] or 0

    data_params = params + [limit + 1, offset]
    cur.execute(
        f"""
        SELECT
          tq.task_id::text                                                AS task_id,
          COALESCE(t.name, 'unknown')                                     AS template_name,
          tq.last_error,
          EXTRACT(EPOCH FROM (NOW() - tq.completed_at))::int / 86400.0   AS age_days,
          tq.surfaced_as_feedback_id::text                                AS surfaced_as_feedback_id
        FROM claude.task_queue tq
        LEFT JOIN claude.job_templates t ON t.template_id = tq.template_id
        WHERE {where_sql}
        ORDER BY tq.completed_at ASC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        data_params,
    )
    rows = _serialize(_rows_to_list(cur))
    truncated = len(rows) > limit
    tasks = rows[:limit]

    return {
        "success": True, "view": "dead_letter",
        "tasks": tasks, "total": total,
        "truncated": truncated,
        "limit": limit, "offset": offset,
    }


def _view_runs(
    cur,
    project: Optional[str],
    template_filter: Optional[str],
    status_filter: Optional[list],
    days_back: int,
    limit: int,
    offset: int,
) -> dict:
    """
    Audit log: job_run_history rows, filterable.

    Returns:
        {runs: [...], total, truncated}
    """
    # Always attempt — job_run_history always exists; gracefully handles
    # absence of new columns (template_id, trigger_kind) via LEFT JOIN / COALESCE.
    params: list = [days_back]
    where_clauses = ["h.started_at >= NOW() - (%s || ' days')::interval"]

    if project:
        where_clauses.append("tq.project_id = %s::uuid")
        params.append(project)
    if status_filter:
        where_clauses.append("h.status = ANY(%s)")
        params.append(status_filter)

    template_join = ""
    template_name_col = "NULL AS template_name"
    trigger_kind_col = "NULL AS trigger_kind"

    # Detect whether new columns and job_templates exist
    has_new_cols = _tables_exist(cur, "job_templates")
    if has_new_cols:
        template_join = "LEFT JOIN claude.job_templates t ON t.template_id = h.template_id"
        template_name_col = "COALESCE(t.name, 'unknown') AS template_name"
        trigger_kind_col = "h.trigger_kind"
        if template_filter:
            where_clauses.append("(t.template_id = %s::uuid OR t.name = %s)")
            params.extend([template_filter, template_filter])
    elif template_filter:
        # Cannot filter by template name without join; silently ignore
        pass

    where_sql = " AND ".join(where_clauses)

    try:
        # Count
        count_params = list(params)
        cur.execute(
            f"""
            SELECT COUNT(*) AS cnt
            FROM claude.job_run_history h
            {template_join}
            WHERE {where_sql}
            """,
            count_params,
        )
        total = cur.fetchone()["cnt"] or 0

        # Data
        data_params = list(params) + [limit + 1, offset]
        cur.execute(
            f"""
            SELECT
              h.id::text                                                        AS run_id,
              {template_name_col},
              {trigger_kind_col},
              h.status,
              h.started_at,
              EXTRACT(EPOCH FROM (h.completed_at - h.started_at))::numeric(10,1)
                                                                                AS duration_secs,
              h.error_message                                                   AS error
            FROM claude.job_run_history h
            {template_join}
            WHERE {where_sql}
            ORDER BY h.started_at DESC
            LIMIT %s OFFSET %s
            """,
            data_params,
        )
        rows = _serialize(_rows_to_list(cur))
        truncated = len(rows) > limit
        runs = rows[:limit]

        return {
            "success": True, "view": "runs",
            "runs": runs, "total": total,
            "truncated": truncated,
            "limit": limit, "offset": offset,
        }
    except Exception as exc:
        return {
            "success": False, "view": "runs",
            "error": str(exc),
        }


def _view_result(cur, task_id: str) -> dict:
    """
    Single task: full task_queue row + agent_session join + linked feedback.

    Returns:
        {task: {...}, agent_session: {...}|None, feedback: {...}|None}
    """
    if not _tables_exist(cur, "task_queue"):
        return {
            "success": False, "view": "result",
            "error": "task_queue table not yet created (pre-migration)",
        }

    # Main task row with run history join to get agent_session_id
    cur.execute(
        """
        SELECT
          tq.*,
          tq.task_id::text      AS task_id_str,
          t.name                AS template_name,
          h.agent_session_id    AS agent_session_id
        FROM claude.task_queue tq
        LEFT JOIN claude.job_templates t ON t.template_id = tq.template_id
        LEFT JOIN claude.job_run_history h
          ON h.trigger_id = tq.task_id AND h.trigger_kind = 'ad_hoc'
        WHERE tq.task_id = %s::uuid
        ORDER BY h.started_at DESC
        LIMIT 1
        """,
        (task_id,),
    )
    task_row = cur.fetchone()
    if not task_row:
        return {
            "success": False, "view": "result",
            "error": f"Task not found: {task_id}",
        }

    task = _serialize([dict(task_row)])[0]

    # Agent session join
    agent_session = None
    agent_session_id = task_row.get("agent_session_id")
    if agent_session_id:
        cur.execute(
            """
            SELECT *
            FROM claude.agent_sessions
            WHERE session_id = %s::uuid
            """,
            (str(agent_session_id),),
        )
        session_row = cur.fetchone()
        if session_row:
            agent_session = _serialize([dict(session_row)])[0]

    # Linked feedback (if task was surfaced)
    feedback = None
    surfaced_id = task_row.get("surfaced_as_feedback_id")
    if surfaced_id:
        cur.execute(
            """
            SELECT feedback_id::text, feedback_type, description, status, created_at
            FROM claude.feedback
            WHERE feedback_id = %s::uuid
            """,
            (str(surfaced_id),),
        )
        fb_row = cur.fetchone()
        if fb_row:
            feedback = _serialize([dict(fb_row)])[0]

    return {
        "success": True, "view": "result",
        "task": task,
        "agent_session": agent_session,
        "feedback": feedback,
    }


def _view_templates(
    cur,
    project: Optional[str],
    limit: int,
    offset: int,
) -> dict:
    """
    Template catalog with stats from job_template_stats VIEW.

    Graceful fallback: if VIEW doesn't exist yet, returns template rows
    without stats.

    Returns:
        {templates: [...], total, truncated, has_stats}
    """
    if not _tables_exist(cur, "job_templates"):
        return {
            "success": True, "view": "templates",
            "templates": [], "total": 0, "truncated": False, "has_stats": False,
            "_note": "job_templates table not yet created (pre-migration)",
        }

    has_stats = _tables_exist(cur, "job_template_stats")

    # Total
    cur.execute("SELECT COUNT(*) AS cnt FROM claude.job_templates")
    total = cur.fetchone()["cnt"] or 0

    if has_stats:
        cur.execute(
            """
            SELECT
              t.template_id::text         AS template_id,
              t.name,
              t.kind,
              t.is_paused,
              t.current_version,
              s.runs_total_30d,
              s.runs_succeeded_30d,
              s.runs_dead_30d,
              s.p95_duration_secs,
              s.last_run_at
            FROM claude.job_templates t
            LEFT JOIN claude.job_template_stats s USING (template_id)
            ORDER BY t.name
            LIMIT %s OFFSET %s
            """,
            (limit + 1, offset),
        )
    else:
        cur.execute(
            """
            SELECT
              template_id::text   AS template_id,
              name,
              kind,
              is_paused,
              current_version,
              NULL                AS runs_total_30d,
              NULL                AS runs_succeeded_30d,
              NULL                AS runs_dead_30d,
              NULL                AS p95_duration_secs,
              NULL                AS last_run_at
            FROM claude.job_templates
            ORDER BY name
            LIMIT %s OFFSET %s
            """,
            (limit + 1, offset),
        )

    rows = _serialize(_rows_to_list(cur))
    truncated = len(rows) > limit
    templates = rows[:limit]

    return {
        "success": True, "view": "templates",
        "templates": templates, "total": total,
        "truncated": truncated,
        "has_stats": has_stats,
        "limit": limit, "offset": offset,
    }


def _view_template(cur, template_id: str) -> dict:
    """
    Single template detail: row + last 10 versions + origins + last 20 runs.

    Returns:
        {template: {...}, versions: [...], origins: [...], recent_runs: [...]}
    """
    if not _tables_exist(cur, "job_templates"):
        return {
            "success": False, "view": "template",
            "error": "job_templates table not yet created (pre-migration)",
        }

    # Resolve template by UUID or name
    try:
        cur.execute(
            "SELECT * FROM claude.job_templates WHERE template_id = %s::uuid",
            (template_id,),
        )
    except Exception:
        cur.execute(
            "SELECT * FROM claude.job_templates WHERE name = %s",
            (template_id,),
        )
    tpl_row = cur.fetchone()
    if not tpl_row:
        return {
            "success": False, "view": "template",
            "error": f"Template not found: {template_id}",
        }

    template = _serialize([dict(tpl_row)])[0]
    resolved_id = tpl_row["template_id"]

    # Versions (last 10)
    versions: list = []
    if _tables_exist(cur, "job_template_versions"):
        cur.execute(
            """
            SELECT version_id::text, version, created_at, created_by, notes
            FROM claude.job_template_versions
            WHERE template_id = %s::uuid
            ORDER BY version DESC
            LIMIT 10
            """,
            (str(resolved_id),),
        )
        versions = _serialize(_rows_to_list(cur))

    # Origins
    origins: list = []
    if _tables_exist(cur, "job_template_origins"):
        cur.execute(
            """
            SELECT origin_id::text, origin_kind, origin_role, note, created_at
            FROM claude.job_template_origins
            WHERE template_id = %s::uuid
            ORDER BY created_at DESC
            """,
            (str(resolved_id),),
        )
        origins = _serialize(_rows_to_list(cur))

    # Recent runs (last 20 from job_run_history)
    recent_runs: list = []
    has_new_cols = _tables_exist(cur, "job_templates")
    try:
        cur.execute(
            """
            SELECT
              id::text         AS run_id,
              trigger_kind,
              status,
              started_at,
              EXTRACT(EPOCH FROM (completed_at - started_at))::numeric(10,1)
                               AS duration_secs,
              error_message    AS error
            FROM claude.job_run_history
            WHERE template_id = %s::uuid
            ORDER BY started_at DESC
            LIMIT 20
            """,
            (str(resolved_id),),
        )
        recent_runs = _serialize(_rows_to_list(cur))
    except Exception:
        # template_id column not yet added to job_run_history
        recent_runs = []

    return {
        "success": True, "view": "template",
        "template": template,
        "versions": versions,
        "origins": origins,
        "recent_runs": recent_runs,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def handle_job_status(
    view: str,
    project: Optional[str] = None,
    template_id: Optional[str] = None,
    task_id: Optional[str] = None,
    template_filter: Optional[str] = None,
    status_filter: Optional[list] = None,
    limit: int = 50,
    offset: int = 0,
    days_back: int = 7,
) -> dict:
    """
    Read-only visibility into the task queue system. Mirrors work_board() view pattern.

    Args:
        view:            One of: board | queue | dead_letter | runs | result |
                         templates | template
        project:         Optional project UUID for filtering (queue, dead_letter, runs, board).
        template_id:     Template UUID or name — required for view='template';
                         optional filter for view='result'.
        task_id:         Task UUID — required for view='result'.
        template_filter: Template UUID or name filter for view='queue' and 'runs'.
        status_filter:   Status list filter for view='queue' and 'runs'.
        limit:           Max rows returned (default 50, max 200).
        offset:          Pagination offset.
        days_back:       For view='runs', how many days of history to include (default 7).

    Returns:
        dict with success, view, and view-specific payload.
    """
    # Clamp limit
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    days_back = max(1, min(days_back, 365))

    VALID_VIEWS = {"board", "queue", "dead_letter", "runs", "result", "templates", "template"}
    if view not in VALID_VIEWS:
        return {
            "success": False,
            "error": f"Unknown view: '{view}'. Must be one of: {sorted(VALID_VIEWS)}",
        }

    # View-level argument validation
    if view == "result" and not task_id:
        return {
            "success": False,
            "error": "view='result' requires task_id",
        }
    if view == "template" and not template_id:
        return {
            "success": False,
            "error": "view='template' requires template_id",
        }

    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        if view == "board":
            return _view_board(cur, project)
        elif view == "queue":
            return _view_queue(cur, project, template_filter, status_filter, limit, offset)
        elif view == "dead_letter":
            return _view_dead_letter(cur, project, limit, offset)
        elif view == "runs":
            return _view_runs(cur, project, template_filter, status_filter, days_back, limit, offset)
        elif view == "result":
            return _view_result(cur, task_id)
        elif view == "templates":
            return _view_templates(cur, project, limit, offset)
        elif view == "template":
            return _view_template(cur, template_id)
        else:
            # Unreachable — caught above, but makes linters happy
            return {"success": False, "error": f"Unknown view: {view}"}

    finally:
        if cur:
            cur.close()
        conn.close()
