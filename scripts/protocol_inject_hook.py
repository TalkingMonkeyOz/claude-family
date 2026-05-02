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
        # FB338: select summary column too — prefer it when populated.
        cur.execute(f"""
            SELECT title, summary, description, knowledge_type, confidence_level,
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

        # 2026-04-26: FB338 — prefer summary (purpose-built ≤200 char) when populated;
        # fall back to LEFT(description, 250). Plus FB339 widening:
        #   - Top-3 always get body — covers most relevant hits
        #   - Anything ranked 4+ that is type 'decision' OR confidence >= 85 ALSO
        #     gets body — pulls high-signal architectural memories out of the tail
        #   - Pure title + recall hint for the residual long tail
        lines = ["RELEVANT KNOWLEDGE (top-3 + high-confidence/decisions get body; rest: recall_memories(\"...\") for full):"]
        for i, (title, summary, desc, ktype, confidence, tier) in enumerate(results):
            body_source = summary if summary else desc
            give_body = bool(body_source) and (
                i < 3
                or ktype == 'decision'
                or (confidence is not None and confidence >= 85)
            )
            if give_body:
                if summary:
                    preview = summary.replace('\n', ' ').strip()
                else:
                    preview = desc[:250].replace('\n', ' ').strip()
                    if len(desc) > 250:
                        preview += "…"
                lines.append(f"  [{ktype}|c{confidence}] {title}: {preview}")
            else:
                lines.append(f"  [{ktype}] {title} …")

        return "\n".join(lines)
    except Exception:
        return ""


def _query_recent_changes(project_name: str) -> str:
    """Surface decisions/patterns/learnings/gotchas remembered in the last 7 days.

    FB342 — change-log injection. Closes the loop with change_capture_process:
    every system change gets remember()'d before commit (Rule 7), this surfaces
    those memories back so Claude sees "what changed lately" without manually
    calling recall_memories(). Pure SQL (~20ms), no Voyage AI.

    Disabled via CLAUDE_DISABLE_CHANGE_LOG=1.
    """
    if os.environ.get("CLAUDE_DISABLE_CHANGE_LOG") == "1":
        return ""
    if not DB_URI:
        return ""
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URI, connect_timeout=2)
        cur = conn.cursor()
        # Type-priority then confidence then recency. 6 rows, ~300 token budget.
        # Filter by applies_to_projects so global memories also surface.
        cur.execute("""
            SELECT title,
                   COALESCE(summary, LEFT(description, 180)) AS preview,
                   knowledge_type,
                   confidence_level,
                   created_at::date AS dt
            FROM claude.knowledge
            WHERE status = 'active'
              AND knowledge_type IN ('decision','pattern','gotcha','learned')
              AND created_at > NOW() - INTERVAL '7 days'
              AND (
                  applies_to_projects IS NULL
                  OR cardinality(applies_to_projects) = 0
                  OR %s = ANY(applies_to_projects)
              )
            ORDER BY
                CASE knowledge_type
                    WHEN 'decision' THEN 1
                    WHEN 'learned'  THEN 2
                    WHEN 'pattern'  THEN 3
                    WHEN 'gotcha'   THEN 4
                    ELSE 5
                END,
                confidence_level DESC NULLS LAST,
                created_at DESC
            LIMIT 6
        """, (project_name,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return ""

        lines = ["RECENT CHANGES (last 7 days — decisions/patterns/learnings/gotchas remembered):"]
        for title, preview, ktype, confidence, dt in rows:
            preview = (preview or "").replace('\n', ' ').strip()
            if len(preview) > 160:
                preview = preview[:160] + "…"
            tag = f"{ktype}|c{confidence}" if confidence else ktype
            lines.append(f"  [{dt}|{tag}] {title}: {preview}")
        lines.append("  Use recall_memories(\"...\") to load any of these in full.")
        return "\n".join(lines)
    except Exception:
        return ""


def _build_queue_digest() -> str:
    """Build a one-line queue digest (Tier 3 surfacing). Returns None if all clean.

    Queries task_queue and job_templates for live metrics. Silent if no issues.
    Returns: "Job queue: N dead_letter unreviewed (oldest: D days), M template(s) paused, R runs/24h"
    or empty string if all clean.
    """
    if not DB_URI:
        return ""
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URI, connect_timeout=2)
        cur = conn.cursor()
        # Single round-trip: dead_letter metrics + paused templates + 24h run count.
        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM claude.task_queue
               WHERE status='dead_letter' AND resolution_status IS NULL) AS dead_letter_unresolved,
              (SELECT EXTRACT(EPOCH FROM (now() - MIN(completed_at)))/86400
               FROM claude.task_queue
               WHERE status='dead_letter' AND resolution_status IS NULL
               AND completed_at IS NOT NULL) AS oldest_dead_letter_days,
              (SELECT COUNT(*) FROM claude.job_templates
               WHERE is_paused=true) AS paused_templates,
              (SELECT COUNT(*) FROM claude.job_run_history
               WHERE started_at > now() - interval '24 hours') AS runs_24h
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            dead_unresolved, oldest_days, paused_count, runs_24h = row
            # Silent if all clean
            if not dead_unresolved and not paused_count:
                return ""
            # Build non-empty parts
            parts = []
            if dead_unresolved:
                oldest_str = f"oldest: {int(oldest_days)} days" if oldest_days else "recently"
                parts.append(f"{dead_unresolved} dead_letter unreviewed ({oldest_str})")
            if paused_count:
                parts.append(f"{paused_count} template(s) paused")
            if runs_24h:
                parts.append(f"{runs_24h} runs/24h")
            return f"Job queue: {', '.join(parts)}"
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

    # 4. Queue digest (Tier 3 surfacing) — lightweight per-session check
    queue_digest = _build_queue_digest()

    # 5. Knowledge + domain concept + recent-changes queries — parallel w/ timeout
    user_prompt = hook_input.get('prompt', '')
    dossier_context = ""
    knowledge_context = ""
    recent_changes_context = ""
    decomposition_hint = ""
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Recent changes runs even on empty prompts (it's project-wide, not query-specific)
        recent_changes_future = executor.submit(_query_recent_changes, project_name)
        if user_prompt:
            dossier_future = executor.submit(_query_domain_concepts, user_prompt, project_name)
            knowledge_future = executor.submit(_query_knowledge, user_prompt, project_name)
        else:
            dossier_future = None
            knowledge_future = None
        try:
            recent_changes_context = recent_changes_future.result(timeout=5.0)
        except (FuturesTimeout, Exception):
            recent_changes_context = ""
        if dossier_future:
            try:
                dossier_context = dossier_future.result(timeout=5.0)
            except (FuturesTimeout, Exception):
                dossier_context = ""
        if knowledge_future:
            try:
                knowledge_context = knowledge_future.result(timeout=5.0)
            except (FuturesTimeout, Exception):
                knowledge_context = ""
    # Decomposer is pure-Python and very fast — run in main thread, fail-open.
    # Disable via env var if it's ever noisy: CLAUDE_DISABLE_DECOMPOSER=1.
    if user_prompt and os.environ.get("CLAUDE_DISABLE_DECOMPOSER") != "1":
        decomposition_hint = _decompose_prompt(user_prompt)

    # 6. Combine — decomposition hint goes near the top (after protocol) so it's
    # the first thing Claude sees about the incoming prompt's shape.
    # Queue digest follows message_alert for time-sensitive operational concerns.
    # Recent changes lives between knowledge_context and dossier_context — same
    # tier as RELEVANT KNOWLEDGE, just time-windowed instead of keyword-matched.
    parts = [p for p in [
        protocol,
        decomposition_hint,
        session_context,
        message_alert,
        queue_digest,
        knowledge_context,
        recent_changes_context,
        dossier_context,
    ] if p]
    combined = "\n\n".join(parts)

    # 7. Return in Claude Code hook format
    result = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": combined,
        }
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
