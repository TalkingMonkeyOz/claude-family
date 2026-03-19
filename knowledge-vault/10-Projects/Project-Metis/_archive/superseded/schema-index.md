---
projects:
- project-metis
- claude-family
tags:
- research
- data-model
- knowledge-engine
- schema
synced: false
---

# Metis Data Model Research: Schema Index

**Purpose**: Index for the 7-table knowledge schema analysis supporting the METIS Knowledge Engine data model assessment.

**Research method**: Static code analysis of `server.py`, `server_v2.py`, `embed_vault_documents.py`, SQL migration files, hook scripts, and the 2026-02-28 Table Code Reference Map audit. Row counts are from that audit unless noted.

**Database**: `ai_company_foundation`, schema `claude`

---

## Table Summary

| Table | Rows (audit) | Embed dim | Status | Detail File |
| --- | --- | --- | --- | --- |
| `claude.knowledge` | 717 | 1024 (voyage-3) | Active, growing | [[schema-knowledge]] |
| `claude.knowledge_relations` | 67 | — | Active, sparse graph | [[schema-knowledge-relations]] |
| `claude.knowledge_retrieval_log` | 77 | — | Frozen (legacy writer retired) | [[schema-knowledge-retrieval-log]] |
| `claude.session_facts` | 394 | — | Active | [[schema-session-facts]] |
| `claude.vault_embeddings` | 9,655 | 1024 (voyage-3) | Active, largest table | [[schema-vault-embeddings]] |
| `claude.documents` | 5,940 | — | Active, partially deprecated | [[schema-documents]] |
| `claude.project_workfiles` | ~new (2026-03-09) | 1024 (voyage-3) | New, growing | [[schema-project-workfiles]] |

---

## Architecture Overview

### Three Semantic Search Indexes (Same Embedding Space)

All three semantic tables use Voyage AI `voyage-3` at 1024 dimensions:

| Table | Index Type | Reader |
| --- | --- | --- |
| `vault_embeddings` | hnsw | `rag_query_hook.py` (every prompt) |
| `knowledge` | ivfflat | `recall_memories()`, `recall_knowledge()` |
| `project_workfiles` | ivfflat | `search_workfiles()`, WCC assembly |

### 3-Tier Memory Model Mapping

| Tier | Storage | Writer | Reader |
| --- | --- | --- | --- |
| SHORT | `session_facts` | `store_session_fact()`, `remember()` short-path | `recall_memories()` short budget |
| MID | `knowledge` WHERE `tier='mid'` | `remember()`, `end_session()`, `store_knowledge()` | `recall_memories()` mid budget |
| LONG | `knowledge` WHERE `tier='long'` + `knowledge_relations` 1-hop | `remember()` pattern/gotcha types | `recall_memories()` long budget |
| ARCHIVED | `knowledge` WHERE `tier='archived'` | `consolidate_memories()` decay | Not retrieved |

### Session Lifecycle Intersections

```
SessionStart       → reads session_facts (pinned) + project_workfiles (is_pinned=true)
Each prompt        → vault_embeddings (RAG hook) + knowledge + session_facts + workfiles (WCC)
remember()         → short→session_facts | mid/long→knowledge + knowledge_relations (auto-link)
recall_memories()  → session_facts + knowledge(mid) + knowledge(long) + knowledge_relations
SessionEnd         → consolidate_memories() promotes tiers; end_session() writes knowledge(mid)
```

---

## Key Findings for METIS Assessment

### Strengths

1. **Unified embedding space** — all three semantic tables share the same model and dimension, enabling cross-table semantic search without re-embedding.
2. **Tiered lifecycle** — `knowledge.tier` with automated promotion/decay via `consolidate_memories()`.
3. **Idempotent writes** — `session_facts` and `project_workfiles` use deterministic conflict keys for safe upsert.
4. **Usage tracking** — `times_applied`, `access_count`, `last_accessed_at` support relevance scoring and decay.

### Gaps (Detailed in [[schema-assessment-gaps]])

1. `knowledge_retrieval_log` is frozen — no observability for current `recall_memories()` calls.
2. Knowledge graph is very sparse (67 edges / 717 nodes = 9.3% density).
3. No FK linkage between `knowledge` and `vault_embeddings` — no provenance tracing.
4. `documents` table has deprecated columns (`project_id`, `category`) not yet removed.
5. Embedding failures are silent — entries stored without vectors are invisible to semantic search.
6. `session_facts` cross-session recovery limited to N previous sessions (default 3).
7. `knowledge_relations` has no provenance metadata (which session, which code path created the edge).

---

## Recommended Live Queries Before METIS Design

Run these before finalizing the METIS data model:

```sql
-- 1. Tier distribution in knowledge
SELECT tier, knowledge_type, count(*), avg(confidence_level)::int AS avg_confidence
FROM claude.knowledge GROUP BY tier, knowledge_type ORDER BY count(*) DESC;

-- 2. Relation type distribution
SELECT relation_type, count(*), avg(strength)::numeric(3,2) AS avg_strength
FROM claude.knowledge_relations GROUP BY relation_type ORDER BY count(*) DESC;

-- 3. Fact type distribution
SELECT fact_type, count(*) FROM claude.session_facts GROUP BY fact_type ORDER BY count(*) DESC;

-- 4. Vault embedding aggregate
SELECT count(*) AS chunks, count(DISTINCT document_id) AS with_doc_id,
       avg(token_count)::int AS avg_tokens FROM claude.vault_embeddings;

-- 5. Workfile component breakdown
SELECT component, count(*), max(access_count)
FROM claude.project_workfiles GROUP BY component ORDER BY count(*) DESC;

-- 6. Embedding coverage in knowledge
SELECT count(*) FILTER (WHERE embedding IS NOT NULL) AS with_embed,
       count(*) FILTER (WHERE embedding IS NULL) AS without_embed FROM claude.knowledge;

-- 7. Retrieval log date range
SELECT count(*), min(created_at), max(created_at) FROM claude.knowledge_retrieval_log;
```

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-index.md
