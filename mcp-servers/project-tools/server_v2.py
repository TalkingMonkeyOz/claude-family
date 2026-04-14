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
import asyncio
import threading
from typing import Any, Literal, Optional
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

# ============================================================================
# FastMCP Setup
# ============================================================================

from mcp.server.fastmcp import FastMCP


# ============================================================================
# Channel Messaging — Real-time LISTEN/NOTIFY (merged from channel-messaging)
# ============================================================================

class _ChannelState:
    """Shared state for the background PostgreSQL LISTEN/NOTIFY listener."""
    session = None          # Captured from first tool call
    connected: bool = False
    project_name: str = ""
    listening_channels: list = []
    _thread = None
    _conn = None
    _stop_event = threading.Event()

_channel = _ChannelState()


def _pg_listen_thread(main_loop):
    """Background thread: LISTEN on PostgreSQL channels using SelectorEventLoop.

    psycopg3 async requires SelectorEventLoop, but Windows defaults to
    ProactorEventLoop (which FastMCP uses). We run our own event loop in
    a thread and dispatch notifications back to the main loop.
    """
    import selectors
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_pg_listen_loop_inner(main_loop))
    except Exception as e:
        print(f"Channel messaging thread exited: {e}", file=sys.stderr)
    finally:
        loop.close()
        _channel.connected = False


async def _pg_listen_loop_inner(main_loop):
    """Async LISTEN loop running inside SelectorEventLoop thread."""
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')
    if not conn_string:
        print("Channel messaging: no DATABASE_URI set, skipping", file=sys.stderr)
        return

    project = _channel.project_name
    pg_channel = 'claude_msg_' + project.lower().replace('-', '_')
    broadcast_channel = 'claude_msg_broadcast'
    _channel.listening_channels = [pg_channel, broadcast_channel]

    while not _channel._stop_event.is_set():
        try:
            import psycopg
            _channel._conn = await psycopg.AsyncConnection.connect(
                conn_string, autocommit=True
            )
            async with _channel._conn:
                _channel.connected = True
                await _channel._conn.execute(f"LISTEN {pg_channel}")
                await _channel._conn.execute(f"LISTEN {broadcast_channel}")
                print(f"Channel messaging: listening on {pg_channel}, {broadcast_channel}", file=sys.stderr)

                async for notify in _channel._conn.notifies():
                    if _channel._stop_event.is_set():
                        return
                    if _channel.session is None:
                        continue  # No session yet, skip
                    try:
                        payload = json.loads(notify.payload)
                        # Dispatch notification to main event loop (MCP session writes)
                        asyncio.run_coroutine_threadsafe(
                            _send_channel_notification(payload), main_loop
                        )
                    except Exception as e:
                        print(f"Channel notification error: {e}", file=sys.stderr)

        except Exception as e:
            _channel.connected = False
            _channel._conn = None
            if _channel._stop_event.is_set():
                return
            print(f"Channel messaging reconnecting in 5s: {e}", file=sys.stderr)
            await asyncio.sleep(5)


async def _send_channel_notification(payload: dict):
    """Push a real-time notification into the Claude session via MCP."""
    session = _channel.session
    if session is None:
        return

    from_project = payload.get('from_project', 'unknown')
    subject = payload.get('subject', '')
    msg_type = payload.get('message_type', 'notification')
    subject_text = f': {subject}' if subject else ''
    content = f"New {msg_type} from {from_project}{subject_text}. Use check_inbox() to read the full message."

    try:
        # Try experimental claude/channel notification first
        from mcp.types import JSONRPCNotification, JSONRPCMessage
        from mcp.shared.message import SessionMessage

        notification = JSONRPCNotification(
            jsonrpc="2.0",
            method="notifications/claude/channel",
            params={"content": content, "meta": {
                "from_project": from_project,
                "message_type": msg_type,
                "priority": payload.get('priority', 'normal'),
                "message_id": payload.get('message_id'),
            }}
        )
        session_message = SessionMessage(
            message=JSONRPCMessage(notification),
            metadata=None,
        )
        await session._write_stream.send(session_message)
    except Exception:
        # Fallback: standard log message (always works)
        try:
            await session.send_log_message(level="info", data=content)
        except Exception:
            pass


@asynccontextmanager
async def _channel_lifespan(app: FastMCP) -> AsyncIterator[dict]:
    """Start the PostgreSQL LISTEN/NOTIFY background listener on server startup.

    Runs in a separate thread with SelectorEventLoop because psycopg3 async
    requires it (Windows defaults to ProactorEventLoop which is incompatible).
    """
    _channel.project_name = os.environ.get(
        'CLAUDE_PROJECT',
        os.path.basename(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))
    )

    # Get the main event loop for dispatching notifications back
    main_loop = asyncio.get_running_loop()

    # Launch background listener in a daemon thread
    _channel._stop_event.clear()
    _channel._thread = threading.Thread(
        target=_pg_listen_thread,
        args=(main_loop,),
        daemon=True,
        name="pg-channel-listener",
    )
    _channel._thread.start()

    yield {}

    # Shutdown: signal thread to stop, close connection
    _channel._stop_event.set()
    if _channel._conn:
        try:
            # Close the async connection to unblock the notifies() iterator
            # This is safe from another thread for psycopg3
            _channel._conn.close()
        except Exception:
            pass
    if _channel._thread:
        _channel._thread.join(timeout=3)
    _channel.connected = False


mcp = FastMCP(
    "project-tools",
    instructions=(
        "Project-aware tooling for Claude Family development. "
        "Use start_session at the beginning of work. "
        "Use get_schema when you need to understand database tables. "
        "Use end_session when finishing work."
    ),
    lifespan=_channel_lifespan,
)


# ============================================================================
# MCP _meta: Raise persist-to-disk threshold for heavy tools (v2.1.91+)
# ============================================================================
# FastMCP doesn't expose _meta on @mcp.tool(), so we patch list_tools to
# inject anthropic/maxResultSizeChars on tools that return large responses.
# Without this, Claude Code silently truncates results that exceed the default
# persist threshold, causing incomplete data for schema, context, and board ops.

LARGE_RESULT_TOOLS: dict[str, int] = {
    # Session & orientation (returns full project context, todos, features, messages)
    "start_session": 200_000,
    # Schema reference (full table defs with constraints for 60+ tables)
    "get_schema": 200_000,
    # Build board (stream → feature → task hierarchy for entire project)
    "get_build_board": 200_000,
    # Context assembly (WCC multi-source context, token-budgeted)
    "assemble_context": 200_000,
    # Memory recall (3-tier retrieval: short/mid/long with graph walk)
    "recall_memories": 100_000,
    # Entity catalog search (structured data with full properties)
    "recall_entities": 100_000,
    # Work context (feature-level or project-level overviews)
    "get_work_context": 100_000,
    # Session end (extracts insights, stores conversation)
    "end_session": 100_000,
    # Conversation extraction (full session turns)
    "extract_conversation": 200_000,
    # Module map (project-wide symbol listing)
    "get_module_map": 100_000,
    # Symbol context (body + callers + callees + siblings)
    "get_context": 100_000,
    # Dependency graph (recursive call chains)
    "get_dependency_graph": 100_000,
}

_original_list_tools = mcp.list_tools


async def _list_tools_with_meta() -> list:
    """Wrap list_tools to inject _meta on tools that return large results."""
    tools = await _original_list_tools()
    for tool in tools:
        if tool.name in LARGE_RESULT_TOOLS:
            tool.meta = {
                "anthropic/maxResultSizeChars": LARGE_RESULT_TOOLS[tool.name]
            }
    return tools

