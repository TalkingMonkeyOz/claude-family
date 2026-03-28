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

# Force UTF-8 stdout for JSON output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Port resolution (must match ckg_daemon.py)
PORT_RANGE_START = 9800
PORT_RANGE_SIZE = 100


def resolve_port(project_name: str) -> int:
    """Deterministic port from project name. Range: 9800-9899."""
    digest = int(hashlib.md5(project_name.encode()).hexdigest(), 16)
    return PORT_RANGE_START + (digest % PORT_RANGE_SIZE)


def main():
    try:
        # Read hook input
        input_data = sys.stdin.read()

        # Determine project from CWD
        project_name = os.path.basename(os.getcwd())
        port = resolve_port(project_name)

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
