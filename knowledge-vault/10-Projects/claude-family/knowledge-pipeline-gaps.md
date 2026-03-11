---
projects:
- claude-family
tags:
- knowledge-pipeline
- gaps
- recommendations
- cognitive-memory
synced: false
---

# Knowledge Pipeline — Part 4: Gaps and Recommendations

Index: [[knowledge-pipeline-analysis]]
Prev: [[knowledge-pipeline-lifecycle]]

---

## Root Cause: Why Junk Gets Stored

`remember()` is promoted in the Core Protocol as the general-purpose memory tool
with no guidance on what constitutes worthwhile content. Agents following the
protocol store:
- Task state: "Starting work on BT47 — implementing the dedup gate"
- Confirmations: "agent1_complete: successfully created the BPMN file"
- Ephemeral decisions: "Using approach A for this task, approach B failed"

All three are ephemeral — they describe one session's execution state, not
reusable knowledge. But `remember()` cannot distinguish them from genuine patterns
and gotchas. It has no content awareness.

### Ingestion Path for Junk

1. Agent calls `remember("agent1_complete: ...")` with default args.
2. `memory_type="learned"` routes to `tier="mid"`.
3. Embedding is generated.
4. Dedup check: no similar entry exists (first occurrence).
5. Row inserted: `confidence=65`, `tier='mid'`, `source='remember'`.
6. Row is now searchable and will surface in future sessions.

---

## Gap Analysis

### Gap 1: No Content Quality Gate at Ingestion

**Severity: Critical**

No function validates whether content is meaningful knowledge. The only content
gate in the entire pipeline is the 50-character minimum in `consolidate_memories()`
Phase 1 for session_facts promotion. Direct `remember()` and `store_knowledge()`
calls have no equivalent.

### Gap 2: mark_knowledge_applied() Never Called

**Severity: High**

The confidence feedback loop and MID->LONG promotion both require `times_applied`
being incremented. Since no code calls this function:
- Confidence stays at 65 for virtually all mid-tier entries.
- `times_applied` stays at 0 or NULL everywhere.
- No entry ever reaches `times_applied >= 3 AND confidence >= 80`.
- MID->LONG promotion does not happen in practice.

### Gap 3: Embedding-less Rows from session_end_hook

**Severity: High**

Facts promoted by the session_end_hook have no embedding and are invisible to all
semantic search. The subsequent MCP consolidation call is blocked by a dedup guard
that treats the existing embedding-less row as a prior successful insertion.
The embeddings are never added unless rows are manually deleted and re-inserted.

### Gap 4: Periodic Consolidation Never Runs

**Severity: High**

Phase 2 (MID->LONG) and Phase 3 (decay/archive) only run when `trigger` is
`"periodic"` or `"manual"`. There is no scheduled job, no hook, and no automatic
invocation. The lifecycle machinery exists but is never activated.

### Gap 5: Dedup Threshold Too High

**Severity: Medium**

The 0.85 cosine similarity dedup threshold in `remember()` misses near-duplicates
phrased differently. Entries with similarity 0.70-0.84 both get stored as separate
rows.

### Gap 6: recall_knowledge() Does Not Exclude Archived Tier

**Severity: Medium**

`tool_recall_knowledge()` has no `AND tier != 'archived'` filter. The RAG hook's
`query_knowledge()` does exclude archived, but the direct MCP tool does not.

### Gap 7: Tags Column Does Not Exist

**Severity: Low**

The `recall_knowledge()` `tags` parameter implies a tags array column. In practice
tags are matched against `knowledge_category` via ILIKE. No actual tags column
exists on `claude.knowledge`.

---

## Recommendations

### Rec 1: Content Quality Gate at remember() — server.py:1928

Add before the INSERT in `tool_remember()`:
- Minimum 80 characters for mid-tier content.
- Block strings matching task-state patterns: regex `agent\d+_complete`,
  `task done`, `moving to`, `step \d+ of \d+`.
- A structural hint that content is reusable: presence of `:`, `_`, or a word
  longer than 8 characters.

### Rec 2: Call mark_knowledge_applied() from RAG Hook — rag_query_hook.py:1034

After `query_knowledge()` updates `access_count`, also increment `times_applied`
for returned knowledge IDs. Use `success=True` as a weak positive signal (the
entry was deemed relevant enough to inject). Alternatively, return knowledge IDs
in `recall_memories()` results and add a Core Protocol instruction for Claude to
call `mark_knowledge_applied()` for each ID it actually used.

### Rec 3: Fix Embedding-less Promotion — server.py:2047

Change the Phase 1 dedup guard to require an existing row also has an embedding:
```sql
AND NOT EXISTS (
    SELECT 1 FROM claude.knowledge k
    WHERE k.title = sf.fact_key AND k.source = 'consolidation'
      AND k.embedding IS NOT NULL
)
```
This allows Phase 1 to re-process embedding-less rows and add embeddings without
creating duplicates.

### Rec 4: Automate Periodic Consolidation

Add to `server_v2.py:start_session()` or `session_startup_hook_enhanced.py`:
- Read a `last_periodic_consolidation` timestamp from `claude.session_state` or
  a new `claude.maintenance_log` table.
- If more than 24 hours have passed, call `tool_consolidate_memories("periodic")`.
- Store the new timestamp after completion.

### Rec 5: Lower Dedup Threshold — server.py:1875

Change `> 0.85` to `> 0.75` to catch near-identical entries phrased differently.

### Rec 6: Fix recall_knowledge Archived Filter — server.py:1079

Add `AND tier != 'archived'` to the WHERE clause of `tool_recall_knowledge()`.

### Rec 7: Guidance on Ephemeral vs. Reusable Memory

Update Core Protocol rule 4 to specify:
- Call `remember()` only for reusable patterns, gotchas, or decisions that would
  help a future session working on the same codebase.
- For within-session progress notes, use `store_session_fact()` instead.
- Examples of what NOT to store: task completion acknowledgments, agent handoff
  messages, step-by-step execution logs.

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/claude-family/knowledge-pipeline-gaps.md
