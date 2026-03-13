---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- unified
- retrieval
synced: false
---

# Unified Storage Design — Retrieval, Maintenance, and Migration

**Parent**: [design-unified-storage.md](../../../docs/design-unified-storage.md)

---

## Retrieval Redesign

**Current**: 3 parallel search paths in `rag_query_hook.py` (vault RAG, knowledge recall, workfile search). No deduplication. Results concatenated, often redundant.

**New**: Single `recall()` path with hybrid BM25+vector RRF fusion.

### Schema changes

```sql
-- tsvector column on knowledge
ALTER TABLE claude.knowledge ADD COLUMN search_vector tsvector;
CREATE INDEX idx_knowledge_search ON claude.knowledge USING gin(search_vector);

-- tsvector column on workfiles (dossiers)
ALTER TABLE claude.project_workfiles ADD COLUMN search_vector tsvector;
CREATE INDEX idx_workfiles_search ON claude.project_workfiles USING gin(search_vector);

-- Auto-populate trigger
CREATE OR REPLACE FUNCTION update_search_vector() RETURNS trigger AS $$
BEGIN
  NEW.search_vector := to_tsvector('english', NEW.content);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_knowledge_sv BEFORE INSERT OR UPDATE OF content
  ON claude.knowledge FOR EACH ROW EXECUTE FUNCTION update_search_vector();
CREATE TRIGGER trg_workfiles_sv BEFORE INSERT OR UPDATE OF content
  ON claude.project_workfiles FOR EACH ROW EXECUTE FUNCTION update_search_vector();

-- Backfill existing rows
UPDATE claude.knowledge SET search_vector = to_tsvector('english', content)
  WHERE search_vector IS NULL;
UPDATE claude.project_workfiles SET search_vector = to_tsvector('english', content)
  WHERE search_vector IS NULL;
```

### RRF fusion query

Reciprocal Rank Fusion with k=60 (standard parameter). Single SQL query with CTEs.

```sql
WITH vault_hits AS (
  SELECT id, 'vault' AS source, content,
    ROW_NUMBER() OVER (ORDER BY embedding <=> $1) AS rank_vec
  FROM claude.vault_embeddings
  WHERE embedding <=> $1 < 0.7
  LIMIT 20
),
knowledge_hits AS (
  SELECT id, 'knowledge' AS source, content,
    ROW_NUMBER() OVER (ORDER BY embedding <=> $1) AS rank_vec,
    ROW_NUMBER() OVER (
      ORDER BY ts_rank(search_vector, to_tsquery('english', $2)) DESC
    ) AS rank_bm25
  FROM claude.knowledge
  WHERE confidence > 20 AND tier != 'archived'
    AND (embedding <=> $1 < 0.7 OR search_vector @@ to_tsquery('english', $2))
  LIMIT 20
),
dossier_hits AS (
  SELECT id, 'dossier' AS source, content,
    ROW_NUMBER() OVER (ORDER BY embedding <=> $1) AS rank_vec,
    ROW_NUMBER() OVER (
      ORDER BY ts_rank(search_vector, to_tsquery('english', $2)) DESC
    ) AS rank_bm25
  FROM claude.project_workfiles
  WHERE title != '_index'
    AND (embedding <=> $1 < 0.7 OR search_vector @@ to_tsquery('english', $2))
  LIMIT 20
),
fused AS (
  SELECT source, content,
    1.0/(60 + rank_vec) AS score_vec, 0 AS score_bm25
  FROM vault_hits
  UNION ALL
  SELECT source, content,
    1.0/(60 + rank_vec), 1.0/(60 + rank_bm25)
  FROM knowledge_hits
  UNION ALL
  SELECT source, content,
    1.0/(60 + rank_vec), 1.0/(60 + rank_bm25)
  FROM dossier_hits
)
SELECT source, content, SUM(score_vec + score_bm25) AS rrf_score
FROM fused GROUP BY source, content
ORDER BY rrf_score DESC LIMIT 10;
```

Parameters: `$1` = query embedding (vector), `$2` = tsquery string.

### RAG hook simplification

