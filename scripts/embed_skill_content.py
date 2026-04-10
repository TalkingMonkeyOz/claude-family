#!/usr/bin/env python3
"""
Embed skill_content descriptions for semantic search.

One-time script to generate embeddings for all skill_content entries via embedding_provider.
"""

import os
import sys

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri

from embedding_provider import embed_batch

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

def main():
    # Connect to database
    conn_str = get_database_uri()
    conn = psycopg.connect(conn_str, row_factory=dict_row)
    cur = conn.cursor()

    # Get all skills without embeddings
    cur.execute("""
        SELECT content_id, name, description
        FROM claude.skill_content
        WHERE active = true
          AND description IS NOT NULL
          AND (description_embedding IS NULL OR description_embedding IS NOT NULL)
    """)
    skills = cur.fetchall()
    print(f"Found {len(skills)} skills to embed")

    if not skills:
        print("No skills to embed")
        return

    # Embed in batches
    batch_size = 20
    updated = 0

    for i in range(0, len(skills), batch_size):
        batch = skills[i:i+batch_size]
        texts = [s['description'] for s in batch]

        print(f"Embedding batch {i//batch_size + 1}: {len(texts)} descriptions...")

        embeddings = embed_batch(texts)
        if embeddings is None:
            print(f"  [ERROR] Embedding batch failed, skipping")
            continue

        for skill, embedding in zip(batch, embeddings):
            cur.execute("""
                UPDATE claude.skill_content
                SET description_embedding = %s::vector
                WHERE content_id = %s
            """, (embedding, skill['content_id']))
            updated += 1
            print(f"  [OK] {skill['name']}")

        conn.commit()

    print(f"\nEmbedded {updated} skill descriptions")
    conn.close()

if __name__ == "__main__":
    main()