mcp.list_tools = _list_tools_with_meta


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
    next_steps = (data.get("previous_state", {}) or {}).get("next_steps", []) or []
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

    # Next priorities from previous session's end_session() call
    if next_steps:
        lines.append(row(f"NEXT PRIORITIES ({len(next_steps)}):"))
        for i, step in enumerate(next_steps[:9], 1):
            step_text = step if isinstance(step, str) else str(step)
            lines.append(row(f"  {i}. {step_text[:w - 8]}"))
        lines.append(div)

    # Active workfiles (filing cabinet components) — populated by start_session()
    active_workfiles = data.get("active_workfiles", [])
    if active_workfiles:
        lines.append(row(f"ACTIVE WORKFILES ({len(active_workfiles)}):"))
        for wf in active_workfiles[:5]:
            pin = " [pinned]" if wf.get("pinned_count", 0) > 0 else ""
            lines.append(row(f"  - {wf['component']} ({wf['file_count']} files){pin}"))
        lines.append(div)

    # Native task count from disk (~/.claude/tasks/{list_id}/)
    # Claude Code natively persists tasks as JSON files. Show count so
    # user knows their backlog size. Use /tasks to see details.
    native_task_count = 0
    try:
        list_id = os.environ.get("CLAUDE_CODE_TASK_LIST_ID", "")
        if list_id:
            tasks_dir = Path.home() / ".claude" / "tasks" / list_id
            if tasks_dir.exists():
                native_task_count = len(list(tasks_dir.glob("*.json")))
    except OSError:
        pass
    lines.append(row(f"TASK BACKLOG: {native_task_count} pending (use /tasks to view)"))
    lines.append(div)

    # Features section — detect streams for build board view
    has_streams = any(f.get('feature_type') == 'stream' for f in features)
    if features:
        if has_streams:
            # Build board view: streams → child features
            lines.append(row("BUILD BOARD:"))
            for f in features:
                if f.get('feature_type') == 'stream':
                    lines.append(row(f"  {f.get('code')} {f.get('feature_name')} [{f.get('status')}]"))
                    # Show children inline
                    children = [c for c in features
                                if c.get('parent_feature_id') and str(c.get('parent_feature_id')) == str(f.get('feature_id', ''))]
                    for c in children[:4]:
                        done = c.get('tasks_done', 0)
                        total = c.get('tasks_total', 0)
                        lines.append(row(f"    {c.get('code')} {c.get('feature_name', '?')} ({done}/{total})"))
            # Show standalone features too
            stream_ids = {str(f.get('feature_id', '')) for f in features if f.get('feature_type') == 'stream'}
            standalone = [f for f in features
                         if f.get('feature_type') != 'stream'
                         and not (f.get('parent_feature_id') and str(f.get('parent_feature_id')) in stream_ids)]
            if standalone:
                lines.append(row("  Standalone:"))
                for f in standalone[:3]:
                    done = f.get('tasks_done', 0)
                    total = f.get('tasks_total', 0)
                    lines.append(row(f"    {f.get('code')} {f.get('feature_name', '?')} ({done}/{total})"))
        else:
            # Flat feature view (no streams)
            lines.append(row("ACTIVE FEATURES:"))
            for f in features[:5]:
                done = f.get("tasks_done", 0)
                total = f.get("tasks_total", 0)
                lines.append(row(f"  {f.get('code', '?')} {f.get('feature_name', '?')} ({done}/{total})"))
        lines.append(div)

    # Ready tasks (for stream-enabled projects)
    ready_tasks = data.get("ready_tasks", [])
    if has_streams and ready_tasks:
        lines.append(row(f"READY TASKS ({len(ready_tasks)}):"))
        for rt in ready_tasks[:5]:
            lines.append(row(f"  {rt.get('task_code', '?')} {rt.get('task_name', '?')[:w - 12]}"))
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

    # Capture MCP session for channel messaging (first tool call captures it)
    _try_capture_session()

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
                        f.feature_id,
                        f.feature_name,
                        f.status,
                        f.priority,
                        f.feature_type,
                        f.parent_feature_id,
                        (SELECT COUNT(*) FROM claude.build_tasks bt
                         WHERE bt.feature_id = f.feature_id AND bt.status = 'completed') as tasks_done,
                        (SELECT COUNT(*) FROM claude.build_tasks bt
                         WHERE bt.feature_id = f.feature_id) as tasks_total
                    FROM claude.features f
                    WHERE f.project_id = %s::uuid
                      AND f.status NOT IN ('completed', 'cancelled')
                    ORDER BY f.priority, f.short_code
                    LIMIT 20
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
                      AND to_project = %s
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

                # Active workfiles (components with file counts, pinned first)
                try:
                    cur.execute("""
                        SELECT component,
                               COUNT(*) AS file_count,
                               MAX(updated_at) AS last_updated,
                               COUNT(*) FILTER (WHERE is_pinned) AS pinned_count
                        FROM claude.project_workfiles
                        WHERE project_id = %s::uuid AND is_active = TRUE
                        GROUP BY component
                        ORDER BY MAX(CASE WHEN is_pinned THEN 1 ELSE 0 END) DESC, MAX(updated_at) DESC
                        LIMIT 10
                    """, (project_id,))
                    workfile_rows = cur.fetchall()
                    if workfile_rows:
                        result["active_workfiles"] = [{
                            "component": r['component'],
                            "file_count": r['file_count'],
                            "last_updated": str(r['last_updated']),
                            "pinned_count": r['pinned_count'],
                        } for r in workfile_rows]
                except Exception:
                    pass

                # Surface available entity types (Option B discoverability)
                # Shows what structured data is available in the catalog for this project's domain
                try:
                    cur.execute("""
                        SELECT et.type_name, et.display_name, COUNT(*) as count
                        FROM claude.entities e
                        JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                        WHERE e.project_id = %s::uuid AND NOT e.is_archived
                        GROUP BY et.type_name, et.display_name
                        ORDER BY count DESC
                    """, (project_id,))
                    entity_rows = cur.fetchall()
                    if entity_rows:
                        result["available_entities"] = [{
                            "type": r['type_name'],
                            "display_name": r['display_name'],
                            "count": r['count'],
                            "search_hint": f'recall_entities("query", entity_type="{r["type_name"]}")',
                        } for r in entity_rows]
                except Exception:
                    pass
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
            # BUG FIX (2026-04-08): Previous query updated ALL open sessions for the project.
            # Now uses subquery to target only the most recent open session.
            cur.execute("""
                UPDATE claude.sessions
                SET session_end = NOW(),
                    session_summary = %s,
                    tasks_completed = %s,
                    learnings_gained = %s
                WHERE session_id = (
                    SELECT session_id FROM claude.sessions
                    WHERE project_name = %s
                      AND session_end IS NULL
                      AND session_start > NOW() - INTERVAL '24 hours'
                    ORDER BY session_start DESC
                    LIMIT 1
                )
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

        # 2b. Auto-stash session handoff workfile when there are next steps
        if next_steps:
            try:
                stash_content = f"## Session Summary ({datetime.now().strftime('%Y-%m-%d')})\n\n"
                stash_content += f"**What was done:** {summary}\n\n"
                if tasks_completed:
                    stash_content += "**Completed:**\n"
                    for tc in tasks_completed:
                        stash_content += f"- {tc}\n"
                stash_content += "\n**Next priorities:**\n"
                for ns in next_steps:
                    stash_content += f"- {ns}\n"
                if learnings:
                    stash_content += "\n**Key learnings:**\n"
                    for lg in learnings:
                        stash_content += f"- {lg}\n"

                stash_result = stash(
                    component="session-handoff",
                    title=f"handoff-{datetime.now().strftime('%Y-%m-%d')}",
                    content=stash_content,
                    project=project,
                    workfile_type="notes",
                    mode="replace",
                )
                results["handoff_stashed"] = stash_result.get("success", False)
            except Exception:
                pass  # Don't break end_session if stash fails

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
                            applies_to_projects, embedding, tier, created_at
                        ) VALUES (
                            gen_random_uuid(), %s, %s, 'learned', %s,
                            %s, 85, %s, %s, 'mid', NOW()
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

        # 6. F130: Phase 1 consolidation (short→mid promotion)
        if closed_session_id:
            try:
                consolidation_result = _run_async(tool_consolidate_memories("session_end", project))
                results["consolidation"] = {
                    "promoted": consolidation_result.get("promoted_short_to_mid", 0),
                }
            except Exception as cons_err:
                results["consolidation"] = {"error": str(cons_err)}

        # 7. F190: Merge session corrections into domain_concept dossiers
        if closed_session_id:
            try:
                scripts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
                if scripts_dir not in sys.path:
                    sys.path.insert(0, os.path.abspath(scripts_dir))
                from knowledge_consolidation import consolidate_session
                kc_result = consolidate_session(conn, session_id=closed_session_id)
                results["dossier_consolidation"] = kc_result
            except Exception as kc_err:
                results["dossier_consolidation"] = {"error": str(kc_err)}

        knowledge_note = f", {results['knowledge_created']} knowledge entries created" if results.get("knowledge_created") else ""
        insights_note = f", {results['insights_extracted']} insights extracted" if results.get("insights_extracted") else ""
        consolidation_note = f", {results.get('consolidation', {}).get('promoted', 0)} facts promoted" if results.get("consolidation", {}).get("promoted") else ""
        dossier_note = f", {results.get('dossier_consolidation', {}).get('consolidated', 0)} corrections merged into dossiers" if results.get("dossier_consolidation", {}).get("consolidated") else ""
        results["summary"] = f"Session ended. {len(tasks_completed)} tasks logged, {len(next_steps)} next steps saved{knowledge_note}{insights_note}{consolidation_note}{dossier_note}."
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
                # Check if this is a stream (has child features) or regular feature (has tasks)
                cur.execute("""
                    SELECT feature_type FROM claude.features WHERE feature_id = %s::uuid
                """, (entity_id,))
                feat_row = cur.fetchone()
                if feat_row and feat_row['feature_type'] == 'stream':
                    # Stream: all child features must be completed or cancelled
                    cur.execute("""
                        SELECT COUNT(*) as remaining
                        FROM claude.features
                        WHERE parent_feature_id = %s::uuid
                          AND status NOT IN ('completed', 'cancelled')
                    """, (entity_id,))
                    row = cur.fetchone()
                    remaining = row['remaining']
                    if remaining > 0:
                        return (False, f"{remaining} child feature(s) still not completed")
                    return (True, "All child features completed")
                else:
                    # Regular feature: all build_tasks must be completed or cancelled
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

    def _check_dependencies(self, entity_uuid: str) -> tuple:
        """Check if all predecessors of a task are completed. Returns (passed, message)."""
        cur = self.conn.cursor()
        try:
            # Check both task_dependencies table AND legacy blocked_by_task_id
            cur.execute("""
                WITH blockers AS (
                    -- From task_dependencies table
                    SELECT td.predecessor_id as blocker_id, 'dependency' as source
                    FROM claude.task_dependencies td
                    WHERE td.successor_id = %s::uuid
                    UNION
                    -- From legacy blocked_by_task_id column
                    SELECT blocked_by_task_id as blocker_id, 'blocked_by' as source
                    FROM claude.build_tasks
                    WHERE task_id = %s::uuid AND blocked_by_task_id IS NOT NULL
                )
                SELECT b.blocker_id, 'BT' || bt.short_code as code, bt.task_name, bt.status
                FROM blockers b
                JOIN claude.build_tasks bt ON bt.task_id = b.blocker_id
                WHERE bt.status NOT IN ('completed', 'cancelled')
            """, (entity_uuid, entity_uuid))
            blockers = cur.fetchall()
            if blockers:
                blocker_list = [f"{b['code']} ({b['task_name']}: {b['status']})" for b in blockers]
                return (False, f"Blocked by: {', '.join(blocker_list)}")
            return (True, "All predecessors completed")
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
                           f.parent_feature_id::text as parent_id,
                           (SELECT COUNT(*) FROM claude.build_tasks bt
                            WHERE bt.feature_id = f.feature_id
                              AND bt.status NOT IN ('completed', 'cancelled')) as remaining
                    FROM claude.build_tasks bt
                    JOIN claude.features f ON bt.feature_id = f.feature_id
                    WHERE bt.task_id = %s::uuid
                """, (entity_id,))
                row = cur.fetchone()
                if row and row['remaining'] == 0 and row['status'] == 'in_progress':
                    msg = f"All tasks done for {row['code']}. Feature ready for completion."
                    # Also check if parent stream has all children done
                    if row.get('parent_id'):
                        cur.execute("""
                            SELECT 'F' || short_code as code,
                                   (SELECT COUNT(*) FROM claude.features
                                    WHERE parent_feature_id = %s::uuid
                                      AND status NOT IN ('completed', 'cancelled')) as remaining
                            FROM claude.features WHERE feature_id = %s::uuid
                        """, (row['parent_id'], row['parent_id']))
                        parent = cur.fetchone()
                        if parent and parent['remaining'] <= 1:  # <= 1 because current feature not yet completed
                            msg += f" Parent stream {parent['code']} may also be ready for completion."
                    return msg
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
        skip_conditions: bool = False,
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

            # 3. Check conditions (skipped if override_reason provided)
            if not skip_conditions:
                # 3a. Check workflow-defined conditions
                if transition.get('requires_condition'):
                    condition = transition['requires_condition']
                    passed, message = self.check_condition(condition, entity_type, entity_uuid)
                    result['condition_results'][condition] = {'passed': passed, 'message': message}
                    if not passed:
                        result['error'] = f"Condition '{condition}' not met: {message}"
                        return result

                # 3b. Check dependency prerequisites (for build_tasks moving to in_progress)
                if entity_type == 'build_tasks' and new_status == 'in_progress':
                    dep_passed, dep_msg = self._check_dependencies(entity_uuid)
                    result['condition_results']['dependencies'] = {'passed': dep_passed, 'message': dep_msg}
                    if not dep_passed:
                        result['error'] = f"Dependency check failed: {dep_msg}"
                        return result
            elif skip_conditions:
                result['condition_results']['skipped'] = {
                    'passed': True,
                    'message': f"Conditions skipped via override: {(metadata or {}).get('override_reason', 'no reason given')}",
                }

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
                event_type = (metadata or {}).get('event_type', 'status_change')
                cur.execute("""
                    INSERT INTO claude.audit_log
                    (entity_type, entity_id, entity_code, from_status, to_status,
                     changed_by, change_source, side_effects_executed, metadata, event_type)
                    VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    entity_type, entity_uuid, entity_code,
                    current_status, new_status,
                    changed_by, change_source,
                    [se['name'] for se in result['side_effects']] or None,
                    json.dumps(metadata) if metadata else None,
                    event_type,
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
    override_reason: str = "",
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
        override_reason: If provided, bypasses condition checks (deps, docs) and logs justification.
    """
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    conn = get_db_connection()
    try:
        engine = WorkflowEngine(conn)
        metadata = None
        if override_reason:
            metadata = {'override_reason': override_reason, 'event_type': 'override'}
        return engine.execute_transition(
            entity_type=item_type,
            item_id=item_id,
            new_status=new_status,
            changed_by=session_id,
            change_source='mcp_tool' if not override_reason else 'override',
            metadata=metadata,
            skip_conditions=bool(override_reason),
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
        cur = conn.cursor()

        # Transition to in_progress (WorkflowEngine._check_dependencies handles blocking)
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

        # Find next ready task from same feature (dependency-aware)
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
              AND NOT EXISTS (
                  SELECT 1 FROM claude.task_dependencies td
                  JOIN claude.build_tasks pred ON td.predecessor_id = pred.task_id
                  WHERE td.successor_id = bt2.task_id
                    AND pred.status NOT IN ('completed', 'cancelled')
              )
            ORDER BY bt2.step_order
            LIMIT 1
        """, (entity_id,))
        next_task = cur.fetchone()

        if next_task:
            transition_result['next_task'] = dict(next_task)
        else:
            transition_result['next_task'] = None
            # Check if all sibling tasks are done — feature may be ready for completion
            cur.execute("""
                SELECT f.feature_id::text, 'F' || f.short_code as code, f.feature_name, f.status,
                       (SELECT COUNT(*) FROM claude.build_tasks bt3
                        WHERE bt3.feature_id = f.feature_id
                          AND bt3.status NOT IN ('completed', 'cancelled')) as remaining
                FROM claude.build_tasks bt
                JOIN claude.features f ON bt.feature_id = f.feature_id
                WHERE bt.task_id = %s::uuid
            """, (entity_id,))
            feat = cur.fetchone()
            if feat and feat['remaining'] == 0 and feat['status'] == 'in_progress':
                transition_result['message'] = f"All tasks done! Feature {feat['code']} ({feat['feature_name']}) is ready for completion."
                transition_result['feature_ready'] = feat['code']
            else:
                transition_result['message'] = "No more ready tasks for this feature."

        return transition_result

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# Build Tracking Tools
# ============================================================================

@mcp.tool()
def get_build_board(
    project: str = "",
) -> dict:
    """Get the build board: streams → features → ready tasks with dependency resolution.

    One-call orientation for any Claude instance starting work on a project.
    Shows hierarchy (streams contain features, features contain tasks) with
    dependency-aware ready task identification.

    Use when: Starting a session, planning work, or checking project status.
    Returns: {project, streams: [{code, name, status, features: [{code, name,
              status, tasks_done, tasks_total, ready_tasks: [{code, name, type}]}]}],
              standalone_features: [...], summary}.

    Args:
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())
    project_id = get_project_id(project)
    if not project_id:
        return {"success": False, "error": f"Project '{project}' not found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get all active features with their hierarchy
        cur.execute("""
            WITH active_features AS (
                SELECT feature_id, 'F' || short_code as code, feature_name, status,
                       feature_type, parent_feature_id, priority,
                       (SELECT COUNT(*) FROM claude.build_tasks bt
                        WHERE bt.feature_id = f.feature_id AND bt.status = 'completed') as tasks_done,
                       (SELECT COUNT(*) FROM claude.build_tasks bt
                        WHERE bt.feature_id = f.feature_id) as tasks_total
                FROM claude.features f
                WHERE project_id = %s::uuid
                  AND status NOT IN ('completed', 'cancelled')
                ORDER BY priority, short_code
            )
            SELECT * FROM active_features
        """, (project_id,))
        features = [dict(r) for r in cur.fetchall()]

        # Get ready tasks (todo + all predecessors completed) with dependency awareness
        cur.execute("""
            SELECT bt.task_id, 'BT' || bt.short_code as code, bt.task_name, bt.task_type,
                   bt.feature_id, bt.step_order, bt.priority,
                   bt.blocked_by_task_id
            FROM claude.build_tasks bt
            WHERE bt.project_id = %s::uuid
              AND bt.status = 'todo'
              AND (bt.blocked_by_task_id IS NULL
                   OR bt.blocked_by_task_id IN (
                       SELECT task_id FROM claude.build_tasks WHERE status = 'completed'))
              AND NOT EXISTS (
                  SELECT 1 FROM claude.task_dependencies td
                  JOIN claude.build_tasks pred ON td.predecessor_id = pred.task_id
                  WHERE td.successor_id = bt.task_id
                    AND pred.status NOT IN ('completed', 'cancelled')
              )
            ORDER BY bt.priority, bt.step_order
        """, (project_id,))
        ready_tasks = [dict(r) for r in cur.fetchall()]

        # Build hierarchy
        streams = []
        standalone_features = []
        feature_map = {str(f['feature_id']): f for f in features}

        # Identify streams and their children
        for f in features:
            if f['feature_type'] == 'stream':
                stream = {
                    'code': f['code'],
                    'name': f['feature_name'],
                    'status': f['status'],
                    'priority': f['priority'],
                    'features': [],
                }
                # Find child features
                for child in features:
                    if child.get('parent_feature_id') and str(child['parent_feature_id']) == str(f['feature_id']):
                        child_ready = [
                            {'code': rt['code'], 'name': rt['task_name'], 'type': rt['task_type']}
                            for rt in ready_tasks if str(rt['feature_id']) == str(child['feature_id'])
                        ]
                        stream['features'].append({
                            'code': child['code'],
                            'name': child['feature_name'],
                            'status': child['status'],
                            'tasks_done': child['tasks_done'],
                            'tasks_total': child['tasks_total'],
                            'ready_tasks': child_ready,
                        })
                streams.append(stream)

        # Standalone features (not streams, not children of streams)
        stream_ids = {str(f['feature_id']) for f in features if f['feature_type'] == 'stream'}
        child_ids = {str(f['feature_id']) for f in features
                     if f.get('parent_feature_id') and str(f['parent_feature_id']) in stream_ids}

        for f in features:
            fid = str(f['feature_id'])
            if fid not in stream_ids and fid not in child_ids:
                f_ready = [
                    {'code': rt['code'], 'name': rt['task_name'], 'type': rt['task_type']}
                    for rt in ready_tasks if str(rt['feature_id']) == fid
                ]
                standalone_features.append({
                    'code': f['code'],
                    'name': f['feature_name'],
                    'status': f['status'],
                    'tasks_done': f['tasks_done'],
                    'tasks_total': f['tasks_total'],
                    'ready_tasks': f_ready,
                })

        # Summary
        total_ready = len(ready_tasks)
        total_features = len(features)
        total_streams = len(streams)

        return {
            'success': True,
            'project': project,
            'streams': streams,
            'standalone_features': standalone_features,
            'summary': {
                'total_streams': total_streams,
                'total_features': total_features,
                'total_ready_tasks': total_ready,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def add_dependency(
    predecessor_type: Literal["build_task", "feature"] = "build_task",
    predecessor_id: str = "",
    successor_type: Literal["build_task", "feature"] = "build_task",
    successor_id: str = "",
) -> dict:
    """Add a dependency: predecessor must complete before successor can start.

    Supports both task-to-task and feature-to-feature dependencies.
    Performs cycle detection before inserting — rejects circular dependencies.

    Use when: Establishing ordering between tasks or features.
    Returns: {success, dependency_id, predecessor, successor} or {success: false, error}.

    Args:
        predecessor_type: 'build_task' or 'feature'.
        predecessor_id: Short code (e.g., 'BT3', 'F5') or UUID of the predecessor.
        successor_type: 'build_task' or 'feature'.
        successor_id: Short code (e.g., 'BT4', 'F6') or UUID of the successor.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Resolve IDs
        def resolve_id(entity_type, item_id):
            if entity_type == 'build_task':
                prefix = 'BT'
                table = 'claude.build_tasks'
                pk = 'task_id'
                sc = 'short_code'
            else:
                prefix = 'F'
                table = 'claude.features'
                pk = 'feature_id'
                sc = 'short_code'

            # Try as short code first
            code = item_id.upper().replace(prefix, '')
            if code.isdigit():
                cur.execute(f"SELECT {pk}::text as id FROM {table} WHERE short_code = %s", (int(code),))
            else:
                cur.execute(f"SELECT {pk}::text as id FROM {table} WHERE {pk} = %s::uuid", (item_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"{entity_type} '{item_id}' not found")
            return row['id']

        pred_uuid = resolve_id(predecessor_type, predecessor_id)
        succ_uuid = resolve_id(successor_type, successor_id)

        if pred_uuid == succ_uuid:
            return {"success": False, "error": "Cannot depend on itself"}

        # Cycle detection: DFS from predecessor following existing deps backwards
        # If we can reach successor by walking predecessors of predecessor, it's a cycle
        cur.execute("""
            WITH RECURSIVE dep_chain AS (
                SELECT predecessor_id, successor_id, 1 as depth
                FROM claude.task_dependencies
                WHERE successor_id = %s::uuid
                UNION ALL
                SELECT td.predecessor_id, td.successor_id, dc.depth + 1
                FROM claude.task_dependencies td
                JOIN dep_chain dc ON td.successor_id = dc.predecessor_id
                WHERE dc.depth < 50
            )
            SELECT EXISTS(
                SELECT 1 FROM dep_chain WHERE predecessor_id = %s::uuid
            ) as has_cycle
        """, (pred_uuid, succ_uuid))
        if cur.fetchone()['has_cycle']:
            return {"success": False, "error": "Circular dependency detected — this would create a cycle"}

        # Insert dependency
        cur.execute("""
            INSERT INTO claude.task_dependencies (predecessor_type, predecessor_id, successor_type, successor_id, created_by)
            VALUES (%s, %s::uuid, %s, %s::uuid, %s)
            ON CONFLICT (predecessor_id, successor_id) DO NOTHING
            RETURNING dependency_id
        """, (predecessor_type, pred_uuid, successor_type, succ_uuid,
              os.environ.get('CLAUDE_SESSION_ID')))

        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "Dependency already exists"}

        # Log to audit_log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, entity_code, from_status, to_status,
             changed_by, change_source, event_type, metadata)
            VALUES ('task_dependencies', %s::uuid, %s, NULL, NULL,
                    %s, 'add_dependency', 'dependency_change',
                    %s)
        """, (succ_uuid, f"{successor_type}:{successor_id}",
              os.environ.get('CLAUDE_SESSION_ID'),
              json.dumps({'predecessor': f"{predecessor_type}:{predecessor_id}",
                         'successor': f"{successor_type}:{successor_id}"})))

        conn.commit()
        return {
            "success": True,
            "dependency_id": row['dependency_id'],
            "predecessor": f"{predecessor_type}:{predecessor_id}",
            "successor": f"{successor_type}:{successor_id}",
        }

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
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

        # Dedup check: reject if a non-cancelled task with same name exists for this feature
        cur.execute("""
            SELECT 'BT' || short_code as task_code, status
            FROM claude.build_tasks
            WHERE feature_id = %s::uuid AND task_name = %s AND status != 'cancelled'
        """, (feature['feature_id'], task_name))
        existing = cur.fetchone()
        if existing:
            return {
                "success": False,
                "error": f"Duplicate task: '{task_name}' already exists as {existing['task_code']} "
                         f"(status: {existing['status']}) for this feature. "
                         f"Use advance_status to update it instead of creating a new one."
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
        profile_row = cur.fetchone()
        profile_updated = profile_row is not None
        profile_id = profile_row['profile_id'] if profile_row else None

        # Create version snapshot in profile_versions
        version_created = False
        if profile_updated and profile_id:
            try:
                cur.execute("""
                    UPDATE claude.profiles SET current_version = current_version + 1
                    WHERE profile_id = %s::uuid
                    RETURNING current_version
                """, (profile_id,))
                new_version = cur.fetchone()['current_version']

                cur.execute("""
                    INSERT INTO claude.profile_versions
                    (version_id, profile_id, version, config, created_at, notes)
                    VALUES (
                        gen_random_uuid(),
                        %s::uuid,
                        %s,
                        (SELECT config FROM claude.profiles WHERE profile_id = %s::uuid),
                        NOW(),
                        %s
                    )
                """, (profile_id, new_version, profile_id,
                      f"Section '{section}' {mode}d via update_claude_md"))
                version_created = True
            except Exception as ve:
                logger.warning(f"Failed to create profile version: {ve}")

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

        # Template compliance check (2026-04-08)
        template_warning = None
        try:
            cur2 = conn.cursor()
            cur2.execute("""
                SELECT properties->'required_sections' as req
                FROM claude.entities
                WHERE entity_type = 'template'
                  AND properties->>'name' = 'claude-md-standard'
                  AND is_active = true LIMIT 1
            """)
            tmpl_row = cur2.fetchone()
            if tmpl_row and tmpl_row['req']:
                required = json.loads(tmpl_row['req']) if isinstance(tmpl_row['req'], str) else tmpl_row['req']
                if section not in required:
                    template_warning = f"Section '## {section}' is not in the standard template (claude-md-standard v1.0). Consider moving this content to vault, entities, or rules."
        except Exception:
            pass

        result = {
            "success": True,
            "section_name": section,
            "lines_changed": lines_changed,
            "file_path": str(claude_md_path),
            "mode": mode,
            "profile_updated": profile_updated,
            "version_created": version_created,
        }
        if template_warning:
            result["template_warning"] = template_warning
        return result

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

        # Validate against template (2026-04-08: template compliance check)
        template_warnings = []
        try:
            cur.execute("""
                SELECT properties FROM claude.entities
                WHERE entity_type = 'template'
                  AND properties->>'name' = 'claude-md-standard'
                  AND is_active = true
                LIMIT 1
            """)
            tmpl_row = cur.fetchone()
            if tmpl_row:
                tmpl = tmpl_row['properties']
                required = tmpl.get('required_sections', [])
                # Extract ## headers from the content being deployed
                import re as _re
                found_sections = [m.group(1) for m in _re.finditer(r'^## (.+)$', new_content, _re.MULTILINE)]
                missing = [s for s in required if s not in found_sections]
                if missing:
                    template_warnings = [f"Missing required section: ## {s}" for s in missing]
                # Check line count
                line_count = len(new_content.split('\n'))
                max_lines = tmpl.get('max_lines', 250)
                if line_count > max_lines:
                    template_warnings.append(f"CLAUDE.md is {line_count} lines (max: {max_lines})")
        except Exception:
            pass  # Template validation is advisory, don't block deploy

        conn.commit()

        # Write file AFTER successful DB commit
        with open(claude_md_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        result = {
            "success": True,
            "diff_summary": diff_summary,
            "file_path": str(claude_md_path),
        }
        if template_warnings:
            result["template_warnings"] = template_warnings
            result["template_version"] = "claude-md-standard v1.0"
        return result

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to deploy CLAUDE.md: {str(e)}"}
    finally:
        conn.close()


def _parse_skill_frontmatter(content: str) -> dict:
    """Parse YAML-like frontmatter from skill markdown content."""
    import re
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    frontmatter = {}
    # Fields that should always be treated as plain strings (never split on commas)
    string_fields = {'name', 'description', 'model'}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            if key in string_fields:
                frontmatter[key] = value
            elif value.startswith('[') or ',' in value:
                value = value.strip('[]')
                frontmatter[key] = [v.strip() for v in value.split(',') if v.strip()]
            else:
                frontmatter[key] = value
    return frontmatter


def _sync_skills_to_entities(cur, project_id: str | None = None) -> dict:
    """Sync skills from claude.skills to claude.entities for search/linking.

    Reads all active skills, parses frontmatter for descriptions, and upserts
    corresponding entities with embeddings. Skills remain as .md files for
    Claude Code; entities are the searchable/linkable representation.
    """
    # Get skill entity type
    cur.execute("""
        SELECT type_id::text, embedding_template, name_property, summary_template
        FROM claude.entity_types WHERE type_name = 'skill' AND is_active = TRUE
    """)
    type_row = cur.fetchone()
    if not type_row:
        return {"synced": 0, "error": "skill entity type not registered"}

    type_id = type_row['type_id']
    embedding_template = type_row['embedding_template']
    summary_template = type_row['summary_template']

    # Read all active skills
    cur.execute("""
        SELECT skill_id::text, name, content, scope, scope_ref
        FROM claude.skills WHERE is_active = true
    """)
    skills = cur.fetchall()

    created = 0
    updated = 0
    errors = []

    for skill in skills:
        try:
            fm = _parse_skill_frontmatter(skill['content'] or '')
            description = fm.get('description', '')
            allowed_tools_raw = fm.get('allowed-tools', [])
            if isinstance(allowed_tools_raw, str):
                allowed_tools_raw = [t.strip() for t in allowed_tools_raw.split(',') if t.strip()]

            properties = {
                "name": skill['name'],
                "description": description,
                "scope": skill['scope'],
                "allowed_tools": allowed_tools_raw,
                "skill_id": skill['skill_id'],
            }

            # Check for existing entity by name
            cur.execute("""
                SELECT entity_id::text FROM claude.entities
                WHERE entity_type_id = %s::uuid
                  AND properties->>'name' = %s
                  AND NOT is_archived
                LIMIT 1
            """, (type_id, skill['name']))
            existing = cur.fetchone()

            embed_text = _interpolate_template(embedding_template, properties)
            embedding = generate_embedding(embed_text)
            summary = _interpolate_template(summary_template or '', properties) if summary_template else None

            if existing:
                cur.execute("""
                    UPDATE claude.entities
                    SET properties = %s, tags = %s, embedding = %s::vector,
                        summary = %s, updated_at = NOW()
                    WHERE entity_id = %s::uuid
                """, (
                    json.dumps(properties),
                    [skill['scope']],
                    embedding,
                    summary,
                    existing['entity_id'],
                ))
                updated += 1
            else:
                cur.execute("""
                    INSERT INTO claude.entities (
                        entity_type_id, project_id, properties, tags,
                        embedding, summary, created_at, updated_at
                    ) VALUES (
                        %s::uuid, %s, %s, %s, %s::vector, %s, NOW(), NOW()
                    )
                """, (
                    type_id,
                    project_id,
                    json.dumps(properties),
                    [skill['scope']],
                    embedding,
                    summary,
                ))
                created += 1
        except Exception as e:
            errors.append(f"{skill['name']}: {str(e)}")

    return {"created": created, "updated": updated, "total": len(skills), "errors": errors}


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
    skills, instructions, claude_md, skill_entities. Omit components to deploy all.
    Returns: {success, project, deployed_components: [], changes_summary: []}.

    Args:
        project: Project name.
        components: List of components to deploy. Valid: 'settings', 'rules', 'skills',
                   'instructions', 'claude_md', 'skill_entities'. If None, deploys all.
    """
    valid_components = ['settings', 'rules', 'skills', 'instructions', 'claude_md', 'skill_entities']
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
            # Get project type for scope filtering
            cur.execute(
                "SELECT project_type FROM claude.workspaces WHERE project_id = %s::uuid",
                (project_id,),
            )
            pt_row = cur.fetchone()
            project_type = pt_row['project_type'] if pt_row else 'infrastructure'

            cur.execute("""
                SELECT name, content, scope
                FROM claude.skills
                WHERE is_active = true
                  AND (
                    scope = 'global'
                    OR (scope = 'project_type' AND scope_ref = %s)
                    OR (scope = 'project' AND (scope_ref = %s OR scope_ref = %s::text))
                  )
                  AND scope NOT IN ('command', 'agent')
            """, (project_type, project_name, project_id))
            skills = cur.fetchall()

            # Filter out global skills (they live in ~/.claude/skills/, deploying causes duplicates)
            project_skills = [s for s in skills if s['scope'] != 'global']

            if project_skills:
                skills_dir = project_path / ".claude" / "skills"
                skills_dir.mkdir(parents=True, exist_ok=True)

                for skill in project_skills:
                    skill_dir = skills_dir / skill['name']
                    skill_dir.mkdir(parents=True, exist_ok=True)
                    skill_file = skill_dir / "SKILL.md"
                    with open(skill_file, 'w', encoding='utf-8') as f:
                        f.write(skill['content'])

                deployed.append('skills')
                changes_summary.append(f"skills: {len(project_skills)} skills → {skills_dir}")
            else:
                changes_summary.append("skills: No project-scoped skills found")

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

        # Component: skill_entities (sync skills to entity catalog for search)
        if 'skill_entities' in components:
            try:
                sync_result = _sync_skills_to_entities(cur, project_id)
                deployed.append('skill_entities')
                changes_summary.append(
                    f"skill_entities: {sync_result.get('created', 0)} created, "
                    f"{sync_result.get('updated', 0)} updated of {sync_result.get('total', 0)} skills"
                )
                if sync_result.get('errors'):
                    changes_summary.append(f"  errors: {sync_result['errors'][:3]}")
            except Exception as e:
                changes_summary.append(f"skill_entities: failed - {str(e)}")

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


def _validate_config_content(content: str, component_type: str) -> str | None:
    """Scan config content for dangerous patterns. Returns error message if blocked, None if clean."""
    import re
    DANGEROUS_PATTERNS = [
        (r'(?i)ignore\s+(all\s+)?previous\s+instructions', 'Prompt injection attempt'),
        (r'(?i)(rm\s+-rf\s+/|del\s+/[sq]\s+|format\s+[a-z]:)', 'Destructive shell command'),
        (r'(?i)DROP\s+(TABLE|DATABASE|SCHEMA)\s+', 'Destructive SQL command'),
        (r'(?i)(sk-[a-zA-Z0-9]{20,}|password\s*[:=]\s*\S{8,})', 'Embedded secret/credential'),
        (r'(?i)disableAllHooks\s*:\s*true', 'Hook bypass attempt'),
    ]
    for pattern, desc in DANGEROUS_PATTERNS:
        match = re.search(pattern, content)
        if match:
            return f"Content blocked — {desc} (matched: '{match.group()[:40]}')"

    # Size limit: skills 500 lines, rules 150 lines, instructions 300 lines
    MAX_LINES = {"skill": 500, "rule": 150, "instruction": 300}
    limit = MAX_LINES.get(component_type, 500)
    line_count = content.count('\n') + 1
    if line_count > limit:
        return f"Content exceeds {limit}-line limit for {component_type} ({line_count} lines)"

    return None


def update_config(
    component_type: Literal["skill", "rule", "instruction", "claude_md"],
    project: str,
    component_name: str = "",
    content: str = "",
    change_reason: str = "",
    section: str = "",
    mode: Literal["replace", "append"] = "replace",
    scope: str = "",
    description: str = "",
) -> dict:
    """Create or update a deployable config component with versioning and filesystem deployment.

    Unified tool for managing skills, rules, instructions, and CLAUDE.md sections.
    If the component exists: creates version snapshot, updates content, deploys to file.
    If the component doesn't exist: creates it in the database and deploys to file.

    Use when: Creating or updating skills, rules, instructions, or CLAUDE.md from any project.
    Projects can self-serve config changes without messaging claude-family.
    Returns: {success, action: 'created'|'updated', component_type, component_name, version, file_path}.

    Args:
        component_type: What to manage: skill, rule, instruction, or claude_md.
        project: Project name (for scoping and file deployment).
        component_name: Name of the skill/rule/instruction. Not needed for claude_md.
        content: Content to write.
        change_reason: Why this change was made (stored in version history).
        section: For claude_md only — which section to update.
        mode: replace (default) or append. For claude_md, passed to update_claude_md logic.
        scope: For creating new components — 'global', 'project_type', 'project', 'command', 'agent'.
               If omitted for new skills, defaults to 'project'. Ignored for updates (keeps existing scope).
        description: For creating new components — optional description text.
    """
    # Delegate claude_md to existing tool
    if component_type == "claude_md":
        if not section:
            return {"success": False, "error": "section is required for claude_md updates"}
        return update_claude_md(project=project, section=section, content=content, mode=mode)

    if not component_name:
        return {"success": False, "error": "component_name is required for skill/rule/instruction updates"}
    if not content:
        return {"success": False, "error": "content is required"}

    # Content security validation (FB194)
    content_error = _validate_config_content(content, component_type)
    if content_error:
        return {"success": False, "error": content_error, "blocked_by": "content_validation"}

    # Scope permission check — only claude-family can create global components
    effective_scope = scope or ("project" if component_type == "skill" else "global")
    if effective_scope == "global" and project != "claude-family":
        return {"success": False, "error": f"Only claude-family can create global-scoped {component_type}s. Use scope='project' for project-scoped components."}

    # Map component_type to table/column/version_table/deploy_path
    CONFIG_MAP = {
        "skill": {
            "table": "claude.skills",
            "id_col": "skill_id",
            "name_col": "name",
            "version_table": "claude.skills_versions",
            "version_fk": "skill_id",
        },
        "rule": {
            "table": "claude.rules",
            "id_col": "rule_id",
            "name_col": "name",
            "version_table": "claude.rules_versions",
            "version_fk": "rule_id",
        },
        "instruction": {
            "table": "claude.instructions",
            "id_col": "instruction_id",
            "name_col": "name",
            "version_table": "claude.instructions_versions",
            "version_fk": "instruction_id",
        },
    }

    cfg = CONFIG_MAP[component_type]
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Step 1: Find the component (or create it)
        # Scope-aware lookup: if scope provided, filter by it; otherwise check for ambiguity
        if scope:
            cur.execute(
                f"SELECT {cfg['id_col']}::text, content, scope FROM {cfg['table']} "
                f"WHERE LOWER({cfg['name_col']}) = LOWER(%s) AND scope = %s AND is_active = true",
                (component_name, scope),
            )
            row = cur.fetchone()
        else:
            cur.execute(
                f"SELECT {cfg['id_col']}::text, content, scope FROM {cfg['table']} "
                f"WHERE LOWER({cfg['name_col']}) = LOWER(%s) AND is_active = true",
                (component_name,),
            )
            rows = cur.fetchall()
            if len(rows) > 1:
                scopes = [r['scope'] for r in rows]
                return {
                    "success": False,
                    "error": f"Ambiguous: '{component_name}' exists in multiple scopes: {scopes}. "
                             f"Specify scope parameter to disambiguate.",
                    "matching_scopes": scopes,
                }
            row = rows[0] if rows else None
        is_create = row is None

        if is_create:
            # CREATE path — insert new component
            effective_scope = scope or ("project" if component_type == "skill" else "global")

            # Resolve scope_ref for project-scoped components
            scope_ref = None
            if effective_scope == "project":
                cur.execute(
                    "SELECT project_id::text FROM claude.projects WHERE LOWER(project_name) = LOWER(%s)",
                    (project,),
                )
                proj_row = cur.fetchone()
                if proj_row:
                    scope_ref = proj_row['project_id']
            elif effective_scope == "project_type":
                scope_ref = project  # project_type string

            # Build INSERT — columns vary by table but all have name, content, scope, is_active
            if component_type == "skill":
                cur.execute(
                    "INSERT INTO claude.skills (name, scope, scope_ref, content, description, is_active) "
                    "VALUES (%s, %s, %s, %s, %s, true) RETURNING skill_id::text",
                    (component_name, effective_scope, scope_ref, content, description or None),
                )
            elif component_type == "rule":
                cur.execute(
                    "INSERT INTO claude.rules (name, scope, scope_ref, content, description, is_active) "
                    "VALUES (%s, %s, %s, %s, %s, true) RETURNING rule_id::text",
                    (component_name, effective_scope, scope_ref, content, description or None),
                )
            elif component_type == "instruction":
                cur.execute(
                    "INSERT INTO claude.instructions (name, scope, scope_ref, content, description, is_active) "
                    "VALUES (%s, %s, %s, %s, %s, true) RETURNING instruction_id::text",
                    (component_name, effective_scope, scope_ref, content, description or None),
                )

            component_id = cur.fetchone()[cfg['id_col']]
            old_content = ""
            final_scope = effective_scope
            next_version = 1
        else:
            # UPDATE path — existing component
            component_id = row[cfg['id_col']]
            old_content = row['content'] or ""
            final_scope = row['scope']

            # Version — create snapshot of old content
            cur.execute(
                f"SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver "
                f"FROM {cfg['version_table']} WHERE {cfg['version_fk']} = %s::uuid",
                (component_id,),
            )
            next_version = cur.fetchone()['next_ver']

            cur.execute(
                f"INSERT INTO {cfg['version_table']} "
                f"(version_id, {cfg['version_fk']}, version_number, content, changed_by, change_reason, created_at) "
                f"VALUES (gen_random_uuid(), %s::uuid, %s, %s, 'update_config', %s, NOW())",
                (component_id, next_version, old_content, change_reason or "Updated via update_config"),
            )

            # Update content + version
            final_content = content if mode == "replace" else (old_content + "\n" + content)
            cur.execute(
                f"UPDATE {cfg['table']} SET content = %s, version = %s, updated_at = NOW() "
                f"WHERE {cfg['id_col']} = %s::uuid",
                (final_content, next_version, component_id),
            )
            content = final_content  # Use merged content for file deploy

        # Deploy — write to filesystem
        cur.execute(
            "SELECT project_path FROM claude.workspaces WHERE LOWER(project_name) = LOWER(%s)",
            (project,),
        )
        ws_row = cur.fetchone()
        project_path = ws_row['project_path'] if ws_row else os.getcwd()

        # Determine deploy path based on scope
        if component_type == "skill":
            if final_scope == "command":
                deploy_path = os.path.join(project_path, ".claude", "commands", f"{component_name}.md")
            elif final_scope == "agent":
                deploy_path = os.path.join(project_path, ".claude", "agents", f"{component_name}.md")
            else:
                deploy_dir = os.path.join(project_path, ".claude", "skills", component_name)
                os.makedirs(deploy_dir, exist_ok=True)
                deploy_path = os.path.join(deploy_dir, "SKILL.md")
        elif component_type == "rule":
            deploy_path = os.path.join(project_path, ".claude", "rules", f"{component_name}.md")
        elif component_type == "instruction":
            deploy_path = os.path.join(project_path, ".claude", "instructions", f"{component_name}.instructions.md")

        os.makedirs(os.path.dirname(deploy_path), exist_ok=True)
        with open(deploy_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Audit
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, entity_code, change_source, from_status, to_status)
            VALUES (%s, %s::uuid, %s, 'update_config', %s, %s)
        """, (
            cfg['table'].split('.')[1],
            component_id,
            component_name,
            "new" if is_create else (f"v{next_version - 1}" if next_version > 1 else "initial"),
            f"v{next_version}",
        ))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "action": "created" if is_create else "updated",
            "component_type": component_type,
            "component_name": component_name,
            "scope": final_scope,
            "version": next_version,
            "file_path": deploy_path,
            "change_reason": change_reason,
        }

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return {"success": False, "error": str(e)}


# ============================================================================
# Import existing tools from server.py for backward compatibility
# ============================================================================

# Load .env file BEFORE importing server.py (which captures VOYAGE_API_KEY at import time)
# Encapsulation: the MCP server loads its own config. Callers don't pass credentials.
_env_file = os.path.normpath(os.path.expanduser('~/OneDrive/Documents/AI_projects/ai-workspace/.env'))
if os.path.exists(_env_file):
    with open(_env_file, 'r') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _value = _line.split('=', 1)
                _key, _value = _key.strip(), _value.strip()
                _existing = os.environ.get(_key, '')
                # Force-set if missing or if caller passed unexpanded ${} placeholder
                if not _existing or _existing.startswith('${'):
                    os.environ[_key] = _value

    # Build DATABASE_URI from individual POSTGRES_* vars if not already set
    if not os.environ.get('DATABASE_URI') and os.environ.get('POSTGRES_PASSWORD'):
        os.environ['DATABASE_URI'] = (
            f"postgresql://{os.environ.get('POSTGRES_USER', 'postgres')}"
            f":{os.environ['POSTGRES_PASSWORD']}"
            f"@{os.environ.get('POSTGRES_HOST', 'localhost')}"
            f"/{os.environ.get('POSTGRES_DATABASE', 'ai_company_foundation')}"
        )

# Import the old server module to get access to all existing tool implementations
_old_server_dir = os.path.dirname(os.path.abspath(__file__))
if _old_server_dir not in sys.path:
    sys.path.insert(0, _old_server_dir)

# We import the tool implementations (not the MCP app) from the old server
from server import (  # noqa: E402
    tool_get_incomplete_todos,
    tool_create_feedback,
    tool_create_feature,
    tool_add_build_task,
    tool_get_ready_tasks,
    tool_update_work_status,
    tool_store_knowledge,
    tool_recall_knowledge,
    tool_graph_search,
    tool_decay_knowledge,
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
    tool_recall_memories,
    tool_remember,
    tool_consolidate_memories,
    tool_list_memories,
    tool_update_memory,
    tool_archive_memory,
    tool_merge_memories,
    tool_archive_workfile,
    tool_delete_workfile,
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
    feature_type: Literal["feature", "enhancement", "refactor", "infrastructure", "documentation", "stream"] = "feature",
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


def update_work_status(
    item_type: Literal["feedback", "feature", "build_task"],
    item_id: str,
    new_status: str,
) -> dict:
    """DEPRECATED: Use advance_status() instead (same behavior, consistent naming).

    Update status of a feedback, feature, or build_task.
    Routes through WorkflowEngine. For build tasks, prefer start_work()/complete_work().
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




# LEGACY - F130 cognitive memory is preferred
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
    """LEGACY: Prefer remember() which auto-routes to the correct tier with dedup/merge.

    Store new knowledge with automatic embedding for semantic search.

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


# LEGACY - F130 cognitive memory is preferred
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
    """LEGACY: Prefer recall_memories() which searches all 3 tiers with budget-capped results.

    Semantic search over knowledge entries with structured filters.

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


# LEGACY - F130 cognitive memory is preferred
def graph_search(
    query: str,
    max_initial_hits: int = 5,
    max_hops: int = 2,
    min_edge_strength: float = 0.3,
    min_similarity: float = 0.5,
    token_budget: int = 500,
) -> dict:
    """LEGACY: Prefer recall_memories() for most use cases. Use graph_search only when you need explicit relationship traversal.

    Graph-aware knowledge search: pgvector similarity + relationship graph walk.

    Finds knowledge via semantic similarity, then walks the knowledge_relations
    graph to discover connected entries up to max_hops away. Returns both direct
    hits and graph-discovered entries, ranked by composite relevance score.

    Use when: You need richer context than recall_knowledge provides. This finds
    not just similar entries but also related knowledge connected via typed
    relationships (extends, contradicts, supports, etc.).
    Returns: {query, result_count, direct_hits, graph_discovered, results:
              [{knowledge_id, title, knowledge_type, description, source_type,
              similarity, graph_depth, edge_path, relevance_score}]}.

    Args:
        query: Natural language search query.
        max_initial_hits: Max pgvector seed results (default: 5).
        max_hops: Max relationship hops from seed nodes (default: 2).
        min_edge_strength: Minimum edge strength to traverse (default: 0.3).
        min_similarity: Minimum pgvector similarity for seeds (default: 0.5).
        token_budget: Approximate token budget for results (default: 500).
    """
    return _run_async(tool_graph_search(
        query, max_initial_hits, max_hops,
        min_edge_strength, min_similarity, token_budget,
    ))


@mcp.tool()
def decay_knowledge(
    min_strength: float = 0.05,
    stale_days: int = 90,
) -> dict:
    """Apply decay to knowledge graph edges and find stale subgraphs.

    Reduces edge strength over time based on access patterns. Knowledge that
    hasn't been accessed loses edge strength gradually (0.95^days formula).
    Also identifies stale knowledge entries (not accessed + low confidence).

    Use when: Running periodic maintenance on the knowledge graph. Call this
    during maintenance cycles to keep the graph healthy and identify knowledge
    that should be reviewed or archived.
    Returns: {success, decayed_edges, stale_entries, stale_knowledge_ids, message}.

    Args:
        min_strength: Floor for edge strength decay (default: 0.05).
        stale_days: Days without access to consider knowledge stale (default: 90).
    """
    return _run_async(tool_decay_knowledge(min_strength, stale_days))


# ============================================================================
# Cognitive Memory Tools (F130)
# ============================================================================

@mcp.tool()
def recall_memories(
    query: str,
    budget: int = 1000,
    query_type: Literal["default", "task_specific", "exploration"] = "default",
    project_name: str = "",
) -> dict:
    """Retrieve memories from all 3 tiers (short/mid/long) in a single call, budget-capped.

    Queries SHORT (session facts), MID (working knowledge), and LONG (proven
    knowledge + graph relations) tiers. Budget-capped at ~1000 tokens with
    diversity guarantee (1+ per tier if available). Use query_type to shift
    budget allocation between tiers.

    Use when: You need contextual memories before starting work, making decisions,
    or solving problems. This replaces separate calls to recall_knowledge,
    list_session_facts, and graph_search with a single encapsulated operation.
    Returns: {query, total_budget, token_count, memory_count, tier_counts,
              memories: [{tier, title, content, memory_type, score}]}.

    Args:
        query: Natural language query describing what you need to remember.
        budget: Token budget cap (default: 1000). Memories are filled greedily by score.
        query_type: Budget profile - 'task_specific' (40% short, 40% mid, 20% long),
                    'exploration' (10% short, 30% mid, 60% long),
                    'default' (20% short, 40% mid, 40% long).
        project_name: Project name (default: current directory).
    """
    return _run_async(tool_recall_memories(
        query, budget,
        query_type,
        project_name or None,
    ))


@mcp.tool()
def remember(
    content: str,
    context: str = "",
    memory_type: Literal["learned", "pattern", "gotcha", "preference", "fact", "procedure",
                          "credential", "config", "endpoint", "decision", "note", "data"] = "learned",
    tier_hint: Literal["auto", "short", "mid", "long"] = "auto",
    project_name: str = "",
) -> dict:
    """Store a memory with automatic tier classification, dedup/merge, and relation linking.

    Routes to the right storage: credentials/configs/endpoints → session_facts (short tier),
    learned/facts/decisions → knowledge table (mid tier), patterns/procedures/gotchas →
    knowledge table (long tier). Automatically deduplicates (merges if >75% similar),
    detects contradictions, and creates relation links to nearby knowledge.

    Use when: You learn something worth remembering. Call this instead of separate
    store_knowledge / store_session_fact — it auto-routes to the right place.
    Quality gate: rejects content < 80 chars or junk patterns (task acks, agent handoffs).
    Returns: {success, memory_id, tier, action: 'created'|'merged'|'contradiction_flagged',
              relations_created}.

    Args:
        content: The memory content to store.
        context: Optional context about when/why this memory was captured.
        memory_type: Type of memory (determines auto tier routing).
        tier_hint: Override auto tier classification ('auto' uses memory_type rules).
        project_name: Project name (default: current directory).
    """
    return _run_async(tool_remember(
        content, context, memory_type,
        tier_hint,
        project_name or None,
    ))


@mcp.tool()
def consolidate_memories(
    trigger: Literal["session_end", "periodic", "manual"] = "session_end",
    project_name: str = "",
) -> dict:
    """Run memory lifecycle management: promote, decay, and archive.

    Three trigger modes control which phases run:
    - session_end: Phase 1 only — promotes qualifying session facts (short→mid).
    - periodic: Phase 2+3 — promotes proven mid→long, decays edges, archives stale.
    - manual: Full cycle — all phases.

    Use when: At session end (auto-called), periodically for maintenance, or
    manually to force a full lifecycle pass.
    Returns: {trigger, promoted_short_to_mid, promoted_mid_to_long,
              decayed_edges, archived}.

    Args:
        trigger: Which phases to run.
        project_name: Project name (default: current directory).
    """
    return _run_async(tool_consolidate_memories(
        trigger,
        project_name or None,
    ))


@mcp.tool()
def list_memories(
    project: str = "",
    tier: str = "",
    memory_type: str = "",
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Browse stored memories with filters. Returns metadata, not full content.

    Use when: Auditing what memories exist for a project, finding duplicates,
    or reviewing what knowledge is stored before cleanup.
    Returns: {success, project, total_count, memories: [{knowledge_id, title,
              tier, memory_type, confidence, status, created_at, last_accessed_at,
              description_preview}]}.

    Args:
        project: Project name. Defaults to current directory.
        tier: Filter by tier: 'mid' or 'long'. Empty = all.
        memory_type: Filter by type (learned, pattern, gotcha, etc). Empty = all.
        include_archived: If True, include archived memories. Default False.
        limit: Max results (default 50, max 200).
        offset: Skip first N results for pagination.
    """
    return _run_async(tool_list_memories(project or None, tier, memory_type, include_archived, min(limit, 200), offset))


@mcp.tool()
def update_memory(
    memory_id: str,
    content: str = "",
    title: str = "",
    tier: str = "",
    memory_type: str = "",
) -> dict:
    """Update an existing memory's content, title, tier, or type. Re-embeds if content changes.

    Use when: Fixing incorrect information in a stored memory, updating stale
    content, or reclassifying a memory's tier or type.
    Returns: {success, memory_id, updated_fields, re_embedded}.

    Args:
        memory_id: UUID of the memory to update.
        content: New description/content. If provided, re-embeds.
        title: New title. Empty = no change.
        tier: New tier ('mid' or 'long'). Empty = no change.
        memory_type: New type. Empty = no change.
    """
    return _run_async(tool_update_memory(memory_id, content, title, tier, memory_type))


@mcp.tool()
def archive_memory(
    memory_id: str,
    reason: str = "",
) -> dict:
    """Soft-delete a memory by setting status to 'archived'. Excluded from recall by default.

    Use when: A memory is wrong, outdated, or superseded. Archived memories
    are not permanently deleted — the background curator handles purging.
    Returns: {success, memory_id, title, previous_status, reason}.

    Args:
        memory_id: UUID of the memory to archive.
        reason: Why this memory is being archived (stored for audit trail).
    """
    return _run_async(tool_archive_memory(memory_id, reason))


@mcp.tool()
def merge_memories(
    keep_id: str,
    archive_id: str,
    reason: str = "",
) -> dict:
    """Merge two memories: keep the better one, archive the other, preserve relations.

    Use when: Two memories contain overlapping or duplicate information.
    The kept memory's content is unchanged. The archived memory's relations
    are transferred to the kept memory before archiving.
    Returns: {success, kept_id, archived_id, relations_transferred}.

    Args:
        keep_id: UUID of the memory to keep.
        archive_id: UUID of the memory to archive (the duplicate/weaker one).
        reason: Why these are being merged.
    """
    return _run_async(tool_merge_memories(keep_id, archive_id, reason))


@mcp.tool()
def archive_workfile(
    component: str,
    title: str,
    project: str = "",
) -> dict:
    """Mark a workfile as inactive (soft-delete). Excluded from unstash by default.

    Use when: A workfile is stale, superseded, or no longer relevant.
    The file remains in DB but is_active=False hides it from normal queries.
    Returns: {success, component, title, previous_state}.

    Args:
        component: Component/drawer name.
        title: Workfile title within component.
        project: Project name. Defaults to current directory.
    """
    return _run_async(tool_archive_workfile(component, title, project or None))


@mcp.tool()
def delete_workfile(
    component: str,
    title: str,
    project: str = "",
) -> dict:
    """Permanently delete a workfile. Cannot be undone.

    Use when: A workfile should be completely removed (not just archived).
    Prefer archive_workfile for most cases — only hard-delete when the
    content is genuinely wrong or harmful.
    Returns: {success, component, title, deleted}.

    Args:
        component: Component/drawer name.
        title: Workfile title within component.
        project: Project name. Defaults to current directory.
    """
    return _run_async(tool_delete_workfile(component, title, project or None))


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


def _parse_bpmn_header_comments(file_path: str) -> dict:
    """Parse deployment_target and model_version from BPMN XML header comments.

    Looks for comments like:
        <!-- Deployment: claude-family (Windows local) -->
        <!-- Version: 1.0 -->

    Returns dict with 'deployment_target' and 'model_version' (with defaults).
    """
    deployment_target = "all"
    model_version = "1.0"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Only scan the first 2KB for header comments
            header = f.read(2048)
        # Parse deployment comment
        deploy_match = re.search(r"<!--\s*Deployment:\s*(.+?)\s*-->", header)
        if deploy_match:
            raw = deploy_match.group(1).strip().lower()
            if any(kw in raw for kw in ("claude-family", "windows local")):
                deployment_target = "claude-family-local"
            elif any(kw in raw for kw in ("metis", "linux")):
                deployment_target = "metis-linux"
            else:
                deployment_target = "all"
        # Parse version comment
        version_match = re.search(r"<!--\s*Version:\s*(.+?)\s*-->", header)
        if version_match:
            model_version = version_match.group(1).strip()
    except Exception:
        pass  # Return defaults on any read error
    return {"deployment_target": deployment_target, "model_version": model_version}


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

        # Parse deployment_target and model_version from header comments
        header_meta = _parse_bpmn_header_comments(file_path)

        return {
            "process_id": process_id,
            "process_name": process_name,
            "level": level,
            "category": category,
            "description": description,
            "elements": elements,
            "flows": flows,
            "deployment_target": header_meta["deployment_target"],
            "model_version": header_meta["model_version"],
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
                     deployment_target, model_version,
                     created_by_session, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
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
                    deployment_target = EXCLUDED.deployment_target,
                    model_version = EXCLUDED.model_version,
                    created_by_session = COALESCE(claude.bpmn_processes.created_by_session, EXCLUDED.created_by_session),
                    updated_at = NOW()
            """, (
                pid, project, rel_path, parsed["process_name"],
                parsed["level"], parsed["category"], parsed["description"],
                json.dumps(parsed["elements"]), json.dumps(parsed["flows"]),
                file_hash,
                str(embedding) if embedding else None,
                parsed["deployment_target"], parsed["model_version"],
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
# System Maintenance
# ============================================================================


@mcp.tool()
def system_maintenance(
    scope: str = "full",
    auto_repair: bool = True,
) -> dict:
    """Run system maintenance: detect and repair staleness across 5 subsystems.

    Implements the system_maintenance BPMN process. Detects staleness in schema registry,
    vault embeddings, BPMN registry, memory embeddings, and column registry. Optionally
    repairs stale subsystems.

    Args:
        scope: What to maintain. Options:
            - "full": All 5 subsystems (default)
            - "detect_only": Detection only, no repairs
            - "schema": Schema registry + embeddings only
            - "vault": Vault document embeddings only
            - "bpmn": BPMN process registry only
            - "memory": Knowledge memory embeddings only
            - "column_registry": Column constraint registry only
        auto_repair: If True, repair stale subsystems. If False, detect only.

    Returns dict with:
        - detection: Per-subsystem staleness results
        - repairs: Per-subsystem repair results (empty if detect_only)
        - summary: Human-readable report
        - any_stale: Whether any staleness was detected
        - any_repaired: Whether any repairs were performed
    """
    import importlib.util
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    spec = importlib.util.spec_from_file_location("system_maintenance_mod", os.path.join(scripts_dir, "system_maintenance.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_maintenance(scope=scope, auto_repair=auto_repair)


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

    WARNING: CORE_PROTOCOL is injected on EVERY prompt for EVERY Claude instance.
    Changes here have system-wide blast radius. Test content carefully before updating.

    Use when: Changing the CORE_PROTOCOL or other injected protocols.
    Creates a new version in claude.protocol_versions, sets it active,
    and deploys to scripts/core_protocol.txt for runtime use.
    Use get_protocol_history() to review previous versions before making changes.
    Returns: {success, protocol_name, old_version, new_version, deployed}.

    Args:
        content: The full new protocol text.
        change_reason: Why this change was made (for audit trail).
        protocol_name: Protocol to update (default: CORE_PROTOCOL).
    """
    conn = get_db_connection()
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
    conn = get_db_connection()
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
    conn = get_db_connection()
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
# Standing Orders Tool
# ============================================================================

STANDING_ORDERS_PROTOCOL = "STANDING_ORDERS"
STANDING_ORDERS_SECTION = "## Standing Orders"


@mcp.tool()
def standing_orders(
    action: str,
    content: str = "",
    change_reason: str = "",
) -> dict:
    """Manage standing orders — persistent behavioral reinforcements deployed to MEMORY.md.

    Standing orders are DB-versioned rules that get deployed to each project's
    auto-memory MEMORY.md file at session start. They reinforce key behaviors
    (storage routing, task decomposition, etc.) in a high-visibility location.

    Use when: Viewing, updating, or deploying standing orders.
    Returns: {success, content, version} for get; {success, new_version} for update;
             {success, versions} for history; {success, deployed_to} for deploy.

    Args:
        action: get, update, history, or deploy.
        content: New standing orders text (required for update).
        change_reason: Why this change was made (required for update).
    """
    if action == "get":
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT version, content, change_reason, changed_by, created_at::text
                FROM claude.protocol_versions
                WHERE protocol_name = %s AND is_active = true
            """, (STANDING_ORDERS_PROTOCOL,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": f"No active version for {STANDING_ORDERS_PROTOCOL}"}
            return {
                "success": True,
                "protocol_name": STANDING_ORDERS_PROTOCOL,
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

    elif action == "update":
        if not content:
            return {"success": False, "error": "content is required for update action"}
        if not change_reason:
            return {"success": False, "error": "change_reason is required for update action"}

        conn = get_db_connection()
        try:
            cur = conn.cursor()

            # Get current active version
            cur.execute("""
                SELECT version_id, version FROM claude.protocol_versions
                WHERE protocol_name = %s AND is_active = true
            """, (STANDING_ORDERS_PROTOCOL,))
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
            """, (STANDING_ORDERS_PROTOCOL, new_version, content.strip(), change_reason,
                  f"session:{os.environ.get('SESSION_ID', 'unknown')}"))

            new_id = cur.fetchone()["version_id"]
            conn.commit()

            return {
                "success": True,
                "protocol_name": STANDING_ORDERS_PROTOCOL,
                "old_version": old_version,
                "new_version": new_version,
                "version_id": new_id,
                "note": "Standing orders updated in DB. Run deploy action to push to MEMORY.md files.",
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    elif action == "history":
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT version, content, change_reason, changed_by,
                       created_at::text, is_active
                FROM claude.protocol_versions
                WHERE protocol_name = %s
                ORDER BY version DESC
                LIMIT 10
            """, (STANDING_ORDERS_PROTOCOL,))

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
                "protocol_name": STANDING_ORDERS_PROTOCOL,
                "version_count": len(versions),
                "versions": versions,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    elif action == "deploy":
        # Step 1: Get active standing orders from DB
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT version, content
                FROM claude.protocol_versions
                WHERE protocol_name = %s AND is_active = true
            """, (STANDING_ORDERS_PROTOCOL,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": f"No active version for {STANDING_ORDERS_PROTOCOL} — create one with action='update' first"}
            active_version = row["version"]
            active_content = row["content"].strip()
        except Exception as e:
            return {"success": False, "error": f"DB error: {str(e)}"}
        finally:
            conn.close()

        # Step 2: Determine MEMORY.md path from CWD
        cwd = os.getcwd()
        # Encode path: replace drive colon+backslash and remaining separators with --
        # e.g. C:\Projects\claude-family -> C--Projects--claude-family
        encoded = cwd.replace(":\\", "--").replace("\\", "--").replace("/", "--")
        memory_dir = Path.home() / ".claude" / "projects" / encoded / "memory"
        memory_path = memory_dir / "MEMORY.md"

        # Step 3: Read existing MEMORY.md (or start with empty string)
        if memory_path.exists():
            existing = memory_path.read_text(encoding="utf-8")
        else:
            existing = ""
            # Ensure directory exists
            memory_dir.mkdir(parents=True, exist_ok=True)

        # Step 4: Build new standing orders block
        section_block = f"{STANDING_ORDERS_SECTION}\n\n{active_content}\n"

        # Step 5: Replace or prepend the standing orders section
        if STANDING_ORDERS_SECTION in existing:
            # Find start of section
            start_idx = existing.index(STANDING_ORDERS_SECTION)
            # Find end of section: next ## heading after the section header, or end of file
            after_header = existing[start_idx + len(STANDING_ORDERS_SECTION):]
            # Search for the next ## heading
            import re
            next_heading = re.search(r'\n##\s', after_header)
            if next_heading:
                end_idx = start_idx + len(STANDING_ORDERS_SECTION) + next_heading.start()
                # Preserve everything before the section, insert new block, then rest
                new_content = existing[:start_idx] + section_block + "\n" + existing[end_idx:].lstrip("\n")
            else:
                # Standing orders is the last section — replace to end of file
                new_content = existing[:start_idx] + section_block
        else:
            # Prepend at top, separated from existing content by a blank line
            if existing:
                new_content = section_block + "\n" + existing
            else:
                new_content = section_block

        # Step 6: Write back
        memory_path.write_text(new_content, encoding="utf-8")

        return {
            "success": True,
            "deployed_to": str(memory_path),
            "version": active_version,
            "section_existed": STANDING_ORDERS_SECTION in existing,
        }

    else:
        return {"success": False, "error": f"Unknown action '{action}'. Valid actions: get, update, history, deploy"}


# ============================================================================
# Channel Messaging Status Tool
# ============================================================================


def _try_capture_session():
    """Try to capture the MCP session for the background channel listener.

    Called from within tool handlers (where request_ctx is set).
    Only needs to succeed once — the session is the same for the entire
    stdio transport lifetime.
    """
    if _channel.session is not None:
        return True
    try:
        ctx = mcp._mcp_server.request_context
        _channel.session = ctx.session
        return True
    except (LookupError, AttributeError):
        return False


@mcp.tool()
def channel_status() -> dict:
    """Check the real-time messaging channel connection status.

    Use when: Checking if real-time push notifications are working.
    Also captures the MCP session for the background listener (needed on first call).
    Returns: {connected, project, listening_channels, session_captured}.
    """
    session_captured = _try_capture_session()

    return {
        "connected": _channel.connected,
        "project": _channel.project_name,
        "listening_channels": _channel.listening_channels,
        "session_captured": session_captured,
    }


# ============================================================================
# Messaging Tools (migrated from orchestrator MCP)
# ============================================================================


@mcp.tool()
def list_recipients() -> dict:
    """List all valid messaging recipients (projects with active workspaces).

    Use when: Discovering who you can send messages to. Shows project names,
    display names, client domains, and when each project was last active.
    Returns: {count, recipients: [{project_name, description, client_domain, last_session}]}.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                w.project_name,
                COALESCE(p.description, w.project_name) as description,
                p.client_domain,
                (SELECT MAX(s.created_at)
                 FROM claude.sessions s
                 WHERE s.project_name = w.project_name) as last_session
            FROM claude.workspaces w
            LEFT JOIN claude.projects p ON p.project_name = w.project_name
            WHERE w.is_active = true
            ORDER BY last_session DESC NULLS LAST
        """)
        rows = cur.fetchall()
        cur.close()

        recipients = []
        for row in rows:
            row_dict = dict(row) if not isinstance(row, dict) else row
            if row_dict.get('last_session'):
                row_dict['last_session'] = row_dict['last_session'].isoformat()
            recipients.append(row_dict)

        return {"count": len(recipients), "recipients": recipients}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def check_inbox(
    project_name: str = "",
    session_id: str = "",
    include_broadcasts: bool = True,
    include_read: bool = False,
) -> dict:
    """Check for pending messages from other Claude instances. Returns unread messages addressed to you or broadcast to all. IMPORTANT: Pass project_name to see project-targeted messages!

    Use when: Checking for messages from other Claude instances at session start
    or periodically during work. For actionable messages only (task_request/question/handoff),
    use get_unactioned_messages() instead.
    Returns: {count, messages: [{message_id, from_session_id, from_project, to_project, message_type,
              priority, subject, body, metadata, status, created_at, parent_message_id, thread_id}]}.

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
                from_project,
                to_project,
                message_type,
                priority,
                subject,
                body,
                metadata,
                status,
                created_at,
                parent_message_id::text,
                thread_id::text
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


VALID_CONVERSATION_MODES = [
    "fire_and_forget",
    "question",
    "collaborative",
    "task_handoff",
    "review_request",
]


@mcp.tool()
def send_message(
    message_type: Literal["task_request", "status_update", "question", "notification", "handoff", "broadcast"],
    body: str,
    subject: str = "",
    to_project: str = "",
    to_session_id: str = "",
    priority: Literal["urgent", "normal", "low"] = "normal",
    from_session_id: str = "",
    from_project: str = "",
    parent_message_id: str = "",
    metadata: Optional[dict] = None,
    conversation_mode: str = "fire_and_forget",
) -> dict:
    """Send a message to another Claude instance or project.

    Use when: Communicating with other Claude instances, requesting tasks,
    sending status updates, or handing off work.
    Returns: {success, message_id, created_at, from_project}.

    Args:
        message_type: Type of message.
        body: Message content.
        subject: Message subject/title.
        to_project: Target project name (validated against workspaces).
        to_session_id: Target session ID (for direct message).
        priority: Message priority (default: normal).
        from_session_id: Your session ID.
        from_project: Sender project name (auto-detected from session if empty).
        parent_message_id: ID of parent message for threading (optional).
        metadata: Optional metadata dict stored as JSONB.
        conversation_mode: Conversation protocol mode (fire_and_forget, question,
            collaborative, task_handoff, review_request). Default: fire_and_forget.
    """
    # Validate conversation_mode
    if conversation_mode not in VALID_CONVERSATION_MODES:
        return {
            "success": False,
            "error": f"Invalid conversation_mode: {conversation_mode}. Valid: {VALID_CONVERSATION_MODES}",
        }

    # Mode-specific validation
    if conversation_mode == "task_handoff" and not (metadata or {}).get("done_criteria"):
        return {
            "success": False,
            "error": "task_handoff mode requires metadata.done_criteria",
        }

    if conversation_mode == "collaborative" and not (metadata or {}).get("ownership"):
        return {
            "success": False,
            "error": "collaborative mode requires metadata.ownership (dict with who_develops, who_deploys)",
        }

    # Merge conversation_mode into metadata
    if metadata is None:
        metadata = {}
    metadata["conversation_mode"] = conversation_mode

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Auto-detect from_project from session if not provided
        resolved_from_project = from_project or None
        if not resolved_from_project and from_session_id:
            cur.execute(
                "SELECT project_name FROM claude.sessions WHERE session_id = %s",
                (from_session_id,),
            )
            row = cur.fetchone()
            if row:
                row_dict = dict(row) if not isinstance(row, dict) else row
                resolved_from_project = row_dict.get('project_name')

        # Validate to_project against workspaces if specified
        if to_project:
            cur.execute(
                "SELECT project_name FROM claude.workspaces WHERE LOWER(project_name) = LOWER(%s)",
                (to_project,),
            )
            if not cur.fetchone():
                # Fuzzy match: suggest similar project names
                cur.execute(
                    "SELECT project_name FROM claude.workspaces ORDER BY project_name",
                )
                all_projects = [dict(r)['project_name'] if not isinstance(r, dict) else r['project_name'] for r in cur.fetchall()]
                suggestions = [p for p in all_projects if to_project.lower() in p.lower() or p.lower() in to_project.lower()]
                if not suggestions:
                    # Broader fuzzy: any partial word match
                    words = to_project.lower().replace('-', ' ').split()
                    suggestions = [p for p in all_projects if any(w in p.lower() for w in words)][:5]
                cur.close()
                conn.close()
                return {
                    "success": False,
                    "error": f"Unknown recipient project: '{to_project}'",
                    "suggestions": suggestions[:5],
                    "hint": "Use list_recipients() to see valid targets",
                }

        # Resolve threading: inherit thread_id from parent, or start new thread
        resolved_thread_id = None
        resolved_parent_id = parent_message_id or None
        if resolved_parent_id:
            cur.execute(
                "SELECT thread_id::text FROM claude.messages WHERE message_id = %s",
                (resolved_parent_id,),
            )
            parent_row = cur.fetchone()
            if parent_row:
                parent_dict = dict(parent_row) if not isinstance(parent_row, dict) else parent_row
                resolved_thread_id = parent_dict.get('thread_id') or resolved_parent_id
            else:
                resolved_thread_id = resolved_parent_id

        cur.execute("""
            INSERT INTO claude.messages
            (from_session_id, from_project, to_session_id, to_project,
             message_type, priority, subject, body, metadata,
             parent_message_id, thread_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING message_id::text, created_at
        """, (
            from_session_id or None,
            resolved_from_project,
            to_session_id or None,
            to_project or None,
            message_type,
            priority,
            subject or None,
            body,
            json.dumps(metadata),
            resolved_parent_id,
            resolved_thread_id,
        ))
        result = cur.fetchone()
        cur.close()
        conn.commit()

        result_dict = dict(result) if not isinstance(result, dict) else result
        return {
            "success": True,
            "message_id": result_dict['message_id'],
            "created_at": result_dict['created_at'].isoformat(),
            "from_project": resolved_from_project,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if not conn.closed:
            conn.close()


@mcp.tool()
def broadcast(
    body: str,
    subject: str = "",
    from_session_id: str = "",
    from_project: str = "",
    priority: Literal["urgent", "normal", "low"] = "normal",
) -> dict:
    """Send a message to ALL active Claude instances.

    Use when: Announcing something to all Claude instances (maintenance,
    important updates, team-wide notifications).
    Returns: {success, message_id, created_at, from_project}.

    Args:
        body: Message content.
        subject: Message subject.
        from_session_id: Your session ID.
        from_project: Sender project name.
        priority: Message priority (default: normal).
    """
    return send_message(
        message_type="broadcast",
        body=body,
        subject=subject,
        priority=priority,
        from_session_id=from_session_id,
        from_project=from_project,
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
    from_project: str = "",
    message_type: str = "",
    thread_status: str = "",
) -> dict:
    """Reply to a specific message. Routes to the sender's PROJECT (not session).

    Use when: Responding to a message from another Claude instance.
    Automatically addresses the reply to the original sender's project
    and sets threading (parent_message_id, thread_id).
    Returns: {success, message_id, created_at, from_project}.

    Args:
        original_message_id: ID of message to reply to.
        body: Reply content.
        from_session_id: Your session ID.
        from_project: Sender project name.
        message_type: Override the reply message type. Defaults to the original
            message's type (e.g. task_request replies stay task_request).
            Falls back to "status_update" if the original type cannot be resolved.
        thread_status: Optional thread lifecycle marker stored in metadata.
            Use "resolved" or "done" to signal the thread is closed.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT from_session_id::text, from_project, to_project, subject,
                   thread_id::text, message_type
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

    # Auto-mark original as read when replying (pending -> read only, don't downgrade)
    conn_ack = get_db_connection()
    try:
        cur_ack = conn_ack.cursor()
        cur_ack.execute("""
            UPDATE claude.messages
            SET status = 'read', read_at = COALESCE(read_at, NOW())
            WHERE message_id = %s AND status = 'pending'
        """, (original_message_id,))
        conn_ack.commit()
        cur_ack.close()
    finally:
        conn_ack.close()

    # Resolve reply message_type: caller > original type > fallback
    VALID_MESSAGE_TYPES = [
        "task_request", "status_update", "question", "notification", "handoff", "broadcast",
    ]
    resolved_message_type = message_type or original_dict.get('message_type') or "status_update"
    if resolved_message_type not in VALID_MESSAGE_TYPES:
        resolved_message_type = "status_update"

    # Build metadata for thread_status if provided
    reply_metadata = None
    if thread_status:
        reply_metadata = {"thread_status": thread_status}

    # Route to from_project (preferred) or fall back to session lookup
    reply_to_project = original_dict.get('from_project') or ""
    if not reply_to_project and original_dict.get('from_session_id'):
        # Legacy fallback: resolve project from session
        conn2 = get_db_connection()
        try:
            cur2 = conn2.cursor()
            cur2.execute(
                "SELECT project_name FROM claude.sessions WHERE session_id = %s",
                (original_dict['from_session_id'],),
            )
            row = cur2.fetchone()
            if row:
                row_dict = dict(row) if not isinstance(row, dict) else row
                reply_to_project = row_dict.get('project_name') or ""
            cur2.close()
        finally:
            conn2.close()

    return send_message(
        message_type=resolved_message_type,
        body=body,
        subject=f"Re: {original_dict['subject']}" if original_dict.get('subject') else "Reply",
        to_project=reply_to_project,
        from_session_id=from_session_id,
        from_project=from_project,
        parent_message_id=original_message_id,
        metadata=reply_metadata,
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
    Unlike check_inbox() which returns all pending messages, this filters to only
    actionable types (task_request, question, handoff) that haven't been actioned or deferred.
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
                from_project,
                message_type,
                priority,
                subject,
                body,
                status,
                created_at,
                parent_message_id::text,
                thread_id::text
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
                # Use from_project directly (no fragile session subquery)
                direction_conditions.append("from_project = %s")
                params.append(project_name)
            if direction_conditions:
                conditions.append(f"({' OR '.join(direction_conditions)})")

        if message_type:
            conditions.append("message_type = %s")
            params.append(message_type)

        query = f"""
            SELECT
                message_id::text, from_session_id::text, from_project,
                to_session_id::text, to_project, message_type, priority,
                subject, body, status, created_at,
                parent_message_id::text, thread_id::text
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
# Workfile Tools (Project-Scoped Component Working Context)
# ============================================================================


@mcp.tool()
def stash(
    component: str,
    title: str,
    content: str,
    project: str = "",
    workfile_type: str = "notes",
    tags: list[str] | None = None,
    feature_code: str | None = None,
    is_pinned: bool = False,
    mode: str = "replace",
) -> dict:
    """Store/update a workfile. UPSERT on (project, component, title).

    Like filing a document in a cabinet: project is the cabinet, component
    is the drawer (e.g. "parallel-runner", "auth-flow"), title is the file.

    Use when: Saving component-scoped working context that should bridge
    sessions. Unlike session_facts (session-scoped) or knowledge (permanent),
    workfiles are project+component scoped with transient lifecycle.
    Returns: {success, workfile_id, action: "created"|"updated"|"appended",
              component, title}.

    Args:
        component: Drawer name (e.g., "parallel-runner", "auth-flow").
        title: File title within component (e.g., "approach notes", "open questions").
        content: The workfile content to store.
        project: Project name. Defaults to current directory.
        workfile_type: notes, findings, questions, approach, investigation, or reference.
        tags: Optional list of tags for categorization.
        feature_code: Optional link to a feature (e.g., "F12").
        is_pinned: If True, auto-surfaces at session start and in precompact.
        mode: "replace" (default) overwrites content, "append" concatenates with separator.
    """
    from server import tool_stash
    return _run_async(tool_stash(
        component=component, title=title, content=content,
        project=project, workfile_type=workfile_type, tags=tags,
        feature_code=feature_code, is_pinned=is_pinned, mode=mode,
    ))


@mcp.tool()
def unstash(
    component: str,
    title: str = "",
    project: str = "",
) -> dict:
    """Retrieve workfile(s). If title given, single file. If omitted, all active in component.

    Use when: Loading component working context at the start of work on a
    specific component, or retrieving specific notes/findings.
    Returns: {success, component, file_count, files: [{title, content,
              workfile_type, tags, updated_at, access_count}]}.

    Args:
        component: Drawer name to retrieve from.
        title: Specific file title. If empty, returns all files in component.
        project: Project name. Defaults to current directory.
    """
    from server import tool_unstash
    return _run_async(tool_unstash(
        component=component,
        title=title or None,
        project=project,
    ))


@mcp.tool()
def list_workfiles(
    project: str = "",
    component: str = "",
    is_active: bool = True,
) -> dict:
    """Browse the filing cabinet. Groups by component with file counts and last-updated.

    No content returned (metadata only — keeps response small).

    Use when: Discovering what components have workfiles, how many files each has,
    and which are pinned. If component given, lists files within that component.
    Returns: {success, project, components: [{name, file_count, last_updated,
              pinned_count}]} or {success, project, component, files: [...]}.

    Args:
        project: Project name. Defaults to current directory.
        component: If given, list files in this component. If empty, list all components.
        is_active: Filter by active status (default True). Set False to see archived.
    """
    from server import tool_list_workfiles
    return _run_async(tool_list_workfiles(
        project=project,
        component=component or None,
        is_active=is_active,
    ))


@mcp.tool()
def search_workfiles(
    query: str,
    project: str = "",
    component: str = "",
    limit: int = 5,
) -> dict:
    """Semantic search via Voyage AI embeddings + optional component filter.

    Returns content preview (200 chars) + similarity score.

    Use when: Looking for workfile content by meaning rather than exact title.
    Useful for finding notes about a topic across all components.
    Returns: {success, query, result_count, results: [{component, title,
              preview, similarity, workfile_type}]}.

    Args:
        query: Natural language search query.
        project: Project name. Defaults to current directory.
        component: Optional filter to search within a specific component.
        limit: Maximum number of results (default 5).
    """
    from server import tool_search_workfiles
    return _run_async(tool_search_workfiles(
        query=query,
        project=project,
        component=component or None,
        limit=limit,
    ))


# ============================================================================
# Activity / WCC Tools (Work Context Container)
# ============================================================================


@mcp.tool()
def create_activity(
    name: str,
    aliases: list[str] | None = None,
    description: str = "",
    project: str = "",
) -> dict:
    """Create a named activity for WCC context assembly.

    Activities represent named work contexts (e.g., "auth-flow",
    "data-migration") that group related knowledge, workfiles, tasks,
    and session facts. WCC auto-detects activities from prompts and
    assembles context automatically.

    Use when: Explicitly creating an activity with aliases for better
    detection. Activities are also auto-created when workfile components
    match prompt text.
    Returns: {success, activity_id, action: "created"|"updated", name, project}.

    Args:
        name: Activity name (e.g., "auth-flow", "data-migration").
        aliases: Alternative names for detection (e.g., ["authentication", "login"]).
        description: What this activity is about.
        project: Project name. Defaults to current directory.
    """
    from server import tool_create_activity
    return _run_async(tool_create_activity(
        name=name, aliases=aliases, description=description, project=project,
    ))


@mcp.tool()
def list_activities(
    project: str = "",
) -> dict:
    """List activities with access stats for a project.

    Use when: Reviewing what activities exist, how often they're accessed,
    and managing activity lifecycle.
    Returns: {success, project, count, activities: [{activity_id, name,
              aliases, description, last_accessed_at, access_count, is_active}]}.

    Args:
        project: Project name. Defaults to current directory.
    """
    from server import tool_list_activities
    return _run_async(tool_list_activities(project=project))


@mcp.tool()
def update_activity(
    activity_id: str,
    aliases: list[str] | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> dict:
    """Update an existing activity's aliases, description, or active status.

    Use when: Adding aliases for better detection, updating descriptions,
    or deactivating stale activities.
    Returns: {success, activity_id, name, updated_fields}.

    Args:
        activity_id: UUID of the activity to update.
        aliases: New aliases list (replaces existing).
        description: New description.
        is_active: Set to False to deactivate.
    """
    from server import tool_update_activity
    return _run_async(tool_update_activity(
        activity_id=activity_id, aliases=aliases,
        description=description, is_active=is_active,
    ))


@mcp.tool()
def assemble_context(
    activity_name: str,
    project: str = "",
    budget: int = 1000,
) -> dict:
    """Manually assemble WCC context for a named activity.

    Queries 6 sources (workfiles, knowledge, features, session facts,
    vault RAG, BPMN) with proportional budget allocation and returns
    the assembled context. Normally this happens automatically via the
    RAG hook — use this for manual inspection or debugging.

    Use when: Manually triggering context assembly, debugging WCC output,
    or loading context for an activity without waiting for auto-detection.
    Returns: {success, activity_name, project, context, token_estimate}.

    Args:
        activity_name: Name of the activity to assemble context for.
        project: Project name. Defaults to current directory.
        budget: Token budget for assembled context (default 1000).
    """
    from server import tool_assemble_context
    return _run_async(tool_assemble_context(
        activity_name=activity_name, project=project, budget=budget,
    ))


# ============================================================================
# Entity Catalog Tools
# ============================================================================


def _interpolate_template(template: str, properties: dict) -> str:
    """Replace {placeholders} with property values, skip missing."""
    import re
    def replacer(match):
        key = match.group(1)
        val = properties.get(key, '')
        return str(val) if val else ''
    return re.sub(r'\{(\w+)\}', replacer, template).strip()


def _compute_entity_summary(properties: dict, summary_template: str | None = None) -> str:
    """Compute a smart summary from entity properties for progressive disclosure.

    Returns a compact string (~100-200 bytes) containing entity name, key fields,
    navigation properties, and top property names — enough for the AI to decide
    if it needs full details. Written for machine consumption, not human readability.
    """
    if summary_template == 'odata_smart_summary':
        name = properties.get('name', 'Unknown')
        fields = properties.get('fields', [])
        key_props = properties.get('key_properties', [])
        description = properties.get('description', '')

        # Separate navigation properties from data properties
        nav_props = [f['name'] for f in fields if f.get('type') == 'NavigationProperty']
        data_props = [f for f in fields if f.get('type') != 'NavigationProperty']
        data_names = [f['name'] for f in data_props]

        # Build key info
        key_str = ', '.join(key_props) if key_props else '?'

        # Build nav props (max 6)
        nav_str = ', '.join(nav_props[:6])
        if len(nav_props) > 6:
            nav_str += f', ... (+{len(nav_props) - 6} more)'

        # Build top data property names (max 8)
        top_props = ', '.join(data_names[:8])
        if len(data_names) > 8:
            top_props += ', ...'

        # Build description snippet
        desc_str = f' {description}' if description else ''

        return (
            f"{name} (Key: {key_str}).{desc_str} "
            f"Nav [{len(nav_props)}]: {nav_str}. "
            f"Props [{len(data_props)}]: {top_props}. "
            f"(use detail='full' for all properties)"
        )

    # Generic fallback for non-OData entities
    name = properties.get('name', properties.get('title', 'Unknown'))
    prop_count = len(properties)
    top_keys = ', '.join(list(properties.keys())[:5])
    return f"{name}. Fields [{prop_count}]: {top_keys}. (use detail='full' for all properties)"


@mcp.tool()
def catalog(
    entity_type: str,
    properties: dict,
    project: str = "",
    tags: list[str] | None = None,
    relationships: list[dict] | None = None,
) -> dict:
    """Store a structured entity in the catalog with type validation and embedding.

    Entities are typed, validated, embeddable reference data: books, API endpoints,
    OData entities, patterns, etc. New entity types can be registered via SQL INSERT
    into claude.entity_types — no code change needed.

    Use when: Cataloging structured reference data that should be searchable later.
    Deduplicates: if an entity with the same type and key properties exists, merges.
    Returns: {success, entity_id, entity_type, display_name, action: 'created'|'merged'}.

    Args:
        entity_type: Type name (e.g., 'book', 'api_endpoint', 'odata_entity').
        properties: JSONB properties validated against the type's json_schema.
        project: Project scope (optional, defaults to current directory).
        tags: Tags for filtering.
        relationships: List of {to_entity_id, relationship_type} dicts.
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # 1. Lookup entity type
        cur.execute("""
            SELECT type_id::text, json_schema, embedding_template, name_property, summary_template
            FROM claude.entity_types
            WHERE type_name = %s AND is_active = TRUE
        """, (entity_type,))
        type_row = cur.fetchone()
        if not type_row:
            return {"success": False, "error": f"Unknown entity type: '{entity_type}'. "
                    "Check claude.entity_types for valid types."}

        type_id = type_row['type_id']
        json_schema = type_row['json_schema']
        embedding_template = type_row['embedding_template']
        name_property = type_row['name_property']
        summary_template = type_row.get('summary_template')

        # 2. Validate properties against json_schema
        if json_schema and json_schema.get('required'):
            missing = [r for r in json_schema['required'] if r not in properties]
            if missing:
                return {"success": False,
                        "error": f"Missing required properties: {missing}"}

        # 3. Resolve project_id
        project_id = None
        if project:
            project_id = get_project_id(project)

        # 4. Check for existing entity (dedup)
        name_val = properties.get(name_property, properties.get('name', properties.get('title', '')))
        cur.execute("""
            SELECT entity_id::text FROM claude.entities
            WHERE entity_type_id = %s::uuid
              AND properties ->> %s = %s
              AND NOT is_archived
            LIMIT 1
        """, (type_id, name_property, str(name_val)))
        existing = cur.fetchone()

        if existing:
            # Merge properties into existing entity
            summary = _compute_entity_summary(properties, summary_template)
            cur.execute("""
                UPDATE claude.entities
                SET properties = properties || %s,
                    tags = CASE WHEN %s::text[] != '{}' THEN %s ELSE tags END,
                    summary = %s,
                    updated_at = NOW()
                WHERE entity_id = %s::uuid
                RETURNING entity_id::text,
                    COALESCE(properties->>'name', properties->>'title', 'Unnamed') AS display_name
            """, (json.dumps(properties), tags or [], tags or [], summary, existing['entity_id']))
            merged = cur.fetchone()

            # Refresh embedding
            embed_text = _interpolate_template(embedding_template, properties)
            embedding = generate_embedding(embed_text)
            if embedding:
                cur.execute("""
                    UPDATE claude.entities SET embedding = %s::vector
                    WHERE entity_id = %s::uuid
                """, (embedding, existing['entity_id']))

            conn.commit()
            return {
                "success": True,
                "entity_id": merged['entity_id'],
                "entity_type": entity_type,
                "display_name": merged['display_name'],
                "action": "merged",
            }

        # 5. Generate embedding from template
        embed_text = _interpolate_template(embedding_template, properties)
        embedding = generate_embedding(embed_text)

        # 5b. Compute summary for progressive disclosure
        summary = _compute_entity_summary(properties, summary_template)

        # 6. INSERT new entity
        cur.execute("""
            INSERT INTO claude.entities (
                entity_type_id, project_id, properties, tags, embedding, summary,
                created_at, updated_at
            ) VALUES (
                %s::uuid, %s, %s, %s, %s::vector, %s, NOW(), NOW()
            )
            RETURNING entity_id::text,
                COALESCE(properties->>'name', properties->>'title', 'Unnamed') AS display_name
        """, (type_id, project_id, json.dumps(properties), tags or [], embedding, summary))
        result = cur.fetchone()

        # 7. Create relationships if provided
        rel_count = 0
        if relationships:
            for rel in relationships:
                to_id = rel.get('to_entity_id')
                rel_type = rel.get('relationship_type', 'related_to')
                if to_id and to_id != result['entity_id']:
                    cur.execute("""
                        INSERT INTO claude.entity_relationships (
                            from_entity_id, to_entity_id, relationship_type
                        ) VALUES (%s::uuid, %s::uuid, %s)
                    """, (result['entity_id'], to_id, rel_type))
                    rel_count += 1

        conn.commit()
        return {
            "success": True,
            "entity_id": result['entity_id'],
            "entity_type": entity_type,
            "display_name": result['display_name'],
            "action": "created",
            "relationships_created": rel_count,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to catalog entity: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def update_entity(
    entity_id: str = "",
    entity_name: str = "",
    entity_type: str = "",
    patch: dict | None = None,
    tags: list[str] | None = None,
    is_archived: bool | None = None,
) -> dict:
    """Update an existing entity's properties without full upsert.

    Supports targeted patch operations on JSONB properties fields so you don't
    need to know the full properties to fix a single value.

    Use when: Fixing a gotcha in an entity, adding a field, removing stale data,
    or archiving an entity. Avoids the need for raw SQL to modify entity data.
    Returns: {success, entity_id, display_name, changes_applied, action: 'updated'}.

    Args:
        entity_id: Entity UUID (preferred). Either entity_id or entity_name required.
        entity_name: Display name to look up (case-insensitive). If ambiguous, also
            provide entity_type to disambiguate.
        entity_type: Filter by type name when using entity_name lookup.
        patch: Dict of property patches. Each key is a property field name, value is
            either a literal (shorthand for "set") or an operation dict:
            - {"op": "set", "value": <any>} — set/overwrite the field
            - {"op": "append", "value": <any>} — append to an array field
            - {"op": "remove", "value": <any>} — remove a value from an array field
            - {"op": "remove_key"} — remove the property key entirely
            - Shorthand: {"field": "new_value"} is equivalent to {"field": {"op": "set", "value": "new_value"}}
        tags: Replace tags entirely (set to [] to clear). None = no change.
        is_archived: Set archive status. None = no change.
    """
    if not patch and tags is None and is_archived is None:
        return {"success": False, "error": "Nothing to update. Provide patch, tags, or is_archived."}

    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # 1. Resolve entity
        if entity_id:
            cur.execute("""
                SELECT e.entity_id::text, e.properties, e.entity_type_id::text,
                       et.embedding_template, et.summary_template,
                       COALESCE(e.properties->>'name', e.properties->>'title', 'Unnamed') AS display_name
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE e.entity_id = %s::uuid
            """, (entity_id,))
        elif entity_name:
            type_filter = ""
            params = [entity_name]
            if entity_type:
                type_filter = "AND et.type_name = %s"
                params.append(entity_type)
            cur.execute(f"""
                SELECT e.entity_id::text, e.properties, e.entity_type_id::text,
                       et.embedding_template, et.summary_template,
                       COALESCE(e.properties->>'name', e.properties->>'title', 'Unnamed') AS display_name
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE LOWER(COALESCE(e.properties->>'name', e.properties->>'title', '')) = LOWER(%s)
                  AND NOT e.is_archived
                  {type_filter}
            """, params)
        else:
            return {"success": False, "error": "Provide entity_id or entity_name."}

        rows = cur.fetchall()
        if not rows:
            return {"success": False, "error": f"Entity not found: {entity_id or entity_name}"}
        if len(rows) > 1:
            matches = [{"entity_id": r['entity_id'], "display_name": r['display_name']} for r in rows]
            return {"success": False, "error": "Ambiguous name — multiple matches. Provide entity_type or use entity_id.",
                    "matches": matches}

        row = rows[0]
        eid = row['entity_id']
        properties = row['properties']
        embedding_template = row['embedding_template']
        summary_template = row.get('summary_template')

        # 2. Apply patches to properties
        changes = []
        if patch:
            for field, operation in patch.items():
                # Shorthand: literal value = set
                if not isinstance(operation, dict) or 'op' not in operation:
                    operation = {"op": "set", "value": operation}

                op = operation['op']
                val = operation.get('value')

                if op == 'set':
                    properties[field] = val
                    changes.append(f"set {field}")

                elif op == 'append':
                    if field not in properties:
                        properties[field] = []
                    if not isinstance(properties[field], list):
                        return {"success": False, "error": f"Cannot append to non-array field '{field}'"}
                    properties[field].append(val)
                    changes.append(f"appended to {field}")

                elif op == 'remove':
                    if field in properties and isinstance(properties[field], list):
                        try:
                            properties[field].remove(val)
                            changes.append(f"removed from {field}")
                        except ValueError:
                            changes.append(f"'{val}' not found in {field} (no change)")
                    elif field in properties:
                        return {"success": False, "error": f"Cannot remove from non-array field '{field}'. Use 'remove_key' to delete the field."}

                elif op == 'remove_key':
                    if field in properties:
                        del properties[field]
                        changes.append(f"removed key {field}")
                    else:
                        changes.append(f"key {field} not present (no change)")

                else:
                    return {"success": False, "error": f"Unknown op '{op}'. Valid: set, append, remove, remove_key."}

        # 3. Build UPDATE query
        set_clauses = ["properties = %s", "updated_at = NOW()"]
        params = [json.dumps(properties)]

        if tags is not None:
            set_clauses.append("tags = %s")
            params.append(tags)
            changes.append("replaced tags")

        if is_archived is not None:
            set_clauses.append("is_archived = %s")
            params.append(is_archived)
            changes.append(f"{'archived' if is_archived else 'unarchived'}")

        # Recompute summary
        summary = _compute_entity_summary(properties, summary_template)
        set_clauses.append("summary = %s")
        params.append(summary)

        params.append(eid)
        cur.execute(f"""
            UPDATE claude.entities
            SET {', '.join(set_clauses)}
            WHERE entity_id = %s::uuid
            RETURNING entity_id::text,
                COALESCE(properties->>'name', properties->>'title', 'Unnamed') AS display_name
        """, params)
        updated = cur.fetchone()

        # 4. Refresh embedding
        embed_text = _interpolate_template(embedding_template, properties)
        embedding = generate_embedding(embed_text)
        if embedding:
            cur.execute("""
                UPDATE claude.entities SET embedding = %s::vector
                WHERE entity_id = %s::uuid
            """, (embedding, eid))

        conn.commit()
        return {
            "success": True,
            "entity_id": updated['entity_id'],
            "display_name": updated['display_name'],
            "changes_applied": changes,
            "action": "updated",
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to update entity: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


# ============================================================================
# KNOWLEDGE ARTICLES — Narrative knowledge linking multiple entities [F198]
# ============================================================================


@mcp.tool()
def write_article(
    title: str,
    abstract: str,
    article_type: str = "research",
    tags: list | None = None,
    project_ids: list | None = None,
    article_id: str = "",
    project: str = "",
) -> dict:
    """Create or update a knowledge article header.

    Knowledge articles are narrative documents that explain how multiple entities
    connect. They contain ordered sections, each independently searchable.

    Use when: Capturing research findings, explaining entity relationships,
    documenting investigations, or writing reference guides.
    Returns: {success, article_id, title, action: 'created'|'updated'}.

    Args:
        title: Article title.
        abstract: Short summary (1-3 sentences) for search results and index.
        article_type: investigation, reference, tutorial, architecture, or research.
        tags: Tags for classification and filtering.
        project_ids: UUIDs of projects this article relates to. Empty = cross-project.
        article_id: If provided, updates existing article. Otherwise creates new.
        project: Project name (used to resolve project_id if project_ids not given).
    """
    # Validate article_type
    valid_types = get_valid_values('knowledge_articles', 'article_type')
    if valid_types and article_type not in valid_types:
        return {"success": False, "error": f"Invalid article_type '{article_type}'. Valid: {valid_types}"}

    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Resolve project_ids from project name if needed
        resolved_project_ids = project_ids or []
        if not resolved_project_ids and project:
            cur.execute("SELECT project_id FROM claude.projects WHERE project_name = %s", (project,))
            row = cur.fetchone()
            if row:
                resolved_project_ids = [str(row['project_id'])]

        # Generate embedding from title + abstract
        embed_text = f"{title}. {abstract}"
        embedding = generate_embedding(embed_text)

        if article_id:
            # UPDATE existing
            cur.execute("""
                UPDATE claude.knowledge_articles
                SET title = %s, abstract = %s, article_type = %s,
                    tags = %s, project_ids = %s::uuid[],
                    updated_at = now(), version = version + 1,
                    embedding = CASE WHEN %s IS NOT NULL THEN %s::vector ELSE embedding END
                WHERE article_id = %s::uuid
                RETURNING article_id, title, version
            """, (title, abstract, article_type, tags or [],
                  resolved_project_ids or None,
                  embedding, embedding, article_id))
            updated = cur.fetchone()
            if not updated:
                return {"success": False, "error": f"Article {article_id} not found"}
            conn.commit()
            return {"success": True, "article_id": str(updated['article_id']),
                    "title": updated['title'], "version": updated['version'],
                    "action": "updated"}
        else:
            # INSERT new
            cur.execute("""
                INSERT INTO claude.knowledge_articles
                    (title, abstract, article_type, status, tags, project_ids, embedding)
                VALUES (%s, %s, %s, 'draft', %s, %s::uuid[], %s::vector)
                RETURNING article_id, title
            """, (title, abstract, article_type, tags or [],
                  resolved_project_ids or None, embedding))
            created = cur.fetchone()
            conn.commit()
            return {"success": True, "article_id": str(created['article_id']),
                    "title": created['title'], "action": "created", "status": "draft"}

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"write_article failed: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def write_article_section(
    article_id: str,
    title: str,
    body: str,
    section_order: int = 0,
    summary: str = "",
    linked_entity_ids: list | None = None,
    section_id: str = "",
    change_reason: str = "",
) -> dict:
    """Add or update a section in a knowledge article.

    Each section covers ONE semantic topic (300-5000 tokens). Sections are
    independently embeddable and retrievable. On update, previous version
    is saved to article_section_versions.

    Use when: Building out an article's content section by section.
    Returns: {success, section_id, article_id, title, section_order, action}.

    Args:
        article_id: Parent article UUID.
        title: Section title (e.g., "Mapping Results", "Key Findings").
        body: Section content (300-5000 tokens recommended, one topic).
        section_order: Position in reading order. 0 = auto-append at end.
        summary: Optional 1-2 sentence summary for the article index.
        linked_entity_ids: UUIDs of entities discussed in this section.
        section_id: If provided, updates existing section. Otherwise creates new.
        change_reason: Why this section was updated (stored in version history).
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Verify article exists
        cur.execute("SELECT article_id, title FROM claude.knowledge_articles WHERE article_id = %s::uuid",
                    (article_id,))
        article = cur.fetchone()
        if not article:
            return {"success": False, "error": f"Article {article_id} not found"}

        # Generate embedding from section title + body
        embed_text = f"{title}. {body[:2000]}"
        embedding = generate_embedding(embed_text)

        if section_id:
            # Save current version before updating
            cur.execute("""
                INSERT INTO claude.article_section_versions (section_id, version, body, changed_by_session, change_reason)
                SELECT section_id, version, body, %s::uuid, %s
                FROM claude.article_sections WHERE section_id = %s::uuid
            """, (None, change_reason or "Updated", section_id))

            # UPDATE existing section
            cur.execute("""
                UPDATE claude.article_sections
                SET title = %s, body = %s, summary = %s,
                    linked_entity_ids = %s::uuid[],
                    section_order = CASE WHEN %s > 0 THEN %s ELSE section_order END,
                    version = version + 1, updated_at = now(),
                    embedding = CASE WHEN %s IS NOT NULL THEN %s::vector ELSE embedding END
                WHERE section_id = %s::uuid
                RETURNING section_id, title, section_order, version
            """, (title, body, summary or None,
                  linked_entity_ids or None,
                  section_order, section_order,
                  embedding, embedding, section_id))
            updated = cur.fetchone()
            if not updated:
                return {"success": False, "error": f"Section {section_id} not found"}
            conn.commit()
            return {"success": True, "section_id": str(updated['section_id']),
                    "article_id": article_id, "title": updated['title'],
                    "section_order": updated['section_order'],
                    "version": updated['version'], "action": "updated"}
        else:
            # Auto-assign section_order if 0
            if section_order == 0:
                cur.execute("""
                    SELECT COALESCE(MAX(section_order), 0) + 1 as next_order
                    FROM claude.article_sections WHERE article_id = %s::uuid
                """, (article_id,))
                section_order = cur.fetchone()['next_order']

            # INSERT new section
            cur.execute("""
                INSERT INTO claude.article_sections
                    (article_id, section_order, title, body, summary,
                     embedding, linked_entity_ids)
                VALUES (%s::uuid, %s, %s, %s, %s, %s::vector, %s::uuid[])
                RETURNING section_id, title, section_order
            """, (article_id, section_order, title, body, summary or None,
                  embedding, linked_entity_ids or None))
            created = cur.fetchone()

            # Update article's updated_at
            cur.execute("UPDATE claude.knowledge_articles SET updated_at = now() WHERE article_id = %s::uuid",
                        (article_id,))

            conn.commit()
            return {"success": True, "section_id": str(created['section_id']),
                    "article_id": article_id, "title": created['title'],
                    "section_order": created['section_order'], "action": "created"}

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"write_article_section failed: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def recall_articles(
    query: str,
    project: str = "",
    article_type: str = "",
    entity_id: str = "",
    tags: list | None = None,
    limit: int = 5,
) -> dict:
    """Search knowledge articles using semantic similarity.

    Searches both article abstracts and section bodies. Returns article
    headers with matching sections for progressive disclosure.

    Use when: Looking for narrative knowledge about a topic, finding articles
    linked to specific entities, or browsing articles by type/tag.
    Returns: {success, query, result_count, results: [{article_id, title,
              abstract, article_type, tags, similarity, matching_sections}]}.

    Args:
        query: Natural language search query.
        project: Filter by project name (optional).
        article_type: Filter by article type (optional).
        entity_id: Find articles with sections linked to this entity (optional).
        tags: Filter by tags overlap (optional).
        limit: Max results (default 5).
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Generate query embedding
        query_embedding = generate_query_embedding(query)
        if not query_embedding:
            return {"success": False, "error": "Failed to generate query embedding"}

        # If entity_id provided, find articles with sections linking to that entity
        if entity_id:
            cur.execute("""
                SELECT DISTINCT a.article_id, a.title, a.abstract, a.article_type,
                       a.tags, a.status, a.version, a.updated_at,
                       1 - (a.embedding <=> %s::vector) as similarity
                FROM claude.knowledge_articles a
                JOIN claude.article_sections s ON s.article_id = a.article_id
                WHERE a.status != 'archived'
                AND %s::uuid = ANY(s.linked_entity_ids)
                ORDER BY similarity DESC
                LIMIT %s
            """, (query_embedding, entity_id, limit))
        else:
            # Semantic search on article abstracts
            filters = ["a.status != 'archived'"]
            params = [query_embedding]

            if project:
                filters.append("""
                    EXISTS (SELECT 1 FROM claude.projects p
                            WHERE p.project_name = %s
                            AND p.project_id = ANY(a.project_ids))
                """)
                params.append(project)
            if article_type:
                filters.append("a.article_type = %s")
                params.append(article_type)
            if tags:
                filters.append("a.tags && %s")
                params.append(tags)

            params.append(limit)
            where = " AND ".join(filters)

            cur.execute(f"""
                SELECT a.article_id, a.title, a.abstract, a.article_type,
                       a.tags, a.status, a.version, a.updated_at,
                       1 - (a.embedding <=> %s::vector) as similarity
                FROM claude.knowledge_articles a
                WHERE {where}
                AND a.embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT %s
            """, params)

        articles = cur.fetchall()

        # For each article, find matching sections
        results = []
        for art in articles:
            cur.execute("""
                SELECT section_id, title, summary,
                       section_order, linked_entity_ids,
                       1 - (embedding <=> %s::vector) as similarity
                FROM claude.article_sections
                WHERE article_id = %s::uuid
                AND embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT 3
            """, (query_embedding, art['article_id']))
            sections = cur.fetchall()

            results.append({
                "article_id": str(art['article_id']),
                "title": art['title'],
                "abstract": art['abstract'],
                "article_type": art['article_type'],
                "tags": art['tags'],
                "status": art['status'],
                "similarity": round(float(art['similarity']), 4) if art['similarity'] else 0,
                "matching_sections": [{
                    "section_id": str(s['section_id']),
                    "title": s['title'],
                    "summary": s['summary'],
                    "section_order": s['section_order'],
                    "similarity": round(float(s['similarity']), 4) if s['similarity'] else 0,
                } for s in sections]
            })

        return {
            "success": True,
            "query": query,
            "result_count": len(results),
            "results": results,
        }

    except Exception as e:
        return {"success": False, "error": f"recall_articles failed: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def read_article(
    article_id: str,
    section_id: str = "",
) -> dict:
    """Read a full article or a single section, formatted as markdown.

    Use when: Reading article content after finding it via recall_articles.
    Full read returns all sections in order. Section read returns one section.
    Returns: {success, article_id, title, abstract, content (markdown),
              sections: [{section_id, title, body, section_order}]}.

    Args:
        article_id: Article UUID.
        section_id: If provided, returns only this section. Otherwise full article.
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Get article header
        cur.execute("""
            SELECT article_id, title, abstract, article_type, status,
                   tags, project_ids, version, created_at, updated_at
            FROM claude.knowledge_articles WHERE article_id = %s::uuid
        """, (article_id,))
        article = cur.fetchone()
        if not article:
            return {"success": False, "error": f"Article {article_id} not found"}

        if section_id:
            # Single section
            cur.execute("""
                SELECT section_id, title, body, summary, section_order,
                       linked_entity_ids, version
                FROM claude.article_sections
                WHERE section_id = %s::uuid AND article_id = %s::uuid
            """, (section_id, article_id))
            section = cur.fetchone()
            if not section:
                return {"success": False, "error": f"Section {section_id} not found"}

            content = f"# {article['title']}\n## {section['title']}\n\n{section['body']}"
            return {
                "success": True,
                "article_id": str(article['article_id']),
                "title": article['title'],
                "content": content,
                "section": {
                    "section_id": str(section['section_id']),
                    "title": section['title'],
                    "body": section['body'],
                    "section_order": section['section_order'],
                    "linked_entity_ids": [str(e) for e in (section['linked_entity_ids'] or [])],
                },
            }
        else:
            # Full article
            cur.execute("""
                SELECT section_id, title, body, summary, section_order,
                       linked_entity_ids, version
                FROM claude.article_sections
                WHERE article_id = %s::uuid
                ORDER BY section_order
            """, (article_id,))
            sections = cur.fetchall()

            # Build markdown
            lines = [f"# {article['title']}"]
            lines.append(f"*{article['article_type']} | {article['status']} | v{article['version']}*")
            lines.append(f"\n> {article['abstract']}\n")

            if sections:
                lines.append("## Table of Contents")
                for s in sections:
                    summary_text = f" — {s['summary']}" if s['summary'] else ""
                    lines.append(f"{s['section_order']}. {s['title']}{summary_text}")
                lines.append("")

                for s in sections:
                    lines.append(f"## {s['section_order']}. {s['title']}\n")
                    lines.append(s['body'])
                    lines.append("")

            content = "\n".join(lines)

            return {
                "success": True,
                "article_id": str(article['article_id']),
                "title": article['title'],
                "abstract": article['abstract'],
                "article_type": article['article_type'],
                "status": article['status'],
                "tags": article['tags'],
                "section_count": len(sections),
                "content": content,
                "sections": [{
                    "section_id": str(s['section_id']),
                    "title": s['title'],
                    "section_order": s['section_order'],
                    "summary": s['summary'],
                    "linked_entity_ids": [str(e) for e in (s['linked_entity_ids'] or [])],
                } for s in sections],
            }

    except Exception as e:
        return {"success": False, "error": f"read_article failed: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def manage_article(
    article_id: str,
    action: str,
    new_status: str = "",
) -> dict:
    """Manage article lifecycle: archive, publish, change status.

    Use when: Publishing a draft article, archiving a stale one, or
    checking article metadata.
    Returns: {success, article_id, action, previous_status, new_status}.

    Args:
        article_id: Article UUID.
        action: 'publish' (draft→published), 'archive' (any→archived),
                'revert_draft' (published→draft), 'info' (return metadata).
        new_status: Direct status override (optional, use action instead).
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT article_id, title, status, article_type, tags,
                   version, created_at, updated_at
            FROM claude.knowledge_articles WHERE article_id = %s::uuid
        """, (article_id,))
        article = cur.fetchone()
        if not article:
            return {"success": False, "error": f"Article {article_id} not found"}

        if action == "info":
            # Count sections
            cur.execute("SELECT COUNT(*) as cnt FROM claude.article_sections WHERE article_id = %s::uuid",
                        (article_id,))
            section_count = cur.fetchone()['cnt']
            return {
                "success": True,
                "article_id": str(article['article_id']),
                "title": article['title'],
                "status": article['status'],
                "article_type": article['article_type'],
                "tags": article['tags'],
                "version": article['version'],
                "section_count": section_count,
                "created_at": str(article['created_at']),
                "updated_at": str(article['updated_at']),
                "action": "info",
            }

        # Determine target status
        prev_status = article['status']
        if action == "publish":
            target = "published"
        elif action == "archive":
            target = "archived"
        elif action == "revert_draft":
            target = "draft"
        elif new_status:
            valid_statuses = get_valid_values('knowledge_articles', 'status')
            if valid_statuses and new_status not in valid_statuses:
                return {"success": False, "error": f"Invalid status '{new_status}'. Valid: {valid_statuses}"}
            target = new_status
        else:
            return {"success": False, "error": f"Unknown action '{action}'. Use: publish, archive, revert_draft, info"}

        cur.execute("""
            UPDATE claude.knowledge_articles
            SET status = %s, updated_at = now()
            WHERE article_id = %s::uuid
        """, (target, article_id))

        conn.commit()
        return {
            "success": True,
            "article_id": str(article['article_id']),
            "title": article['title'],
            "action": action,
            "previous_status": prev_status,
            "new_status": target,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"manage_article failed: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


# ============================================================================
# RESOURCE LINKING — Universal cross-system bridge
# ============================================================================


def _get_linked_resources(cur, resource_type: str, resource_id: str,
                          link_type: str = "", direction: str = "both") -> list:
    """Internal helper: query resource_links for a given resource."""
    results = []
    if direction in ("both", "outgoing"):
        type_filter = "AND link_type = %s" if link_type else ""
        params = [resource_type, resource_id]
        if link_type:
            params.append(link_type)
        cur.execute(f"""
            SELECT link_id::text, to_type, to_id::text, link_type, strength, metadata
            FROM claude.resource_links
            WHERE from_type = %s AND from_id = %s::uuid {type_filter}
            ORDER BY strength DESC
        """, params)
        for row in cur.fetchall():
            results.append({
                "link_id": row['link_id'], "direction": "outgoing",
                "resource_type": row['to_type'], "resource_id": row['to_id'],
                "link_type": row['link_type'], "strength": row['strength'],
                "metadata": row.get('metadata', {}),
            })
    if direction in ("both", "incoming"):
        type_filter = "AND link_type = %s" if link_type else ""
        params = [resource_type, resource_id]
        if link_type:
            params.append(link_type)
        cur.execute(f"""
            SELECT link_id::text, from_type, from_id::text, link_type, strength, metadata
            FROM claude.resource_links
            WHERE to_type = %s AND to_id = %s::uuid {type_filter}
            ORDER BY strength DESC
        """, params)
        for row in cur.fetchall():
            results.append({
                "link_id": row['link_id'], "direction": "incoming",
                "resource_type": row['from_type'], "resource_id": row['from_id'],
                "link_type": row['link_type'], "strength": row['strength'],
                "metadata": row.get('metadata', {}),
            })
    return results


@mcp.tool()
def link_resources(
    from_type: str,
    from_id: str,
    to_type: str,
    to_id: str,
    link_type: str = "related_to",
    strength: float = 1.0,
    metadata: dict | None = None,
) -> dict:
    """Create a link between any two resources in the system.

    Use when: Connecting a skill to related entities, a feature to its BPMN
    process, a workfile to a knowledge entry, or any cross-system relationship.
    Returns: {success, link_id, from_type, from_id, to_type, to_id, link_type}.

    Args:
        from_type: Source resource type (entity, skill, workfile, feature, build_task,
            feedback, bpmn_process, knowledge, activity, rule, project).
        from_id: UUID of the source resource.
        to_type: Target resource type (same options as from_type).
        to_id: UUID of the target resource.
        link_type: Relationship type: related_to, depends_on, implements, documents,
            extends, part_of, uses, produces, validates.
        strength: Link strength 0-1 (default 1.0).
        metadata: Optional JSONB metadata.
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.resource_links (from_type, from_id, to_type, to_id, link_type, strength, metadata)
            VALUES (%s, %s::uuid, %s, %s::uuid, %s, %s, %s)
            ON CONFLICT (from_type, from_id, to_type, to_id, link_type)
            DO UPDATE SET strength = EXCLUDED.strength, metadata = EXCLUDED.metadata
            RETURNING link_id::text
        """, (from_type, from_id, to_type, to_id, link_type, strength,
              json.dumps(metadata or {})))
        result = cur.fetchone()
        conn.commit()
        return {
            "success": True, "link_id": result['link_id'],
            "from_type": from_type, "from_id": from_id,
            "to_type": to_type, "to_id": to_id, "link_type": link_type,
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Failed to link resources: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def get_linked_resources(
    resource_type: str,
    resource_id: str,
    link_type: str = "",
    direction: str = "both",
) -> dict:
    """Get all resources linked to a given resource.

    Use when: Understanding what's connected to a skill, entity, feature, or
    any other resource. Bidirectional by default — shows both outgoing and
    incoming links.
    Returns: {success, resource_type, resource_id, links: [{direction, resource_type,
              resource_id, link_type, strength}]}.

    Args:
        resource_type: Type of the resource to query (entity, skill, workfile, etc.).
        resource_id: UUID of the resource.
        link_type: Filter by link type (optional).
        direction: 'both' (default), 'outgoing', or 'incoming'.
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()
        links = _get_linked_resources(cur, resource_type, resource_id, link_type, direction)
        return {
            "success": True, "resource_type": resource_type,
            "resource_id": resource_id, "link_count": len(links), "links": links,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to get linked resources: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def recall_entities(
    query: str,
    entity_type: str = "",
    project: str = "",
    tags: list[str] | None = None,
    limit: int = 10,
    min_similarity: float = 0.5,
    detail: str = "summary",
    entity_id: str = "",
) -> dict:
    """Search cataloged entities using RRF fusion (vector + BM25 full-text).

    Returns summaries by default (name, key fields, nav props) — compact and
    context-efficient. Use detail='full' for complete properties, or entity_id
    for a single entity's full details.

    Summary mode is ~87% smaller — use it for browsing/finding entities, then
    request full detail only for the specific entities you need to work with.

    Use when: Looking for structured reference data previously stored via catalog().
    Returns: {success, query, result_count, results: [{entity_id, entity_type,
              display_name, summary|properties, tags, similarity, rrf_score}]}.

    Args:
        query: Natural language search query.
        entity_type: Filter by entity type name (optional).
        project: Filter by project (optional).
        tags: Filter by tags overlap (optional).
        limit: Max results (default: 10).
        min_similarity: Minimum vector similarity threshold (default: 0.5).
        detail: 'summary' (default) returns compact summaries, 'full' returns complete properties.
        entity_id: If provided, returns full details for this specific entity (ignores query).
    """
    from server import generate_query_embedding

    # Fast path: single entity by ID (always returns full properties)
    if entity_id:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT e.entity_id::text, et.type_name, e.display_name,
                    e.properties::text, e.summary, e.tags
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE e.entity_id = %s::uuid AND NOT e.is_archived
            """, (entity_id,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": f"Entity not found: {entity_id}"}
            cur.execute("UPDATE claude.entities SET last_accessed_at = NOW(), access_count = access_count + 1 WHERE entity_id = %s::uuid", (entity_id,))
            conn.commit()
            return {
                "success": True, "query": f"entity_id={entity_id}", "result_count": 1,
                "results": [{
                    "entity_id": row['entity_id'], "entity_type": row['type_name'],
                    "display_name": row['display_name'],
                    "properties": json.loads(row['properties']) if isinstance(row['properties'], str) else row['properties'],
                    "tags": row['tags'] or [], "similarity": 1.0, "rrf_score": 1.0,
                }],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    # Generate query embedding (uses FastEmbed local or Voyage AI based on EMBEDDING_PROVIDER)
    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        return {"error": "Failed to generate query embedding — embedding service may be unavailable"}

    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()

        # Build optional filters
        filters = []
        filter_params = []

        if entity_type:
            filters.append("AND et.type_name = %s")
            filter_params.append(entity_type)

        if project:
            project_id = get_project_id(project)
            if project_id:
                filters.append("AND (e.project_id = %s OR e.project_id IS NULL)")
                filter_params.append(project_id)

        if tags and len(tags) > 0:
            filters.append("AND e.tags && %s")
            filter_params.append(tags)

        filter_clause = " ".join(filters)

        # Build tsquery from natural language
        # Split words, join with & for AND matching
        ts_words = [w.strip() for w in query.split() if w.strip() and len(w.strip()) > 2]
        ts_query_str = " | ".join(ts_words) if ts_words else query

        # RRF fusion: vector similarity + BM25
        cur.execute(f"""
            WITH entity_vec AS (
                SELECT e.entity_id, e.properties, e.tags, e.display_name,
                    et.type_name, e.summary,
                    1 - (e.embedding <=> %s::vector) AS similarity,
                    ROW_NUMBER() OVER (ORDER BY e.embedding <=> %s::vector) AS rank_vec
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE NOT e.is_archived
                  AND e.embedding IS NOT NULL
                  AND 1 - (e.embedding <=> %s::vector) >= %s
                  {filter_clause}
                ORDER BY e.embedding <=> %s::vector
                LIMIT 20
            ),
            entity_bm25 AS (
                SELECT e.entity_id,
                    ts_rank(e.search_vector, to_tsquery('english', %s)) AS bm25_score,
                    ROW_NUMBER() OVER (
                        ORDER BY ts_rank(e.search_vector, to_tsquery('english', %s)) DESC
                    ) AS rank_bm25
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE NOT e.is_archived
                  AND e.search_vector @@ to_tsquery('english', %s)
                  {filter_clause}
                LIMIT 20
            ),
            rrf AS (
                SELECT v.entity_id, v.properties, v.tags, v.display_name, v.type_name,
                    v.summary,
                    v.similarity,
                    COALESCE(1.0 / (60 + v.rank_vec), 0) +
                    COALESCE(1.0 / (60 + b.rank_bm25), 0) AS rrf_score
                FROM entity_vec v
                LEFT JOIN entity_bm25 b ON v.entity_id = b.entity_id
                UNION
                SELECT e.entity_id, e.properties, e.tags, e.display_name,
                    et.type_name, e.summary,
                    0 AS similarity,
                    COALESCE(1.0 / (60 + b.rank_bm25), 0) AS rrf_score
                FROM entity_bm25 b
                JOIN claude.entities e ON b.entity_id = e.entity_id
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE b.entity_id NOT IN (SELECT entity_id FROM entity_vec)
            )
            SELECT entity_id::text, type_name, display_name, properties::text,
                summary, tags, similarity, rrf_score
            FROM rrf
            ORDER BY rrf_score DESC
            LIMIT %s
        """, (
            query_embedding, query_embedding, query_embedding, min_similarity,
            *filter_params,  # vec filters
            query_embedding,
            ts_query_str, ts_query_str, ts_query_str,
            *filter_params,  # bm25 filters
            limit,
        ))

        results = []
        entity_ids = []
        for row in cur.fetchall():
            entity_ids.append(row['entity_id'])
            result_item = {
                "entity_id": row['entity_id'],
                "entity_type": row['type_name'],
                "display_name": row['display_name'],
                "tags": row['tags'] or [],
                "similarity": round(row['similarity'], 4) if row['similarity'] else 0,
                "rrf_score": round(row['rrf_score'], 4),
            }
            if detail == "full":
                result_item["properties"] = json.loads(row['properties']) if isinstance(row['properties'], str) else row['properties']
            else:
                # Summary mode (default) — return compact summary instead of full properties
                result_item["summary"] = row['summary'] or row['display_name']
            results.append(result_item)

        # Update access stats for returned entities
        if entity_ids:
            cur.execute("""
                UPDATE claude.entities
                SET last_accessed_at = NOW(),
                    access_count = access_count + 1
                WHERE entity_id = ANY(%s::uuid[])
            """, (entity_ids,))
            conn.commit()

        return {
            "success": True,
            "query": query,
            "result_count": len(results),
            "results": results,
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Entity recall failed: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


@mcp.tool()
def explore_entities(
    tags: list = None,
    entity_type: str = "",
    entity_id: str = "",
    project: str = "",
    page: int = 1,
    page_size: int = 30,
) -> dict:
    """Browse the entity catalog with progressive disclosure (inventory → list → detail).

    Three stages of progressive disclosure for token-efficient navigation:

    Stage 1 - INVENTORY: explore_entities(tags=["nimbus"]) → type counts as tree
    Stage 2 - BROWSE: explore_entities(tags=["nimbus"], entity_type="odata_entity") → entity list
    Stage 3 - DETAIL: explore_entities(entity_id="xxx") → full properties

    This is a BROWSE tool, not a search tool. Use recall_entities() for search.

    Use when: Orienting to a project's knowledge, browsing what entities exist,
    or drilling into a specific entity's details.
    Returns: {success, stage, tree/entities/entity, total_count, page, page_size}.

    Args:
        tags: Filter entities by tags (e.g. ["nimbus"]). Used in Stage 1 and 2.
        entity_type: Filter by entity type name. Triggers Stage 2 browse.
        entity_id: Specific entity UUID. Triggers Stage 3 detail.
        project: Project name filter (optional).
        page: Page number for Stage 2 browse (default 1).
        page_size: Entities per page in Stage 2 (default 30, max 50).
    """
    conn = get_db_connection()
    cur = None
    try:
        cur = conn.cursor()
        page_size = min(page_size, 50)
        offset = (page - 1) * page_size

        # ── Stage 3: DETAIL (entity_id provided) ──
        if entity_id:
            cur.execute("""
                SELECT e.entity_id::text, e.display_name, et.type_name,
                       e.properties, e.tags, e.confidence, e.access_count,
                       e.created_at::text, e.updated_at::text
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE e.entity_id = %s::uuid AND NOT e.is_archived
            """, (entity_id,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": f"Entity not found: {entity_id}"}

            # Get explicit relationships from entity_relationships table
            cur.execute("""
                SELECT er.relationship_type, er.strength,
                       e2.entity_id::text as related_id,
                       e2.display_name as related_name,
                       et2.type_name as related_type,
                       'outgoing' as direction
                FROM claude.entity_relationships er
                JOIN claude.entities e2 ON er.to_entity_id = e2.entity_id
                JOIN claude.entity_types et2 ON e2.entity_type_id = et2.type_id
                WHERE er.from_entity_id = %s::uuid AND NOT e2.is_archived
                UNION ALL
                SELECT er.relationship_type, er.strength,
                       e2.entity_id::text as related_id,
                       e2.display_name as related_name,
                       et2.type_name as related_type,
                       'incoming' as direction
                FROM claude.entity_relationships er
                JOIN claude.entities e2 ON er.from_entity_id = e2.entity_id
                JOIN claude.entity_types et2 ON e2.entity_type_id = et2.type_id
                WHERE er.to_entity_id = %s::uuid AND NOT e2.is_archived
            """, (entity_id, entity_id))
            explicit_rels = [dict(r) for r in cur.fetchall()]

            # Resolve implicit relationships based on entity type
            entity_data = dict(row)
            type_name = entity_data.get("type_name", "")
            props = entity_data.get("properties", {}) or {}
            implicit_rels = []

            if type_name == "odata_entity":
                # Extract NavigationProperty fields and resolve to catalog entities
                fields = props.get("fields", [])
                if isinstance(fields, list):
                    nav_names = []
                    for f in fields:
                        if isinstance(f, dict) and f.get("type") == "NavigationProperty":
                            name = f.get("name", "")
                            # Strip "List" suffix for collection nav props
                            target = name[:-4] if name.endswith("List") else name
                            nav_names.append((name, target))

                    if nav_names:
                        # Batch resolve: look up target entity names in the catalog
                        targets = [t for _, t in nav_names]
                        cur.execute("""
                            SELECT e2.entity_id::text, e2.display_name
                            FROM claude.entities e2
                            JOIN claude.entity_types et2 ON e2.entity_type_id = et2.type_id
                            WHERE et2.type_name = 'odata_entity'
                              AND e2.display_name = ANY(%s)
                              AND NOT e2.is_archived
                        """, (targets,))
                        resolved = {r['display_name']: r['entity_id'] for r in cur.fetchall()}

                        for nav_name, target in nav_names:
                            rel = {
                                "relationship_type": "nav_property",
                                "nav_property": nav_name,
                                "related_name": target,
                                "related_type": "odata_entity",
                                "source": "implicit",
                            }
                            if target in resolved:
                                rel["related_id"] = resolved[target]
                                rel["resolved"] = True
                            else:
                                rel["resolved"] = False
                            implicit_rels.append(rel)

            elif type_name == "domain_concept":
                # Resolve workfile_refs
                for wref in props.get("workfile_refs", []):
                    if isinstance(wref, dict):
                        implicit_rels.append({
                            "relationship_type": "workfile_ref",
                            "related_name": f"{wref.get('component', '?')}/{wref.get('title', '?')}",
                            "related_type": "workfile",
                            "source": "implicit",
                        })
                # Resolve vault_refs
                for vref in props.get("vault_refs", []):
                    if isinstance(vref, dict):
                        implicit_rels.append({
                            "relationship_type": "vault_ref",
                            "related_name": vref.get("title", vref.get("path", "?")),
                            "related_type": "vault_doc",
                            "source": "implicit",
                        })
                    elif isinstance(vref, str):
                        implicit_rels.append({
                            "relationship_type": "vault_ref",
                            "related_name": vref,
                            "related_type": "vault_doc",
                            "source": "implicit",
                        })

            # Mark explicit relationships with source
            for r in explicit_rels:
                r["source"] = "explicit"

            # Update access tracking
            cur.execute("""
                UPDATE claude.entities
                SET access_count = access_count + 1, last_accessed_at = NOW()
                WHERE entity_id = %s::uuid
            """, (entity_id,))
            conn.commit()

            # Build summary counts
            all_rels = explicit_rels + implicit_rels
            rel_summary = {}
            for r in all_rels:
                rt = r["relationship_type"]
                rel_summary[rt] = rel_summary.get(rt, 0) + 1

            return {
                "success": True,
                "stage": "detail",
                "entity": entity_data,
                "relationships": explicit_rels,
                "implicit_connections": implicit_rels,
                "connection_summary": rel_summary,
            }

        # ── Build tag/project filter ──
        filter_clauses = ["NOT e.is_archived"]
        filter_params = []

        if tags:
            filter_clauses.append("e.tags @> %s")
            filter_params.append(tags)

        if project:
            cur.execute("SELECT project_id FROM claude.projects WHERE project_name = %s", (project,))
            proj = cur.fetchone()
            if proj:
                filter_clauses.append("e.project_id = %s::uuid")
                filter_params.append(str(proj['project_id']))

        where = " AND ".join(filter_clauses)

        # ── Stage 2: BROWSE (entity_type provided) ──
        if entity_type:
            # Get total count
            cur.execute(f"""
                SELECT count(*) as total
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE et.type_name = %s AND {where}
            """, [entity_type] + filter_params)
            total = cur.fetchone()['total']

            # Get paginated entity list with compact info
            cur.execute(f"""
                SELECT e.entity_id::text, e.display_name, e.summary,
                       e.tags, e.access_count,
                       jsonb_typeof(e.properties->'fields') as has_fields,
                       CASE WHEN e.properties ? 'field_count'
                            THEN (e.properties->>'field_count')::int
                            ELSE NULL END as field_count
                FROM claude.entities e
                JOIN claude.entity_types et ON e.entity_type_id = et.type_id
                WHERE et.type_name = %s AND {where}
                ORDER BY e.display_name
                LIMIT %s OFFSET %s
            """, [entity_type] + filter_params + [page_size, offset])
            rows = cur.fetchall()

            entities = []
            for r in rows:
                entry = {
                    "entity_id": r['entity_id'],
                    "name": r['display_name'],
                }
                if r['summary']:
                    entry["summary"] = r['summary']
                if r['field_count']:
                    entry["field_count"] = r['field_count']
                entities.append(entry)

            tag_label = f" (tags: {', '.join(tags)})" if tags else ""
            total_pages = (total + page_size - 1) // page_size

            return {
                "success": True,
                "stage": "browse",
                "entity_type": entity_type,
                "filter": tag_label.strip(),
                "entities": entities,
                "total_count": total,
                "page": page,
                "total_pages": total_pages,
                "page_size": page_size,
            }

        # ── Stage 1: INVENTORY (default) ──
        cur.execute(f"""
            SELECT et.type_name, et.display_name as type_display,
                   count(e.entity_id) as count
            FROM claude.entity_types et
            LEFT JOIN claude.entities e ON e.entity_type_id = et.type_id AND {where}
            WHERE et.is_active = TRUE
            GROUP BY et.type_name, et.display_name
            HAVING count(e.entity_id) > 0
            ORDER BY count(e.entity_id) DESC
        """, filter_params)
        type_rows = cur.fetchall()

        total_entities = sum(r['count'] for r in type_rows)
        tag_label = ', '.join(tags) if tags else 'all'

        # Build ASCII tree
        tree_lines = [f"Knowledge Map ({tag_label}) — {total_entities} entities"]
        for i, r in enumerate(type_rows):
            is_last = (i == len(type_rows) - 1)
            prefix = "└── " if is_last else "├── "
            tree_lines.append(f"{prefix}{r['type_display']} ({r['count']})")

        tree = "\n".join(tree_lines)

        # Also return structured data
        types = [{"type_name": r['type_name'], "display_name": r['type_display'],
                  "count": r['count']} for r in type_rows]

        return {
            "success": True,
            "stage": "inventory",
            "tree": tree,
            "types": types,
            "total_entities": total_entities,
            "filter_tags": tags or [],
        }

    except Exception as e:
        conn.rollback()
        return {"success": False, "error": f"Entity exploration failed: {str(e)}"}
    finally:
        if cur:
            cur.close()
        conn.close()


# ============================================================================
# Code Knowledge Graph Tools
# ============================================================================


@mcp.tool()
def index_codebase(project: str = "", project_path: str = "", force_full: bool = False, dry_run: bool = False) -> dict:
    """Index a project's codebase into the Code Knowledge Graph.

    Parses source files using tree-sitter, extracts symbols (functions, classes,
    methods) and cross-references (calls, imports, extends), stores in DB with
    Voyage AI embeddings for semantic search.

    Use when: Setting up code intelligence for a project, or after major code changes.
    First run does full index; subsequent runs are incremental (only changed files).
    Returns: {files_scanned, files_indexed, symbols_extracted, refs_extracted,
              refs_resolved, symbols_embedded, stale_deleted}.

    Args:
        project: Project name. Defaults to current directory.
        project_path: Path to project root. Auto-detected from workspaces if empty.
        force_full: Force full re-index (ignore file hashes).
        dry_run: Report what would happen without writing to DB. Returns per-file
                 diagnostics: skip reason, parse results, error details.
    """
    import sys
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'scripts')
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from code_indexer import index_project

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        proj_name = project or os.path.basename(os.getcwd())
        if not project_path:
            cur.execute(
                "SELECT config->>'workspace_path' as path FROM claude.workspaces WHERE project_name = %s AND is_active = true",
                (proj_name,)
            )
            row = cur.fetchone()
            if row and row['path']:
                project_path = row['path']
            else:
                project_path = os.getcwd()
        conn.close()

        result = index_project(proj_name, project_path, force_full=force_full, dry_run=dry_run)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def find_symbol(query: str, project: str = "", kind: str = "", limit: int = 20) -> dict:
    """Search for code symbols by name or semantic meaning.

    Hybrid search combining exact name matching and Voyage AI embedding similarity.
    Finds functions, classes, methods, and other symbols across the indexed codebase.

    Use when: Looking for a specific function/class, or finding symbols related to a concept.
    Returns: {success, query, result_count, symbols: [{symbol_id, name, kind, file_path,
              line_number, signature, similarity}]}.

    Args:
        query: Search text — matched against symbol names and embeddings.
        project: Project name filter. If empty, searches all indexed projects.
        kind: Filter by symbol kind (function, class, method, interface, enum).
        limit: Maximum results (default 20).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        project_id = None
        if project:
            cur.execute("SELECT project_id FROM claude.projects WHERE project_name = %s", (project,))
            row = cur.fetchone()
            if row:
                project_id = row['project_id']

        params = []
        where_clauses = ["name ILIKE %s"]
        params.append(f"%{query}%")
        if project_id:
            where_clauses.append("project_id = %s")
            params.append(project_id)
        if kind:
            where_clauses.append("kind = %s")
            params.append(kind)

        where_sql = " AND ".join(where_clauses)
        cur.execute(f"""
            SELECT symbol_id::text, name, kind, file_path, line_number,
                   signature, visibility, language, scope,
                   1.0 as similarity
            FROM claude.code_symbols
            WHERE {where_sql}
            ORDER BY
                CASE WHEN name = %s THEN 0
                     WHEN name ILIKE %s THEN 1
                     ELSE 2 END,
                name
            LIMIT %s
        """, params + [query, f"{query}%", limit])

        exact_results = cur.fetchall()

        if len(exact_results) < limit:
            try:
                embedding = generate_query_embedding(query)
                if not embedding:
                    raise ValueError("Embedding generation failed")
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

                embed_params = [embedding_str]
                embed_where = []
                if project_id:
                    embed_where.append("project_id = %s")
                    embed_params.append(project_id)
                if kind:
                    embed_where.append("kind = %s")
                    embed_params.append(kind)
                embed_where.append("embedding IS NOT NULL")

                found_ids = [r['symbol_id'] for r in exact_results]
                if found_ids:
                    embed_where.append("symbol_id::text != ALL(%s)")
                    embed_params.append(found_ids)

                embed_where_sql = " AND ".join(embed_where)
                remaining = limit - len(exact_results)
                embed_params.append(remaining)

                cur.execute(f"""
                    SELECT symbol_id::text, name, kind, file_path, line_number,
                           signature, visibility, language, scope,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM claude.code_symbols
                    WHERE {embed_where_sql}
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT %s
                """, [embedding_str] + embed_params[1:] + [embedding_str])

                embed_results = [r for r in cur.fetchall() if r['similarity'] > 0.3]
                exact_results.extend(embed_results)
            except Exception:
                pass  # Embedding search is optional enhancement

        return {
            "success": True,
            "query": query,
            "result_count": len(exact_results),
            "symbols": exact_results,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_context(symbol_name: str, project: str = "", depth: int = 1) -> dict:
    """Get full context for a symbol: body, callers, callees, types, and siblings.

    One call replaces 5-10 file reads. Returns everything needed to understand
    or modify a symbol without opening any files.

    Use when: About to modify a function/class, need to understand its usage,
    or want to see what calls it and what it calls.
    Returns: {success, symbol, body, callers: [], callees: [], siblings: [],
              file_context: {path, language, total_symbols}}.

    Args:
        symbol_name: Exact name of the symbol (function, class, method).
        project: Project name. Defaults to current directory basename.
        depth: How many levels of callers/callees to follow (1=direct, 2=transitive). Max 2.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        depth = min(depth, 2)

        # Resolve project
        if not project:
            project = os.path.basename(os.getcwd())
        cur.execute("SELECT project_id FROM claude.projects WHERE project_name = %s", (project,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"Project '{project}' not found"}
        project_id = row['project_id']

        # Find the symbol (exact match first, then ILIKE)
        cur.execute("""
            SELECT symbol_id, name, kind, file_path, line_number, end_line,
                   signature, visibility, language, scope, body, parent_symbol_id
            FROM claude.code_symbols
            WHERE project_id = %s AND name = %s
            ORDER BY visibility DESC, line_number
            LIMIT 1
        """, (project_id, symbol_name))
        sym = cur.fetchone()

        if not sym:
            cur.execute("""
                SELECT symbol_id, name, kind, file_path, line_number, end_line,
                       signature, visibility, language, scope, body, parent_symbol_id
                FROM claude.code_symbols
                WHERE project_id = %s AND name ILIKE %s
                ORDER BY visibility DESC, line_number
                LIMIT 1
            """, (project_id, symbol_name))
            sym = cur.fetchone()

        if not sym:
            return {"success": False, "error": f"Symbol '{symbol_name}' not found in {project}"}

        symbol_id = sym['symbol_id']

        # Get callees (what this symbol calls)
        cur.execute("""
            SELECT cr.to_symbol_name, cr.ref_type,
                   ts.name as resolved_name, ts.kind as resolved_kind,
                   ts.file_path as resolved_file, ts.line_number as resolved_line
            FROM claude.code_references cr
            LEFT JOIN claude.code_symbols ts ON cr.to_symbol_id = ts.symbol_id
            WHERE cr.from_symbol_id = %s
            ORDER BY cr.ref_type, cr.to_symbol_name
        """, (symbol_id,))
        callees = cur.fetchall()

        # Get callers (what calls this symbol)
        cur.execute("""
            SELECT fs.name as caller_name, fs.kind as caller_kind,
                   fs.file_path as caller_file, fs.line_number as caller_line,
                   cr.ref_type
            FROM claude.code_references cr
            JOIN claude.code_symbols fs ON cr.from_symbol_id = fs.symbol_id
            WHERE cr.to_symbol_id = %s
               OR (cr.to_symbol_id IS NULL AND cr.to_symbol_name = %s)
            ORDER BY fs.file_path, fs.line_number
        """, (symbol_id, symbol_name))
        callers = cur.fetchall()

        # Get siblings (other symbols in same file)
        cur.execute("""
            SELECT name, kind, line_number, visibility, signature
            FROM claude.code_symbols
            WHERE project_id = %s AND file_path = %s AND symbol_id != %s
            ORDER BY line_number
        """, (project_id, sym['file_path'], symbol_id))
        siblings = cur.fetchall()

        # Get parent symbol if exists
        parent = None
        if sym['parent_symbol_id']:
            cur.execute("""
                SELECT name, kind, file_path, line_number, signature
                FROM claude.code_symbols WHERE symbol_id = %s
            """, (sym['parent_symbol_id'],))
            parent = cur.fetchone()

        # File context
        cur.execute("""
            SELECT count(*) as cnt FROM claude.code_symbols
            WHERE project_id = %s AND file_path = %s
        """, (project_id, sym['file_path']))
        file_sym_count = cur.fetchone()['cnt']

        # Depth 2: get transitive callers/callees
        transitive_callers = []
        transitive_callees = []
        if depth >= 2 and callers:
            caller_ids = [c['caller_name'] for c in callers[:10]]
            if caller_ids:
                placeholders = ','.join(['%s'] * len(caller_ids))
                cur.execute(f"""
                    SELECT DISTINCT fs.name as caller_name, fs.kind as caller_kind,
                           fs.file_path as caller_file, cr.ref_type
                    FROM claude.code_references cr
                    JOIN claude.code_symbols fs ON cr.from_symbol_id = fs.symbol_id
                    JOIN claude.code_symbols ts ON cr.to_symbol_id = ts.symbol_id
                    WHERE ts.project_id = %s AND ts.name IN ({placeholders})
                    LIMIT 20
                """, [project_id] + caller_ids)
                transitive_callers = cur.fetchall()

        result = {
            "success": True,
            "symbol": {
                "name": sym['name'],
                "kind": sym['kind'],
                "file_path": sym['file_path'],
                "line_number": sym['line_number'],
                "end_line": sym['end_line'],
                "signature": sym['signature'],
                "visibility": sym['visibility'],
                "language": sym['language'],
                "scope": sym['scope'],
            },
            "body": sym['body'],
            "parent": dict(parent) if parent else None,
            "callers": [dict(c) for c in callers],
            "callees": [dict(c) for c in callees],
            "siblings": [dict(s) for s in siblings[:20]],
            "file_context": {
                "path": sym['file_path'],
                "language": sym['language'],
                "total_symbols": file_sym_count,
            },
        }

        if depth >= 2:
            result["transitive_callers"] = [dict(c) for c in transitive_callers]

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def check_collision(name: str, project: str = "", file_path: str = "") -> dict:
    """Check if a symbol name already exists in the project codebase.

    Use when: Before creating a new function/class to avoid name collisions.
    Returns: {success, name, has_collision, collisions: [{name, kind, file_path,
              line_number, signature, visibility}]}.

    Args:
        name: Symbol name to check for collisions.
        project: Project name. Defaults to current directory.
        file_path: Exclude this file from results (the file being edited).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        proj_name = project or os.path.basename(os.getcwd())
        cur.execute("SELECT project_id FROM claude.projects WHERE project_name = %s", (proj_name,))
        row = cur.fetchone()
        if not row:
            return {"success": True, "name": name, "has_collision": False, "collisions": [], "message": "Project not indexed"}

        project_id = row['project_id']

        params = [project_id, name]
        exclude = ""
        if file_path:
            exclude = " AND file_path != %s"
            params.append(file_path)

        cur.execute(f"""
            SELECT name, kind, file_path, line_number, signature, visibility
            FROM claude.code_symbols
            WHERE project_id = %s AND name = %s{exclude}
            ORDER BY file_path, line_number
        """, params)

        collisions = cur.fetchall()
        return {
            "success": True,
            "name": name,
            "has_collision": len(collisions) > 0,
            "collisions": collisions,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def _resolve_ckg_file_path(cur, project_id: str, project_name: str, file_path: str) -> str:
    """Normalize a file_path for CKG queries.

    Handles: relative paths, forward slashes, missing drive letters.
    Strategy:
      1. Normalize slashes to OS-native
      2. If absolute, use as-is
      3. If relative, resolve against workspace_path
      4. Fallback: suffix match in DB
    """
    import os
    normalized = os.path.normpath(file_path)

    # If already absolute, return normalized
    if os.path.isabs(normalized):
        return normalized

    # Try resolving against workspace_path
    cur.execute(
        "SELECT config->>'workspace_path' as path FROM claude.workspaces "
        "WHERE project_name = %s AND is_active = true",
        (project_name,)
    )
    ws_row = cur.fetchone()
    if ws_row and ws_row['path']:
        resolved = os.path.normpath(os.path.join(ws_row['path'], normalized))
        # Verify it exists in the DB
        cur.execute(
            "SELECT 1 FROM claude.code_symbols WHERE project_id = %s AND file_path = %s LIMIT 1",
            (project_id, resolved),
        )
        if cur.fetchone():
            return resolved

    # Fallback: suffix match (handles both slash directions)
    suffix = normalized.replace('\\', '/').lstrip('/')
    cur.execute(
        "SELECT DISTINCT file_path FROM claude.code_symbols "
        "WHERE project_id = %s AND file_path LIKE %s LIMIT 1",
        (project_id, '%' + suffix),
    )
    match = cur.fetchone()
    if match:
        return match['file_path']

    # Nothing found — return normalized as best effort
    return normalized


@mcp.tool()
def get_module_map(project: str = "", file_path: str = "") -> dict:
    """Get a structural map of symbols in a file or project.

    With file_path: lists all symbols in that file with parent-child hierarchy.
    Without file_path: returns project overview (files with symbol counts).

    Use when: Understanding code structure, reviewing a module, or getting
    a project-level overview of the codebase.
    Returns: {success, scope, symbols: [{name, kind, line_number, signature, children}]}
    or {success, scope, files: [{file_path, language, symbol_count, symbols}]}.

    Args:
        project: Project name. Defaults to current directory.
        file_path: Specific file to map. If empty, returns project overview.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        proj_name = project or os.path.basename(os.getcwd())
        cur.execute("SELECT project_id FROM claude.projects WHERE project_name = %s", (proj_name,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": f"Project '{proj_name}' not found or not indexed"}
        project_id = row['project_id']

        if file_path:
            resolved_path = _resolve_ckg_file_path(cur, project_id, proj_name, file_path)
            cur.execute("""
                SELECT symbol_id::text, name, kind, line_number, end_line,
                       signature, visibility, scope, parent_symbol_id::text
                FROM claude.code_symbols
                WHERE project_id = %s AND file_path = %s
                ORDER BY line_number
            """, (project_id, resolved_path))
            symbols = cur.fetchall()

            by_id = {s['symbol_id']: {**s, 'children': []} for s in symbols}
            roots = []
            for s in symbols:
                if s['parent_symbol_id'] and s['parent_symbol_id'] in by_id:
                    by_id[s['parent_symbol_id']]['children'].append(by_id[s['symbol_id']])
                else:
                    roots.append(by_id[s['symbol_id']])

            return {
                "success": True,
                "scope": "file",
                "file_path": file_path,
                "symbol_count": len(symbols),
                "symbols": roots,
            }
        else:
            cur.execute("""
                SELECT file_path, language, count(*) as symbol_count,
                       array_agg(kind || ' ' || name ORDER BY line_number) as symbol_list
                FROM claude.code_symbols
                WHERE project_id = %s
                GROUP BY file_path, language
                ORDER BY file_path
            """, (project_id,))
            files = cur.fetchall()
            return {
                "success": True,
                "scope": "project",
                "project": proj_name,
                "file_count": len(files),
                "total_symbols": sum(f['symbol_count'] for f in files),
                "files": files,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def find_similar(symbol_id: str, limit: int = 10) -> dict:
    """Find symbols that are semantically similar to a given symbol.

    Uses Voyage AI code embeddings to find functions/classes with similar
    purpose or signature, useful for detecting potential duplicates or
    finding related code.

    Use when: Checking for duplicate implementations, finding related functions,
    or understanding similar patterns across the codebase.
    Returns: {success, source_symbol, similar: [{name, kind, file_path,
              line_number, signature, similarity}]}.

    Args:
        symbol_id: UUID of the source symbol.
        limit: Maximum similar symbols to return (default 10).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT symbol_id::text, name, kind, file_path, line_number, signature, embedding
            FROM claude.code_symbols WHERE symbol_id = %s::uuid
        """, (symbol_id,))
        source = cur.fetchone()
        if not source:
            return {"success": False, "error": f"Symbol {symbol_id} not found"}
        if source['embedding'] is None:
            return {"success": False, "error": "Source symbol has no embedding"}

        cur.execute("""
            SELECT symbol_id::text, name, kind, file_path, line_number, signature,
                   visibility, language,
                   1 - (embedding <=> (SELECT embedding FROM claude.code_symbols WHERE symbol_id = %s::uuid)) as similarity
            FROM claude.code_symbols
            WHERE symbol_id != %s::uuid AND embedding IS NOT NULL
                AND project_id = (SELECT project_id FROM claude.code_symbols WHERE symbol_id = %s::uuid)
            ORDER BY embedding <=> (SELECT embedding FROM claude.code_symbols WHERE symbol_id = %s::uuid) ASC
            LIMIT %s
        """, (symbol_id, symbol_id, symbol_id, symbol_id, limit))

        similar = cur.fetchall()
        return {
            "success": True,
            "source_symbol": {"name": source['name'], "kind": source['kind'], "file_path": source['file_path']},
            "result_count": len(similar),
            "similar": similar,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@mcp.tool()
def get_dependency_graph(symbol_id: str, depth: int = 2, direction: str = "both") -> dict:
    """Walk the code reference graph from a symbol to find dependencies.

    Shows what a symbol calls (outgoing), what calls it (incoming), or both.
    Recursive to specified depth for transitive dependencies.

    Use when: Understanding how a function is used, what it depends on,
    or tracing call chains through the codebase.
    Returns: {success, root, direction, edges: [{from_name, from_file, to_name,
              to_file, ref_type, depth}]}.

    Args:
        symbol_id: UUID of the root symbol.
        depth: How many hops to traverse (default 2, max 5).
        direction: 'outgoing' (what this calls), 'incoming' (what calls this), or 'both'.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        depth = min(depth, 5)

        cur.execute("""
            SELECT symbol_id::text, name, kind, file_path, line_number, signature
            FROM claude.code_symbols WHERE symbol_id = %s::uuid
        """, (symbol_id,))
        root = cur.fetchone()
        if not root:
            return {"success": False, "error": f"Symbol {symbol_id} not found"}

        edges = []

        if direction in ('outgoing', 'both'):
            cur.execute("""
                WITH RECURSIVE deps(from_id, to_id, ref_type, depth) AS (
                    SELECT from_symbol_id, to_symbol_id, ref_type, 1
                    FROM claude.code_references
                    WHERE from_symbol_id = %s::uuid AND to_symbol_id IS NOT NULL
                    UNION ALL
                    SELECT r.from_symbol_id, r.to_symbol_id, r.ref_type, d.depth + 1
                    FROM claude.code_references r
                    JOIN deps d ON r.from_symbol_id = d.to_id
                    WHERE d.depth < %s AND r.to_symbol_id IS NOT NULL
                )
                SELECT DISTINCT
                    fs.name as from_name, fs.kind as from_kind, fs.file_path as from_file,
                    ts.name as to_name, ts.kind as to_kind, ts.file_path as to_file,
                    d.ref_type, d.depth, 'outgoing' as direction
                FROM deps d
                JOIN claude.code_symbols fs ON fs.symbol_id = d.from_id
                JOIN claude.code_symbols ts ON ts.symbol_id = d.to_id
                ORDER BY d.depth, fs.name
            """, (symbol_id, depth))
            edges.extend(cur.fetchall())

        if direction in ('incoming', 'both'):
            cur.execute("""
                WITH RECURSIVE callers(from_id, to_id, ref_type, depth) AS (
                    SELECT from_symbol_id, to_symbol_id, ref_type, 1
                    FROM claude.code_references
                    WHERE to_symbol_id = %s::uuid
                    UNION ALL
                    SELECT r.from_symbol_id, r.to_symbol_id, r.ref_type, c.depth + 1
                    FROM claude.code_references r
                    JOIN callers c ON r.to_symbol_id = c.from_id
                    WHERE c.depth < %s
                )
                SELECT DISTINCT
                    fs.name as from_name, fs.kind as from_kind, fs.file_path as from_file,
                    ts.name as to_name, ts.kind as to_kind, ts.file_path as to_file,
                    c.ref_type, c.depth, 'incoming' as direction
                FROM callers c
                JOIN claude.code_symbols fs ON fs.symbol_id = c.from_id
                JOIN claude.code_symbols ts ON ts.symbol_id = c.to_id
                ORDER BY c.depth, fs.name
            """, (symbol_id, depth))
            edges.extend(cur.fetchall())

        return {
            "success": True,
            "root": {"name": root['name'], "kind": root['kind'], "file_path": root['file_path']},
            "direction": direction,
            "depth": depth,
            "edge_count": len(edges),
            "edges": edges,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# Secret Vault: Windows Credential Manager Integration
# ============================================================================

def _get_keyring():
    """Import and return keyring module, or None if unavailable."""
    try:
        import keyring as kr
        # Verify a usable backend exists
        backend = kr.get_keyring()
        if "fail" in type(backend).__name__.lower():
            return None
        return kr
    except Exception:
        return None


def _safe_db_connect():
    """Get DB connection or None if unavailable."""
    try:
        return get_db_connection()
    except Exception:
        return None


def _secret_service_name(project: str, key: str) -> str:
    """Build WCM service name: claude/{project}/{key}."""
    return f"claude/{project}/{key}"


@mcp.tool()
def set_secret(
    secret_key: str,
    secret_value: str,
    project: str = "",
    description: str = "",
) -> dict:
    """Store a secret in the OS credential vault (Windows Credential Manager).

    Persists across sessions — no need to re-enter credentials. Also registers
    the key in claude.secret_registry so bulk_load can find it at session start.
    The secret is also stored as a session fact for immediate use.

    Use when: Storing API keys, auth tokens, connection strings, or any credential
    that should persist across sessions. Replaces the old pattern of storing
    credentials as session facts that die with the session.
    Returns: {success, secret_key, project, stored_in, persist_across_sessions}.

    Args:
        secret_key: Key name (e.g., 'monash_auth_token', 'voyage_api_key').
        secret_value: The secret value to store.
        project: Project name. Defaults to current directory.
        description: Optional description of what this secret is for.
    """
    project = project or os.path.basename(os.getcwd())

    if not secret_key or not secret_value:
        return {"success": False, "error": "secret_key and secret_value are required"}

    kr = _get_keyring()
    if not kr:
        return {
            "success": False,
            "error": "No keyring backend available. Install keyring: pip install keyring",
            "stored_in": "none",
            "persist_across_sessions": False,
        }

    service = _secret_service_name(project, secret_key)

    try:
        # Check if exists (for rotation logging)
        existing = kr.get_password(service, "secret")
        is_rotation = existing is not None

        # Write to WCM
        kr.set_password(service, "secret", secret_value)

        # Register in DB so bulk_load knows about it
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO claude.secret_registry (project_name, secret_key, description, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (project_name, secret_key)
                DO UPDATE SET description = EXCLUDED.description, updated_at = NOW()
            """, (project, secret_key, description))
            conn.commit()
            conn.close()
        except Exception:
            pass  # Registry is nice-to-have, WCM store already succeeded

        return {
            "success": True,
            "secret_key": secret_key,
            "project": project,
            "stored_in": "windows_credential_manager",
            "persist_across_sessions": True,
            "is_rotation": is_rotation,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "persist_across_sessions": False}


@mcp.tool()
def get_secret(
    secret_key: str,
    project: str = "",
) -> dict:
    """Retrieve a secret from the OS credential vault (Windows Credential Manager).

    Checks WCM first, then falls back to session facts. If not found anywhere,
    returns a prompt message asking the user to provide the credential.

    Use when: You need a credential (API key, auth token, connection string).
    Call this instead of asking the user — the secret may already be stored.
    Returns: {success, secret_key, value, source} or {success: false, prompt_user: true}.

    Args:
        secret_key: Key name (e.g., 'monash_auth_token', 'voyage_api_key').
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())

    if not secret_key:
        return {"success": False, "error": "secret_key is required"}

    # Try WCM first
    kr = _get_keyring()
    if kr:
        service = _secret_service_name(project, secret_key)
        try:
            value = kr.get_password(service, "secret")
            if value:
                return {
                    "success": True,
                    "secret_key": secret_key,
                    "value": value,
                    "source": "windows_credential_manager",
                    "project": project,
                }
        except Exception:
            pass  # Fall through to session facts

    # Fallback: check session facts
    conn = _safe_db_connect()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT fact_value FROM claude.session_facts sf
                JOIN claude.sessions s ON sf.session_id = s.session_id
                WHERE sf.fact_key = %s AND sf.fact_type = 'credential'
                  AND s.project_name = %s
                ORDER BY sf.created_at DESC LIMIT 1
            """, (secret_key, project))
            row = cur.fetchone()
            if row:
                return {
                    "success": True,
                    "secret_key": secret_key,
                    "value": row[0] if isinstance(row, tuple) else row["fact_value"],
                    "source": "session_fact",
                    "project": project,
                }
        finally:
            conn.close()

    return {
        "success": False,
        "secret_key": secret_key,
        "project": project,
        "prompt_user": True,
        "message": f"Secret '{secret_key}' not found in credential vault or session facts. "
                   f"Please provide it and I'll store it permanently with set_secret().",
    }


@mcp.tool()
def list_secrets(
    project: str = "",
) -> dict:
    """List all registered secrets for a project (keys only, not values).

    Shows what secrets are registered in the vault for this project.
    Does NOT reveal secret values — only the key names and descriptions.

    Use when: Checking what credentials are available, or debugging
    missing credentials at session start.
    Returns: {success, project, secrets: [{secret_key, description, has_value}]}.

    Args:
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())
    secrets = []

    conn = _safe_db_connect()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT secret_key, description, updated_at
                FROM claude.secret_registry
                WHERE project_name = %s
                ORDER BY secret_key
            """, (project,))
            rows = cur.fetchall()
        finally:
            conn.close()
    else:
        rows = []

    kr = _get_keyring()

    for row in rows:
        key = row[0] if isinstance(row, tuple) else row["secret_key"]
        desc = row[1] if isinstance(row, tuple) else row["description"]
        # Check if value actually exists in WCM
        has_value = False
        if kr:
            try:
                service = _secret_service_name(project, key)
                has_value = kr.get_password(service, "secret") is not None
            except Exception:
                pass
        secrets.append({
            "secret_key": key,
            "description": desc or "",
            "has_value": has_value,
        })

    return {
        "success": True,
        "project": project,
        "count": len(secrets),
        "secrets": secrets,
    }


@mcp.tool()
def delete_secret(
    secret_key: str,
    project: str = "",
) -> dict:
    """Delete a secret from the OS credential vault and registry.

    Removes both the WCM entry and the registry row. Use for credential
    rotation cleanup or removing stale entries.

    Use when: A credential is no longer valid or needs to be removed.
    Returns: {success, secret_key, project, deleted_from}.

    Args:
        secret_key: Key name to delete.
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())

    if not secret_key:
        return {"success": False, "error": "secret_key is required"}

    deleted_from = []

    # Delete from WCM
    kr = _get_keyring()
    if kr:
        service = _secret_service_name(project, secret_key)
        try:
            kr.delete_password(service, "secret")
            deleted_from.append("windows_credential_manager")
        except Exception:
            pass  # May not exist

    # Delete from registry
    conn = _safe_db_connect()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM claude.secret_registry
                WHERE project_name = %s AND secret_key = %s
            """, (project, secret_key))
            if cur.rowcount > 0:
                deleted_from.append("secret_registry")
            conn.commit()
        finally:
            conn.close()

    return {
        "success": len(deleted_from) > 0,
        "secret_key": secret_key,
        "project": project,
        "deleted_from": deleted_from,
    }


@mcp.tool()
def load_project_secrets(
    project: str = "",
) -> dict:
    """Load all registered secrets for a project from WCM into session facts.

    Reads the secret registry, retrieves each secret from WCM, and stores
    them as session facts for the current session. Called automatically at
    session start, but can also be called manually.

    Use when: Starting work on a project and need all credentials loaded.
    Normally called by the session startup hook automatically.
    Returns: {success, project, loaded, missing, total}.

    Args:
        project: Project name. Defaults to current directory.
    """
    project = project or os.path.basename(os.getcwd())

    kr = _get_keyring()
    if not kr:
        return {
            "success": False,
            "project": project,
            "error": "No keyring backend available",
            "loaded": 0,
            "missing": 0,
            "total": 0,
        }

    # Get registered secrets
    conn = _safe_db_connect()
    if not conn:
        return {"success": False, "error": "No database connection"}

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT secret_key FROM claude.secret_registry
            WHERE project_name = %s ORDER BY secret_key
        """, (project,))
        rows = cur.fetchall()

        if not rows:
            return {
                "success": True,
                "project": project,
                "loaded": 0,
                "missing": 0,
                "total": 0,
                "message": "No secrets registered for this project",
            }

        loaded = []
        missing = []

        # Get current session ID
        cur.execute("""
            SELECT session_id FROM claude.sessions
            WHERE project_name = %s AND status = 'active'
            ORDER BY session_start DESC LIMIT 1
        """, (project,))
        session_row = cur.fetchone()
        session_id = (session_row[0] if isinstance(session_row, tuple)
                      else session_row["session_id"]) if session_row else None

        for row in rows:
            key = row[0] if isinstance(row, tuple) else row["secret_key"]
            service = _secret_service_name(project, key)
            try:
                value = kr.get_password(service, "secret")
                if value and session_id:
                    # Store as session fact
                    cur.execute("""
                        INSERT INTO claude.session_facts
                            (session_id, fact_key, fact_value, fact_type, is_sensitive)
                        VALUES (%s, %s, %s, 'credential', true)
                        ON CONFLICT (session_id, fact_key)
                        DO UPDATE SET fact_value = EXCLUDED.fact_value
                    """, (session_id, key, value))
                    loaded.append(key)
                else:
                    missing.append(key)
            except Exception:
                missing.append(key)

        conn.commit()

        return {
            "success": True,
            "project": project,
            "loaded": len(loaded),
            "loaded_keys": loaded,
            "missing": len(missing),
            "missing_keys": missing if missing else [],
            "total": len(rows),
        }
    finally:
        conn.close()


# ============================================================================
# Consolidated Tools — Multi-Action Dispatch Pattern
# 97 tools → 32 tools (67% reduction)
# These dispatch wrappers call existing tool functions based on parameters.
# Old tool names remain as-is above — they become aliases in a future phase.
# ============================================================================


def _detect_item_type(code: str) -> str:
    """Detect work item type from short code prefix.

    Args:
        code: Short code like 'BT5', 'F12', 'FB3' or a UUID.

    Returns:
        Item type: 'build_tasks', 'features', or 'feedback'.
    """
    if code.startswith("BT"):
        return "build_tasks"
    elif code.startswith("FB"):
        return "feedback"
    elif code.startswith("F"):
        return "features"
    else:
        return "build_tasks"


# --- Work Tracking (14 old → 3 new) ---

@mcp.tool()
def work_create(
    type: Literal["feature", "feedback", "task", "simple_task"],
    project: str,
    name: str,
    description: str,
    feature_type: Literal["feature", "enhancement", "refactor", "infrastructure", "documentation", "stream"] = "feature",
    plan_data: dict | None = None,
    feedback_type: Literal["bug", "design", "idea", "question", "change", "improvement"] = "bug",
    feature_code: str = "",
    verification: str = "",
    files_affected: list[str] | None = None,
    task_type: Literal["implementation", "testing", "documentation", "deployment", "investigation"] = "implementation",
    blocked_by: str | None = None,
    estimated_hours: float | None = None,
    priority: int = 3,
    title: str = "",
) -> dict:
    """Create any work item: feature, feedback, or task.

    Use when: Creating features, filing bugs/ideas, or adding tasks to features.
    Returns: {success, item_code, item_id, item_type, status}.

    Args:
        type: Item type to create.
        project: Project name.
        name: Item name/title.
        description: Detailed description.
        feature_type: Feature type (feature, enhancement, refactor, infrastructure, documentation, stream).
        plan_data: Optional structured plan data for features.
        feedback_type: Bug, design, idea, question, change, or improvement.
        feature_code: Parent feature code for tasks (e.g., 'F12').
        verification: How to verify task completion (required for type='task').
        files_affected: Files this item affects (required for type='task').
        task_type: Task type (implementation, testing, documentation, deployment, investigation).
        blocked_by: Task code that blocks this one (e.g., 'BT316').
        estimated_hours: Rough estimate for tasks.
        priority: 1=critical, 2=high, 3=normal, 4=low, 5=backlog.
        title: Title override (defaults to name for feedback).
    """
    if type == "feature":
        return create_feature(
            project=project, feature_name=name, description=description,
            feature_type=feature_type, priority=priority, plan_data=plan_data,
        )
    elif type == "feedback":
        priority_map = {1: "high", 2: "high", 3: "medium", 4: "low", 5: "low"}
        return create_feedback(
            project=project, feedback_type=feedback_type, description=description,
            title=name or title, priority=priority_map.get(priority, "medium"),
        )
    elif type == "task":
        return create_linked_task(
            feature_code=feature_code, task_name=name, task_description=description,
            verification=verification, files_affected=files_affected or [],
            task_type=task_type, priority=priority, estimated_hours=estimated_hours,
            blocked_by=blocked_by,
        )
    elif type == "simple_task":
        return add_build_task(
            feature_id=feature_code, task_name=name, task_description=description,
            task_type=task_type, files_affected=files_affected,
            blocked_by_task_id=blocked_by or "",
        )
    else:
        return {"success": False, "error": f"Unknown work type: {type}"}


@mcp.tool()
def work_status(
    item_code: str,
    action: Literal["start", "complete", "advance", "promote", "resolve", "add_dep"],
    new_status: str = "",
    override_reason: str = "",
    feature_name: str = "",
    feature_type: str = "feature",
    plan_data: dict | None = None,
    resolution_note: str = "",
    predecessor_id: str = "",
    successor_id: str = "",
) -> dict:
    """Change status of any work item.

    Use when: Starting/completing tasks, advancing feedback, managing dependencies.
    Returns: {success, item_code, from_status, to_status}.

    Args:
        item_code: Item short code (e.g., 'BT5', 'F12', 'FB3').
        action: Action to take: start, complete, advance, promote, resolve, or add_dep.
        new_status: Target status for advance action.
        override_reason: Reason to bypass condition checks (rare).
        feature_name: Override feature name for promote action.
        feature_type: Feature type for promote action.
        plan_data: Plan data for promote action.
        resolution_note: Note for resolve action.
        predecessor_id: Predecessor item code for add_dep (defaults to item_code).
        successor_id: Successor item code for add_dep.
    """
    if action == "start":
        return start_work(task_code=item_code)
    elif action == "complete":
        return complete_work(task_code=item_code)
    elif action == "advance":
        item_type = _detect_item_type(item_code)
        return advance_status(
            item_type=item_type, item_id=item_code,
            new_status=new_status, override_reason=override_reason,
        )
    elif action == "promote":
        return promote_feedback(
            feedback_id=item_code, feature_name=feature_name,
            feature_type=feature_type, priority=3, plan_data=plan_data,
        )
    elif action == "resolve":
        return resolve_feedback(feedback_id=item_code, resolution_note=resolution_note)
    elif action == "add_dep":
        pred_type = _detect_item_type(predecessor_id or item_code)
        succ_type = _detect_item_type(successor_id)
        return add_dependency(
            predecessor_type=pred_type, predecessor_id=predecessor_id or item_code,
            successor_type=succ_type, successor_id=successor_id,
        )
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


@mcp.tool()
def work_board(
    project: str,
    view: Literal["board", "ready", "todos"] = "board",
) -> dict:
    """Read work tracking state: build board, ready tasks, or incomplete todos.

    Use when: Checking project status, finding next work, reviewing outstanding items.
    Returns: {project, streams/features/tasks} for board; {tasks} for ready; {todos} for todos.

    Args:
        project: Project name.
        view: View type: board (full hierarchy), ready (next tasks), or todos (incomplete).
    """
    if view == "board":
        return get_build_board(project=project)
    elif view == "ready":
        return get_ready_tasks(project=project)
    elif view == "todos":
        return get_incomplete_todos(project=project)
    else:
        return {"success": False, "error": f"Unknown view: {view}"}


# --- Memory Management (8 old → 1 new, remember + recall_memories stay) ---

@mcp.tool()
def memory_manage(
    action: Literal["list", "update", "archive", "merge", "mark_applied", "consolidate"],
    memory_id: str = "",
    content: str = "",
    title: str = "",
    tier: str = "",
    memory_type: str = "",
    reason: str = "",
    keep_id: str = "",
    archive_id: str = "",
    success: bool = True,
    project: str = "",
    tier_filter: str = "",
    memory_type_filter: str = "",
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
    trigger: Literal["session_end", "periodic", "manual"] = "session_end",
    project_name: str = "",
) -> dict:
    """Memory admin operations: list, update, archive, merge, mark applied, consolidate.

    Use when: Managing stored memories, fixing stale entries, deduplicating, running lifecycle.
    Returns: {success, action_result}.

    Args:
        action: Operation to perform.
        memory_id: Target memory UUID (for update/archive/mark_applied).
        content: New content for update (re-embeds automatically).
        title: New title for update.
        tier: New tier for update ('mid' or 'long').
        memory_type: New type for update.
        reason: Reason for archive or merge.
        keep_id: Memory to keep in merge.
        archive_id: Memory to archive in merge.
        success: Whether knowledge application was successful (mark_applied).
        project: Project filter for list.
        tier_filter: Tier filter for list.
        memory_type_filter: Type filter for list.
        include_archived: Include archived in list.
        limit: Max results for list.
        offset: Pagination offset for list.
        trigger: Consolidation trigger mode.
        project_name: Project for consolidation.
    """
    if action == "list":
        return list_memories(
            project=project, tier=tier_filter, memory_type=memory_type_filter,
            include_archived=include_archived, limit=limit, offset=offset,
        )
    elif action == "update":
        return update_memory(
            memory_id=memory_id, content=content, title=title,
            tier=tier, memory_type=memory_type,
        )
    elif action == "archive":
        return archive_memory(memory_id=memory_id, reason=reason)
    elif action == "merge":
        return merge_memories(keep_id=keep_id, archive_id=archive_id, reason=reason)
    elif action == "mark_applied":
        return mark_knowledge_applied(knowledge_id=memory_id, success=success)
    elif action == "consolidate":
        return consolidate_memories(trigger=trigger, project_name=project_name or project)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# --- Session Facts (4 old → 1 new, store_session_fact stays) ---

@mcp.tool()
def session_facts(
    fact_key: str = "",
    project_name: str = "",
    include_sensitive: bool = False,
    n_sessions: int = 0,
    fact_types: list[str] | None = None,
) -> dict:
    """Read session facts: recall one, list all, or recall from previous sessions.

    Use when: Retrieving notepad entries from this or prior sessions.
    Returns: {success, fact_key, fact_value} or {facts} or {sessions_checked}.

    Args:
        fact_key: Specific fact key to recall. If provided, recalls that fact.
        project_name: Project name filter.
        include_sensitive: Include sensitive values in list.
        n_sessions: If >0, search previous N sessions instead of current.
        fact_types: Filter by fact types (for previous session recall).
    """
    if fact_key:
        return recall_session_fact(fact_key=fact_key, project_name=project_name)
    elif n_sessions > 0:
        return recall_previous_session_facts(
            project_name=project_name, n_sessions=n_sessions, fact_types=fact_types,
        )
    else:
        return list_session_facts(project_name=project_name, include_sensitive=include_sensitive)


# --- Session Lifecycle (6 old → 1 new, start/end_session stay) ---

@mcp.tool()
def session_manage(
    action: Literal["checkpoint", "recover", "store_notes", "get_notes", "search_conversations", "extract_conversation", "extract_insights"],
    focus: str = "",
    progress_notes: str = "",
    content: str = "",
    section: Literal["general", "decisions", "progress", "blockers", "findings"] = "general",
    append: bool = True,
    query: str = "",
    date_range_days: int | None = None,
    limit: int = 10,
    session_id: str = "",
    project: str = "",
) -> dict:
    """Session management: checkpoint, recovery, notes, conversation search/extract.

    Use when: Saving mid-session progress, recovering from crashes, managing notes, searching history.
    Returns: {success, action_result}.

    Args:
        action: Operation to perform.
        focus: Current focus for checkpoint.
        progress_notes: Progress notes for checkpoint.
        content: Note content for store_notes.
        section: Note section for store/get notes.
        append: Append to section (True) or replace (False).
        query: Search query for search_conversations.
        date_range_days: Limit conversation search to last N days.
        limit: Max results for search.
        session_id: Session ID for extract operations.
        project: Project name.
    """
    if action == "checkpoint":
        return save_checkpoint(focus=focus, progress_notes=progress_notes, project=project)
    elif action == "recover":
        return recover_session(project=project)
    elif action == "store_notes":
        return store_session_notes(content=content, section=section, append=append)
    elif action == "get_notes":
        return get_session_notes(section=section)
    elif action == "search_conversations":
        return search_conversations(query=query, project=project, date_range_days=date_range_days, limit=limit)
    elif action == "extract_conversation":
        return extract_conversation(session_id=session_id, project=project)
    elif action == "extract_insights":
        return extract_insights(session_id=session_id, project=project)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# --- Workfiles (6 old → 2 new) ---

@mcp.tool()
def workfile_store(
    component: str,
    title: str,
    content: str = "",
    project: str = "",
    workfile_type: str = "notes",
    tags: list[str] | None = None,
    feature_code: str | None = None,
    is_pinned: bool = False,
    mode: Literal["replace", "append", "archive", "delete"] = "replace",
) -> dict:
    """Store, archive, or delete workfiles in the filing cabinet.

    Use when: Saving component working notes, archiving stale files, or deleting wrong content.
    Returns: {success, workfile_id, action}.

    Args:
        component: Drawer name (e.g., 'auth-flow', 'parallel-runner').
        title: File title within component.
        content: Content to store (required for replace/append).
        project: Project name. Defaults to current directory.
        workfile_type: notes, findings, questions, approach, investigation, or reference.
        tags: Optional tags for categorization.
        feature_code: Optional link to a feature (e.g., 'F12').
        is_pinned: If True, auto-surfaces at session start.
        mode: replace (overwrite), append (add to end), archive (soft-delete), delete (hard-delete).
    """
    if mode == "archive":
        return archive_workfile(component=component, title=title, project=project)
    elif mode == "delete":
        return delete_workfile(component=component, title=title, project=project)
    else:
        return stash(
            component=component, title=title, content=content, project=project,
            workfile_type=workfile_type, tags=tags, feature_code=feature_code,
            is_pinned=is_pinned, mode=mode,
        )


@mcp.tool()
def workfile_read(
    query: str = "",
    component: str = "",
    title: str = "",
    project: str = "",
    is_active: bool = True,
    limit: int = 5,
) -> dict:
    """Read, search, or list workfiles from the filing cabinet.

    Use when: Loading component context, finding notes by topic, browsing drawers.
    Returns: {success, files} or {success, components}.

    Args:
        query: Semantic search query. If provided, searches across all workfiles.
        component: Drawer name. If provided, reads files from this component.
        title: Specific file within component.
        project: Project name. Defaults to current directory.
        is_active: Filter by active status (default True).
        limit: Max results for search.
    """
    if query:
        return search_workfiles(query=query, project=project, component=component, limit=limit)
    elif component:
        return unstash(component=component, title=title, project=project)
    else:
        return list_workfiles(project=project, component=component, is_active=is_active)


# --- Entities (4 old → 2 new) ---

@mcp.tool()
def entity_store(
    entity_type: str = "",
    properties: dict | None = None,
    entity_id: str = "",
    entity_name: str = "",
    patch: dict | None = None,
    tags: list[str] | None = None,
    is_archived: bool | None = None,
    project: str = "",
    relationships: list[dict] | None = None,
) -> dict:
    """Create or update entities in the reference library.

    Use when: Cataloging structured data (API endpoints, OData entities, domain concepts) or patching existing entities.
    Returns: {success, entity_id, action}.

    Args:
        entity_type: Type name for new entities (e.g., 'odata_entity', 'domain_concept').
        properties: JSONB properties for new entities.
        entity_id: UUID for updating existing entity.
        entity_name: Name lookup for updating (case-insensitive).
        patch: Targeted property patches (set/append/remove/remove_key operations).
        tags: Tags for filtering.
        is_archived: Set archive status.
        project: Project scope.
        relationships: List of {to_entity_id, relationship_type} for new entities.
    """
    if entity_id or entity_name or patch:
        return update_entity(
            entity_id=entity_id, entity_name=entity_name, entity_type=entity_type,
            patch=patch, tags=tags, is_archived=is_archived,
        )
    elif entity_type and properties:
        return catalog(
            entity_type=entity_type, properties=properties, project=project,
            tags=tags, relationships=relationships,
        )
    else:
        return {"success": False, "error": "Provide entity_type+properties to create, or entity_id/entity_name+patch to update"}


@mcp.tool()
def entity_read(
    query: str = "",
    entity_type: str = "",
    entity_id: str = "",
    tags: list | None = None,
    project: str = "",
    detail: Literal["summary", "full"] = "summary",
    limit: int = 10,
    page: int = 1,
    page_size: int = 30,
    min_similarity: float = 0.5,
) -> dict:
    """Search or browse entities in the reference library.

    Use when: Finding structured data by meaning, browsing by type, or viewing entity details.
    Returns: {success, results} or {success, tree} or {success, entity}.

    Args:
        query: Semantic search query.
        entity_type: Filter by type name.
        entity_id: Specific entity UUID for detail view.
        tags: Filter by tags.
        project: Project filter.
        detail: 'summary' (compact) or 'full' (all properties).
        limit: Max search results.
        page: Page number for browsing.
        page_size: Entities per page.
        min_similarity: Minimum vector similarity threshold.
    """
    if entity_id and not query:
        return explore_entities(entity_id=entity_id, project=project)
    elif query:
        return recall_entities(
            query=query, entity_type=entity_type, project=project, tags=tags,
            limit=limit, min_similarity=min_similarity, detail=detail, entity_id=entity_id,
        )
    elif entity_type or tags:
        return explore_entities(
            tags=tags, entity_type=entity_type, project=project,
            page=page, page_size=page_size,
        )
    else:
        return explore_entities(project=project, page=page, page_size=page_size)


# --- Articles (5 old → 2 new) ---

@mcp.tool()
def article_write(
    title: str = "",
    abstract: str = "",
    article_id: str = "",
    article_type: str = "research",
    tags: list | None = None,
    project: str = "",
    project_ids: list | None = None,
    section_title: str = "",
    section_body: str = "",
    section_id: str = "",
    section_order: int = 0,
    summary: str = "",
    linked_entity_ids: list | None = None,
    change_reason: str = "",
    status_action: Literal["", "publish", "archive", "revert_draft", "info"] = "",
) -> dict:
    """Create/update knowledge articles, sections, and lifecycle.

    Use when: Writing narrative knowledge, adding sections, or managing article lifecycle.
    Returns: {success, article_id} or {success, section_id}.

    Args:
        title: Article title (required for new articles).
        abstract: Article summary (required for new articles).
        article_id: Existing article UUID for updates.
        article_type: investigation, reference, tutorial, architecture, or research.
        tags: Classification tags.
        project: Project name.
        project_ids: Project UUIDs this article relates to.
        section_title: Section title (triggers section write).
        section_body: Section content (triggers section write).
        section_id: Existing section UUID for updates.
        section_order: Position in reading order.
        summary: Section summary for index.
        linked_entity_ids: Entity UUIDs discussed in section.
        change_reason: Why section was updated (version history).
        status_action: Lifecycle action: publish, archive, revert_draft, or info.
    """
    if status_action:
        return manage_article(article_id=article_id, action=status_action)
    elif section_title and section_body:
        return write_article_section(
            article_id=article_id, title=section_title, body=section_body,
            section_order=section_order, summary=summary,
            linked_entity_ids=linked_entity_ids, section_id=section_id,
            change_reason=change_reason,
        )
    elif title:
        return write_article(
            title=title, abstract=abstract, article_type=article_type,
            tags=tags, project_ids=project_ids, article_id=article_id, project=project,
        )
    else:
        return {"success": False, "error": "Provide title+abstract for article, section_title+section_body for section, or status_action for lifecycle"}


@mcp.tool()
def article_read(
    query: str = "",
    article_id: str = "",
    section_id: str = "",
    project: str = "",
    article_type: str = "",
    entity_id: str = "",
    tags: list | None = None,
    limit: int = 5,
) -> dict:
    """Search or read knowledge articles.

    Use when: Finding narrative knowledge or reading specific articles/sections.
    Returns: {success, results} for search or {success, content} for read.

    Args:
        query: Semantic search query.
        article_id: Specific article UUID to read.
        section_id: Specific section within article.
        project: Project filter.
        article_type: Filter by article type.
        entity_id: Find articles linked to this entity.
        tags: Filter by tags.
        limit: Max search results.
    """
    if article_id:
        return read_article(article_id=article_id, section_id=section_id)
    elif query:
        return recall_articles(
            query=query, project=project, article_type=article_type,
            entity_id=entity_id, tags=tags, limit=limit,
        )
    else:
        return {"success": False, "error": "Provide query for search or article_id to read"}


# --- Messaging (8 old → 2 new) ---

@mcp.tool()
def inbox(
    view: Literal["pending", "unactioned", "history"] = "pending",
    project_name: str = "",
    message_id: str = "",
    message_ids: list[str] | None = None,
    ack_action: Literal["", "read", "acknowledged", "actioned", "deferred"] = "",
    project_id: str = "",
    defer_reason: str = "",
    priority: int = 3,
    days: int = 7,
    message_type: str = "",
    limit: int = 50,
    session_id: str = "",
    include_broadcasts: bool = True,
    include_read: bool = False,
) -> dict:
    """Check, search, and manage incoming messages from other Claude instances.

    Use when: Checking inbox, acknowledging messages, or reviewing message history.
    Returns: {count, messages} or {success, acknowledged_count}.

    Args:
        view: View type: pending (unread), unactioned (needs response), history (past messages).
        project_name: Project name filter.
        message_id: Single message ID to acknowledge.
        message_ids: Multiple message IDs to bulk acknowledge.
        ack_action: Acknowledge action: read, acknowledged, actioned, deferred.
        project_id: Project UUID for actioned acks (creates todo).
        defer_reason: Reason for deferred acks.
        priority: Priority for actioned ack todos.
        days: History lookback days.
        message_type: Filter history by message type.
        limit: Max history results.
        session_id: Filter by session.
        include_broadcasts: Include broadcast messages in pending.
        include_read: Include already-read messages in pending.
    """
    if message_ids:
        return bulk_acknowledge(message_ids=message_ids, action=ack_action or "read")
    if message_id:
        return acknowledge(
            message_id=message_id, action=ack_action or "read",
            project_id=project_id, defer_reason=defer_reason, priority=priority,
        )
    if view == "history":
        return get_message_history(
            project_name=project_name, days=days, message_type=message_type, limit=limit,
        )
    if view == "unactioned":
        return get_unactioned_messages(project_name=project_name)
    return check_inbox(
        project_name=project_name, session_id=session_id,
        include_broadcasts=include_broadcasts, include_read=include_read,
    )


@mcp.tool()
def send_msg(
    body: str,
    message_type: Literal["task_request", "status_update", "question", "notification", "handoff", "broadcast"] = "notification",
    to_project: str = "",
    subject: str = "",
    priority: Literal["urgent", "normal", "low"] = "normal",
    reply_to_id: str = "",
    thread_status: str = "",
    is_broadcast: bool = False,
    from_project: str = "",
    from_session_id: str = "",
    to_session_id: str = "",
    parent_message_id: str = "",
    metadata: dict | None = None,
    conversation_mode: str = "fire_and_forget",
) -> dict:
    """Send a message, reply, or broadcast to other Claude instances.

    Use when: Communicating with other instances, replying, or broadcasting.
    Returns: {success, message_id, created_at}.

    Args:
        body: Message content.
        message_type: Type of message.
        to_project: Target project name.
        subject: Message subject.
        priority: Message priority.
        reply_to_id: Original message ID to reply to (triggers reply mode).
        thread_status: Thread lifecycle marker for replies.
        is_broadcast: If True, broadcast to all instances.
        from_project: Sender project name.
        from_session_id: Sender session ID.
        to_session_id: Target session ID.
        parent_message_id: Parent message for threading.
        metadata: Optional metadata dict.
        conversation_mode: Conversation protocol mode.
    """
    if is_broadcast:
        return broadcast(
            body=body, subject=subject, from_session_id=from_session_id,
            from_project=from_project, priority=priority,
        )
    if reply_to_id:
        return reply_to(
            original_message_id=reply_to_id, body=body,
            from_session_id=from_session_id, from_project=from_project,
            message_type=message_type, thread_status=thread_status,
        )
    return send_message(
        message_type=message_type, body=body, subject=subject,
        to_project=to_project, to_session_id=to_session_id, priority=priority,
        from_session_id=from_session_id, from_project=from_project,
        parent_message_id=parent_message_id, metadata=metadata,
        conversation_mode=conversation_mode,
    )


# --- Secrets (5 old → 1 new) ---

@mcp.tool()
def secret(
    action: Literal["get", "set", "list", "delete", "load_all"],
    secret_key: str = "",
    secret_value: str = "",
    description: str = "",
    project: str = "",
) -> dict:
    """Manage credentials in the OS credential vault (Windows Credential Manager).

    Use when: Storing, retrieving, listing, or deleting API keys, tokens, and credentials.
    Returns: {success, secret_key, value} or {success, secrets} or {success, loaded}.

    Args:
        action: Operation: get, set, list, delete, or load_all.
        secret_key: Key name (required for get/set/delete).
        secret_value: Secret value (required for set).
        description: Description of what this secret is for (set only).
        project: Project name. Defaults to current directory.
    """
    if action == "get":
        return get_secret(secret_key=secret_key, project=project)
    elif action == "set":
        return set_secret(
            secret_key=secret_key, secret_value=secret_value,
            project=project, description=description,
        )
    elif action == "list":
        return list_secrets(project=project)
    elif action == "delete":
        return delete_secret(secret_key=secret_key, project=project)
    elif action == "load_all":
        return load_project_secrets(project=project)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# --- Config (4 old → 1 new) ---

@mcp.tool()
def config_manage(
    action: Literal["update_section", "deploy_claude_md", "deploy_project", "regenerate_settings"],
    project: str,
    section: str = "",
    content: str = "",
    mode: Literal["replace", "append"] = "replace",
    components: list[str] | None = None,
) -> dict:
    """Manage project configuration and deployment.

    Use when: Updating CLAUDE.md sections, deploying configs, or regenerating settings.
    Returns: {success, diff_summary} or {success, deployed_components}.

    Args:
        action: Operation to perform.
        project: Project name.
        section: CLAUDE.md section name (for update_section).
        content: Content to write (for update_section).
        mode: 'replace' or 'append' (for update_section).
        components: Components to deploy (for deploy_project).
    """
    if action == "update_section":
        return update_claude_md(project=project, section=section, content=content, mode=mode)
    elif action == "deploy_claude_md":
        return deploy_claude_md(project=project)
    elif action == "deploy_project":
        return deploy_project(project=project, components=components)
    elif action == "regenerate_settings":
        return regenerate_settings(project=project)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# --- Code Intelligence (8 old → 2 new) ---

@mcp.tool()
def code_search(
    query: str = "",
    name: str = "",
    symbol_id: str = "",
    project: str = "",
    file_path: str = "",
    kind: str = "",
    limit: int = 20,
) -> dict:
    """Search code symbols by name, meaning, or structure.

    Use when: Finding functions/classes, checking name collisions, exploring module structure.
    Returns: {success, symbols} or {success, has_collision} or {success, files}.

    Args:
        query: Semantic search query.
        name: Check if symbol name exists (collision detection).
        symbol_id: Find symbols similar to this one.
        project: Project filter.
        file_path: Get module structure for file (or exclude from collision check).
        kind: Filter by symbol kind (function, class, method, etc.).
        limit: Max results.
    """
    if name:
        return check_collision(name=name, project=project, file_path=file_path)
    elif symbol_id:
        return find_similar(symbol_id=symbol_id, limit=limit)
    elif file_path and not query and not name and not symbol_id:
        return get_module_map(project=project, file_path=file_path)
    elif query:
        return find_symbol(query=query, project=project, kind=kind, limit=limit)
    else:
        return get_module_map(project=project)


@mcp.tool()
def code_context(
    symbol_name: str = "",
    symbol_id: str = "",
    project: str = "",
    depth: int = 1,
    direction: str = "both",
) -> dict:
    """Get deep symbol analysis: full context, callers, callees, and dependency graph.

    Use when: Understanding symbol usage, preparing to modify code, tracing call chains.
    Returns: {success, symbol, body, callers, callees} or {success, root, edges}.

    Args:
        symbol_name: Get full context (body, callers, callees, siblings).
        symbol_id: Get dependency graph (walk reference graph).
        project: Project name.
        depth: How many levels to traverse (1=direct, 2=transitive).
        direction: For dependency graph: 'incoming', 'outgoing', or 'both'.
    """
    if symbol_name:
        return get_context(symbol_name=symbol_name, project=project, depth=depth)
    elif symbol_id:
        return get_dependency_graph(symbol_id=symbol_id, depth=depth, direction=direction)
    else:
        return {"success": False, "error": "Provide symbol_name for context or symbol_id for dependency graph"}


# --- Books (3 old → 2 new) ---

@mcp.tool()
def book_store(
    book_title: str,
    author: str = "",
    isbn: str = "",
    year: int | None = None,
    topics: list[str] | None = None,
    summary: str = "",
    concept: str = "",
    chapter: str = "",
    page_range: str = "",
    description: str = "",
    quote: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Store books and references in the reference library.

    Use when: Adding a new book or capturing specific concepts/quotes from books.
    Returns: {success, book_id} or {success, ref_id}.

    Args:
        book_title: Title of the book (required).
        author: Book author.
        isbn: ISBN identifier.
        year: Publication year.
        topics: Topic tags for the book.
        summary: Brief summary of the book.
        concept: Concept/idea from the book (if provided, stores a reference instead).
        chapter: Chapter for the reference.
        page_range: Pages for the reference.
        description: Explanation of the concept.
        quote: Direct quote from the book.
        tags: Tags for the reference.
    """
    if concept:
        return store_book_reference(
            book_title=book_title, concept=concept, chapter=chapter,
            page_range=page_range, description=description, quote=quote, tags=tags,
        )
    else:
        return store_book(
            title=book_title, author=author, isbn=isbn,
            year=year, topics=topics, summary=summary,
        )


@mcp.tool()
def book_read(
    query: str,
    book_title: str = "",
    tags: list[str] | None = None,
    limit: int = 5,
) -> dict:
    """Search book references using semantic similarity.

    Use when: Looking for ideas or patterns from books.
    Returns: {success, references}.

    Args:
        query: Natural language search query.
        book_title: Optional filter by book title.
        tags: Filter by tags.
        limit: Max results.
    """
    return recall_book_reference(query=query, book_title=book_title, tags=tags, limit=limit)


# --- Knowledge Graph (4 old → 1 new) ---

@mcp.tool()
def link(
    from_knowledge_id: str = "",
    to_knowledge_id: str = "",
    relation_type: Literal["", "extends", "contradicts", "supports", "supersedes", "depends_on", "relates_to", "part_of", "caused_by"] = "",
    strength: float = 1.0,
    notes: str = "",
    from_type: str = "",
    from_id: str = "",
    to_type: str = "",
    to_id: str = "",
    link_type: str = "related_to",
    metadata: dict | None = None,
    knowledge_id: str = "",
    resource_type: str = "",
    resource_id: str = "",
    direction: str = "both",
    include_reverse: bool = True,
    relation_types: list[str] | None = None,
) -> dict:
    """Create or read links between resources and knowledge entries.

    Use when: Connecting related knowledge, linking resources, or exploring relationships.
    Returns: {success, relation_id} or {success, link_id} or {success, relations/links}.

    Args:
        from_knowledge_id: Source knowledge UUID (creates knowledge link).
        to_knowledge_id: Target knowledge UUID (creates knowledge link).
        relation_type: Relation type for knowledge links.
        strength: Link strength 0-1.
        notes: Notes about the relation.
        from_type: Source resource type (creates resource link).
        from_id: Source resource UUID.
        to_type: Target resource type.
        to_id: Target resource UUID.
        link_type: Relationship type for resource links.
        metadata: Optional metadata for resource links.
        knowledge_id: Get relations for this knowledge entry (read mode).
        resource_type: Resource type to query (read mode).
        resource_id: Resource UUID to query (read mode).
        direction: 'both', 'incoming', or 'outgoing' for reads.
        include_reverse: Include incoming relations for knowledge reads.
        relation_types: Filter by relation types for knowledge reads.
    """
    if from_knowledge_id and to_knowledge_id:
        return link_knowledge(
            from_knowledge_id=from_knowledge_id, to_knowledge_id=to_knowledge_id,
            relation_type=relation_type, strength=strength, notes=notes,
        )
    elif from_type and from_id and to_type and to_id:
        return link_resources(
            from_type=from_type, from_id=from_id, to_type=to_type, to_id=to_id,
            link_type=link_type, strength=strength, metadata=metadata,
        )
    elif knowledge_id:
        return get_related_knowledge(
            knowledge_id=knowledge_id, relation_types=relation_types,
            include_reverse=include_reverse,
        )
    elif resource_type and resource_id:
        return get_linked_resources(
            resource_type=resource_type, resource_id=resource_id,
            link_type=link_type, direction=direction,
        )
    else:
        return {"success": False, "error": "Provide from/to IDs to create a link, or knowledge_id/resource_id to read links"}


# --- BPMN (2 old → 1 new, sync becomes background) ---

@mcp.tool()
def bpmn_search(
    query: str,
    project: str = "",
    level: str = "",
    category: str = "",
    client_domain: str = "",
    limit: int = 10,
) -> dict:
    """Search BPMN processes using semantic similarity.

    Use when: Finding processes by keyword, understanding workflow relationships.
    Returns: {success, processes}.

    Args:
        query: Natural language search query.
        project: Filter by project name.
        level: Filter by level (L0, L1, L2).
        category: Filter by category.
        client_domain: Filter by client domain.
        limit: Max results.
    """
    return search_bpmn_processes(
        query=query, project=project, level=level,
        category=category, client_domain=client_domain, limit=limit,
    )


# --- Protocol (3 old → 1 new) ---

@mcp.tool()
def protocol(
    content: str = "",
    change_reason: str = "",
    protocol_name: str = "CORE_PROTOCOL",
    limit: int = 0,
) -> dict:
    """Protocol version management: view, history, or update.

    Use when: Checking active protocol, viewing history, or updating protocol content.
    Returns: {success, content} or {success, versions} or {success, new_version}.

    Args:
        content: New protocol content (triggers update).
        change_reason: Why this change was made (required with content).
        protocol_name: Protocol to manage (default: CORE_PROTOCOL).
        limit: Number of history versions to return (triggers history view).
    """
    if content and change_reason:
        return update_protocol(content=content, change_reason=change_reason, protocol_name=protocol_name)
    elif limit > 0:
        return get_protocol_history(protocol_name=protocol_name, limit=limit)
    else:
        return get_active_protocol(protocol_name=protocol_name)


# --- System (3 old → 1 new) ---

@mcp.tool()
def system_info(
    view: Literal["channel", "sessions", "recipients"] = "sessions",
) -> dict:
    """Check system status: channel connectivity, active sessions, or message recipients.

    Use when: Checking who's online, verifying messaging, or discovering recipients.
    Returns: {connected} or {count, sessions} or {count, recipients}.

    Args:
        view: What to check: channel (messaging status), sessions (who's active), recipients (valid targets).
    """
    if view == "channel":
        return channel_status()
    elif view == "sessions":
        return get_active_sessions()
    elif view == "recipients":
        return list_recipients()
    else:
        return {"success": False, "error": f"Unknown view: {view}"}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Embedding now uses shared HTTP service (embedding_service.py) by default.
    # No in-process model loading needed — saves ~1.4GB RAM per instance.
    # Fallback to in-process FastEmbed if service is unavailable.
    import sys as _sys
    _scripts = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
    if os.path.abspath(_scripts) not in _sys.path:
        _sys.path.insert(0, os.path.abspath(_scripts))
    from embedding_provider import get_provider_info
    info = get_provider_info()
    print(f"[server_v2] Embedding provider: {info['provider']} (local={info['local']})", file=_sys.stderr)
    mcp.run(transport="stdio")
