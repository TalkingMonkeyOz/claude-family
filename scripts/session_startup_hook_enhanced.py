#!/usr/bin/env python3
"""
Session Startup Hook Script for claude-family-core plugin.

This is called automatically via SessionStart hook.
- Logs session to PostgreSQL
- Loads recent session context
- Checks for pending messages
- Shows "where we left off" state (todo list, focus, pending actions)
- Outputs JSON for Claude Code to consume
"""

import json
import os
import sys
from datetime import datetime

# Try to import psycopg for database access
DB_AVAILABLE = False
try:
    import psycopg
    from psycopg.rows import dict_row
    DB_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        DB_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        DB_AVAILABLE = False

# Known identity mapping
IDENTITY_MAP = {
    'claude-code-unified': 'ff32276f-9d05-4a18-b092-31b54c82fff9',
    'claude-desktop': '3be37dfb-c3bb-4303-9bf1-952c7287263f',
}

def get_db_connection():
    """Get PostgreSQL connection. Tries multiple connection strings."""
    conn_strings = [
        os.environ.get('DATABASE_URI'),
        os.environ.get('POSTGRES_CONNECTION_STRING'),
        # Known working connection string
        'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation',
        'postgresql://postgres:postgres@localhost:5432/ai_company_foundation',
    ]

    last_error = None
    for conn_string in conn_strings:
        if not conn_string:
            continue
        try:
            if PSYCOPG_VERSION == 3:
                return psycopg.connect(conn_string, row_factory=dict_row)
            else:
                return psycopg.connect(conn_string, cursor_factory=RealDictCursor)
        except Exception as e:
            last_error = e
            continue

    raise last_error if last_error else Exception("No valid connection string")

def log_session_start(project_name: str, identity_id: str) -> str:
    """Log session start to database, return session_id."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude_family.session_history
            (identity_id, session_start, project_name, session_summary)
            VALUES (%s, NOW(), %s, 'Session auto-started via hook')
            RETURNING session_id::text
        """, (identity_id, project_name))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return result['session_id'] if result else None
    except Exception as e:
        return None

def get_recent_sessions(project_name: str, limit: int = 3) -> list:
    """Get recent session summaries for this project."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT session_summary, session_start,
                   COALESCE(array_to_string(tasks_completed, ', '), '') as tasks
            FROM claude_family.session_history
            WHERE project_name = %s AND session_summary IS NOT NULL
            ORDER BY session_start DESC
            LIMIT %s
        """, (project_name, limit))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in results]
    except Exception:
        return []

def check_pending_messages(project_name: str) -> int:
    """Check for pending messages for this project."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as count
            FROM claude_family.instance_messages
            WHERE status = 'pending'
              AND (to_project = %s OR (to_session_id IS NULL AND to_project IS NULL))
        """, (project_name,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result['count'] if result else 0
    except Exception:
        return 0

def get_session_state(project_name: str) -> dict:
    """Get the saved session state (where we left off) for this project."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                todo_list,
                current_focus,
                files_modified,
                pending_actions,
                updated_at
            FROM claude_family.session_state
            WHERE project_name = %s
        """, (project_name,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return dict(result) if result else None
    except Exception:
        return None

def format_todo_list(todo_list: list) -> list:
    """Format todo list items for display."""
    lines = []
    if not todo_list:
        return lines

    for item in todo_list:
        status = item.get('status', 'pending')
        content = item.get('content', '')
        if status == 'completed':
            lines.append(f"  [x] {content}")
        elif status == 'in_progress':
            lines.append(f"  [>] {content} (in progress)")
        else:
            lines.append(f"  [ ] {content}")
    return lines

def main():
    """Run session startup with full automation."""

    result = {
        "additionalContext": "",
        "systemMessage": ""
    }

    context_lines = []

    # Get current directory to determine project
    cwd = os.getcwd()
    project_name = os.path.basename(cwd)

    # Determine identity (default to unified)
    identity_name = 'claude-code-unified'
    identity_id = IDENTITY_MAP.get(identity_name, IDENTITY_MAP['claude-code-unified'])

    context_lines.append(f"=== Claude Family Session Started ===")
    context_lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    context_lines.append(f"Project: {project_name}")
    context_lines.append(f"Identity: {identity_name}")

    if DB_AVAILABLE:
        # Log session to database
        session_id = log_session_start(project_name, identity_id)
        if session_id:
            context_lines.append(f"Session ID: {session_id}")
            context_lines.append("Session logged to database")
        else:
            context_lines.append("Could not log session to database")

        # === WHERE WE LEFT OFF ===
        state = get_session_state(project_name)
        if state:
            context_lines.append("")
            context_lines.append("=== WHERE WE LEFT OFF ===")

            # Last updated
            if state.get('updated_at'):
                updated = state['updated_at'].strftime('%Y-%m-%d %H:%M')
                context_lines.append(f"Last saved: {updated}")

            # Current focus
            if state.get('current_focus'):
                context_lines.append(f"Focus: {state['current_focus']}")

            # Todo list
            if state.get('todo_list'):
                context_lines.append("")
                context_lines.append("Todo List:")
                todo_lines = format_todo_list(state['todo_list'])
                context_lines.extend(todo_lines)

            # Pending actions
            if state.get('pending_actions'):
                context_lines.append("")
                context_lines.append("Pending Actions:")
                for action in state['pending_actions'][:5]:
                    context_lines.append(f"  - {action}")

            # Files modified
            if state.get('files_modified'):
                context_lines.append("")
                context_lines.append(f"Files touched: {len(state['files_modified'])} files")
                for f in state['files_modified'][:3]:
                    context_lines.append(f"  - {f}")
                if len(state['files_modified']) > 3:
                    context_lines.append(f"  ... and {len(state['files_modified']) - 3} more")

        # Load recent context
        recent = get_recent_sessions(project_name)
        if recent:
            context_lines.append("")
            context_lines.append("=== Recent Sessions ===")
            for i, session in enumerate(recent, 1):
                date = session['session_start'].strftime('%Y-%m-%d') if session.get('session_start') else 'Unknown'
                summary = session.get('session_summary', '')[:100]
                context_lines.append(f"{i}. [{date}] {summary}...")

        # Check messages
        msg_count = check_pending_messages(project_name)
        if msg_count > 0:
            context_lines.append("")
            context_lines.append(f"Pending messages: {msg_count} - use mcp__orchestrator__check_inbox")
    else:
        context_lines.append("Database not available (psycopg not installed)")
        context_lines.append("Manual /session-start required for full context")

    # Check for CLAUDE.md
    claude_md = os.path.join(cwd, "CLAUDE.md")
    if os.path.exists(claude_md):
        context_lines.append("")
        context_lines.append("CLAUDE.md found - project instructions loaded")

    result["additionalContext"] = "\n".join(context_lines)
    result["systemMessage"] = f"Claude Family session started for {project_name}. Session logged to database."

    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
