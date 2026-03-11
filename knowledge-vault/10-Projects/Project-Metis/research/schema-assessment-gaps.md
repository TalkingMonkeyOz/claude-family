---
projects:
- project-metis
- claude-family
tags:
- research
- assessment
- data-model
- knowledge-engine
synced: false
---

# Schema Assessment: Gaps and METIS Design Implications

Back to [[schema-index]]

**Purpose**: Consolidated gaps, risks, and opportunities identified across all 7 tables. Supports METIS Knowledge Engine data model design decisions.

---

## Critical Gaps

### G1: No Retrieval Observability for `recall_memories()`

`claude.knowledge_retrieval_log` is frozen at 77 rows (last write from retired `process_router.py`). The current `recall_memories()` tool updates `knowledge.access_count` and `last_accessed_at` but writes no structured log.

**Impact**: METIS cannot answer:
- Which knowledge entries are retrieved most (beyond checking `access_count`)?
- What query patterns trigger the 3-tier system?
- How often does each tier contribute to results?
- What is the latency distribution for retrieval?

**Options**:
1. Reactivate `knowledge_retrieval_log` with new columns (`tiers_queried`, `query_type`, `tier_results_count`).
2. Add a log write inside `tool_recall_memories()` in `server.py`.
3. Create a new `cognitive_retrieval_log` table with a cleaner schema.

---

### G2: No Provenance Link Between `knowledge` and `vault_embeddings`

A knowledge entry created from a vault document (via `extract_insights()` or manual `remember()`) has no FK pointer to the source vault chunk. The `knowledge.source` column stores free-text strings like `session:<uuid>` or `conversation:<id>` — not vault document paths.

**Impact**: METIS cannot:
- Trace a knowledge entry back to its source document.
- Identify which vault documents have contributed knowledge.
- Detect when a source document is updated and the corresponding knowledge entry may be stale.

**Recommended fix**: Add `source_doc_path text` and `source_chunk_id uuid` nullable columns to `claude.knowledge`, populated when `extract_insights()` is used to generate knowledge from vault content.

---

### G3: Knowledge Graph is Very Sparse

67 edges across 717 nodes = 9.3% edge:node ratio. The auto-link window (0.50–0.85 cosine similarity) and per-entry limit (3 auto-links) result in most knowledge entries having no graph connections.

**Impact**: The 1-hop graph walk in `recall_memories()` rarely adds useful entries. The graph adds complexity without meaningful benefit at current scale.

**Options**:
1. Lower the auto-link similarity threshold to 0.40 to create more edges.
2. Switch from auto-linking at write time to a batch graph construction pass.
3. Add entity extraction and entity-to-knowledge linking for stronger structural connections.
4. Accept sparse graph at current scale — revisit when knowledge entries exceed 5,000.

---

### G4: Silent Embedding Failures

When Voyage AI is unavailable, both `knowledge` entries and `project_workfiles` are stored without embeddings. These entries are completely invisible to semantic search — they can only be found by exact text queries.

**Impact**: Unknown number of knowledge entries (possibly 5–15%) lack embeddings. Semantic search quality degrades silently.

**Recommended fix**: A background backfill job that queries `WHERE embedding IS NULL AND created_at < NOW() - interval '1 hour'` and generates embeddings in batches. Add a monitoring alert if `count(WHERE embedding IS NULL)` exceeds 50.

---

### G5: `session_facts` Cross-Session Recovery is Session-Count Dependent

`recall_previous_session_facts()` scans back N sessions (default 3). A project with frequent short sessions loses facts faster than a project with infrequent long sessions.

**Impact**: Critical facts (credentials, decisions) stored in session 1 may be unreachable by session 5 without any time-based signal.

**Recommended fix**: Add a `is_important` flag (boolean) to `session_facts` that lifts the fact into a "persistent important facts" bucket immune to session-count decay. Alternatively, auto-promote `decision` and `credential` type facts to `claude.knowledge` at session end.

---

## Schema Design Issues

### D1: `claude.documents` Deprecated Columns

| Column | Issue | Recommended Action |
| --- | --- | --- |
| `project_id` | Deprecated in favor of `document_projects` junction table; 293 rows still use it | Migrate, then DROP COLUMN |
| `category` | Redundant lowercase copy of `doc_type` | DROP COLUMN (compute from `doc_type` when needed) |

### D2: Missing DB Constraints on `documents`

Two consistency rules are enforced only at the application layer:
- `status='ARCHIVED'` should require `is_archived=true`
- `is_archived=true` should require `archived_at IS NOT NULL`

Neither has a DB CHECK constraint. Direct SQL writes can violate these rules silently.

### D3: `knowledge_relations` Has No Provenance

The edge table records relation type and strength but not:
- Which session created the relation
- Whether it was auto-linked or manually created
- Which feature or task was active when it was created

This makes graph curation and quality auditing impossible.

---

## Opportunities for METIS

### O1: Unified 1024-Dimension Embedding Space

All three semantic tables (`vault_embeddings`, `knowledge`, `project_workfiles`) use Voyage AI voyage-3 at 1024 dimensions. Cross-table semantic search is theoretically possible without re-embedding. METIS could implement a unified search that queries all three in a single pass and merges results by cosine similarity.

### O2: `project_workfiles` is the Cleanest Table

The newest table has no deprecated columns, clear semantics, good indexing, and BPMN coverage. It is the best candidate for METIS to extend or build new patterns on top of.

### O3: `knowledge.times_applied` and `access_count` Enable Learning

These usage tracking columns support reinforcement-style knowledge management. METIS could implement confidence boosting for frequently accessed entries and faster decay for rarely accessed ones — creating a self-organizing memory.

### O4: `knowledge_relations.strength` Enables Weighted Traversal

The current graph walk uses a binary threshold (strength >= 0.3). METIS could implement weighted PageRank-style propagation using `strength` as edge weights to find more relevant connected knowledge.

---

## Recommended Live Queries Before METIS Design

See [[schema-index]] section "Recommended Live Queries Before METIS Design" for the exact SQL to run.

Key unknowns that require live data:
1. Exact `tier` distribution in `knowledge` (mid vs long vs archived counts)
2. `relation_type` distribution (confirm `relates_to` dominance)
3. `fact_type` distribution in `session_facts` (confirm `note` is most common)
4. `document_id` NULL rate in `vault_embeddings` (critical for provenance assessment)
5. `project_workfiles` current row count (table is new)
6. Embedding NULL rate in `knowledge`

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-assessment-gaps.md
