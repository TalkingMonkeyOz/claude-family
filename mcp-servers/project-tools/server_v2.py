#!/usr/bin/env python3
"""
Claude Project Tools v2 - Application Layer MCP Server

Rebuilt from CRUD wrapper to outcome-level application layer using FastMCP.
Self-documenting schemas via type hints (Literal → enum, defaults, docstrings).

Phase 1: Foundation + Schema
- start_session: Returns ALL context in one call (replaces 4+ separate tools)
- get_schema: Compact schema reference with constraints inlined
- end_session: Saves state, closes session, captures knowledge
- save_checkpoint: Mid-session state save

Plus all existing tools from server.py (backward compatibility).

Author: Claude Family
Created: 2026-02-10
"""

import json
import os
import sys
import re
import glob
from typing import Any, Literal, Optional
from datetime import datetime
from pathlib import Path

# ============================================================================
# FastMCP Setup
# ============================================================================

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "claude-project-tools",
    instructions=(
        "Project-aware tooling for Claude Family development. "
        "Use start_session at the beginning of work. "
        "Use get_schema when you need to understand database tables. "
        "Use end_session when finishing work."
    ),
)

# ============================================================================
# Database Connection (shared with server.py)
# ============================================================================

# PostgreSQL (supports both psycopg2 and psycopg3)
POSTGRES_AVAILABLE = False
psycopg = None
PSYCOPG_VERSION = 0

try:
    import psycopg
    from psycopg.rows import dict_row
    POSTGRES_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        POSTGRES_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        print("ERROR: Neither psycopg nor psycopg2 installed.", file=sys.stderr)
        sys.exit(1)


def get_db_connection():
    """Get PostgreSQL connection."""
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')
    if not conn_string:
        raise RuntimeError("DATABASE_URI or POSTGRES_CONNECTION_STRING environment variable required")
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_string, row_factory=dict_row)
    else:
        return psycopg.connect(conn_string, cursor_factory=RealDictCursor)


def get_project_id(project_identifier: str) -> Optional[str]:
    """Get project_id from name or path."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.project_id::text
            FROM claude.projects p
            JOIN claude.workspaces w ON p.project_id = w.project_id
            WHERE w.project_name = %s OR w.project_path = %s OR p.project_name = %s
            LIMIT 1
        """, (project_identifier, project_identifier, project_identifier))
        row = cur.fetchone()
        cur.close()
        return row['project_id'] if row else None
    finally:
        conn.close()


# ============================================================================
# Schema Introspection Module
# ============================================================================

# Table tier system - determines which tables are shown for which project types
TIER_1_TABLES = [
    'sessions', 'todos', 'feedback', 'features', 'build_tasks',
    'projects', 'workspaces', 'column_registry', 'session_state',
    'session_facts', 'messages',
]

TIER_2_TABLES = [
    'identities', 'knowledge', 'config_templates', 'profiles',
    'agent_sessions', 'mcp_configs', 'context_rules', 'knowledge_relations',
    'skill_content', 'project_type_configs',
]

# In-memory cache (schema doesn't change mid-session)
_schema_cache: dict[str, Any] = {}


def _get_schemas_for_project(project_name: str) -> list[str]:
    """Get relevant schemas for a project from workspaces + project_type_configs."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT w.project_type, ptc.default_schemas
            FROM claude.workspaces w
            LEFT JOIN claude.project_type_configs ptc ON w.project_type = ptc.project_type
            WHERE w.project_name = %s
            LIMIT 1
        """, (project_name,))
        row = cur.fetchone()
        cur.close()
        if row and row.get('default_schemas'):
            return row['default_schemas']
        return ['claude']
    finally:
        conn.close()


