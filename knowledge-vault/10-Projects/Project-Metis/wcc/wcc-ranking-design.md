---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - domain/work-context-container
  - domain/retrieval
  - type/design
created: 2026-03-11
updated: 2026-03-11
status: active
---

# WCC Ranking & Assembly — Design

Parent: [[work-context-container-design]]
Detail: [[wcc-ranking-agentic-routing]]

The ranking and assembly subsystem answers: given all candidate knowledge chunks across 6 sources, which ones go into the context window? This is the librarian's selection decision, made on every prompt where activity-scoped retrieval is active.

---

## The Core Problem with CF's Approach

CF has three retrieval paths for the same knowledge store with different scoring, different thresholds, and no deduplication:

| Path | Code Location | Min Similarity | Scoring |
|------|--------------|----------------|---------|
| `recall_memories()` | server.py MCP tool | 0.5 | Tier weight + similarity |
| `query_knowledge_graph()` | rag_query_hook.py | 0.35 | Similarity only |
| `query_knowledge()` | rag_query_hook.py (fallback) | 0.5 | Similarity + recency |

The same knowledge entry can be retrieved by all three paths, scored differently, and appear multiple times in the context window. The 400-600ms query latency is this: sequential execution across overlapping paths.

**METIS fix**: One retrieval path. All sources feed it. One ranking function. One dedup step. One budget cap.

---

## Single Retrieval Path

```
retrieve_and_rank(prompt, activity, tenant_id, budget_tokens) → ranked_chunks[]

1. Embed prompt (Voyage AI, cache 5 min)
2. Query all active sources in PARALLEL:
   a. persistent_knowledge WHERE linked to activity OR cosine_sim >= 0.50
   b. knowledge_chunks (types per activity.linked_knowledge_types) cosine_sim >= 0.45
   c. activity_workfiles WHERE activity_id = current_activity
   d. delivery_cache WHERE feature_id IN activity.linked_features
3. Collect all candidates into single list
4. Score each with composite_score()
5. Deduplicate by content_hash (keep higher-scored copy)
6. Sort by composite_score DESC
7. Apply budget cap (greedy fill + diversity constraint)
8. Return ranked_chunks[]
```

Steps 2a-2d execute in parallel. Measured parallel latency: 80-120ms vs 400-600ms sequential. Target: end-to-end < 200ms. Connection pooling: one shared connection per retrieval operation (not one per source query).

---

## 6 Ranking Signals

### Signal 1: Vector Similarity
Cosine distance via pgvector `<=>` operator (HNSW index). Range 0-1. Chunks below 0.45 excluded at query time. Primary relevance signal.

### Signal 2: Co-Access Frequency
Items retrieved together in the same assembly, tracked in `co_access_log`. Schema: `(session_id, prompt_hash, chunk_ids[], retrieved_at, tenant_id)`. For candidate C, score = frequency C appeared alongside current candidate set, normalised by total retrieval count. Bootstraps to zero — signal strengthens after ~100 retrievals per activity. Library science principle: materials found together are related, even when embeddings disagree.

### Signal 3: Freshness Score
`freshness_score` (0.0-1.0) on every chunk. Event-driven, not time-driven:
- Created: 1.0
- Source document changed (different hash): 0.5
- Human re-verified: 1.0
- Superseded by newer chunk: 0.2
- Product release event with known impact: `max(0.3, current - 0.3)`

Stale content is penalised, not excluded — it may be the only content available.

### Signal 4: Recency of Retrieval
`last_retrieved_at` on each chunk (NOT `created_at` — CF's bug decays new content faster than old). Exponential decay: retrieved in last 24h = full bonus; not retrieved in 30+ days = near-zero. Tracks which knowledge is actively in use during the current project phase.

### Signal 5: Task Relevance
Binary boost (+0.15) if chunk is explicitly linked to the active activity or feature (`linked_knowledge` on activity, feature FK on chunk). Not a multiplier — ensures explicitly linked content always outranks similar-but-unlinked content.

### Signal 6: Retrieval Feedback
Running average per chunk adjusted by feedback events. Implicit: rephrasing (weak negative for prior assembly's chunks), task completion (positive for chunks in context). Explicit: "remember this" (strong positive), "that's wrong" (negative). Range 0.1-1.0. Neutral at launch — no effect until data accumulates.

---

## Composite Score Formula

```
composite_score =
    (0.55 × vector_similarity)
  + (0.30 × co_access_frequency)
  + (0.15 × task_relevance_boost)   ← binary: 0 or 0.15
  × freshness_score                  ← multiplier: 0.2 - 1.0
  × recency_factor                   ← multiplier: 0.5 - 1.0
  × feedback_factor                  ← multiplier: 0.1 - 1.0
```

Freshness, recency, and feedback are multipliers applied after additive signals. A stale, old, negatively-rated chunk cannot top the list regardless of similarity — these are trust signals, not relevance signals.

| Weight | Signal | Rationale |
|--------|--------|-----------|
| 0.55 | Vector similarity | Primary relevance; highest weight at launch (no co-access data yet) |
| 0.30 | Co-access frequency | Strong secondary — behavioural evidence of relatedness |
| 0.15 | Task relevance (binary boost) | Explicit link bonus — confirmed relevance, hard advantage |

After 3+ months per tenant, expect `w_co` to grow to 0.35-0.40 as co-access patterns stabilise.

---

## The Assembler: Budget-Capped Greedy Fill

Rank ALL candidates by composite score. Fill budget greedily from the top. Apply one diversity constraint.

```
assemble(ranked_chunks[], budget_tokens) → selected[]

greedy_fill:
  selected = [], used_tokens = 0
  for chunk in ranked_chunks DESC:
      if used_tokens + chunk.token_count <= budget_tokens:
          selected.append(chunk); used_tokens += chunk.token_count
      elif chunk.token_count < (budget_tokens * 0.1):
          selected.append(chunk); used_tokens += chunk.token_count

diversity_constraint:
  # Ensure >= 1 chunk from each of top-3 scoring sources
  top_3_sources = top 3 knowledge_types by their highest chunk score
  for source in top_3_sources not yet represented:
      if top unused chunk fits within budget * 1.05:
          selected.append(it)
```

The 5% overflow allowance prevents complete starvation of high-scoring sources that lost greedy competition due to token count. This replaces CF's per-source fixed budgets (25/25/15/10/15/10) — see [[wcc-ranking-agentic-routing]] for the full challenge argument.

**`token_count` is mandatory.** The assembler cannot function without it. Every stored item must know its cost before inclusion. This is the single most impactful schema requirement for METIS.

---

## Performance Targets

| Metric | CF Prototype | METIS Target | How |
|--------|-------------|-------------|-----|
| End-to-end retrieval | 400-600ms | < 200ms | Parallel queries + connection pool |
| DB queries (4 parallel) | 80-160ms total | < 100ms | HNSW index + pooled connection |
| Scoring + dedup | ~5ms | < 10ms | In-memory |
| Assembler | ~2ms | < 5ms | O(n) greedy fill |
| Cache hit | 0ms | 0ms | State file read |

---

*Parent: [[work-context-container-design]]*
*Detail: [[wcc-ranking-agentic-routing]] — Agentic routing triggers, per-source budget challenge*
*Related: [[wcc-activity-space-design]], [[library-science-research]]*

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/wcc-ranking-design.md
