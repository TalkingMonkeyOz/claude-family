#!/usr/bin/env python3
"""
Session Startup Hook Script for claude-family-core plugin.

This is called automatically via SessionStart hook.
- Checks for saved session state (todo list, focus)
- Checks for pending messages
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


def get_db_connection():
    """Get PostgreSQL connection."""
    conn_strings = [
        os.environ.get('DATABASE_URL'),
        'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation',
    ]

    for conn_str in conn_strings:
        if not conn_str:
            continue
        try:
            if PSYCOPG_VERSION == 3:
                return psycopg.connect(conn_str, row_factory=dict_row)
            else:
                return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
        except:
            continue
    return None


def get_session_state(project_name):
    """Get saved session state for project."""
    if not DB_AVAILABLE:
        return None

    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT todo_list, current_focus, files_modified, pending_actions, updated_at
            FROM claude_family.session_state
            WHERE project_name = %s
        """, (project_name,))

        row = cur.fetchone()
        conn.close()

        if row:
            return dict(row) if PSYCOPG_VERSION == 3 else row
        return None
    except Exception as e:
        return None


def get_pending_messages(project_name):
    """Check for pending messages."""
    if not DB_AVAILABLE:
        return 0

    conn = get_db_connection()
    if not conn:
        return 0

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as count
            FROM claude_family.instance_messages
            WHERE status = 'pending'
              AND (to_project = %s OR to_project IS NULL)
        """, (project_name,))

        row = cur.fetchone()
        conn.close()

        if row:
            return row['count'] if isinstance(row, dict) else row[0]
        return 0
    except:
        return 0


def main():
    """Run startup checks and output JSON context."""

    is_resume = '--resume' in sys.argv

    result = {
        "additionalContext": "",
        "systemMessage": ""
    }

    context_lines = []

    # Get current directory to determine project
    cwd = os.getcwd()
    project_name = os.path.basename(cwd)

    context_lines.append(f"=== Claude Family Session {'Resumed' if is_resume else 'Started'} ===")
    context_lines.append(f"Project: {project_name}")
    context_lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    context_lines.append("")

    # Check for saved session state
    state = get_session_state(project_name)
    if state:
        context_lines.append("📋 PREVIOUS SESSION STATE FOUND:")
        if state.get('current_focus'):
            context_lines.append(f"   Focus: {state['current_focus']}")
        if state.get('todo_list'):
            todo_list = state['todo_list']
            if isinstance(todo_list, str):
                try:
                    todo_list = json.loads(todo_list)
                except:
                    pass
            if isinstance(todo_list, list):
                context_lines.append(f"   Todo items: {len(todo_list)}")
                for item in todo_list[:5]:  # Show first 5
                    status = item.get('status', 'pending')
                    icon = '✓' if status == 'completed' else '→' if status == 'in_progress' else '○'
                    context_lines.append(f"   {icon} {item.get('content', 'Unknown')}")
                if len(todo_list) > 5:
                    context_lines.append(f"   ... and {len(todo_list) - 5} more")
        if state.get('pending_actions'):
            context_lines.append(f"   Pending actions: {', '.join(state['pending_actions'][:3])}")
        context_lines.append("")

    # Check for pending messages
    msg_count = get_pending_messages(project_name)
    if msg_count > 0:
        context_lines.append(f"📬 {msg_count} pending message(s) - use /inbox-check to view")
        context_lines.append("")

    # Reminder about commands
    context_lines.append("Available commands: /session-start, /session-end, /inbox-check, /feedback-check, /team-status, /broadcast")

    result["additionalContext"] = "\n".join(context_lines)

    # Build system message
    if state and state.get('current_focus'):
        result["systemMessage"] = f"Session resumed for {project_name}. Previous focus: {state['current_focus']}"
    else:
        result["systemMessage"] = f"Claude Family session initialized for {project_name}."

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