Current `rag_query_hook.py` has 4 parallel branches. Replace with:
1. Classify prompt (action vs question) -- keep existing classifier
2. If question: call `recall()` internally (single path)
3. Inject results with source labels
4. Done. One code path instead of four.

---

## Promotion and Maintenance

**Current broken pipeline**: 3 tiers, promotion requires `access_count >= 5 AND age >= 7d`, 96% never promoted.

**New approach**: No explicit tiers. Confidence score handles everything.

| Event | Confidence Change |
|-------|-------------------|
| Created via `remember()` | Set to 50 |
| Returned by `recall()` to Claude | +5, cap 100 |
| Duplicate detected and merged | +10 to surviving entry |
| 30 days without access | * 0.95 per month |
| Explicit `forget()` | Set to 0, archived |
| Below 20 after 90 days no access | Auto-archived |

### Entropy gate (SimpleMem-inspired)

Before storing via `remember()`:

```python
max_sim = get_max_cosine_similarity(new_embedding, project_id)
if max_sim > 0.75:
    # Near-duplicate. Update existing entry, don't create new.
    existing = get_most_similar_entry(new_embedding, project_id)
    merged = merge_content(existing.content, new_content)
    update_entry(existing.id, merged, confidence=existing.confidence + 10)
else:
    # Genuinely new information. Store it.
    insert_entry(new_content, confidence=50, embedding=new_embedding)
```

This prevents the 930-row MID tier accumulation problem. Near-duplicates merge instead of piling up.

### pg_cron autonomous maintenance

```sql
SELECT cron.schedule('storage-maintenance', '0 3 * * *', $$
  -- 1. Decay stale entries
  UPDATE claude.knowledge
  SET confidence = GREATEST(confidence * 0.95, 0)
  WHERE last_accessed < now() - interval '30 days'
    AND confidence > 20 AND tier != 'archived';

  -- 2. Archive entries below threshold
  UPDATE claude.knowledge
  SET tier = 'archived'
  WHERE confidence < 20
    AND last_accessed < now() - interval '90 days'
    AND tier != 'archived';

  -- 3. Log maintenance run
  INSERT INTO claude.audit_log (entity_type, entity_id, action, details)
  VALUES ('system', 'maintenance', 'consolidate',
    json_build_object('timestamp', now()));
$$);
```

No dependency on Claude sessions. System maintains itself.

---

## Migration Plan

| Phase | Week | Changes | Risk |
|-------|------|---------|------|
| **0: Cleanup** | Now | DROP: mcp_usage, enforcement_log, workflow_state, knowledge_retrieval_log, activities | None. All dead. |
| **1: Foundation** | 1 | Add tsvector columns + triggers + indexes. Backfill rows. | Low. Additive. |
| **2: Dossier** | 2 | Implement `dossier()` in project-tools. Add to Core Protocol. Create BPMN. | Medium. New tool. |
| **3: Retrieval** | 2 | Implement `recall()` with RRF. Simplify RAG hook to single path. | Medium. Core change. |
| **4: Remember fix** | 3 | Remove tier routing. Add entropy gate. Deploy `forget()`. Backfill confidence. | Low. Behavioral. |
| **5: Task fix** | 3 | `source` column on todos. Closure gate. Completion ratio in startup. | Low. Additive. |
| **6: Deprecate** | 4 | Mark old tools deprecated. Remove from CLAUDE.md tool index. Keep functional 30d. | Low. Soft. |
| **7: Maintenance** | 4 | Deploy pg_cron job. Remove session-dependent consolidation. | Low. Replaces manual. |

### Rollback strategy

Each phase is independently reversible:
- tsvector columns are additive (no existing columns changed)
- New tools are additive (old tools kept 30 days)
- pg_cron job unscheduled with one command
- Dossier built on existing workfiles table (no schema migration)

### Validation criteria

| Phase | Success metric |
|-------|---------------|
| 2 | 5+ dossiers created in first week of use |
| 3 | recall() returns relevant results for 80%+ of test queries |
| 4 | Knowledge table growth rate drops 50% (entropy gate working) |
| 5 | Task closure rate visible in startup, trending upward |
| 7 | pg_cron runs daily without manual intervention for 2 weeks |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/design-storage-retrieval.md
