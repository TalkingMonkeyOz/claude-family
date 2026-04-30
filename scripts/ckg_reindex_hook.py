#!/usr/bin/env python3
"""
CKG Re-index Hook — PostToolUse hook for incremental CKG updates.

Fires after Write/Edit to tell the CKG daemon to re-index the affected file.
Fire-and-forget: doesn't wait for re-indexing to complete.
Fails silently if daemon is down (CKG staleness is non-critical).

Author: Project HAL (F161/BT491)
Created: 2026-03-28
"""

import sys
import os
import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path

PORT_RANGE_START = 9800
PORT_RANGE_SIZE = 100
PID_DIR = Path.home() / ".claude"


def resolve_port(project_name: str) -> int:
    """Hashed fallback port (FB220 prefers PID-file port)."""
    digest = int(hashlib.md5(project_name.encode()).hexdigest(), 16)
    return PORT_RANGE_START + (digest % PORT_RANGE_SIZE)


def read_port_from_pid_file(project_name: str):
    """Read the daemon's actual bound port from its PID file. None if absent/legacy."""
    pid_file = PID_DIR / f"ckg-daemon-{project_name}.pid"
    if not pid_file.exists():
        return None
    try:
        text = pid_file.read_text().strip()
    except OSError:
        return None
    if "=" not in text:
        return None
    for line in text.splitlines():
        if line.startswith("port="):
            try:
                return int(line.split("=", 1)[1].strip())
            except ValueError:
                return None
    return None


def main():
    try:
        input_data = json.load(sys.stdin)

        # Support both event shapes:
        #   - PostToolUse: {tool_name, tool_input: {file_path}}
        #   - FileChanged (v2.1.83+): {file_path, change_type} or {path}
        event_name = input_data.get('hook_event_name', '')

        if event_name == 'FileChanged' or 'file_path' in input_data and 'tool_input' not in input_data:
            # FileChanged payload: file_path at top level
            file_path = input_data.get('file_path') or input_data.get('path', '')
        else:
            # PostToolUse payload (legacy fallback)
            tool_name = input_data.get('tool_name', '')
            if tool_name not in ('Write', 'Edit'):
                return
            tool_input = input_data.get('tool_input', {})
            file_path = tool_input.get('file_path', '')

        if not file_path:
            return

        # Skip non-source files (in-script filter; also duplicated by v2.1.85 `if` clause on registration)
        skip_extensions = {'.md', '.json', '.yml', '.yaml', '.toml', '.txt', '.csv', '.log', '.bpmn'}
        ext = os.path.splitext(file_path)[1].lower()
        if ext in skip_extensions:
            return

        project_name = os.path.basename(os.getcwd())
        # FB220: prefer PID-file port (daemon may have moved off the hash slot
        # if another project's name hashed to the same port).
        port = read_port_from_pid_file(project_name) or resolve_port(project_name)

        url = f'http://127.0.0.1:{port}/reindex-file'
        data = json.dumps({'file_path': file_path}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        # Short timeout — fire and forget
        urllib.request.urlopen(req, timeout=1)

    except Exception:
        pass  # Silent fail — re-indexing is non-critical


if __name__ == '__main__':
    main()
