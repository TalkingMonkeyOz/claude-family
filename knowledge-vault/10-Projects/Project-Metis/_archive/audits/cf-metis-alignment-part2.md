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

# CF vs. Metis Alignment — Dossier Concept, Alignment Score

**Part 1**: [Tiers, Ranking, Co-Access, Promotion](cf-metis-alignment-part1.md)
**Index**: [docs/cf-metis-alignment.md](../../../docs/cf-metis-alignment.md)
**Date**: 2026-03-12

---

## 5. Dossier Concept vs. Workfiles

**Metis "dossier" design**: The Activity Space is the dossier. When an activity is created or detected, the system assembles its dossier: linked workfiles, linked knowledge chunks, linked features, scoped by knowledge type. The dossier is persistent, accumulates over time, and is the unit of retrieval scope. Items are linked to the activity explicitly or via co-access. The dossier survives sessions, grows with work, and is archived when the work is complete (dormant at 7 days, archived at 30).

The key design properties:
- Named, described, embedded (semantic detection)
- Links to knowledge, workfiles, features explicitly
- Scoped by knowledge type (only queries relevant sources)
- Lifecycle-managed (active → dormant → archived)
- Event-driven cache invalidation when contents change

**CF "workfiles" implementation**: Cross-session component-scoped working context. Filing cabinet: project = cabinet, component = drawer, title = file. UPSERT on `(project_id, component, title)`. Append mode. Voyage AI embeddings. `linked_sessions` tracks contributing sessions. `is_pinned` flag for precompact surfacing. Created 2026-03-09.

**Are these the same thing?**

They are the same concept at different levels of completeness. Both implement the dossier metaphor. The gap is that CF workfiles are half the mechanism:

| Capability | Metis Design | CF Workfiles | Gap |
|---|---|---|---|
| Named, persistent topic container | Activity (named, described) | Workfile (component name only) | CF has no activity-level container; only file-level |
| Semantic detection (find the right dossier) | Embedding-based cosine similarity on activity description | Word-overlap fallback (coarse) | CF detection is unreliable; no activity embedding |
| Knowledge type scoping | `linked_knowledge_types` narrows which sources are queried | Not present | CF queries all knowledge regardless of relevance |
| Explicit knowledge linking | `linked_knowledge UUID[]` on activity | Not present | CF has no link from activity/workfile to knowledge chunks |
| Co-access accumulation | `co_access_log` builds evidence of relatedness | Not present | CF has zero behavioral signal |
| Lifecycle management | active → dormant → archived (7d/30d) | `is_pinned` flag only | CF has no lifecycle; workfiles accumulate indefinitely |
| Cache invalidation | `invalidate_wcc_cache()` called on stash/remember | Documented but not wired | Cache expires by TTL only; new content invisible for 5 min |

**What is the gap between Metis design and CF implementation?**

The core gap is the Activity entity itself. CF has workfiles (the filing drawers) but no Activity (the filing cabinet with a subject). Without an Activity, the WCC has no semantic anchor. Without semantic detection, the assembler cannot determine which dossier is relevant to the current prompt. The workfile table is the right building block — it needs an Activity wrapper with an embedding to be the dossier.

The CF implementation built the filing system from the drawers up. Metis built from the cabinet down. The drawers are good. The cabinet is missing.

---

## 6. Alignment Score

How far is CF from the Metis target?

| Metis Concept | CF Status | Gap Severity | Notes |
|---|---|---|---|
| **2-tier memory (session + persistent)** | 3-tier with broken promotion | High | 96% stuck at MID; 2-tier would be simpler and work better today |
| **Single retrieval path** | 3 overlapping paths, 400-600ms sequential | High | Duplicate context injection; latency 2-3x Metis target |
| **Composite scoring (6 signals)** | 4-signal formula in recall_memories() only; vault RAG uses similarity+recency only | Medium | CF formula exists but not applied uniformly; missing co-access and feedback signals |
| **Unified dedup before budget cap** | No dedup; same entry can appear from multiple paths | High | Direct cause of context bloat |
| **Co-access tracking** | Not present; no table, no writes, no signal | Medium | Not needed at current scale; cheap to add now for future value |
| **Event-driven freshness** | `created_at` decay (known bug); `freshness_score` field does not exist | Medium | Decays new content faster than old; correctness bug |
| **Task-completion promotion** | `mark_knowledge_applied()` exists but is never called | High | Automatic positive feedback on task close — the most valuable promotion signal |
| **Activity Space (semantic dossier)** | `activities` table created; 0 explicit activities; wcc_assembly.py absent | Critical | The entire WCC architecture depends on this; it does not function at all |
| **Workfile system (filing drawers)** | Present, 3 rows, not in Core Protocol | Medium | The right mechanism; zero adoption due to missing protocol mention |
| **Embedding-based activity detection** | Trigram word-overlap fallback only; MIN_ACTIVITY_SIMILARITY dead code | High | False positives; wrong activity activates |
| **Lifecycle management (dormant/archive)** | Not present for knowledge or activities | Low | Nice-to-have; not blocking |
| **Feedback loops (explicit + implicit)** | `rag_feedback` table exists; `mark_knowledge_applied()` never called; rephrasing detection absent | High | CF has the schema but the write paths are dead |
| **Token-count on stored items** | Not present on knowledge entries | Medium | Assembler cannot accurately fill budget without token counts |
| **BPMN model-to-code alignment** | 72% overall; WCC critical gap; 2 stale threshold values | Medium | Mostly aligned on implemented features; gaps on WCC and aspirational graph |

**Overall alignment**: CF is approximately 35-40% of the way to the Metis target for the knowledge retrieval and assembly subsystem.

The high-severity gaps (broken 2-tier promotion, 3 overlapping paths, no dedup, task-completion feedback dead, WCC non-functional) are all fixable with targeted code changes. None require a redesign. The architectural direction is correct; the implementation has accumulated technical debt at the pipeline level.

**Minimum viable path to Metis parity** (ordered by impact/effort):

| Step | Change | Effort | Unlocks |
|---|---|---|---|
| 1 | Deploy MID→LONG promotion fix (access_count >= 5, age >= 7d) | Small | LONG tier finally works |
| 2 | Add `stash()` to Core Protocol Rules | Trivial | Workfile adoption |
| 3 | Wire `mark_knowledge_applied()` into `complete_work()` | Small | Task-completion promotion signal |
| 4 | Replace 3 RAG paths with 1 parallel path + dedup | Medium | Latency halved; no duplicate context |
| 5 | Add Activity embeddings + cosine detection | Medium | WCC becomes functional |
| 6 | Ship `wcc_assembly.py` | Medium | Activity-scoped retrieval active |
| 7 | Replace `created_at` decay with `last_retrieved_at` + `freshness_score` | Medium | Correct freshness behavior |
| 8 | Add `co_access_log` table (write only, no scoring yet) | Small | Signal accumulation starts |

Steps 1-3 are immediate fixes requiring minimal code. Steps 4-6 are the core retrieval redesign. Steps 7-8 are quality improvements that compound over time.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/cf-metis-alignment-part2.md
