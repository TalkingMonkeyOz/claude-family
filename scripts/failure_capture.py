#!/usr/bin/env python3
"""
Failure Capture Module - Automated Process Improvement Loop

When hook scripts fail, they call capture_failure() from their fail-open
catch blocks. This module:
1. Logs the failure to claude.feedback (type=bug, auto-filed)
2. Records which hook/system failed for BPMN coverage tracking
3. Surfaces pending failures to Claude via get_pending_failures()

This implements the "Process Failure Capture" pattern from the
bpmn-modeling skill and system-change-process rule.

Usage in hook scripts:
    except Exception as e:
        from failure_capture import capture_failure
        capture_failure("hook_name", str(e), "scripts/hook_name.py")
        # ... fail-open logic ...

Author: Claude Family
Date: 2026-02-20
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('failure_capture')

# Failure log file (JSON lines format - survives across sessions)
FAILURE_LOG = Path.home() / ".claude" / "process_failures.jsonl"


def _get_db_connection():
    """Get PostgreSQL connection (reuses pattern from task_sync_hook)."""
    try:
        sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
        from config import POSTGRES_CONFIG as _PG_CONFIG
        conn_str = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
    except ImportError:
        return None

    try:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(conn_str, row_factory=dict_row)
    except ImportError:
        try:
            import psycopg2 as psycopg
            from psycopg2.extras import RealDictCursor
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
        except ImportError:
            return None
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return None


def capture_failure(
    system_name: str,
    error_message: str,
    source_file: str = "",
    project_name: str = "claude-family",
    auto_file_feedback: bool = True,
) -> dict:
    """Capture a process failure for the self-improvement loop.

    Args:
        system_name: Name of the failing system (e.g., "task_discipline_hook")
        error_message: The error message/traceback
        source_file: Path to the failing script
        project_name: Project name for feedback filing
        auto_file_feedback: Whether to auto-file as feedback (default True)

    Returns:
        Dict with {captured, feedback_id, logged}
    """
    result = {"captured": False, "feedback_id": None, "logged": False}

    # 1. Always log to file (survives even if DB is down)
    failure_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "system": system_name,
        "error": error_message[:500],
        "source_file": source_file,
        "project": project_name,
        "filed_as_feedback": False,
    }

    try:
        FAILURE_LOG.parent.mkdir(exist_ok=True)
        with open(FAILURE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(failure_entry) + "\n")
        result["logged"] = True
    except Exception as e:
        logger.error(f"Failed to write failure log: {e}")

    # 2. Auto-file as feedback in DB
    if auto_file_feedback:
        try:
            conn = _get_db_connection()
            if conn:
                cur = conn.cursor()

                # Get project_id
                cur.execute(
                    "SELECT project_id::text FROM claude.projects WHERE project_name = %s",
                    (project_name,)
                )
                row = cur.fetchone()
                project_id = (row['project_id'] if isinstance(row, dict) else row[0]) if row else None

                if project_id:
                    # Check for duplicate: don't file the same failure twice
                    title = f"Auto: {system_name} failure"
                    cur.execute("""
                        SELECT feedback_id::text FROM claude.feedback
                        WHERE project_id = %s::uuid
                          AND title = %s
                          AND status IN ('new', 'triaged', 'in_progress')
                        LIMIT 1
                    """, (project_id, title))

                    existing = cur.fetchone()
                    if existing:
                        result["feedback_id"] = existing['feedback_id'] if isinstance(existing, dict) else existing[0]
                        logger.info(f"Failure already filed: {result['feedback_id'][:8]}")
                    else:
                        description = (
                            f"**Automated failure capture**\n\n"
                            f"**System**: {system_name}\n"
                            f"**Source**: {source_file}\n"
                            f"**Error**: {error_message[:300]}\n\n"
                            f"**Action**: Check if this system is BPMN-modeled. "
                            f"If so, update the model. If not, create one. "
                            f"Follow the system-change-process."
                        )
                        cur.execute("""
                            INSERT INTO claude.feedback
                                (feedback_id, project_id, feedback_type, title, description, priority, status, created_at)
                            VALUES (gen_random_uuid(), %s::uuid, 'bug', %s, %s, 'medium', 'new', NOW())
                            RETURNING feedback_id::text, 'FB' || short_code as code
                        """, (project_id, title, description))

                        new_row = cur.fetchone()
                        result["feedback_id"] = new_row['feedback_id'] if isinstance(new_row, dict) else new_row[0]
                        fb_code = new_row['code'] if isinstance(new_row, dict) else new_row[1]
                        logger.info(f"Auto-filed failure as {fb_code}: {system_name}")

                conn.commit()
                conn.close()
                result["captured"] = True

        except Exception as e:
            logger.error(f"Failed to auto-file feedback: {e}")
            try:
                conn.close()
            except Exception:
                pass

    return result


def get_pending_failures(project_name: str = "claude-family", max_age_hours: int = 48) -> list:
    """Get recent failures that haven't been addressed yet.

    Used by hooks (e.g., rag_query_hook) to surface pending failures to Claude.

    Returns list of {system, error, timestamp, feedback_code} dicts.
    """
    conn = _get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                'FB' || f.short_code as code,
                f.title,
                f.description,
                f.created_at,
                f.status
            FROM claude.feedback f
            JOIN claude.projects p ON f.project_id = p.project_id
            WHERE p.project_name = %s
              AND f.title LIKE 'Auto: %% failure'
              AND f.status IN ('new', 'triaged')
              AND f.created_at > NOW() - INTERVAL '%s hours'
            ORDER BY f.created_at DESC
            LIMIT 5
        """, (project_name, max_age_hours))

        rows = cur.fetchall()
        conn.close()

        return [
            {
                "code": row['code'] if isinstance(row, dict) else row[0],
                "title": row['title'] if isinstance(row, dict) else row[1],
                "status": row['status'] if isinstance(row, dict) else row[4],
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to get pending failures: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return []


def format_pending_failures(failures: list) -> str:
    """Format pending failures for injection into Claude's context."""
    if not failures:
        return ""

    lines = [f"PROCESS FAILURES ({len(failures)} pending):"]
    for f in failures:
        lines.append(f"  - {f['code']}: {f['title']} [{f['status']}]")
    lines.append("Use system-change-process to address these.")
    return "\n".join(lines)
