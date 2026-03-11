---
projects:
- claude-family
- project-metis
tags:
- research
- implementation-audit
- architecture
- lessons-learned
synced: false
---

# Implementation Audit: Cross-Cutting Findings

Back to: [index](impl-audit-index.md)

Systemic issues that cut across multiple components, plus what the prototype taught us.

---

## Systemic Issues

### The "85% token reduction" claim does not hold up

CLAUDE.md and MEMORY.md both state the RAG hook provides "85% token reduction."
This compares against a hypothetical where the full vault is loaded into context.
Actual injection per prompt on the semantic search path:

```
Always:   core_protocol (~300) + critical_facts (~100)  = ~400 tokens
Question: + knowledge_graph (~400) + vault_rag (~600)   = ~1400 tokens total
WCC:      + wcc_context (up to 1500)                    = ~1900 tokens total
```

On a long session with many questions, the hook contributes 1-2k tokens per prompt to
an already-growing context window. The injection is not small. The claim reflects
marketing intent rather than measurement.

### Three retrieval paths for the same data

The mid/long knowledge tier can be retrieved via:
1. `recall_memories()` MCP tool (tool_recall_memories in server.py:1548)
2. `query_knowledge_graph()` in the RAG hook (rag_query_hook.py:1103)
3. `query_knowledge()` in the RAG hook (rag_query_hook.py:959) as fallback

All three query `claude.knowledge` with different thresholds, scoring, and formatting.
On a question prompt, the RAG hook runs path 2 (which falls back to path 3). If Claude
also calls `recall_memories()` explicitly, it runs path 1. Both can return overlapping
results with different scores. There is no deduplication between these paths.

### Four DB connections per prompt

In a single prompt on the semantic search path:
1. `process_implicit_feedback()` — connection, close
2. `query_critical_session_facts()` — connection, close
3. WCC module `wcc_conn` — connection, close
4. `query_vault_rag()` — connection, close (possibly a 5th for knowledge graph)

Each connection on Windows localhost: ~5-15ms. Total: 20-60ms connection overhead
per prompt. A connection pool shared across the hook invocation would eliminate this.

### Features exist in the schema without runtime behavior

Several schema features are populated but never read back to affect behavior:

| Feature | Populated by | Read by | Effect |
|---------|-------------|---------|--------|
| `rag_doc_quality.flagged_for_review` | `update_doc_quality()` | Nothing | None |
| `rag_feedback` table | `log_implicit_feedback()` | Nothing | None |
| `vocabulary_mappings` | Manual SQL | `expand_query_with_vocabulary()` | Only if table populated |
| `wcc_state.cache_invalidated` | `invalidate_wcc_cache()` | `_is_cache_valid()` | Dead — never set |

These represent incomplete feedback loops. The data collection code is correct; the
consumption code was never written or wired up.

### Two implementations of the same consolidation logic

Phase 2+3 of memory consolidation appears in:
- `server.py:2098-2136` (inside `tool_consolidate_memories`)
- `session_startup_hook_enhanced.py:283-313` (direct SQL in `run_periodic_consolidation`)

Thresholds (`times_applied >= 3`, `confidence_level >= 80`, `access_count >= 5`)
exist in both places. If thresholds are tuned in one, the other silently diverges.

### Session ID propagation is fragile

The session_id flows: startup hook → DB → RAG hook (from hook_input) → WCC →
session_facts queries. Race condition on the first prompt: if the startup hook
has not yet committed the session, `query_critical_session_facts()` silently returns
no facts. `query_vault_rag()` retries with NULL session_id but generates warning logs
every first prompt of every session.

---

## What the Prototype Taught Us

**1. Context injection works but is expensive.**
The system successfully assembles relevant context per prompt. The cost is 3-5 DB
connections, 1-2 Voyage AI API calls, and 300-600ms of latency per question prompt.
This is viable but not negligible. Any redesign should target a single DB connection
per prompt and a shared embedding client.

**2. Activity detection is the right abstraction, wrongly implemented.**
WCC — detect current activity, assemble scoped context — is the correct mental model.
The implementation using word overlap is a shortcut that produces false positives.
Embedding-based activity detection (compute cosine similarity between the prompt
embedding and activity name embeddings) would be more accurate and would actually
use the `MIN_ACTIVITY_SIMILARITY = 0.6` constant that is already defined but unused.

**3. Memory tiers are correct in concept, not integrated end-to-end.**
Short/mid/long separation is meaningful. The problem is that the RAG hook runs its
own knowledge retrieval path (`query_knowledge_graph`) rather than calling
`recall_memories()`. Two retrieval paths exist for the same data with different
thresholds, scoring, and formatting. A redesign should have one retrieval path.

**4. Task persistence is architecturally limited.**
The hook-based sync is a shim over a fundamentally session-scoped system. Claude Code's
native task list was not designed for cross-session persistence. Any redesign should
use DB-first task tracking rather than syncing from an ephemeral in-memory list. The
`restore_count` field (how many times the same task has been re-created) is a symptom
counter for a structural problem.

**5. Precompact survival is the most reliable mechanism.**
Of all retrieval mechanisms, the precompact hook is most reliable: predictable timing,
injects exactly the right state, no relevance guessing required. Its weakness is
requiring Claude to have saved state proactively before compaction occurs. A
redesign should invest more in automatic state capture rather than relying on
advisory recovery instructions post-compaction.

**6. Caching exists but invalidation does not.**
WCC caches for 5 minutes but `invalidate_wcc_cache()` is never called. The intent
(invalidate when workfiles or memories change) is correct; the wiring is missing.
Any new caching layer must have invalidation integrated at the write path, not added
as an afterthought.

**7. The feedback loop architecture is sound but incomplete.**
Implicit feedback detection (negative phrases, query rephrases) → doc quality scoring
→ retrieval penalization is the right design. The first two steps are implemented;
the third is not. Adding a quality filter to `query_vault_rag()` would complete the loop.

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/impl-audit-cross-cutting.md
