---
projects:
- project-metis
- claude-family
tags:
- research
- data-model
- schema
- rag
synced: false
---

# Schema Detail: `claude.vault_embeddings`

Back to [[schema-index]]

**Row count (audit 2026-02-28)**: 9,655
**Purpose**: Chunked document embeddings for the RAG system. Every vault markdown file is split into ~1000-char chunks with 200-char overlap; each chunk gets a Voyage AI embedding. This is the primary RAG target queried on every user prompt by `rag_query_hook.py`.

---

## Columns

| # | Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `embedding_id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| 2 | `doc_path` | `text` | NO | — | Relative path from vault root |
| 3 | `doc_title` | `text` | YES | NULL | From frontmatter or filename |
| 4 | `chunk_index` | `integer` | NO | `0` | 0-based chunk position within document |
| 5 | `chunk_text` | `text` | NO | — | Actual text of this chunk |
| 6 | `embedding` | `vector(1024)` | NO | — | Voyage AI voyage-3 embedding (1024 dims) |
| 7 | `metadata` | `jsonb` | YES | NULL | Parsed YAML frontmatter (projects, tags, synced) |
| 8 | `file_hash` | `varchar` | YES | NULL | SHA-256 of source file (for incremental re-embed) |
| 9 | `file_modified_at` | `timestamptz` | YES | NULL | Source file mtime |
| 10 | `doc_source` | `varchar` | YES | NULL | Source type (see enum below) |
| 11 | `project_name` | `varchar` | YES | NULL | Project name for `project`-source documents |
| 12 | `document_id` | `uuid` | YES | NULL | FK to `claude.documents` (may be NULL) |
| 13 | `token_count` | `integer` | YES | NULL | Estimated token count of chunk |
| 14 | `created_at` | `timestamptz` | YES | `NOW()` | First embed time |
| 15 | `updated_at` | `timestamptz` | YES | `NOW()` | Last re-embed time |

**Embedding dimension evolution**: Originally `vector(768)` with Ollama nomic-embed-text (2025-12-30). Migrated to `vector(1024)` with Voyage AI voyage-3 between Dec 2025 and Feb 2026.

---

## Unique Constraint

`UNIQUE(doc_path, chunk_index)` — the UPSERT in `embed_vault_documents.py` updates existing chunks in-place when file content changes.

---

## doc_source Values

| Value | Description |
| --- | --- |
| `vault` | Obsidian knowledge-vault documents (majority) |
| `project` | Project CLAUDE.md, ARCHITECTURE.md, etc. |
| `global` | Global standards/instructions |
| `awesome-copilot` | GitHub Copilot agent definitions (excluded from RAG queries) |

---

## Indexes

| Index | Type | Columns | Purpose |
| --- | --- | --- | --- |
| `vault_embeddings_pkey` | btree (PK) | `embedding_id` | PK |
| `vault_embeddings_vector_idx` | hnsw | `embedding vector_cosine_ops` | Semantic search (primary) |
| `idx_ve_doc_path` | btree | `doc_path` | Document path lookup |
| `idx_ve_chunk` | btree | `(doc_path, chunk_index)` | Unique constraint |
| `idx_ve_doc_source` | btree | `doc_source` | Source filtering |
| `idx_ve_document_id` | btree | `document_id` | FK lookup |

HNSW is used for vault_embeddings (as originally created 2025-12-30). Other tables in the schema use ivfflat.

---

## Foreign Keys

| Column | References | On Delete |
| --- | --- | --- |
| `document_id` | `claude.documents.doc_id` | SET NULL (likely, column is nullable) |

The `document_id` linkage to `claude.documents` may be NULL for many rows — the pipeline may not populate this FK on every embed. This is unconfirmed and needs a live query.

---

## Embedding Pipeline (`scripts/embed_vault_documents.py`)

| Parameter | Value |
| --- | --- |
| Chunk size | 1000 characters |
| Chunk overlap | 200 characters |
| Model | Voyage AI `voyage-3` |
| Input type | `"document"` |
| Incremental | Yes — skips file if SHA-256 hash unchanged |
| Exclusion | `awesome-copilot-reference/` entirely excluded |

**Chunk boundary logic**: Prefers sentence-ending punctuation (`. `, `! `, `? `, `\n\n`) for cleaner semantic chunks.

---

## RAG Query Pattern

The `rag_query_hook.py` queries this table on every UserPromptSubmit event:

```sql
SELECT doc_path, doc_title, chunk_text, 1 - (embedding <=> %s::vector) AS similarity_score
FROM claude.vault_embeddings
WHERE doc_path NOT LIKE '%%awesome-copilot%%'
  AND (doc_source IS NULL OR doc_source != 'awesome-copilot')
ORDER BY embedding <=> %s::vector
LIMIT %s
```

The query embedding is generated with input_type `"query"` (vs `"document"` for stored chunks) as required by Voyage AI's asymmetric retrieval design.

---

## Volume Estimates

- 9,655 chunks at ~1000 chars each ≈ ~9.7 million characters of indexed text
- Implied unique documents: 9,655 / avg_chunks_per_doc. At ~5 chunks/doc ≈ 1,931 distinct documents.
- `claude.documents` has 5,940 entries (larger — includes non-embedded project/config docs)
- Average token count per chunk: ~250 tokens (1000 chars / 4 chars per token)

---

## METIS Assessment Notes

**Strength**: Largest and most consistently populated semantic index. 100% embedding coverage (NOT NULL constraint on `embedding`). The HNSW index provides sub-millisecond nearest-neighbor lookup.

**Gap**: No FK link back to `claude.knowledge`. A knowledge entry derived from a vault document has no pointer to the source chunk. Provenance is lost.

**Gap**: `document_id` linkage to `claude.documents` may be sparse — the pipeline may create `documents` records but not always populate the FK in `vault_embeddings`. Needs verification.

**Gap**: RAG queries `awesome-copilot` exclusion is applied in SQL but could silently break if `doc_source` is NULL (handled with `IS NULL` check in WHERE clause).

---

## Source Code References

- `scripts/embed_vault_documents.py` lines 202–291 (full embedding pipeline)
- `scripts/rag_query_hook.py` lines 1640–1704 (RAG query + rag_usage_log write)
- `docs/SESSION_SUMMARY_2025-12-30.md` lines 127–142 (original table DDL)

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-vault-embeddings.md
