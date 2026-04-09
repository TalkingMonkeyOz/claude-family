#!/usr/bin/env python3
"""
rag_queries.py — All query engines that produce formatted context strings.

Extracted from rag_query_hook.py. Contains:
- query_knowledge()              — pgvector on claude.knowledge
- query_knowledge_graph()        — Seed + recursive CTE, falls back to query_knowledge
- query_critical_session_facts() — Simple SQL, no embeddings
- query_nimbus_context()         — Keyword search on nimbus_context schema
- needs_schema_search()          — Keyword check predicate
- query_schema_context()         — pgvector on claude.schema_registry
- query_vault_rag()              — pgvector on claude.vault_embeddings
- query_skill_suggestions()      — pgvector on claude.skill_content
- query_entity_catalog()         — pgvector on claude.entity_catalog
- query_workfiles()              — pgvector on claude.workfiles
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import json
import logging
import time
from typing import Optional, List
from pathlib import Path

from config import get_db_connection, detect_psycopg
from rag_utils import generate_embedding, extract_query_from_prompt, expand_query_with_vocabulary

# ---------------------------------------------------------------------------
# Module-level setup
# ---------------------------------------------------------------------------

DB_AVAILABLE = detect_psycopg()

logger = logging.getLogger('rag_query.queries')


# =============================================================================
# CONSTANTS
# =============================================================================

# Fact types that are always injected into every prompt (no embedding needed)
CRITICAL_FACT_TYPES = ['credential', 'endpoint', 'decision', 'config']

# Nimbus project names that should trigger nimbus_context queries
NIMBUS_PROJECTS = [
    'monash-nimbus-reports',
    'nimbus-user-loader',
    'nimbus-customer-app',
    'nimbus-mui',
    'ATO-Tax-Agent',
]

# Schema-related keywords that trigger schema_registry search
SCHEMA_KEYWORDS = [
    'table', 'column', 'schema', 'database', 'db ', ' db', 'foreign key',
    'constraint', 'which table', 'what table', 'where is', 'data model',
    'stores ', 'stored in', 'tracks ', 'tracks ', 'registry',
    'field', 'relation', 'index', 'primary key',
]


# =============================================================================
# KNOWLEDGE QUERIES (pgvector)
# =============================================================================

def query_knowledge(user_prompt: str, project_name: str, session_id: str = None,
                    top_k: int = 3, min_similarity: float = 0.55) -> str:
    """Query knowledge table for relevant entries.

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
        return None

    # Note: VOYAGE_AVAILABLE is checked inside generate_embedding() (lazy-loaded)

    try:
        start_time = time.time()

        # Extract query from user prompt
        query_text = extract_query_from_prompt(user_prompt)

        # Generate embedding for query (lazy-loads voyageai if needed)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Search knowledge table for similar entries
        # Filter by project if applies_to_projects is set, or include general knowledge
        # Note: applies_to_projects can be NULL, empty array [], or contain project names
        cur.execute("""
            SELECT
                knowledge_id::text,
                title,
                description,
                knowledge_type,
                knowledge_category,
                code_example,
                confidence_level,
                times_applied,
                1 - (embedding <=> %s::vector) as similarity_score,
                COALESCE(tier, 'mid') as tier
            FROM claude.knowledge
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> %s::vector) >= %s
              AND COALESCE(tier, 'mid') != 'archived'
              AND (
                  applies_to_projects IS NULL
                  OR cardinality(applies_to_projects) = 0
                  OR %s = ANY(applies_to_projects)
              )
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, project_name, query_embedding, top_k))

        results = cur.fetchall()

        if not results:
            conn.close()
            return None

        # Update access tracking for returned knowledge
        for r in results:
            knowledge_id = r['knowledge_id'] if isinstance(r, dict) else r[0]
            cur.execute("""
                UPDATE claude.knowledge
                SET last_accessed_at = NOW(),
                    access_count = COALESCE(access_count, 0) + 1
                WHERE knowledge_id = %s::uuid
            """, (knowledge_id,))
        conn.commit()

        latency_ms = int((time.time() - start_time) * 1000)

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"KNOWLEDGE RECALL ({len(results)} relevant entries, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                title = r['title']
                description = r['description']
                knowledge_type = r['knowledge_type']
                category = r['knowledge_category']
                code_example = r['code_example']
                confidence = r['confidence_level']
                times_applied = r['times_applied']
                similarity = round(r['similarity_score'], 3)
                tier = r.get('tier', 'mid')
            else:
                title = r[1]
                description = r[2]
                knowledge_type = r[3]
                category = r[4]
                code_example = r[5]
                confidence = r[6]
                times_applied = r[7]
                similarity = round(r[8], 3)
                tier = r[9] if len(r) > 9 else 'mid'

            # Format entry with tier label
            tier_label = f"[{tier.upper()}]" if tier else "[MID]"
            type_info = knowledge_type or 'knowledge'
            if category:
                type_info += f"/{category}"
            confidence_str = f"conf={confidence}%" if confidence else ""
            applied_str = f"used {times_applied}x" if times_applied else "never used"

            context_lines.append(f"{tier_label} {title} ({similarity} match, {type_info})")
            context_lines.append(f"   {confidence_str} | {applied_str}")
            context_lines.append("")
            context_lines.append(description)

            if code_example:
                context_lines.append("")
                context_lines.append("Code Example:")
                context_lines.append(code_example)

            context_lines.append("")
            context_lines.append("-" * 70)
            context_lines.append("")

        logger.info(f"Knowledge query success: {len(results)} entries, latency={latency_ms}ms")
        conn.close()
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Knowledge query failed: {e}", exc_info=True)
        return None


def query_knowledge_graph(user_prompt: str, project_name: str, session_id: str = None,
                          max_initial_hits: int = 3, max_hops: int = 2,
                          min_similarity: float = 0.55, token_budget: int = 400) -> Optional[str]:
    """Graph-aware knowledge search: pgvector seed + recursive CTE graph walk.

    Enhanced version of query_knowledge that also walks knowledge_relations
    to discover connected entries. Falls back to query_knowledge on error.

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        session_id: Current session ID (for logging)
        max_initial_hits: Max pgvector seed results
        max_hops: Max relationship hops from seed nodes
        min_similarity: Minimum similarity score (0-1)
        token_budget: Approximate token budget for results

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        return None

    try:
        start_time = time.time()

        query_text = extract_query_from_prompt(user_prompt)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Call the graph-aware search SQL function (explicit casts for psycopg type matching)
        cur.execute("""
            SELECT * FROM claude.graph_aware_search(
                %s::vector, %s::integer, %s::integer, 0.3::numeric, %s::numeric, %s::integer
            )
        """, (query_embedding, max_initial_hits, max_hops,
              min_similarity, token_budget))

        results = cur.fetchall()

        if not results:
            conn.close()
            return None

        # Update access stats via the bulk function
        knowledge_ids = [r['knowledge_id'] if isinstance(r, dict) else r[0] for r in results]
        cur.execute("SELECT claude.update_knowledge_access(%s)", (knowledge_ids,))
        conn.commit()

        latency_ms = int((time.time() - start_time) * 1000)
        direct_count = sum(1 for r in results if (r['source_type'] if isinstance(r, dict) else r[6]) == 'direct')
        graph_count = sum(1 for r in results if (r['source_type'] if isinstance(r, dict) else r[6]) == 'graph')

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        label = f"KNOWLEDGE GRAPH ({len(results)} entries: {direct_count} direct + {graph_count} graph, {latency_ms}ms)"
        context_lines.append(label)
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                title = r['title']
                description = r['description']
                knowledge_type = r['knowledge_type']
                category = r['knowledge_category']
                confidence = r['confidence_level']
                source_type = r['source_type']
                similarity = round(r['similarity'], 3)
                graph_depth = r['graph_depth']
                edge_path = r['edge_path']
                relevance = round(r['relevance_score'], 3)
            else:
                title = r[1]
                description = r[4]
                knowledge_type = r[2]
                category = r[3]
                confidence = r[5]
                source_type = r[6]
                similarity = round(r[7], 3)
                graph_depth = r[8]
                edge_path = r[9]
                relevance = round(r[10], 3)

            type_info = knowledge_type or 'knowledge'
            if category:
                type_info += f"/{category}"
            confidence_str = f"conf={confidence}%" if confidence else ""

            # Show source indicator
            if source_type == 'graph':
                source_label = f"graph:{edge_path}(depth={graph_depth})"
            else:
                source_label = f"direct(sim={similarity})"

            context_lines.append(f"💡 {title} ({relevance} score, {type_info})")
            context_lines.append(f"   {confidence_str} | {source_label}")
            context_lines.append("")
            context_lines.append(description)
            context_lines.append("")
            context_lines.append("-" * 70)
            context_lines.append("")

        logger.info(f"Graph knowledge query: {len(results)} entries ({direct_count}+{graph_count}g), {latency_ms}ms")
        conn.close()
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Graph knowledge query failed, falling back: {e}", exc_info=True)
        # Fall back to standard pgvector-only search
        return query_knowledge(user_prompt, project_name, session_id,
                               top_k=max_initial_hits, min_similarity=min_similarity)


# =============================================================================
# SESSION FACTS AUTO-INJECTION (No embedding - just SQL)
# =============================================================================
# Lightweight query to inject critical session facts (credentials, endpoints,
# decisions) into every prompt. No Voyage AI needed - just a simple SELECT.

def query_critical_session_facts(project_name: str, session_id: str = None,
                                  limit: int = 5) -> Optional[str]:
    """Query critical session facts for auto-injection.

    This is LIGHTWEIGHT - no embeddings, just a simple SQL query.
    Only returns facts of critical types that Claude should always see.

    Args:
        project_name: Current project name
        session_id: Current session ID (optional)
        limit: Max facts to return

    Returns:
        Formatted context string or None if no facts
    """
    if not DB_AVAILABLE:
        return None

    try:
        start_time = time.time()
        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Simple query - no embeddings needed
        # Cast session_id to text for type inference on NULL check (fixes PostgreSQL parameter $4 error)
        cur.execute("""
            SELECT fact_key, fact_value, fact_type, is_sensitive
            FROM claude.session_facts
            WHERE project_name = %s
              AND fact_type = ANY(%s)
              AND (session_id::text = %s OR session_id IS NULL OR %s::text IS NULL)
            ORDER BY
                CASE fact_type
                    WHEN 'credential' THEN 1
                    WHEN 'endpoint' THEN 2
                    WHEN 'config' THEN 3
                    WHEN 'decision' THEN 4
                    ELSE 5
                END,
                created_at DESC
            LIMIT %s
        """, (project_name, CRITICAL_FACT_TYPES, session_id, session_id, limit))

        facts = cur.fetchall()
        conn.close()

        if not facts:
            return None

        latency_ms = int((time.time() - start_time) * 1000)

        # Format as compact notepad view
        lines = []
        lines.append("")
        lines.append("📓 YOUR NOTEPAD (auto-loaded critical facts):")

        for f in facts:
            if isinstance(f, dict):
                key = f['fact_key']
                value = f['fact_value'] if not f['is_sensitive'] else '[SENSITIVE]'
                ftype = f['fact_type']
            else:
                key = f[0]
                value = f[1] if not f[3] else '[SENSITIVE]'
                ftype = f[2]

            # Truncate long values
            if len(value) > 60:
                value = value[:57] + "..."

            lines.append(f"  [{ftype}] {key}: {value}")

        lines.append(f"  (Use list_session_facts() for full notepad | {latency_ms}ms)")
        lines.append("")

        logger.info(f"Session facts auto-inject: {len(facts)} facts, {latency_ms}ms")
        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Session facts query failed: {e}")
        return None


# =============================================================================
# NIMBUS CONTEXT QUERY (keyword search)
# =============================================================================

def query_nimbus_context(user_prompt: str, project_name: str, top_k: int = 3) -> str:
    """Query nimbus_context schema for Nimbus project knowledge.

    Uses keyword search (no embeddings) for:
    - code_patterns: Reusable code patterns
    - project_learnings: Lessons learned
    - project_facts: Known facts about the codebase

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        top_k: Number of results per table

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        return None

    # Only query for Nimbus projects
    if project_name not in NIMBUS_PROJECTS:
        return None

    try:
        start_time = time.time()
        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Extract keywords from prompt (simple tokenization)
        keywords = [w.lower() for w in re.findall(r'\w+', user_prompt) if len(w) > 3]
        if not keywords:
            conn.close()
            return None

        # Build search pattern (any keyword match)
        search_pattern = '%' + '%'.join(keywords[:5]) + '%'  # Limit to 5 keywords

        results = []

        # 1. Search code_patterns
        try:
            cur.execute("""
                SELECT 'pattern' as source, pattern_type, solution, context, created_at
                FROM nimbus_context.code_patterns
                WHERE solution ILIKE %s OR context ILIKE %s OR pattern_type ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, top_k))
            results.extend([('pattern', r) for r in cur.fetchall()])
        except Exception as e:
            logger.warning(f"code_patterns query failed: {e}")

        # 2. Search project_learnings
        try:
            cur.execute("""
                SELECT 'learning' as source, category, learning, context, created_at
                FROM nimbus_context.project_learnings
                WHERE learning ILIKE %s OR context ILIKE %s OR category ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, top_k))
            results.extend([('learning', r) for r in cur.fetchall()])
        except Exception as e:
            logger.warning(f"project_learnings query failed: {e}")

        # 3. Search project_facts
        try:
            cur.execute("""
                SELECT 'fact' as source, category, fact_key, fact_value, created_at
                FROM nimbus_context.project_facts
                WHERE fact_key ILIKE %s OR fact_value ILIKE %s OR category ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, top_k))
            results.extend([('fact', r) for r in cur.fetchall()])
        except Exception as e:
            logger.warning(f"project_facts query failed: {e}")

        conn.close()

        if not results:
            logger.info(f"No nimbus_context results for keywords: {keywords[:3]}")
            return None

        latency_ms = int((time.time() - start_time) * 1000)

        # Format results
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"NIMBUS PROJECT CONTEXT ({len(results)} entries, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for source_type, r in results:
            if isinstance(r, dict):
                if source_type == 'pattern':
                    context_lines.append(f"🔧 PATTERN [{r['pattern_type']}]")
                    context_lines.append(f"   Context: {r['context'] or 'N/A'}")
                    context_lines.append(f"   Solution: {r['solution'][:200]}...")
                elif source_type == 'learning':
                    context_lines.append(f"💡 LEARNING [{r['category']}]")
                    context_lines.append(f"   Context: {r['context'] or 'N/A'}")
                    context_lines.append(f"   {r['learning']}")
                elif source_type == 'fact':
                    context_lines.append(f"📋 FACT [{r['category']}]")
                    context_lines.append(f"   {r['fact_key']}: {r['fact_value']}")
            else:
                # Tuple format (psycopg2)
                if source_type == 'pattern':
                    context_lines.append(f"🔧 PATTERN [{r[1]}]")
                    context_lines.append(f"   Context: {r[3] or 'N/A'}")
                    context_lines.append(f"   Solution: {r[2][:200] if r[2] else 'N/A'}...")
                elif source_type == 'learning':
                    context_lines.append(f"💡 LEARNING [{r[1]}]")
                    context_lines.append(f"   Context: {r[3] or 'N/A'}")
                    context_lines.append(f"   {r[2]}")
                elif source_type == 'fact':
                    context_lines.append(f"📋 FACT [{r[1]}]")
                    context_lines.append(f"   {r[2]}: {r[3]}")
            context_lines.append("")

        context_lines.append("-" * 70)
        context_lines.append("")

        logger.info(f"Nimbus context query: {len(results)} results, latency={latency_ms}ms")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Nimbus context query failed: {e}", exc_info=True)
        return None