def _introspect_tables(schemas: list[str], tier: int = 1) -> list[dict]:
    """Introspect tables from information_schema + column_registry.

    Args:
        schemas: List of schema names to introspect
        tier: 1 = core tables only, 2 = include infrastructure tables
    """
    # Determine which tables to include
    include_tables = list(TIER_1_TABLES)
    if tier >= 2:
        include_tables.extend(TIER_2_TABLES)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        tables = []
        for schema in schemas:
            # Get table info from information_schema
            cur.execute("""
                SELECT
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position
                FROM information_schema.columns c
                WHERE c.table_schema = %s
                  AND c.table_name = ANY(%s)
                ORDER BY c.table_name, c.ordinal_position
            """, (schema, include_tables))

            columns_by_table: dict[str, list[dict]] = {}
            for row in cur.fetchall():
                tname = row['table_name']
                if tname not in columns_by_table:
                    columns_by_table[tname] = []
                columns_by_table[tname].append({
                    'name': row['column_name'],
                    'type': row['data_type'],
                    'nullable': row['is_nullable'] == 'YES',
                    'default': row['column_default'],
                })

            # Get column_registry constraints for these tables
            cur.execute("""
                SELECT table_name, column_name, valid_values, description
                FROM claude.column_registry
                WHERE table_name = ANY(%s)
            """, (include_tables,))

            constraints: dict[str, dict[str, dict]] = {}
            for row in cur.fetchall():
                tname = row['table_name']
                if tname not in constraints:
                    constraints[tname] = {}
                constraints[tname][row['column_name']] = {
                    'valid_values': row['valid_values'],
                    'description': row.get('description'),
                }

            # Get primary keys
            cur.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = %s
                  AND tc.table_name = ANY(%s)
            """, (schema, include_tables))

            pkeys: dict[str, list[str]] = {}
            for row in cur.fetchall():
                tname = row['table_name']
                if tname not in pkeys:
                    pkeys[tname] = []
                pkeys[tname].append(row['column_name'])

            # Build table info
            for tname, cols in sorted(columns_by_table.items()):
                table_constraints = constraints.get(tname, {})

                # Inline constraints into column info
                for col in cols:
                    if col['name'] in table_constraints:
                        constraint = table_constraints[col['name']]
                        if constraint['valid_values']:
                            col['valid_values'] = constraint['valid_values']
                        if constraint.get('description'):
                            col['description'] = constraint['description']

                tables.append({
                    'schema': schema,
                    'table': tname,
                    'primary_key': pkeys.get(tname, []),
                    'columns': cols,
                })

        cur.close()
        return tables

    finally:
        conn.close()


def _format_compact_reference(tables: list[dict]) -> str:
    """Format tables as compact markdown reference (~600-1000 tokens)."""
    lines = ["# Schema Reference\n"]

    for tbl in tables:
        pk_cols = set(tbl['primary_key'])
        lines.append(f"## {tbl['schema']}.{tbl['table']}")

        col_parts = []
        for col in tbl['columns']:
            name = col['name']
            dtype = col['type']

            # Shorten common types
            type_map = {
                'uuid': 'uuid',
                'character varying': 'varchar',
                'timestamp without time zone': 'timestamp',
                'timestamp with time zone': 'timestamptz',
                'ARRAY': 'text[]',
                'boolean': 'bool',
                'integer': 'int',
                'text': 'text',
                'jsonb': 'jsonb',
                'double precision': 'float',
                'smallint': 'smallint',
                'numeric': 'numeric',
                'USER-DEFINED': 'vector',
            }
            short_type = type_map.get(dtype, dtype)

            # Build column descriptor
            flags = []
            if name in pk_cols:
                flags.append('PK')
            if not col['nullable'] and name not in pk_cols:
                flags.append('NOT NULL')
            if col.get('valid_values'):
                vals = col['valid_values']
                if len(vals) <= 8:
                    flags.append(f"enum: {vals}")
                else:
                    flags.append(f"enum: {vals[:5]}... ({len(vals)} values)")
            if col.get('description'):
                flags.append(col['description'])

            flag_str = f" ({', '.join(flags)})" if flags else ""
            col_parts.append(f"  - {name}: {short_type}{flag_str}")

        lines.append('\n'.join(col_parts))
        lines.append('')

    return '\n'.join(lines)


# ============================================================================
# Phase 1 Tools
# ============================================================================

@mcp.tool()
def get_schema(
    project: str = "",
    detail: Literal["compact", "full"] = "compact",
    tier: Literal[1, 2] = 1,
) -> str:
    """Get database schema reference with column constraints inlined.

    Use when: You need to understand table structures before writing SQL.
    Returns column names, types, valid values (from column_registry), and keys.
    Result is cached for the session - safe to call multiple times.
    Returns: Formatted string (compact) or JSON (full) with table definitions.

    Args:
        project: Project name. Defaults to current directory.
        detail: 'compact' for readable reference, 'full' for raw JSON.
        tier: 1 = core tables (sessions, todos, feedback, features, etc.),
              2 = include infrastructure tables (identities, knowledge, configs).
    """
    project = project or os.path.basename(os.getcwd())

    cache_key = f"{project}:{detail}:{tier}"
    if cache_key in _schema_cache:
        return _schema_cache[cache_key]

    schemas = _get_schemas_for_project(project)
    tables = _introspect_tables(schemas, tier=tier)

    if detail == "compact":
        result = _format_compact_reference(tables)
    else:
        result = json.dumps(tables, indent=2, default=str)

    _schema_cache[cache_key] = result
    return result


def _format_resume(data: dict) -> dict:
    """Build a pre-formatted resume display box from start_session data.

    Returns dict with 'display' (ready to print) and 'restore_tasks' (for TaskCreate).
    """
    project = data.get("project_name", "unknown")
    w = 66  # inner width of box

    # Extract fields
    last = data.get("last_session", {})
    last_date = str(last.get("ended", ""))[:10] if last.get("ended") else "N/A"
    last_summary = last.get("summary", "No previous session") or "No summary"
    focus = (data.get("previous_state", {}) or {}).get("focus", "None set")
    todos = data.get("todos", {"in_progress": [], "pending": []})
    features = data.get("active_features", [])
    msg_count = data.get("pending_messages", 0)
    fb_count = data.get("pending_feedback_count", 0)

    # Count uncommitted (placeholder - git status must run client-side)
    lines = []
    bar = "+" + "=" * w + "+"
    div = "+" + "-" * w + "+"

    def row(text: str) -> str:
        return f"|  {text:{w - 3}}|"

    lines.append(bar)
    lines.append(row(f"SESSION RESUME - {project}"))
    lines.append(bar)
    lines.append(row(f"Last Session: {last_date} - {last_summary[:w - 20]}"))
    lines.append(row(f"Focus: {focus[:w - 10]}"))
    lines.append(div)

    # Prior tasks section (display-only, NOT restored as TaskCreate)
    # Claude Code natively persists tasks in ~/.claude/tasks/.
    # DB todo restoration was creating zombie tasks carried forward indefinitely.
    in_prog = todos.get("in_progress", [])
    pending = todos.get("pending", [])
    stale = todos.get("stale", [])
    task_count = len(in_prog) + len(pending)
    if task_count > 0:
        lines.append(row(f"PRIOR SESSION TASKS ({task_count}) - for reference only:"))
        if in_prog:
            lines.append(row("  Were in progress:"))
            for t in in_prog:
                lines.append(row(f"    > {t['content'][:w - 8]}"))
        if pending:
            lines.append(row("  Were pending:"))
            for t in pending:
                lines.append(row(f"    - {t['content'][:w - 10]}"))
    else:
        lines.append(row("PRIOR SESSION TASKS: (none)"))

    if stale:
        lines.append(row(f"  Stale ({len(stale)}):"))
        for t in stale:
            age = t.get('age_days', '?')
            lines.append(row(f"    ~ {t['content'][:w - 16]} ({age}d old)"))
    lines.append(div)

    # Features section
    if features:
        feat_parts = []
        for f in features[:5]:
            done = f.get("tasks_done", 0)
            total = f.get("tasks_total", 0)
            feat_parts.append(f"{f.get('code', '?')} {f.get('feature_name', '?')} ({done}/{total})")
        lines.append(row("ACTIVE FEATURES:"))
        for fp in feat_parts:
            lines.append(row(f"  {fp[:w - 6]}"))
        lines.append(div)

    # Footer
    counts = []
    if msg_count:
        counts.append(f"MESSAGES: {msg_count}")
    if fb_count:
        counts.append(f"FEEDBACK: {fb_count}")
    footer = " | ".join(counts) if counts else "No pending items"
    lines.append(row(f"GIT: run 'git status --short' | {footer}"))
    lines.append(bar)

    display = "\n".join(lines)

    # No longer returning restore_tasks - Claude Code natively persists tasks
    # in ~/.claude/tasks/. DB todo restoration was creating zombie tasks.
    # Prior tasks are displayed as informational text only.

    return {
        "display": display,
        "restore_tasks": [],  # Empty - no task restoration (display-only)
        "git_check_needed": True,
    }


@mcp.tool()
def start_session(
    project: str = "",
    resume: bool = False,
) -> dict:
    """Start a session and get ALL context in one call.

    Use when: Beginning any work session. Call this first. Returns: project info,
    session state, active todos, work items (features + tasks), pending messages.
    With resume=True, returns pre-formatted display box for /session-resume.
    Use get_schema() separately if you need table structures.
    Returns: {project_name, project_id, project_context, previous_state,
              last_session, todos, active_features, pending_messages, ...}.

    Args:
        project: Project name or path. Defaults to current directory basename.
        resume: If True, returns pre-formatted display box + restore_tasks list
                for /session-resume. Claude just displays the box and restores tasks.
    """
    project = project or os.path.basename(os.getcwd())
    project_id = get_project_id(project)

    result: dict[str, Any] = {
        "project_name": project,
        "project_id": project_id,
        "session_started_at": datetime.now().isoformat(),
    }

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # CTE 1: Project context + session state + last session (single query)
        cur.execute("""
            WITH project_ctx AS (
                SELECT p.status as project_status, p.phase, p.priority,
                       w.project_path, w.project_type
                FROM claude.workspaces w
                LEFT JOIN claude.projects p ON w.project_id = p.project_id
                WHERE w.project_name = %s
                LIMIT 1
            ),
            session_st AS (
                SELECT current_focus, next_steps
                FROM claude.session_state
                WHERE project_name = %s
            ),
            last_sess AS (
                SELECT session_summary, session_end, tasks_completed
                FROM claude.sessions
                WHERE project_name = %s AND session_end IS NOT NULL
                ORDER BY session_end DESC LIMIT 1
            )
            SELECT
                (SELECT row_to_json(pc) FROM project_ctx pc) as project_ctx,
                (SELECT row_to_json(ss) FROM session_st ss) as session_state,
                (SELECT row_to_json(ls) FROM last_sess ls) as last_session
        """, (project, project, project))
        meta = cur.fetchone()

        if meta and meta['project_ctx']:
            pc = meta['project_ctx'] if isinstance(meta['project_ctx'], dict) else json.loads(meta['project_ctx'])
            result["project_context"] = {
                "type": pc.get('project_type'),
                "status": pc.get('project_status'),
                "phase": pc.get('phase'),
                "priority": pc.get('priority'),
                "path": pc.get('project_path'),
            }
        if meta and meta['session_state']:
            ss = meta['session_state'] if isinstance(meta['session_state'], dict) else json.loads(meta['session_state'])
            result["previous_state"] = {
                "focus": ss.get('current_focus'),
                "next_steps": ss.get('next_steps') or [],
            }
        if meta and meta['last_session']:
            ls = meta['last_session'] if isinstance(meta['last_session'], dict) else json.loads(meta['last_session'])
            result["last_session"] = {
                "summary": ls.get('session_summary'),
                "ended": ls.get('session_end'),
                "tasks_completed": ls.get('tasks_completed') or [],
            }

        if project_id:
            # Startup demotion: demote orphaned in_progress todos from closed sessions.
            # Safety net for when SessionEnd hook fails or session crashes (FB129).
            cur.execute("""
                UPDATE claude.todos
                SET status = 'pending', updated_at = NOW()
                WHERE project_id = %s::uuid
                  AND status = 'in_progress'
                  AND NOT is_deleted
                  AND created_session_id IS NOT NULL
                  AND created_session_id IN (
                      SELECT session_id FROM claude.sessions WHERE session_end IS NOT NULL
                  )
            """, (project_id,))
            demoted = cur.rowcount

            # Auto-archive zombie todos restored 4+ times without completion (FB130).
            cur.execute("""
                UPDATE claude.todos
                SET status = 'archived', updated_at = NOW()
                WHERE project_id = %s::uuid
                  AND status IN ('pending', 'in_progress')
                  AND NOT is_deleted
                  AND COALESCE(restore_count, 0) >= 4
            """, (project_id,))
            archived_zombies = cur.rowcount

            if demoted > 0 or archived_zombies > 0:
                conn.commit()

            # CTE 2: Todos + features + ready tasks + feedback count (single query)
            cur.execute("""
                WITH todos AS (
                    SELECT content, active_form, status, priority,
                           EXTRACT(DAY FROM NOW() - created_at)::int as age_days
                    FROM claude.todos
                    WHERE project_id = %s::uuid
                      AND status IN ('pending', 'in_progress')
                      AND NOT is_deleted
                    ORDER BY CASE status WHEN 'in_progress' THEN 0 ELSE 1 END, priority ASC
                    LIMIT 15
                ),
                features AS (
                    SELECT
                        'F' || f.short_code as code,
                        f.feature_name,
                        f.status,
                        f.priority,
                        (SELECT COUNT(*) FROM claude.build_tasks bt
                         WHERE bt.feature_id = f.feature_id AND bt.status = 'completed') as tasks_done,
                        (SELECT COUNT(*) FROM claude.build_tasks bt
                         WHERE bt.feature_id = f.feature_id) as tasks_total
                    FROM claude.features f
                    WHERE f.project_id = %s::uuid
                      AND f.status NOT IN ('completed', 'cancelled')
                    ORDER BY f.priority, f.short_code
                    LIMIT 10
                ),
                ready AS (
                    SELECT
                        'BT' || bt.short_code as task_code,
                        bt.task_name,
                        bt.task_type,
                        bt.files_affected,
                        'F' || f.short_code as feature_code,
                        f.feature_name
                    FROM claude.build_tasks bt
                    JOIN claude.features f ON bt.feature_id = f.feature_id
                    WHERE bt.project_id = %s::uuid AND bt.status = 'todo'
                      AND (bt.blocked_by_task_id IS NULL
                           OR bt.blocked_by_task_id IN (
                               SELECT task_id FROM claude.build_tasks WHERE status = 'completed'))
                    ORDER BY f.priority, f.short_code, bt.step_order
                    LIMIT 5
                ),
                fb_count AS (
                    SELECT COUNT(*) as count
                    FROM claude.feedback
                    WHERE project_id = %s::uuid
                      AND status IN ('new', 'triaged', 'in_progress')
                ),
                msg_count AS (
                    SELECT COUNT(*) as count
                    FROM claude.messages
                    WHERE status = 'pending'
                      AND (to_project = %s OR to_project IS NULL)
                )
                SELECT
                    (SELECT COALESCE(json_agg(row_to_json(t)), '[]') FROM todos t) as todos,
                    (SELECT COALESCE(json_agg(row_to_json(f)), '[]') FROM features f) as features,
                    (SELECT COALESCE(json_agg(row_to_json(r)), '[]') FROM ready r) as ready_tasks,
                    (SELECT count FROM fb_count) as feedback_count,
                    (SELECT count FROM msg_count) as message_count
            """, (project_id, project_id, project_id, project_id, project))
            work = cur.fetchone()

            if work:
                # Parse todos into buckets
                todos_raw = work['todos']
                if isinstance(todos_raw, str):
                    todos_raw = json.loads(todos_raw)
                todos = {"in_progress": [], "pending": [], "stale": []}
                for t in todos_raw:
                    age_days = t.get('age_days', 0) or 0
                    if t['status'] == 'in_progress' and age_days > 3:
                        bucket = "stale"  # in_progress > 3 days = stale
                    elif t['status'] == 'in_progress':
                        bucket = "in_progress"
                    elif age_days > 7 and t['status'] == 'pending':
                        bucket = "stale"  # pending > 7 days = stale
                    else:
                        bucket = "pending"
                    todos[bucket].append({
                        "content": t['content'],
                        "active_form": t.get('active_form', ''),
                        "priority": t['priority'],
                        "status": t['status'],
                        "age_days": age_days,
                    })
                result["todos"] = todos

                features_raw = work['features']
                if isinstance(features_raw, str):
                    features_raw = json.loads(features_raw)
                result["active_features"] = features_raw

                ready_raw = work['ready_tasks']
                if isinstance(ready_raw, str):
                    ready_raw = json.loads(ready_raw)
                result["ready_tasks"] = ready_raw

                result["pending_feedback_count"] = work['feedback_count']
                result["pending_messages"] = work['message_count']

                # Get recommended actions (unblocked todo tasks)
                cur.execute("""
                    SELECT 'BT' || bt.short_code as code, bt.task_name, bt.priority, bt.status,
                           bt.verification, bt.blocked_by_task_id IS NOT NULL as is_blocked
                    FROM claude.build_tasks bt
                    JOIN claude.features f ON bt.feature_id = f.feature_id
                    WHERE f.project_id = %s::uuid AND bt.status = 'todo'
                      AND bt.blocked_by_task_id IS NULL  -- only unblocked tasks
                    ORDER BY bt.priority, bt.short_code
                    LIMIT 10
                """, (project_id,))
                recommended_raw = cur.fetchall()
                result["recommended_actions"] = [dict(r) for r in recommended_raw]
                result["recommended_actions_note"] = "Use TaskCreate for each task you plan to work on this session"

                # Recent decisions from session facts
                try:
                    cur.execute("""
                        SELECT sf.fact_key, sf.fact_value, sf.fact_type, s.session_start
                        FROM claude.session_facts sf
                        JOIN claude.sessions s ON sf.session_id = s.session_id
                        WHERE s.project_name = %s
                          AND sf.fact_type = 'decision'
                        ORDER BY sf.created_at DESC
                        LIMIT 10
                    """, (project,))
                    result["recent_decisions"] = [dict(r) for r in cur.fetchall()]
                except Exception:
                    result["recent_decisions"] = []

                # Relevant knowledge for this project
                try:
                    cur.execute("""
                        SELECT k.title, k.description, k.knowledge_type, k.knowledge_category,
                               k.confidence_level, k.created_at
                        FROM claude.knowledge k
                        WHERE (k.applies_to_projects IS NULL OR %s = ANY(k.applies_to_projects))
                        ORDER BY k.created_at DESC
                        LIMIT 5
                    """, (project,))
                    result["relevant_knowledge"] = [dict(r) for r in cur.fetchall()]
                except Exception:
                    result["relevant_knowledge"] = []
        else:
            # No project_id - still get messages
            cur.execute("""
                SELECT COUNT(*) as count FROM claude.messages
                WHERE status = 'pending' AND (to_project = %s OR to_project IS NULL)
            """, (project,))
            result["pending_messages"] = cur.fetchone()['count']

        cur.close()

    finally:
        conn.close()

    if resume:
        return _format_resume(result)

    return result


def _extract_turns_from_jsonl(project: str, session_id: str = "") -> tuple[list[dict], str, str | None]:
    """Helper function to extract conversation turns from JSONL file.

    Returns:
        Tuple of (turns, jsonl_file_path, warning_message)
    """
    # Find project directory in ~/.claude/projects/
    home = Path.home()
    projects_dir = home / ".claude" / "projects"

    if not projects_dir.exists():
        raise FileNotFoundError(f"Projects directory not found: {projects_dir}")

    # Search for project directory (format: C--Projects-project-name)
    project_dirs = list(projects_dir.glob(f"*{project.replace('/', '-').replace('\\', '-')}*"))

    if not project_dirs:
        raise FileNotFoundError(f"No project directory found for '{project}' in {projects_dir}")

    project_dir = project_dirs[0]  # Take first match

    # Find JSONL file
    jsonl_files = list(project_dir.glob("*.jsonl"))

    if not jsonl_files:
        raise FileNotFoundError(f"No JSONL files found in {project_dir}")

    # Filter by session_id if provided, otherwise get most recent
    if session_id:
        matching = [f for f in jsonl_files if session_id.lower() in f.name.lower()]
        if not matching:
            raise FileNotFoundError(f"No JSONL file found matching session_id '{session_id}'")
        jsonl_file = matching[0]
    else:
        # Most recent by modification time
        jsonl_file = max(jsonl_files, key=lambda f: f.stat().st_mtime)

    # Check file size (limit to 10MB)
    file_size_mb = jsonl_file.stat().st_size / (1024 * 1024)
    truncate_warning = None
    if file_size_mb > 10:
        truncate_warning = f"File size {file_size_mb:.1f}MB > 10MB. Reading last 500 turns only."

    # Parse JSONL
    turns = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                msg_type = entry.get('type')

                if msg_type == 'user':
                    # User message: content is in message.content
                    content = entry.get('message', {}).get('content', '')
                    if content:
                        turns.append({"role": "user", "content": content})

                elif msg_type == 'assistant':
                    # Assistant message: extract text blocks only (skip tool_use)
                    message = entry.get('message', {})
                    content_blocks = message.get('content', [])

                    if isinstance(content_blocks, str):
                        turns.append({"role": "assistant", "content": content_blocks})
                    elif isinstance(content_blocks, list):
                        text_parts = []
                        for block in content_blocks:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text_parts.append(block.get('text', ''))
                        if text_parts:
                            turns.append({"role": "assistant", "content": '\n\n'.join(text_parts)})

            except json.JSONDecodeError:
                continue  # Skip malformed lines

    # Truncate if necessary
    if truncate_warning and len(turns) > 500:
        turns = turns[-500:]

    return turns, str(jsonl_file), truncate_warning


@mcp.tool()
def end_session(
    summary: str,
    next_steps: list[str] | None = None,
    tasks_completed: list[str] | None = None,
    learnings: list[str] | None = None,
    project: str = "",
) -> dict:
    """End the current session and save state to database.

    Use when: Finishing a work session. Saves summary, next steps, and learnings
    so the next session can pick up where you left off. Also extracts and stores
    the conversation for later search/insight extraction.
    Returns: {session_closed, session_id, state_saved, next_steps_saved,
              conversation_stored, conversation_id (if stored)}.

    Args:
        summary: Brief summary of what was accomplished this session.
        next_steps: List of things to do next session.
        tasks_completed: List of completed task descriptions.
        learnings: Key learnings or insights from this session.
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    next_steps = next_steps or []
    tasks_completed = tasks_completed or []
    learnings = learnings or []

    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()
        results = {}

        # 1. Close the session record
        if session_id:
            cur.execute("""
                UPDATE claude.sessions
                SET session_end = NOW(),
                    session_summary = %s,
                    tasks_completed = %s,
                    learnings_gained = %s
                WHERE session_id = %s::uuid
                  AND session_end IS NULL
                RETURNING session_id::text
            """, (summary, tasks_completed, learnings, session_id))
            closed = cur.fetchone()
            results["session_closed"] = closed is not None
            if closed:
                results["session_id"] = closed['session_id']
        else:
            # Try to close the most recent open session for this project
            cur.execute("""
                UPDATE claude.sessions
                SET session_end = NOW(),
                    session_summary = %s,
                    tasks_completed = %s,
                    learnings_gained = %s
                WHERE project_name = %s
                  AND session_end IS NULL
                  AND session_start > NOW() - INTERVAL '24 hours'
                RETURNING session_id::text
            """, (summary, tasks_completed, learnings, project))
            closed = cur.fetchone()
            results["session_closed"] = closed is not None
            if closed:
                results["session_id"] = closed['session_id']

        # 2. Update session_state (upsert)
        next_steps_json = json.dumps(next_steps) if next_steps else None
        cur.execute("""
            INSERT INTO claude.session_state (project_name, current_focus, next_steps, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (project_name) DO UPDATE SET
                current_focus = EXCLUDED.current_focus,
                next_steps = EXCLUDED.next_steps,
                updated_at = NOW()
        """, (project, summary, next_steps_json))

        results["state_saved"] = True
        results["next_steps_saved"] = len(next_steps)

        conn.commit()

        # 3. Extract and store conversation (after successful commit)
        closed_session_id = results.get("session_id")
        if closed_session_id:
            try:
                turns, jsonl_path, warning = _extract_turns_from_jsonl(project, closed_session_id)

                if turns:
                    # Calculate token estimate (rough: 1 token ≈ 4 characters)
                    total_chars = sum(len(turn.get("content", "")) for turn in turns)
                    token_estimate = total_chars // 4

                    # Insert into conversations table
                    cur.execute("""
                        INSERT INTO claude.conversations (
                            session_id, project_name, turns, turn_count,
                            token_count_estimate, summary, extracted_at
                        ) VALUES (
                            %s::uuid, %s, %s::jsonb, %s, %s, %s, NOW()
                        )
                        RETURNING conversation_id::text
                    """, (
                        closed_session_id,
                        project,
                        json.dumps(turns),
                        len(turns),
                        token_estimate,
                        summary
                    ))
                    conv_result = cur.fetchone()

                    # Log to audit_log
                    cur.execute("""
                        INSERT INTO claude.audit_log (
                            entity_type, entity_id, to_status, changed_by, change_source, metadata
                        ) VALUES (
                            'conversation', %s::uuid, 'extracted', 'end_session', 'end_session', %s::jsonb
                        )
                    """, (
                        conv_result['conversation_id'],
                        json.dumps({
                            "session_id": closed_session_id,
                            "turn_count": len(turns),
                            "jsonl_path": jsonl_path,
                            "truncated": warning is not None
                        })
                    ))

                    conn.commit()

                    results["conversation_extracted"] = True
                    results["turn_count"] = len(turns)
                    if warning:
                        results["conversation_warning"] = warning
                else:
                    results["conversation_extracted"] = False
                    results["conversation_note"] = "No turns found in JSONL"

            except FileNotFoundError:
                # Silently skip if JSONL not found
                results["conversation_extracted"] = False
                results["conversation_note"] = "JSONL file not found"
            except Exception as conv_err:
                # Don't fail the entire end_session if conversation extraction fails
                results["conversation_extracted"] = False
                results["conversation_error"] = str(conv_err)

        # 4. Convert learnings to searchable knowledge entries (with embeddings)
        if learnings and closed_session_id:
            knowledge_count = 0
            for learning in learnings[:5]:  # Cap at 5 to limit Voyage AI latency
                if len(learning) < 20:
                    continue
                try:
                    # Generate embedding for RAG searchability
                    embedding = None
                    try:
                        embedding = generate_embedding(learning)
                    except Exception:
                        pass  # Store without embedding if Voyage unavailable

                    cur.execute("""
                        INSERT INTO claude.knowledge (
                            knowledge_id, title, description, knowledge_type,
                            knowledge_category, source, confidence_level,
                            applies_to_projects, embedding, created_at
                        ) VALUES (
                            gen_random_uuid(), %s, %s, 'learned', %s,
                            %s, 85, %s, %s, NOW()
                        )
                    """, (
                        learning[:100],
                        learning,
                        project,
                        f"session:{closed_session_id}",
                        [project],
                        embedding,
                    ))
                    knowledge_count += 1
                except Exception:
                    pass
            if knowledge_count:
                conn.commit()
            results["knowledge_created"] = knowledge_count

        # 5. FB136: Auto-extract insights from conversation (if stored)
        if results.get("conversation_extracted") and closed_session_id:
            try:
                insight_result = extract_insights(closed_session_id, project)
                if insight_result.get("success"):
                    results["insights_extracted"] = insight_result.get("insights_count", 0)
                else:
                    results["insights_extracted"] = 0
            except Exception as insight_err:
                # Non-blocking - don't fail end_session for insight extraction
                results["insights_extracted"] = 0
                results["insights_error"] = str(insight_err)

        knowledge_note = f", {results['knowledge_created']} knowledge entries created" if results.get("knowledge_created") else ""
        insights_note = f", {results['insights_extracted']} insights extracted" if results.get("insights_extracted") else ""
        results["summary"] = f"Session ended. {len(tasks_completed)} tasks logged, {len(next_steps)} next steps saved{knowledge_note}{insights_note}."
        return results

    except Exception as e:
        conn.rollback()
        return {"error": f"Failed to end session: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def save_checkpoint(
    focus: str,
    progress_notes: str = "",
    project: str = "",
) -> dict:
    """Save a mid-session checkpoint without closing the session.

    Use when: You want to persist current progress (e.g., before a risky
    operation, or periodically during long sessions). Does NOT close the session.
    Returns: {success, project, focus_saved, timestamp}.

    Args:
        focus: What you're currently working on.
        progress_notes: Brief notes on progress so far.
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())

    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Upsert session_state
        cur.execute("""
            INSERT INTO claude.session_state (project_name, current_focus, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (project_name) DO UPDATE SET
                current_focus = EXCLUDED.current_focus,
                updated_at = NOW()
        """, (project, focus))

        # Optionally update current session metadata
        session_id = os.environ.get('CLAUDE_SESSION_ID')
        if session_id and progress_notes:
            cur.execute("""
                UPDATE claude.sessions
                SET session_metadata = COALESCE(session_metadata, '{}'::jsonb)
                    || jsonb_build_object(
                        'last_checkpoint', NOW()::text,
                        'checkpoint_notes', %s
                    )
                WHERE session_id = %s::uuid
            """, (progress_notes, session_id))

        conn.commit()

        return {
            "success": True,
            "project": project,
            "focus_saved": focus,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        conn.rollback()
        return {"error": f"Failed to save checkpoint: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


# ============================================================================
# Workflow Engine - State Machine Enforcement
# ============================================================================

class WorkflowEngine:
    """Validates state transitions against claude.workflow_transitions table,
    executes side effects, and logs all changes to claude.audit_log.

    Usage:
        engine = WorkflowEngine(conn)
        result = engine.execute_transition('build_tasks', task_id, 'completed',
                                           changed_by=session_id)
    """

    # Map entity_type to (table, pk_column, short_code_prefix)
    ENTITY_MAP = {
        'feedback':    ('claude.feedback',    'feedback_id', 'FB'),
        'features':    ('claude.features',    'feature_id',  'F'),
        'build_tasks': ('claude.build_tasks', 'task_id',     'BT'),
    }

    def __init__(self, conn):
        self.conn = conn

    def _resolve_entity(self, entity_type: str, item_id: str) -> tuple:
        """Resolve item_id (UUID or short code like 'BT3') to (uuid, current_status, short_code).

        Returns (entity_uuid, current_status, short_code) or raises ValueError.
        """
        if entity_type not in self.ENTITY_MAP:
            raise ValueError(f"Unknown entity_type: {entity_type}")

        table, pk_col, prefix = self.ENTITY_MAP[entity_type]
        cur = self.conn.cursor()
        try:
            # Try short code first (e.g., 'BT3', 'F12', 'FB5')
            clean_id = item_id.upper().strip()
            if clean_id.startswith(prefix):
                code_num = clean_id[len(prefix):]
                if code_num.isdigit():
                    cur.execute(f"""
                        SELECT {pk_col}::text, status, short_code
                        FROM {table}
                        WHERE short_code = %s
                    """, (int(code_num),))
                    row = cur.fetchone()
                    if row:
                        return (row[pk_col], row['status'], row['short_code'])

            # Try UUID
            cur.execute(f"""
                SELECT {pk_col}::text, status, short_code
                FROM {table}
                WHERE {pk_col}::text = %s
            """, (item_id,))
            row = cur.fetchone()
            if row:
                return (row[pk_col], row['status'], row['short_code'])

            raise ValueError(f"{entity_type} '{item_id}' not found")
        finally:
            cur.close()

    def validate_transition(self, entity_type: str, from_status: str, to_status: str) -> dict:
        """Check if a transition is valid. Returns transition row or None."""
        cur = self.conn.cursor()
        try:
            cur.execute("""
                SELECT transition_id, requires_condition, side_effect, description
                FROM claude.workflow_transitions
                WHERE entity_type = %s AND from_status = %s AND to_status = %s
            """, (entity_type, from_status, to_status))
            return cur.fetchone()
        finally:
            cur.close()

    def check_condition(self, condition_name: str, entity_type: str, entity_id: str) -> tuple:
        """Evaluate a named condition. Returns (passed: bool, message: str)."""
        cur = self.conn.cursor()
        try:
            if condition_name == 'all_tasks_done':
                # All build_tasks for this feature must be completed or cancelled
                cur.execute("""
                    SELECT COUNT(*) as remaining
                    FROM claude.build_tasks
                    WHERE feature_id = %s::uuid
                      AND status NOT IN ('completed', 'cancelled')
                """, (entity_id,))
                row = cur.fetchone()
                remaining = row['remaining']
                if remaining > 0:
                    return (False, f"{remaining} task(s) still not completed")
                return (True, "All tasks completed")

            if condition_name == 'has_assignee':
                cur.execute("""
                    SELECT assigned_to FROM claude.build_tasks WHERE task_id = %s::uuid
                """, (entity_id,))
                row = cur.fetchone()
                if row and row.get('assigned_to'):
                    return (True, "Has assignee")
                return (False, "No assignee set")

            # Unknown condition - pass by default (log warning)
            return (True, f"Unknown condition '{condition_name}' - passed by default")
        finally:
            cur.close()

    def execute_side_effect(self, side_effect_name: str, entity_type: str, entity_id: str) -> str:
        """Execute a named side effect. Returns description of what happened."""
        cur = self.conn.cursor()
        try:
            if side_effect_name == 'check_feature_completion':
                # When a build_task completes, check if all tasks for the parent feature are done
                cur.execute("""
                    SELECT f.feature_id::text, f.status, 'F' || f.short_code as code,
                           (SELECT COUNT(*) FROM claude.build_tasks bt
                            WHERE bt.feature_id = f.feature_id
                              AND bt.status NOT IN ('completed', 'cancelled')) as remaining
                    FROM claude.build_tasks bt
                    JOIN claude.features f ON bt.feature_id = f.feature_id
                    WHERE bt.task_id = %s::uuid
                """, (entity_id,))
                row = cur.fetchone()
                if row and row['remaining'] == 0 and row['status'] == 'in_progress':
                    return f"All tasks done for {row['code']}. Feature ready for completion."
                elif row:
                    return f"{row['remaining']} task(s) remaining for {row['code']}"
                return "No parent feature found"

            if side_effect_name == 'set_started_at':
                cur.execute("""
                    UPDATE claude.build_tasks
                    SET started_at = COALESCE(started_at, NOW())
                    WHERE task_id = %s::uuid
                """, (entity_id,))
                return "Set started_at timestamp"

            if side_effect_name == 'archive_plan_data':
                # Could archive plan_data to a history table - for now just log
                return "Plan data archived (no-op)"

            return f"Unknown side effect '{side_effect_name}'"
        finally:
            cur.close()

    def execute_transition(
        self,
        entity_type: str,
        item_id: str,
        new_status: str,
        changed_by: str = None,
        change_source: str = 'workflow_engine',
        metadata: dict = None,
    ) -> dict:
        """Validate and execute a state transition.

        Returns dict with:
            success: bool
            from_status: previous status
            to_status: new status
            entity_code: short code (e.g., 'BT3')
            side_effects: list of side effect results
            condition_results: dict of condition checks
            error: error message if failed
        """
        result = {
            'success': False,
            'entity_type': entity_type,
            'item_id': item_id,
            'side_effects': [],
            'condition_results': {},
        }

        try:
            # 1. Resolve entity
            entity_uuid, current_status, short_code = self._resolve_entity(entity_type, item_id)
            _, _, prefix = self.ENTITY_MAP[entity_type]
            entity_code = f"{prefix}{short_code}"

            result['from_status'] = current_status
            result['to_status'] = new_status
            result['entity_code'] = entity_code
            result['entity_id'] = entity_uuid

            # 2. Validate transition
            transition = self.validate_transition(entity_type, current_status, new_status)
            if not transition:
                # Get valid transitions for error message
                cur = self.conn.cursor()
                try:
                    cur.execute("""
                        SELECT to_status, description
                        FROM claude.workflow_transitions
                        WHERE entity_type = %s AND from_status = %s
                    """, (entity_type, current_status))
                    valid = [f"{r['to_status']} ({r['description']})" for r in cur.fetchall()]
                finally:
                    cur.close()
                result['error'] = (
                    f"Invalid transition: {entity_code} cannot go from "
                    f"'{current_status}' to '{new_status}'. "
                    f"Valid transitions: {', '.join(valid) if valid else 'none'}"
                )
                return result

            # 3. Check conditions
            if transition.get('requires_condition'):
                condition = transition['requires_condition']
                passed, message = self.check_condition(condition, entity_type, entity_uuid)
                result['condition_results'][condition] = {'passed': passed, 'message': message}
                if not passed:
                    result['error'] = f"Condition '{condition}' not met: {message}"
                    return result

            # 4. Execute the status update
            table, pk_col, _ = self.ENTITY_MAP[entity_type]
            cur = self.conn.cursor()
            try:
                cur.execute(f"""
                    UPDATE {table}
                    SET status = %s, updated_at = NOW()
                    WHERE {pk_col} = %s::uuid
                """, (new_status, entity_uuid))

                # 5. Execute side effects
                if transition.get('side_effect'):
                    effect_result = self.execute_side_effect(
                        transition['side_effect'], entity_type, entity_uuid
                    )
                    result['side_effects'].append({
                        'name': transition['side_effect'],
                        'result': effect_result,
                    })

                # 6. Log to audit_log
                cur.execute("""
                    INSERT INTO claude.audit_log
                    (entity_type, entity_id, entity_code, from_status, to_status,
                     changed_by, change_source, side_effects_executed, metadata)
                    VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    entity_type, entity_uuid, entity_code,
                    current_status, new_status,
                    changed_by, change_source,
                    [se['name'] for se in result['side_effects']] or None,
                    json.dumps(metadata) if metadata else None,
                ))

                self.conn.commit()
                result['success'] = True
                return result
            finally:
                cur.close()

        except ValueError as e:
            result['error'] = str(e)
            return result
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            result['error'] = f"Transition failed: {str(e)}"
            return result


