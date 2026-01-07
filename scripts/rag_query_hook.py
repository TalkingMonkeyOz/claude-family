#!/usr/bin/env python3
"""
RAG Query Hook for UserPromptSubmit

Automatically queries Voyage AI embeddings on every user prompt to inject
relevant vault knowledge into Claude's context.

SELF-LEARNING: Also captures implicit feedback signals:
- Explicit negative phrases ("that didn't work", "wrong doc")
- Query rephrasing within recent prompts
- No mention of returned docs (low confidence)

This is SILENT - no visible output to user, just additionalContext injection.

Output Format:
{
    "additionalContext": "...",  # Injected into Claude's context
    "systemMessage": "",
    "environment": {}
}
"""

import json
import os
import sys
import time
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

# Setup file-based logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('rag_query')

# Try to import required libraries
DB_AVAILABLE = False
VOYAGE_AVAILABLE = False

try:
    import psycopg
    from psycopg.rows import dict_row
    DB_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        DB_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        DB_AVAILABLE = False

try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False

# Default connection string - loaded from environment or ai-workspace config
DEFAULT_CONN_STR = None

# Try to load from ai-workspace secure config
try:
    import sys as _sys
    _sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    pass


def get_db_connection():
    """Get PostgreSQL connection from environment or default."""
    conn_str = os.environ.get('DATABASE_URL', DEFAULT_CONN_STR)

    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(conn_str, row_factory=dict_row)
        else:
            return psycopg.connect(conn_str, cursor_factory=RealDictCursor)
    except Exception:
        return None


def generate_embedding(text: str) -> list:
    """Generate embedding using Voyage AI API."""
    try:
        api_key = os.environ.get('VOYAGE_API_KEY')
        if not api_key:
            logger.warning("VOYAGE_API_KEY not set - skipping RAG")
            return None

        client = voyageai.Client(api_key=api_key)
        result = client.embed([text], model="voyage-3", input_type="query")
        return result.embeddings[0]
    except Exception as e:
        logger.warning(f"Failed to generate embedding: {e}")
        return None


def extract_query_from_prompt(user_prompt: str) -> str:
    """Extract meaningful query from user prompt.

    For now, just use the prompt as-is. Could add keyword extraction later.
    """
    # Truncate very long prompts (Voyage AI has token limits)
    max_length = 500
    if len(user_prompt) > max_length:
        return user_prompt[:max_length]
    return user_prompt


# ============================================================================
# SELF-LEARNING: Implicit Feedback Detection
# ============================================================================

NEGATIVE_PHRASES = [
    "that didn't work",
    "that's not what i",
    "wrong doc",
    "not helpful",
    "ignore that",
    "that's irrelevant",
    "that's old",
    "that's outdated",
    "that's stale",
    "wrong file",
    "not what i asked",
    "that's not it",
]

# Session context keywords - trigger session handoff context injection
SESSION_KEYWORDS = [
    "where was i",
    "where were we",
    "what was i working on",
    "what were we working on",
    "what's next",
    "whats next",
    "next steps",
    "resume",
    "continue from",
    "last session",
    "previous session",
    "pick up where",
    "what todos",
    "my todos",
    "active todos",
    "pending tasks",
    "what should i do",
    "what should we do",
    "session context",
    "session resume",
    "/session-resume",
]


def detect_explicit_negative(user_prompt: str) -> Optional[Tuple[str, float]]:
    """Detect explicit negative feedback in user prompt.

    Returns: (signal_type, confidence) or None
    """
    prompt_lower = user_prompt.lower()
    for phrase in NEGATIVE_PHRASES:
        if phrase in prompt_lower:
            logger.info(f"Detected explicit negative: '{phrase}'")
            return ('explicit_negative', 0.9)
    return None


def get_recent_rag_queries(conn, session_id: str, limit: int = 3) -> List[dict]:
    """Get recent RAG queries from this session for rephrase detection."""
    if not session_id:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT log_id, query_text, docs_returned, top_similarity, created_at
            FROM claude.rag_usage_log
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (session_id, limit))

        results = cur.fetchall()
        if isinstance(results[0] if results else {}, dict):
            return results
        else:
            # Convert tuple to dict for psycopg2
            return [
                {'log_id': r[0], 'query_text': r[1], 'docs_returned': r[2],
                 'top_similarity': r[3], 'created_at': r[4]}
                for r in results
            ]
    except Exception as e:
        logger.warning(f"Failed to get recent queries: {e}")
        return []