# =============================================================================
# SCHEMA CONTEXT QUERY (pgvector on schema_registry)
# =============================================================================

def needs_schema_search(user_prompt: str) -> bool:
    """Detect if prompt would benefit from schema context."""
    prompt_lower = user_prompt.lower()
    return any(kw in prompt_lower for kw in SCHEMA_KEYWORDS)


def query_schema_context(user_prompt: str, top_k: int = 3,
                         min_similarity: float = 0.40) -> Optional[str]:
    """Query schema_registry embeddings for relevant table context.

    Returns formatted schema context or None if no results.
    """
    if not DB_AVAILABLE:
        return None

    try:
        start_time = time.time()
        query_text = extract_query_from_prompt(user_prompt)

        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()
        cur.execute("""
            SELECT
                table_name,
                purpose,
                column_descriptions,
                fk_relationships,
                row_count_actual,
                1 - (embedding <=> %s::vector) as similarity
            FROM claude.schema_registry
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity,
              query_embedding, top_k))

        results = cur.fetchall()
        conn.close()

        if not results:
            return None

        latency_ms = int((time.time() - start_time) * 1000)

        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"SCHEMA CONTEXT ({len(results)} relevant tables, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                tbl = r['table_name']
                purpose = r['purpose']
                cols = r.get('column_descriptions') or {}
                fks = r.get('fk_relationships') or []
                rows = r.get('row_count_actual')
                sim = round(r['similarity'], 3)
            else:
                tbl, purpose, cols, fks, rows, sim = r[0], r[1], r[2] or {}, r[3] or [], r[4], round(r[5], 3)

            context_lines.append(f"[TABLE] claude.{tbl} ({sim} match)")
            context_lines.append(f"  Purpose: {purpose}")

            # Show key columns (limit to 8 to save tokens)
            if isinstance(cols, dict):
                col_list = list(cols.items())[:8]
                if col_list:
                    context_lines.append(f"  Columns: {', '.join(c[0] for c in col_list)}")

            # Show relationships
            if fks:
                fk_list = fks if isinstance(fks, list) else []
                for fk in fk_list[:3]:
                    if isinstance(fk, dict):
                        context_lines.append(f"  FK: {fk.get('column', '?')} -> {fk.get('references', '?')}")

            if rows is not None:
                context_lines.append(f"  Rows: ~{rows:,}")

            context_lines.append("")

        logger.info(f"Schema context: {len(results)} tables, latency={latency_ms}ms")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Schema context query failed: {e}", exc_info=True)
        return None


# =============================================================================
# VAULT RAG QUERY (pgvector on vault_embeddings)
# =============================================================================

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

    # Note: VOYAGE_AVAILABLE is checked inside generate_embedding() (lazy-loaded)

    try:
        start_time = time.time()

        # Extract query from user prompt
        query_text = extract_query_from_prompt(user_prompt)

        # Connect to database (needed for vocabulary expansion and search)
        conn = get_db_connection()
        if not conn:
            logger.warning("Could not connect to database - skipping RAG")
            return None

        # VOCABULARY EXPANSION: Expand query with learned user vocabulary
        # This translates user phrases (e.g., "spin up") to canonical concepts (e.g., "create")
        expanded_query = expand_query_with_vocabulary(conn, query_text)

        # Generate embedding for EXPANDED query (better semantic matching)
        query_embedding = generate_embedding(expanded_query)
        if not query_embedding:
            conn.close()
            return None

        cur = conn.cursor()

        # Search for similar documents (prefer vault docs, include project docs)
        # EXCLUSIONS: awesome-copilot-reference is reference material, not searchable knowledge
        # DEDUPLICATION: Fetch extra results, then dedupe by doc_path (take best chunk per doc)
        fetch_count = top_k * 3  # Fetch 3x to allow for deduplication
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
              AND doc_path NOT LIKE '%%awesome-copilot%%'
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, project_name, query_embedding, fetch_count))

        raw_results = cur.fetchall()

        # DEDUPLICATION: Group by doc_path, keep highest similarity chunk per doc
        # This prevents the same document appearing 2-3 times with different chunks
        seen_docs = {}
        for r in raw_results:
            doc_path = r['doc_path'] if isinstance(r, dict) else r[0]
            similarity = r['similarity_score'] if isinstance(r, dict) else r[4]

            if doc_path not in seen_docs or similarity > (seen_docs[doc_path]['similarity_score'] if isinstance(seen_docs[doc_path], dict) else seen_docs[doc_path][4]):
                seen_docs[doc_path] = r

        # Convert back to list and take top_k
        results = list(seen_docs.values())[:top_k]
        logger.info(f"Deduplication: {len(raw_results)} raw -> {len(seen_docs)} unique docs -> {len(results)} returned")

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


# =============================================================================
# SKILL SUGGESTIONS QUERY (pgvector on skill_content)
# =============================================================================

def query_skill_suggestions(user_prompt: str, project_name: str,
                             top_k: int = 2, min_similarity: float = 0.50) -> str:
    """Query skill_content for relevant skills by semantic similarity.

    Args:
        user_prompt: The user's question/prompt
        project_name: Current project name
        top_k: Number of skills to suggest
        min_similarity: Minimum similarity score (0-1)

    Returns:
        Formatted skill suggestions or None if no matches
    """
    if not DB_AVAILABLE:
        return None

    # Note: VOYAGE_AVAILABLE is checked inside generate_embedding() (lazy-loaded)

    try:
        start_time = time.time()

        # Generate embedding for query (lazy-loads voyageai if needed)
        query_text = extract_query_from_prompt(user_prompt)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()

        # Search skill_content by embedding similarity
        cur.execute("""
            SELECT
                name,
                description,
                category,
                1 - (description_embedding <=> %s::vector) as similarity_score
            FROM claude.skill_content
            WHERE active = true
              AND description_embedding IS NOT NULL
              AND 1 - (description_embedding <=> %s::vector) >= %s
            ORDER BY description_embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, query_embedding, top_k))

        results = cur.fetchall()
        conn.close()

        if not results:
            logger.info(f"No skill matches >= {min_similarity} for query: {query_text[:50]}")
            return None

        latency_ms = int((time.time() - start_time) * 1000)

        # Format suggestions
        context_lines = []
        context_lines.append("")
        context_lines.append("=" * 70)
        context_lines.append(f"SKILL SUGGESTIONS ({len(results)} matches, {latency_ms}ms)")
        context_lines.append("=" * 70)
        context_lines.append("")

        for r in results:
            if isinstance(r, dict):
                name = r['name']
                description = r['description']
                category = r['category']
                similarity = round(r['similarity_score'], 2)
            else:
                name = r[0]
                description = r[1]
                category = r[2]
                similarity = round(r[3], 2)

            # Truncate description
            desc_short = description[:100] + "..." if len(description) > 100 else description

            context_lines.append(f">> {name} ({similarity} match, {category})")
            context_lines.append(f"   {desc_short}")
            context_lines.append(f"   Action: Use Skill tool to load if task is complex")
            context_lines.append("")

        context_lines.append("-" * 70)
        context_lines.append("")

        logger.info(f"Skill suggestions: {len(results)} matches, top={results[0]['similarity_score'] if isinstance(results[0], dict) else results[0][3]:.2f}")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Skill suggestion query failed: {e}", exc_info=True)
        return None


