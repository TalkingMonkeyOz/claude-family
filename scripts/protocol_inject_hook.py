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
    from config import DATABASE_URI as _db_uri
    DB_URI = _db_uri or ""
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
                f"  Use inbox() to read. Address urgent messages before other work."
            )
    except Exception:
        pass  # Fail silently — don't block the hook
    return ""


def _decompose_prompt(user_prompt: str) -> str:
    """Detect multi-item prompts and surface the structure BEFORE Claude reads.

    Structural scaffolding for the DECOMPOSE protocol rule — Claude sees a
    pre-parsed list of items at the top of the context, making it hard to
    latch onto the first request and forget the rest.

    Heuristics (kept simple and fail-open):
    - Questions: segments ending with '?'
    - Directives: segments after conjunctions ('and', 'also', 'plus', 'then'),
      or sentence starts with imperative verbs (list below).
    - Secondary-ask bridges: 'don't forget', 'and also', 'can you also',
      'while you're at it', 'btw', 'by the way', 'another thing'.

    Emits a hint only if 2+ distinct items are detected. Otherwise silent.
    Returns empty string on any exception.
    """
    if not user_prompt or len(user_prompt.strip()) < 20:
        return ""
    if user_prompt.strip().startswith('/'):
        return ""
    # Skip if looks like a code paste (many newlines, no natural language)
    if user_prompt.count('\n') > 30 and user_prompt.count(' ') < 50:
        return ""

    try:
        import re

        text = user_prompt.strip()
        text_lower = text.lower()
        items: list[tuple[int, str]] = []  # (position, excerpt)

        imperatives = {
            'add', 'also', 'and', 'audit', 'build', 'can', 'change', 'check',
            'commit', 'could', 'create', 'delete', 'deploy', 'describe',
            'explain', 'find', 'fix', 'generate', 'implement', 'install',
            'investigate', 'list', 'make', 'please', 'push', 'refactor',
            'remove', 'rename', 'review', 'run', 'search', 'ship', 'show',
            'summarize', 'test', 'update', 'verify', 'write', 'would',
            "let's",
        }

        # 1. Split on sentence terminators (., ?, !) while keeping the terminator
        sentence_parts = re.split(r'(?<=[\.\?\!])\s+', text)
        for part in sentence_parts:
            p = part.strip()
            if not p or len(p) < 8:
                continue
            # Question?
            if p.endswith('?'):
                items.append((text.find(p), p[:120]))
                continue
            # Imperative sentence
            first_word = p.split(None, 1)[0].lower().rstrip(',:;')
            if first_word in imperatives:
                items.append((text.find(p), p[:120]))

        # 2. Explicit "also" bridges — catch piggyback asks inside a sentence
        bridge_patterns = [
            r"(?i)(?:and\s+also|also(?:,|\s+can\s+you|\s+update|\s+add|\s+run|\s+fix)|"
            r"don'?t\s+forget|btw|by\s+the\s+way|another\s+thing|"
            r"oh\s+and|plus\s+can\s+you|while\s+you'?re\s+at\s+it|one\s+more\s+thing)"
        ]
        for pat in bridge_patterns:
            for m in re.finditer(pat, text):
                start = m.start()
                snippet = text[start:start + 140].strip()
                items.append((start, snippet[:120]))

        # Dedupe — collapse items that start inside the span of an earlier item.
        # If a bridge match is within the first item's text, drop the dupe.
        items.sort(key=lambda x: x[0])
        deduped: list[str] = []
        covered_until = -1
        for pos, excerpt in items:
            if pos < covered_until:
                continue
            deduped.append(excerpt)
            covered_until = pos + len(excerpt)

        if len(deduped) < 2:
            return ""

        lines = [f"PROMPT STRUCTURE (auto-decomposed — {len(deduped)} items detected):"]
        for i, excerpt in enumerate(deduped[:8], 1):
            # Collapse internal whitespace
            clean = re.sub(r'\s+', ' ', excerpt).strip()
            lines.append(f"  {i}. {clean}")
        if len(deduped) > 8:
            lines.append(f"  ... +{len(deduped) - 8} more")
        lines.append(
            "  ACTION: Create a task for each item above BEFORE starting work. "
            "Don't latch onto the first item and forget the rest."
        )
        return "\n".join(lines)
    except Exception:
        return ""  # Fail-open — never block the hook


