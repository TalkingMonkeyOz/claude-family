"""rag_feedback.py — Self-learning via implicit feedback detection and logging.

Extracted from rag_query_hook.py. Handles implicit feedback signals (explicit
negatives, query rephrases) and doc quality tracking.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import re
from typing import List, Optional, Tuple

from config import get_db_connection, detect_psycopg
from rag_utils import detect_explicit_negative

DB_AVAILABLE = detect_psycopg()

logger = logging.getLogger('rag_query.feedback')


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
                # Only warn on the exact transition to flagged (miss_count == 3), not on every subsequent miss
                if flagged and miss_count == 3:
                    logger.warning(f"Doc flagged for review after {miss_count} misses: {doc_path}")

        conn.commit()
    except Exception as e:
        logger.warning(f"Failed to update doc quality: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


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