def query_entity_catalog(user_prompt: str, project_name: str,
                         top_k: int = 3, min_similarity: float = 0.45) -> str:
    """Query entity catalog for structured reference data (APIs, schemas, domain concepts).

    Searches claude.entities using pgvector similarity on the embedding column.
    Returns formatted context showing matching entities with their summaries.

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        return None

    try:
        start_time = time.time()
        query_text = extract_query_from_prompt(user_prompt)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()
        cur.execute("""
            SELECT
                e.display_name,
                et.type_name,
                e.summary,
                e.tags,
                1 - (e.embedding <=> %s::vector) as similarity_score
            FROM claude.entities e
            JOIN claude.entity_types et ON et.type_id = e.entity_type_id
            LEFT JOIN claude.projects p ON p.project_id = e.project_id
            WHERE e.embedding IS NOT NULL
              AND e.is_archived = false
              AND 1 - (e.embedding <=> %s::vector) >= %s
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, query_embedding, top_k))

        results = cur.fetchall()
        conn.close()

        if not results:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Entity catalog: 0 matches >= {min_similarity} in {elapsed_ms:.0f}ms")
            return None

        elapsed_ms = (time.time() - start_time) * 1000
        context_lines = [
            "[ENTITY CATALOG — Structured reference data]",
        ]

        similarities = []
        for r in results:
            if isinstance(r, dict):
                name, etype, summary, tags, sim = r['display_name'], r['type_name'], r['summary'], r['tags'], r['similarity_score']
            else:
                name, etype, summary, tags, sim = r[0], r[1], r[2], r[3], r[4]

            similarities.append(round(sim, 3))
            summary_short = (summary[:150] + "...") if summary and len(summary) > 150 else (summary or "")
            tag_str = ", ".join(tags[:3]) if tags else ""
            context_lines.append(f">> {name} ({etype}, {round(sim, 2)} match)")
            if tag_str:
                context_lines.append(f"   Tags: {tag_str}")
            if summary_short:
                context_lines.append(f"   {summary_short}")
            context_lines.append(f"   Use: recall_entities(\"{name}\") for full details")
            context_lines.append("")

        logger.info(f"Entity catalog: {len(results)} matches in {elapsed_ms:.0f}ms, similarities={similarities}")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Entity catalog query failed: {e}", exc_info=True)
        return None


