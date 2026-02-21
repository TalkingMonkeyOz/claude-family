#!/usr/bin/env python3
"""
Task Discipline Hook - PreToolUse Hook for Claude Code

Enforces that TaskCreate is called before "action" tools (Write, Edit, Task).
Blocks tool calls when no tasks have been created, ensuring Claude plans before acting.
Also tracks unique files edited per session and issues a delegation advisory at 3+ files.

Hook Event: PreToolUse
Matchers: Write, Edit, Task, Bash (registered separately per tool)

How it works (4-way cascade - FB108 + FB109):
1. Reads task map file written by task_sync_hook.py on TaskCreate
2. Checks _session_id in map matches current session
3. Decision cascade:
   a. Tasks exist + session match -> allow (normal case)
   b. Tasks exist + no session_id -> allow (edge case)
   c. Tasks exist + session mismatch + map fresh (< 2h) -> allow with warning (continuation)
   d. No tasks + map recently modified (< 30s) -> allow (race condition)
   e. DB fallback: query build_tasks for active tasks (covers MCP create_linked_task) -> allow
   f. Otherwise -> deny

Delegation advisory (FB139):
- Tracks unique file paths edited via Write/Edit in `_files_edited` list in the task map
- At 3+ unique files, emits a one-time additionalContext advisory suggesting agent delegation
- Advisory state tracked by `_delegation_advised` boolean in the task map
- Never blocks; advisory only

Session scoping:
- task_sync_hook.py writes _session_id into the map file on every TaskCreate
- This hook compares map's _session_id with the current session_id from hook_input
- Session mismatch with fresh map (< 2h) = continuation session (FB108 fix)
- Truly stale maps (> 2h) from previous sessions are denied

Response pattern: exit code 0 + JSON with permissionDecision: "deny" or "allow"
(Exit code 2 ignores JSON - only uses stderr as plain text, so we use exit 0)

Author: Claude Family
Date: 2026-02-09
Updated: 2026-02-21 (FB139 - delegation advisory at 3+ unique files edited)
"""

import json
import os
import sys
import io
import logging
import tempfile
import time
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
# Action tools + Bash (most investigation work goes through Bash).
# Read/Grep/Glob are passive and ungated to allow initial exploration.
GATED_TOOLS = {'Write', 'Edit', 'Task', 'Bash'}


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


def save_task_map_fields(project_name: str, updates: dict):
    """Merge specific fields into the task map using Windows file locking.

    Used by the delegation tracker to persist _files_edited and _delegation_advised
    without clobbering task entries written by task_sync_hook.py. Uses the same
    locking strategy as task_sync_hook.save_task_map for safety.

    Args:
        project_name: Project name (used to resolve the map file path).
        updates: Dict of key-value pairs to merge into the existing map.
    """
    import msvcrt  # Windows file locking

    path = get_task_map_path(project_name)
    lock_path = path.with_suffix('.lock')
    try:
        with open(lock_path, 'w') as lock_file:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                current_map = {}
                if path.exists():
                    try:
                        with open(path, 'r') as f:
                            current_map = json.load(f)
                            if not isinstance(current_map, dict):
                                current_map = {}
                    except (json.JSONDecodeError, IOError):
                        current_map = {}

                current_map.update(updates)

                with open(path, 'w') as f:
                    json.dump(current_map, f)
            finally:
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    except (IOError, OSError) as e:
        # Lock acquisition failed - fall back to direct write of only the updates
        logger.warning(f"Delegation tracker: lock failed, falling back to direct merge: {e}")
        try:
            current_map = load_task_map(project_name)
            current_map.update(updates)
            with open(path, 'w') as f:
                json.dump(current_map, f)
        except IOError as e2:
            logger.error(f"Delegation tracker: failed to save task map: {e2}")


