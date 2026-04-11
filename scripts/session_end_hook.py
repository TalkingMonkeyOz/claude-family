#!/usr/bin/env python3
"""
Session End Hook - Auto-Save Session State on Exit

Automatically saves the current session state (todos, focus) to the database
when Claude Code exits. This replaces the old "prompt" hook that only reminded
users to run /session-end (which they usually forgot).

What gets saved:
- Marks session_end timestamp in claude.sessions
- Preserves session_state (current_focus from latest session_summary)
- Promotes qualifying session facts to mid-tier knowledge WITH embeddings (FB266)

What does NOT happen here (left for manual /session-end):
- Detailed session summary (requires Claude's analysis)
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


def close_session_scoped_todos(project_name: str, conn):
    """Cancel session-scoped todos at session end.

    Session-scoped tasks (task_scope='session') are ephemeral by design and
    should not survive past the session that created them. Any still pending
    or in_progress are cancelled automatically here.

    Returns the number of todos cancelled.
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE claude.todos t
            SET status = 'cancelled', completed_at = NOW(), updated_at = NOW()
            FROM claude.projects p
            WHERE t.project_id = p.project_id
              AND p.project_name = %s
              AND t.task_scope = 'session'
              AND t.status IN ('pending', 'in_progress')
              AND NOT t.is_deleted
            RETURNING t.todo_id
        """, (project_name,))
        cancelled = cur.fetchall()
        cancelled_count = len(cancelled)
        if cancelled_count > 0:
            logger.info(f"Auto-cancelled {cancelled_count} session-scoped todo(s) for {project_name}")
            try:
                cur.execute("""
                    INSERT INTO claude.audit_log
                    (entity_type, entity_id, action, changed_by, change_source, metadata)
                    VALUES ('todo_session_cleanup', %s, 'session_scoped_cancel',
                            'session_end_hook', 'session_end_hook', %s::jsonb)
                """, (
                    project_name,
                    json.dumps({"count": cancelled_count,
                                "reason": "Session-scoped todos auto-cancelled at session end"})
                ))
            except Exception as audit_err:
                logger.warning(f"Failed to write audit log for session-scoped todo cleanup: {audit_err}")
        return cancelled_count
    except Exception as e:
        if 'column' in str(e).lower() and 'task_scope' in str(e).lower():
            logger.warning("task_scope column does not exist on claude.todos — skipping session-scoped cleanup")
        else:
            logger.error(f"Failed to close session-scoped todos: {e}")
        return 0


def _format_knowledge_for_embedding(title: str, knowledge_type: str,
                                    description: str, projects: list) -> str:
    """Format a knowledge entry as text for embedding.

    Matches the format used by embed_knowledge.py for consistency.
    """
    parts = []
    if title:
        parts.append(f"# {title}")
    if knowledge_type:
        parts.append(f"Type: {knowledge_type}")
    if description:
        parts.append(description)
    if projects:
        parts.append(f"\nApplies to: {', '.join(projects)}")
    return '\n\n'.join(parts)


def consolidate_session_facts(project_name: str, conn, current_session_id: str = None):
    """Promote qualifying session facts to mid-tier knowledge (F130 Cognitive Memory).

    Inserts into claude.knowledge with inline embedding generation via FastEmbed.
    If embedding fails, the fact is still promoted (just without embedding),
    matching pre-FB266 behavior.

    Args:
        project_name: Project to consolidate facts for.
        conn: Active DB connection.
        current_session_id: The session being closed. Included in the query even
            though session_end is not yet set, so current-session facts are promoted.
            Without this, the session_end IS NOT NULL filter would exclude them.
    """
    try:
        cur = conn.cursor()
        # Include facts from:
        # (a) sessions already closed (session_end IS NOT NULL) within 7 days, OR
        # (b) the current session being closed right now (session_end not yet stamped)
        cur.execute("""
            SELECT sf.fact_id, sf.fact_key, sf.fact_value, sf.fact_type
            FROM claude.session_facts sf
            JOIN claude.sessions s ON sf.session_id = s.session_id
            WHERE sf.project_name = %s
              AND sf.fact_type IN ('decision', 'reference', 'note', 'data')
              AND LENGTH(sf.fact_value) >= 50
              AND (
                  (s.session_end IS NOT NULL AND s.session_end > NOW() - INTERVAL '7 days')
                  OR (s.session_id = %s::uuid)
              )
              AND NOT EXISTS (
                  SELECT 1 FROM claude.knowledge k
                  WHERE k.title = sf.fact_key AND k.source = 'consolidation'
              )
            LIMIT 5
        """, (project_name, current_session_id))

        facts = cur.fetchall()
        promoted = 0
        embedded = 0
        for fact in facts:
            ktype = 'learned' if fact['fact_type'] in ('note', 'data') else fact['fact_type']

            # Generate embedding inline (FB266: eliminate 1-hour embedding gap)
            embedding_vec = None
            try:
                from embedding_provider import embed
                embed_text = _format_knowledge_for_embedding(
                    fact['fact_key'], ktype, fact['fact_value'], [project_name]
                )
                embedding_vec = embed(embed_text)
            except Exception as embed_err:
                logger.warning(f"Inline embedding failed for '{fact['fact_key']}' (non-fatal): {embed_err}")

            if embedding_vec is not None:
                cur.execute("""
                    INSERT INTO claude.knowledge
                        (knowledge_id, title, description, knowledge_type, tier,
                         confidence_level, source, created_at, applies_to_projects,
                         embedding)
                    VALUES (gen_random_uuid(), %s, %s, %s, 'mid', 65, 'consolidation',
                            NOW(), %s, %s::vector)
                """, (fact['fact_key'], fact['fact_value'], ktype, [project_name],
                      embedding_vec))
                embedded += 1
            else:
                cur.execute("""
                    INSERT INTO claude.knowledge
                        (knowledge_id, title, description, knowledge_type, tier,
                         confidence_level, source, created_at, applies_to_projects)
                    VALUES (gen_random_uuid(), %s, %s, %s, 'mid', 65, 'consolidation',
                            NOW(), %s)
                """, (fact['fact_key'], fact['fact_value'], ktype, [project_name]))
            promoted += 1

        if promoted > 0:
            logger.info(f"Promoted {promoted} session fact(s) to mid-tier knowledge for {project_name} ({embedded} with embeddings)")
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

        # Safety net: roll back any aborted transaction left by a prior failed
        # operation (e.g. a helper called before this point). Without this,
        # PostgreSQL raises "current transaction is aborted, commands ignored
        # until end of transaction block" for every subsequent statement.
        try:
            conn.rollback()
        except Exception:
            pass

        # BPMN step: demote_to_pending - in_progress todos become pending
        demote_in_progress_todos(project_name, conn)

        # Cancel session-scoped todos (ephemeral tasks that don't survive sessions)
        close_session_scoped_todos(project_name, conn)

        # F156: Extract lessons from active dossiers and log to session notes
        try:
            cur.execute("""
                SELECT pw.component, pw.title, LEFT(pw.content, 500) as content_preview
                FROM claude.project_workfiles pw
                JOIN claude.projects p ON pw.project_id = p.project_id
                WHERE p.project_name = %s
                  AND pw.is_active = TRUE
                  AND pw.is_pinned = TRUE
                  AND pw.updated_at > NOW() - INTERVAL '24 hours'
                ORDER BY pw.updated_at DESC
                LIMIT 5
            """, (project_name,))
            active_dossiers = cur.fetchall()
            if active_dossiers:
                dossier_summary = []
                for d in active_dossiers:
                    comp = d['component'] if isinstance(d, dict) else d[0]
                    title = d['title'] if isinstance(d, dict) else d[1]
                    dossier_summary.append(f"  - [{comp}] {title}")
                logger.info(f"F156: {len(active_dossiers)} active dossier(s) found at session end: {', '.join(d['component'] if isinstance(d, dict) else d[0] for d in active_dossiers)}")
        except Exception as e:
            logger.warning(f"Dossier extraction skipped: {e}")

        # F130: Promote qualifying session facts to mid-tier knowledge.
        # Pass session_id so current-session facts are included even though
        # session_end is not yet stamped on this session (ordering fix).
        consolidate_session_facts(project_name, conn, current_session_id=session_id)

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

        # Clean up completed task files from disk
        try:
            from task_cleanup import cleanup_completed_tasks
            cleaned = cleanup_completed_tasks()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} completed task file(s)")
        except Exception as e:
            logger.warning(f"Task cleanup failed (non-fatal): {e}")

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
