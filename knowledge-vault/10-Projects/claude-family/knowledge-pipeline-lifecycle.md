---
projects:
- claude-family
tags:
- knowledge-pipeline
- lifecycle
- consolidation
- cognitive-memory
synced: false
---

# Knowledge Pipeline — Part 3: Lifecycle Management

Index: [[knowledge-pipeline-analysis]]
Prev: [[knowledge-pipeline-recall]]
Next: [[knowledge-pipeline-gaps]]

---

## tool_consolidate_memories() — server.py:2008

### What it does

Three-phase lifecycle operation controlled by `trigger` parameter:
- `session_end`: Phase 1 only (SHORT->MID promotion).
- `periodic`: Phase 2+3 (MID->LONG promotion, edge decay, archive).
- `manual`: All phases.

### Phase 1: SHORT to MID (server.py:2034-2096)

Finds session facts meeting all criteria:
- `fact_type IN ('decision', 'reference', 'note', 'data')`
- `LENGTH(fact_value) >= 50` — the only content-length quality gate in the
  entire pipeline.
- Session closed within 7 days, OR is the current session being closed.
- No existing knowledge entry with identical `title` AND `source='consolidation'`
  (title-only dedup — does not check embedding similarity).

The 50-character minimum is the only content-length gate anywhere. A 51-character
"agent1_complete: task finished, proceeding" would pass. Credential, config, and
endpoint fact types are correctly excluded.

Promoted entries receive: `tier='mid'`, `confidence=65`, `source='consolidation'`.
The MCP version generates embeddings for promoted entries. The session_end_hook
version does NOT (see below).

### Phase 2: MID to LONG (server.py:2098-2111)

```sql
UPDATE claude.knowledge
SET tier = 'long'
WHERE tier = 'mid'
  AND COALESCE(times_applied, 0) >= 3
  AND confidence_level >= 80
  AND COALESCE(access_count, 0) >= 5
```

Promotion criteria explained:
- `times_applied >= 3`: incremented only by `mark_knowledge_applied(success=True)`.
- `confidence_level >= 80`: starts at 65 for mid entries; each successful
  `mark_knowledge_applied` adds 1 point; dedup merges add 5 points.
- `access_count >= 5`: updated by every recall query.

**Critical gap**: `mark_knowledge_applied()` is never called anywhere. `times_applied`
stays at 0 or NULL for virtually every row. The `times_applied >= 3` gate is
permanently unreachable by organic usage.

Reaching confidence=80 from 65 without `mark_knowledge_applied()` requires either:
- 3 dedup merges via `remember()` (+5 each = 65+15=80), OR
- Manual intervention.

### Phase 3: Decay and Archive (server.py:2113-2136)

**Edge decay:**
```sql
UPDATE claude.knowledge_relations
SET strength = GREATEST(0.05, strength * POWER(0.95,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0))
WHERE strength > 0.05 AND created_at < NOW() - INTERVAL '7 days'
```
Formula: `0.95^days`. A 30-day-old edge at strength 1.0 decays to ≈0.21. Floor is 0.05.

**Archive:**
```sql
UPDATE claude.knowledge SET tier = 'archived'
WHERE tier IN ('mid', 'long')
  AND confidence_level < 30
  AND COALESCE(last_accessed_at, created_at) < NOW() - INTERVAL '90 days'
```

Since confidence starts at 65 and can only decrease via `mark_knowledge_applied(success=False)`,
which is never called, entries never drop below 30. Junk entries created at
confidence=65 persist indefinitely unless manually archived.

### When consolidate_memories() is Called Automatically

- `server_v2.py:end_session()` (line 1035): `trigger="session_end"` — Phase 1 only.
- **No automatic periodic call.** Phase 2+3 require explicit `trigger="periodic"`
  or `trigger="manual"`. No hook, scheduler, or startup check invokes this.

---

## tool_mark_knowledge_applied() — server.py:2582

### What it does

Increments `times_applied` and adds 1 to `confidence_level` on success.
Decrements `confidence_level` by 5 on failure, increments `times_failed`.

```sql
-- success=True:
SET times_applied = COALESCE(times_applied, 0) + 1,
    last_applied_at = NOW(),
    confidence_level = LEAST(100, COALESCE(confidence_level, 80) + 1)

-- success=False:
SET times_failed = COALESCE(times_failed, 0) + 1,
    confidence_level = GREATEST(0, COALESCE(confidence_level, 80) - 5)
```

### Why It Is Never Called

The function is correct. The gap is at the call-site level:
- `query_knowledge()` in the RAG hook updates `access_count` but not
  `times_applied`.
- `recall_memories()` updates `access_count` but not `times_applied`.
- The Core Protocol does not instruct Claude to call it after using knowledge.
- `recall_memories()` return values include `knowledge_id` but no reminder to
  call `mark_knowledge_applied()`.

Consequence: `times_applied` is 0 or NULL across the entire table. The confidence
feedback loop (success increases confidence, failure decreases) is entirely broken.
The MID->LONG promotion gate is permanently blocked.

---

## session_end_hook: Fact Promotion — session_end_hook.py:97

### What it does

Called automatically on SessionEnd. Runs a lightweight Phase 1 — finds qualifying
session facts and inserts them to `claude.knowledge`. Explicitly does NOT generate
embeddings (comment on line 100-101): "Embeddings are added later by the MCP
consolidate_memories() tool."

### The Embedding Gap

The deferred-embedding plan fails because of the dedup guard in Phase 1:

```sql
AND NOT EXISTS (
    SELECT 1 FROM claude.knowledge k
    WHERE k.title = sf.fact_key AND k.source = 'consolidation'
)
```

When `end_session()` subsequently calls `tool_consolidate_memories("session_end")`,
Phase 1 runs again, hits the existing embedding-less row, and skips. No embedding
is ever added.

Result: Session-end-hook-promoted facts are permanently invisible to all
semantic search (which requires `embedding IS NOT NULL`). The hook's intended
"lightweight insert now, add embedding later" design is broken by the dedup guard
checking only for the row's existence, not whether it has an embedding.

Fix (server.py:2047-2052): Change the dedup guard to also require the existing
row has an embedding:
```sql
AND NOT EXISTS (
    SELECT 1 FROM claude.knowledge k
    WHERE k.title = sf.fact_key AND k.source = 'consolidation'
      AND k.embedding IS NOT NULL
)
```

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/claude-family/knowledge-pipeline-lifecycle.md