# ============================================================================
# Phase 2 Tools - Workflow-Enforced Operations
# ============================================================================

@mcp.tool()
def advance_status(
    item_type: Literal["feedback", "features", "build_tasks"],
    item_id: str,
    new_status: str,
) -> dict:
    """Move a work item to a new status through the workflow state machine.

    Validates the transition is allowed, checks any required conditions,
    executes side effects, and logs to audit_log.

    Use when: Changing status of any feedback, feature, or build task. Prefer
    start_work/complete_work for build tasks (they add context loading).
    Returns: {success, entity_type, entity_id, entity_code, from_status, to_status,
              side_effects_executed}. On invalid transition: {success: false, error,
              valid_transitions: [list of allowed next statuses]}.

    Args:
        item_type: Entity type: feedback, features, or build_tasks.
        item_id: Item ID or short_code (e.g., 'FB12', 'F5', 'BT23').
        new_status: Target status. Invalid transitions are rejected with valid options shown.
    """
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    conn = get_db_connection()
    try:
        engine = WorkflowEngine(conn)
        return engine.execute_transition(
            entity_type=item_type,
            item_id=item_id,
            new_status=new_status,
            changed_by=session_id,
            change_source='mcp_tool',
        )
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def start_work(
    task_code: str,
) -> dict:
    """Start working on a build task: transitions todo->in_progress, sets focus, returns plan_data.

    Shortcut for advance_status('build_tasks', code, 'in_progress') plus
    context loading. Returns the task details and parent feature plan_data
    so you know what to build.

    Use when: Beginning implementation of a build task. Call this instead of
    advance_status for build tasks - it loads task context automatically.
    Returns: {success, entity_code, task_context: {task_name, description, type,
              files_affected, verification, feature_code, feature_name, plan_data}}.

    Args:
        task_code: Task short code (e.g., 'BT3') or UUID.
    """
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    conn = get_db_connection()
    try:
        engine = WorkflowEngine(conn)

        # Transition to in_progress
        transition_result = engine.execute_transition(
            entity_type='build_tasks',
            item_id=task_code,
            new_status='in_progress',
            changed_by=session_id,
            change_source='start_work',
        )

        if not transition_result.get('success'):
            return transition_result

        # Load task context + parent feature plan_data
        entity_id = transition_result.get('entity_id')
        cur = conn.cursor()
        cur.execute("""
            SELECT
                bt.task_name,
                bt.task_description,
                bt.task_type,
                bt.files_affected,
                bt.verification,
                'F' || f.short_code as feature_code,
                f.feature_name,
                f.plan_data
            FROM claude.build_tasks bt
            JOIN claude.features f ON bt.feature_id = f.feature_id
            WHERE bt.task_id = %s::uuid
        """, (entity_id,))
        task_row = cur.fetchone()

        if task_row:
            transition_result['task_context'] = {
                'task_name': task_row['task_name'],
                'description': task_row['task_description'],
                'type': task_row['task_type'],
                'files_affected': task_row['files_affected'] or [],
                'verification': task_row['verification'],
                'feature_code': task_row['feature_code'],
                'feature_name': task_row['feature_name'],
                'plan_data': task_row['plan_data'],
            }

        # Update session focus
        project = os.path.basename(os.getcwd())
        focus_text = f"Working on {transition_result.get('entity_code')}: {task_row['task_name'] if task_row else 'unknown'}"
        cur.execute("""
            INSERT INTO claude.session_state (project_name, current_focus, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (project_name) DO UPDATE SET
                current_focus = EXCLUDED.current_focus,
                updated_at = NOW()
        """, (project, focus_text))
        conn.commit()

        return transition_result

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def complete_work(
    task_code: str,
) -> dict:
    """Complete a build task: transitions in_progress->completed, checks parent feature, returns next task.

    Shortcut for advance_status('build_tasks', code, 'completed') plus
    feature completion check and next-task suggestion.

    Use when: Finishing a build task. Call this instead of advance_status -
    it checks if all sibling tasks are done and suggests the next ready task.
    Returns: {success, entity_code, next_task: {next_task_code, next_task_name,
              next_task_type} or null, message}.

    Args:
        task_code: Task short code (e.g., 'BT3') or UUID.
    """
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    conn = get_db_connection()
    try:
        engine = WorkflowEngine(conn)

        # Transition to completed
        transition_result = engine.execute_transition(
            entity_type='build_tasks',
            item_id=task_code,
            new_status='completed',
            changed_by=session_id,
            change_source='complete_work',
        )

        if not transition_result.get('success'):
            return transition_result

        # Find next ready task from same feature
        entity_id = transition_result.get('entity_id')
        cur = conn.cursor()
        cur.execute("""
            SELECT
                'BT' || bt2.short_code as next_task_code,
                bt2.task_name as next_task_name,
                bt2.task_type as next_task_type
            FROM claude.build_tasks bt
            JOIN claude.build_tasks bt2 ON bt2.feature_id = bt.feature_id
            WHERE bt.task_id = %s::uuid
              AND bt2.status = 'todo'
              AND (bt2.blocked_by_task_id IS NULL
                   OR bt2.blocked_by_task_id IN (
                       SELECT task_id FROM claude.build_tasks WHERE status = 'completed'
                   ))
            ORDER BY bt2.step_order
            LIMIT 1
        """, (entity_id,))
        next_task = cur.fetchone()

        if next_task:
            transition_result['next_task'] = dict(next_task)
        else:
            transition_result['next_task'] = None
            transition_result['message'] = "No more ready tasks for this feature."

        return transition_result

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_work_context(
    scope: Literal["current", "feature", "project"] = "current",
    project: str = "",
) -> dict:
    """Get token-budgeted work context at different zoom levels.

    - current (~200 tokens): Active task, its description, files_affected
    - feature (~500 tokens): Current feature, all its tasks with statuses
    - project (~800 tokens): All active features, ready tasks, pending feedback

    Use when: You need to understand what you're working on without loading
    full session context. Use 'current' mid-task, 'feature' for planning,
    'project' for orientation. Replaces the old get_session_context RAG hook.
    Returns: {scope, project, active_task} for current; {scope, project,
              feature, tasks: []} for feature; {scope, project, features: [],
              ready_tasks: [], feedback: []} for project.

    Args:
        scope: Zoom level: 'current' for active task, 'feature' for parent feature,
               'project' for full project overview.
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())
    project_id = get_project_id(project)

    if not project_id:
        return {"error": f"Project '{project}' not found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        result = {"scope": scope, "project": project}

        if scope == "current":
            # Active task (in_progress build_task for this project)
            cur.execute("""
                SELECT
                    'BT' || bt.short_code as code,
                    bt.task_name,
                    bt.task_description,
                    bt.task_type,
                    bt.files_affected,
                    bt.verification,
                    'F' || f.short_code as feature_code,
                    f.feature_name
                FROM claude.build_tasks bt
                JOIN claude.features f ON bt.feature_id = f.feature_id
                WHERE bt.project_id = %s::uuid AND bt.status = 'in_progress'
                ORDER BY bt.updated_at DESC
                LIMIT 1
            """, (project_id,))
            task = cur.fetchone()
            result['active_task'] = dict(task) if task else None

        elif scope == "feature":
            # Current feature + all its tasks
            # First: find feature via its in_progress task (most reliable)
            # Fallback: feature with status 'in_progress'
            cur.execute("""
                (SELECT
                    'F' || f.short_code as code,
                    f.feature_name,
                    f.description,
                    f.status,
                    f.plan_data
                FROM claude.features f
                JOIN claude.build_tasks bt ON bt.feature_id = f.feature_id
                WHERE f.project_id = %s::uuid AND bt.status = 'in_progress'
                ORDER BY bt.updated_at DESC
                LIMIT 1)
                UNION ALL
                (SELECT
                    'F' || f.short_code as code,
                    f.feature_name,
                    f.description,
                    f.status,
                    f.plan_data
                FROM claude.features f
                WHERE f.project_id = %s::uuid AND f.status = 'in_progress'
                ORDER BY f.updated_at DESC
                LIMIT 1)
                LIMIT 1
            """, (project_id, project_id))
            feature = cur.fetchone()

            if feature:
                result['feature'] = dict(feature)
                # Get all tasks for this feature
                feature_code = feature['code']
                short_code = int(feature_code[1:])
                cur.execute("""
                    SELECT
                        'BT' || bt.short_code as code,
                        bt.task_name,
                        bt.status,
                        bt.step_order
                    FROM claude.build_tasks bt
                    JOIN claude.features f ON bt.feature_id = f.feature_id
                    WHERE f.short_code = %s AND f.project_id = %s::uuid
                    ORDER BY bt.step_order
                """, (short_code, project_id))
                result['tasks'] = [dict(r) for r in cur.fetchall()]
            else:
                result['feature'] = None

        elif scope == "project":
            # All active features + ready tasks + feedback count
            cur.execute("""
                WITH active_features AS (
                    SELECT
                        'F' || f.short_code as code,
                        f.feature_name,
                        f.status,
                        f.priority,
                        (SELECT COUNT(*) FROM claude.build_tasks bt
                         WHERE bt.feature_id = f.feature_id AND bt.status = 'completed') as done,
                        (SELECT COUNT(*) FROM claude.build_tasks bt
                         WHERE bt.feature_id = f.feature_id) as total
                    FROM claude.features f
                    WHERE f.project_id = %s::uuid
                      AND f.status NOT IN ('completed', 'cancelled')
                    ORDER BY f.priority, f.short_code
                    LIMIT 10
                ),
                ready_tasks AS (
                    SELECT
                        'BT' || bt.short_code as code,
                        bt.task_name,
                        'F' || f.short_code as feature_code
                    FROM claude.build_tasks bt
                    JOIN claude.features f ON bt.feature_id = f.feature_id
                    WHERE bt.project_id = %s::uuid AND bt.status = 'todo'
                      AND (bt.blocked_by_task_id IS NULL
                           OR bt.blocked_by_task_id IN (
                               SELECT task_id FROM claude.build_tasks WHERE status = 'completed'))
                    ORDER BY f.priority, bt.step_order
                    LIMIT 5
                ),
                feedback_counts AS (
                    SELECT
                        status,
                        COUNT(*) as cnt
                    FROM claude.feedback
                    WHERE project_id = %s::uuid
                      AND status NOT IN ('resolved', 'wont_fix', 'duplicate')
                    GROUP BY status
                )
                SELECT 'features' as section, json_agg(row_to_json(af)) as data FROM active_features af
                UNION ALL
                SELECT 'ready_tasks', json_agg(row_to_json(rt)) FROM ready_tasks rt
                UNION ALL
                SELECT 'feedback', json_agg(row_to_json(fc)) FROM feedback_counts fc
            """, (project_id, project_id, project_id))

            for row in cur.fetchall():
                section = row['section']
                data = row['data']
                if data:
                    if isinstance(data, str):
                        data = json.loads(data)
                    result[section] = data
                else:
                    result[section] = []

        return result

    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def create_linked_task(
    feature_code: str,
    task_name: str,
    task_description: str,
    verification: str,
    files_affected: list[str],
    task_type: Literal["implementation", "testing", "documentation", "deployment", "investigation"] = "implementation",
    priority: int = 3,
    estimated_hours: float | None = None,
    blocked_by: str | None = None,
) -> dict:
    """Create a build task linked to an active feature. Rejects if feature is not active.

    Enforces that tasks must belong to a valid in-progress or planned feature.
    Auto-assigns step_order based on existing tasks.

    Use when: Breaking a feature into implementation steps. Feature must be
    'planned' or 'in_progress'. Use add_build_task for simpler/less strict tasks.
    Returns: {success, task_code (e.g. 'BT42'), task_id, feature_code,
              feature_name, step_order, priority, status: 'todo'}.

    REQUIRED DETAIL LEVEL - the tool will reject vague tasks:
    - task_description: Must be >= 100 chars. Include WHAT to build, WHERE in the code,
      HOW it connects to existing code, and EDGE CASES to handle.
    - verification: Must be non-empty. How to verify this task is complete.
      Include specific test commands, expected output, or observable behavior.
    - files_affected: Must have at least one file path. List every file this task modifies.

    Args:
        feature_code: Feature short code (e.g., 'F12') or UUID.
        task_name: Name of the task (concise, imperative).
        task_description: Detailed implementation spec (>= 100 chars). Must include:
            what to build, where, how it connects, edge cases.
        verification: How to verify completion (non-empty). Specific commands/checks.
        files_affected: Files this task modifies (>= 1 file). Full relative paths.
        task_type: implementation, testing, documentation, deployment, or investigation.
        priority: 1=critical, 2=high, 3=normal, 4=low, 5=backlog. Default 3.
        estimated_hours: Rough estimate (optional but recommended).
        blocked_by: Task code that must complete first (e.g., 'BT316'). Optional.
    """
    # === QUALITY ENFORCEMENT (Tier 1 - tool rejects vague tasks) ===
    errors = []
    if not task_description or len(task_description.strip()) < 100:
        errors.append(
            f"task_description must be >= 100 chars (got {len(task_description.strip()) if task_description else 0}). "
            "Include: WHAT to build, WHERE in the code, HOW it connects, EDGE CASES."
        )
    if not verification or len(verification.strip()) < 10:
        errors.append(
            "verification is required. Describe how to verify this task is complete: "
            "test commands, expected output, or observable behavior."
        )
    if not files_affected or len(files_affected) == 0:
        errors.append(
            "files_affected must list at least one file path this task will modify."
        )
    if priority not in (1, 2, 3, 4, 5):
        errors.append("priority must be 1-5 (1=critical, 5=backlog).")
    if errors:
        return {
            "success": False,
            "error": "Task rejected - insufficient detail. Fix these issues:\n" + "\n".join(f"  - {e}" for e in errors),
            "hint": "Build tasks must be detailed enough for a future session to implement "
                    "without the original conversation context."
        }

    # Resolve blocked_by to task_id if provided
    blocked_by_task_id = None

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if blocked_by:
            blocked_code = blocked_by.upper().strip()
            if blocked_code.startswith('BT') and blocked_code[2:].isdigit():
                cur.execute(
                    "SELECT task_id::text FROM claude.build_tasks WHERE short_code = %s",
                    (int(blocked_code[2:]),)
                )
                blocker = cur.fetchone()
                if blocker:
                    blocked_by_task_id = blocker['task_id']
                else:
                    return {"success": False, "error": f"Blocked-by task '{blocked_by}' not found"}

        # Resolve feature
        clean_code = feature_code.upper().strip()
        if clean_code.startswith('F') and clean_code[1:].isdigit():
            cur.execute("""
                SELECT feature_id::text, project_id::text, status, feature_name
                FROM claude.features
                WHERE short_code = %s
            """, (int(clean_code[1:]),))
        else:
            cur.execute("""
                SELECT feature_id::text, project_id::text, status, feature_name
                FROM claude.features
                WHERE feature_id::text = %s
            """, (feature_code,))

        feature = cur.fetchone()
        if not feature:
            return {"success": False, "error": f"Feature '{feature_code}' not found"}

        if feature['status'] not in ('planned', 'in_progress'):
            return {
                "success": False,
                "error": f"Feature '{clean_code}' has status '{feature['status']}'. "
                         f"Tasks can only be added to 'planned' or 'in_progress' features."
            }

        # Get next step_order
        cur.execute("""
            SELECT COALESCE(MAX(step_order), 0) + 1 as next_order
            FROM claude.build_tasks
            WHERE feature_id = %s::uuid
        """, (feature['feature_id'],))
        next_order = cur.fetchone()['next_order']

        # Get next short_code
        cur.execute("SELECT COALESCE(MAX(short_code), 0) + 1 as next_code FROM claude.build_tasks")
        next_code = cur.fetchone()['next_code']

        # Insert task with full detail
        cur.execute("""
            INSERT INTO claude.build_tasks
            (task_id, feature_id, project_id, task_name, task_description,
             task_type, files_affected, verification, priority, estimated_hours,
             blocked_by_task_id, status, step_order, short_code, created_at, updated_at)
            VALUES (gen_random_uuid(), %s::uuid, %s::uuid, %s, %s, %s, %s,
                    %s, %s, %s, %s::uuid, 'todo', %s, %s, NOW(), NOW())
            RETURNING task_id::text, short_code
        """, (
            feature['feature_id'], feature['project_id'],
            task_name, task_description, task_type,
            files_affected, verification, priority, estimated_hours,
            blocked_by_task_id, next_order, next_code,
        ))

        new_task = cur.fetchone()
        conn.commit()

        return {
            "success": True,
            "task_code": f"BT{new_task['short_code']}",
            "task_id": new_task['task_id'],
            "feature_code": clean_code,
            "feature_name": feature['feature_name'],
            "step_order": next_order,
            "priority": priority,
            "verification": verification,
            "blocked_by": blocked_by,
            "status": "todo",
        }

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# Phase 3 Tools - Configuration & Session Management
# ============================================================================

@mcp.tool()
def extract_conversation(
    session_id: str = "",
    project: str = "",
) -> dict:
    """Extract conversation turns from a session's JSONL log file.

    Finds and parses the JSONL conversation log to extract user/assistant turns.
    Skips tool_use blocks, returning only text content for readability.

    Use when: Reviewing what happened in a past session, or feeding conversation
    data to extract_insights. Dependencies: None, but store result in
    claude.conversations via end_session for persistence.
    Returns: {success, session_file, turn_count, turns: [{role, content}],
              truncated, warning}.

    Args:
        session_id: Session ID (UUID or prefix). If omitted, uses most recent JSONL in project.
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())

    try:
        turns, jsonl_file, warning = _extract_turns_from_jsonl(project, session_id)

        return {
            "success": True,
            "session_file": jsonl_file,
            "turn_count": len(turns),
            "turns": turns,
            "truncated": warning is not None,
            "warning": warning,
        }

    except FileNotFoundError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to extract conversation: {str(e)}"}