def query_workfiles(user_prompt: str, project_name: str,
                    top_k: int = 2, min_similarity: float = 0.45) -> str:
    """Query active workfiles for component working context.

    Searches claude.project_workfiles using pgvector similarity on the embedding column.
    Returns formatted context showing matching workfiles with content previews.

    Returns:
        Formatted context string or None if no results
    """
    if not DB_AVAILABLE:
        return None

    try:
        start_time = time.time()
        query_text = extract_query_from_prompt(user_prompt)
        query_embedding = generate_embedding(query_text)
        if not query_embedding:
            return None

        conn = get_db_connection()
        if not conn:
            return None

        cur = conn.cursor()
        cur.execute("""
            SELECT
                w.component,
                w.title,
                LEFT(w.content, 200) as preview,
                w.workfile_type,
                w.is_pinned,
                1 - (w.embedding <=> %s::vector) as similarity_score
            FROM claude.project_workfiles w
            JOIN claude.projects p ON p.project_id = w.project_id
            WHERE w.embedding IS NOT NULL
              AND w.is_active = true
              AND p.project_name = %s
              AND 1 - (w.embedding <=> %s::vector) >= %s
            ORDER BY w.embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, project_name, query_embedding, min_similarity, query_embedding, top_k))

        results = cur.fetchall()
        conn.close()

        if not results:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(f"Workfile search: 0 matches >= {min_similarity} in {elapsed_ms:.0f}ms")
            return None

        elapsed_ms = (time.time() - start_time) * 1000
        context_lines = [
            "[WORKFILES — Component working context]",
        ]

        similarities = []
        for r in results:
            if isinstance(r, dict):
                comp, title, preview, wtype, pinned, sim = r['component'], r['title'], r['preview'], r['workfile_type'], r['is_pinned'], r['similarity_score']
            else:
                comp, title, preview, wtype, pinned, sim = r[0], r[1], r[2], r[3], r[4], r[5]

            similarities.append(round(sim, 3))
            pin_marker = " [PINNED]" if pinned else ""
            preview_clean = preview.replace('\n', ' ').strip() if preview else ""
            context_lines.append(f">> {comp}/{title} ({wtype}, {round(sim, 2)} match){pin_marker}")
            if preview_clean:
                context_lines.append(f"   {preview_clean[:120]}...")
            context_lines.append(f"   Use: unstash(\"{comp}\") for full content")
            context_lines.append("")

        logger.info(f"Workfile search: {len(results)} matches in {elapsed_ms:.0f}ms, similarities={similarities}")
        return "\n".join(context_lines)

    except Exception as e:
        logger.error(f"Workfile search failed: {e}", exc_info=True)
        return None
