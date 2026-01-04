#!/usr/bin/env python3
"""
Log rotation for Claude Code hooks.log

Rotates ~/.claude/hooks.log when it exceeds size threshold.
Called from SessionStart hook to run once per session.

Rotation strategy:
- hooks.log -> hooks.log.1 -> hooks.log.2 -> ... -> hooks.log.N (deleted)
- Keeps last N rotated files
- Size-based trigger (default 10MB)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Configuration
MAX_SIZE_MB = 10  # Rotate when file exceeds this size
MAX_ROTATED_FILES = 5  # Keep this many rotated files
LOG_DIR = Path.home() / ".claude"
LOG_FILE = LOG_DIR / "hooks.log"


def get_file_size_mb(filepath: Path) -> float:
    """Get file size in megabytes."""
    if filepath.exists():
        return filepath.stat().st_size / (1024 * 1024)
    return 0


def rotate_logs():
    """Perform log rotation if needed."""
    if not LOG_FILE.exists():
        return {"rotated": False, "reason": "log file doesn't exist"}

    size_mb = get_file_size_mb(LOG_FILE)

    if size_mb < MAX_SIZE_MB:
        return {
            "rotated": False,
            "reason": f"size {size_mb:.1f}MB < threshold {MAX_SIZE_MB}MB"
        }

    # Rotate: delete oldest, shift others, rename current
    # hooks.log.5 -> deleted
    # hooks.log.4 -> hooks.log.5
    # ...
    # hooks.log.1 -> hooks.log.2
    # hooks.log -> hooks.log.1

    # Delete oldest if exists
    oldest = LOG_DIR / f"hooks.log.{MAX_ROTATED_FILES}"
    if oldest.exists():
        oldest.unlink()

    # Shift rotated files
    for i in range(MAX_ROTATED_FILES - 1, 0, -1):
        old_path = LOG_DIR / f"hooks.log.{i}"
        new_path = LOG_DIR / f"hooks.log.{i + 1}"
        if old_path.exists():
            old_path.rename(new_path)

    # Rotate current log
    rotated_path = LOG_DIR / "hooks.log.1"
    LOG_FILE.rename(rotated_path)

    # Create fresh empty log with rotation notice
    with open(LOG_FILE, 'w') as f:
        f.write(f"# Log rotated at {datetime.now().isoformat()}\n")
        f.write(f"# Previous log: hooks.log.1 ({size_mb:.1f}MB)\n\n")

    return {
        "rotated": True,
        "previous_size_mb": size_mb,
        "rotated_to": str(rotated_path)
    }


def check_total_log_size():
    """Report total size of all log files."""
    total = 0
    files = []

    if LOG_FILE.exists():
        size = get_file_size_mb(LOG_FILE)
        total += size
        files.append(("hooks.log", size))

    for i in range(1, MAX_ROTATED_FILES + 1):
        rotated = LOG_DIR / f"hooks.log.{i}"
        if rotated.exists():
            size = get_file_size_mb(rotated)
            total += size
            files.append((f"hooks.log.{i}", size))

    return {"total_mb": total, "files": files}


def main():
    """Main entry point - rotate logs and report status."""
    result = rotate_logs()

    if result["rotated"]:
        print(f"Log rotated: {result['previous_size_mb']:.1f}MB -> {result['rotated_to']}")
    else:
        # Silent unless explicitly requested
        if "--verbose" in sys.argv:
            print(f"No rotation needed: {result['reason']}")

    if "--status" in sys.argv:
        status = check_total_log_size()
        print(f"\nTotal log size: {status['total_mb']:.1f}MB")
        for name, size in status['files']:
            print(f"  {name}: {size:.1f}MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
