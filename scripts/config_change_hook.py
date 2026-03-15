#!/usr/bin/env python3
"""
ConfigChange Hook — fires when settings or skills change.

Logs config changes to audit_log for tracking.
Does NOT block changes — audit only.

Hook event: ConfigChange
Matchers: user_settings, project_settings, local_settings, policy_settings, skills
"""

import json
import sys
import logging

try:
    from config import setup_hook_logging
    setup_hook_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("config_change")


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        hook_input = {}

    source = hook_input.get("source", "unknown")
    file_path = hook_input.get("file_path", "")
    session_id = hook_input.get("session_id", "")

    logger.info(f"ConfigChange: source={source}, file={file_path}")

    # Log to DB
    try:
        from config import get_db_connection
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO claude.audit_log
                (entity_type, entity_id, entity_code, to_status, changed_by, change_source, metadata)
                VALUES ('config', NULL, %s, 'changed', %s, 'config_change_hook', %s::jsonb)
            """, (
                source,
                session_id,
                json.dumps({
                    "source": source,
                    "file_path": file_path,
                })
            ))
            conn.commit()
            conn.close()
            logger.info(f"Config change logged: {source}")
    except Exception as e:
        logger.warning(f"Failed to log config change: {e}")

    # Allow change (exit 0)
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
