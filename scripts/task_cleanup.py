#!/usr/bin/env python3
"""
Task Cleanup - Delete completed task files from disk.

Claude Code stores tasks as JSON files in ~/.claude/tasks/<project>/.
Completed tasks accumulate on disk even though they're no longer needed.
This module finds and deletes them.

Integrated into:
- session_end_hook.py (cleanup on exit)
- session_startup_hook_enhanced.py (cleanup on start)
- job_runner.py (periodic cleanup every 6 hours)

Usage:
    python task_cleanup.py              # Delete completed tasks
    python task_cleanup.py --dry-run    # Show what would be deleted

Author: Claude Family
Date: 2026-03-28
"""

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("task_cleanup")


def cleanup_completed_tasks(dry_run: bool = False) -> int:
    """Find and delete completed task JSON files from disk.

    Looks for task files in ~/.claude/tasks/. If CLAUDE_CODE_TASK_LIST_ID
    is set, checks only that project directory. Otherwise scans all
    project directories under ~/.claude/tasks/.

    Only deletes files where status is exactly 'completed'.

    Args:
        dry_run: If True, log what would be deleted but don't delete.

    Returns:
        Count of deleted (or would-be-deleted) files.
    """
    tasks_root = Path.home() / ".claude" / "tasks"
    if not tasks_root.exists():
        logger.debug("No tasks directory found at %s", tasks_root)
        return 0

    # Determine which directories to scan
    list_id = os.environ.get("CLAUDE_CODE_TASK_LIST_ID", "")
    if list_id:
        scan_dirs = [tasks_root / list_id]
    else:
        # Scan all project directories
        try:
            scan_dirs = [d for d in tasks_root.iterdir() if d.is_dir()]
        except OSError as e:
            logger.warning("Cannot list tasks directory: %s", e)
            return 0

    deleted = 0
    for task_dir in scan_dirs:
        if not task_dir.exists() or not task_dir.is_dir():
            continue

        try:
            json_files = list(task_dir.glob("*.json"))
        except OSError as e:
            logger.warning("Cannot list files in %s: %s", task_dir, e)
            continue

        for task_file in json_files:
            try:
                data = json.loads(task_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Skipping unreadable file %s: %s", task_file, e)
                continue

            if not isinstance(data, dict):
                continue

            if data.get("status") == "completed":
                subject = data.get("subject", "(no subject)")
                if dry_run:
                    logger.info("Would delete: %s - %s", task_file.name, subject)
                else:
                    try:
                        task_file.unlink()
                        logger.info("Deleted: %s - %s", task_file.name, subject)
                    except OSError as e:
                        logger.warning("Failed to delete %s: %s", task_file, e)
                        continue
                deleted += 1

    action = "Would delete" if dry_run else "Deleted"
    if deleted > 0:
        logger.info("%s %d completed task file(s)", action, deleted)
    else:
        logger.debug("No completed task files found")

    return deleted


if __name__ == "__main__":
    # Configure logging for standalone usage
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    dry = "--dry-run" in sys.argv
    count = cleanup_completed_tasks(dry_run=dry)
    print(f"{'Would delete' if dry else 'Deleted'} {count} completed task file(s)")