# ============================================================================
# Phase 3 Tools - Book Reference System
# ============================================================================

@mcp.tool()
def store_book(
    title: str,
    author: str = "",
    isbn: str = "",
    year: int | None = None,
    topics: list[str] | None = None,
    summary: str = "",
) -> dict:
    """Store a book in the reference library.

    Use when: Adding a new book you want to reference later. Call this before
    store_book_reference to create the parent book record.
    Returns: {success, book_id, title}.

    Args:
        title: Book title (required).
        author: Book author.
        isbn: ISBN identifier.
        year: Publication year.
        topics: List of topic tags.
        summary: Brief summary of the book.
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Insert book
        cur.execute("""
            INSERT INTO claude.books (
                book_id, title, author, isbn, year, topics, summary, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            RETURNING book_id::text
        """, (title, author, isbn, year, topics or [], summary))

        result = cur.fetchone()
        conn.commit()

        return {
            "success": True,
            "book_id": result['book_id'],
            "title": title,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to store book: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def store_book_reference(
    book_title: str,
    concept: str,
    chapter: str = "",
    page_range: str = "",
    description: str = "",
    quote: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Store a reference to a concept, quote, or insight from a book.

    Generates semantic embedding for the concept+description for later retrieval
    via recall_book_reference.

    Use when: Capturing a specific idea, quote, or pattern from a book. The book
    must already exist (use store_book first). Embedding is auto-generated.
    Returns: {success, ref_id, book_id, has_embedding, concept}.

    Args:
        book_title: Title of the book (case-insensitive lookup).
        concept: The concept or idea being referenced.
        chapter: Chapter name or number.
        page_range: Page range (e.g., "45-47", "102").
        description: Explanation or context for the concept.
        quote: Direct quote from the book.
        tags: List of tags for categorization.
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # 1. Lookup book_id by title (case-insensitive)
        cur.execute("""
            SELECT book_id::text FROM claude.books
            WHERE title ILIKE %s
            LIMIT 1
        """, (book_title,))

        book_result = cur.fetchone()
        if not book_result:
            return {
                "success": False,
                "error": f"Book not found: '{book_title}'. Use store_book first.",
            }

        book_id = book_result['book_id']

        # 2. Generate embedding for concept + description
        embedding = None
        has_embedding = False
        try:
            embedding_text = f"{concept}: {description}" if description else concept
            embedding = generate_embedding(embedding_text)
            has_embedding = embedding is not None
        except Exception as embed_err:
            print(f"Warning: Embedding generation failed for book reference: {embed_err}", file=sys.stderr)

        # 3. Insert reference
        cur.execute("""
            INSERT INTO claude.book_references (
                ref_id, book_id, chapter, page_range, concept, description, quote, tags, embedding, created_at
            ) VALUES (
                gen_random_uuid(), %s::uuid, %s, %s, %s, %s, %s, %s, %s::vector, NOW()
            )
            RETURNING ref_id::text
        """, (book_id, chapter, page_range, concept, description, quote, tags or [], embedding))

        result = cur.fetchone()
        conn.commit()

        return {
            "success": True,
            "ref_id": result['ref_id'],
            "book_id": book_id,
            "has_embedding": has_embedding,
            "concept": concept,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to store book reference: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def recall_book_reference(
    query: str,
    book_title: str = "",
    tags: list[str] | None = None,
    limit: int = 5,
) -> dict:
    """Search book references using semantic similarity.

    Finds concepts, quotes, and insights from books that match the query.

    Use when: Looking for ideas or patterns from books you've read. Uses
    Voyage AI embeddings for semantic search (not keyword matching).
    Returns: {success, query, result_count, references: [{ref_id, book: {title,
              author, year}, concept, description, quote, chapter, page_range,
              tags, similarity}]}.

    Args:
        query: Natural language search query.
        book_title: Optional filter by book title (case-insensitive).
        tags: Optional filter by tags (matches any).
        limit: Maximum number of results (default 5).
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # 1. Generate query embedding
        query_embedding = None
        try:
            query_embedding = generate_query_embedding(query)
        except Exception as embed_err:
            return {
                "success": False,
                "error": f"Failed to generate query embedding: {str(embed_err)}",
            }

        if not query_embedding:
            return {
                "success": False,
                "error": "Query embedding generation returned None",
            }

        # 2. Build query with optional filters
        sql = """
            SELECT
                br.ref_id::text,
                br.concept,
                br.description,
                br.quote,
                br.chapter,
                br.page_range,
                br.tags,
                b.book_id::text,
                b.title,
                b.author,
                b.year,
                1 - (br.embedding <=> %s::vector) as similarity
            FROM claude.book_references br
            JOIN claude.books b ON br.book_id = b.book_id
            WHERE br.embedding IS NOT NULL
        """

        params = [query_embedding]

        # Add book_title filter
        if book_title:
            sql += " AND b.title ILIKE %s"
            params.append(f"%{book_title}%")

        # Add tags filter (array overlap)
        if tags:
            sql += " AND br.tags && %s"
            params.append(tags)

        # Similarity threshold and ordering
        sql += """
            AND (1 - (br.embedding <=> %s::vector)) >= 0.5
            ORDER BY similarity DESC
            LIMIT %s
        """
        params.append(query_embedding)
        params.append(limit)

        cur.execute(sql, params)
        results = cur.fetchall()

        # Format results
        references = []
        for row in results:
            references.append({
                "ref_id": row['ref_id'],
                "book": {
                    "book_id": row['book_id'],
                    "title": row['title'],
                    "author": row['author'],
                    "year": row['year'],
                },
                "concept": row['concept'],
                "description": row['description'],
                "quote": row['quote'],
                "chapter": row['chapter'],
                "page_range": row['page_range'],
                "tags": row['tags'],
                "similarity": float(row['similarity']),
            })

        return {
            "success": True,
            "query": query,
            "result_count": len(references),
            "references": references,
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to recall book references: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


# ============================================================================
# Phase 4 Tools - Conversation Intelligence
# ============================================================================

@mcp.tool()
def extract_insights(
    session_id: str,
    project: str = "",
) -> dict:
    """Extract knowledge insights from a stored conversation.

    Reads turns from claude.conversations and identifies decisions, requirements,
    architectural directions, and patterns. Creates knowledge entries automatically.

    Use when: Mining a past conversation for reusable knowledge. Conversation must
    already be stored (via end_session or extract_conversation + manual insert).
    Pattern-matches user turns for decisions, rules, learnings, and patterns.
    Returns: {success, insights_count, insight_summaries: [{knowledge_id, title,
              type, turn_index}]}.

    Args:
        session_id: Session ID (UUID) to extract insights from.
        project: Project name filter (optional).
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # 1. Fetch conversation
        sql = """
            SELECT conversation_id, session_id, project_name, turns, turn_count, summary
            FROM claude.conversations
            WHERE session_id = %s::uuid
        """
        params = [session_id]

        if project:
            sql += " AND project_name = %s"
            params.append(project)

        cur.execute(sql, params)
        row = cur.fetchone()

        if not row:
            return {
                "success": False,
                "error": f"No conversation found for session_id={session_id}",
            }

        project_name = row['project_name']
        turns = row['turns']

        if not turns or not isinstance(turns, list):
            return {
                "success": False,
                "error": "Conversation has no turns to analyze",
            }

        # 2. Extract insights from user turns
        insights = []

        # Pattern matching for different insight types
        decision_patterns = [
            "we should", "let's", "the approach is", "we'll use", "i'll use",
            "decided to", "going with", "the plan is", "strategy is"
        ]
        rule_patterns = [
            "make sure", "always", "never", "must", "required",
            "don't", "avoid", "important to", "critical that"
        ]
        learning_patterns = [
            "i learned", "the fix was", "the problem was", "turned out",
            "discovered that", "realized that", "found that", "issue was"
        ]
        pattern_patterns = [
            "the pattern is", "this works because", "pattern for",
            "approach works", "solution is to", "technique is"
        ]

        for i, turn in enumerate(turns):
            if not isinstance(turn, dict):
                continue

            role = turn.get('role', '')
            content = turn.get('content', '')

            if role != 'user' or not content:
                continue

            content_lower = content.lower()

            # Check for decision insights
            for pattern in decision_patterns:
                if pattern in content_lower:
                    # Extract context (surrounding turns for better description)
                    context_parts = [content]
                    if i + 1 < len(turns) and isinstance(turns[i + 1], dict):
                        context_parts.append(turns[i + 1].get('content', '')[:300])

                    insights.append({
                        'type': 'fact',
                        'title': f"Decision: {content[:80]}...",
                        'content': content,
                        'context': '\n\n'.join(context_parts[:2]),
                        'turn_index': i
                    })
                    break

            # Check for rule/preference insights
            for pattern in rule_patterns:
                if pattern in content_lower:
                    insights.append({
                        'type': 'preference',
                        'title': f"Rule: {content[:80]}...",
                        'content': content,
                        'context': content,
                        'turn_index': i
                    })
                    break

            # Check for learning insights
            for pattern in learning_patterns:
                if pattern in content_lower:
                    insights.append({
                        'type': 'learned',
                        'title': f"Learning: {content[:80]}...",
                        'content': content,
                        'context': content,
                        'turn_index': i
                    })
                    break

            # Check for pattern insights
            for pattern in pattern_patterns:
                if pattern in content_lower:
                    insights.append({
                        'type': 'pattern',
                        'title': f"Pattern: {content[:80]}...",
                        'content': content,
                        'context': content,
                        'turn_index': i
                    })
                    break

        if not insights:
            return {
                "success": True,
                "insights_count": 0,
                "message": "No insights extracted from conversation",
            }

        # 3. Store insights as knowledge entries
        created_insights = []

        for insight in insights:
            # Generate embedding for the insight
            embedding = None
            try:
                embedding_text = f"{insight['title']}\n\n{insight['context']}"
                embedding = generate_embedding(embedding_text)
            except Exception as embed_err:
                print(f"Warning: Embedding generation failed for insight: {embed_err}", file=sys.stderr)

            # Insert into claude.knowledge
            insert_sql = """
                INSERT INTO claude.knowledge (
                    knowledge_id, title, description, knowledge_type,
                    knowledge_category, source, confidence_level,
                    applies_to_projects, embedding, created_at
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                RETURNING knowledge_id::text
            """

            cur.execute(insert_sql, (
                insight['title'],
                insight['context'],
                insight['type'],
                project_name,
                f"conversation:{session_id}",
                70,  # auto-extracted, lower confidence
                [project_name],
                embedding,
            ))

            result = cur.fetchone()
            knowledge_id = result['knowledge_id']

            created_insights.append({
                'knowledge_id': knowledge_id,
                'title': insight['title'],
                'type': insight['type'],
                'turn_index': insight['turn_index'],
            })

        conn.commit()

        return {
            "success": True,
            "insights_count": len(created_insights),
            "insight_summaries": created_insights,
        }

    except Exception as e:
        if conn:
            conn.rollback()
        return {
            "success": False,
            "error": f"Failed to extract insights: {str(e)}",
        }
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def search_conversations(
    query: str,
    project: str = "",
    date_range_days: int | None = None,
    limit: int = 10,
) -> dict:
    """Search across stored conversations by keyword.

    Full-text search across conversation turns (JSONB). Returns matching
    turns with surrounding context (previous and next turn).

    Use when: Finding what was discussed in past sessions. Uses ILIKE keyword
    matching (not semantic search). For semantic search, use recall_knowledge.
    Returns: {success, query, match_count, matches: [{conversation_id, session_id,
              project, summary, matching_turn: {turn_index, role, content},
              prev_turn, next_turn}]}.

    Args:
        query: Search query (keywords to find in conversation turns).
        project: Filter by project name (optional).
        date_range_days: Only search conversations from last N days (optional).
        limit: Maximum number of matching turns to return (default: 10).
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Build SQL query to search through JSONB turns
        sql = """
            SELECT
                c.conversation_id::text,
                c.session_id::text,
                c.project_name,
                c.summary,
                c.extracted_at as created_at,
                c.turn_count,
                turn_data.idx as turn_index,
                turn_data.turn->>'role' as role,
                turn_data.turn->>'content' as content,
                c.turns
            FROM claude.conversations c,
                LATERAL jsonb_array_elements(c.turns) WITH ORDINALITY AS turn_data(turn, idx)
            WHERE turn_data.turn->>'content' ILIKE %s
        """

        params = [f"%{query}%"]

        # Add project filter
        if project:
            sql += " AND c.project_name = %s"
            params.append(project)

        # Add date range filter
        if date_range_days is not None:
            sql += " AND c.extracted_at > NOW() - INTERVAL %s"
            params.append(f"{date_range_days} days")

        # Order and limit
        sql += " ORDER BY c.extracted_at DESC LIMIT %s"
        params.append(limit)

        cur.execute(sql, params)
        results = cur.fetchall()

        if not results:
            return {
                "success": True,
                "query": query,
                "match_count": 0,
                "matches": [],
            }

        # Format results with surrounding context
        matches = []
        for row in results:
            turns = row['turns']
            turn_index = row['turn_index']

            # Get previous and next turns for context
            prev_turn = None
            next_turn = None

            if isinstance(turns, list):
                # JSONB array is 0-indexed, WITH ORDINALITY is 1-indexed
                actual_index = turn_index - 1

                if actual_index > 0 and actual_index - 1 < len(turns):
                    prev_turn_data = turns[actual_index - 1]
                    if isinstance(prev_turn_data, dict):
                        prev_turn = {
                            'role': prev_turn_data.get('role', ''),
                            'content': prev_turn_data.get('content', '')[:300],
                        }

                if actual_index < len(turns) - 1:
                    next_turn_data = turns[actual_index + 1]
                    if isinstance(next_turn_data, dict):
                        next_turn = {
                            'role': next_turn_data.get('role', ''),
                            'content': next_turn_data.get('content', '')[:300],
                        }

            matches.append({
                'conversation_id': row['conversation_id'],
                'session_id': row['session_id'],
                'project': row['project_name'],
                'summary': row['summary'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'turn_count': row['turn_count'],
                'matching_turn': {
                    'turn_index': turn_index,
                    'role': row['role'],
                    'content': row['content'],
                },
                'prev_turn': prev_turn,
                'next_turn': next_turn,
            })

        return {
            "success": True,
            "query": query,
            "match_count": len(matches),
            "matches": matches,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to search conversations: {str(e)}",
        }
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def update_claude_md(
    project: str,
    section: str,
    content: str,
    mode: Literal["replace", "append"] = "replace",
) -> dict:
    """Update a section in CLAUDE.md file.

    Finds CLAUDE.md in the project workspace, parses it by ## headers,
    and updates the specified section. Also updates the profiles table and
    logs to audit_log.

    Use when: Modifying a specific section of a project's CLAUDE.md (e.g.,
    updating "Recent Changes" or "Architecture Overview"). For full rewrite
    from DB, use deploy_claude_md instead.
    Returns: {success, section_name, lines_changed, file_path, mode,
              profile_updated}.

    Args:
        project: Project name.
        section: Section header name (without ##, e.g., "Problem Statement").
        content: Content to write to the section.
        mode: 'replace' to replace section content, 'append' to add to end of section.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get project_path from workspaces
        cur.execute("""
            SELECT project_path FROM claude.workspaces WHERE project_name = %s
        """, (project,))
        row = cur.fetchone()

        if not row:
            return {"success": False, "error": f"Project '{project}' not found in workspaces"}

        project_path = row['project_path']
        claude_md_path = Path(project_path) / "CLAUDE.md"

        if not claude_md_path.exists():
            return {"success": False, "error": f"CLAUDE.md not found at {claude_md_path}"}

        # Read and parse CLAUDE.md
        with open(claude_md_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find sections by ## headers
        sections = {}
        current_section = None
        current_lines = []

        for i, line in enumerate(lines):
            if line.startswith('## '):
                # Save previous section
                if current_section:
                    sections[current_section] = {
                        'start_idx': sections[current_section]['start_idx'],
                        'end_idx': i,
                        'lines': current_lines
                    }
                # Start new section
                current_section = line[3:].strip()
                sections[current_section] = {'start_idx': i, 'end_idx': None}
                current_lines = []
            elif current_section:
                current_lines.append(line)

        # Save last section
        if current_section:
            sections[current_section] = {
                'start_idx': sections[current_section]['start_idx'],
                'end_idx': len(lines),
                'lines': current_lines
            }

        # Update the target section
        target_section = section
        if target_section not in sections:
            if mode == 'replace':
                return {"success": False, "error": f"Section '{section}' not found. Available: {', '.join(sections.keys())}"}
            else:
                # Append mode: create new section at end
                new_section_lines = [f"\n## {section}\n\n", content, "\n\n"]
                lines.extend(new_section_lines)
                lines_changed = len(new_section_lines)
        else:
            # Section exists
            sect_info = sections[target_section]
            start_idx = sect_info['start_idx']
            end_idx = sect_info['end_idx']

            if mode == 'replace':
                # Replace: keep header, replace content until next header
                new_section_content = [f"## {target_section}\n\n", content, "\n\n"]
                lines = lines[:start_idx] + new_section_content + lines[end_idx:]
                lines_changed = len(new_section_content) - (end_idx - start_idx)
            else:
                # Append: add content before next section
                append_lines = [content, "\n\n"]
                lines = lines[:end_idx] + append_lines + lines[end_idx:]
                lines_changed = len(append_lines)

        # Build the new full content for DB sync
        new_full_content = ''.join(lines)

        # Update profiles table: sync full CLAUDE.md content to config->behavior
        cur.execute("""
            UPDATE claude.profiles
            SET config = jsonb_set(
                COALESCE(config, '{}'::jsonb),
                '{behavior}',
                to_jsonb(%s::text)
            ),
            updated_at = NOW()
            WHERE name = %s
            RETURNING profile_id::text
        """, (new_full_content, project))
        profile_updated = cur.fetchone() is not None

        # Log to audit_log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, entity_code, to_status, changed_by, change_source, metadata)
            VALUES (
                'profiles',
                (SELECT profile_id FROM claude.profiles WHERE name = %s),
                %s,
                'updated',
                %s,
                'update_claude_md',
                %s::jsonb
            )
        """, (
            project,
            f"CLAUDE.md:{section}",
            os.environ.get('CLAUDE_SESSION_ID'),
            json.dumps({"section": section, "mode": mode, "lines_changed": lines_changed})
        ))

        conn.commit()

        # Write file AFTER successful DB commit (file can be re-generated if needed)
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return {
            "success": True,
            "section_name": section,
            "lines_changed": lines_changed,
            "file_path": str(claude_md_path),
            "mode": mode,
            "profile_updated": profile_updated,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to update CLAUDE.md: {str(e)}"}
    finally:
        conn.close()


@mcp.tool()
def deploy_claude_md(
    project: str,
) -> dict:
    """Deploy CLAUDE.md from database to file. One-way: DB is source of truth.

    Reads profiles.config->behavior from the database and writes it to the
    project's CLAUDE.md file. Use update_claude_md() for section-level edits.

    Use when: Regenerating CLAUDE.md from the database after DB-side changes.
    This is a full overwrite - file content is replaced entirely from DB.
    Returns: {success, diff_summary, file_path}.

    Args:
        project: Project name.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get project_path
        cur.execute("""
            SELECT w.project_path, w.project_id::text
            FROM claude.workspaces w
            WHERE w.project_name = %s
        """, (project,))
        row = cur.fetchone()

        if not row:
            return {"success": False, "error": f"Project '{project}' not found"}

        project_path = row['project_path']
        project_id = row['project_id']
        claude_md_path = Path(project_path) / "CLAUDE.md"

        # Read from profiles.config->behavior
        cur.execute("""
            SELECT config->'behavior' as behavior_text
            FROM claude.profiles
            WHERE name = %s
        """, (project,))
        profile_row = cur.fetchone()

        if not profile_row or not profile_row['behavior_text']:
            return {"success": False, "error": f"No profile behavior text found for project '{project}'"}

        behavior_text = profile_row['behavior_text']
        if isinstance(behavior_text, str):
            new_content = behavior_text
        else:
            new_content = json.dumps(behavior_text, indent=2)

        # Read existing file to compute diff
        old_content = ""
        if claude_md_path.exists():
            with open(claude_md_path, 'r', encoding='utf-8') as f:
                old_content = f.read()

        # Simple diff summary
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        diff_summary = f"Lines: {len(old_lines)} → {len(new_lines)} (Δ {len(new_lines) - len(old_lines)})"

        # Log to audit_log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, to_status, changed_by, change_source, metadata)
            VALUES (
                'profiles',
                (SELECT profile_id FROM claude.profiles WHERE name = %s),
                'deployed',
                %s,
                'deploy_claude_md',
                %s::jsonb
            )
        """, (
            project,
            os.environ.get('CLAUDE_SESSION_ID'),
            json.dumps({"diff_summary": diff_summary})
        ))

        conn.commit()

        # Write file AFTER successful DB commit
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return {
            "success": True,
            "diff_summary": diff_summary,
            "file_path": str(claude_md_path),
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to deploy CLAUDE.md: {str(e)}"}
    finally:
        conn.close()


@mcp.tool()
def deploy_project(
    project: str,
    components: list[str] | None = None,
) -> dict:
    """Deploy project components from database to filesystem.

    Reads component definitions from the database and writes them to the
    appropriate locations in the project directory. Self-healing config system.

    Use when: Regenerating project config files from DB (e.g., after DB changes
    or to fix corrupted files). Deploys any combination of: settings, rules,
    skills, instructions, claude_md. Omit components to deploy all.
    Returns: {success, project, deployed_components: [], changes_summary: []}.

    Args:
        project: Project name.
        components: List of components to deploy. Valid: 'settings', 'rules', 'skills',
                   'instructions', 'claude_md'. If None, deploys all.
    """
    valid_components = ['settings', 'rules', 'skills', 'instructions', 'claude_md']
    components = components or valid_components

    # Validate components
    invalid = [c for c in components if c not in valid_components]
    if invalid:
        return {"success": False, "error": f"Invalid components: {invalid}. Valid: {valid_components}"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get project info
        cur.execute("""
            SELECT w.project_path, w.project_id::text, w.project_type, w.startup_config
            FROM claude.workspaces w
            WHERE w.project_name = %s
        """, (project,))
        row = cur.fetchone()

        if not row:
            return {"success": False, "error": f"Project '{project}' not found"}

        project_path = Path(row['project_path'])
        project_id = row['project_id']
        project_type = row['project_type']
        startup_config = row['startup_config'] or {}

        deployed = []
        changes_summary = []

        # Component: settings
        if 'settings' in components:
            # Read config_templates + merge with workspace startup_config
            cur.execute("""
                SELECT template_config FROM claude.config_templates
                WHERE template_id = 1  -- hooks-base template
            """)
            template_row = cur.fetchone()

            if template_row:
                base_config = template_row['template_config'] or {}
                # Merge with startup_config (workspace overrides template)
                merged_config = {**base_config, **startup_config}

                settings_path = project_path / ".claude" / "settings.local.json"
                settings_path.parent.mkdir(parents=True, exist_ok=True)

                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(merged_config, f, indent=2)

                deployed.append('settings')
                changes_summary.append(f"settings: {len(merged_config)} keys → {settings_path}")

        # Component: rules
        if 'rules' in components:
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'claude' AND table_name = 'rules'
                )
            """)
            if cur.fetchone()['exists']:
                cur.execute("""
                    SELECT rule_name, rule_content
                    FROM claude.rules
                    WHERE project_id = %s::uuid OR project_id IS NULL
                """, (project_id,))
                rules = cur.fetchall()

                if rules:
                    rules_dir = project_path / ".claude" / "rules"
                    rules_dir.mkdir(parents=True, exist_ok=True)

                    for rule in rules:
                        rule_file = rules_dir / f"{rule['rule_name']}.md"
                        with open(rule_file, 'w', encoding='utf-8') as f:
                            f.write(rule['rule_content'])

                    deployed.append('rules')
                    changes_summary.append(f"rules: {len(rules)} files → {rules_dir}")
                else:
                    changes_summary.append("rules: No rules found for this project")
            else:
                changes_summary.append("rules: Table 'claude.rules' does not exist")

        # Component: skills
        if 'skills' in components:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'claude' AND table_name = 'skill_content'
                )
            """)
            if cur.fetchone()['exists']:
                cur.execute("""
                    SELECT skill_name, content
                    FROM claude.skill_content
                    WHERE project_id = %s::uuid OR project_id IS NULL
                """, (project_id,))
                skills = cur.fetchall()

                if skills:
                    skills_dir = project_path / ".claude" / "skills"
                    skills_dir.mkdir(parents=True, exist_ok=True)

                    for skill in skills:
                        skill_dir = skills_dir / skill['skill_name']
                        skill_dir.mkdir(parents=True, exist_ok=True)
                        skill_file = skill_dir / "SKILL.md"
                        with open(skill_file, 'w', encoding='utf-8') as f:
                            f.write(skill['content'])

                    deployed.append('skills')
                    changes_summary.append(f"skills: {len(skills)} skills → {skills_dir}")
                else:
                    changes_summary.append("skills: No skills found for this project")
            else:
                changes_summary.append("skills: Table 'claude.skill_content' does not exist")

        # Component: instructions
        if 'instructions' in components:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'claude' AND table_name = 'instructions'
                )
            """)
            if cur.fetchone()['exists']:
                cur.execute("""
                    SELECT instruction_name, content
                    FROM claude.instructions
                    WHERE project_id = %s::uuid OR project_id IS NULL
                """, (project_id,))
                instructions = cur.fetchall()

                if instructions:
                    instructions_dir = project_path / ".claude" / "instructions"
                    instructions_dir.mkdir(parents=True, exist_ok=True)

                    for instr in instructions:
                        instr_file = instructions_dir / f"{instr['instruction_name']}.instructions.md"
                        with open(instr_file, 'w', encoding='utf-8') as f:
                            f.write(instr['content'])

                    deployed.append('instructions')
                    changes_summary.append(f"instructions: {len(instructions)} files → {instructions_dir}")
                else:
                    changes_summary.append("instructions: No instructions found for this project")
            else:
                changes_summary.append("instructions: Table 'claude.instructions' does not exist")

        # Component: claude_md
        if 'claude_md' in components:
            cur.execute("""
                SELECT config->'behavior' as behavior_text
                FROM claude.profiles
                WHERE project_id = %s::uuid
            """, (project_id,))
            profile_row = cur.fetchone()

            if profile_row and profile_row['behavior_text']:
                behavior_text = profile_row['behavior_text']
                if not isinstance(behavior_text, str):
                    behavior_text = json.dumps(behavior_text, indent=2)

                claude_md_path = project_path / "CLAUDE.md"
                with open(claude_md_path, 'w', encoding='utf-8') as f:
                    f.write(behavior_text)

                deployed.append('claude_md')
                changes_summary.append(f"claude_md: {len(behavior_text)} chars → {claude_md_path}")
            else:
                changes_summary.append("claude_md: No profile found for this project")

        # Log to audit_log
        for component in deployed:
            cur.execute("""
                INSERT INTO claude.audit_log
                (entity_type, entity_id, to_status, changed_by, change_source, metadata)
                VALUES (
                    'project_deployment',
                    %s::uuid,
                    'deployed',
                    %s,
                    'deploy_project',
                    %s::jsonb
                )
            """, (
                project_id,
                os.environ.get('CLAUDE_SESSION_ID'),
                json.dumps({"component": component})
            ))

        conn.commit()

        return {
            "success": True,
            "project": project,
            "deployed_components": deployed,
            "changes_summary": changes_summary,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to deploy project: {str(e)}"}
    finally:
        conn.close()


@mcp.tool()
def regenerate_settings(
    project: str,
) -> dict:
    """Regenerate .claude/settings.local.json from database (config_templates + workspace overrides).

    Reads the base template (template_id=1) and merges with project-specific
    overrides from workspaces.startup_config, then writes the merged result.

    Use when: Settings file is corrupted, missing, or out of sync with DB.
    Also call after updating config_templates or workspaces.startup_config.
    Returns: {success, project, file_path, changes: ['+key', '-key', '~key'],
              total_keys}.

    Args:
        project: Project name.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get workspace info
        cur.execute("""
            SELECT w.project_path, w.startup_config, w.project_type
            FROM claude.workspaces w
            WHERE w.project_name = %s
        """, (project,))
        row = cur.fetchone()

        if not row:
            return {"success": False, "error": f"Project '{project}' not found in workspaces"}

        project_path = Path(row['project_path'])
        startup_config = row['startup_config'] or {}
        project_type = row['project_type']

        # Get base template (template_id=1 = hooks-base)
        cur.execute("""
            SELECT template_config FROM claude.config_templates
            WHERE template_id = 1
        """)
        template_row = cur.fetchone()

        if not template_row:
            return {"success": False, "error": "Base config template (template_id=1) not found"}

        base_config = template_row['template_config'] or {}

        # Merge: workspace overrides base
        merged_config = {**base_config, **startup_config}

        # Write to .claude/settings.local.json
        settings_path = project_path / ".claude" / "settings.local.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Read old settings to compute diff
        old_config = {}
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                old_config = json.load(f)

        # Write new settings
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(merged_config, f, indent=2)

        # Compute changes
        changes = []
        for key in set(list(old_config.keys()) + list(merged_config.keys())):
            if key not in old_config:
                changes.append(f"+ {key}")
            elif key not in merged_config:
                changes.append(f"- {key}")
            elif old_config[key] != merged_config[key]:
                changes.append(f"~ {key}")

        conn.commit()

        return {
            "success": True,
            "project": project,
            "file_path": str(settings_path),
            "changes": changes,
            "total_keys": len(merged_config),
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to regenerate settings: {str(e)}"}
    finally:
        conn.close()


# ============================================================================
# Import existing tools from server.py for backward compatibility
# ============================================================================

# Import the old server module to get access to all existing tool implementations
_old_server_dir = os.path.dirname(os.path.abspath(__file__))
if _old_server_dir not in sys.path:
    sys.path.insert(0, _old_server_dir)

# We import the tool implementations (not the MCP app) from the old server
from server import (  # noqa: E402
    tool_get_project_context,
    tool_get_session_resume,
    tool_get_incomplete_todos,
    tool_restore_session_todos,
    tool_create_feedback,
    tool_create_feature,
    tool_add_build_task,
    tool_get_ready_tasks,
    tool_update_work_status,
    tool_find_skill,
    tool_todos_to_build_tasks,
    tool_store_knowledge,
    tool_recall_knowledge,
    tool_link_knowledge,
    tool_get_related_knowledge,
    tool_mark_knowledge_applied,
    tool_store_session_fact,
    tool_recall_session_fact,
    tool_list_session_facts,
    tool_recall_previous_session_facts,
    tool_store_session_notes,
    tool_get_session_notes,
    get_valid_values,
    validate_value,
    generate_embedding,
    generate_query_embedding,
)


# ============================================================================
# Legacy Tool Wrappers (backward compatibility)
# ============================================================================
# These wrap the old async tool implementations as sync FastMCP tools.
# They maintain the exact same interface so existing callers don't break.

import asyncio

def _run_async(coro):
    """Run an async function synchronously."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're already in an async context - create a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


@mcp.tool()
def get_project_context(
    project_path: str,
) -> dict:
    """DEPRECATED: Use start_session() instead.

    Loads project context. start_session() returns everything this does plus todos,
    work items, and messages in a single optimized call.

    Args:
        project_path: Project path or name (e.g., 'claude-family' or 'C:/Projects/claude-family').
    """
    return _run_async(tool_get_project_context(project_path))


@mcp.tool()
def get_session_resume(
    project: str,
) -> dict:
    """DEPRECATED: Use start_session() instead.

    Gets session resume context. start_session() returns everything this does plus
    work items in a single optimized call.

    Args:
        project: Project name (defaults to current directory basename).
    """
    return _run_async(tool_get_session_resume(project))


@mcp.tool()
def get_incomplete_todos(
    project: str,
) -> dict:
    """Get all incomplete todos for a project across all sessions.

    Use when: Reviewing outstanding work items across sessions. For current
    session only, use list_session_facts or get_work_context instead.
    Returns: {todos: [{todo_id, content, status, priority, session_id, created_at}]}.

    Args:
        project: Project name or path.
    """
    return _run_async(tool_get_incomplete_todos(project))


@mcp.tool()
def restore_session_todos(
    session_id: str,
) -> dict:
    """Get todos from a specific past session, formatted for TodoWrite.

    Use when: Restoring work items from a crashed or resumed session. Used
    internally by /session-resume. Returns data shaped for TodoWrite.
    Returns: {todos: [{content, status, priority}], session_id}.

    Args:
        session_id: Session UUID to restore todos from.
    """
    return _run_async(tool_restore_session_todos(session_id))


@mcp.tool()
def create_feedback(
    project: str,
    feedback_type: Literal["bug", "design", "idea", "question", "change", "improvement"],
    description: str,
    title: str = "",
    priority: Literal["high", "medium", "low"] = "medium",
) -> dict:
    """Report a bug, propose a change, or capture an idea.

    Use when: You discover a bug, have an improvement idea, or want to propose
    a change. Auto-validates against column_registry. Status starts at 'new'.
    Returns: {success, feedback_id, short_code (e.g. 'FB42'), title, status: 'new'}.

    Args:
        project: Project name or path.
        feedback_type: bug=something broken, idea=enhancement, change=behavior modification,
                       question=needs clarification, design=visual/UX issue, improvement=general improvement.
        description: Detailed description of the feedback.
        title: Short title (optional, defaults to first 50 chars of description).
        priority: high, medium (default), or low.
    """
    return _run_async(tool_create_feedback(project, feedback_type, description, title or None, priority))


@mcp.tool()
def create_feature(
    project: str,
    feature_name: str,
    description: str,
    feature_type: Literal["feature", "enhancement", "refactor", "infrastructure", "documentation"] = "feature",
    priority: Literal[1, 2, 3, 4, 5] = 3,
    plan_data: dict | None = None,
) -> dict:
    """Create a feature for tracking implementation.

    Use when: Starting a new piece of work that needs build tasks. Features
    group related build_tasks. Status starts at 'draft' - advance to 'planned'
    then 'in_progress'. Attach plan_data for structured specs.
    Returns: {success, feature_id, short_code (e.g. 'F42'), feature_name,
              status: 'draft'}.

    Args:
        project: Project name or path.
        feature_name: Feature name.
        description: Feature description.
        feature_type: feature, enhancement, refactor, infrastructure, or documentation.
        priority: 1=critical, 2=high, 3=medium (default), 4=low, 5=minimal.
        plan_data: Optional structured plan data (requirements, risks, etc.).
    """
    return _run_async(tool_create_feature(project, feature_name, description, feature_type, priority, plan_data))


@mcp.tool()
def add_build_task(
    feature_id: str,
    task_name: str,
    task_description: str = "",
    task_type: Literal["implementation", "testing", "documentation", "deployment", "investigation"] = "implementation",
    files_affected: list[str] | None = None,
    blocked_by_task_id: str = "",
) -> dict:
    """Add a build task to a feature. Tasks are ordered by step_order.

    Use when: Adding a task to a feature without strict validation. For
    enforced quality (>= 100 char description, verification, files), use
    create_linked_task instead. Status starts at 'todo'.
    Returns: {success, task_id, short_code (e.g. 'BT42'), task_name,
              feature_id, step_order}.

    Args:
        feature_id: Feature ID or short_code (e.g., 'F12').
        task_name: Task name.
        task_description: Detailed description (optional).
        task_type: implementation, testing, documentation, deployment, or investigation.
        files_affected: List of files this task will modify.
        blocked_by_task_id: Task ID that blocks this one (optional).
    """
    return _run_async(tool_add_build_task(
        feature_id, task_name,
        task_description or None,
        task_type,
        files_affected,
        blocked_by_task_id or None,
    ))


@mcp.tool()
def get_ready_tasks(
    project: str,
) -> dict:
    """Get build tasks that are ready to work on (not blocked).

    Use when: Looking for the next task to start. Returns tasks with status
    'todo' whose blockers (if any) are completed.
    Returns: {tasks: [{task_code, task_name, task_type, feature_code,
              feature_name, priority, step_order}]}.

    Args:
        project: Project name or path.
    """
    return _run_async(tool_get_ready_tasks(project))


@mcp.tool()
def update_work_status(
    item_type: Literal["feedback", "feature", "build_task"],
    item_id: str,
    new_status: str,
) -> dict:
    """Update status of a feedback, feature, or build_task.

    Use when: Changing status (legacy interface). Routes through WorkflowEngine.
    Prefer advance_status (same behavior, consistent naming).
    Use short codes: FB12, F5, BT23.
    Returns: Same as advance_status - {success, entity_type, entity_code,
              from_status, to_status}.

    Args:
        item_type: Type of item: feedback, feature, or build_task.
        item_id: Item ID or short_code (e.g., 'FB12', 'F5', 'BT23').
        new_status: New status value. Invalid transitions are rejected.
    """
    # Map legacy item_type names to entity_type
    entity_type_map = {
        'feedback': 'feedback',
        'feature': 'features',
        'build_task': 'build_tasks',
    }
    entity_type = entity_type_map.get(item_type, item_type)

    return advance_status(
        item_type=entity_type,
        item_id=item_id,
        new_status=new_status,
    )


@mcp.tool()
def find_skill(
    task_description: str,
    limit: int = 5,
) -> dict:
    """Search skill_content by task description to find relevant skills/guidelines.

    Use when: Looking for a skill or guideline that applies to your current task.
    Searches skill_content table by keyword similarity.
    Returns: {skills: [{skill_name, content, similarity}]}.

    Args:
        task_description: Description of what you're trying to do.
        limit: Max results (default: 5).
    """
    return _run_async(tool_find_skill(task_description, limit))


@mcp.tool()
def todos_to_build_tasks(
    feature_id: str,
    project: str,
    include_completed: bool = False,
) -> dict:
    """Convert session todos to persistent build_tasks linked to a feature.

    Use when: Promoting ad-hoc session todos into tracked build_tasks on a
    feature. Archives the converted todos after creating build_tasks.
    Returns: {success, converted_count, feature_code, archived_todos}.

    Args:
        feature_id: Feature ID or short_code to link tasks to.
        project: Project name or path.
        include_completed: Include completed todos (default: false).
    """
    return _run_async(tool_todos_to_build_tasks(feature_id, project, include_completed))


@mcp.tool()
def store_knowledge(
    title: str,
    description: str,
    knowledge_type: Literal["learned", "pattern", "gotcha", "preference", "fact", "procedure"] = "learned",
    knowledge_category: str = "",
    code_example: str = "",
    applies_to_projects: list[str] | None = None,
    applies_to_platforms: list[str] | None = None,
    confidence_level: int = 80,
    source: str = "",
) -> dict:
    """Store new knowledge with automatic embedding for semantic search.

    Use when: Capturing a reusable insight, pattern, or fact. Embedding is
    auto-generated via Voyage AI for later recall via recall_knowledge.
    Returns: {success, knowledge_id, title, has_embedding}.

    Args:
        title: Short descriptive title.
        description: Detailed knowledge content.
        knowledge_type: learned, pattern, gotcha, preference, fact, or procedure.
        knowledge_category: Category (e.g., 'database', 'react', 'testing').
        code_example: Optional code example.
        applies_to_projects: Projects this knowledge applies to (null = all).
        applies_to_platforms: Platforms (windows, mac, linux).
        confidence_level: Confidence 0-100 (default: 80).
        source: Source of knowledge (e.g., 'session', 'documentation').
    """
    return _run_async(tool_store_knowledge(
        title, description, knowledge_type,
        knowledge_category or None,
        code_example or None,
        applies_to_projects,
        applies_to_platforms,
        confidence_level,
        source or None,
    ))


@mcp.tool()
def recall_knowledge(
    query: str,
    limit: int = 5,
    knowledge_type: str = "",
    project: str = "",
    min_similarity: float = 0.5,
    domain: str = "",
    source_type: str = "",
    tags: list[str] | None = None,
    date_range_days: int | None = None,
) -> dict:
    """Semantic search over knowledge entries with structured filters.

    Use when: Looking for previously stored knowledge (learnings, patterns,
    gotchas). Uses Voyage AI embeddings for semantic similarity matching.
    Returns: {results: [{knowledge_id, title, description, knowledge_type,
              similarity, confidence_level, code_example}]}.

    Args:
        query: Natural language query.
        limit: Max results (default: 5).
        knowledge_type: Filter by type (optional).
        project: Filter by project (optional).
        min_similarity: Minimum similarity 0-1 (default: 0.5).
        domain: Filter by knowledge domain (e.g., 'database', 'winforms', 'hooks', 'mcp') (optional).
        source_type: Filter by source (e.g., 'session', 'vault', 'manual', 'conversation') (optional).
        tags: Filter by tags array overlap (optional).
        date_range_days: Filter to knowledge created within N days (optional).
    """
    return _run_async(tool_recall_knowledge(
        query, limit,
        knowledge_type or None,
        project or None,
        min_similarity,
        domain or None,
        source_type or None,
        tags,
        date_range_days,
    ))


@mcp.tool()
def link_knowledge(
    from_knowledge_id: str,
    to_knowledge_id: str,
    relation_type: Literal["extends", "contradicts", "supports", "supersedes", "depends_on", "relates_to", "part_of", "caused_by"],
    strength: float = 1.0,
    notes: str = "",
) -> dict:
    """Create a typed relation between knowledge entries.

    Use when: Connecting related knowledge entries (e.g., a pattern that
    supersedes an older one, or a gotcha that contradicts a fact).
    Returns: {success, relation_id, from_id, to_id, relation_type}.

    Args:
        from_knowledge_id: Source knowledge UUID.
        to_knowledge_id: Target knowledge UUID.
        relation_type: Type of relation.
        strength: Relation strength 0-1 (default: 1.0).
        notes: Optional notes about the relation.
    """
    return _run_async(tool_link_knowledge(
        from_knowledge_id, to_knowledge_id, relation_type,
        strength, notes or None,
    ))


@mcp.tool()
def get_related_knowledge(
    knowledge_id: str,
    relation_types: list[str] | None = None,
    include_reverse: bool = True,
) -> dict:
    """Get knowledge entries related to a given entry via knowledge_relations.

    Use when: Exploring the knowledge graph from a specific entry. Finds
    both outgoing and incoming relations.
    Returns: {relations: [{relation_id, relation_type, direction,
              related: {knowledge_id, title, description, type}}]}.

    Args:
        knowledge_id: Knowledge UUID to find relations for.
        relation_types: Filter by relation types (optional).
        include_reverse: Include incoming relations (default: true).
    """
    return _run_async(tool_get_related_knowledge(knowledge_id, relation_types, include_reverse))


@mcp.tool()
def mark_knowledge_applied(
    knowledge_id: str,
    success: bool = True,
) -> dict:
    """Track when knowledge is applied (success or failure). Updates confidence level.

    Use when: After using a knowledge entry, report whether it was helpful.
    Success increases confidence, failure decreases it. Helps surface reliable knowledge.
    Returns: {success, knowledge_id, new_confidence_level}.

    Args:
        knowledge_id: Knowledge UUID that was applied.
        success: Whether application was successful (default: true).
    """
    return _run_async(tool_mark_knowledge_applied(knowledge_id, success))


@mcp.tool()
def store_session_fact(
    fact_key: str,
    fact_value: str,
    fact_type: Literal["credential", "config", "endpoint", "decision", "note", "data", "reference"] = "note",
    is_sensitive: bool = False,
    project_name: str = "",
) -> dict:
    """Store a fact in your session notepad (survives context compaction).

    Use when: You learn something important mid-session that must survive
    compaction (credentials, endpoints, decisions, key findings). Facts persist
    in DB and can be recalled via recall_session_fact or list_session_facts.
    Returns: {success, fact_key, fact_type, session_id}.

    Args:
        fact_key: Unique key for the fact (e.g., 'api_endpoint', 'nimbus_creds').
        fact_value: The fact value to store.
        fact_type: credential, config, endpoint, decision, note (default), data, or reference.
        is_sensitive: If true, value won't appear in logs (default: false).
        project_name: Project name (default: current directory).
    """
    return _run_async(tool_store_session_fact(
        fact_key, fact_value, fact_type, is_sensitive,
        project_name or None,
    ))


@mcp.tool()
def recall_session_fact(
    fact_key: str,
    project_name: str = "",
) -> dict:
    """Recall a specific fact by key. Looks in current session first, falls back to recent.

    Use when: Retrieving a previously stored fact (e.g., after context
    compaction or to check a stored credential/endpoint).
    Returns: {success, fact_key, fact_value, fact_type, session_id, stored_at}.

    Args:
        fact_key: The key of the fact to recall.
        project_name: Project name (default: current directory).
    """
    return _run_async(tool_recall_session_fact(fact_key, project_name or None))


@mcp.tool()
def list_session_facts(
    project_name: str = "",
    include_sensitive: bool = False,
) -> dict:
    """List all facts stored in the current session.

    Use when: Reviewing your session notepad to see what's been stored.
    Sensitive values are hidden by default unless include_sensitive=True.
    Returns: {success, facts: [{fact_key, fact_value, fact_type, stored_at}],
              count}.

    Args:
        project_name: Project name (default: current directory).
        include_sensitive: Include sensitive fact values (default: false).
    """
    return _run_async(tool_list_session_facts(project_name or None, include_sensitive))


@mcp.tool()
def recall_previous_session_facts(
    project_name: str = "",
    n_sessions: int = 3,
    fact_types: list[str] | None = None,
) -> dict:
    """Recall facts from previous sessions (after context compaction).

    Use when: Resuming work in a new session and need facts from prior sessions
    (e.g., credentials, endpoints, decisions). Scans the last N sessions.
    Returns: {success, facts: [{fact_key, fact_value, fact_type, session_id,
              stored_at}], sessions_checked}.

    Args:
        project_name: Project name (default: current directory).
        n_sessions: Number of previous sessions to check (default: 3).
        fact_types: Filter by fact types (optional).
    """
    return _run_async(tool_recall_previous_session_facts(project_name or None, n_sessions, fact_types))


@mcp.tool()
def store_session_notes(
    content: str,
    section: Literal["general", "decisions", "progress", "blockers", "findings"] = "general",
    append: bool = True,
) -> dict:
    """Store structured notes during a session (persists to markdown file).

    Use when: Recording progress, decisions, or findings during a session.
    Notes persist to a markdown file and survive context compaction.
    Returns: {success, section, file_path, action: 'appended' or 'replaced'}.

    Args:
        content: Note content to store.
        section: Section header: general, decisions, progress, blockers, or findings.
        append: If True, append to section. If False, replace section.
    """
    return _run_async(tool_store_session_notes(content, section, append))


@mcp.tool()
def get_session_notes(
    section: str = "",
) -> dict:
    """Retrieve session notes for the current project.

    Use when: Reviewing progress after context compaction or at end of session.
    Returns: {success, notes: {section_name: content}, file_path}.

    Args:
        section: Section to retrieve (optional). If omitted, returns all notes.
    """
    return _run_async(tool_get_session_notes(section or None))


# ============================================================================
# BPMN Process Registry Tools
# ============================================================================
# Hybrid storage: BPMN files in git (source of truth) + DB registry for
# cross-project search and discovery. See bpmn_sync.bpmn for the process model.

import hashlib
from xml.etree import ElementTree as ET

_BPMN_NS = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}

# Map process_id prefixes/paths to level and category
_LEVEL_CATEGORY_MAP = {
    "L0_": ("L0", "architecture"),
    "L1_": ("L1", "architecture"),
    "processes/architecture/": ("L0", "architecture"),
    "processes/lifecycle/": ("L2", "lifecycle"),
    "processes/development/": ("L2", "development"),
    "processes/infrastructure/": ("L2", "infrastructure"),
    "processes/nimbus/": ("L2", "nimbus"),
}


def _infer_level_category(process_id: str, file_path: str) -> tuple[str, str]:
    """Infer level and category from process_id and file path."""
    for prefix, (level, category) in _LEVEL_CATEGORY_MAP.items():
        if process_id.startswith(prefix) or prefix in file_path.replace("\\", "/"):
            return level, category
    return "L2", "unknown"


def _get_current_session_id() -> str | None:
    """Get current session UUID from environment, or None."""
    return os.environ.get('CLAUDE_SESSION_ID')


def _parse_bpmn_file(file_path: str) -> dict | None:
    """Parse a BPMN file and extract process metadata, elements, and flows."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Find the first executable process
        process = root.find(".//bpmn:process[@isExecutable='true']", _BPMN_NS)
        if process is None:
            # Try without isExecutable filter
            process = root.find(".//bpmn:process", _BPMN_NS)
        if process is None:
            return None

        process_id = process.get("id", "")
        process_name = process.get("name", process_id)

        # Extract elements (tasks, events, gateways)
        elements = []
        element_types = [
            "startEvent", "endEvent", "userTask", "scriptTask", "serviceTask",
            "exclusiveGateway", "parallelGateway", "callActivity",
        ]
        for etype in element_types:
            for elem in process.findall(f"bpmn:{etype}", _BPMN_NS):
                elements.append({
                    "id": elem.get("id", ""),
                    "type": etype,
                    "name": elem.get("name", ""),
                })

        # Extract flows
        flows = []
        for flow in process.findall("bpmn:sequenceFlow", _BPMN_NS):
            cond_elem = flow.find("bpmn:conditionExpression", _BPMN_NS)
            flows.append({
                "id": flow.get("id", ""),
                "from": flow.get("sourceRef", ""),
                "to": flow.get("targetRef", ""),
                "condition": cond_elem.text if cond_elem is not None else None,
            })

        # Extract description from first comment in process
        description = ""
        # Look for XML comments inside the process (they become tail/text in ET)
        # Actually, ET strips comments. Use process_name + element summary instead.
        element_names = [e["name"] for e in elements if e["name"]]
        description = f"{process_name}: {', '.join(element_names[:10])}"

        level, category = _infer_level_category(process_id, file_path)

        return {
            "process_id": process_id,
            "process_name": process_name,
            "level": level,
            "category": category,
            "description": description,
            "elements": elements,
            "flows": flows,
        }
    except Exception:
        return None


@mcp.tool()
def sync_bpmn_processes(
    project: str = "",
    processes_dir: str = "",
) -> dict:
    """Sync BPMN files from a project directory into the database registry.

    Discovers .bpmn files, parses them, and upserts into claude.bpmn_processes
    with Voyage AI embeddings for semantic search. Uses file hash for incremental
    sync (unchanged files are skipped).

    Use when: After creating or modifying BPMN process files. Keeps the DB
    registry in sync with the git source of truth.
    Returns: {success, project, synced_count, skipped_count, parse_errors,
              file_count, details: [{process_id, action}]}.

    Args:
        project: Project name (default: current directory).
        processes_dir: Override path to processes directory. If empty, auto-discovers.
    """
    project = project or os.path.basename(os.getcwd())

    # Discover processes directory
    if not processes_dir:
        # Check common locations
        candidates = [
            os.path.join(os.getcwd(), "mcp-servers", "bpmn-engine", "processes"),
            os.path.join(os.getcwd(), "processes"),
        ]
        for cand in candidates:
            if os.path.isdir(cand):
                processes_dir = cand
                break

    if not processes_dir or not os.path.isdir(processes_dir):
        return {"success": True, "project": project, "synced_count": 0,
                "skipped_count": 0, "parse_errors": 0, "file_count": 0,
                "message": "No processes directory found"}

    # Glob for .bpmn files
    bpmn_files = glob.glob(os.path.join(processes_dir, "**", "*.bpmn"), recursive=True)
    if not bpmn_files:
        return {"success": True, "project": project, "synced_count": 0,
                "skipped_count": 0, "parse_errors": 0, "file_count": 0,
                "message": "No .bpmn files found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Load existing hashes for incremental sync
        cur.execute(
            "SELECT process_id, file_hash FROM claude.bpmn_processes WHERE project_name = %s",
            (project,),
        )
        existing_hashes = {row["process_id"]: row["file_hash"] for row in cur.fetchall()}

        synced_count = 0
        skipped_count = 0
        parse_errors = 0
        details = []

        for file_path in bpmn_files:
            # Compute file hash
            with open(file_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            # Parse BPMN
            parsed = _parse_bpmn_file(file_path)
            if parsed is None:
                parse_errors += 1
                details.append({"file": os.path.basename(file_path), "action": "parse_error"})
                continue

            pid = parsed["process_id"]

            # Check if unchanged
            if existing_hashes.get(pid) == file_hash:
                skipped_count += 1
                details.append({"process_id": pid, "action": "skipped"})
                continue

            # Generate embedding
            embed_text = f"{parsed['process_name']} {parsed['description']}"
            embedding = generate_embedding(embed_text)

            # Relative file path for portability
            rel_path = os.path.relpath(file_path, os.getcwd()).replace("\\", "/")

            # Upsert
            cur.execute("""
                INSERT INTO claude.bpmn_processes
                    (process_id, project_name, file_path, process_name, level, category,
                     description, elements, flows, file_hash, embedding,
                     created_by_session, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (process_id) DO UPDATE SET
                    project_name = EXCLUDED.project_name,
                    file_path = EXCLUDED.file_path,
                    process_name = EXCLUDED.process_name,
                    level = EXCLUDED.level,
                    category = EXCLUDED.category,
                    description = EXCLUDED.description,
                    elements = EXCLUDED.elements,
                    flows = EXCLUDED.flows,
                    file_hash = EXCLUDED.file_hash,
                    embedding = EXCLUDED.embedding,
                    created_by_session = COALESCE(claude.bpmn_processes.created_by_session, EXCLUDED.created_by_session),
                    updated_at = NOW()
            """, (
                pid, project, rel_path, parsed["process_name"],
                parsed["level"], parsed["category"], parsed["description"],
                json.dumps(parsed["elements"]), json.dumps(parsed["flows"]),
                file_hash,
                str(embedding) if embedding else None,
                _get_current_session_id(),
            ))

            action = "updated" if pid in existing_hashes else "created"
            synced_count += 1
            details.append({"process_id": pid, "action": action})

        conn.commit()
        cur.close()

        return {
            "success": True,
            "project": project,
            "synced_count": synced_count,
            "skipped_count": skipped_count,
            "parse_errors": parse_errors,
            "file_count": len(bpmn_files),
            "details": details,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Sync failed: {str(e)}"}
    finally:
        conn.close()


@mcp.tool()
def search_bpmn_processes(
    query: str,
    project: str = "",
    level: str = "",
    category: str = "",
    client_domain: str = "",
    limit: int = 10,
) -> dict:
    """Search BPMN processes using semantic similarity or filters.

    Uses Voyage AI embeddings for semantic search across all registered
    BPMN processes. Can filter by project, level (L0/L1/L2), category,
    and client_domain (groups related projects, e.g. 'nimbus' includes
    nimbus-import, nimbus-user-loader, nimbus-mui).

    Use when: Looking for a process that handles a specific workflow,
    understanding how processes relate, or finding processes by keyword.
    Returns: {success, query, result_count, processes: [{process_id,
              process_name, level, category, project_name, file_path,
              description, element_count, similarity}]}.

    Args:
        query: Natural language search query.
        project: Filter by project name (optional).
        level: Filter by level: L0, L1, or L2 (optional).
        category: Filter by category (optional).
        client_domain: Filter by client domain (e.g. 'nimbus', 'ato', 'finance').
            Also includes 'infrastructure' processes which are shared. (optional).
        limit: Maximum results (default: 10).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Generate query embedding
        query_embedding = generate_query_embedding(query)

        # Build JOIN clause for client_domain filtering
        join_sql = ""
        if client_domain:
            join_sql = "JOIN claude.projects p ON bp.project_name = p.project_name"

        if query_embedding:
            # Semantic search with optional filters
            where_clauses = []
            params = [str(query_embedding)]

            if project:
                where_clauses.append("bp.project_name = %s")
                params.append(project)
            if level:
                where_clauses.append("bp.level = %s")
                params.append(level)
            if category:
                where_clauses.append("bp.category = %s")
                params.append(category)
            if client_domain:
                # Include the requested domain + infrastructure (shared)
                where_clauses.append("(p.client_domain = %s OR p.client_domain = 'infrastructure')")
                params.append(client_domain)

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            params.append(limit)

            cur.execute(f"""
                SELECT bp.process_id, bp.process_name, bp.level, bp.category,
                       bp.project_name, bp.file_path, bp.description,
                       bp.elements, bp.flows,
                       1 - (bp.embedding <=> %s::vector) AS similarity
                FROM claude.bpmn_processes bp
                {join_sql}
                {where_sql}
                ORDER BY bp.embedding <=> %s::vector
                LIMIT %s
            """, (*params, str(query_embedding), limit))
        else:
            # Fallback: keyword search on process_name + description
            where_clauses = ["(bp.process_name ILIKE %s OR bp.description ILIKE %s)"]
            params = [f"%{query}%", f"%{query}%"]

            if project:
                where_clauses.append("bp.project_name = %s")
                params.append(project)
            if level:
                where_clauses.append("bp.level = %s")
                params.append(level)
            if category:
                where_clauses.append("bp.category = %s")
                params.append(category)
            if client_domain:
                where_clauses.append("(p.client_domain = %s OR p.client_domain = 'infrastructure')")
                params.append(client_domain)

            params.append(limit)

            cur.execute(f"""
                SELECT bp.process_id, bp.process_name, bp.level, bp.category,
                       bp.project_name, bp.file_path, bp.description,
                       bp.elements, bp.flows,
                       0.5 AS similarity
                FROM claude.bpmn_processes bp
                {join_sql}
                WHERE {" AND ".join(where_clauses)}
                ORDER BY bp.process_name
                LIMIT %s
            """, params)

        rows = cur.fetchall()
        cur.close()

        processes = []
        for row in rows:
            elements = row.get("elements") or []
            if isinstance(elements, str):
                elements = json.loads(elements)
            flows = row.get("flows") or []
            if isinstance(flows, str):
                flows = json.loads(flows)

            processes.append({
                "process_id": row["process_id"],
                "process_name": row["process_name"],
                "level": row["level"],
                "category": row["category"],
                "project_name": row["project_name"],
                "file_path": row["file_path"],
                "description": row["description"],
                "element_count": len(elements),
                "flow_count": len(flows),
                "similarity": round(float(row.get("similarity", 0)), 4),
            })

        return {
            "success": True,
            "query": query,
            "result_count": len(processes),
            "processes": processes,
        }

    except Exception as e:
        return {"success": False, "error": f"Search failed: {str(e)}"}
    finally:
        conn.close()


# ============================================================================
# Promote Feedback to Feature
# ============================================================================

@mcp.tool()
def promote_feedback(
    feedback_id: str,
    feature_name: str = "",
    feature_type: str = "feature",
    priority: int = 3,
    plan_data: dict = None,
) -> dict:
    """Promote a feedback item to a tracked feature.

    Follows the feedback_to_feature BPMN process:
    1. Looks up the feedback item
    2. Creates a feature from it (with optional name override)
    3. Advances the feedback to 'triaged' status
    4. Returns the new feature code for further work

    Use when: A feedback item (bug, idea, improvement) needs to become
    a tracked feature with build tasks. This bridges the gap between
    ad-hoc feedback capture and structured feature development.
    Returns: {success, feature_code, feature_id, feedback_code,
              feedback_title, feature_name, from_status, to_status}.

    Args:
        feedback_id: Feedback short code (e.g., 'FB42') or UUID.
        feature_name: Override feature name (defaults to feedback title).
        feature_type: feature, enhancement, refactor, infrastructure, or documentation.
        priority: 1=critical, 2=high, 3=medium, 4=low, 5=minimal.
        plan_data: Optional structured plan data for the feature.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Resolve feedback by short_code or UUID
        if feedback_id.upper().startswith("FB"):
            try:
                code_num = int(feedback_id[2:])
            except ValueError:
                return {"success": False, "error": f"Invalid feedback code: {feedback_id}"}
            cur.execute("""
                SELECT feedback_id::text, title, description, feedback_type, priority, status,
                       project_id::text, short_code
                FROM claude.feedback
                WHERE short_code = %s
            """, (code_num,))
        else:
            cur.execute("""
                SELECT feedback_id::text, title, description, feedback_type, priority, status,
                       project_id::text, short_code
                FROM claude.feedback
                WHERE feedback_id = %s::uuid
            """, (feedback_id,))

        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"Feedback not found: {feedback_id}"}

        fb_id = row['feedback_id']
        fb_title = row['title'] or row['description'][:80]
        fb_desc = row['description']
        fb_status = row['status']
        fb_project_id = row['project_id']
        fb_short_code = row['short_code']
        fb_code = f"FB{fb_short_code}"

        # Determine feature name
        f_name = feature_name or fb_title

        # Validate feature_type
        valid_types = get_valid_values('features', 'feature_type')
        if valid_types and feature_type not in valid_types:
            return {"success": False, "error": f"Invalid feature_type: {feature_type}. Valid: {valid_types}"}

        # Create feature
        plan_json = json.dumps(plan_data) if plan_data else None
        cur.execute("""
            INSERT INTO claude.features
            (project_id, feature_name, description, feature_type, priority, status, plan_data)
            VALUES (%s::uuid, %s, %s, %s, %s, 'draft', %s::jsonb)
            RETURNING feature_id::text, short_code
        """, (
            fb_project_id,
            f_name,
            f"Promoted from {fb_code}: {fb_desc}",
            feature_type,
            priority,
            plan_json,
        ))

        feat_row = cur.fetchone()
        feature_id = feat_row['feature_id']
        feature_code = f"F{feat_row['short_code']}"

        # Advance feedback status to triaged (if currently new)
        new_fb_status = fb_status
        if fb_status == 'new':
            cur.execute("""
                UPDATE claude.feedback SET status = 'triaged', updated_at = NOW()
                WHERE feedback_id = %s::uuid
            """, (fb_id,))
            new_fb_status = 'triaged'

            # Log transition
            cur.execute("""
                INSERT INTO claude.audit_log
                (entity_type, entity_id, entity_code, from_status, to_status,
                 changed_by, change_source, metadata)
                VALUES ('feedback', %s::uuid, %s, %s, 'triaged', %s, 'promote_feedback', %s::jsonb)
            """, (
                fb_id, fb_code, fb_status,
                os.environ.get('CLAUDE_SESSION_ID'),
                json.dumps({"promoted_to": feature_code, "feature_id": feature_id}),
            ))

        conn.commit()

        return {
            "success": True,
            "feature_code": feature_code,
            "feature_id": feature_id,
            "feedback_code": fb_code,
            "feedback_title": fb_title,
            "feature_name": f_name,
            "from_status": fb_status,
            "to_status": new_fb_status,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to promote feedback: {str(e)}"}
    finally:
        conn.close()


@mcp.tool()
def resolve_feedback(
    feedback_id: str,
    resolution_note: str = "",
) -> dict:
    """Resolve a feedback item in one call, auto-advancing through intermediate states.

    Convenience tool that handles multi-step state transitions automatically.
    Each transition is individually logged to audit_log via WorkflowEngine.
    Supports feedback at any status: new, triaged, or in_progress.

    Use when: A feedback item has been fixed and you want to mark it resolved.
    Avoids the need for multiple advance_status calls (new→in_progress→resolved).
    Returns: {success, feedback_code, from_status, to_status, transitions_made,
              path: [list of statuses traversed]}.

    Args:
        feedback_id: Feedback short code (e.g., 'FB42') or UUID.
        resolution_note: Optional note about the resolution.
    """
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    conn = get_db_connection()
    try:
        engine = WorkflowEngine(conn)

        # Resolve the short code to get current status
        cur = conn.cursor()
        if feedback_id.upper().startswith("FB"):
            try:
                code_num = int(feedback_id[2:])
            except ValueError:
                return {"success": False, "error": f"Invalid feedback code: {feedback_id}"}
            cur.execute("""
                SELECT feedback_id::text, status, short_code, title
                FROM claude.feedback
                WHERE short_code = %s
            """, (code_num,))
        else:
            cur.execute("""
                SELECT feedback_id::text, status, short_code, title
                FROM claude.feedback
                WHERE feedback_id = %s::uuid
            """, (feedback_id,))

        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"Feedback not found: {feedback_id}"}

        current_status = row['status']
        fb_code = f"FB{row['short_code']}"
        original_status = current_status
        path = [current_status]

        # Already resolved
        if current_status == 'resolved':
            return {
                "success": True,
                "feedback_code": fb_code,
                "from_status": current_status,
                "to_status": "resolved",
                "transitions_made": 0,
                "path": path,
                "message": "Already resolved",
            }

        # Terminal states that can't reach resolved
        if current_status in ('wont_fix', 'duplicate'):
            return {
                "success": False,
                "feedback_code": fb_code,
                "error": f"Cannot resolve from '{current_status}' - item is already closed.",
            }

        # Define the path to resolved from each status
        transitions_needed = {
            'new': ['in_progress', 'resolved'],
            'triaged': ['in_progress', 'resolved'],
            'in_progress': ['resolved'],
        }

        steps = transitions_needed.get(current_status)
        if not steps:
            return {
                "success": False,
                "feedback_code": fb_code,
                "error": f"Unexpected status '{current_status}' - cannot auto-resolve.",
            }

        # Execute each transition through the WorkflowEngine
        transitions_made = 0
        for next_status in steps:
            result = engine.execute_transition(
                entity_type='feedback',
                item_id=feedback_id,
                new_status=next_status,
                changed_by=session_id,
                change_source='resolve_feedback',
            )
            if not result.get('success'):
                return {
                    "success": False,
                    "feedback_code": fb_code,
                    "from_status": original_status,
                    "failed_at": f"{current_status}→{next_status}",
                    "transitions_completed": transitions_made,
                    "path": path,
                    "error": result.get('error', 'Transition failed'),
                }
            current_status = next_status
            path.append(next_status)
            transitions_made += 1

        # Add resolution note if provided
        if resolution_note:
            cur.execute("""
                UPDATE claude.feedback
                SET description = description || E'\n\n**Resolution:** ' || %s,
                    updated_at = NOW()
                WHERE short_code = %s
            """, (resolution_note, row['short_code']))
            conn.commit()

        return {
            "success": True,
            "feedback_code": fb_code,
            "title": row['title'],
            "from_status": original_status,
            "to_status": "resolved",
            "transitions_made": transitions_made,
            "path": path,
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to resolve feedback: {str(e)}"}
    finally:
        conn.close()


@mcp.tool()
def recover_session(
    project: str = "",
) -> dict:
    """Recover context after a session crash or unexpected exit.

    Single-call replacement for raw SQL crash-recovery. Follows the
    crash_recovery BPMN process: loads session facts, finds crashed sessions
    (filtering re-fires), parses transcript for crash signals, collects
    in-progress work, and returns structured recovery context.

    Use when: A session ended unexpectedly (crash, timeout, CLI exit) and
    you need to understand what happened and recover context.
    Returns: {success, project, session_facts, crashed_sessions,
              last_completed_session, in_progress_work, crash_analysis,
              git_status, recovery_actions}.

    Args:
        project: Project name. Defaults to current directory.
    """
    from pathlib import Path

    project = project or os.path.basename(os.getcwd())
    result = {"success": True, "project": project}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # ── Step 1: Load session facts from recent sessions ──
        # (Reuses recall_previous_session_facts logic inline)
        cur.execute("""
            WITH recent_sessions AS (
                SELECT session_id
                FROM claude.sessions
                WHERE project_name = %s
                ORDER BY session_start DESC
                LIMIT 3
            )
            SELECT sf.fact_key, sf.fact_value, sf.fact_type, sf.created_at,
                   sf.session_id::text
            FROM claude.session_facts sf
            WHERE sf.session_id = ANY(
                SELECT session_id FROM recent_sessions
            )
              AND sf.is_sensitive = false
            ORDER BY sf.created_at DESC
        """, (project,))
        facts = cur.fetchall()
        result["session_facts"] = {
            "count": len(facts),
            "facts": [
                {
                    "key": f['fact_key'],
                    "value": f['fact_value'][:200],
                    "type": f['fact_type'],
                }
                for f in facts
            ],
        }

        # ── Step 2: Find unclosed sessions ──
        cur.execute("""
            SELECT session_id::text,
                   session_start,
                   EXTRACT(EPOCH FROM (NOW() - session_start))/3600 as hours_ago
            FROM claude.sessions
            WHERE project_name = %s
              AND session_end IS NULL
            ORDER BY session_start DESC
            LIMIT 10
        """, (project,))
        unclosed = cur.fetchall()

        # ── Step 3: Filter continuation re-fires (<60s apart) ──
        genuine_crashes = []
        refires = 0
        for i, s in enumerate(unclosed):
            if i == 0:
                # Most recent is always kept (likely current session)
                genuine_crashes.append(s)
                continue
            # Check if this session started within 60s of the previous one
            prev = unclosed[i - 1]
            time_gap = abs(
                (prev['session_start'] - s['session_start']).total_seconds()
            )
            if time_gap < 60:
                refires += 1  # Skip re-fire
            else:
                genuine_crashes.append(s)

        # Remove current session from crash list (it's the one running now)
        if genuine_crashes and genuine_crashes[0]['hours_ago'] < 0.01:
            current_session = genuine_crashes.pop(0)

        result["crashed_sessions"] = {
            "count": len(genuine_crashes),
            "refires_filtered": refires,
            "sessions": [
                {
                    "session_id": s['session_id'][:8] + "...",
                    "hours_ago": round(float(s['hours_ago']), 2),
                    "started": str(s['session_start']),
                }
                for s in genuine_crashes
            ],
        }

        # ── Step 4: Get last completed session ──
        cur.execute("""
            SELECT session_summary, session_end, tasks_completed
            FROM claude.sessions
            WHERE project_name = %s AND session_end IS NOT NULL
            ORDER BY session_end DESC LIMIT 1
        """, (project,))
        last = cur.fetchone()
        if last:
            result["last_completed_session"] = {
                "summary": last['session_summary'],
                "ended": str(last['session_end']),
                "tasks_completed": last['tasks_completed'] or [],
            }
        else:
            result["last_completed_session"] = None

        # ── Step 5: Get in-progress work items ──
        cur.execute("""
            SELECT 'TODO' as type, t.content as description, t.priority::text
            FROM claude.todos t
            JOIN claude.projects p ON t.project_id = p.project_id
            WHERE p.project_name = %s
              AND t.status = 'in_progress'
              AND t.is_deleted = false

            UNION ALL

            SELECT 'TASK' as type, bt.task_name as description, '2' as priority
            FROM claude.build_tasks bt
            JOIN claude.features f ON bt.feature_id = f.feature_id
            JOIN claude.projects p ON f.project_id = p.project_id
            WHERE p.project_name = %s
              AND bt.status = 'in_progress'

            UNION ALL

            SELECT 'FEATURE' as type, f.feature_name as description, '1' as priority
            FROM claude.features f
            JOIN claude.projects p ON f.project_id = p.project_id
            WHERE p.project_name = %s
              AND f.status = 'in_progress'

            ORDER BY priority
        """, (project, project, project))
        work = cur.fetchall()
        result["in_progress_work"] = {
            "count": len(work),
            "items": [dict(w) for w in work],
        }

        # ── Step 6: Parse transcript for crash signals ──
        crash_analysis = {"analyzed": False}
        if genuine_crashes:
            try:
                # Find project transcript directory (exact match to avoid
                # picking up sub-project dirs like ...-mcp-servers-orchestrator)
                home = Path.home()
                projects_dir = home / ".claude" / "projects"
                project_slug = f"C--Projects-{project}"
                # Use exact directory name first, fall back to glob
                exact_dir = projects_dir / project_slug
                if exact_dir.is_dir():
                    project_dir = exact_dir
                else:
                    project_dirs = list(projects_dir.glob(f"*{project_slug}"))
                    project_dir = project_dirs[0] if project_dirs else None

                if project_dir:
                    jsonl_files = sorted(
                        project_dir.glob("*.jsonl"),
                        key=lambda f: f.stat().st_mtime,
                        reverse=True,
                    )
                    # Skip the MOST RECENT file (index 0) - it's the
                    # current session's transcript, actively locked by
                    # Claude Code on Windows. Reading it causes deadlock.
                    # Use the PREVIOUS session's transcript instead.
                    transcript_file = None
                    if len(jsonl_files) > 1:
                        transcript_file = jsonl_files[1]
                    elif len(jsonl_files) == 1:
                        # Only one file - try non-blocking read with timeout
                        transcript_file = jsonl_files[0]

                    if transcript_file:
                        file_size_kb = transcript_file.stat().st_size / 1024

                        # Parse only the TAIL of the file (last 200 lines)
                        entries = []
                        all_lines = []
                        try:
                            with open(transcript_file, 'r', encoding='utf-8') as f:
                                all_lines = f.readlines()
                        except (PermissionError, OSError):
                            # File locked (Windows) - skip transcript analysis
                            all_lines = []

                        tail_lines = all_lines[-200:] if len(all_lines) > 200 else all_lines
                        for line in tail_lines:
                            if line.strip():
                                try:
                                    entries.append(json.loads(line))
                                except json.JSONDecodeError:
                                    pass

                        # Count continuation markers from full file
                        continuation_markers = sum(
                            1 for ln in all_lines
                            if 'continued from' in ln.lower()
                        )
                        del all_lines  # Free memory

                        # Analyze crash signals from tail entries
                        output_tokens_1_count = 0
                        stop_reason_none_count = 0
                        max_input_tokens = 0
                        last_user_msg = ""
                        last_assistant_action = ""

                        for entry in entries:
                            t = entry.get('type', '')
                            msg = entry.get('message', {})

                            if t == 'user':
                                content = msg.get('content', '') if isinstance(msg, dict) else ''
                                if isinstance(content, str) and '<system-reminder>' not in content and content.strip():
                                    last_user_msg = content[:200]
                                elif isinstance(content, list):
                                    for c in content:
                                        if isinstance(c, dict) and c.get('type') == 'text':
                                            text = c.get('text', '')
                                            if '<system-reminder>' not in text and text.strip():
                                                last_user_msg = text[:200]

                            if t == 'assistant' and isinstance(msg, dict):
                                usage = msg.get('usage', {})
                                if usage:
                                    out_tokens = usage.get('output_tokens', 0)
                                    total_in = (
                                        usage.get('cache_read_input_tokens', 0)
                                        + usage.get('input_tokens', 0)
                                        + usage.get('cache_creation_input_tokens', 0)
                                    )
                                    if total_in > max_input_tokens:
                                        max_input_tokens = total_in
                                    if out_tokens == 1:
                                        output_tokens_1_count += 1

                                stop = msg.get('stop_reason')
                                if stop is None and usage:
                                    stop_reason_none_count += 1

                                content = msg.get('content', [])
                                if isinstance(content, list):
                                    for c in content:
                                        if isinstance(c, dict):
                                            if c.get('type') == 'tool_use':
                                                last_assistant_action = f"tool:{c.get('name', '?')}"
                                            elif c.get('type') == 'text' and c.get('text', '').strip():
                                                last_assistant_action = f"text:{c['text'][:100]}"

                        # Determine crash type
                        crash_type = "unknown"
                        if output_tokens_1_count >= 5 and stop_reason_none_count >= 3:
                            crash_type = "cli_process_crash"
                        elif continuation_markers > 0:
                            crash_type = "context_exhaustion"
                        elif max_input_tokens > 180000:
                            crash_type = "context_limit"

                        crash_analysis = {
                            "analyzed": True,
                            "transcript_file": transcript_file.name,
                            "file_size_kb": round(file_size_kb, 1),
                            "total_entries": len(entries),
                            "crash_type": crash_type,
                            "max_input_tokens": max_input_tokens,
                            "output_tokens_1_count": output_tokens_1_count,
                            "stop_reason_none_count": stop_reason_none_count,
                            "continuation_markers": continuation_markers,
                            "last_user_message": last_user_msg,
                            "last_assistant_action": last_assistant_action,
                        }

            except Exception as e:
                crash_analysis = {"analyzed": False, "error": str(e)}

        result["crash_analysis"] = crash_analysis

        # ── Step 7: Git info (file-based, no subprocess) ──
        # subprocess.run deadlocks on Windows when called from MCP server
        # subprocesses (pipe handle inheritance issue). Read .git/ directly.
        git_info = {}
        try:
            git_dir = Path(os.getcwd()) / ".git"
            if git_dir.is_dir():
                # Current branch
                head_file = git_dir / "HEAD"
                if head_file.exists():
                    head = head_file.read_text().strip()
                    if head.startswith("ref: refs/heads/"):
                        git_info["branch"] = head[16:]
                    else:
                        git_info["branch"] = head[:8] + "... (detached)"

                # Recent commits from reflog (no subprocess needed)
                reflog = git_dir / "logs" / "HEAD"
                if reflog.exists():
                    lines = reflog.read_text(encoding='utf-8', errors='replace').strip().split('\n')
                    recent = []
                    for line in reversed(lines[-5:]):
                        # Reflog format: old_sha new_sha Author <email> timestamp tz\taction: message
                        parts = line.split('\t', 1)
                        if len(parts) == 2:
                            sha = parts[0].split()[1][:7] if parts[0].split() else "?"
                            msg = parts[1]
                            recent.append(f"{sha} {msg}")
                    git_info["recent_reflog"] = recent

                git_info["note"] = "File-based read (no git subprocess). Run 'git status' for full details."
            else:
                git_info["note"] = "Not a git repository"
        except Exception as e:
            git_info = {"error": f"Could not read .git: {str(e)}"}

        result["git_status"] = git_info

        # ── Step 8: Recovery actions ──
        actions = []
        if result["session_facts"]["count"] > 0:
            actions.append("Session facts recovered - key decisions/configs available")
        if len(genuine_crashes) > 0:
            actions.append(f"{len(genuine_crashes)} crashed session(s) found - review crash analysis")
        if result["in_progress_work"]["count"] > 0:
            actions.append(f"{result['in_progress_work']['count']} in-progress work item(s) - continue where you left off")
        if git_info.get("branch"):
            actions.append(f"On branch '{git_info['branch']}' - run 'git status' to check uncommitted changes")
        if crash_analysis.get("crash_type") == "cli_process_crash":
            actions.append("CLI crash detected (output_tokens=1 pattern) - not a context issue")
        elif crash_analysis.get("crash_type") == "context_exhaustion":
            actions.append("Context exhaustion detected - consider smaller tasks or checkpointing")
        result["recovery_actions"] = actions

        return result

    except Exception as e:
        return {"success": False, "error": f"Recovery failed: {str(e)}"}
    finally:
        conn.close()


# ============================================================================
# Protocol Version Control
# ============================================================================


@mcp.tool()
def update_protocol(
    content: str,
    change_reason: str,
    protocol_name: str = "CORE_PROTOCOL",
) -> dict:
    """Update a protocol to a new version. Deactivates old, inserts new, deploys to file.

    Use when: Changing the CORE_PROTOCOL or other injected protocols.
    Creates a new version in claude.protocol_versions, sets it active,
    and deploys to scripts/core_protocol.txt for runtime use.
    Returns: {success, protocol_name, old_version, new_version, deployed}.

    Args:
        content: The full new protocol text.
        change_reason: Why this change was made (for audit trail).
        protocol_name: Protocol to update (default: CORE_PROTOCOL).
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # Get current active version
        cur.execute("""
            SELECT version_id, version FROM claude.protocol_versions
            WHERE protocol_name = %s AND is_active = true
        """, (protocol_name,))
        current = cur.fetchone()
        old_version = current["version"] if current else 0

        new_version = old_version + 1

        # Deactivate current
        if current:
            cur.execute("""
                UPDATE claude.protocol_versions
                SET is_active = false
                WHERE version_id = %s
            """, (current["version_id"],))

        # Insert new version
        cur.execute("""
            INSERT INTO claude.protocol_versions
            (protocol_name, version, content, change_reason, changed_by, is_active)
            VALUES (%s, %s, %s, %s, %s, true)
            RETURNING version_id
        """, (protocol_name, new_version, content.strip(), change_reason,
              f"session:{os.environ.get('SESSION_ID', 'unknown')}"))

        new_id = cur.fetchone()["version_id"]

        # Deploy to file
        deployed = False
        try:
            scripts_dir = Path(__file__).parent.parent.parent / "scripts"
            protocol_file = scripts_dir / "core_protocol.txt"
            if scripts_dir.exists():
                protocol_file.write_text(content.strip(), encoding="utf-8")
                deployed = True
        except Exception:
            pass  # Non-fatal - hook falls back to hardcoded default

        conn.commit()
        return {
            "success": True,
            "protocol_name": protocol_name,
            "old_version": old_version,
            "new_version": new_version,
            "version_id": new_id,
            "deployed": deployed,
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_protocol_history(
    protocol_name: str = "CORE_PROTOCOL",
    limit: int = 10,
) -> dict:
    """Get version history for a protocol.

    Use when: Reviewing what changed in the CORE_PROTOCOL over time.
    Returns all versions with content, change reasons, and timestamps.
    Returns: {success, protocol_name, versions: [{version, content,
              change_reason, changed_by, created_at, is_active}]}.

    Args:
        protocol_name: Protocol to get history for (default: CORE_PROTOCOL).
        limit: Maximum versions to return (default: 10).
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT version, content, change_reason, changed_by,
                   created_at::text, is_active
            FROM claude.protocol_versions
            WHERE protocol_name = %s
            ORDER BY version DESC
            LIMIT %s
        """, (protocol_name, limit))

        versions = []
        for row in cur.fetchall():
            versions.append({
                "version": row["version"],
                "content": row["content"],
                "change_reason": row["change_reason"],
                "changed_by": row["changed_by"],
                "created_at": row["created_at"],
                "is_active": row["is_active"],
            })

        return {
            "success": True,
            "protocol_name": protocol_name,
            "version_count": len(versions),
            "versions": versions,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_active_protocol(
    protocol_name: str = "CORE_PROTOCOL",
) -> dict:
    """Get the currently active protocol content.

    Use when: Checking what protocol is currently being injected.
    Returns: {success, protocol_name, version, content, change_reason, created_at}.

    Args:
        protocol_name: Protocol to retrieve (default: CORE_PROTOCOL).
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT version, content, change_reason, changed_by, created_at::text
            FROM claude.protocol_versions
            WHERE protocol_name = %s AND is_active = true
        """, (protocol_name,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"No active version for {protocol_name}"}
        return {
            "success": True,
            "protocol_name": protocol_name,
            "version": row["version"],
            "content": row["content"],
            "change_reason": row["change_reason"],
            "changed_by": row["changed_by"],
            "created_at": row["created_at"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# Messaging Tools (migrated from orchestrator MCP)
# ============================================================================


@mcp.tool()
def check_inbox(
    project_name: str = "",
    session_id: str = "",
    include_broadcasts: bool = True,
    include_read: bool = False,
) -> dict:
    """Check for pending messages from other Claude instances. Returns unread messages addressed to you or broadcast to all. IMPORTANT: Pass project_name to see project-targeted messages!

    Use when: Checking for messages from other Claude instances at session start
    or periodically during work.
    Returns: {count, messages: [{message_id, from_session_id, to_project, message_type,
              priority, subject, body, metadata, status, created_at}]}.

    Args:
        project_name: Your project name to filter messages (IMPORTANT: required to see project-targeted messages).
        session_id: Your session ID to filter direct messages.
        include_broadcasts: Include broadcast messages (default: true).
        include_read: Include already-read messages (default: false, only pending).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Status filter
        if include_read:
            status_condition = "status IN ('pending', 'read')"
        else:
            status_condition = "status = 'pending'"

        conditions = [status_condition]
        params = []

        # Build WHERE clause for recipients
        or_conditions = []
        has_specific_recipient = False

        if project_name:
            or_conditions.append("to_project = %s")
            params.append(project_name)
            has_specific_recipient = True
        if session_id:
            or_conditions.append("to_session_id = %s")
            params.append(session_id)
            has_specific_recipient = True

        if not has_specific_recipient:
            or_conditions.append("(to_session_id IS NULL AND to_project IS NULL)")
        elif include_broadcasts:
            or_conditions.append("(to_session_id IS NULL AND to_project IS NULL)")

        conditions.append(f"({' OR '.join(or_conditions)})")

        query = f"""
            SELECT
                message_id::text,
                from_session_id::text,
                to_project,
                message_type,
                priority,
                subject,
                body,
                metadata,
                status,
                created_at
            FROM claude.messages
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'normal' THEN 2
                    ELSE 3
                END,
                created_at DESC
            LIMIT 20
        """

        cur.execute(query, params)
        messages = cur.fetchall()
        cur.close()

        result_messages = []
        for msg in messages:
            msg_dict = dict(msg) if not isinstance(msg, dict) else msg
            if msg_dict.get('created_at'):
                msg_dict['created_at'] = msg_dict['created_at'].isoformat()
            result_messages.append(msg_dict)

        return {"count": len(result_messages), "messages": result_messages}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def send_message(
    message_type: Literal["task_request", "status_update", "question", "notification", "handoff", "broadcast"],
    body: str,
    subject: str = "",
    to_project: str = "",
    to_session_id: str = "",
    priority: Literal["urgent", "normal", "low"] = "normal",
    from_session_id: str = "",
) -> dict:
    """Send a message to another Claude instance or project.

    Use when: Communicating with other Claude instances, requesting tasks,
    sending status updates, or handing off work.
    Returns: {success, message_id, created_at}.

    Args:
        message_type: Type of message.
        body: Message content.
        subject: Message subject/title.
        to_project: Target project name.
        to_session_id: Target session ID (for direct message).
        priority: Message priority (default: normal).
        from_session_id: Your session ID.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.messages
            (from_session_id, to_session_id, to_project, message_type, priority, subject, body, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING message_id::text, created_at
        """, (
            from_session_id or None,
            to_session_id or None,
            to_project or None,
            message_type,
            priority,
            subject or None,
            body,
            json.dumps({}),
        ))
        result = cur.fetchone()
        cur.close()
        conn.commit()

        result_dict = dict(result) if not isinstance(result, dict) else result
        return {
            "success": True,
            "message_id": result_dict['message_id'],
            "created_at": result_dict['created_at'].isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def broadcast(
    body: str,
    subject: str = "",
    from_session_id: str = "",
    priority: Literal["urgent", "normal", "low"] = "normal",
) -> dict:
    """Send a message to ALL active Claude instances.

    Use when: Announcing something to all Claude instances (maintenance,
    important updates, team-wide notifications).
    Returns: {success, message_id, created_at}.

    Args:
        body: Message content.
        subject: Message subject.
        from_session_id: Your session ID.
        priority: Message priority (default: normal).
    """
    return send_message(
        message_type="broadcast",
        body=body,
        subject=subject,
        priority=priority,
        from_session_id=from_session_id,
        to_project="",
        to_session_id="",
    )


@mcp.tool()
def acknowledge(
    message_id: str,
    action: Literal["read", "acknowledged", "actioned", "deferred"] = "read",
    project_id: str = "",
    defer_reason: str = "",
    priority: int = 3,
) -> dict:
    """Mark a message as read, acknowledged, actioned (converted to todo), or deferred (explicitly skipped).

    Use when: Processing messages from your inbox. 'read' marks as seen,
    'acknowledged' confirms receipt, 'actioned' converts to a todo,
    'deferred' skips with a reason.
    Returns: {success, message_id, new_status} or {success, todo_id} for actioned.

    Args:
        message_id: ID of message to acknowledge.
        action: Action to take.
        project_id: Required if action='actioned' - UUID of project to create todo in.
        defer_reason: Required if action='deferred' - Explanation for why message is being deferred.
        priority: Optional priority for created todo (1-5, default 3). Only used if action='actioned'.
    """
    if action == "actioned":
        if not project_id:
            return {"success": False, "error": "project_id required for actioned messages"}
        return _action_message(message_id, project_id, priority)

    if action == "deferred":
        if not defer_reason:
            return {"success": False, "error": "defer_reason required for deferred messages"}
        return _defer_message(message_id, defer_reason)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if action == "read":
            cur.execute("""
                UPDATE claude.messages
                SET status = 'read', read_at = NOW()
                WHERE message_id = %s
                RETURNING message_id::text
            """, (message_id,))
        else:  # acknowledged
            cur.execute("""
                UPDATE claude.messages
                SET status = 'acknowledged', acknowledged_at = NOW()
                WHERE message_id = %s
                RETURNING message_id::text
            """, (message_id,))

        result = cur.fetchone()
        cur.close()
        conn.commit()

        return {
            "success": result is not None,
            "message_id": message_id,
            "new_status": action,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_active_sessions() -> dict:
    """Get all currently active Claude sessions (who's online).

    Use when: Checking who else is working, before sending messages.
    Returns: {count, sessions: [{session_id, identity_name, project_name,
              session_start, minutes_active}]}.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                sh.session_id::text,
                i.identity_name,
                sh.project_name,
                sh.session_start,
                EXTRACT(EPOCH FROM (NOW() - sh.session_start))/60 as minutes_active
            FROM claude.sessions sh
            JOIN claude.identities i ON sh.identity_id = i.identity_id
            WHERE sh.session_end IS NULL
            ORDER BY sh.session_start DESC
        """)
        sessions = cur.fetchall()
        cur.close()

        result_sessions = []
        for s in sessions:
            s_dict = dict(s) if not isinstance(s, dict) else s
            if s_dict.get('session_start'):
                s_dict['session_start'] = s_dict['session_start'].isoformat()
            if s_dict.get('minutes_active'):
                s_dict['minutes_active'] = float(s_dict['minutes_active'])
            result_sessions.append(s_dict)

        return {"count": len(result_sessions), "sessions": result_sessions}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def reply_to(
    original_message_id: str,
    body: str,
    from_session_id: str = "",
) -> dict:
    """Reply to a specific message.

    Use when: Responding to a message from another Claude instance.
    Automatically addresses the reply to the original sender.
    Returns: {success, message_id, created_at}.

    Args:
        original_message_id: ID of message to reply to.
        body: Reply content.
        from_session_id: Your session ID.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT from_session_id::text, to_project, subject
            FROM claude.messages
            WHERE message_id = %s
        """, (original_message_id,))
        original = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    if not original:
        return {"success": False, "error": "Original message not found"}

    original_dict = dict(original) if not isinstance(original, dict) else original

    return send_message(
        message_type="notification",
        body=body,
        subject=f"Re: {original_dict['subject']}" if original_dict.get('subject') else "Reply",
        to_session_id=original_dict.get('from_session_id') or "",
        to_project=original_dict.get('to_project') or "",
        from_session_id=from_session_id,
    )


@mcp.tool()
def bulk_acknowledge(
    message_ids: list[str],
    action: Literal["read", "acknowledged"] = "read",
) -> dict:
    """Acknowledge multiple messages at once. Useful for clearing inbox after reviewing messages.

    Use when: Processing multiple messages from inbox at once.
    Returns: {success, acknowledged_count}.

    Args:
        message_ids: List of message UUIDs to acknowledge.
        action: Action to apply: 'read' or 'acknowledged' (default: read).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        count = 0
        for mid in message_ids:
            if action == "read":
                cur.execute("""
                    UPDATE claude.messages SET status = 'read', read_at = NOW()
                    WHERE message_id = %s AND status = 'pending'
                """, (mid,))
            else:
                cur.execute("""
                    UPDATE claude.messages SET status = 'acknowledged', acknowledged_at = NOW()
                    WHERE message_id = %s
                """, (mid,))
            count += cur.rowcount
        cur.close()
        conn.commit()
        return {"success": True, "acknowledged_count": count}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_unactioned_messages(
    project_name: str,
) -> dict:
    """Get actionable messages (task_request/question/handoff) that haven't been actioned or deferred for a project.

    Use when: Checking for messages that need action during session start.
    Returns: {count, messages: [...]}.

    Args:
        project_name: Name of the project to check for unactioned messages.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                message_id::text,
                from_session_id::text,
                message_type,
                priority,
                subject,
                body,
                status,
                created_at
            FROM claude.messages
            WHERE to_project = %s
              AND message_type IN ('task_request', 'question', 'handoff')
              AND status NOT IN ('actioned', 'deferred')
            ORDER BY
                CASE priority WHEN 'urgent' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                created_at DESC
            LIMIT 20
        """, (project_name,))
        messages = cur.fetchall()
        cur.close()

        result = []
        for msg in messages:
            msg_dict = dict(msg) if not isinstance(msg, dict) else msg
            if msg_dict.get('created_at'):
                msg_dict['created_at'] = msg_dict['created_at'].isoformat()
            result.append(msg_dict)

        return {"count": len(result), "messages": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_message_history(
    project_name: str = "",
    days: int = 7,
    message_type: str = "",
    include_sent: bool = True,
    include_received: bool = True,
    limit: int = 50,
) -> dict:
    """Get message history for a project with filtering options.

    Use when: Reviewing past communications with other Claude instances.
    Returns: {count, messages: [...]}.

    Args:
        project_name: Project name to get message history for.
        days: Number of days to look back (default: 7).
        message_type: Filter by message type (optional).
        include_sent: Include messages sent by this project (default: true).
        include_received: Include messages received by this project (default: true).
        limit: Maximum messages to return (default: 50).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        conditions = [f"created_at > NOW() - INTERVAL '{min(days, 90)} days'"]
        params = []

        if project_name:
            direction_conditions = []
            if include_received:
                direction_conditions.append("to_project = %s")
                params.append(project_name)
            if include_sent:
                # Messages sent by sessions working on this project
                direction_conditions.append("""
                    from_session_id IN (
                        SELECT session_id FROM claude.sessions WHERE project_name = %s
                    )
                """)
                params.append(project_name)
            if direction_conditions:
                conditions.append(f"({' OR '.join(direction_conditions)})")

        if message_type:
            conditions.append("message_type = %s")
            params.append(message_type)

        query = f"""
            SELECT
                message_id::text, from_session_id::text, to_session_id::text,
                to_project, message_type, priority, subject, body, status, created_at
            FROM claude.messages
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT {min(limit, 100)}
        """

        cur.execute(query, params)
        messages = cur.fetchall()
        cur.close()

        result = []
        for msg in messages:
            msg_dict = dict(msg) if not isinstance(msg, dict) else msg
            if msg_dict.get('created_at'):
                msg_dict['created_at'] = msg_dict['created_at'].isoformat()
            result.append(msg_dict)

        return {"count": len(result), "messages": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers for acknowledge sub-actions
# ---------------------------------------------------------------------------

def _action_message(message_id: str, project_id: str, priority: int = 3) -> dict:
    """Convert a message into an actionable todo."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT subject, body, message_type
            FROM claude.messages WHERE message_id = %s
        """, (message_id,))
        message = cur.fetchone()

        if not message:
            cur.close()
            conn.close()
            return {"success": False, "error": "Message not found"}

        msg_dict = dict(message) if not isinstance(message, dict) else message
        content = msg_dict.get('subject', 'Unnamed task')
        active_form = f"Working on: {content}"

        cur.execute("""
            INSERT INTO claude.todos
            (project_id, content, active_form, status, priority, source_message_id)
            VALUES (%s, %s, %s, 'pending', %s, %s)
            RETURNING todo_id::text
        """, (project_id, content, active_form, priority, message_id))

        todo_result = cur.fetchone()
        todo_dict = dict(todo_result) if not isinstance(todo_result, dict) else todo_result

        cur.execute("""
            UPDATE claude.messages SET status = 'actioned', acknowledged_at = NOW()
            WHERE message_id = %s
        """, (message_id,))

        cur.close()
        conn.commit()
        return {"success": True, "todo_id": todo_dict['todo_id'], "message": "Message converted to todo"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def _defer_message(message_id: str, reason: str) -> dict:
    """Defer a message with a reason."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE claude.messages
            SET status = 'deferred',
                acknowledged_at = NOW(),
                metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('defer_reason', %s, 'deferred_at', NOW()::text)
            WHERE message_id = %s
            RETURNING message_id::text
        """, (reason, message_id))

        result = cur.fetchone()
        cur.close()
        conn.commit()

        if not result:
            return {"success": False, "error": "Message not found"}
        return {"success": True, "message": "Message deferred", "reason": reason}
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
