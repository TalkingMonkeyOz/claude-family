#!/usr/bin/env python3
"""Lightweight core protocol injector for UserPromptSubmit hook.

Reads core_protocol.txt + session context cache + pending messages and returns as additionalContext.
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

# Load DB connection from config module (shared with other hooks)
sys.path.insert(0, SCRIPT_DIR)
try:
    from config import get_connection_string
    DB_URI = get_connection_string()
except Exception:
    DB_URI = os.environ.get("DATABASE_URI", "")


def _read_file(path: str) -> str:
    """Read a file, return empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return ""


def _check_pending_messages(project_name: str) -> str:
    """Check for unread messages addressed to this project. Returns alert string or empty."""
    if not DB_URI:
        return ""
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URI, connect_timeout=2)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*),
                   string_agg(DISTINCT from_project, ', ' ORDER BY from_project),
                   MAX(priority)
            FROM claude.messages
            WHERE (to_project = %s OR message_type = 'broadcast')
              AND status = 'pending'
              AND created_at > NOW() - INTERVAL '7 days'
        """, (project_name,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0] and row[0] > 0:
            count, senders, priority = row
            senders = senders or "unknown"
            return (
                f"PENDING MESSAGES:\n"
                f"  {count} unread message(s) from: {senders}. Priority: {priority}.\n"
                f"  Use check_inbox() to read. Address urgent messages before other work."
            )
    except Exception:
        pass  # Fail silently — don't block the hook
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

    # 3. Pending messages — lightweight DB check (belt-and-suspenders with channels)
    message_alert = _check_pending_messages(project_name)

    # 4. Combine
    parts = [p for p in [protocol, session_context, message_alert] if p]
    combined = "\n\n".join(parts)

    # 5. Return in Claude Code hook format
    result = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": combined,
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
