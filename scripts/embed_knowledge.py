#!/usr/bin/env python3
"""
Knowledge Embedding Script - Generate embeddings for knowledge table entries

Reads knowledge entries from the database, generates embeddings using Voyage AI,
and stores them back for semantic search.

Usage:
    python embed_knowledge.py [--force] [--batch-size N]

Options:
    --force         Re-embed all entries even if they have embeddings
    --batch-size N  Number of entries to process per API call (default: 10)
"""

import os
import sys
import argparse
import logging
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('knowledge_embedder')

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    logger.error("psycopg not installed. Run: pip install psycopg")
    sys.exit(1)

try:
    import requests
except ImportError:
    logger.error("requests not installed. Run: pip install requests")
    sys.exit(1)

# Configuration
DB_CONNECTION = "postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation"
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
EMBEDDING_MODEL = "voyage-3"


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts using Voyage AI."""
    if not VOYAGE_API_KEY:
        raise RuntimeError("VOYAGE_API_KEY environment variable not set")

    response = requests.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {VOYAGE_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "input": texts,
            "model": EMBEDDING_MODEL,
            "input_type": "document"
        },
        timeout=60
    )
    response.raise_for_status()
    result = response.json()
    return [item["embedding"] for item in result["data"]]


def format_knowledge_for_embedding(entry: dict) -> str:
    """Format a knowledge entry as text for embedding."""
    parts = []

    # Title and type
    if entry.get('title'):
        parts.append(f"# {entry['title']}")

    if entry.get('knowledge_type') or entry.get('knowledge_category'):
        type_cat = f"Type: {entry.get('knowledge_type', 'unknown')}"
        if entry.get('knowledge_category'):
            type_cat += f" | Category: {entry['knowledge_category']}"
        parts.append(type_cat)

    # Description (main content)
    if entry.get('description'):
        parts.append(entry['description'])

    # Code example if present
    if entry.get('code_example'):
        parts.append(f"\nCode Example:\n{entry['code_example']}")

    # Projects it applies to
    if entry.get('applies_to_projects'):
        projects = ', '.join(entry['applies_to_projects'])
        parts.append(f"\nApplies to: {projects}")

    return '\n\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description='Embed knowledge entries for semantic search')
    parser.add_argument('--force', action='store_true', help='Re-embed all entries')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for API calls')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    if not VOYAGE_API_KEY:
        logger.error("VOYAGE_API_KEY environment variable not set")
        logger.info("Set it with: export VOYAGE_API_KEY='your-key'")
        sys.exit(1)

    logger.info("Connecting to database...")
    with psycopg.connect(DB_CONNECTION, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Get entries that need embedding
            if args.force:
                cur.execute("""
                    SELECT knowledge_id, title, knowledge_type, knowledge_category,
                           description, code_example, applies_to_projects
                    FROM claude.knowledge
                    ORDER BY created_at DESC
                """)
            else:
                cur.execute("""
                    SELECT knowledge_id, title, knowledge_type, knowledge_category,
                           description, code_example, applies_to_projects
                    FROM claude.knowledge
                    WHERE embedding IS NULL
                    ORDER BY created_at DESC
                """)

            entries = cur.fetchall()

            if not entries:
                logger.info("No knowledge entries need embedding")
                return

            logger.info(f"Found {len(entries)} entries to embed")

            if args.dry_run:
                for entry in entries[:5]:
                    logger.info(f"  Would embed: {entry['title']}")
                if len(entries) > 5:
                    logger.info(f"  ... and {len(entries) - 5} more")
                return

            # Process in batches
            processed = 0
            errors = 0

            for i in range(0, len(entries), args.batch_size):
                batch = entries[i:i + args.batch_size]

                try:
                    # Format texts for embedding
                    texts = [format_knowledge_for_embedding(e) for e in batch]

                    # Generate embeddings
                    logger.info(f"Generating embeddings for batch {i//args.batch_size + 1}...")
                    embeddings = generate_embeddings_batch(texts)

                    # Store embeddings
                    for entry, embedding in zip(batch, embeddings):
                        cur.execute("""
                            UPDATE claude.knowledge
                            SET embedding = %s::vector
                            WHERE knowledge_id = %s
                        """, (embedding, entry['knowledge_id']))
                        processed += 1

                    conn.commit()
                    logger.info(f"  Processed {processed}/{len(entries)} entries")

                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    errors += len(batch)
                    conn.rollback()

            logger.info(f"\nComplete! Processed: {processed}, Errors: {errors}")

            # Show stats
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(embedding) as with_embedding
                FROM claude.knowledge
            """)
            stats = cur.fetchone()
            logger.info(f"Knowledge table: {stats['with_embedding']}/{stats['total']} entries have embeddings")


if __name__ == "__main__":
    main()
