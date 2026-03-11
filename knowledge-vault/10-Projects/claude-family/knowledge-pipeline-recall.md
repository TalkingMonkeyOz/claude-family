---
projects:
- claude-family
tags:
- knowledge-pipeline
- recall
- rag
- cognitive-memory
synced: false
---

# Knowledge Pipeline — Part 2: Recall and RAG Injection

Index: [[knowledge-pipeline-analysis]]
Prev: [[knowledge-pipeline-ingest]]
Next: [[knowledge-pipeline-lifecycle]]

---

## tool_recall_knowledge() — server.py:1007

### What it does

Semantic search over `claude.knowledge` using pgvector cosine similarity. Returns
up to `limit` results sorted by similarity descending. Updates `last_accessed_at`
and `access_count` for every returned row. Does NOT call `mark_knowledge_applied()`.

### Quality Gates on Retrieval

- Requires `embedding IS NOT NULL` — rows without embeddings are invisible.
- Default `min_similarity=0.5`.
- Does NOT filter by `tier` — returns mid, long, and archived entries.
- **Gap**: No `AND tier != 'archived'` filter. Archived entries with high embedding
  similarity to a query will be returned.

### Available Filters

All optional: `knowledge_type`, `project`, `min_similarity`, `domain` (ILIKE on
`knowledge_category`), `source_type` (ILIKE on `source`), `tags` (ILIKE hack on
`knowledge_category` — no actual tags column exists), `date_range_days`.

**Gap**: Tags filtering matches `knowledge_category` via ILIKE. The `tags`
parameter is documented but `claude.knowledge` has no tags array column.

---

## tool_recall_memories() — server.py:1548

### What it does

The preferred 3-tier retrieval function. Executes three sequential queries (SHORT,
MID, LONG) in one connection, then applies budget caps. Performs a 1-hop graph
walk from long-tier seed results via `knowledge_relations`.

### Budget Profiles (server.py:1563-1568)

```python
profiles = {
    "task_specific": {"short": 0.40, "mid": 0.40, "long": 0.20},
    "exploration":   {"short": 0.10, "mid": 0.30, "long": 0.60},
    "default":       {"short": 0.20, "mid": 0.40, "long": 0.40},
}
```

Default 1000-token budget splits 200/400/400 by tier.

### Composite Scoring (server.py:1650-1656)

Mid-tier:
```
score = sim * 0.4 + recency * 0.3 + access_freq * 0.2 + conf * 0.1
```
- `recency = max(0, 1.0 - days_since_access / 90.0)`
- `access_freq = min(times_applied / 10.0, 1.0)`
- `conf = confidence_level / 100.0`

Long-tier uses same formula with `days / 180.0` for recency.

Gap: Similarity dominates at 40%. A recently created junk entry with high
embedding similarity will outscore an old high-confidence pattern if the junk is
slightly more topically similar.

### Similarity Thresholds

- MID tier: hardcoded `0.4` (server.py:1641) — lower than recall_knowledge default.
- LONG tier: hardcoded `0.35` (server.py:1685) — even lower. Long-tier assumed
  higher quality, but no ingestion gate enforces that.

### Budget Enforcement

Each tier gets its own budget; there is no cross-tier total cap enforced. The
function can return up to 3x the `budget` parameter in tokens in edge cases.
The "1+ per tier diversity guarantee" mentioned in the docstring is implicit, not
enforced in code.

### Access Tracking

Updates `last_accessed_at` and `access_count` for mid/long results (server.py:1756-1763).
Does NOT call `mark_knowledge_applied()`.

---

## RAG Hook: query_knowledge() — rag_query_hook.py:959

### What it does

Queries `claude.knowledge` via pgvector. Parameters: `top_k=3`,
`min_similarity=0.55`. Calls `claude.graph_aware_search()` SQL function first
(graph-aware walk); falls back to direct pgvector query on error.

### Archived Exclusion

`query_knowledge()` does exclude archived via `COALESCE(tier, 'mid') != 'archived'`
(line 1013). This is correct, and is more careful than `tool_recall_knowledge()`.

### Access Tracking

Updates `last_accessed_at` and `access_count` (line 1034-1036). Does NOT call
`mark_knowledge_applied()`. The hook has no way to know whether the injected
knowledge was actually used or useful.

---

## RAG Hook: main() injection pipeline — rag_query_hook.py:1927

### Context Budget

`MAX_CONTEXT_TOKENS = 3000` (line 86). Priority 0 blocks are always included;
priority 1-9 are dropped when budget is exceeded.

```
Priority 0 (pinned):
  - Core protocol (task discipline)
  - Critical session facts (credential/endpoint/config/decision types)
  - Context health warning

Priority 1-9 (trimmable):
  1. Process failures
  2. WCC context (replaces 4-9 when active)
  3. Config warning
  4. Knowledge graph results
  5. Vault RAG results
  6. Skill suggestions
  7. Schema context
  8. Design map
  9. Nimbus context
```

### When RAG Fires (needs_rag — line 676)

- Prompts < 15 chars: always skip.
- Question indicators (`?`, `how do`, `what is`, etc.): always run.
- Action indicator as first word: skip unless prompt > 50 chars AND contains
  embedded question signals.
- Default: run only if prompt > 100 characters.

`is_command()` (line 597) provides a fast-path bypass for short imperative
commands, including core protocol injection.

### WCC Override (line 2090-2091)

When the Work Context Container (WCC) is active, knowledge graph, vault RAG,
nimbus context, and schema context queries are all skipped. WCC pre-assembles
context from those sources for the detected activity.

---

## RAG Hook: query_vault_rag() — rag_query_hook.py:1574

Queries `claude.vault_embeddings` (Obsidian markdown documents). Separate from
the `claude.knowledge` table. `min_similarity=0.45`, `top_k=3`. Deduplicates
results by `doc_path` (keeps highest-similarity chunk per document). Logs to
`claude.rag_usage_log`. Processes implicit feedback signals.

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/claude-family/knowledge-pipeline-recall.md
