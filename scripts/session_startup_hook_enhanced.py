#!/usr/bin/env python3
"""
Session Startup Hook Script for claude-family-core plugin.

This is called automatically via SessionStart hook.
- Logs session to PostgreSQL
- Checks system health (no DB query)
- Counts outstanding todos (1 query)
- Outputs lean JSON for Claude Code to consume

Full context loading is deferred to start_session() MCP tool.
"""

import json
import os
import sys
from datetime import datetime

# Try to load POSTGRES_CONFIG from central config or .env file
POSTGRES_CONFIG = None
try:
    # First try to load .env file directly (in case config.py fails due to working directory)
    config_dir = os.path.normpath(os.path.expanduser('~/OneDrive/Documents/AI_projects/ai-workspace'))
    env_file = os.path.join(config_dir, '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())  # Don't overwrite existing

    # Now try to import config (which will use the env vars we just set)
    sys.path.insert(0, config_dir)
    from config import POSTGRES_CONFIG
except (ImportError, ValueError, FileNotFoundError):
    # Fall back to environment variables only
    if os.environ.get('POSTGRES_PASSWORD'):
        POSTGRES_CONFIG = {
            'host': os.environ.get('POSTGRES_HOST', 'localhost'),
            'database': os.environ.get('POSTGRES_DATABASE', 'ai_company_foundation'),
            'user': os.environ.get('POSTGRES_USER', 'postgres'),
            'password': os.environ.get('POSTGRES_PASSWORD')
        }

# Try to import psycopg for database access
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

# Known identity mapping
IDENTITY_MAP = {
    'claude-code-unified': 'ff32276f-9d05-4a18-b092-31b54c82fff9',
    'claude-desktop': '3be37dfb-c3bb-4303-9bf1-952c7287263f',
}

def check_system_health() -> dict:
    """Check system health: DB, Voyage AI, required env vars."""
    health = {
        'database': {'status': 'unknown', 'message': ''},
        'voyage_ai': {'status': 'unknown', 'message': ''},
        'env_vars': {'status': 'unknown', 'message': ''},
        'overall': 'unknown'
    }
    issues = []

    # Check database
    if not DB_AVAILABLE:
        health['database'] = {'status': 'error', 'message': 'psycopg not installed'}
        issues.append('DB: psycopg missing')
    elif not POSTGRES_CONFIG and not os.environ.get('DATABASE_URI'):
        health['database'] = {'status': 'error', 'message': 'No DB config found'}
        issues.append('DB: No config')
    else:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            health['database'] = {'status': 'ok', 'message': 'Connected'}
        except Exception as e:
            health['database'] = {'status': 'error', 'message': str(e)[:50]}
            issues.append(f'DB: {str(e)[:30]}')

    # Check Voyage AI (for RAG)
    voyage_key = os.environ.get('VOYAGE_API_KEY', '')
    if not voyage_key:
        health['voyage_ai'] = {'status': 'warning', 'message': 'VOYAGE_API_KEY not set (RAG disabled)'}
        issues.append('Voyage AI: No API key')
    elif len(voyage_key) < 10:
        health['voyage_ai'] = {'status': 'warning', 'message': 'VOYAGE_API_KEY looks invalid'}
        issues.append('Voyage AI: Invalid key')
    else:
        health['voyage_ai'] = {'status': 'ok', 'message': 'API key configured'}

    # Check required env vars
    required_vars = ['POSTGRES_PASSWORD']
    optional_vars = ['ANTHROPIC_API_KEY', 'VOYAGE_API_KEY']
    missing_required = [v for v in required_vars if not os.environ.get(v)]
    missing_optional = [v for v in optional_vars if not os.environ.get(v)]

    if missing_required:
        health['env_vars'] = {'status': 'error', 'message': f'Missing: {", ".join(missing_required)}'}
        issues.append(f'Env: Missing {", ".join(missing_required)}')
    elif missing_optional:
        health['env_vars'] = {'status': 'warning', 'message': f'Optional missing: {", ".join(missing_optional)}'}
    else:
        health['env_vars'] = {'status': 'ok', 'message': 'All vars configured'}

    # Overall status
    statuses = [h['status'] for h in health.values() if isinstance(h, dict)]
    if 'error' in statuses:
        health['overall'] = 'degraded'
    elif 'warning' in statuses:
        health['overall'] = 'partial'
    else:
        health['overall'] = 'healthy'

    health['issues'] = issues
    return health

def get_db_connection():
    """Get PostgreSQL connection using central config or environment variables."""
    # Try central config first
    if POSTGRES_CONFIG:
        try:
            if PSYCOPG_VERSION == 3:
                # psycopg3 uses 'dbname' not 'database'
                config = POSTGRES_CONFIG.copy()
                if 'database' in config and 'dbname' not in config:
                    config['dbname'] = config.pop('database')
                return psycopg.connect(**config, row_factory=dict_row)
            else:
                return psycopg.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)
        except Exception:
            pass

    # Fall back to environment variables
    conn_strings = [
        os.environ.get('DATABASE_URI'),
        os.environ.get('POSTGRES_CONNECTION_STRING'),
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

    raise last_error if last_error else Exception("No valid connection - set DATABASE_URI or POSTGRES_CONNECTION_STRING env var, or configure ai-workspace/config.py")

def log_session_start(project_name: str, identity_id: str) -> tuple:
    """Log session start to database, return (session_id, error_msg).

    Uses ON CONFLICT upsert to prevent duplicate session crashes when the
    SessionStart hook fires multiple times in quick succession (restart/resume).
    If a session for this project started within the last 60 seconds, reuses it.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check for a very recent session (within 60s) to avoid duplicates
        cur.execute("""
            SELECT session_id::text
            FROM claude.sessions
            WHERE project_name = %s
              AND identity_id = %s
              AND session_start > NOW() - INTERVAL '60 seconds'
              AND session_end IS NULL
            ORDER BY session_start DESC
            LIMIT 1
        """, (project_name, identity_id))
        existing = cur.fetchone()

        if existing:
            session_id = existing['session_id']
            cur.close()
            conn.close()
            return (session_id, None)

        # No recent session - create new one
        cur.execute("""
            INSERT INTO claude.sessions
            (session_id, identity_id, session_start, project_name, session_summary)
            VALUES (gen_random_uuid(), %s, NOW(), %s, 'Session auto-started via hook')
            RETURNING session_id::text
        """, (identity_id, project_name))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return (result['session_id'] if result else None, None)
    except Exception as e:
        return (None, str(e))

def get_outstanding_todo_count(project_name: str) -> tuple:
    """Get count of outstanding todos, auto-archiving stale pending items.

    Stale = pending items not updated in >7 days. These are zombie todos that
    would otherwise be restored every session forever.

    Returns:
        (active_count, archived_count) - active remaining and how many were archived.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Auto-archive stale pending todos (>7 days old, pending only - not in_progress)
        cur.execute("""
            UPDATE claude.todos t
            SET status = 'archived', updated_at = NOW()
            FROM claude.projects p
            WHERE t.project_id = p.project_id
              AND p.project_name = %s
              AND t.status = 'pending'
              AND NOT t.is_deleted
              AND COALESCE(t.updated_at, t.created_at) < NOW() - INTERVAL '7 days'
            RETURNING t.todo_id
        """, (project_name,))
        archived_count = len(cur.fetchall())
        conn.commit()

        # Count remaining active todos
        cur.execute("""
            SELECT COUNT(*) as count
            FROM claude.todos t
            JOIN claude.projects p ON t.project_id = p.project_id
            WHERE p.project_name = %s
              AND t.status IN ('pending', 'in_progress')
              AND NOT t.is_deleted
        """, (project_name,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        active_count = result['count'] if result else 0
        return (active_count, archived_count)
    except Exception:
        return (0, 0)

def _reset_task_map(project_name: str, session_id: str):
    """Write a fresh task_map with new session_id and no task entries.

    This prevents the discipline hook from rejecting Write/Edit calls due to
    a stale task_map left over from a crashed or interrupted session.
    """
    import tempfile
    map_path = os.path.join(tempfile.gettempdir(), f"claude_task_map_{project_name}.json")
    try:
        with open(map_path, 'w') as f:
            json.dump({"_session_id": session_id}, f)
    except IOError:
        pass  # Non-critical - discipline hook will just prompt for tasks


def main():
    """Run session startup with lean output."""

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

    # === HEALTH CHECK ===
    health = check_system_health()
    health_icon = {'healthy': '[OK]', 'partial': '[!]', 'degraded': '[X]'}.get(health['overall'], '[?]')

    context_lines.append(f"=== Claude Family Session Started ===")
    context_lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    context_lines.append(f"Project: {project_name}")
    context_lines.append(f"Health: {health_icon} {health['overall'].upper()}")

    if health['issues']:
        context_lines.append(f"Issues: {' | '.join(health['issues'])}")

    if DB_AVAILABLE:
        # Log session to database
        session_id, error = log_session_start(project_name, identity_id)
        if session_id:
            context_lines.append(f"Session ID: {session_id}")
        else:
            context_lines.append(f"Could not log session: {error or 'unknown error'}")

        # Count outstanding todos + auto-archive stale ones
        todo_count, archived_count = get_outstanding_todo_count(project_name)
        if archived_count > 0:
            context_lines.append(f"Auto-archived {archived_count} stale pending todo(s) (>7 days old)")
        if todo_count > 0:
            context_lines.append("")
            context_lines.append(f"You have {todo_count} outstanding tasks from previous sessions. Restore them by calling start_session() and creating TaskCreate entries for each outstanding todo.")

        # Clean task_map to prevent stale session errors from discipline hook
        if session_id:
            _reset_task_map(project_name, session_id)
    else:
        context_lines.append("Database not available (psycopg not installed)")

    result["additionalContext"] = "\n".join(context_lines)
    result["systemMessage"] = f"Claude Family session started for {project_name}. Session logged to database."

    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
