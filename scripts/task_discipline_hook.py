#!/usr/bin/env python3
"""
Task Discipline Hook - PreToolUse Hook for Claude Code

Enforces that TaskCreate is called before "action" tools (Write, Edit, Task).
Blocks tool calls when no tasks have been created, ensuring Claude plans before acting.

Hook Event: PreToolUse
Matchers: Write, Edit, Task (registered separately per tool)

How it works:
1. Reads task map file written by task_sync_hook.py on TaskCreate
2. Checks _session_id in map matches current session (prevents stale map from old session)
3. If current-session tasks exist → allow
4. If no tasks or stale session → deny with helpful message

Session scoping:
- task_sync_hook.py writes _session_id into the map file on every TaskCreate
- This hook compares map's _session_id with the current session_id from hook_input
- Stale map files from previous sessions are treated as "no tasks"

Response pattern: exit code 0 + JSON with permissionDecision: "deny" or "allow"
(Exit code 2 ignores JSON - only uses stderr as plain text, so we use exit 0)

Author: Claude Family
Date: 2026-02-09
"""

import json
import os
import sys
import io
import logging
import tempfile
from pathlib import Path

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('task_discipline')

# Tools that REQUIRE tasks to exist before use.
# Only "action" tools that modify state - not research tools (Read, Grep, Glob, Bash).
GATED_TOOLS = {'Write', 'Edit', 'Task'}


def get_task_map_path(project_name: str) -> Path:
    """Get path to the task->todo mapping file for this project.

    Uses same path as task_sync_hook.py for consistency.
    """
    return Path(tempfile.gettempdir()) / f"claude_task_map_{project_name}.json"


def load_task_map(project_name: str) -> dict:
    """Load task_number -> todo_id mapping from temp file."""
    path = get_task_map_path(project_name)
    if path.exists():
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def allow():
    """Allow the tool call to proceed."""
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }
    print(json.dumps(response))
    sys.exit(0)


def deny(reason: str):
    """Block the tool call with a reason shown to Claude."""
    logger.warning(f"Blocking: {reason[:200]}")
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }
    print(json.dumps(response))
    sys.exit(0)


def main():
    """Main entry point."""
    try:
        raw_input = sys.stdin.read()
        hook_input = json.loads(raw_input) if raw_input.strip() else {}
    except json.JSONDecodeError:
        hook_input = {}

    tool_name = hook_input.get('tool_name', '')

    # Safety: only gate specific action tools (in case registered as catch-all)
    if tool_name not in GATED_TOOLS:
        allow()
        return

    # Get project name from cwd
    cwd = hook_input.get('cwd', os.getcwd())
    project_name = os.path.basename(cwd.rstrip('/\\'))

    # Get current session_id for scoping
    current_session_id = hook_input.get('session_id', '')

    # Check if tasks have been created THIS session
    task_map = load_task_map(project_name)

    # Filter out metadata keys (prefixed with _)
    task_entries = {k: v for k, v in task_map.items() if not k.startswith('_')}
    map_session_id = task_map.get('_session_id', '')

    # Session scoping: tasks must be from THIS session
    if task_entries and map_session_id == current_session_id:
        logger.debug(f"Tasks exist ({len(task_entries)} tasks, session match) - allowing {tool_name}")
        allow()
    elif task_entries and not current_session_id:
        # No session_id available (edge case) - allow if tasks exist
        logger.debug(f"Tasks exist ({len(task_entries)} tasks, no session_id) - allowing {tool_name}")
        allow()
    else:
        if task_entries and map_session_id != current_session_id:
            reason = (
                f"Stale tasks from a previous session. "
                f"Use TaskCreate to define your work for THIS session BEFORE using {tool_name}."
            )
        else:
            reason = (
                f"No tasks found. Use TaskCreate to define your work BEFORE using {tool_name}. "
                f"Create at least one task describing what you're about to do."
            )
        deny(reason)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Fail open on any error - never block workflow due to hook crash
        logger.error(f"Task discipline hook error: {e}")
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow"
            }
        }))
        sys.exit(0)
