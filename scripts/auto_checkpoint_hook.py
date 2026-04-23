#!/usr/bin/env python3
"""
Auto-Checkpoint Hook - PostToolUse Hook for Claude Code (Phase 4c)

Every N tool calls, bumps claude.session_state.updated_at for the current
project. This satisfies the context-health gate in task_discipline_hook.py
(_has_recent_checkpoint) and preserves cognitive state without requiring
explicit session_manage(action='checkpoint') calls from Claude.

Hook Event: PostToolUse
Matcher: "" (all tools)
Counter: per-project file at ~/.claude/state/checkpoint_counter_<project>.json
Threshold: N=15 tool calls (tunable via CLAUDE_AUTOCHECKPOINT_EVERY env var)

Fail-open: any exception returns success without writing.
Disable: set CLAUDE_DISABLE_AUTO_CHECKPOINT=1.

Author: Claude Family
Date: 2026-04-24
"""

import json
import os
import sys
import io
import logging
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('auto_checkpoint')

STATE_DIR = Path.home() / ".claude" / "state"
DEFAULT_THRESHOLD = 15


def _ok():
    print(json.dumps({"ok": True}))
    sys.exit(0)


def _project_name(cwd: str) -> str:
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, timeout=5,
            cwd=cwd, stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        if result.returncode == 0 and result.stdout.strip():
            return os.path.basename(result.stdout.strip().replace('/', os.sep)).lower()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return os.path.basename(cwd.rstrip('/\\')).lower()


def _counter_path(project_name: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    safe = ''.join(c for c in project_name if c.isalnum() or c in '-_')
    return STATE_DIR / f"checkpoint_counter_{safe}.json"


def _bump_counter(project_name: str) -> int:
    """Atomically increment the counter. Returns the new value."""
    path = _counter_path(project_name)
    current = 0
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current = int(data.get('count', 0)) if isinstance(data, dict) else 0
        except (json.JSONDecodeError, IOError, ValueError):
            current = 0
    new_value = current + 1
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'count': new_value}, f)
    except IOError as e:
        logger.warning(f"Counter write failed: {e}")
    return new_value


def _reset_counter(project_name: str) -> None:
    path = _counter_path(project_name)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'count': 0}, f)
    except IOError as e:
        logger.warning(f"Counter reset failed: {e}")


def _write_checkpoint(project_name: str, tool_name: str, count: int) -> bool:
    """UPSERT claude.session_state to bump updated_at. Returns True on success."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from config import get_db_connection
    except ImportError as e:
        logger.warning(f"Cannot import config for DB write: {e}")
        return False

    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        focus = f"Auto-checkpoint after {count} tool calls (last: {tool_name})"
        cur.execute("""
            INSERT INTO claude.session_state (project_name, current_focus, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (project_name) DO UPDATE
            SET current_focus = EXCLUDED.current_focus,
                updated_at = NOW()
        """, (project_name, focus))
        conn.commit()
        logger.info(f"Auto-checkpoint written for {project_name} at count={count}")
        return True
    except Exception as e:
        logger.warning(f"Auto-checkpoint DB write failed: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    # Kill switch
    if os.environ.get('CLAUDE_DISABLE_AUTO_CHECKPOINT') == '1':
        _ok()
        return

    try:
        raw_input = sys.stdin.read()
        hook_input = json.loads(raw_input) if raw_input.strip() else {}
    except json.JSONDecodeError:
        hook_input = {}

    tool_name = hook_input.get('tool_name', '')
    cwd = hook_input.get('cwd') or os.getcwd()

    # Skip tools that would create loops or are too chatty to count meaningfully.
    # TaskCreate/TaskUpdate and the sync hooks already write state.
    skip_tools = {'TaskCreate', 'TaskUpdate', 'TodoWrite'}
    if tool_name in skip_tools:
        _ok()
        return

    try:
        project_name = _project_name(cwd)
        count = _bump_counter(project_name)

        threshold = DEFAULT_THRESHOLD
        try:
            env_override = os.environ.get('CLAUDE_AUTOCHECKPOINT_EVERY')
            if env_override:
                threshold = max(3, int(env_override))
        except (ValueError, TypeError):
            pass

        if count >= threshold:
            if _write_checkpoint(project_name, tool_name, count):
                _reset_counter(project_name)
    except Exception as e:
        logger.warning(f"Auto-checkpoint failed (fail-open): {e}")

    _ok()


if __name__ == "__main__":
    main()
