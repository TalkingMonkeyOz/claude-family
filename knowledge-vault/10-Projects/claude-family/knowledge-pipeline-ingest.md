---
projects:
- claude-family
tags:
- knowledge-pipeline
- ingestion
- cognitive-memory
synced: false
---

# Knowledge Pipeline — Part 1: Ingestion

Index: [[knowledge-pipeline-analysis]]
Next: [[knowledge-pipeline-recall]]

---

## tool_store_knowledge() — server.py:934

### What it does

Inserts a row into `claude.knowledge` with `tier='mid'` hardcoded. Calls
`generate_embedding()` via `format_knowledge_for_embedding()`. If embedding fails
(Voyage AI unavailable), stores the row without an embedding — the row is then
invisible to all semantic search queries that require `embedding IS NOT NULL`.

### Quality Gates

None. The function accepts any non-empty `title` and `description`:
- No minimum content length.
- No prohibited-pattern rejection.
- No duplicate check before INSERT.
- `knowledge_type` is not validated at the implementation level (only at the MCP
  wrapper's Literal type signature).

### Tier Routing

Hardcoded `tier='mid'` on every INSERT (lines 971 and 984). Tier is not
influenced by `knowledge_type` in any way.

### Dedup Logic

None. Every call produces a new row regardless of similarity to existing entries.

### Known Gaps

- Any string, including ephemeral agent state like "agent1_complete", is stored
  permanently with no quality filter.
- `tier='mid'` is always written even when `knowledge_type='pattern'` (which
  should logically be `long` tier).
- No dedup means the table accumulates identical or near-identical entries.

---

## tool_remember() — server.py:1791

### What it does

The preferred F130 cognitive memory entry point. Routes to `session_facts` (SHORT)
or `claude.knowledge` (MID/LONG) based on `memory_type`. Performs a dedup check
and an auto-linking step for mid/long-tier entries.

### Quality Gates

None for content quality. The only typed validation is at the MCP wrapper
signature (Literal type for `tier_hint`), not at the implementation level.

### Tier Routing (server.py:1807-1819)

```python
short_types = {"credential", "config", "endpoint"}
mid_types   = {"learned", "fact", "decision", "note", "data"}
long_types  = {"pattern", "procedure", "gotcha", "preference"}
```

Logic:
1. If `tier_hint != "auto"`, use the hint directly.
2. Else classify by `memory_type` set membership.
3. `learned` (the default) always routes to `mid`.

Any call to `remember()` with default arguments lands in `mid` tier regardless
of content. An agent writing "agent1_complete" with defaults creates a mid-tier
knowledge entry.

### Dedup Logic (server.py:1867-1907)

Only executes if an embedding was successfully generated.

Query: find a single row in the same tier with cosine similarity > 0.85.

```sql
SELECT knowledge_id, title, description, confidence_level,
       1 - (embedding <=> %s::vector) as similarity
FROM claude.knowledge
WHERE embedding IS NOT NULL AND tier = %s
  AND 1 - (embedding <=> %s::vector) > 0.85
ORDER BY similarity DESC LIMIT 1
```

If a match is found, the merge strategy:
- Keep the longer description (by character count, not semantic quality).
- Increment confidence by 5 (capped at 100).
- Increment `access_count` by 1.
- Return `action='merged'`, no new row inserted.

Gap: The 0.85 threshold is very high for voyage-3 embeddings. Semantically
near-identical entries phrased differently (similarity 0.70-0.84) both get stored
as separate rows.

### Contradiction Detection (server.py:1909-1926)

Finds entries with similarity > 0.75 across mid/long tiers. If the new entry
would be mid-tier and a nearby existing entry has `confidence_level >= 80`, a
`contradiction_flag` is set. The flag changes the returned `action` to
`'contradiction_flagged'` but does NOT prevent storage — the row is still
inserted. No notification beyond the return value.

### Auto-Linking (server.py:1963-1983)

After INSERT, finds entries with similarity 0.5-0.85 and creates
`knowledge_relations` rows with `relation_type='relates_to'`. Best-effort;
failures silently ignored.

### Confidence Initialization (server.py:1933-1934)

```python
confidence = 65 if tier == "mid" else 75
```

All new entries start at fixed values regardless of content quality or source
reliability. No mechanism exists to assign lower confidence to low-quality inputs.

### SHORT Path (server.py:1821-1849)

For `tier="short"`, delegates to `tool_store_session_fact()`. Derives `fact_key`
from the first line of content (first 50 chars, alphanumeric only). Maps
`memory_type` to `fact_type`. Sets `is_sensitive=True` for credentials.

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/claude-family/knowledge-pipeline-ingest.md
