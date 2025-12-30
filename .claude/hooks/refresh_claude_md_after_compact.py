#!/usr/bin/env python3
"""
PostCompaction CLAUDE.md Refresh Hook

Fires after conversation compaction to re-inject CLAUDE.md instructions,
preventing instruction drift during long sessions.

Hook Type: SessionStart (with matcher: "compact")
Trigger: After auto or manual compaction
Output: Re-injects global and project CLAUDE.md files into context
"""

import json
import sys
import os
from pathlib import Path


def read_file_if_exists(filepath: Path) -> str | None:
    """Read file content if it exists, return None otherwise."""
    if filepath.exists() and filepath.is_file():
        try:
            return filepath.read_text(encoding='utf-8')
        except Exception as e:
            return f"<!-- Error reading {filepath}: {e} -->"
    return None


def main():
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
        source = input_data.get("source", "")

        # Only run after compaction (source will be "compact")
        if source != "compact":
            sys.exit(0)

        # Build context to re-inject
        context_parts = []

        # 1. Read global CLAUDE.md (~/.claude/CLAUDE.md)
        global_claude_md = Path.home() / ".claude" / "CLAUDE.md"
        global_content = read_file_if_exists(global_claude_md)
        if global_content:
            context_parts.append(
                f"<claudeMd type=\"global\" path=\"{global_claude_md}\">\n"
                f"{global_content}\n"
                f"</claudeMd>"
            )

        # 2. Read project CLAUDE.md (./CLAUDE.md relative to cwd)
        project_claude_md = Path.cwd() / "CLAUDE.md"
        project_content = read_file_if_exists(project_claude_md)
        if project_content:
            context_parts.append(
                f"<claudeMd type=\"project\" path=\"{project_claude_md}\">\n"
                f"{project_content}\n"
                f"</claudeMd>"
            )

        # If we have context to inject, return it
        if context_parts:
            additional_context = (
                "<system-reminder>\n"
                "Your CLAUDE.md instructions have been refreshed after context compaction. "
                "Please continue following these guidelines:\n\n"
                + "\n\n".join(context_parts) +
                "\n</system-reminder>"
            )

            result = {
                "hookSpecificOutput": {
                    "additionalContext": additional_context
                }
            }
            print(json.dumps(result))

        sys.exit(0)

    except Exception as e:
        # Log error but don't block the session
        error_msg = f"Error in refresh_claude_md_after_compact.py: {e}"
        print(json.dumps({"error": error_msg}), file=sys.stderr)
        sys.exit(0)  # Exit 0 to not block session


if __name__ == "__main__":
    main()
