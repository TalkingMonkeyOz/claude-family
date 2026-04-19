"""Re-embed entities and workfiles with current embedding provider (FastEmbed)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from embedding_provider import embed_batch
from config import get_database_uri
import psycopg
from psycopg.rows import dict_row

DB = get_database_uri()
batch_size = 50

with psycopg.connect(DB, row_factory=dict_row) as conn:
    # Re-embed entities (include rows with NULL embedding — FB301)
    rows = conn.execute(
        "SELECT entity_id::text, COALESCE(properties->>'name', properties->>'title', 'Unknown') as text "
        "FROM claude.entities WHERE NOT is_archived"
    ).fetchall()
    print(f"Entities to re-embed: {len(rows)}")

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        texts = [r['text'] for r in batch]
        embeddings = embed_batch(texts)
        for j, emb in enumerate(embeddings):
            if emb:
                conn.execute(
                    "UPDATE claude.entities SET embedding = %s::vector WHERE entity_id = %s::uuid",
                    (emb, batch[j]['entity_id'])
                )
        conn.commit()
        print(f"  Entities {i+1}-{i+len(batch)} done")

    # Re-embed workfiles (include rows with NULL embedding — FB301)
    rows = conn.execute(
        "SELECT workfile_id::text, title, SUBSTRING(content, 1, 500) as text "
        "FROM claude.project_workfiles WHERE is_active = true"
    ).fetchall()
    print(f"Workfiles to re-embed: {len(rows)}")

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        texts = [w['title'] + ': ' + w['text'] for w in batch]
        embeddings = embed_batch(texts)
        for j, emb in enumerate(embeddings):
            if emb:
                conn.execute(
                    "UPDATE claude.project_workfiles SET embedding = %s::vector WHERE workfile_id = %s::uuid",
                    (emb, batch[j]['workfile_id'])
                )
        conn.commit()
        print(f"  Workfiles {i+1}-{i+len(batch)} done")

print("Entity + workfile re-embedding DONE")
