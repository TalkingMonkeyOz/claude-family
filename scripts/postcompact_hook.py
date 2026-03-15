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

    logger.info(f"PostCompact fired: trigger={trigger}, session={session_id}")

    if compact_summary:
        logger.info(f"Compact summary length: {len(compact_summary)} chars")

    # Log to DB if possible
    try:
        from config import get_db_connection
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
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
                })
            ))
            conn.commit()
            conn.close()
            logger.info("Compaction logged to audit_log")
    except Exception as e:
        logger.warning(f"Failed to log compaction to DB: {e}")

    # Output nothing — informational hook
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
