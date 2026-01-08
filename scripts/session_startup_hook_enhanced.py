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
    """Log session start to database, return (session_id, error_msg)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
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

def get_recent_sessions(project_name: str, limit: int = 3) -> list:
    """Get recent session summaries for this project."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT session_summary, session_start,
                   COALESCE(array_to_string(tasks_completed, ', '), '') as tasks
            FROM claude.sessions
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
            FROM claude.messages
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
                current_focus,
                files_modified,
                pending_actions,
                updated_at
            FROM claude.session_state
            WHERE project_name = %s
        """, (project_name,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return dict(result) if result else None
    except Exception:
        return None

def get_active_todos(project_name: str) -> list:
    """Get active todos from claude.todos table (DATABASE SOURCE OF TRUTH)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Get project_id first
        cur.execute("""
            SELECT project_id::text
            FROM claude.projects
            WHERE project_name = %s
        """, (project_name,))
        project_result = cur.fetchone()
        if not project_result:
            cur.close()
            conn.close()
            return []

        project_id = project_result['project_id']

        # Get active todos
        cur.execute("""
            SELECT
                content,
                status,
                priority,
                created_at
            FROM claude.todos
            WHERE project_id = %s::uuid
              AND is_deleted = false
              AND status IN ('pending', 'in_progress')
            ORDER BY
                CASE status
                    WHEN 'in_progress' THEN 1
                    WHEN 'pending' THEN 2
                END,
                priority ASC,
                created_at ASC
            LIMIT 10
        """, (project_id,))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in results]
    except Exception:
        return []

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

    # === HEALTH CHECK ===
    health = check_system_health()
    health_icon = {'healthy': '[OK]', 'partial': '[!]', 'degraded': '[X]'}.get(health['overall'], '[?]')

    context_lines.append(f"=== Claude Family Session Started ===")
    context_lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    context_lines.append(f"Project: {project_name}")
    context_lines.append(f"Identity: {identity_name}")
    context_lines.append(f"Health: {health_icon} {health['overall'].upper()}")

    if health['issues']:
        context_lines.append(f"Issues: {' | '.join(health['issues'])}")

    if DB_AVAILABLE:
        # Log session to database
        session_id, error = log_session_start(project_name, identity_id)
        if session_id:
            context_lines.append(f"Session ID: {session_id}")
            context_lines.append("Session logged to database")
        else:
            context_lines.append(f"Could not log session: {error or 'unknown error'}")

        # === WHERE WE LEFT OFF ===
        state = get_session_state(project_name)
        todos = get_active_todos(project_name)

        if state or todos:
            context_lines.append("")
            context_lines.append("=== WHERE WE LEFT OFF ===")

            # Last updated
            if state and state.get('updated_at'):
                updated = state['updated_at'].strftime('%Y-%m-%d %H:%M')
                context_lines.append(f"Last saved: {updated}")

            # Current focus
            if state and state.get('current_focus'):
                context_lines.append(f"Focus: {state['current_focus']}")

            # Todo list from DATABASE (claude.todos - SOURCE OF TRUTH)
            if todos:
                in_progress = [t for t in todos if t['status'] == 'in_progress']
                pending = [t for t in todos if t['status'] == 'pending']

                context_lines.append("")
                context_lines.append(f"Active Todos: {len(todos)} total ({len(in_progress)} in progress, {len(pending)} pending)")

                if in_progress:
                    context_lines.append("")
                    context_lines.append("In Progress:")
                    for t in in_progress:
                        priority_label = f"[P{t['priority']}]" if t.get('priority') else ""
                        context_lines.append(f"  [>] {priority_label} {t['content']}")

                if pending[:5]:  # Show top 5 pending
                    context_lines.append("")
                    context_lines.append("Pending (top 5):")
                    for t in pending[:5]:
                        priority_label = f"[P{t['priority']}]" if t.get('priority') else ""
                        context_lines.append(f"  [ ] {priority_label} {t['content']}")

                if len(pending) > 5:
                    context_lines.append(f"  ... and {len(pending) - 5} more pending")

            # Pending actions
            if state and state.get('pending_actions'):
                context_lines.append("")
                context_lines.append("Pending Actions:")
                for action in state['pending_actions'][:5]:
                    context_lines.append(f"  - {action}")

            # Files modified
            if state and state.get('files_modified'):
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
