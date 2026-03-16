#!/usr/bin/env python3
"""
Context Monitor StatusLine Script

Reads context_window metrics from Claude Code's StatusLine stdin JSON,
computes urgency level, writes state to context_health.json, and
outputs a compact status line display.

StatusLine receives JSON on stdin with:
  context_window.remaining_percentage
  context_window.used_percentage
on each render cycle.

Output: Single line displayed in terminal status bar (e.g., "CTX:45%")
Side effect: Writes ~/.claude/state/context_health.json for other hooks

Author: Claude Family
Date: 2026-03-05
Updated: 2026-03-05 (Rewritten from bash to Python - jq not available on Windows)
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception:
        print("CTX:?")
        return

    ctx = data.get("context_window") or {}
    remaining = ctx.get("remaining_percentage")
    used = ctx.get("used_percentage")

    # Extract project name from workspace info
    workspace = data.get("workspace") or {}
    project_dir = workspace.get("project_dir") or workspace.get("current_dir") or ""
    project_name = Path(project_dir).name if project_dir else ""

    if remaining is None:
        print(f"[{project_name}] CTX:?" if project_name else "CTX:?")
        return

    # Compute urgency level
    if remaining > 30:
        level = "green"
    elif remaining > 20:
        level = "yellow"
    elif remaining > 10:
        level = "orange"
    else:
        level = "red"

    # Write state file for RAG hook and task discipline hook
    state_dir = Path.home() / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "context_health.json"
    try:
        state_file.write_text(json.dumps({
            "remaining_pct": remaining,
            "used_pct": used,
            "level": level,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }))
    except Exception:
        pass  # Don't fail the status line if state write fails

    # Output status line display
    suffix = {"red": "!!", "orange": "!", "yellow": "~"}.get(level, "")
    used_display = used if used is not None else "?"
    prefix = f"[{project_name}] " if project_name else ""
    print(f"{prefix}CTX:{used_display}%{suffix}")


if __name__ == "__main__":
    main()
