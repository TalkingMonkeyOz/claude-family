#!/usr/bin/env python3
"""
SubagentStart Hook - Agent Spawn Monitoring

Logs subagent spawns to claude.agent_sessions for tracking and analytics.
New in Claude Code v2.0.43+.

Hook Input:
- subagent_id: Unique ID for spawned agent
- subagent_type: Type of agent (e.g., "coder-haiku", "reviewer-sonnet")
- task_prompt: The task given to the agent
- parent_session_id: Session that spawned this agent

Author: claude-family
Date: 2026-01-08
"""

import sys
import os
import io
import json
import logging
from datetime import datetime
from typing import Optional
import uuid


def is_valid_uuid(val: str) -> bool:
    """Check if string is a valid UUID."""
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False


# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg

psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
HAS_DB = psycopg_mod is not None

# Set up logging
log_path = os.path.expanduser('~/.claude/hooks.log')
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - subagent_start - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

if not HAS_DB:
    logging.warning("No psycopg driver available - agent tracking disabled")




def log_agent_spawn(
    subagent_id: str,
    subagent_type: str,
    task_prompt: str,
    parent_session_id: Optional[str],
    workspace_dir: Optional[str]
):
    """Log agent spawn to database."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # Insert into agent_sessions with correct columns
        cur.execute("""
            INSERT INTO claude.agent_sessions
            (session_id, agent_type, task_description, workspace_dir,
             parent_session_id, spawned_at, success)
            VALUES (%s, %s, %s, %s, %s, NOW(), NULL)
            ON CONFLICT (session_id) DO UPDATE SET
                task_description = EXCLUDED.task_description,
                parent_session_id = EXCLUDED.parent_session_id
        """, (
            subagent_id,
            subagent_type,
            task_prompt[:1000] if task_prompt else 'No description',
            workspace_dir or 'unknown',
            parent_session_id if is_valid_uuid(parent_session_id) else None
        ))
        conn.commit()
        logging.info(f"Logged agent spawn: {subagent_type} ({subagent_id[:8]}...)")

    except Exception as e:
        logging.error(f"Failed to log agent spawn: {e}")
        conn.rollback()
        # JSONL fallback: save data for replay when DB recovers (F114)
        try:
            from hook_data_fallback import log_fallback
            log_fallback("subagent_start", {
                "session_id": subagent_id,
                "agent_type": subagent_type,
                "task_description": task_prompt[:1000] if task_prompt else 'No description',
                "workspace_dir": workspace_dir or 'unknown',
                "parent_session_id": parent_session_id if is_valid_uuid(parent_session_id) else None,
            })
        except Exception:
            pass
    finally:
        conn.close()


def main():
    """Main entry point for SubagentStart hook."""
    logging.info("SubagentStart hook invoked")

    # Read hook input from stdin
    try:
        raw_input = sys.stdin.read()
        hook_input = json.loads(raw_input) if raw_input.strip() else {}
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        print(json.dumps({}))
        return 0

    # Extract subagent info (per Claude Code v2.0.43+ docs)
    subagent_id = hook_input.get('subagent_id', '')
    subagent_type = hook_input.get('subagent_type', 'unknown')
    task_prompt = hook_input.get('task_prompt', '')
    parent_session_id = hook_input.get('session_id')  # Parent's session

    # Get workspace directory from hook input or cwd
    workspace_dir = hook_input.get('workspace_dir') or hook_input.get('cwd', 'unknown')

    logging.info(f"Agent spawned: type={subagent_type}, id={subagent_id[:8] if subagent_id else 'N/A'}..., parent={parent_session_id[:8] if parent_session_id else 'N/A'}...")

    # Log to database
    if subagent_id:
        log_agent_spawn(
            subagent_id=subagent_id,
            subagent_type=subagent_type,
            task_prompt=task_prompt,
            parent_session_id=parent_session_id,
            workspace_dir=workspace_dir
        )

    # Return empty response (allow spawn to proceed)
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
