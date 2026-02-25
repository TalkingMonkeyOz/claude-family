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

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg
DB_AVAILABLE = detect_psycopg()[0] is not None


def demote_in_progress_todos(project_name: str, conn):
    """Demote in_progress todos back to pending when session ends.

    Per task_lifecycle BPMN (demote_to_pending step): when a session ends,
    in_progress tasks should revert to pending. The next session's startup
    hook will then check staleness and either restore or archive them.
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE claude.todos t
            SET status = 'pending', updated_at = NOW()
            FROM claude.projects p
            WHERE t.project_id = p.project_id
              AND p.project_name = %s
              AND t.status = 'in_progress'
              AND NOT t.is_deleted
            RETURNING t.todo_id
        """, (project_name,))
        demoted = cur.fetchall()
        demoted_count = len(demoted)
        if demoted_count > 0:
            logger.info(f"Demoted {demoted_count} in_progress todo(s) to pending for {project_name}")
            # Audit trail: log the demotion so it's visible in audit_log
            try:
                cur.execute("""
                    INSERT INTO claude.audit_log
                    (entity_type, entity_id, from_status, to_status, changed_by, change_source, metadata)
                    VALUES ('todo_demotion', %s, 'in_progress', 'pending', 'session_end_hook',
                            'session_end_hook', %s::jsonb)
                """, (
                    project_name,
                    json.dumps({"reason": f"Auto-demoted {demoted_count} todo(s) on session exit"})
                ))
            except Exception as audit_err:
                logger.warning(f"Failed to write audit log for todo demotion: {audit_err}")
        return demoted_count
    except Exception as e:
        logger.error(f"Failed to demote in_progress todos: {e}")
        return 0


def consolidate_session_facts(project_name: str, conn):
    """Promote qualifying session facts to mid-tier knowledge (F130 Cognitive Memory).

    Lightweight version: inserts into claude.knowledge WITHOUT Voyage AI embeddings.
    Embeddings are added later by the MCP consolidate_memories() tool.
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT sf.fact_id, sf.fact_key, sf.fact_value, sf.fact_type
            FROM claude.session_facts sf
            JOIN claude.sessions s ON sf.session_id = s.session_id
            WHERE sf.project_name = %s
              AND sf.fact_type IN ('decision', 'reference', 'note', 'data')
              AND LENGTH(sf.fact_value) >= 50
              AND s.session_end IS NOT NULL
              AND s.session_end > NOW() - INTERVAL '7 days'
              AND NOT EXISTS (
                  SELECT 1 FROM claude.knowledge k
                  WHERE k.title = sf.fact_key AND k.source = 'consolidation'
              )
            LIMIT 5
        """, (project_name,))

        facts = cur.fetchall()
        promoted = 0
        for fact in facts:
            ktype = 'learned' if fact['fact_type'] in ('note', 'data') else fact['fact_type']
            cur.execute("""
                INSERT INTO claude.knowledge
                    (knowledge_id, title, description, knowledge_type, tier,
                     confidence_level, source, created_at, applies_to_projects)
                VALUES (gen_random_uuid(), %s, %s, %s, 'mid', 65, 'consolidation',
                        NOW(), %s)
            """, (fact['fact_key'], fact['fact_value'], ktype, [project_name]))
            promoted += 1

        if promoted > 0:
            logger.info(f"Promoted {promoted} session fact(s) to mid-tier knowledge for {project_name}")
        conn.commit()
    except Exception as e:
        logger.warning(f"Session fact consolidation failed (non-fatal): {e}")


def auto_save_session(session_id: str, project_name: str):
    """Auto-save session state to database on exit.

    This is a lightweight save - just marks session_end, preserves state,
    and demotes in_progress todos to pending (per task_lifecycle BPMN).
    Full session summary requires manual /session-end.
    """
    conn = get_db_connection()
    if not conn:
        logger.warning("No DB connection - cannot auto-save session")
        # JSONL fallback when DB is entirely unavailable (F114)
        try:
            from hook_data_fallback import log_fallback
            log_fallback("session_end", {
                "session_id": session_id,
                "project_name": project_name,
                "action": "auto_close",
                "reason": "db_unavailable",
            })
        except Exception:
            pass
        return

    try:
        cur = conn.cursor()

        # BPMN step: demote_to_pending - in_progress todos become pending
        demote_in_progress_todos(project_name, conn)

        # F130: Promote qualifying session facts to mid-tier knowledge
        consolidate_session_facts(project_name, conn)

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
        # JSONL fallback: save data for replay when DB recovers (F114)
        try:
            from hook_data_fallback import log_fallback
            log_fallback("session_end", {
                "session_id": session_id,
                "project_name": project_name,
                "action": "auto_close",
            })
        except Exception:
            pass
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
