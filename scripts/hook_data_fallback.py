#!/usr/bin/env python3
"""
Hook Data Fallback - JSONL Write-Ahead Log for DB Outages

When hooks can't reach the database, they lose data silently (fail-open).
This module provides a JSONL write-ahead log so data can be replayed when
DB recovers.

Each hook type gets its own JSONL file in ~/.claude/hook_fallback/:
  - todo_sync_fallback.jsonl
  - task_sync_fallback.jsonl
  - mcp_usage_fallback.jsonl
  - session_end_fallback.jsonl
  - subagent_start_fallback.jsonl

Usage in hook scripts:
    from hook_data_fallback import log_fallback, replay_fallback

    # When DB is down:
    log_fallback("mcp_usage", {"tool_name": "mcp__postgres__execute_sql", ...})

    # When DB is back (e.g., on next SessionStart):
    replayed = replay_fallback("mcp_usage", replay_fn)

Feature: F114 (Hook Resilience - JSONL Fallback)
Author: Claude Family
Date: 2026-02-21
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger('hook_data_fallback')

FALLBACK_DIR = Path.home() / ".claude" / "hook_fallback"


def _ensure_dir():
    """Create fallback directory if it doesn't exist."""
    FALLBACK_DIR.mkdir(parents=True, exist_ok=True)


def _fallback_path(hook_name: str) -> Path:
    """Get JSONL path for a specific hook."""
    return FALLBACK_DIR / f"{hook_name}_fallback.jsonl"


def log_fallback(hook_name: str, data: dict) -> bool:
    """Write a data record to the hook's JSONL fallback file.

    Args:
        hook_name: Hook identifier (e.g., "mcp_usage", "todo_sync")
        data: The data that would have been written to DB

    Returns:
        True if written successfully, False otherwise
    """
    try:
        _ensure_dir()
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "hook": hook_name,
            "data": data,
            "replayed": False,
        }
        path = _fallback_path(hook_name)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return True
    except Exception as e:
        logger.error(f"Failed to write fallback for {hook_name}: {e}")
        return False


def get_pending_count(hook_name: str) -> int:
    """Count unreplayed entries for a hook."""
    path = _fallback_path(hook_name)
    if not path.exists():
        return 0
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if not entry.get("replayed", False):
                        count += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return count


def replay_fallback(
    hook_name: str,
    replay_fn: Callable[[dict], bool],
    max_entries: int = 100
) -> int:
    """Replay pending fallback entries through a provided function.

    Args:
        hook_name: Hook identifier
        replay_fn: Function that takes a data dict and returns True on success
        max_entries: Maximum entries to replay in one call (default 100)

    Returns:
        Number of successfully replayed entries
    """
    path = _fallback_path(hook_name)
    if not path.exists():
        return 0

    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"Failed to read fallback file for {hook_name}: {e}")
        return 0

    replayed_count = 0
    for entry in entries:
        if entry.get("replayed", False):
            continue
        if replayed_count >= max_entries:
            break

        try:
            if replay_fn(entry["data"]):
                entry["replayed"] = True
                replayed_count += 1
        except Exception as e:
            logger.warning(f"Replay failed for {hook_name} entry: {e}")
            break  # Stop on first failure to avoid cascading errors

    # Rewrite file with updated replay status
    if replayed_count > 0:
        try:
            with open(path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to update fallback file for {hook_name}: {e}")

    # Clean up fully-replayed files
    if all(e.get("replayed", False) for e in entries):
        try:
            path.unlink()
            logger.info(f"Cleaned up fully-replayed fallback: {hook_name}")
        except Exception:
            pass

    return replayed_count


def get_all_pending() -> dict:
    """Get pending counts for all hooks with fallback data.

    Returns:
        Dict of {hook_name: pending_count}
    """
    result = {}
    if not FALLBACK_DIR.exists():
        return result

    for path in FALLBACK_DIR.glob("*_fallback.jsonl"):
        hook_name = path.stem.replace("_fallback", "")
        count = get_pending_count(hook_name)
        if count > 0:
            result[hook_name] = count

    return result
