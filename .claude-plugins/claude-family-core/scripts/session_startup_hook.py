#!/usr/bin/env python3
"""
Session Startup Hook Script for claude-family-core plugin.

This is called automatically via SessionStart hook.
Outputs JSON for Claude Code to consume.
"""

import json
import os
import sys
from datetime import datetime

def main():
    """Run minimal startup checks and output JSON context."""

    result = {
        "additionalContext": "",
        "systemMessage": ""
    }

    context_lines = []

    # Get current directory to determine project
    cwd = os.getcwd()
    project_name = os.path.basename(cwd)

    context_lines.append(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    context_lines.append(f"Working directory: {cwd}")
    context_lines.append(f"Detected project: {project_name}")

    # Check for CLAUDE.md
    claude_md = os.path.join(cwd, "CLAUDE.md")
    if os.path.exists(claude_md):
        context_lines.append("CLAUDE.md found - project instructions available")

    # Reminder about key commands
    context_lines.append("")
    context_lines.append("Available commands: /session-start, /session-end, /inbox-check, /feedback-check, /team-status")
    context_lines.append("")
    context_lines.append("IMPORTANT: Run /session-start for full context loading and database logging.")

    result["additionalContext"] = "\n".join(context_lines)
    result["systemMessage"] = f"Claude Family session initialized for {project_name}. Use /session-start for full context."

    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
