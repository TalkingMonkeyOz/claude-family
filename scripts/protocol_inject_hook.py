#!/usr/bin/env python3
"""Lightweight core protocol injector for UserPromptSubmit hook.

Reads core_protocol.txt + session context cache and returns as additionalContext.
NO heavy imports (no voyageai, torch, numpy, langchain). Target: <100ms.

Replaces the 2000-line rag_query_hook.py for per-prompt injection.
RAG/semantic search is handled on-demand by project-tools MCP (long-running process).
"""
import json
import os
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROTOCOL_FILE = os.path.join(SCRIPT_DIR, "core_protocol.txt")


def _read_file(path: str) -> str:
    """Read a file, return empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        hook_input = {}

    # 1. Core protocol — always inject (the critical part)
    protocol = _read_file(PROTOCOL_FILE)

    # 2. Session context cache — pre-computed at SessionStart
    project_name = os.path.basename(os.getcwd())
    cache_file = os.path.join(
        tempfile.gettempdir(),
        f"claude_session_context_{project_name}.txt",
    )
    session_context = _read_file(cache_file)

    # 3. Combine
    parts = [p for p in [protocol, session_context] if p]
    combined = "\n\n".join(parts)

    # 4. Return in Claude Code hook format
    result = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": combined,
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
