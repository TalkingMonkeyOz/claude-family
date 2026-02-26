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
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Shared credential loading from scripts/config.py
# (handles .env loading from all locations including legacy ai-workspace)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import POSTGRES_CONFIG, get_db_connection as _config_get_db_connection, detect_psycopg

logger = logging.getLogger(__name__)

psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = psycopg_mod is not None

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
    """Get PostgreSQL connection using shared config."""
    return _config_get_db_connection(strict=False)

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

        # Auto-archive stale todos (per task_lifecycle BPMN check_staleness step):
        #   - pending > 7 days → archived
        #   - in_progress > 3 days → archived (safety net, session_end_hook should have demoted these)
        cur.execute("""
            UPDATE claude.todos t
            SET status = 'archived', updated_at = NOW()
            FROM claude.projects p
            WHERE t.project_id = p.project_id
              AND p.project_name = %s
              AND NOT t.is_deleted
              AND (
                  (t.status = 'pending' AND COALESCE(t.updated_at, t.created_at) < NOW() - INTERVAL '7 days')
                  OR
                  (t.status = 'in_progress' AND COALESCE(t.updated_at, t.created_at) < NOW() - INTERVAL '3 days')
              )
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


def run_periodic_consolidation(conn):
    """Run periodic memory consolidation if 24h+ since last run (F130).

    Performs mid→long promotion, edge decay, and archival.
    Uses file-based cooldown to avoid running too frequently.
    """
    state_dir = Path.home() / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "consolidation_state.json"

    # Check cooldown
    try:
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
            last_run = datetime.fromisoformat(state.get('last_run', '2000-01-01'))
            if (datetime.now() - last_run).total_seconds() < 86400:  # 24h
                return None  # Too soon
    except Exception:
        pass  # Proceed if state file is corrupt

    try:
        cur = conn.cursor()

        counts = {"promoted_mid_to_long": 0, "decayed_edges": 0, "archived": 0}

        # Mid→Long promotion: applied 3+ times, confidence >= 80, accessed 5+ times
        cur.execute("""
            UPDATE claude.knowledge
            SET tier = 'long'
            WHERE tier = 'mid'
              AND COALESCE(times_applied, 0) >= 3
              AND confidence_level >= 80
              AND COALESCE(access_count, 0) >= 5
        """)
        counts["promoted_mid_to_long"] = cur.rowcount

        # Decay edges older than 7 days
        cur.execute("""
            UPDATE claude.knowledge_relations
            SET strength = GREATEST(0.05, strength * POWER(0.95,
                EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0
            ))
            WHERE strength > 0.05
              AND created_at < NOW() - INTERVAL '7 days'
        """)
        counts["decayed_edges"] = cur.rowcount

        # Archive: confidence < 30, not accessed in 90+ days
        cur.execute("""
            UPDATE claude.knowledge
            SET tier = 'archived'
            WHERE tier IN ('mid', 'long')
              AND confidence_level < 30
              AND COALESCE(last_accessed_at, created_at) < NOW() - INTERVAL '90 days'
        """)
        counts["archived"] = cur.rowcount

        conn.commit()

        # Update cooldown
        with open(state_file, 'w') as f:
            json.dump({"last_run": datetime.now().isoformat()}, f)

        logger.info(f"Periodic consolidation: {counts}")
        return counts
    except Exception as e:
        logger.warning(f"Periodic consolidation failed (non-fatal): {e}")
        return None


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
            context_lines.append(f"Auto-archived {archived_count} stale todo(s) (pending >7d or in_progress >3d)")
        if todo_count > 0:
            context_lines.append("")
            context_lines.append(f"You have {todo_count} outstanding tasks from previous sessions. Restore them by calling start_session() and creating TaskCreate entries for each outstanding todo.")

        # F130: Run periodic memory consolidation (24h cooldown)
        try:
            consolidation_conn = get_db_connection()
            if consolidation_conn:
                counts = run_periodic_consolidation(consolidation_conn)
                if counts and any(v > 0 for v in counts.values()):
                    context_lines.append(f"Memory consolidation: {counts['promoted_mid_to_long']} promoted, {counts['decayed_edges']} decayed, {counts['archived']} archived")
                consolidation_conn.close()
        except Exception as e:
            logger.warning(f"Periodic consolidation skipped: {e}")

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
