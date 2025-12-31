#!/usr/bin/env python3
"""
RAG Query Hook for UserPromptSubmit

Automatically queries Voyage AI embeddings on every user prompt to inject
relevant vault knowledge into Claude's context.

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
from datetime import datetime
from pathlib import Path

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
    except:
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


def query_vault_rag(user_prompt: str, project_name: str, session_id: str = None,
                    top_k: int = 3, min_similarity: float = 0.45) -> str:
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

        # Only log if we have a session_id
        if session_id:
            try:
                cur.execute("""
                    INSERT INTO claude.rag_usage_log
                    (session_id, project_name, query_type, query_text, results_count,
                     top_similarity, docs_returned, latency_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_id,
                    project_name,
                    "user_prompt",
                    query_text,
                    len(results),
                    top_similarity,
                    docs_returned,
                    latency_ms
                ))
                conn.commit()
            except Exception as log_error:
                logger.warning(f"Failed to log RAG usage: {log_error}")

        if not results:
            logger.info(f"No RAG results for query (similarity < {min_similarity})")
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

        if not user_prompt or len(user_prompt.strip()) < 10:
            # Skip very short prompts (likely not substantive questions)
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
        session_id = os.environ.get('CLAUDE_SESSION_ID')

        logger.info(f"RAG query hook invoked for project: {project_name}")

        # Query RAG
        rag_context = query_vault_rag(
            user_prompt=user_prompt,
            project_name=project_name,
            session_id=session_id,
            top_k=3,
            min_similarity=0.45
        )

        # Build result
        result = {
            "additionalContext": rag_context if rag_context else "",
            "systemMessage": "",
            "environment": {}
        }

        # Output JSON to stdout (SILENT - no user-visible messages)
        print(json.dumps(result))

    except Exception as e:
        logger.error(f"RAG hook failed: {e}", exc_info=True)
        # On error, return empty context (don't break the flow)
        result = {
            "additionalContext": "",
            "systemMessage": "",
            "environment": {}
        }
        print(json.dumps(result))


if __name__ == "__main__":
    main()
