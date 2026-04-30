#!/usr/bin/env python3
"""
Code Collision Hook v2 — Thin CKG Daemon Client

PreToolUse hook that delegates collision detection to the CKG daemon.
If daemon is unreachable, returns {"decision": "allow"} (fail-open).

Target: <50ms total (vs 561ms in v1 which spawned full Python + DB each call).

Response Format:
    - allow: {"decision": "allow"}
    - allow with warning: {"decision": "allow", "additionalContext": "warning..."}

Author: Project HAL (F160 CKG Performance Fix)
Created: 2026-03-28
"""

import sys
import io
import os
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

# Force UTF-8 stdout for JSON output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Port resolution (must match ckg_daemon.py)
PORT_RANGE_START = 9800
PORT_RANGE_SIZE = 100
PID_DIR = Path.home() / ".claude"


def resolve_port(project_name: str) -> int:
    """Deterministic port from project name (fallback). Range: 9800-9899."""
    digest = int(hashlib.md5(project_name.encode()).hexdigest(), 16)
    return PORT_RANGE_START + (digest % PORT_RANGE_SIZE)


def read_port_from_pid_file(project_name: str) -> int | None:
    """Read the actual bound port the daemon recorded (FB220).

    Returns None if PID file missing, unreadable, or in legacy format
    without a `port=` line. Caller falls back to resolve_port().
    """
    pid_file = PID_DIR / f"ckg-daemon-{project_name}.pid"
    if not pid_file.exists():
        return None
    try:
        text = pid_file.read_text().strip()
    except OSError:
        return None
    if "=" not in text:
        return None  # legacy single-PID format
    for line in text.splitlines():
        if line.startswith("port="):
            try:
                return int(line.split("=", 1)[1].strip())
            except ValueError:
                return None
    return None


def main():
    try:
        # Read hook input
        input_data = sys.stdin.read()

        # Determine project from CWD
        project_name = os.path.basename(os.getcwd())
        # FB220: prefer PID-file's recorded port, fall back to MD5 hash.
        port = read_port_from_pid_file(project_name) or resolve_port(project_name)

        # POST to daemon — use 127.0.0.1 (not localhost) to avoid Windows DNS lag
        url = f'http://127.0.0.1:{port}/collision-check'
        req = urllib.request.Request(
            url,
            data=input_data.encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )
        resp = urllib.request.urlopen(req, timeout=2)
        result = resp.read().decode('utf-8')
        print(result)

    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError):
        # Daemon not running — fail open
        print(json.dumps({"decision": "allow"}))
    except Exception:
        # Any other error — fail open
        print(json.dumps({"decision": "allow"}))


if __name__ == '__main__':
    main()
