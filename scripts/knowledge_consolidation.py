#!/usr/bin/env python3
"""
Knowledge Consolidation — Link session memories to domain_concept hubs.

Implements BPMN model `knowledge_consolidation` (v2, 2026-04-24):
  1. Load all active domain_concepts with embeddings
  2. Find mid/long tier memories not yet consolidated (last 30 days)
  3. Match memories to concepts via cosine similarity (>= 0.65)
  4. Link memory to concept via consolidated_into column (NO property append)
  5. Log to audit_log

v2 change (2026-04-24): previous version APPENDED memory content to
concept properties.gotchas arrays, creating 10K-token blobs per hub
that duplicated content living in claude.knowledge. v2 links without
duplicating — memory stays in claude.knowledge with per-memory
embedding, hub retrieval surfaces linked memories via the
consolidated_into column.

Usage:
    python knowledge_consolidation.py              # Run consolidation
    python knowledge_consolidation.py --dry-run    # Show what would happen
    python knowledge_consolidation.py --threshold 0.60  # Custom similarity threshold

Author: Claude Family
Date: 2026-04-10 (v2: 2026-04-24)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('knowledge_consolidation')

SIMILARITY_THRESHOLD = 0.65
LOOKBACK_DAYS = 30


def _parse_embedding(v):
    """pgvector round-trips as a JSON-like string '[...]' when psycopg2 has no vector adapter."""
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return None
    return v


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a = _parse_embedding(a)
    b = _parse_embedding(b)
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def generate_embedding(text):
    """Generate embedding using configured provider (FastEmbed local or Voyage AI)."""
    try:
        from embedding_provider import embed
        result = embed(text)
        return result
        return result.embeddings[0]
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


def load_domain_concepts(conn):
    """Load all active domain_concepts with embeddings."""
    cur = conn.cursor()
    cur.execute("""
        SELECT e.entity_id, e.display_name, e.properties, e.embedding
        FROM claude.entities e
        JOIN claude.entity_types et ON et.type_id = e.entity_type_id
        WHERE et.type_name = 'domain_concept'
          AND e.is_archived = false
          AND e.embedding IS NOT NULL
    """)
    rows = cur.fetchall()
    concepts = []
    for r in rows:
        if isinstance(r, dict):
            concepts.append(r)
        else:
            concepts.append({
                'entity_id': r[0], 'display_name': r[1],
                'properties': r[2], 'embedding': r[3]
            })
    logger.info(f"Loaded {len(concepts)} domain_concepts")
    return concepts


def find_unconsolidated_memories(conn):
    """Find mid/long tier memories not yet consolidated."""
    cur = conn.cursor()
    cur.execute("""
        SELECT knowledge_id, title, description, knowledge_type, embedding
        FROM claude.knowledge
        WHERE tier IN ('mid', 'long')
          AND consolidated_into IS NULL
          AND embedding IS NOT NULL
          AND created_at > NOW() - INTERVAL '%s days'
        ORDER BY created_at DESC
    """ % LOOKBACK_DAYS)
    rows = cur.fetchall()
    memories = []
    for r in rows:
        if isinstance(r, dict):
            memories.append(r)
        else:
            memories.append({
                'knowledge_id': r[0], 'title': r[1], 'description': r[2],
                'knowledge_type': r[3], 'embedding': r[4]
            })
    logger.info(f"Found {len(memories)} unconsolidated memories (last {LOOKBACK_DAYS} days)")
    return memories


def match_memories_to_concepts(memories, concepts, threshold):
    """Match each memory to nearest domain_concept via cosine similarity."""
    matches = {}  # concept_id -> [memory dicts]

    for mem in memories:
        mem_emb = mem['embedding']
        if not mem_emb:
            continue

        best_sim = 0
        best_concept = None

        for concept in concepts:
            concept_emb = concept['embedding']
            if not concept_emb:
                continue
            sim = cosine_similarity(mem_emb, concept_emb)
            if sim > best_sim:
                best_sim = sim
                best_concept = concept

        if best_sim >= threshold and best_concept:
            cid = str(best_concept['entity_id'])
            if cid not in matches:
                matches[cid] = {'concept': best_concept, 'memories': []}
            matches[cid]['memories'].append({
                **mem,
                'similarity': round(best_sim, 3)
            })

    total_matched = sum(len(m['memories']) for m in matches.values())
    logger.info(f"Matched {total_matched} memories to {len(matches)} concepts (threshold={threshold})")
    return matches


def link_and_mark(conn, matches, dry_run=False):
    """Link matched memories to their concepts via consolidated_into (v2: no property append).

    v2 change (2026-04-24): previously appended memory content to
    entity.properties.gotchas which caused the 10K-token hub bloat. We
    now leave memory content in claude.knowledge (where per-memory
    embeddings preserve semantic-search precision) and only set the
    consolidated_into column — the hub-surfacing behaviour is driven
    by that column at read time.
    """
    cur = conn.cursor()
    linked_count = 0

    for cid, data in matches.items():
        concept = data['concept']
        memory_ids = [str(m['knowledge_id']) for m in data['memories']]

        logger.info(f"  {concept['display_name']}: linking {len(memory_ids)} memories")

        if dry_run:
            continue

        # Link memories to concept (the load-bearing operation)
        for mid in memory_ids:
            cur.execute("""
                UPDATE claude.knowledge
                SET consolidated_into = %s
                WHERE knowledge_id = %s
                  AND consolidated_into IS NULL
            """, (cid, mid))

        # Audit log — link only, no properties mutation
        cur.execute("""
            INSERT INTO claude.audit_log (entity_type, entity_id, event_type, metadata, created_at)
            VALUES ('entity', %s, 'memories_linked_to_concept', %s::jsonb, NOW())
        """, (cid, json.dumps({
            'memories_linked': len(memory_ids),
            'concept_name': concept['display_name'],
            'bpmn_version': 'knowledge_consolidation_v2',
        })))

        conn.commit()
        linked_count += len(memory_ids)

    return linked_count


def consolidate_session(conn, session_id=None, threshold=SIMILARITY_THRESHOLD):
    """Lightweight consolidation for a single session's memories.

    Called at end_session() to merge corrections discovered during this session
    into domain_concept dossiers immediately, rather than waiting for the daily batch.

    Returns: {consolidated: int, concepts_updated: int}
    """
    try:
        concepts = load_domain_concepts(conn)
        if not concepts:
            return {"consolidated": 0, "concepts_updated": 0, "message": "No domain_concepts found"}

        # Find only this session's unconsolidated memories
        cur = conn.cursor()
        session_filter = ""
        params = []
        if session_id:
            # Match memories created during this session's timeframe
            session_filter = """
                AND k.created_at >= (SELECT session_start FROM claude.sessions WHERE session_id = %s::uuid)
            """
            params = [session_id]

        cur.execute(f"""
            SELECT knowledge_id, title, description, knowledge_type, embedding
            FROM claude.knowledge k
            WHERE tier IN ('mid', 'long')
              AND consolidated_into IS NULL
              AND embedding IS NOT NULL
              AND created_at > NOW() - INTERVAL '1 day'
              {session_filter}
            ORDER BY created_at DESC
        """, params)

        rows = cur.fetchall()
        memories = []
        for r in rows:
            if isinstance(r, dict):
                memories.append(r)
            else:
                memories.append({
                    'knowledge_id': r[0], 'title': r[1], 'description': r[2],
                    'knowledge_type': r[3], 'embedding': r[4]
                })

        if not memories:
            return {"consolidated": 0, "concepts_updated": 0, "message": "No session memories to consolidate"}

        logger.info(f"Session consolidation: {len(memories)} memories to check")

        matches = match_memories_to_concepts(memories, concepts, threshold)
        if not matches:
            return {"consolidated": 0, "concepts_updated": 0, "message": "No memories matched concepts"}

        linked = link_and_mark(conn, matches)
        logger.info(f"Session consolidation: linked {linked} memories to {len(matches)} concepts")
        return {"consolidated": linked, "concepts_updated": len(matches)}

    except Exception as e:
        logger.error(f"Session consolidation failed: {e}", exc_info=True)
        return {"consolidated": 0, "concepts_updated": 0, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description='Knowledge Consolidation Pipeline')
    parser.add_argument('--dry-run', action='store_true', help='Show what would happen')
    parser.add_argument('--threshold', type=float, default=SIMILARITY_THRESHOLD,
                        help=f'Cosine similarity threshold (default: {SIMILARITY_THRESHOLD})')
    args = parser.parse_args()

    conn = get_db_connection()
    if not conn:
        logger.error("Cannot connect to database")
        return 1

    try:
        concepts = load_domain_concepts(conn)
        if not concepts:
            logger.info("No domain_concepts found")
            return 0

        memories = find_unconsolidated_memories(conn)
        if not memories:
            logger.info("No unconsolidated memories found")
            return 0

        matches = match_memories_to_concepts(memories, concepts, args.threshold)
        if not matches:
            logger.info("No memories matched above threshold")
            return 0

        linked = link_and_mark(conn, matches, dry_run=args.dry_run)
        action = "Would link" if args.dry_run else "Linked"
        logger.info(f"{action} {linked} memories to {len(matches)} domain_concepts (v2: link, no append)")
        return 0

    except Exception as e:
        logger.error(f"Consolidation failed: {e}", exc_info=True)
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
