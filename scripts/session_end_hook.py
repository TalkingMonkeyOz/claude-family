#!/usr/bin/env python3
"""
Session End Hook - Auto-Save Session State on Exit

Automatically saves the current session state (todos, focus) to the database
when Claude Code exits. This replaces the old "prompt" hook that only reminded
users to run /session-end (which they usually forgot).

What gets saved:
- Marks session_end timestamp in claude.sessions
- Preserves session_state (current_focus from latest session_summary)

What does NOT happen here (left for manual /session-end):
- Detailed session summary (requires Claude's analysis)
- Knowledge capture
- Git operations

Hook Event: SessionEnd
Output: Standard hook JSON

Author: Claude Family
Date: 2026-02-07
"""

import sys
import os
import io
import json
import logging
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('session_end')

# Try to import psycopg
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
        DB_AVAILABLE = False

# Load config
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


def auto_save_session(session_id: str, project_name: str):
    """Auto-save session state to database on exit.

    This is a lightweight save - just marks session_end and preserves state.
    Full session summary requires manual /session-end.
    """
    conn = get_db_connection()
    if not conn:
        logger.warning("No DB connection - cannot auto-save session")
        return

    try:
        cur = conn.cursor()

        # Mark session end (only if not already closed)
        if session_id:
            cur.execute("""
                UPDATE claude.sessions
                SET session_end = NOW(),
                    session_summary = COALESCE(session_summary, 'Session auto-closed (no manual /session-end)')
                WHERE session_id = %s::uuid
                  AND session_end IS NULL
            """, (session_id,))

            rows_updated = cur.rowcount
            if rows_updated > 0:
                logger.info(f"Auto-closed session {session_id[:8]}...")
            else:
                logger.info(f"Session {session_id[:8]}... already closed or not found")
        else:
            # Try to close the most recent unclosed session for this project
            cur.execute("""
                UPDATE claude.sessions
                SET session_end = NOW(),
                    session_summary = COALESCE(session_summary, 'Session auto-closed (no manual /session-end)')
                WHERE project_name = %s
                  AND session_end IS NULL
                  AND session_start > NOW() - INTERVAL '24 hours'
                ORDER BY session_start DESC
                LIMIT 1
            """, (project_name,))

            rows_updated = cur.rowcount
            if rows_updated > 0:
                logger.info(f"Auto-closed latest session for {project_name}")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Auto-save session failed: {e}")
        try:
            conn.close()
        except Exception:
            pass


def main():
    """Main entry point for SessionEnd hook."""
    logger.info("SessionEnd hook invoked - auto-saving session state")

    try:
        # Read hook input
        try:
            raw_input = sys.stdin.read()
            hook_input = json.loads(raw_input) if raw_input.strip() else {}
        except json.JSONDecodeError:
            hook_input = {}

        # Get session info
        session_id = hook_input.get('session_id')
        cwd = hook_input.get('cwd', os.getcwd())
        project_name = os.path.basename(cwd.rstrip('/\\'))

        # Auto-save session state
        auto_save_session(session_id, project_name)

        # Return reminder to run /session-end for full summary
        print(json.dumps({
            "systemMessage": "Session auto-saved. For detailed summary + knowledge capture, run /session-end before closing."
        }))
        return 0

    except Exception as e:
        logger.error(f"SessionEnd hook failed: {e}", exc_info=True)
        try:
            from failure_capture import capture_failure
            capture_failure("session_end_hook", str(e), "scripts/session_end_hook.py")
        except Exception:
            pass
        print(json.dumps({}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
