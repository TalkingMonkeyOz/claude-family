---
projects:
- claude-family
- project-metis
tags:
- research
- implementation-audit
- rag
- context-injection
synced: false
---

# Implementation Audit: RAG Hook (rag_query_hook.py)

Back to: [index](impl-audit-index.md)

**Source file:** `scripts/rag_query_hook.py` (~2250 lines)

---

## Decision Pipeline — main() at line 1927

Every prompt passes through this sequence:

1. `is_command()` — if true, inject core protocol only and exit early
2. Get `project_name` from cwd basename, `session_id` from hook_input
3. Task map staleness check (detect session change, delete stale map)
4. Implicit feedback detection (negative phrases, query rephrase)
5. Always: `query_critical_session_facts()` — plain SQL, no embedding
6. Config warning if config keywords detected
7. Skill suggestions (DB query, embedding)
8. Design map load (pure file read)
9. WCC detection and assembly (see [wcc audit](impl-audit-wcc.md))
10. If WCC active: skip 11-14
11. If `needs_rag()`: `query_knowledge_graph()`
12. If `needs_rag()`: `query_vault_rag()`
13. If `needs_rag()` and Nimbus project: `query_nimbus_context()`
14. If `needs_schema_search()`: `query_schema_context()`
15. Context health check (StatusLine sensor or prompt-count heuristic)
16. Failure surfacing (pending auto-filed bugs)
17. `_apply_context_budget()` priority assembly
18. Emit JSON

---

## needs_rag() Gate — lines 676-718

Returns True if prompt contains QUESTION_INDICATORS (`?`, `how do`, `what is`,
`explain`, etc.) or prompt length > 100 chars.

Returns False if the first word of the prompt is an ACTION_INDICATOR (`implement`,
`create`, `fix`, `build`, `update`, `change`, etc.).

**Gap:** Compound prompts starting with action verbs miss RAG even when they contain
embedded questions. Handled partially at lines 700-710: if prompt is > 50 chars and
contains embedded question words (`?`, `explain`, `how do`, etc.), RAG is re-enabled.
But "implement the session manager (see the pattern we discussed)" still skips RAG
because no question words appear. Relevant vault docs are missed.

---

## Context Budget — lines 86 and 1883-1924

`MAX_CONTEXT_TOKENS = 3000`

Priority ordering for `_apply_context_budget()`:

```
Priority 0 (pinned, never dropped):
  core_protocol          ~300 tokens
  critical_facts         ~100 tokens
  context_health_msg     ~100 tokens (when generated)

Priority 1-9 (trimmable, highest priority number dropped first):
  1. failure_context
  2. wcc_context         up to 1500 tokens when active
  3. config_warning
  4. knowledge_graph     ~400 tokens
  5. vault_rag           ~600 tokens
  6. skill_context
  7. schema_context
  8. design_map
  9. nimbus_context
```

With WCC active (priority 2, up to 1500 tokens) and pinned blocks (~400 tokens),
~1100 tokens remain. Knowledge graph and vault RAG are set to None when WCC is
active (line 2091). However, skill_context (priority 6) and schema_context (priority 7)
are NOT set to None — they still fire and may consume budget even when WCC is active.

---

## Session Facts Injection — lines 1235-1318

`query_critical_session_facts()` is always called — no `needs_rag()` gate. Queries
`claude.session_facts` for types `{credential, endpoint, decision, config}` with
plain SQL, no embedding. Returns up to 5 facts.

Gap: Session ID FK race. On the very first prompt of a session, the session may not
yet be committed to `claude.sessions` (startup hook is async). When `query_vault_rag()`
tries to log RAG usage, it hits an FK violation and retries with NULL session_id
(lines 1677-1705). The retry works but produces warning log entries every first prompt.
`query_critical_session_facts()` does not retry on FK failure — it returns no facts.

---

## Implicit Feedback Loop — lines 801-957

Detects negative phrases ("that didn't work", "wrong doc") and query rephrases
(30% word overlap with recent queries). Logs to `rag_feedback` table, calls
`update_doc_quality()`. Miss counts reaching 3 flag docs for review in
`rag_doc_quality.flagged_for_review`.

**Gap: feedback is never read back.** `query_vault_rag()` does not filter or
penalize flagged docs. The quality data accumulates but has no downstream effect
on what gets retrieved. This is a complete feedback loop with a missing wire.

---

## Voyage AI Client — lines 385-418

Module is lazy-loaded on first `generate_embedding()` call (saves ~100ms on
command-style prompts). However, `voyageai.Client(api_key=api_key)` is instantiated
on every call (line 413). There is no module-level client reuse. Each embedding
request creates a new HTTP client object.

Gap: Unnecessary overhead. A module-level client initialized once after the first
successful import would eliminate repeated object instantiation.

---

## Vocabulary Expansion — lines 433-505

Queries `claude.vocabulary_mappings` for user phrases and appends canonical terms
to the query text before embedding. Used only in `query_vault_rag()`, not in
`query_knowledge_graph()`.

Gap: `claude.vocabulary_mappings` requires manual population — no auto-populate
mechanism exists. In practice this table is likely empty or near-empty.

---

## Multiple DB Connections Per Prompt

In a single prompt execution there are up to 4 separate DB connections:
1. `get_db_connection()` in `process_implicit_feedback()`
2. `get_db_connection()` in `query_critical_session_facts()`
3. `get_db_connection()` in WCC module
4. `get_db_connection()` in `query_vault_rag()`

Each connection incurs TCP + auth overhead (~5-15ms on localhost). Total: 20-60ms
of connection overhead per prompt on the semantic search path.

---

## Works Well

- Budget priority system is solid and handles the WCC-replaces-per-source pattern correctly
- WCC bypass of per-source queries is clean (when sources are properly set to None)
- Lazy Voyage AI loading is correct
- Implicit feedback detection identifies real failure signals
- Session fact injection is always-on and appropriately lightweight

## Fragile

- Feedback loop collects quality data that never affects retrieval
- Voyage AI client instantiated per call rather than reused
- `needs_rag()` gate misclassifies compound prompts starting with action verbs
- Skill/schema context fire even when WCC is active (not explicitly excluded)
- Vocabulary mappings table is not auto-populated
- Multiple DB connections per prompt add latency

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/impl-audit-rag-hook.md
