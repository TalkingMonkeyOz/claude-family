---
projects:
- claude-family
- project-metis
tags:
- recommendations
- implementation
- roadmap
synced: false
---

# Memory System Implementation Roadmap

Derived from [[research-external-memory-systems]].

## Phase 1: Immediate (2-4 weeks)

### 1. Automatic Fact Extraction (Mem0 Pattern)
On session end, send conversation to LLM: "Extract 5 most important facts, decisions, and patterns for future sessions." Store via `remember()`.

**Impact**: Eliminates manual capture burden; matches Mem0 production approach.

### 2. Upgrade pgvector to 0.8+
Enable iterative index scans:
```sql
SET hnsw.iterative_scan = relaxed_order;
```

Fixes filtered HNSW query reliability.

### 3. Add Hybrid BM25+Vector Search
Add tsvector column + GIN index to `claude.knowledge`. Implement RRF fusion in recall queries.

**Expected improvement**: 15-30% better retrieval accuracy.

## Phase 2: Medium-term (1-2 months)

### 4. Semantic Lossless Compression (SimpleMem Pattern)
Implement three-stage pipeline:

1. **Entropy-aware filtering** — Store only if `new_info > 0.25`
2. **Recursive consolidation** — Merge related memories asynchronously
3. **Adaptive retrieval** — Adjust result count by query complexity

**Impact**: 26.4% F1 improvement over baseline, 30x fewer tokens.

### 5. Simplify to 3-5 Tools
Replace 15+ overlapping mechanisms:
- `remember(content)` — Store with auto-dedup, auto-link
- `recall(query)` — Hybrid search, budget-capped
- `dossier(topic)` — Topic-based knowledge organization (see [[research-dossier-pattern]])
- `forget(id_or_query)` — Remove outdated knowledge
- `consolidate()` — Maintenance (auto, or manual trigger)

## Phase 3: Long-term (2-3 months)

### 6. pg_cron for Autonomous Maintenance
Schedule consolidation/decay/promotion runs (3 AM daily). Removes dependency on Claude sessions.

### 7. Consider ParadeDB pg_search (Optional)
If tsvector ranking proves insufficient, add ParadeDB for native BM25.

## What NOT to Do

Do not adopt Neo4j, Redis, external vector stores, or separate search engines. Our PostgreSQL + pgvector stack is sufficient.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research\implementation-roadmap.md
