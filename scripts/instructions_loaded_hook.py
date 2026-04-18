#!/usr/bin/env python3
"""
InstructionsLoaded Hook — fires when CLAUDE.md or .claude/rules/*.md is loaded.

New in Claude Code v2.1.69. Purely observational — logs each rule/instructions
load to claude.rule_loads for audit/effectiveness queries. Never blocks.

Payload (stdin JSON):
  session_id, transcript_path, cwd, hook_event_name, file_path,
  memory_type, load_reason

Hook event: InstructionsLoaded (empty matcher — fires for all loads)

BT676 / F206.
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

logger = logging.getLogger("instructions-loaded")


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        payload = {}

    file_path = payload.get("file_path", "")
    memory_type = payload.get("memory_type", "")
    load_reason = payload.get("load_reason", "")
    session_id = payload.get("session_id", "")
    cwd = payload.get("cwd", "")
    project_name = Path(cwd).name if cwd else None

    logger.info(
        f"InstructionsLoaded: file={file_path} type={memory_type} "
        f"reason={load_reason} session={session_id[:8] if session_id else ''}"
    )

    # Persist to DB
    try:
        from config import get_db_connection
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO claude.rule_loads
                (session_id, project_name, file_path, memory_type, load_reason)
                VALUES (%s::uuid, %s, %s, %s, %s)
                """,
                (
                    session_id if session_id else None,
                    project_name,
                    file_path,
                    memory_type,
                    load_reason,
                ),
            )
            conn.commit()
            conn.close()
    except Exception as e:
        logger.warning(f"Failed to persist rule_load: {e}")

    # Informational hook — no output shape required
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