def check_and_issue_delegation_advisory(
    tool_name: str,
    tool_input: dict,
    project_name: str,
    task_map: dict,
) -> str | None:
    """Track file edits and return a delegation advisory if the 3-file threshold is crossed.

    Only tracks Write and Edit tool calls (not Bash or Task which don't directly
    edit named files). Reads _files_edited and _delegation_advised from task_map
    in memory, writes back updates via save_task_map_fields if state changes.

    Args:
        tool_name: Name of the tool being called.
        tool_input: Parsed tool_input dict from the hook payload.
        project_name: Project name for task map resolution.
        task_map: Already-loaded task map dict (avoids double read).

    Returns:
        Advisory string if this call crosses the threshold and advisory has not
        yet been issued, otherwise None.
    """
    # Only track Write and Edit - these directly modify named files
    if tool_name not in ('Write', 'Edit'):
        return None

    file_path = tool_input.get('file_path', '').strip()
    if not file_path:
        return None

    # Normalise to lowercase for deduplication (Windows paths are case-insensitive)
    normalised_path = file_path.lower().replace('\\', '/')

    already_advised = task_map.get('_delegation_advised', False)
    if already_advised:
        # Advisory already sent this session - nothing more to do
        return None

    files_edited: list = list(task_map.get('_files_edited', []))

    if normalised_path not in files_edited:
        files_edited.append(normalised_path)

    file_count = len(files_edited)

    if file_count < 3:
        # Below threshold - persist updated list, no advisory yet
        save_task_map_fields(project_name, {'_files_edited': files_edited})
        return None

    # Threshold crossed - mark advised and persist both fields atomically
    save_task_map_fields(project_name, {
        '_files_edited': files_edited,
        '_delegation_advised': True,
    })

    advisory = (
        f"DELEGATION ADVISORY: You've edited {file_count} unique file(s) this session. "
        f"Consider spawning a coder-sonnet or coder-haiku agent for the remaining work. "
        f"See Delegation Rules in CLAUDE.md."
    )
    return advisory


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


def allow_with_advisory(advisory: str):
    """Allow the tool call but surface an advisory message to Claude."""
    logger.info(f"Delegation advisory issued: {advisory[:100]}")
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        },
        "additionalContext": advisory
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


def map_recently_modified(project_name: str, max_age_seconds: int = 30) -> bool:
    """Check if the task map file was recently modified.

    Handles the race condition where multiple PostToolUse hooks fire concurrently
    and the map file is temporarily empty or mid-write. If the file was touched
    recently, it's likely being written to by concurrent hooks.
    """
    import time
    path = get_task_map_path(project_name)
    if not path.exists():
        return False
    try:
        mtime = path.stat().st_mtime
        age = time.time() - mtime
        return age < max_age_seconds
    except OSError:
        return False


def _get_project_name(cwd: str) -> str:
    """Derive project name from git root, falling back to cwd basename.

    Claude Code may pass a subdirectory as cwd (e.g., mcp-servers/bpmn-engine/
    instead of the project root). Using git root ensures we always get the
    correct project name for task map lookup.
    """
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, timeout=5,
            cwd=cwd, stdin=subprocess.DEVNULL
        )
        if result.returncode == 0 and result.stdout.strip():
            git_root = result.stdout.strip().replace('/', os.sep)
            return os.path.basename(git_root)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    # Fallback to cwd basename
    return os.path.basename(cwd.rstrip('/\\'))


