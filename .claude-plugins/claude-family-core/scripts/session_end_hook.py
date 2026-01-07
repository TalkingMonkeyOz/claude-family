#!/usr/bin/env python3
"""
Session End Hook Script for claude-family-core plugin.

Called automatically via SessionEnd hook OR /session-end command.
- Saves current todo list from stdin (passed by Claude)
- Prompts for next_steps if not provided
- Updates session_state table
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
    """Get PostgreSQL connection from environment."""
    conn_str = os.environ.get('DATABASE_URL')
    if not conn_str:
        return None

    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except Exception:
        return None


def save_session_state(project_name, todo_list, current_focus, next_steps, files_modified=None):
    """Save session state to database."""
    if not DB_AVAILABLE:
        return False, "Database not available"

    conn = get_db_connection()
    if not conn:
        return False, "Could not connect to database"

    try:
        cur = conn.cursor()

        # Upsert session state
        cur.execute("""
            INSERT INTO claude.session_state
                (project_name, todo_list, current_focus, next_steps, files_modified, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (project_name) DO UPDATE SET
                todo_list = EXCLUDED.todo_list,
                current_focus = EXCLUDED.current_focus,
                next_steps = EXCLUDED.next_steps,
                files_modified = EXCLUDED.files_modified,
                updated_at = NOW()
        """, (
            project_name,
            json.dumps(todo_list) if todo_list else '[]',
            current_focus,
            json.dumps(next_steps) if next_steps else '[]',
            files_modified or []
        ))

        conn.commit()
        conn.close()
        return True, "Session state saved"
    except Exception as e:
        return False, str(e)


def main():
    """Save session state from Claude's context."""

    # Get project from current directory
    cwd = os.getcwd()
    project_name = os.path.basename(cwd)

    # Check for JSON input from stdin (non-blocking)
    input_data = {}
    if not sys.stdin.isatty():
        try:
            raw = sys.stdin.read()
            if raw.strip():
                input_data = json.loads(raw)
        except (json.JSONDecodeError, Exception):
            pass

    # Extract data from input or environment
    todo_list = input_data.get('todo_list', [])
    current_focus = input_data.get('current_focus', '')
    next_steps = input_data.get('next_steps', [])
    files_modified = input_data.get('files_modified', [])

    # Save to database
    success, message = save_session_state(
        project_name=project_name,
        todo_list=todo_list,
        current_focus=current_focus,
        next_steps=next_steps,
        files_modified=files_modified
    )

    # Output result for Claude to see
    result = {
        "additionalContext": "",
        "systemMessage": ""
    }

    if success:
        summary_lines = [
            f"Session state saved for {project_name}",
            f"  Todos: {len(todo_list)} items",
            f"  Next steps: {len(next_steps)} items",
            f"  Focus: {current_focus[:50]}..." if current_focus else "  Focus: (none)"
        ]
        result["systemMessage"] = f"Session saved: {len(todo_list)} todos, {len(next_steps)} next steps"
        result["additionalContext"] = "\n".join(summary_lines)
    else:
        result["systemMessage"] = f"Failed to save session: {message}"

    print(json.dumps(result))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
