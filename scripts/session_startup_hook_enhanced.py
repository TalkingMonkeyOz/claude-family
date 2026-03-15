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
from config import (
    POSTGRES_CONFIG,
    get_db_connection as _config_get_db_connection,
    detect_psycopg,
    rotate_hooks_log,
    setup_hook_logging,
)

# Rotate hooks.log before configuring the handler so the new file starts fresh.
rotate_hooks_log()
logger = setup_hook_logging(__name__)

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

def get_pending_tasks(project_name: str) -> list:
    """Get ALL pending/in_progress todos for this project with content.

    No time-based archival — tasks persist until explicitly completed or archived.
    Holiday-safe: going away for weeks doesn't lose tasks.

    Returns list of dicts: [{content, status, created_at_str}]
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT t.content, t.status, t.created_at::date::text AS created_date
            FROM claude.todos t
            JOIN claude.projects p ON t.project_id = p.project_id
            WHERE p.project_name = %s
              AND t.status IN ('pending', 'in_progress')
              AND NOT t.is_deleted
            ORDER BY t.status DESC, t.created_at DESC
            LIMIT 30
        """, (project_name,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception:
        return []


def get_recently_completed_tasks(project_name: str) -> list:
    """Get tasks completed in the last closed session for this project.

    Provides "what did we finish?" context without restoring as active tasks.

    Returns list of dicts: [{content, completed_at_str}]
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Get recently completed todos — try session-scoped first, fall back to time-based
        cur.execute("""
            SELECT t.content, t.completed_at::date::text AS completed_date
            FROM claude.todos t
            JOIN claude.projects p ON t.project_id = p.project_id
            WHERE p.project_name = %s
              AND t.status = 'completed'
              AND NOT t.is_deleted
              AND t.completed_at IS NOT NULL
              AND t.completed_at > NOW() - INTERVAL '48 hours'
            ORDER BY t.completed_at DESC
            LIMIT 10
        """, (project_name,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception:
        return []


def get_unactioned_messages(project_name: str) -> list:
    """Get unactioned messages for this project (pending/read/acknowledged).

    Injects into startup context so Claude sees messages without being asked.
    Also auto-defers messages from projects inactive 90+ days.

    Returns list of dicts: [{from_project, subject, message_type, priority, created_date, message_id}]
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Auto-defer messages FROM inactive projects (no session in 90+ days)
        cur.execute("""
            UPDATE claude.messages m
            SET status = 'deferred'
            WHERE m.to_project = %s
              AND m.status IN ('pending', 'read', 'acknowledged')
              AND m.from_project IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM claude.sessions s
                  WHERE s.project_name = m.from_project
                    AND s.session_start > NOW() - INTERVAL '90 days'
              )
        """, (project_name,))
        stale_deferred = cur.rowcount
        if stale_deferred > 0:
            conn.commit()
            logger.info(f"Auto-deferred {stale_deferred} messages from inactive projects")

        # Get unactioned messages (urgent first, then by date)
        cur.execute("""
            SELECT m.message_id::text, m.from_project, m.subject, m.message_type,
                   m.priority, m.created_at::date::text AS created_date
            FROM claude.messages m
            WHERE (m.to_project = %s OR (m.to_project IS NULL AND m.message_type = 'broadcast'))
              AND m.status NOT IN ('actioned', 'deferred')
            ORDER BY
                CASE m.priority WHEN 'urgent' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
                m.created_at DESC
            LIMIT 10
        """, (project_name,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception:
        return []


def get_valid_recipients() -> list:
    """Get list of valid messaging recipients (active workspaces).

    Returns list of dicts: [{project_name, last_session_date}]
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT w.project_name,
                   MAX(s.session_start)::date::text AS last_active
            FROM claude.workspaces w
            LEFT JOIN claude.sessions s ON LOWER(s.project_name) = LOWER(w.project_name)
            WHERE w.is_active = true
            GROUP BY w.project_name
            ORDER BY MAX(s.session_start) DESC NULLS LAST
            LIMIT 20
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception:
        return []


def _reset_task_map(project_name: str, session_id: str):
    """Reset task_map with new session_id.

    In shared task list mode (CLAUDE_CODE_TASK_LIST_ID set), preserves existing
    task entries and only updates _session_id + resets delegation tracking.
    In normal mode, writes a fresh map (previous behavior).

    This prevents the discipline hook from rejecting Write/Edit calls due to
    a stale task_map left over from a crashed or interrupted session.
    """
    import tempfile
    map_path = os.path.join(tempfile.gettempdir(), f"claude_task_map_{project_name}.json")

    shared_list = os.environ.get('CLAUDE_CODE_TASK_LIST_ID')

    if shared_list:
        # Shared mode: preserve task entries, update session metadata only
        try:
            existing = {}
            if os.path.exists(map_path):
                with open(map_path, 'r') as f:
                    existing = json.load(f)
                    if not isinstance(existing, dict):
                        existing = {}
        except (json.JSONDecodeError, IOError):
            existing = {}

        # Update session_id and reset per-session tracking
        existing['_session_id'] = session_id
        existing['_delegation_advised'] = False
        existing['_files_edited'] = []

        try:
            with open(map_path, 'w') as f:
                json.dump(existing, f)
        except IOError:
            pass
    else:
        # Normal mode: fresh map (no task persistence across sessions)
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

        # Mid→Long promotion: retrieval-frequency based
        # access_count >= 5 (retrieved by RAG/recall_memories), age >= 7 days, has embedding
        cur.execute("""
            UPDATE claude.knowledge
            SET tier = 'long'
            WHERE tier = 'mid'
              AND COALESCE(access_count, 0) >= 5
              AND confidence_level >= 60
              AND created_at < NOW() - INTERVAL '7 days'
              AND embedding IS NOT NULL
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


def _replay_session_end_fallback():
    """Replay orphaned session_end records from the JSONL fallback file.

    Called early in startup after DB is confirmed working.  Each fallback entry
    represents a session where session_end_hook could not reach the DB and wrote
    a JSONL record instead.  We close those sessions now.

    Fails silently — this is best-effort cleanup, not critical path.
    """
    try:
        from hook_data_fallback import replay_fallback, get_pending_count

        pending = get_pending_count("session_end")
        if pending == 0:
            return

        def _close_session(data: dict) -> bool:
            """Close a single orphaned session. Returns True on success."""
            session_id = data.get("session_id")
            project_name = data.get("project_name", "")
            try:
                conn = get_db_connection()
                if not conn:
                    return False
                cur = conn.cursor()
                if session_id:
                    cur.execute("""
                        UPDATE claude.sessions
                        SET session_end = NOW(),
                            session_summary = COALESCE(session_summary,
                                'Session auto-closed via fallback replay (startup hook)')
                        WHERE session_id = %s::uuid
                          AND session_end IS NULL
                    """, (session_id,))
                else:
                    # No session_id — close the most recent unclosed session for the project
                    cur.execute("""
                        UPDATE claude.sessions
                        SET session_end = NOW(),
                            session_summary = COALESCE(session_summary,
                                'Session auto-closed via fallback replay (startup hook)')
                        WHERE project_name = %s
                          AND session_end IS NULL
                          AND session_start > NOW() - INTERVAL '48 hours'
                        ORDER BY session_start DESC
                        LIMIT 1
                    """, (project_name,))
                conn.commit()
                cur.close()
                conn.close()
                return True
            except Exception as e:
                logger.warning(f"Fallback replay failed for session {session_id}: {e}")
                try:
                    conn.close()
                except Exception:
                    pass
                return False

        replayed = replay_fallback("session_end", _close_session)
        if replayed > 0:
            logger.info(f"Replayed {replayed} orphaned session_end record(s) from fallback")
    except Exception as e:
        logger.warning(f"session_end fallback replay skipped: {e}")


def main():
    """Run session startup with lean output."""

    result = {
        "additionalContext": "",
        "systemMessage": ""
    }

    context_lines = []
    # Pre-initialize project_name so it is available in the systemMessage even
    # if the try block exits early due to an exception.
    project_name = os.path.basename(os.getcwd())

    try:
        # Confirm project name (may be refined inside the try block)
        cwd = os.getcwd()
        project_name = os.path.basename(cwd)

        # Determine identity (default to unified)
        identity_name = 'claude-code-unified'
        identity_id = IDENTITY_MAP.get(identity_name, IDENTITY_MAP['claude-code-unified'])

        # === SELF-HEAL: Run sync_project.py if not launched via BAT ===
        try:
            sync_script = Path(__file__).parent / "sync_project.py"
            if sync_script.exists():
                import subprocess
                sync_result = subprocess.run(
                    [sys.executable, str(sync_script), "--no-interactive"],
                    capture_output=True, text=True, timeout=30, cwd=cwd
                )
                if sync_result.returncode == 0:
                    logger.info("Self-heal: sync_project.py completed successfully")
                else:
                    logger.warning(f"Self-heal: sync_project.py returned {sync_result.returncode}")
        except Exception as e:
            logger.warning(f"Self-heal sync skipped: {e}")

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
            # Replay any orphaned session_end records from previous DB outages.
            # Run before logging the new session so the DB is confirmed working first.
            _replay_session_end_fallback()

            # Log session to database
            session_id, error = log_session_start(project_name, identity_id)
            if session_id:
                context_lines.append(f"Session ID: {session_id}")
            else:
                context_lines.append(f"Could not log session: {error or 'unknown error'}")
                session_id = None

            # Close zombie sessions (open > 24h, excluding the session just created)
            try:
                zombie_conn = get_db_connection()
                if zombie_conn:
                    zombie_cur = zombie_conn.cursor()
                    zombie_cur.execute("""
                        UPDATE claude.sessions
                        SET session_end = session_start + INTERVAL '1 hour',
                            session_summary = 'auto-closed (zombie cleanup on session start)'
                        WHERE session_end IS NULL
                          AND session_start < NOW() - INTERVAL '24 hours'
                          AND (%s IS NULL OR session_id != %s::uuid)
                    """, (session_id, session_id))
                    zombie_count = zombie_cur.rowcount
                    zombie_conn.commit()
                    zombie_conn.close()
                    if zombie_count > 0:
                        logger.info(f"Closed {zombie_count} zombie sessions (>24h old)")
            except Exception as e:
                logger.warning(f"Zombie cleanup failed (non-fatal): {e}")

            # 60-day retention: archive very old pending todos (holiday-safe threshold)
            try:
                retention_conn = get_db_connection()
                if retention_conn:
                    ret_cur = retention_conn.cursor()
                    ret_cur.execute("""
                        UPDATE claude.todos t
                        SET status = 'archived', updated_at = NOW()
                        FROM claude.projects p
                        WHERE t.project_id = p.project_id
                          AND p.project_name = %s
                          AND NOT t.is_deleted
                          AND t.status = 'pending'
                          AND t.created_at < NOW() - INTERVAL '60 days'
                    """, (project_name,))
                    archived_old = ret_cur.rowcount
                    retention_conn.commit()
                    retention_conn.close()
                    if archived_old > 0:
                        context_lines.append(f"Archived {archived_old} todo(s) older than 60 days")
                        logger.info(f"60-day retention: archived {archived_old} old todos")
            except Exception as e:
                logger.warning(f"Retention cleanup failed (non-fatal): {e}")

            # Read tasks back from DB → inject into context (task_lifecycle BPMN v4)
            pending_tasks = get_pending_tasks(project_name)
            completed_tasks = get_recently_completed_tasks(project_name)

            if pending_tasks:
                context_lines.append("")
                context_lines.append(f"EXISTING TASKS ({len(pending_tasks)} pending/in_progress):")
                for task in pending_tasks:
                    marker = ">>" if task['status'] == 'in_progress' else "  "
                    context_lines.append(f"  {marker} [{task['status']}] {task['content']} (created {task['created_date']})")
                context_lines.append("Check these before creating new tasks - avoid duplicates.")

            if completed_tasks:
                context_lines.append("")
                context_lines.append(f"LAST SESSION COMPLETED ({len(completed_tasks)}):")
                for task in completed_tasks:
                    context_lines.append(f"  [done] {task['content']} ({task['completed_date']})")

            # Read unactioned messages from DB (messaging lifecycle v2)
            unactioned_messages = get_unactioned_messages(project_name)
            if unactioned_messages:
                context_lines.append("")
                context_lines.append(f"UNACTIONED MESSAGES ({len(unactioned_messages)}):")
                for msg in unactioned_messages:
                    pri_marker = "[URGENT] " if msg['priority'] == 'urgent' else ""
                    from_proj = msg['from_project'] or 'broadcast'
                    context_lines.append(f"  {pri_marker}{msg['message_type']}: {msg['subject']} (from {from_proj}, {msg['created_date']})")
                context_lines.append("Use check_inbox() to see full details. Use acknowledge() to action or defer.")

            # Show valid recipients for messaging
            recipients = get_valid_recipients()
            if recipients:
                names = [r['project_name'] for r in recipients[:10]]
                context_lines.append(f"Messaging recipients: {', '.join(names)}")

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

            # System maintenance: detect staleness (fast, ~300ms)
            try:
                from system_maintenance import detect_all_staleness
                staleness = detect_all_staleness(conn=None)  # opens its own connection
                if staleness.get('any_stale'):
                    summary = staleness.get('summary', 'unknown subsystems')
                    context_lines.append(f"System staleness detected: {summary}. Run /maintenance to repair.")
            except Exception as e:
                logger.warning(f"Staleness detection skipped: {e}")

            # Clean task_map to prevent stale session errors from discipline hook
            if session_id:
                _reset_task_map(project_name, session_id)
        else:
            context_lines.append("Database not available (psycopg not installed)")

    except Exception as e:
        logger.error(f"Session startup hook failed: {e}", exc_info=True)
        # failure_capture requires DB — wrap to avoid cascading failure on DB outage
        try:
            from failure_capture import capture_failure
            capture_failure("session_startup_hook", str(e), "scripts/session_startup_hook_enhanced.py")
        except Exception:
            pass
        # Fail-open: still output something so Claude Code can continue
        context_lines.append(f"Session startup encountered an error: {e}")

    # Auto-load storage skill content (always available, survives compaction via PreCompact re-injection)
    try:
        skill_path = Path.home() / ".claude" / "skills" / "skill-load-memory-storage" / "SKILL.md"
        if skill_path.exists():
            skill_content = skill_path.read_text(encoding="utf-8", errors="replace")
            # Trim to essentials — skip the header and "Architecture Reference" section at the end
            if len(skill_content) > 100:
                context_lines.append("\n<storage-guide>\n" + skill_content + "\n</storage-guide>")
                logger.info("Storage skill auto-loaded into session context")
        else:
            logger.debug(f"Storage skill not found at {skill_path}")
    except Exception as e:
        logger.warning(f"Failed to auto-load storage skill: {e}")

    result["additionalContext"] = "\n".join(context_lines)
    result["systemMessage"] = f"Claude Family session started for {project_name}. Session logged to database."

    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
