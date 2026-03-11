---
tags:
  - project/Project-Metis
  - type/handoff
  - domain/data-model
  - from/claude-family
created: 2026-03-11
synced: false
---

# Data Model — Per-Table Assessments

Back to: [[handoff-data-model-response]]

---

## 1. `claude.session_facts` — THE WINNER

**652 rows across 93 sessions** | Distribution: decision (335), note (145), data (93), reference (34), config (21), credential (18), endpoint (6)

**Why it works**: Zero friction. `store_session_fact("key", "value")` is the simplest possible API. Claude uses it heavily because there's no schema to think about. Decisions dominate — Claude naturally captures "we decided X" moments.

**For METIS**: Add `tenant_id`, `token_count` (estimated), `ttl`/`expires_at` (facts never expire currently), `priority` (1-5) for budget-cap by importance, `task_state` type for task persistence.

**METIS mapping**: Layer 2 (Session Notebook).

---

## 2. `claude.knowledge` — CONCEPT RIGHT, EXECUTION STRUGGLING

**1,021 rows** | mid: 985 (96.5%), long: 36 (3.5%), short: 0

**Why mid is bloated**: Promotion requires `times_applied >= 3 AND confidence >= 80 AND access_count >= 5`. In practice `mark_knowledge_applied()` is rarely called so `times_applied` stays 0. Gate is too high.

**Implementation gaps**:
- Short tier unused (session_facts handles that separately)
- Cross-tier dedup missing (same knowledge can exist in mid AND as session_fact)
- Edge decay uses `created_at` not `last_accessed_at` — decays new faster than old
- Three retrieval paths query this table with different thresholds/scoring
- Consolidation logic duplicated in server.py AND startup hook (can silently diverge)

**For METIS**: Flatten to 2 tiers (session-scoped + persistent). Event-driven promotion (retrieve + task success = promote). Add `token_count`, `tenant_id`, `last_retrieved_at`. Don't require explicit `mark_knowledge_applied()`.

**METIS mapping**: Layer 4 (Persistent Knowledge) for patterns/gotchas. Layer 3 (Knowledge Retrieval) for reference material.

---

## 3. `claude.vault_embeddings` — RAG WORKHORSE

**9,655 chunks** | 13 columns | HNSW vector index on 1024-dim Voyage AI

**What works**: Incremental embed via file_hash, HNSW sub-ms lookup, sentence-boundary chunking, 100% embedding coverage.

**Critical gaps**:
- **No `token_count`** — assembler can't budget before loading. Violates "librarian knows cost" principle.
- **No `document_id` FK** — `doc_path` is only link. Orphans undetectable when files move.
- **No freshness scoring** — `updated_at` tracks embed time, not content freshness.
- **No quality scoring** — `rag_doc_quality` exists but retrieval never reads it. Write-only loop.
- **Fixed 1000-char chunks** — no content-type awareness. Code blocks and prose get same treatment.

**For METIS**: Add `token_count` (critical), `content_type`, `freshness_score`, `quality_score`. Content-aware chunking (markdown headers, code blocks, tables as boundaries). `tenant_id` per RBAC.

**METIS mapping**: Core store for Types 1 (Product Domain), 2 (API Reference), 4 (Process/Procedural).

---

## 4. `claude.knowledge_relations` — SPARSE, QUESTIONABLE VALUE

**211 edges for 1,021 nodes** (~0.2 edges/node) | Types: relates_to (~140), extends (~35), supports (~20), contradicts (~10), supersedes (~6)

**Honest assessment**: Built because knowledge graphs are theoretically appealing. With 211 edges, the 2-hop graph walk adds complexity for marginal retrieval improvement over pure vector search. Auto-generated `relates_to` edges from embedding similarity are redundant with... embedding similarity.

**For METIS**: Don't build a knowledge graph from day one. Start with pure vector similarity. If adding relations, make them explicit not auto-generated. Only edges that embeddings can't capture: `contradicts`, `supersedes`, `depends_on`. **Co-access tracking** (items retrieved together) is more valuable than pre-computed edges.

---

## 5. `claude.knowledge_retrieval_log` — BARELY USED

**77 rows** across 1,011 sessions | Tracks: prompt, keywords, results count/IDs, method, latency, session

**Problem**: RAG hook logs to `rag_usage_log` instead. `recall_memories()` doesn't log here. Three retrieval paths, three logging strategies, incomplete observability.

**For METIS**: One retrieval log, all paths. Add `was_useful` (feedback), `tokens_consumed` (cost), `retrieval_source` (which path). Wire from day one — can't improve ranking without measuring it.

---

## 6. `claude.documents` — OVER-ENGINEERED REGISTRY

**5,962 rows** | 18 columns (incl deprecated `project_id`, redundant `category`) | 16 doc types

**Honest assessment**: Designed as comprehensive doc management. In practice, populated by embed script, rarely queried directly. RAG queries `vault_embeddings` — never joins to `documents`. Exists in isolation from retrieval.

**For METIS**: Merge document metadata into chunk table (type, freshness, source, version as columns/JSONB). Or keep separate but actually USE it in retrieval (filter by type, boost by freshness). The many-to-many project pattern (`document_projects`) is correct for shared docs.

---

## 7. `claude.project_workfiles` — CLEANEST DESIGN, TOO NEW

**3 rows** (created 2026-03-09) | 16 columns, no deprecated fields, proper UPSERT

**Why I like it**: Filing cabinet metaphor is intuitive. UPSERT on `(project_id, component, title)` is idempotent. `linked_sessions` accumulates provenance. Partial index on `is_pinned=true` is smart. Append mode with separator.

**For METIS**: Add `token_count`, `source` (who wrote: user/Claude/pipeline), `content_hash`. Best candidate to evolve into Activity Space store — component maps naturally to activity scoping.

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/data-model-table-assessments.md
