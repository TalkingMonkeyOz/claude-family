#!/usr/bin/env python3
"""
PostCompact Hook — fires after context compaction.

Logs the compaction event and verifies session state survived.
Informational only — cannot affect the compaction result.

Hook event: PostCompact
Matchers: manual, auto
"""

import json
import sys
import logging
from pathlib import Path

try:
    from config import setup_hook_logging
    setup_hook_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("postcompact")


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        hook_input = {}

    trigger = hook_input.get("trigger", "unknown")
    session_id = hook_input.get("session_id", "")
    compact_summary = hook_input.get("compact_summary", "")
    cwd = hook_input.get("cwd", "")
    project_name = Path(cwd).name if cwd else None

    logger.info(f"PostCompact fired: trigger={trigger}, session={session_id}, summary_chars={len(compact_summary)}")

    # Persist full summary to dedicated table (solves task #644)
    try:
        from config import get_db_connection
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            if compact_summary:
                cur.execute("""
                    INSERT INTO claude.compaction_summaries
                    (session_id, project_name, trigger, summary)
                    VALUES (%s::uuid, %s, %s, %s)
                    RETURNING summary_id
                """, (
                    session_id if session_id else None,
                    project_name,
                    trigger if trigger in ('manual', 'auto') else 'unknown',
                    compact_summary,
                ))
                row = cur.fetchone()
                summary_id = row['summary_id'] if isinstance(row, dict) else row[0]
                logger.info(f"Compaction summary persisted: {summary_id} ({len(compact_summary)} chars)")
            # Also log the event itself to audit_log (lightweight metadata only)
            cur.execute("""
                INSERT INTO claude.audit_log
                (entity_type, entity_id, entity_code, to_status, changed_by, change_source, metadata)
                VALUES ('session', %s::uuid, 'compaction', %s, %s, 'postcompact_hook', %s::jsonb)
            """, (
                session_id if session_id else None,
                trigger,
                session_id,
                json.dumps({
                    "trigger": trigger,
                    "summary_length": len(compact_summary),
                    "summary_persisted": bool(compact_summary),
                })
            ))
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to persist compaction: {e}")

    # Output nothing — informational hook
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