def _query_knowledge(user_prompt: str, project_name: str) -> str:
    """Search knowledge table for gotchas, patterns, and facts relevant to the prompt.

    Uses keyword matching on title/description (fast, pure SQL, <20ms).
    Prioritizes gotchas and patterns as they prevent mistakes.
    Returns formatted context string or empty string.
    """
    if not DB_URI or not user_prompt or len(user_prompt.strip()) < 15:
        return ""
    if user_prompt.strip().startswith('/'):
        return ""
    try:
        import psycopg2
        import re
        # Extract meaningful words (3+ chars, skip common words)
        stop_words = {
            'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are', 'was',
            'has', 'have', 'had', 'not', 'but', 'can', 'will', 'should', 'would',
            'use', 'using', 'create', 'make', 'add', 'get', 'set', 'run', 'test',
            'please', 'want', 'need', 'let', 'know', 'how', 'what', 'when', 'where',
            'why', 'which', 'does', 'been', 'being', 'also', 'just', 'now', 'new',
        }
        words = [w for w in re.findall(r'[a-zA-Z]{3,}', user_prompt.lower())
                 if w not in stop_words]
        if not words:
            return ""

        # Build OR condition for keyword matching on title + description
        # Use up to 6 most distinctive words
        keywords = words[:6]
        conditions = []
        params = []
        for kw in keywords:
            conditions.append("(LOWER(title) LIKE %s OR LOWER(description) LIKE %s)")
            pattern = f"%{kw}%"
            params.extend([pattern, pattern])

        if not conditions:
            return ""

        where_keywords = " OR ".join(conditions)

        conn = psycopg2.connect(DB_URI, connect_timeout=2)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT title, description, knowledge_type, confidence_level,
                   COALESCE(tier, 'mid') as tier
            FROM claude.knowledge
            WHERE COALESCE(tier, 'mid') != 'archived'
              AND (
                  applies_to_projects IS NULL
                  OR cardinality(applies_to_projects) = 0
                  OR %s = ANY(applies_to_projects)
              )
              AND ({where_keywords})
            ORDER BY
                CASE knowledge_type
                    WHEN 'gotcha' THEN 1
                    WHEN 'pattern' THEN 2
                    WHEN 'decision' THEN 3
                    WHEN 'fact' THEN 4
                    ELSE 5
                END,
                confidence_level DESC
            LIMIT 5
        """, [project_name] + params)

        results = cur.fetchall()
        cur.close()
        conn.close()

        if not results:
            return ""

        # B0 context-bloat trim 2026-04-24: title-only index, preview dropped.
        # Claude loads full content via recall_memories(query) on demand.
        lines = ["RELEVANT KNOWLEDGE (load via recall_memories):"]
        for title, desc, ktype, confidence, tier in results:
            lines.append(f"  [{ktype}] {title}")

        return "\n".join(lines)
    except Exception:
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

    # 4. Knowledge + domain concept queries — run in parallel with timeout
    user_prompt = hook_input.get('prompt', '')
    dossier_context = ""
    knowledge_context = ""
    decomposition_hint = ""
    if user_prompt:
        with ThreadPoolExecutor(max_workers=2) as executor:
            dossier_future = executor.submit(_query_domain_concepts, user_prompt, project_name)
            knowledge_future = executor.submit(_query_knowledge, user_prompt, project_name)
            try:
                dossier_context = dossier_future.result(timeout=5.0)
            except (FuturesTimeout, Exception):
                dossier_context = ""
            try:
                knowledge_context = knowledge_future.result(timeout=5.0)
            except (FuturesTimeout, Exception):
                knowledge_context = ""
        # Decomposer is pure-Python and very fast — run in main thread, fail-open.
        # Disable via env var if it's ever noisy: CLAUDE_DISABLE_DECOMPOSER=1.
        if os.environ.get("CLAUDE_DISABLE_DECOMPOSER") != "1":
            decomposition_hint = _decompose_prompt(user_prompt)

    # 5. Combine — decomposition hint goes near the top (after protocol) so it's
    # the first thing Claude sees about the incoming prompt's shape.
    parts = [p for p in [
        protocol,
        decomposition_hint,
        session_context,
        message_alert,
        knowledge_context,
        dossier_context,
    ] if p]
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