def calculate_query_similarity(query1: str, query2: str) -> float:
    """Simple word overlap similarity between two queries.

    Returns: similarity score 0-1
    """
    words1 = set(re.findall(r'\w+', query1.lower()))
    words2 = set(re.findall(r'\w+', query2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def detect_query_rephrase(current_query: str, recent_queries: List[dict],
                          threshold: float = 0.30) -> Optional[Tuple[str, float, dict]]:
    """Detect if current query is a rephrase of a recent query.

    Returns: (signal_type, confidence, original_query_dict) or None
    """
    for prev in recent_queries:
        prev_text = prev.get('query_text', '')
        similarity = calculate_query_similarity(current_query, prev_text)
        logger.debug(f"Rephrase check: '{current_query[:30]}' vs '{prev_text[:30]}' = {similarity:.2f}")

        if similarity >= threshold:
            logger.info(f"Detected rephrase (similarity={similarity:.2f}): '{current_query[:50]}...'")
            # Use similarity as confidence (0.3-1.0 mapped to 0.5-0.9)
            confidence = min(0.9, 0.5 + (similarity * 0.5))
            return ('rephrase', confidence, prev)

    return None


def log_implicit_feedback(conn, signal_type: str, signal_confidence: float,
                          log_id: str = None, doc_path: str = None,
                          session_id: str = None):
    """Log implicit feedback signal to rag_feedback table."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.rag_feedback
            (log_id, signal_type, signal_confidence, doc_path, session_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (log_id, signal_type, signal_confidence, doc_path, session_id))
        conn.commit()
        logger.info(f"Logged implicit feedback: {signal_type} (confidence={signal_confidence})")
    except Exception as e:
        logger.warning(f"Failed to log implicit feedback: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def update_doc_quality(conn, doc_path: str, is_hit: bool):
    """Update doc quality tracking (miss counter).

    Docs with 3+ misses get flagged for review.
    """
    try:
        cur = conn.cursor()

        if is_hit:
            cur.execute("""
                INSERT INTO claude.rag_doc_quality (doc_path, hit_count, last_hit_at)
                VALUES (%s, 1, NOW())
                ON CONFLICT (doc_path) DO UPDATE SET
                    hit_count = claude.rag_doc_quality.hit_count + 1,
                    last_hit_at = NOW(),
                    quality_score = (claude.rag_doc_quality.hit_count + 1)::float /
                                   NULLIF(claude.rag_doc_quality.hit_count + 1 + claude.rag_doc_quality.miss_count, 0),
                    updated_at = NOW()
            """, (doc_path,))
        else:
            # Miss - increment counter and check for flagging
            cur.execute("""
                INSERT INTO claude.rag_doc_quality (doc_path, miss_count, last_miss_at)
                VALUES (%s, 1, NOW())
                ON CONFLICT (doc_path) DO UPDATE SET
                    miss_count = claude.rag_doc_quality.miss_count + 1,
                    last_miss_at = NOW(),
                    quality_score = claude.rag_doc_quality.hit_count::float /
                                   NULLIF(claude.rag_doc_quality.hit_count + claude.rag_doc_quality.miss_count + 1, 0),
                    flagged_for_review = CASE
                        WHEN claude.rag_doc_quality.miss_count + 1 >= 3 THEN true
                        ELSE claude.rag_doc_quality.flagged_for_review
                    END,
                    updated_at = NOW()
                RETURNING miss_count, flagged_for_review
            """, (doc_path,))

            result = cur.fetchone()
            if result:
                miss_count = result[0] if not isinstance(result, dict) else result['miss_count']
                flagged = result[1] if not isinstance(result, dict) else result['flagged_for_review']
                if flagged:
                    logger.warning(f"Doc flagged for review after {miss_count} misses: {doc_path}")

        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to update doc quality: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def detect_session_keywords(user_prompt: str) -> bool:
    """Detect if user prompt contains session-related keywords.

    Returns True if prompt is asking about session context, todos, or resumption.
    """
    prompt_lower = user_prompt.lower()
    for keyword in SESSION_KEYWORDS:
        if keyword in prompt_lower:
            logger.info(f"Detected session keyword: '{keyword}'")
            return True
    return False


def get_session_context(project_name: str) -> Optional[str]:
    """Query database for session context: todos, focus, last session summary.

    Returns formatted context string or None if no context available.
    """
    if not DB_AVAILABLE:
        return None

    conn = get_db_connection()
    if not conn:
        return None

    try:
        import time
        start_time = time.time()
        cur = conn.cursor()
        context_lines = []

        # 1. Get project_id
        cur.execute("""
            SELECT project_id::text FROM claude.projects WHERE project_name = %s
        """, (project_name,))
        project_row = cur.fetchone()
        if not project_row:
            conn.close()
            return None
        project_id = project_row['project_id'] if isinstance(project_row, dict) else project_row[0]

        # 2. Get active todos from claude.todos (source of truth)
        cur.execute("""
            SELECT content, status, priority
            FROM claude.todos
            WHERE project_id = %s::uuid
              AND is_deleted = false
              AND status IN ('pending', 'in_progress')
            ORDER BY
                CASE status WHEN 'in_progress' THEN 1 ELSE 2 END,
                priority ASC,
                created_at ASC
            LIMIT 10
        """, (project_id,))
        todos = cur.fetchall()

        # 3. Get session_state (current_focus, next_steps)
        cur.execute("""
            SELECT current_focus, next_steps, updated_at
            FROM claude.session_state
            WHERE project_name = %s
        """, (project_name,))
        state_row = cur.fetchone()

        # 4. Get last completed session summary
        cur.execute("""
            SELECT session_summary, session_end, tasks_completed
            FROM claude.sessions
            WHERE project_name = %s AND session_end IS NOT NULL
            ORDER BY session_end DESC
            LIMIT 1
        """, (project_name,))
        last_session = cur.fetchone()

        # 5. Check for pending messages
        cur.execute("""
            SELECT COUNT(*) as count
            FROM claude.messages
            WHERE status = 'pending'
              AND (to_project = %s OR message_type = 'broadcast')
        """, (project_name,))
        msg_row = cur.fetchone()
        msg_count = msg_row['count'] if isinstance(msg_row, dict) else msg_row[0]

        conn.close()

        latency_ms = int((time.time() - start_time) * 1000)

        # Format context
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"SESSION CONTEXT (from database, {latency_ms}ms)")
        context_lines.append("=" * 70)

        # Last session info
        if last_session:
            summary = last_session['session_summary'] if isinstance(last_session, dict) else last_session[0]
            end_time = last_session['session_end'] if isinstance(last_session, dict) else last_session[1]
            if summary:
                context_lines.append("")
                context_lines.append(f"📅 LAST SESSION ({end_time.strftime('%Y-%m-%d %H:%M') if end_time else 'unknown'}):")
                context_lines.append(f"   {summary[:300]}{'...' if len(summary) > 300 else ''}")

        # Current focus
        if state_row:
            focus = state_row['current_focus'] if isinstance(state_row, dict) else state_row[0]
            next_steps = state_row['next_steps'] if isinstance(state_row, dict) else state_row[1]

            if focus:
                context_lines.append("")
                context_lines.append(f"🎯 CURRENT FOCUS: {focus}")

            if next_steps:
                context_lines.append("")
                context_lines.append("📋 NEXT STEPS (from last session):")
                if isinstance(next_steps, list):
                    for i, step in enumerate(next_steps[:5], 1):
                        step_text = step.get('content', str(step)) if isinstance(step, dict) else str(step)
                        context_lines.append(f"   {i}. {step_text}")
                elif isinstance(next_steps, str):
                    context_lines.append(f"   {next_steps}")

        # Active todos
        if todos:
            in_progress = [t for t in todos if (t['status'] if isinstance(t, dict) else t[1]) == 'in_progress']
            pending = [t for t in todos if (t['status'] if isinstance(t, dict) else t[1]) == 'pending']

            context_lines.append("")
            context_lines.append(f"✅ ACTIVE TODOS ({len(todos)} total):")

            if in_progress:
                context_lines.append("   In Progress:")
                for t in in_progress[:3]:
                    content = t['content'] if isinstance(t, dict) else t[0]
                    context_lines.append(f"      → {content}")

            if pending:
                context_lines.append("   Pending:")
                for t in pending[:5]:
                    content = t['content'] if isinstance(t, dict) else t[0]
                    priority = t['priority'] if isinstance(t, dict) else t[2]
                    p_icon = "🔴" if priority == 1 else "🟡" if priority == 2 else "🔵"
                    context_lines.append(f"      {p_icon} {content}")
                if len(pending) > 5:
                    context_lines.append(f"      ... and {len(pending) - 5} more")

        # Message count
        if msg_count > 0:
            context_lines.append("")
            context_lines.append(f"📬 INBOX: {msg_count} pending message(s) - use mcp__orchestrator__check_inbox")

        context_lines.append("")
        context_lines.append("-" * 70)
        context_lines.append("")

        logger.info(f"Session context loaded: {len(todos)} todos, focus={'yes' if state_row else 'no'}, latency={latency_ms}ms")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Failed to get session context: {e}", exc_info=True)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return None


def process_implicit_feedback(conn, user_prompt: str, session_id: str = None):
    """Process current prompt for implicit feedback signals.

    This checks for:
    1. Explicit negative phrases
    2. Query rephrasing (similar to recent query)
    """
    if not session_id:
        return

    # Check for explicit negative feedback
    negative = detect_explicit_negative(user_prompt)
    if negative:
        signal_type, confidence = negative

        # Get most recent query to associate feedback with
        recent = get_recent_rag_queries(conn, session_id, limit=1)
        if recent:
            prev = recent[0]
            log_id = prev.get('log_id')
            docs = prev.get('docs_returned', [])

            # Log feedback for each doc that was returned
            for doc_path in (docs or []):
                log_implicit_feedback(conn, signal_type, confidence,
                                      log_id=log_id, doc_path=doc_path,
                                      session_id=session_id)
                update_doc_quality(conn, doc_path, is_hit=False)
        return

    # Check for query rephrase
    recent = get_recent_rag_queries(conn, session_id, limit=3)
    if recent:
        rephrase = detect_query_rephrase(user_prompt, recent)
        if rephrase:
            signal_type, confidence, prev = rephrase
            log_id = prev.get('log_id')
            docs = prev.get('docs_returned', [])

            # Log feedback - rephrase indicates previous results weren't helpful
            for doc_path in (docs or []):
                log_implicit_feedback(conn, signal_type, confidence,
                                      log_id=log_id, doc_path=doc_path,
                                      session_id=session_id)
                update_doc_quality(conn, doc_path, is_hit=False)


def query_vault_rag(user_prompt: str, project_name: str, session_id: str = None,
                    top_k: int = 3, min_similarity: float = 0.30) -> str:
    """Query vault embeddings and return formatted context.

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        session_id: Current session ID (for logging)
        top_k: Number of results to return
        min_similarity: Minimum similarity score (0-1)

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        logger.warning("Database not available - skipping RAG")
        return None

    if not VOYAGE_AVAILABLE:
        logger.warning("Voyage AI not available - skipping RAG")
        return None

    try:
        start_time = time.time()

        # Extract query from user prompt
        query_text = extract_query_from_prompt(user_prompt)

        # Generate embedding for query
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        # Connect to database
        conn = get_db_connection()
        if not conn:
            logger.warning("Could not connect to database - skipping RAG")
            return None

        cur = conn.cursor()

        # Search for similar documents (prefer vault docs, include project docs)
        cur.execute("""
            SELECT
                doc_path,
                doc_title,
                chunk_text,
                doc_source,
                1 - (embedding <=> %s::vector) as similarity_score
            FROM claude.vault_embeddings
            WHERE 1 - (embedding <=> %s::vector) >= %s
              AND (doc_source = 'vault' OR (doc_source = 'project' AND project_name = %s))
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, project_name, query_embedding, top_k))

        results = cur.fetchall()

        # Log usage
        latency_ms = int((time.time() - start_time) * 1000)
        docs_returned = [r['doc_path'] if isinstance(r, dict) else r[0] for r in results]
        top_similarity = results[0]['similarity_score'] if results and isinstance(results[0], dict) else (results[0][4] if results else None)

        # Log RAG usage to database (try with session_id, fall back to NULL if FK fails)
        try:
            cur.execute("""
                INSERT INTO claude.rag_usage_log
                (session_id, project_name, query_type, query_text, results_count,
                 top_similarity, docs_returned, latency_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session_id,  # May be None or invalid
                project_name,
                "user_prompt",
                query_text,
                len(results),
                top_similarity,
                docs_returned,
                latency_ms
            ))
            conn.commit()
            logger.info(f"RAG usage logged to database (session_id={'NULL' if not session_id else session_id[:8]}...)")
        except Exception as log_error:
            # If foreign key constraint fails (session_id not in sessions table),
            # retry with NULL session_id to preserve usage data
            error_msg = str(log_error)
            if 'fk_session' in error_msg or 'foreign key constraint' in error_msg:
                logger.warning(f"Session ID {session_id[:8] if session_id else 'None'}... not in database, logging with NULL")
                try:
                    # CRITICAL: Rollback failed transaction before retry
                    conn.rollback()

                    cur.execute("""
                        INSERT INTO claude.rag_usage_log
                        (session_id, project_name, query_type, query_text, results_count,
                         top_similarity, docs_returned, latency_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        None,  # Use NULL instead of invalid session_id
                        project_name,
                        "user_prompt",
                        query_text,
                        len(results),
                        top_similarity,
                        docs_returned,
                        latency_ms
                    ))
                    conn.commit()
                    logger.info("RAG usage logged with NULL session_id (session mismatch)")
                except Exception as retry_error:
                    logger.error(f"Failed to log RAG usage even with NULL session_id: {retry_error}")
            else:
                logger.warning(f"Failed to log RAG usage: {log_error}")

        if not results:
            logger.info(f"No RAG results for query (similarity < {min_similarity}). Query: {query_text[:100]}")
            conn.close()
            return None

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"KNOWLEDGE VAULT CONTEXT ({len(results)} relevant docs, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                doc_title = r['doc_title']
                doc_path = r['doc_path']
                chunk_text = r['chunk_text']
                similarity = round(r['similarity_score'], 3)
            else:
                doc_title = r[1]
                doc_path = r[0]
                chunk_text = r[2]
                similarity = round(r[4], 3)

            context_lines.append(f"📄 {doc_title} ({similarity} match)")
            context_lines.append(f"   Location: {doc_path}")
            context_lines.append("")
            # Include full chunk text (not truncated)
            context_lines.append(chunk_text)
            context_lines.append("")
            context_lines.append("-" * 70)
            context_lines.append("")

        logger.info(f"RAG query success: {len(results)} docs, top={top_similarity:.3f}, latency={latency_ms}ms")
        conn.close()
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        return None


def main():
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        # Extract user prompt from hook input
        # UserPromptSubmit hook provides the prompt in the hook_input
        user_prompt = hook_input.get('prompt', '')

        if not user_prompt or len(user_prompt.strip()) < 5:
            # Skip very short prompts (likely not substantive questions)
            # Note: Lowered from 10 to 5 to catch short feedback like "wrong doc"
            result = {
                "additionalContext": "",
                "systemMessage": "",
                "environment": {}
            }
            print(json.dumps(result))
            return

        # Get project context
        cwd = os.getcwd()
        project_name = os.path.basename(cwd)
        session_id = hook_input.get('session_id') or os.environ.get('CLAUDE_SESSION_ID')

        logger.info(f"RAG query hook invoked for project: {project_name}")
        logger.info(f"Query text (first 100 chars): {user_prompt[:100]}")

        # SELF-LEARNING: Check for implicit feedback signals BEFORE querying
        # This detects phrases like "that didn't work" or query rephrasing
        if DB_AVAILABLE and session_id:
            try:
                feedback_conn = get_db_connection()
                if feedback_conn:
                    process_implicit_feedback(feedback_conn, user_prompt, session_id)
                    feedback_conn.close()
            except Exception as e:
                logger.warning(f"Implicit feedback processing failed: {e}")

        # SESSION CONTEXT: Check for session-related keywords and inject context
        # This implements the "progressive context loading" pattern from Anthropic
        session_context = None
        if detect_session_keywords(user_prompt):
            logger.info("Session keywords detected - loading session context from database")
            session_context = get_session_context(project_name)

        # Query RAG (vault knowledge)
        rag_context = query_vault_rag(
            user_prompt=user_prompt,
            project_name=project_name,
            session_id=session_id,
            top_k=3,
            min_similarity=0.30
        )

        # Combine contexts: session context first (if present), then RAG results
        combined_context_parts = []
        if session_context:
            combined_context_parts.append(session_context)
        if rag_context:
            combined_context_parts.append(rag_context)

        combined_context = "\n".join(combined_context_parts) if combined_context_parts else ""

        # Build result (CORRECT format per Claude Code docs)
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": combined_context
            }
        }

        # Output JSON to stdout (SILENT - no user-visible messages)
        print(json.dumps(result))

    except Exception as e:
        logger.error(f"RAG hook failed: {e}", exc_info=True)
        # On error, return empty context (don't break the flow)
        result = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ""
            }
        }
        print(json.dumps(result))


if __name__ == "__main__":
    main()
