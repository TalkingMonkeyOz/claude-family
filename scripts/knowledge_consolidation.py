#!/usr/bin/env python3
"""
Knowledge Consolidation — Merge session memories into domain_concept dossiers.

Implements BPMN model `knowledge_consolidation`:
  1. Load all active domain_concepts with embeddings
  2. Find mid/long tier memories not yet consolidated (last 30 days)
  3. Match memories to concepts via cosine similarity (>= 0.65)
  4. Compare content to avoid duplicates
  5. Append new gotchas/recipes to concept properties
  6. Mark memories as consolidated
  7. Re-embed updated concepts
  8. Log to audit_log

Usage:
    python knowledge_consolidation.py              # Run consolidation
    python knowledge_consolidation.py --dry-run    # Show what would happen
    python knowledge_consolidation.py --threshold 0.60  # Custom similarity threshold

Author: Claude Family
Date: 2026-04-10
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, get_voyage_key, detect_psycopg

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('knowledge_consolidation')

SIMILARITY_THRESHOLD = 0.65
LOOKBACK_DAYS = 30


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def generate_embedding(text):
    """Generate Voyage AI embedding for text."""
    try:
        import voyageai
        key = get_voyage_key()
        if not key:
            logger.warning("No Voyage AI key available")
            return None
        client = voyageai.Client(api_key=key)
        result = client.embed([text], model="voyage-3", input_type="document")
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
        SELECT knowledge_id, title, description, tags, embedding
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
                'tags': r[3], 'embedding': r[4]
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


def is_duplicate_gotcha(new_text, existing_gotchas):
    """Check if a gotcha is already captured (simple substring check)."""
    new_lower = new_text.lower()
    for existing in existing_gotchas:
        existing_lower = existing.lower()
        # If >60% of words overlap, consider it a duplicate
        new_words = set(new_lower.split())
        existing_words = set(existing_lower.split())
        if not new_words:
            return True
        overlap = len(new_words & existing_words) / len(new_words)
        if overlap > 0.6:
            return True
    return False


def extract_new_knowledge(matches):
    """Extract new gotchas from matched memories, avoiding duplicates."""
    results = {}

    for cid, data in matches.items():
        concept = data['concept']
        props = concept['properties'] or {}
        existing_gotchas = props.get('gotchas', [])

        new_gotchas = []
        for mem in data['memories']:
            desc = mem.get('description', '') or mem.get('title', '')
            if not desc or len(desc) < 20:
                continue
            if not is_duplicate_gotcha(desc, existing_gotchas + new_gotchas):
                new_gotchas.append(desc)

        if new_gotchas:
            results[cid] = {
                'concept': concept,
                'new_gotchas': new_gotchas,
                'memory_ids': [str(m['knowledge_id']) for m in data['memories']]
            }

    total_new = sum(len(r['new_gotchas']) for r in results.values())
    logger.info(f"Extracted {total_new} new gotchas for {len(results)} concepts")
    return results


def merge_and_mark(conn, results, dry_run=False):
    """Merge new gotchas into concepts and mark memories as consolidated."""
    cur = conn.cursor()
    merged_count = 0

    for cid, data in results.items():
        concept = data['concept']
        new_gotchas = data['new_gotchas']
        memory_ids = data['memory_ids']

        logger.info(f"  {concept['display_name']}: +{len(new_gotchas)} gotchas from {len(memory_ids)} memories")
        for g in new_gotchas:
            logger.info(f"    + {g[:100]}...")

        if dry_run:
            continue

        # Append gotchas to properties
        cur.execute("""
            UPDATE claude.entities
            SET properties = jsonb_set(
                COALESCE(properties, '{}'::jsonb),
                '{gotchas}',
                COALESCE(properties->'gotchas', '[]'::jsonb) || %s::jsonb
            ),
            updated_at = NOW()
            WHERE entity_id = %s
        """, (json.dumps(new_gotchas), cid))

        # Mark memories as consolidated
        for mid in memory_ids:
            cur.execute("""
                UPDATE claude.knowledge
                SET consolidated_into = %s
                WHERE knowledge_id = %s
            """, (cid, mid))

        # Re-embed the updated concept
        cur.execute("SELECT properties FROM claude.entities WHERE entity_id = %s", (cid,))
        row = cur.fetchone()
        updated_props = row[0] if not isinstance(row, dict) else row['properties']
        embed_text = f"{concept['display_name']}: {json.dumps(updated_props, default=str)[:2000]}"
        new_embedding = generate_embedding(embed_text)
        if new_embedding:
            cur.execute("""
                UPDATE claude.entities SET embedding = %s::vector
                WHERE entity_id = %s
            """, (str(new_embedding), cid))

        # Audit log
        cur.execute("""
            INSERT INTO claude.audit_log (entity_type, entity_id, action, details, created_at)
            VALUES ('entity', %s, 'knowledge_consolidated',
                    %s::jsonb, NOW())
        """, (cid, json.dumps({
            'memories_merged': len(memory_ids),
            'new_gotchas': len(new_gotchas),
            'concept_name': concept['display_name']
        })))

        conn.commit()
        merged_count += len(new_gotchas)

    return merged_count


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

        results = extract_new_knowledge(matches)
        if not results:
            logger.info("All matched memories already captured in concepts")
            return 0

        merged = merge_and_mark(conn, results, dry_run=args.dry_run)
        action = "Would merge" if args.dry_run else "Merged"
        logger.info(f"{action} {merged} new gotchas into domain_concepts")
        return 0

    except Exception as e:
        logger.error(f"Consolidation failed: {e}", exc_info=True)
        return 1
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
