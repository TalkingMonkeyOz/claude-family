#!/usr/bin/env python3
"""
TaskCreate/TaskUpdate Sync Hook - PostToolUse Hook for Claude Code

Intercepts TaskCreate and TaskUpdate tool calls and syncs them to claude.todos
and claude.build_tasks. This bridges the gap where TaskList (in-memory, session-scoped)
items are lost on session end, while database records persist across sessions.

Hook Event: PostToolUse
Triggers On: tool_name='TaskCreate' or tool_name='TaskUpdate'

What it does:
1. On TaskCreate:
   - Inserts a new todo into claude.todos (or reuses existing)
   - Checks for matching build_tasks using similarity matching (75% threshold)
   - If matched, stores bt_code/bt_task_id in task_map for bridging
2. On TaskUpdate (status change):
   - Updates the corresponding todo status
   - If bridged to build_task, updates build_task status
   - On completion, checks if all tasks for parent feature are done
   - Logs audit_log entries for build_task transitions
3. Stores task_number → {todo_id, bt_code?, bt_task_id?} mapping in temp file

Output: Standard hook JSON (no additional context needed for PostToolUse)

Author: Claude Family
Date: 2026-02-08
Updated: 2026-02-11 (Added build_task bridging - BT318)
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


def save_task_map(project_name: str, task_map: dict, session_id: str = None):
    """Save task_number → todo_id mapping to temp file.

    Includes _session_id for session scoping - the discipline hook checks this
    to ensure tasks were created in the CURRENT session, not a stale previous one.
    """
    if session_id:
        task_map['_session_id'] = session_id
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
    """Extract task number from TaskCreate/TaskUpdate tool_response.

    tool_response format (JSON): {"task": {"id": "4", "subject": "..."}}
    Falls back to regex for text format: "Task #3 created successfully: ..."
    """
    # Try JSON format first (actual tool_response format)
    try:
        data = json.loads(output) if isinstance(output, str) else output
        if isinstance(data, dict):
            task = data.get('task', {})
            if isinstance(task, dict) and 'id' in task:
                return str(task['id'])
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: text format with #N
    match = re.search(r'#(\d+)', str(output))
    return match.group(1) if match else None


def similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_existing_todo(subject: str, project_id: str, conn, threshold: float = 0.75) -> dict:
    """Check if a similar todo already exists in the database.

    Prevents duplicates when TaskCreate is called for work that already
    has a pending/in_progress todo. Uses two matching strategies:
    1. Substring: task subject is contained in existing todo (or vice versa)
    2. Similarity: SequenceMatcher ratio >= threshold
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT todo_id::text, content, status
        FROM claude.todos
        WHERE project_id = %s::uuid
          AND is_deleted = false
          AND status IN ('pending', 'in_progress')
        ORDER BY created_at DESC
        LIMIT 50
    """, (project_id,))
    existing = cur.fetchall()

    subject_lower = subject.lower().strip()

    for todo in existing:
        content = todo['content'] if isinstance(todo, dict) else todo[1]
        content_lower = content.lower().strip()

        # Strategy 1: Substring containment (handles shortened task subjects)
        # Only if the shorter string is at least 20 chars (avoid trivial matches)
        shorter = min(len(subject_lower), len(content_lower))
        if shorter >= 20 and (subject_lower in content_lower or content_lower in subject_lower):
            todo_id = todo['todo_id'] if isinstance(todo, dict) else todo[0]
            logger.info(f"Substring match: '{subject[:40]}' ⊂ '{content[:40]}' → reusing {todo_id[:8]}")
            return {'todo_id': todo_id, 'content': content, 'status': todo['status'] if isinstance(todo, dict) else todo[2]}

        # Strategy 2: Fuzzy similarity
        ratio = similarity_ratio(subject, content)
        if ratio >= threshold:
            todo_id = todo['todo_id'] if isinstance(todo, dict) else todo[0]
            logger.info(f"Similarity match ({ratio:.0%}): '{subject[:40]}' ≈ '{content[:40]}' → reusing {todo_id[:8]}")
            return {'todo_id': todo_id, 'content': content, 'status': todo['status'] if isinstance(todo, dict) else todo[2]}

    return None


def find_matching_build_task(subject: str, project_name: str, conn, threshold: float = 0.75) -> dict:
    """Find an active build_task that matches the task subject.

    Queries build_tasks with status todo/in_progress and uses similarity matching.
    Returns dict with {bt_code, bt_task_id, task_name} or None if no match.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT 'BT' || bt.short_code as code, bt.task_name, bt.task_id::text, bt.status
        FROM claude.build_tasks bt
        JOIN claude.features f ON bt.feature_id = f.feature_id
        JOIN claude.projects p ON f.project_id = p.project_id
        WHERE p.project_name = %s
          AND bt.status IN ('todo', 'in_progress')
        ORDER BY bt.created_at DESC
        LIMIT 50
    """, (project_name,))

    build_tasks = cur.fetchall()
    if not build_tasks:
        return None

    subject_lower = subject.lower().strip()

    for bt in build_tasks:
        task_name = bt['task_name'] if isinstance(bt, dict) else bt[1]
        task_name_lower = task_name.lower().strip()

        # Use the existing similarity_ratio function
        ratio = similarity_ratio(subject, task_name)
        if ratio >= threshold:
            bt_code = bt['code'] if isinstance(bt, dict) else bt[0]
            bt_task_id = bt['task_id'] if isinstance(bt, dict) else bt[2]
            logger.info(f"Build task match ({ratio:.0%}): '{subject[:40]}' ≈ '{task_name[:40]}' → {bt_code}")
            return {
                'bt_code': bt_code,
                'bt_task_id': bt_task_id,
                'task_name': task_name
            }

    return None


def handle_task_create(tool_input: dict, tool_output: str, project_name: str, hook_session_id: str = None):
    """Handle TaskCreate: insert new todo or link to existing one in claude.todos.

    Also checks for matching build_tasks and creates a bridge if found.
    """
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

        # Check for duplicate: does a similar todo already exist?
        existing = find_existing_todo(subject, project_id, conn)

        if existing:
            # Reuse existing todo instead of creating duplicate
            todo_id = existing['todo_id']
            logger.info(f"TaskCreate linked to existing todo: task #{task_number} → {todo_id[:8]}...")
        else:
            # Insert new todo
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO claude.todos (project_id, content, active_form, status, priority, created_session_id)
                VALUES (%s::uuid, %s, %s, 'pending', 3, %s::uuid)
                RETURNING todo_id::text
            """, (project_id, subject, active_form, session_id))

            row = cur.fetchone()
            todo_id = row['todo_id'] if isinstance(row, dict) else row[0]
            logger.info(f"TaskCreate synced: task #{task_number} → new todo {todo_id[:8]}... ({subject[:50]})")

        # NEW: Check for matching build_task
        matched_bt = find_matching_build_task(subject, project_name, conn)

        conn.commit()
        conn.close()

        # Save mapping with session_id for discipline hook scoping
        task_map = load_task_map(project_name)

        # Store todo_id plus optional build_task bridge
        if matched_bt:
            task_map[task_number] = {
                "todo_id": todo_id,
                "bt_code": matched_bt['bt_code'],
                "bt_task_id": matched_bt['bt_task_id']
            }
            logger.info(f"Task #{task_number} bridged to {matched_bt['bt_code']}")
        else:
            task_map[task_number] = {"todo_id": todo_id}

        save_task_map(project_name, task_map, session_id=hook_session_id)

    except Exception as e:
        logger.error(f"Failed to sync TaskCreate: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass


def handle_task_update(tool_input: dict, tool_output: str, project_name: str) -> str:
    """Handle TaskUpdate: update todo status in claude.todos.

    If the task is bridged to a build_task, also updates the build_task status
    and checks for feature completion.

    Returns:
        Optional message about feature completion to surface as additionalContext.
    """
    task_id = tool_input.get('taskId', '')
    new_status = tool_input.get('status', '')

    if not task_id or not new_status:
        return  # Not a status update, skip

    # Look up the todo_id (and optional build_task) from our mapping
    task_map = load_task_map(project_name)
    map_entry = task_map.get(str(task_id))

    if not map_entry:
        logger.debug(f"No todo mapping for task #{task_id} - may be pre-existing")
        return

    # Handle both old format (string) and new format (dict)
    if isinstance(map_entry, str):
        todo_id = map_entry
        bt_task_id = None
        bt_code = None
    else:
        todo_id = map_entry.get('todo_id')
        bt_task_id = map_entry.get('bt_task_id')
        bt_code = map_entry.get('bt_code')

    conn = get_db_connection()
    if not conn:
        return

    try:
        session_id = get_current_session_id(project_name, conn)
        cur = conn.cursor()

        # Update the todo status
        if new_status == 'deleted':
            # Map 'deleted' to 'archived' - preserves audit trail instead of hard-delete.
            # TaskUpdate API only supports 'deleted' as discard action, so we remap it.
            cur.execute("""
                UPDATE claude.todos
                SET status = 'archived', updated_at = NOW()
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

        logger.info(f"TaskUpdate synced: task #{task_id} → {new_status}")

        # NEW: Update build_task if bridged
        if bt_task_id:
            if new_status == 'completed':
                cur.execute("""
                    UPDATE claude.build_tasks
                    SET status = 'completed', completed_at = NOW()
                    WHERE task_id = %s::uuid
                """, (bt_task_id,))

                # Insert audit log entry
                cur.execute("""
                    INSERT INTO claude.audit_log (entity_type, entity_id, entity_code, change_source, from_status, to_status)
                    VALUES ('build_tasks', %s::uuid, %s, 'task_sync_hook', 'in_progress', 'completed')
                """, (bt_task_id, bt_code))

                logger.info(f"Build task {bt_code} marked completed")

                # Check if all tasks for the parent feature are done
                cur.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE bt2.status NOT IN ('completed', 'cancelled')) as remaining,
                        'F' || f.short_code as feature_code,
                        f.feature_name
                    FROM claude.build_tasks bt2
                    JOIN claude.features f ON bt2.feature_id = f.feature_id
                    WHERE bt2.feature_id = (SELECT feature_id FROM claude.build_tasks WHERE task_id = %s::uuid)
                    GROUP BY f.short_code, f.feature_name
                """, (bt_task_id,))

                row = cur.fetchone()
                remaining = row['remaining'] if isinstance(row, dict) else row[0]

                if remaining == 0:
                    feature_code = row['feature_code'] if isinstance(row, dict) else row[1]
                    feature_name = row['feature_name'] if isinstance(row, dict) else row[2]
                    logger.info(f"All tasks for {feature_code} complete - surfacing to Claude")
                    conn.commit()
                    conn.close()
                    return f"All build tasks for {feature_code} ({feature_name}) are now completed. Consider running: advance_status('feature', '{feature_code}', 'completed')"

            elif new_status == 'in_progress':
                cur.execute("""
                    UPDATE claude.build_tasks
                    SET status = 'in_progress', started_at = NOW()
                    WHERE task_id = %s::uuid AND status = 'todo'
                """, (bt_task_id,))

                # Insert audit log entry
                cur.execute("""
                    INSERT INTO claude.audit_log (entity_type, entity_id, entity_code, change_source, from_status, to_status)
                    VALUES ('build_tasks', %s::uuid, %s, 'task_sync_hook', 'todo', 'in_progress')
                """, (bt_task_id, bt_code))

                logger.info(f"Build task {bt_code} started")

        conn.commit()
        conn.close()
        return None

    except Exception as e:
        logger.error(f"Failed to sync TaskUpdate: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return None


def main():
    """Main entry point for the hook."""
    try:
        raw_input = sys.stdin.read()
        hook_input = json.loads(raw_input) if raw_input.strip() else {}
    except json.JSONDecodeError:
        hook_input = {}

    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})
    # Field is 'tool_response' (NOT 'tool_output' - that doesn't exist)
    tool_output = hook_input.get('tool_response', '')
    # Ensure string for regex matching
    if not isinstance(tool_output, str):
        tool_output = json.dumps(tool_output) if tool_output else ''

    # Only handle TaskCreate and TaskUpdate
    if tool_name not in ('TaskCreate', 'TaskUpdate'):
        print(json.dumps({}))
        return 0

    # Get project name from cwd
    cwd = hook_input.get('cwd', os.getcwd())
    project_name = os.path.basename(cwd.rstrip('/\\'))

    # Pass session_id from hook_input for map file scoping
    hook_session_id = hook_input.get('session_id', '')

    completion_msg = None
    if tool_name == 'TaskCreate':
        handle_task_create(tool_input, tool_output, project_name, hook_session_id)
    elif tool_name == 'TaskUpdate':
        completion_msg = handle_task_update(tool_input, tool_output, project_name)

    # Surface feature completion advisory if all build_tasks are done
    if completion_msg:
        print(json.dumps({"additionalContext": completion_msg}))
    else:
        print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
