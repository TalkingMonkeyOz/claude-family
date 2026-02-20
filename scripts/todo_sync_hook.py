#!/usr/bin/env python3
"""
TodoWrite Sync Hook - PostToolUse Hook for Claude Code

Intercepts TodoWrite tool calls and syncs todos to claude.todos database.
This solves the architectural flaw where TodoWrite only saves to in-memory state.

Hook Event: PostToolUse
Triggers On: tool_name='TodoWrite'

What it does:
1. Reads todos from TodoWrite tool_input
2. Syncs to claude.todos database (INSERT new, UPDATE existing)
3. Tracks created_session_id and completed_session_id
4. Matches todos by content (fuzzy match to handle minor edits)

Output: Standard hook JSON (no additional context needed for PostToolUse)

Author: Claude Family
Date: 2025-12-31
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from uuid import UUID

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('todo_sync')

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
        logger.warning("psycopg/psycopg2 not available - todo sync disabled")

# Default connection string
DEFAULT_CONN_STR = None
try:
    import sys as _sys
    _sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
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


def is_valid_uuid(uuid_str: str) -> bool:
    """Validate UUID format."""
    if not uuid_str:
        return False
    try:
        UUID(uuid_str)
        return True
    except (ValueError, AttributeError):
        return False


def similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_matching_todo(content: str, existing_todos: list, threshold: float = 0.75) -> dict:
    """Find matching todo by content similarity."""
    best_match = None
    best_ratio = 0.0

    for todo in existing_todos:
        ratio = similarity_ratio(content, todo['content'])
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = todo

    return best_match


def sync_todos_to_database(todos: list, project_id: str, session_id: str):
    """
    Sync todos to claude.todos table.

    Args:
        todos: List of todo dicts from TodoWrite tool
        project_id: Current project UUID
        session_id: Current session UUID
    """
    if not DB_AVAILABLE:
        logger.warning("Database not available - skipping todo sync")
        return

    conn = get_db_connection()
    if not conn:
        logger.error("Failed to get database connection")
        return

    try:
        cur = conn.cursor()

        # Load existing todos for this project
        cur.execute("""
            SELECT
                todo_id::text,
                content,
                active_form,
                status,
                priority,
                display_order
            FROM claude.todos
            WHERE project_id = %s::uuid
              AND is_deleted = false
            ORDER BY display_order, priority, created_at
        """, (project_id,))

        if PSYCOPG_VERSION == 2:
            existing_todos = cur.fetchall()
        else:
            existing_todos = cur.fetchall()

        logger.info(f"Loaded {len(existing_todos)} existing todos from database")

        # Track which todos we've processed (to detect deletions)
        processed_todo_ids = set()

        # Process each todo from TodoWrite
        for idx, todo in enumerate(todos):
            content = todo.get('content', '')
            active_form = todo.get('activeForm', content)
            status = todo.get('status', 'pending')

            # Map 'deleted' to 'archived' - preserves audit trail instead of hard-delete
            if status == 'deleted':
                status = 'archived'

            # Try to find matching existing todo
            matching_todo = find_matching_todo(content, existing_todos)

            if matching_todo:
                # UPDATE existing todo
                todo_id = matching_todo['todo_id']
                processed_todo_ids.add(todo_id)

                old_status = matching_todo['status']

                # Determine if we need to update completion fields
                if status == 'completed' and old_status != 'completed':
                    # Transitioning TO completed - set completion fields
                    if session_id:
                        cur.execute("""
                            UPDATE claude.todos
                            SET status = %s,
                                active_form = %s,
                                display_order = %s,
                                completed_at = NOW(),
                                completed_session_id = %s::uuid,
                                updated_at = NOW()
                            WHERE todo_id = %s::uuid
                        """, (status, active_form, idx, session_id, todo_id))
                    else:
                        cur.execute("""
                            UPDATE claude.todos
                            SET status = %s,
                                active_form = %s,
                                display_order = %s,
                                completed_at = NOW(),
                                completed_session_id = NULL,
                                updated_at = NOW()
                            WHERE todo_id = %s::uuid
                        """, (status, active_form, idx, todo_id))
                elif status != 'completed' and old_status == 'completed':
                    # Transitioning FROM completed - clear completion fields
                    cur.execute("""
                        UPDATE claude.todos
                        SET status = %s,
                            active_form = %s,
                            display_order = %s,
                            completed_at = NULL,
                            completed_session_id = NULL,
                            updated_at = NOW()
                        WHERE todo_id = %s::uuid
                    """, (status, active_form, idx, todo_id))
                else:
                    # No status transition - just update other fields
                    cur.execute("""
                        UPDATE claude.todos
                        SET status = %s,
                            active_form = %s,
                            display_order = %s,
                            updated_at = NOW()
                        WHERE todo_id = %s::uuid
                    """, (status, active_form, idx, todo_id))

                logger.debug(f"Updated todo {todo_id}: {content[:50]}... (status={status})")

            else:
                # INSERT new todo
                if session_id:
                    cur.execute("""
                        INSERT INTO claude.todos (
                            project_id,
                            created_session_id,
                            content,
                            active_form,
                            status,
                            priority,
                            display_order
                        ) VALUES (
                            %s::uuid,
                            %s::uuid,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        RETURNING todo_id::text
                    """, (
                        project_id,
                        session_id,
                        content,
                        active_form,
                        status,
                        3,  # default priority
                        idx
                    ))
                else:
                    cur.execute("""
                        INSERT INTO claude.todos (
                            project_id,
                            created_session_id,
                            content,
                            active_form,
                            status,
                            priority,
                            display_order
                        ) VALUES (
                            %s::uuid,
                            NULL,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                        RETURNING todo_id::text
                    """, (
                        project_id,
                        content,
                        active_form,
                        status,
                        3,  # default priority
                        idx
                    ))

                if PSYCOPG_VERSION == 2:
                    new_todo_id = cur.fetchone()['todo_id']
                else:
                    new_todo_id = cur.fetchone()['todo_id']

                processed_todo_ids.add(new_todo_id)
                logger.info(f"Inserted new todo {new_todo_id}: {content[:50]}...")

        # DON'T auto-delete missing todos!
        # Todos missing from TodoWrite call might just not have been restored yet (session start)
        # or Claude is working on a subset of todos.
        #
        # To delete a todo, explicitly mark it: {"content": "...", "status": "deleted"}
        # or use SQL: UPDATE claude.todos SET is_deleted = true WHERE todo_id = '...'
        #
        # This prevents accidental deletion when:
        # 1. Session starts and Claude hasn't called TodoWrite yet to restore todos
        # 2. Claude creates new todos for a specific task
        # 3. User is working with a subset of todos

        logger.info(f"Skipped auto-deletion check - {len(existing_todos) - len(processed_todo_ids)} todos not in current call (expected behavior)")

        conn.commit()
        logger.info(f"Todo sync complete: processed {len(todos)} todos")

    except Exception as e:
        logger.error(f"Todo sync failed: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def main():
    """Main entry point for PostToolUse hook."""
    try:
        # Read stdin
        hook_input = json.load(sys.stdin)

        tool_name = hook_input.get('tool_name')

        # Only process TodoWrite calls
        if tool_name != 'TodoWrite':
            # Return empty response for other tools
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        logger.info("TodoWrite hook triggered")

        # Extract todos from tool_input
        tool_input = hook_input.get('tool_input', {})
        todos = tool_input.get('todos', [])

        if not todos:
            logger.warning("TodoWrite called with empty todos array")
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        # Get session_id and cwd from hook_input
        session_id = hook_input.get('session_id')
        cwd = hook_input.get('cwd', '')

        if not session_id:
            logger.error("Missing session_id in hook_input")
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        # Validate session_id UUID format
        if not is_valid_uuid(session_id):
            logger.error(f"Invalid session_id format: {session_id}")
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        # Extract project name from cwd (e.g., "C:\\Projects\\claude-family" -> "claude-family")
        if not cwd:
            logger.error("Missing cwd in hook_input")
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        # Get last directory name from path (works for both Windows and Unix paths)
        import os.path
        project_name = os.path.basename(cwd.rstrip('/\\'))

        if not project_name:
            logger.error(f"Could not extract project name from cwd: {cwd}")
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        # Get project_id from database using project_name
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to get database connection for project_id lookup")
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        try:
            cur = conn.cursor()
            cur.execute("SELECT project_id::text FROM claude.projects WHERE project_name = %s", (project_name,))

            if PSYCOPG_VERSION == 2:
                row = cur.fetchone()
            else:
                row = cur.fetchone()

            if not row:
                logger.error(f"Project '{project_name}' not found in claude.projects")
                conn.close()
                print(json.dumps({
                    "additionalContext": "",
                    "systemMessage": "",
                    "environment": {}
                }))
                return 0

            project_id = row['project_id']

            # Validate project_id UUID format
            if not is_valid_uuid(project_id):
                logger.error(f"Invalid project_id format from database: {project_id}")
                conn.close()
                print(json.dumps({
                    "additionalContext": "",
                    "systemMessage": "",
                    "environment": {}
                }))
                return 0

            logger.info(f"Found project '{project_name}' with ID {project_id[:8]}...")

            # Check if session exists in database (needed for foreign key constraint)
            cur.execute("SELECT 1 FROM claude.sessions WHERE session_id = %s::uuid", (session_id,))
            session_exists = cur.fetchone() is not None
            conn.close()

            if not session_exists:
                logger.warning(f"Session {session_id[:8]}... not in database yet - using NULL for session references")
                session_id = None  # Use NULL to avoid foreign key constraint violation

        except Exception as e:
            logger.error(f"Failed to lookup project_id: {e}")
            if conn:
                conn.close()
            print(json.dumps({
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }))
            return 0

        # Sync todos to database
        sync_todos_to_database(todos, project_id, session_id)

        # Return success (no additional context needed for PostToolUse)
        print(json.dumps({
            "additionalContext": "",
            "systemMessage": "",
            "environment": {}
        }))

        return 0

    except Exception as e:
        logger.error(f"TodoWrite hook failed: {e}", exc_info=True)
        try:
            from failure_capture import capture_failure
            capture_failure("todo_sync_hook", str(e), "scripts/todo_sync_hook.py")
        except Exception:
            pass
        # Return empty response on error (don't break Claude Code)
        print(json.dumps({
            "additionalContext": "",
            "systemMessage": "",
            "environment": {}
        }))
        return 1


if __name__ == "__main__":
    sys.exit(main())
