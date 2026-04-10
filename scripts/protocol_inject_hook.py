#!/usr/bin/env python3
"""Lightweight core protocol injector for UserPromptSubmit hook.

Reads core_protocol.txt + session context cache + pending messages and returns as additionalContext.
Also runs domain_concept dossier search (F189) in a background thread — if a prompt
matches a domain_concept entity, the full dossier (overview, gotchas, recipes, auth)
is auto-injected. Other RAG sources are handled on-demand by project-tools MCP.
"""
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

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


def _query_domain_concepts(user_prompt: str, project_name: str) -> str:
    """Search entity catalog for domain_concept dossiers matching the prompt.

    Strategy: BM25 keyword search first (<10ms, pure SQL), then embedding
    fallback only if BM25 finds nothing. This avoids Voyage AI cold-start
    latency (3-8s) that was killing hook performance.
    Returns formatted dossier string or empty string.
    """
    if not user_prompt or len(user_prompt.strip()) < 10:
        return ""
    # Skip slash commands
    if user_prompt.strip().startswith('/'):
        return ""
    try:
        # Fast path: BM25 keyword matching (<10ms, no external API)
        from rag_queries import query_entity_catalog_bm25
        result = query_entity_catalog_bm25(user_prompt, project_name, top_k=2,
                                            domain_concepts_only=True)
        if result:
            return result

        # Slow path: embedding similarity (only if BM25 missed)
        # Skip if prompt is very short (unlikely to benefit from semantic search)
        if len(user_prompt.strip()) < 30:
            return ""
        from rag_queries import query_entity_catalog
        result = query_entity_catalog(user_prompt, project_name, top_k=2, min_similarity=0.35)
        return result or ""
    except Exception:
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

    # 3. Pending messages — lightweight DB check
    message_alert = _check_pending_messages(project_name)

    # 4. Domain concept dossier search (F189) — run in thread with timeout
    user_prompt = hook_input.get('prompt', '')
    dossier_context = ""
    if user_prompt:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_query_domain_concepts, user_prompt, project_name)
            try:
                dossier_context = future.result(timeout=5.0)
            except (FuturesTimeout, Exception):
                dossier_context = ""  # Skip if too slow, don't block

    # 5. Combine
    parts = [p for p in [protocol, session_context, message_alert, dossier_context] if p]
    combined = "\n\n".join(parts)

    # 6. Return in Claude Code hook format
    result = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": combined,
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
