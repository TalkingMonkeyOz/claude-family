---
projects:
- claude-family
- project-metis
tags:
- audit
- synthesis
- alignment
synced: false
---

# CF vs. Metis Alignment — Tiers, Ranking, Co-Access, Promotion

**Part 2**: [Dossier vs Workfiles, Alignment Score](cf-metis-alignment-part2.md)
**Index**: [docs/cf-metis-alignment.md](../../../docs/cf-metis-alignment.md)
**Date**: 2026-03-12

---

## 1. 2-Tier vs. 3-Tier Memory

**Metis design**: 2-tier — Session Notebook (layer 2, `session_facts`) and Persistent Knowledge (layer 4, `persistent_knowledge`). The distinction is lifecycle: session-scoped vs. cross-session. No promotion required — items are placed in the right tier at write time based on intent.

**CF implementation**: 3-tier — SHORT (`session_facts`), MID (`knowledge` tier='mid'), LONG (`knowledge` tier='long'). Promotion from MID→LONG is supposed to happen automatically via `consolidate_memories()`.

**What the audit data shows**:

| Observation | Data |
|---|---|
| MID entries stuck | 987 of 1,026 (96%) — never promoted to LONG |
| Promotion fix identified | 2026-03-11 (access_count >= 5 + age >= 7d replacing broken times_applied >= 3) |
| Promotion fix deployed | Not yet |
| LONG tier effective benefit | Near-zero until fix deployed |
| MID tier quality | Declining — cross-project bleed, junk entries, fixed confidence=65 |

**Should CF adopt 2-tier?**

Yes, with a specific mapping. The 3-tier model adds complexity without adding value at current scale because the MID→LONG promotion pipeline is broken and MID has become a dumping ground. The practical result today is already 2-tier: SHORT (session_facts, working fine) and a polluted middle store that functions as neither working knowledge nor proven patterns.

The Metis 2-tier model is cleaner because it does not depend on automatic promotion. The write decision is made at write time: is this session-scoped (notebook) or cross-session (persistent)? That decision is simpler than "is this a mid or long item?" and does not require a background job to fix.

If CF adopts 2-tier: retain SHORT as `session_facts`, merge MID+LONG into a single `persistent_knowledge` table with a `knowledge_type` field (gotcha, pattern, decision, fact, procedure) replacing tier classification. The `remember()` quality gate and dedup logic can remain unchanged.

---

## 2. Unified Ranking vs. 3 Search Paths

**Metis design**: Single retrieval path. All sources feed one pipeline. One composite scoring function (6 signals). One dedup step. One budget cap. Parallel execution targeting < 200ms end-to-end.

**CF implementation**: 3 parallel but uncoordinated search paths with different thresholds and scoring:

| Path | Code Location | Min Similarity | Scoring | Notes |
|---|---|---|---|---|
| `recall_memories()` | server.py MCP tool | 0.5 | Tier weight + similarity + recency + access_freq + confidence | Explicit call only |
| `query_knowledge_graph()` | rag_query_hook.py | 0.35 | Similarity only | Falls back when WCC inactive |
| `query_knowledge()` | rag_query_hook.py (fallback) | 0.5 | Similarity + recency | Falls back when WCC inactive |

The same knowledge entry can be retrieved by all three paths, scored differently, and appear multiple times in context. Measured 400-600ms sequential latency vs. Metis target of < 200ms parallel.

**Which approach serves better?**

Unified ranking is clearly superior. CF's 3-path approach produces duplicates, inconsistent scoring, and unnecessary latency. The 400-600ms overhead on every prompt is entirely attributable to sequential execution of overlapping queries.

**What unified ranking would look like in CF**:

1. Replace the 3 RAG hook fallback paths with one parallel query function calling vault_embeddings + knowledge (mid+long) simultaneously.
2. Apply a single composite score: `(0.55 × similarity) + (0.30 × recency_factor) + (0.15 × explicit_link_bonus)` as a starting formula (no co-access data yet).
3. One dedup step on content hash before budget cap.
4. This removes one Voyage API call per prompt (the duplicate vault query in WCC path).

This does not require the full Metis scoring machinery. Eliminating the 3-path redundancy alone would halve latency and eliminate duplicate context injection.

---

## 3. Co-Access Tracking

**Metis design**: `co_access_log` table — one row per cache-miss assembly, logging all chunk_ids retrieved together. Drives Signal 2 in composite score (weight 0.30). Bootstraps to zero; meaningful signal after ~100 retrievals per activity, strong after ~500. Captures relationships embeddings miss: two chunks always retrieved together even if semantically distant.

**CF implementation**: No co-access tracking. No equivalent table or concept.

**Is it needed for CF's scale?**

At current scale (24 projects, single-digit active daily sessions per project), co-access signal would take months to accumulate per-project. The 0.30 weight would be dormant for the first 3-4 months as Metis itself acknowledges. For CF Phase 1, co-access tracking is not needed.

However, the schema is cheap and the payoff compounds. Adding the `co_access_log` table now costs one table and one insert per retrieval. Not adding it means no behavioral signal ever accumulates, and any future upgrade requires backfilling from scratch.

**What data currently exists that could bootstrap it**:

None in the current CF schema. `mcp_usage` (the closest candidate) has 6,965 synthetic rows with NULL session_ids — unusable. If CF were to add co-access tracking, it would start from zero.

**Recommendation**: Add the table as a no-op at CF Phase 1 (create, insert on every recall_memories() call, do not yet use in scoring). By the time CF needs it, 6 months of signal will be available.

---

## 4. Event-Driven Promotion

**Metis design**: Promotion is event-driven, not time-driven. Persistent Knowledge (layer 4) is populated via: (a) explicit `remember()` call by Claude, (b) implicit promotion when a task completes (chunks in context at completion → `task_completed` feedback), (c) 3+ retrievals of the same chunk across sessions. Freshness is event-driven (source change, re-verification, contradiction) rather than time-decay.

**CF implementation**: MID→LONG promotion uses `access_count >= 5 AND age >= 7d`. This is retrieval-frequency-based (an improvement over the broken `times_applied >= 3`), but the fix has not been deployed. Freshness uses `created_at` as a staleness proxy — a known bug that decays new content faster than old content.

**What would work for CF**:

The Metis approach is correct. CF should adopt:

1. **Task completion trigger**: When `complete_work()` fires, identify knowledge entries accessed during the task window and write one positive feedback event per chunk. This replaces the never-called `mark_knowledge_applied()`.
2. **Retrieval frequency**: `access_count >= 3` is sufficient for CF's scale (lower threshold than Metis's 5, because CF's session frequency is lower per-project).
3. **Event-driven freshness**: Replace `created_at` decay with `last_retrieved_at` decay (already noted as a CF bug in the BPMN audit). Add `freshness_score` column to `claude.knowledge` starting at 1.0, decremented on source-document-changed events.

The deploy sequence: (1) deploy the retrieval-frequency fix immediately (no schema change needed), (2) add task-completion promotion as a side-effect in `complete_work()`, (3) add `freshness_score` in a future migration.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/cf-metis-alignment-part1.md
