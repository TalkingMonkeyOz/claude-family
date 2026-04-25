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
import tempfile
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
    """Check system health: DB, embedding provider, required env vars."""
    health = {
        'database': {'status': 'unknown', 'message': ''},
        'embeddings': {'status': 'unknown', 'message': ''},
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

    # Check embedding provider (for RAG) — F208.4: config + live /health ping
    try:
        from embedding_provider import get_provider_info
        pinfo = get_provider_info()
        provider_name = pinfo['provider']
        model_name = pinfo['model']
        live_status = ''
        if provider_name == 'http':
            # Ping the service /health endpoint to catch silent degradation (e.g. 2026-04-18 9h outage)
            try:
                import urllib.request as _ur
                import json as _json
                service_url = os.environ.get('EMBEDDING_SERVICE_URL', 'http://127.0.0.1:9900')
                with _ur.urlopen(f'{service_url}/health', timeout=2) as resp:
                    hdata = _json.loads(resp.read().decode('utf-8'))
                if not hdata.get('model_loaded'):
                    raise RuntimeError(f"model_loaded=False")
                live_status = f", service-live (calls={hdata.get('call_count', 0)})"
                health['embeddings'] = {
                    'status': 'ok',
                    'message': f'{provider_name} ({model_name}, local={pinfo["local"]}){live_status}'
                }
            except Exception as live_exc:
                health['embeddings'] = {
                    'status': 'error',
                    'message': f'HTTP service unreachable: {str(live_exc)[:60]}'
                }
                issues.append(f'EMBEDDINGS DOWN: {str(live_exc)[:40]}')
        else:
            health['embeddings'] = {
                'status': 'ok',
                'message': f'{provider_name} ({model_name}, local={pinfo["local"]})'
            }
    except Exception as e:
        if health['embeddings'].get('status') != 'error':
            health['embeddings'] = {'status': 'warning', 'message': f'Embedding provider error: {str(e)[:50]}'}
            issues.append(f'Embeddings: {str(e)[:30]}')

    # Check required env vars
    required_vars = ['POSTGRES_PASSWORD']
    optional_vars = ['ANTHROPIC_API_KEY']
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

def log_session_start(project_name: str, identity_id: str, claude_session_id: str = None) -> tuple:
    """Log session start to database, return (session_id, error_msg).

    If claude_session_id is provided (from Claude Code's SessionStart stdin),
    use it as the DB primary key so end_session() can locate the exact row.
    Otherwise generate a UUID (legacy behavior — loses linkage).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # If Claude Code gave us a session_id, prefer upsert on it so the DB
        # row matches Claude Code's identity 1:1.
        if claude_session_id:
            cur.execute("""
                INSERT INTO claude.sessions
                    (session_id, identity_id, session_start, project_name, session_summary)
                VALUES (%s::uuid, %s, NOW(), %s, 'Session auto-started via hook')
                ON CONFLICT (session_id) DO UPDATE
                    SET project_name = EXCLUDED.project_name
                RETURNING session_id::text
            """, (claude_session_id, identity_id, project_name))
            result = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return (result['session_id'] if result else None, None)

        # Fallback: no Claude session_id — dedup within 60s window
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


def deploy_standing_orders():
    """Deploy standing orders from DB to project's MEMORY.md.

    Reads the active STANDING_ORDERS from protocol_versions and ensures
    it exists as a section at the top of the project's MEMORY.md file.
    Fail-open: if anything goes wrong, log and continue.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT content FROM claude.protocol_versions
            WHERE protocol_name = 'STANDING_ORDERS' AND is_active = true
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            logger.info("No active standing orders found")
            return

        standing_orders_content = row['content'].strip()

        # Find MEMORY.md path
        cwd = os.getcwd()
        # Encode path: C:\Projects\claude-family -> C--Projects--claude-family
        encoded_path = cwd.replace(':\\', '--').replace('\\', '--').replace('/', '--')
        memory_dir = Path.home() / ".claude" / "projects" / encoded_path / "memory"
        memory_file = memory_dir / "MEMORY.md"

        # Ensure directory exists
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Read existing content
        existing_content = ""
        if memory_file.exists():
            existing_content = memory_file.read_text(encoding='utf-8')

        # Check if standing orders section already exists and is current
        section_marker = "## Standing Orders"
        if section_marker in existing_content:
            # Find the section boundaries
            start_idx = existing_content.index(section_marker)
            # Find the next ## heading after the standing orders section
            rest_after_section = existing_content[start_idx + len(section_marker):]
            next_heading_idx = rest_after_section.find('\n## ')

            if next_heading_idx >= 0:
                # There's content after the section
                end_idx = start_idx + len(section_marker) + next_heading_idx
                current_section = existing_content[start_idx:end_idx].strip()
                rest_content = existing_content[end_idx:]
            else:
                # Standing orders is the last section
                current_section = existing_content[start_idx:].strip()
                rest_content = ""

            before_section = existing_content[:start_idx]

            # Only rewrite if content changed
            if current_section.strip() != standing_orders_content.strip():
                new_content = before_section + standing_orders_content + "\n\n" + rest_content.lstrip('\n')
                memory_file.write_text(new_content, encoding='utf-8')
                logger.info("Standing orders updated in MEMORY.md")
            else:
                logger.info("Standing orders already current in MEMORY.md")
        else:
            # Prepend standing orders at the top
            if existing_content:
                new_content = standing_orders_content + "\n\n" + existing_content
            else:
                new_content = standing_orders_content + "\n"
            memory_file.write_text(new_content, encoding='utf-8')
            logger.info("Standing orders deployed to MEMORY.md")

    except Exception as e:
        logger.warning(f"Standing orders deployment failed (non-fatal): {e}")


def main():
    """Run session startup with lean output."""

    result = {
        "additionalContext": "",
        "systemMessage": ""
    }

    context_lines = []
    handoff_summary = ""  # Visible handoff for systemMessage (set in handoff block)
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

        # Read Claude Code's session_id from stdin JSON. Claude Code sends
        # {session_id, transcript_path, hook_event_name, ...} on SessionStart.
        # Using this as the DB primary key makes end_session() able to find
        # the exact row later instead of guessing by project_name.
        claude_session_id = None
        try:
            if not sys.stdin.isatty():
                stdin_data = sys.stdin.read()
                if stdin_data:
                    payload = json.loads(stdin_data)
                    claude_session_id = payload.get("session_id")
        except Exception as e:
            logger.warning(f"Could not parse SessionStart stdin: {e}")

        # === SELF-HEAL: Run sync_project.py if not launched via BAT ===
        try:
            sync_script = Path(__file__).parent / "sync_project.py"
            if sync_script.exists():
                import subprocess
                creationflags = 0
                if hasattr(subprocess, "CREATE_NO_WINDOW"):
                    creationflags = subprocess.CREATE_NO_WINDOW
                sync_result = subprocess.run(
                    [sys.executable, str(sync_script), "--no-interactive"],
                    capture_output=True, text=True, timeout=30, cwd=cwd,
                    creationflags=creationflags
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

            # Log session to database (use Claude Code session_id if available)
            session_id, error = log_session_start(project_name, identity_id, claude_session_id)
            if session_id:
                context_lines.append(f"Session ID: {session_id}")
                # Persist the session_id to disk so end_session() can find it
                # without relying on env vars (which Claude Code does not set
                # for MCP tools).
                try:
                    marker_dir = Path(cwd) / ".claude"
                    marker_dir.mkdir(exist_ok=True)
                    (marker_dir / ".current_session_id").write_text(session_id, encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Could not write .current_session_id: {e}")
            else:
                context_lines.append(f"Could not log session: {error or 'unknown error'}")
                session_id = None

            # Deploy standing orders to MEMORY.md
            deploy_standing_orders()

            # Close zombie sessions (open > 12h, excluding the session just created).
            # Threshold tightened from 24h → 12h (BT719, 2026-04-22): with the
            # session_id fix landed, real sessions close properly; anything older
            # than 12h without session_end is definitively abandoned. Stops the
            # pre-fix orphan-accumulation pattern from recurring.
            try:
                zombie_conn = get_db_connection()
                if zombie_conn:
                    zombie_cur = zombie_conn.cursor()
                    zombie_cur.execute("""
                        UPDATE claude.sessions
                        SET session_end = session_start + INTERVAL '1 hour',
                            session_summary = 'auto-closed (zombie cleanup on session start)'
                        WHERE session_end IS NULL
                          AND session_start < NOW() - INTERVAL '12 hours'
                          AND (%s IS NULL OR session_id != %s::uuid)
                    """, (session_id, session_id))
                    zombie_count = zombie_cur.rowcount
                    zombie_conn.commit()
                    zombie_conn.close()
                    if zombie_count > 0:
                        logger.info(f"Closed {zombie_count} zombie sessions (>24h old)")
            except Exception as e:
                logger.warning(f"Zombie cleanup failed (non-fatal): {e}")

            # FB317: Expire stale inbox messages. Anything with expires_at in
            # the past that hasn't been actioned/deferred is auto-deferred.
            # Mirrors the zombie-session cleanup pattern.
            try:
                exp_conn = get_db_connection()
                if exp_conn:
                    exp_cur = exp_conn.cursor()
                    exp_cur.execute("""
                        UPDATE claude.messages
                        SET status = 'deferred',
                            metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                              'auto_deferred_at', NOW()::text,
                              'auto_deferred_reason', 'FB317 auto-expire (SessionStart sweep)'
                            )
                        WHERE status IN ('pending','read','acknowledged')
                          AND expires_at IS NOT NULL
                          AND expires_at < NOW()
                    """)
                    exp_count = exp_cur.rowcount
                    exp_conn.commit()
                    exp_conn.close()
                    if exp_count > 0:
                        logger.info(f"Auto-deferred {exp_count} expired messages")
            except Exception as e:
                logger.warning(f"Message expiry sweep failed (non-fatal): {e}")

            # FB242: Archive stale [S]-prefixed session tasks from prior sessions
            # Protocol convention: [S]=session-scope dies at session end, [P]=persistent survives
            try:
                sess_conn = get_db_connection()
                if sess_conn:
                    sess_cur = sess_conn.cursor()
                    sess_cur.execute("""
                        UPDATE claude.todos t
                        SET status = 'archived', updated_at = NOW()
                        FROM claude.projects p
                        WHERE t.project_id = p.project_id
                          AND p.project_name = %s
                          AND NOT t.is_deleted
                          AND t.status IN ('pending', 'in_progress')
                          AND t.content LIKE '[S]%%'
                          AND (%s::uuid IS NULL OR t.created_session_id IS DISTINCT FROM %s::uuid)
                    """, (project_name, session_id, session_id))
                    archived_session_tasks = sess_cur.rowcount
                    sess_conn.commit()
                    sess_conn.close()
                    if archived_session_tasks > 0:
                        context_lines.append(f"Archived {archived_session_tasks} stale [S]-prefixed task(s) from prior sessions")
                        logger.info(f"FB242: archived {archived_session_tasks} stale session-scope tasks")
            except Exception as e:
                logger.warning(f"Session task cleanup failed (non-fatal): {e}")

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

            # Clean up completed task files from disk
            try:
                from task_cleanup import cleanup_completed_tasks
                cleaned = cleanup_completed_tasks()
                if cleaned > 0:
                    context_lines.append(f"Cleaned up {cleaned} completed task file(s)")
                    logger.info(f"Cleaned up {cleaned} completed task file(s) at startup")
            except Exception as e:
                logger.warning(f"Task cleanup failed (non-fatal): {e}")

            # === CKG STALENESS CHECK: async re-index if code changed ===
            try:
                import subprocess as _sp
                _cflags = 0x08000000 if sys.platform == 'win32' else 0  # CREATE_NO_WINDOW
                # Get current git HEAD
                git_result = _sp.run(
                    ['git', 'rev-parse', 'HEAD'],
                    capture_output=True, text=True, timeout=5, cwd=cwd,
                    creationflags=_cflags
                )
                if git_result.returncode == 0:
                    current_head = git_result.stdout.strip()
                    # Check last indexed commit from DB
                    ckg_conn = get_db_connection()
                    if ckg_conn:
                        ckg_cur = ckg_conn.cursor()
                        ckg_cur.execute("""
                            SELECT count(*) as sym_count,
                                   max(last_indexed_at) as last_indexed
                            FROM claude.code_symbols cs
                            JOIN claude.projects p ON cs.project_id = p.project_id
                            WHERE p.project_name = %s
                        """, (project_name,))
                        ckg_row = ckg_cur.fetchone()
                        sym_count = ckg_row['sym_count'] if isinstance(ckg_row, dict) else ckg_row[0]
                        ckg_conn.close()

                        if sym_count > 0:
                            # Project is indexed — check if git HEAD changed since last index
                            # by comparing file hashes (the indexer handles this internally)
                            # Spawn async re-index in background
                            indexer_script = Path(__file__).parent / "code_indexer.py"
                            if indexer_script.exists():
                                _sp.Popen(
                                    [sys.executable, str(indexer_script), project_name, cwd],
                                    stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                                    creationflags=0x08000008 if sys.platform == 'win32' else 0,  # CREATE_NO_WINDOW | DETACHED_PROCESS
                                    start_new_session=True if sys.platform != 'win32' else False,
                                )
                                logger.info(f"CKG: spawned async re-index for {project_name} ({sym_count} existing symbols)")

                        # Spawn CKG daemon if not already running (F160 perf fix)
                        daemon_script = Path(__file__).parent / "ckg_daemon.py"
                        if daemon_script.exists():
                            import hashlib as _hl
                            daemon_port = 9800 + (int(_hl.md5(project_name.encode()).hexdigest(), 16) % 100)
                            # Quick health check — is daemon already up?
                            import urllib.request as _ur
                            try:
                                _ur.urlopen(f'http://127.0.0.1:{daemon_port}/health', timeout=0.5)
                                logger.info(f"CKG daemon already running on port {daemon_port}")
                            except Exception:
                                _sp.Popen(
                                    [sys.executable, str(daemon_script), project_name, cwd],
                                    stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                                    creationflags=0x00000008 if sys.platform == 'win32' else 0,
                                    start_new_session=True if sys.platform != 'win32' else False,
                                )
                                logger.info(f"CKG: spawned daemon for {project_name} on port {daemon_port}")
            except Exception as e:
                logger.warning(f"CKG staleness check failed (non-fatal): {e}")

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
                context_lines.append("Use inbox() to see full details. Use inbox(ack_action='acknowledged') to action or defer.")

            # Show valid recipients for messaging
            recipients = get_valid_recipients()
            if recipients:
                names = [r['project_name'] for r in recipients[:10]]
                context_lines.append(f"Messaging recipients: {', '.join(names)}")

            # Added 2026-04-08: Inject handoff context from session_state for session continuity
            try:
                handoff_conn = get_db_connection()
                if handoff_conn:
                    handoff_cur = handoff_conn.cursor()
                    handoff_cur.execute("""
                        SELECT current_focus, next_steps, updated_at
                        FROM claude.session_state
                        WHERE project_name = %s
                    """, (project_name,))
                    handoff = handoff_cur.fetchone()
                    handoff_conn.close()

                    if handoff and handoff.get('current_focus'):
                        import json as _json
                        focus = handoff['current_focus']
                        next_steps = handoff.get('next_steps') or []
                        if isinstance(next_steps, str):
                            try:
                                next_steps = _json.loads(next_steps)
                            except Exception:
                                next_steps = [next_steps]

                        context_lines.append("")
                        context_lines.append("## Previous Session Handoff")
                        context_lines.append(f"**Last focus:** {focus}")
                        if next_steps:
                            context_lines.append("**Next steps:**")
                            for i, step in enumerate(next_steps, 1):
                                context_lines.append(f"  {i}. {step}")

                        # Build visible summary for systemMessage
                        # Truncate focus to first 80 chars for readability
                        short_focus = focus[:80] + ("..." if len(focus) > 80 else "")
                        step_list = "; ".join(f"{i}. {s}" for i, s in enumerate(next_steps[:3], 1)) if next_steps else ""
                        handoff_summary = f"\nHandoff: {short_focus}"
                        if step_list:
                            handoff_summary += f"\nNext: {step_list}"

                        logger.info(f"Injected handoff context: focus='{focus[:50]}...', {len(next_steps)} next steps")
            except Exception as e:
                logger.warning(f"Handoff context injection skipped (non-fatal): {e}")

            # F156: Auto-detect and load dossier from git branch or active tasks
            try:
                import subprocess as _git_sp
                _git_cflags = 0x08000000 if sys.platform == 'win32' else 0  # CREATE_NO_WINDOW
                branch_result = _git_sp.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True, text=True, timeout=5, cwd=cwd,
                    creationflags=_git_cflags
                )
                branch_name = branch_result.stdout.strip() if branch_result.returncode == 0 else ""

                # Extract component hint from branch: feature/F156-dossier-system → dossier-system
                dossier_component = None
                if branch_name and '/' in branch_name:
                    branch_suffix = branch_name.split('/', 1)[1]
                    # Strip feature code prefix (F123-, FB45-, BT67-)
                    import re
                    component_hint = re.sub(r'^[A-Z]+\d+-', '', branch_suffix)
                    if component_hint:
                        dossier_component = component_hint

                # Also check active in_progress tasks for component hints
                if not dossier_component and pending_tasks:
                    in_progress = [t for t in pending_tasks if t.get('status') == 'in_progress']
                    if in_progress:
                        # Use first in-progress task content as search hint
                        task_hint = in_progress[0].get('content', '')
                        if len(task_hint) > 10:
                            dossier_component = task_hint[:50].lower().replace(' ', '-')

                if dossier_component:
                    dossier_conn = get_db_connection()
                    if dossier_conn:
                        dossier_cur = dossier_conn.cursor()
                        dossier_cur.execute("""
                            SELECT component, title, LEFT(content, 300) as preview
                            FROM claude.project_workfiles pw
                            JOIN claude.projects p ON pw.project_id = p.project_id
                            WHERE p.project_name = %s
                              AND pw.is_active = TRUE
                              AND (pw.component ILIKE %s OR pw.component ILIKE %s)
                            ORDER BY pw.updated_at DESC
                            LIMIT 3
                        """, (project_name, f"%{dossier_component}%", f"%{dossier_component.split('-')[0]}%"))
                        dossiers = dossier_cur.fetchall()
                        dossier_conn.close()

                        if dossiers:
                            context_lines.append("")
                            context_lines.append(f"ACTIVE WORKFILE (auto-detected from branch/task):")
                            for d in dossiers:
                                comp = d['component'] if isinstance(d, dict) else d[0]
                                title = d['title'] if isinstance(d, dict) else d[1]
                                preview = d['preview'] if isinstance(d, dict) else d[2]
                                context_lines.append(f"  [{comp}] {title}")
                                if preview:
                                    context_lines.append(f"    {preview[:150]}...")
                            context_lines.append("  Use workfile_read(component) to load full workfile content")
                            logger.info(f"F156: Auto-detected {len(dossiers)} dossier(s) for component '{dossier_component}'")
            except Exception as e:
                logger.warning(f"Dossier auto-detection skipped (non-fatal): {e}")

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

    # === SESSION CONTEXT CACHE for protocol_inject_hook.py ===
    # Pre-compute context that gets injected on every prompt via the lightweight hook.
    # This replaces the old rag_query_hook.py per-prompt RAG (which timed out due to voyageai 8s import).
    try:
        cache_parts = []
        cache_conn = get_db_connection()
        if cache_conn:
            cache_cur = cache_conn.cursor()
            # Active features for this project
            cache_cur.execute("""
                SELECT f.short_code, f.feature_name, f.status
                FROM claude.features f
                JOIN claude.projects p ON f.project_id = p.project_id
                WHERE p.project_name = %s AND f.status IN ('planned', 'in_progress')
                ORDER BY f.priority, f.created_at
                LIMIT 5
            """, (project_name,))
            features = cache_cur.fetchall()
            if features:
                cache_parts.append("ACTIVE FEATURES:")
                for f in features:
                    code = f['short_code'] if isinstance(f, dict) else f[0]
                    name = f['feature_name'] if isinstance(f, dict) else f[1]
                    status = f['status'] if isinstance(f, dict) else f[2]
                    cache_parts.append(f"  {code} {name} ({status})")

            # Pinned workfiles — title-only pointers (B0 context-bloat trim 2026-04-24).
            # Claude loads full content on demand via workfile_read(component, title).
            cache_cur.execute("""
                SELECT pw.component, pw.title,
                       LEFT(pw.content, 120) as content_headline
                FROM claude.project_workfiles pw
                JOIN claude.projects p ON pw.project_id = p.project_id
                WHERE p.project_name = %s AND pw.is_pinned = true AND pw.is_active = true
                ORDER BY pw.access_count DESC
                LIMIT 5
            """, (project_name,))
            workfiles = cache_cur.fetchall()
            if workfiles:
                cache_parts.append("PINNED WORKFILES (use workfile_read to load full content):")
                for w in workfiles:
                    comp = w['component'] if isinstance(w, dict) else w[0]
                    title = w['title'] if isinstance(w, dict) else w[1]
                    headline = w['content_headline'] if isinstance(w, dict) else w[2]
                    # One-line headline only — strip newlines, collapse whitespace
                    if headline:
                        import re as _re
                        headline_clean = _re.sub(r'\s+', ' ', headline).strip()[:100]
                        cache_parts.append(f"  {comp}/{title} — {headline_clean}")
                    else:
                        cache_parts.append(f"  {comp}/{title}")

            # Top knowledge gotchas — proactive injection of high-confidence entries
            # 2026-04-25: partial restore of B0 trim. Top-3 gotchas now ship with a
            # 220-char body so Claude can ACT on them without an extra recall hop.
            # Remainder stay title-only with explicit recall hint. The pure title-only
            # version (cbbf21e) caused regression — titles felt familiar, Claude pattern-
            # matched without recalling, and lost the gotcha content entirely.
            cache_cur.execute("""
                SELECT title, LEFT(description, 220) as desc_preview, LENGTH(description) as full_len
                FROM claude.knowledge
                WHERE (%s = ANY(applies_to_projects) OR applies_to_projects IS NULL)
                  AND knowledge_type = 'gotcha'
                  AND tier IN ('long', 'mid')
                  AND confidence_level >= 75
                ORDER BY confidence_level DESC, access_count DESC
                LIMIT 10
            """, (project_name,))
            gotchas = cache_cur.fetchall()
            if gotchas:
                cache_parts.append("KEY GOTCHAS (top-3 with body; rest: recall_memories(\"gotcha title\") for full):")
                import re as _re_g
                for i, g in enumerate(gotchas):
                    title = g['title'] if isinstance(g, dict) else g[0]
                    desc = g['desc_preview'] if isinstance(g, dict) else g[1]
                    full_len = g['full_len'] if isinstance(g, dict) else g[2]
                    if i < 3 and desc:
                        body = _re_g.sub(r'\s+', ' ', desc).strip()
                        ellipsis = "…" if full_len and full_len > 220 else ""
                        cache_parts.append(f"  - {title}: {body}{ellipsis}")
                    else:
                        cache_parts.append(f"  - {title} …")

            # Session facts from recent sessions (credentials masked)
            cache_cur.execute("""
                SELECT fact_key, fact_type
                FROM claude.session_facts
                WHERE project_name = %s
                  AND fact_type IN ('credential', 'config', 'endpoint')
                ORDER BY created_at DESC
                LIMIT 10
            """, (project_name,))
            facts = cache_cur.fetchall()
            if facts:
                cache_parts.append("SESSION FACTS AVAILABLE:")
                for sf in facts:
                    key = sf['fact_key'] if isinstance(sf, dict) else sf[0]
                    ftype = sf['fact_type'] if isinstance(sf, dict) else sf[1]
                    cache_parts.append(f"  [{ftype}] {key}")
                cache_parts.append("  Use recall_session_fact(key) to retrieve values.")

            # Architecture articles — title-only index (B0 context-bloat trim 2026-04-24).
            # Claude loads abstract + body via article_read(query) on demand.
            cache_cur.execute("""
                SELECT title
                FROM claude.knowledge_articles
                WHERE status = 'published'
                  AND article_type = 'architecture'
                ORDER BY updated_at DESC
                LIMIT 5
            """)
            articles = cache_cur.fetchall()
            if articles:
                titles = [a['title'] if isinstance(a, dict) else a[0] for a in articles]
                cache_parts.append("ARCHITECTURE ARTICLES: " + " | ".join(titles))
                cache_parts.append("  Use article_read(query) to load any of the above.")

            cache_conn.close()

        # Write cache file
        if cache_parts:
            cache_file = os.path.join(
                tempfile.gettempdir(),
                f"claude_session_context_{project_name}.txt",
            )
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write("\n".join(cache_parts))
            logger.info(f"Session context cache written: {len(cache_parts)} lines -> {cache_file}")
    except Exception as e:
        logger.warning(f"Session context cache generation failed (non-fatal): {e}")

    # =========================================================================
    # Due reminders (scheduled_reminders) — surface and mark as surfaced.
    # Global (project_name IS NULL) + this project's reminders whose due_at has
    # passed AND snoozed_until is not in the future AND not yet surfaced.
    # =========================================================================
    reminder_lines: list = []
    try:
        reminder_conn = get_db_connection()
        if reminder_conn:
            rcur = reminder_conn.cursor()
            rcur.execute("""
                SELECT reminder_id::text, short_code, due_at, body, rationale,
                       linked_todo_id::text, linked_workfile_component,
                       linked_workfile_title, linked_feature_code
                FROM claude.scheduled_reminders
                WHERE (project_name IS NULL OR project_name = %s)
                  AND surfaced_at IS NULL
                  AND due_at <= NOW()
                  AND (snoozed_until IS NULL OR snoozed_until <= NOW())
                ORDER BY due_at ASC
                LIMIT 10
            """, (project_name,))
            due_rows = rcur.fetchall()

            if due_rows:
                reminder_lines.append("")
                reminder_lines.append("⏰ DUE REMINDERS (fire once, acknowledged on display):")
                surfaced_ids = []
                for r in due_rows:
                    code = r['short_code']
                    body = r['body']
                    rationale = r['rationale']
                    link_bits = []
                    if r['linked_todo_id']:
                        link_bits.append(f"todo={r['linked_todo_id'][:8]}")
                    if r['linked_feature_code']:
                        link_bits.append(f"feature={r['linked_feature_code']}")
                    if r['linked_workfile_component']:
                        wf = r['linked_workfile_component']
                        if r['linked_workfile_title']:
                            wf += f"/{r['linked_workfile_title']}"
                        link_bits.append(f"workfile={wf}")
                    link_str = f" [{', '.join(link_bits)}]" if link_bits else ""

                    reminder_lines.append(f"  {code}: {body}{link_str}")
                    if rationale:
                        reminder_lines.append(f"    why: {rationale}")
                    surfaced_ids.append(r['reminder_id'])

                reminder_lines.append(
                    "  Action: use snooze_reminder(code, new_due_at, reason) to push forward, "
                    "or just act now."
                )

                rcur.execute(
                    "UPDATE claude.scheduled_reminders SET surfaced_at = NOW() "
                    "WHERE reminder_id = ANY(%s::uuid[])",
                    (surfaced_ids,),
                )
                reminder_conn.commit()

            rcur.close()
            reminder_conn.close()
    except Exception as e:
        logger.warning(f"Reminder surfacing failed (non-fatal): {e}")

    if reminder_lines:
        context_lines.extend(reminder_lines)

    result["additionalContext"] = "\n".join(context_lines)
    result["systemMessage"] = f"Claude Family session started for {project_name}. Session logged to database.{handoff_summary}"

    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
