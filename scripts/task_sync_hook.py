#!/usr/bin/env python3
"""
TaskCreate/TaskUpdate Sync Hook - PostToolUse Hook for Claude Code

Intercepts TaskCreate and TaskUpdate tool calls and syncs them to claude.todos.
This bridges the gap where TaskList (in-memory, session-scoped) items are lost
on session end, while claude.todos persist across sessions.

Hook Event: PostToolUse
Triggers On: tool_name='TaskCreate' or tool_name='TaskUpdate'

What it does:
1. On TaskCreate: Inserts a new todo into claude.todos
2. On TaskUpdate (status change): Updates the corresponding todo status
3. Stores task_number → todo_id mapping in a temp file for correlation

Output: Standard hook JSON (no additional context needed for PostToolUse)

Author: Claude Family
Date: 2026-02-08
"""

import json
import os
import sys
import io
import re
import logging
import tempfile
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('task_sync')

# Try to import PostgreSQL
DB_AVAILABLE = False
PSYCOPG_VERSION = None

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
        logger.warning("psycopg/psycopg2 not available - task sync disabled")

# Default connection string
DEFAULT_CONN_STR = None
try:
    sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass


def get_db_connection():
    """Get PostgreSQL connection."""
    if not DB_AVAILABLE:
        return None
    conn_str = os.environ.get('DATABASE_URL', DEFAULT_CONN_STR)
    if not conn_str:
        return None
    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def get_task_map_path(project_name: str) -> Path:
    """Get path to the task→todo mapping file for this project."""
    return Path(tempfile.gettempdir()) / f"claude_task_map_{project_name}.json"


def load_task_map(project_name: str) -> dict:
    """Load task_number → todo_id mapping from temp file."""
    path = get_task_map_path(project_name)
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_task_map(project_name: str, task_map: dict):
    """Save task_number → todo_id mapping to temp file."""
    path = get_task_map_path(project_name)
    try:
        with open(path, 'w') as f:
            json.dump(task_map, f)
    except IOError as e:
        logger.error(f"Failed to save task map: {e}")


def get_current_session_id(project_name: str, conn) -> str:
    """Get the current open session ID for this project."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT session_id::text FROM claude.sessions
            WHERE project_name = %s AND session_end IS NULL
            ORDER BY session_start DESC LIMIT 1
        """, (project_name,))
        row = cur.fetchone()
        if row:
            return row['session_id'] if isinstance(row, dict) else row[0]
    except Exception as e:
        logger.error(f"Failed to get session ID: {e}")
    return None


def get_project_id(project_name: str, conn) -> str:
    """Get the project ID for this project."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT project_id::text FROM claude.projects WHERE project_name = %s", (project_name,))
        row = cur.fetchone()
        if row:
            return row['project_id'] if isinstance(row, dict) else row[0]
    except Exception as e:
        logger.error(f"Failed to get project ID: {e}")
    return None


def extract_task_number(output: str) -> str:
    """Extract task number from TaskCreate/TaskUpdate output."""
    # "Task #3 created successfully: ..." or "Updated task #3 status"
    match = re.search(r'#(\d+)', output)
    return match.group(1) if match else None


def handle_task_create(tool_input: dict, tool_output: str, project_name: str):
    """Handle TaskCreate: insert new todo into claude.todos."""
    subject = tool_input.get('subject', '')
    description = tool_input.get('description', '')
    active_form = tool_input.get('activeForm', subject)

    if not subject:
        logger.warning("TaskCreate with empty subject - skipping")
        return

    task_number = extract_task_number(tool_output)
    if not task_number:
        logger.warning(f"Could not extract task number from output: {tool_output}")
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        project_id = get_project_id(project_name, conn)
        if not project_id:
            logger.warning(f"Project not found: {project_name}")
            conn.close()
            return

        session_id = get_current_session_id(project_name, conn)

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.todos (project_id, content, active_form, status, priority, created_session_id)
            VALUES (%s::uuid, %s, %s, 'pending', 3, %s::uuid)
            RETURNING todo_id::text
        """, (project_id, subject, active_form, session_id))

        row = cur.fetchone()
        todo_id = row['todo_id'] if isinstance(row, dict) else row[0]

        conn.commit()
        conn.close()

        # Save mapping
        task_map = load_task_map(project_name)
        task_map[task_number] = todo_id
        save_task_map(project_name, task_map)

        logger.info(f"TaskCreate synced: task #{task_number} → todo {todo_id[:8]}... ({subject[:50]})")

    except Exception as e:
        logger.error(f"Failed to sync TaskCreate: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass


def handle_task_update(tool_input: dict, tool_output: str, project_name: str):
    """Handle TaskUpdate: update todo status in claude.todos."""
    task_id = tool_input.get('taskId', '')
    new_status = tool_input.get('status', '')

    if not task_id or not new_status:
        return  # Not a status update, skip

    # Look up the todo_id from our mapping
    task_map = load_task_map(project_name)
    todo_id = task_map.get(str(task_id))

    if not todo_id:
        logger.debug(f"No todo mapping for task #{task_id} - may be pre-existing")
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        session_id = get_current_session_id(project_name, conn)

        cur = conn.cursor()

        if new_status == 'deleted':
            cur.execute("""
                UPDATE claude.todos
                SET is_deleted = true, deleted_at = NOW(), updated_at = NOW()
                WHERE todo_id = %s::uuid
            """, (todo_id,))
        elif new_status == 'completed':
            cur.execute("""
                UPDATE claude.todos
                SET status = 'completed', completed_at = NOW(), completed_session_id = %s::uuid, updated_at = NOW()
                WHERE todo_id = %s::uuid
            """, (session_id, todo_id))
        elif new_status in ('pending', 'in_progress'):
            cur.execute("""
                UPDATE claude.todos
                SET status = %s, completed_at = NULL, updated_at = NOW()
                WHERE todo_id = %s::uuid
            """, (new_status, todo_id))

        conn.commit()
        conn.close()

        logger.info(f"TaskUpdate synced: task #{task_id} → {new_status}")

    except Exception as e:
        logger.error(f"Failed to sync TaskUpdate: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass


def main():
    """Main entry point for the hook."""
    try:
        raw_input = sys.stdin.read()
        hook_input = json.loads(raw_input) if raw_input.strip() else {}
    except json.JSONDecodeError:
        hook_input = {}

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})
    tool_output = hook_input.get('tool_output', '')

    # Only handle TaskCreate and TaskUpdate
    if tool_name not in ('TaskCreate', 'TaskUpdate'):
        print(json.dumps({}))
        return 0

    # Get project name from cwd
    cwd = hook_input.get('cwd', os.getcwd())
    project_name = os.path.basename(cwd.rstrip('/\\'))

    if tool_name == 'TaskCreate':
        handle_task_create(tool_input, tool_output, project_name)
    elif tool_name == 'TaskUpdate':
        handle_task_update(tool_input, tool_output, project_name)

    # PostToolUse hooks return empty (no context injection needed)
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