def check_db_for_recent_tasks(project_name: str, max_age_hours: int = 2) -> bool:
    """Fallback: check database for recent build_tasks when task_map is empty.

    This covers the case where tasks were created via MCP create_linked_task
    (which writes to DB but not the task_map file). Only queries DB when
    the fast task_map check fails - not on every tool call.

    Returns True if active build_tasks exist for this project (created recently).
    """
    try:
        sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
        from config import POSTGRES_CONFIG as _PG_CONFIG
        conn_str = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
    except ImportError:
        return False

    try:
        import psycopg
        conn = psycopg.connect(conn_str)
    except ImportError:
        try:
            import psycopg2 as psycopg
            conn = psycopg.connect(conn_str)
        except ImportError:
            return False
    except Exception:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM claude.build_tasks bt
            JOIN claude.features f ON bt.feature_id = f.feature_id
            JOIN claude.projects p ON f.project_id = p.project_id
            WHERE p.project_name = %s
              AND bt.status IN ('todo', 'in_progress')
              AND bt.created_at > NOW() - INTERVAL '%s hours'
        """, (project_name, max_age_hours))
        row = cur.fetchone()
        count = row[0] if row else 0
        conn.close()
        if count > 0:
            logger.info(f"DB fallback: found {count} active build_tasks for {project_name}")
        return count > 0
    except Exception as e:
        logger.error(f"DB fallback check failed: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def _do_allow(tool_name: str, tool_input: dict, project_name: str, task_map: dict):
    """Issue an allow response, with a delegation advisory if the file-edit threshold is met.

    Centralises the allow path so every branch in main() uses identical advisory logic.
    Calls allow_with_advisory() when the delegation check returns a message, otherwise
    calls allow().
    """
    advisory = check_and_issue_delegation_advisory(tool_name, tool_input, project_name, task_map)
    if advisory:
        allow_with_advisory(advisory)
    else:
        allow()


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

    # Get project name from git root (not raw cwd - cwd may be a subdirectory)
    cwd = hook_input.get('cwd', os.getcwd())
    project_name = _get_project_name(cwd)

    # Get current session_id for scoping
    current_session_id = hook_input.get('session_id', '')

    tool_input = hook_input.get('tool_input', {})

    # Check if tasks have been created THIS session
    task_map = load_task_map(project_name)

    # Filter out metadata keys (prefixed with _)
    task_entries = {k: v for k, v in task_map.items() if not k.startswith('_')}
    map_session_id = task_map.get('_session_id', '')

    logger.debug(
        f"Discipline check: project={project_name}, tasks={len(task_entries)}, "
        f"map_session={map_session_id[:8] if map_session_id else 'NONE'}"
    )

    # Session scoping: tasks must be from THIS session
    if task_entries and map_session_id == current_session_id:
        logger.debug(f"Tasks exist ({len(task_entries)} tasks, session match) - allowing {tool_name}")
        _do_allow(tool_name, tool_input, project_name, task_map)
    elif task_entries and not current_session_id:
        # No session_id available (edge case) - allow if tasks exist
        logger.debug(f"Tasks exist ({len(task_entries)} tasks, no session_id) - allowing {tool_name}")
        _do_allow(tool_name, tool_input, project_name, task_map)
    elif not task_entries and map_recently_modified(project_name):
        # Race condition fallback: map is empty but was recently written to.
        # This happens when multiple PostToolUse hooks fire concurrently (e.g.,
        # batch TaskCreate) and the map is mid-write. Allow with a warning.
        logger.warning(f"Map empty but recently modified (race condition) - allowing {tool_name}")
        _do_allow(tool_name, tool_input, project_name, task_map)
    elif task_entries and map_recently_modified(project_name, max_age_seconds=7200):
        # FB108 fix: Session mismatch but map is fresh (< 2 hours).
        # This happens in continuation sessions where Claude Code assigns a new
        # session_id after context compaction. The tasks are still valid work items
        # from the same logical session, so allow with a warning.
        logger.warning(
            f"Continuation session detected: map session={map_session_id[:8]}, "
            f"current={current_session_id[:8]}, allowing {tool_name}"
        )
        _do_allow(tool_name, tool_input, project_name, task_map)
    else:
        # FB109 fix: Before denying, check DB for active build_tasks.
        # This covers tasks created via MCP create_linked_task (which writes
        # to DB but not the task_map file). Only fires on the deny path,
        # so no performance impact on the normal allow path.
        if check_db_for_recent_tasks(project_name):
            logger.warning(
                f"DB fallback: active build_tasks found for {project_name} "
                f"(tasks created via MCP, not task_map) - allowing {tool_name}"
            )
            _do_allow(tool_name, tool_input, project_name, task_map)
        elif task_entries and map_session_id != current_session_id:
            reason = (
                f"Stale tasks from a previous session (map > 2h old). "
                f"Use TaskCreate to define your work for THIS session BEFORE using {tool_name}."
            )
            deny(reason)
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
        try:
            from failure_capture import capture_failure
            capture_failure("task_discipline_hook", str(e), "scripts/task_discipline_hook.py")
        except Exception:
            pass  # Failure capture itself failed - just log and move on
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow"
            }
        }))
        sys.exit(0)
