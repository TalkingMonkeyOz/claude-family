---
projects:
- claude-family
- project-metis
tags:
- research
- implementation-audit
- wcc
- activity-detection
synced: false
---

# Implementation Audit: Work Context Container (WCC)

Back to: [index](impl-audit-index.md)

**Source file:** `scripts/wcc_assembly.py` (849 lines)

---

## Activity Detection — lines 111-162

Detection runs in four priority levels:

1. Manual override via `session_facts.current_activity` (requires live session_id)
2. Exact string match: `activity_name.lower() in prompt_lower` or alias match
3. Word overlap: count 3+ char words shared between prompt and activity name;
   if overlap >= MIN_WORD_MATCH (2), that activity is a candidate
4. Workfile component fallback: `component.lower() in prompt_lower`

**The trigram gap:** `MIN_ACTIVITY_SIMILARITY = 0.6` is defined at line 43 and the
docstring at line 9 says "trigram fuzzy matching." The actual `_match_activity_from_db`
function (lines 189-256) does NOT use trigrams or this constant at all. It uses only
word overlap scoring. The constant is dead code.

**Word overlap scoring is coarse.** Any activity sharing two 3+ char words with the
prompt matches. "Session Management" would match any prompt mentioning "session" and
any other common word. This produces false positives on long activity names.

**Auto-create side effect (lines 305-330):** When a workfile component name matches
the prompt, `_ensure_activity_exists()` auto-creates an activity via UPSERT. This
silently grows the activities table without explicit user action.

---

## Budget Allocation — lines 33-41

```
SOURCE_BUDGETS = {
    "workfiles":     0.25,   # 375 tokens of 1500 default
    "knowledge":     0.25,   # 375 tokens
    "features":      0.15,   # 225 tokens
    "session_facts": 0.10,   # 150 tokens
    "vault_rag":     0.15,   # 225 tokens
    "skills_bpmn":   0.10,   # 150 tokens
}
```

Total budget default is 1500 tokens (passed from `rag_query_hook.py:2071`).

Sources are queried sequentially (line 392). No parallelism despite the comment
acknowledging this. With 50ms per DB round trip, 6 sources = 300ms minimum per
cache miss, typically 400-600ms in practice.

---

## Source Queries

**Workfiles (lines 488-536):** Fetches up to 5 workfiles by exact component name
or alias match. Content truncated to 200 chars per workfile at line 529.
Gap: 200 chars is far less than the 375-token budget allows (~1500 chars). The
per-workfile truncation is applied before budget math, wasting most of the allocation.

**Knowledge (lines 539-610):** Falls back from embedding to ILIKE keyword search
when no embedding function is provided. Minimum similarity 0.35. Graceful degradation
is good but the fallback is silent — no indicator in the output block that embedding
was skipped.

**Features/Tasks (lines 613-652):** ILIKE match on feature name or description.
Returns feature code, name, status, and task counts. Lightweight and correct.

**Session Facts (lines 655-693):** ILIKE match on fact_key and fact_value for the
activity name. Only returns non-sensitive facts from the current session. Reasonable.

**Vault RAG (lines 696-741):** Embedding search against `claude.vault_embeddings`.
Threshold 0.4. Only runs if `generate_embedding_fn` is provided. Returns None silently
if embedding is unavailable.

**BPMN/Skills (lines 744-777):** ILIKE search on `claude.bpmn_processes`. No
embedding. Returns process IDs and names. Likely low hit rate unless the activity
name exactly matches a process name.

---

## Caching Strategy — lines 53-104

Cache lives in `~/.claude/state/wcc_state.json`. TTL is 300 seconds (5 minutes).
Cache fields: `current_activity`, `cached_wcc`, `cached_at`, `cache_invalidated`.

**Cache invalidation is never called.** `invalidate_wcc_cache()` (lines 83-90) has
a docstring saying "called when stash() or remember() fires" but neither function
calls it. The `stash()` and `remember()` MCP tools in `server_v2.py` do not import
or call this function. Cache expires only by TTL.

Consequence: if Claude stores new workfiles mid-session, the WCC will show stale
content for up to 5 minutes before the TTL expires.

---

## Summary

**Works well:**
- 5-minute TTL cache is appropriate for activity switching cadence
- Priority detection chain (manual override > exact > word overlap > component) is logical
- Budget percentages are reasonable for the source types

**Fragile:**
- Documented trigram matching does not exist — dead constant at line 43
- Cache invalidation is unimplemented despite being documented
- Sequential source queries add 400-600ms latency per cache miss
- Workfile content truncated to 200 chars before budget is applied
- Auto-activity creation from component names is an undocumented side effect

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/impl-audit-wcc.md
