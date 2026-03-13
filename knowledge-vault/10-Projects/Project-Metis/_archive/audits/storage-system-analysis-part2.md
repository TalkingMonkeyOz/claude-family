---
projects:
- claude-family
- project-metis
tags:
- audit
- synthesis
- storage
synced: false
---

# Storage System Analysis — Notepad Model and Dead Mechanisms

**Part 1**: [Overlap Map, Gap Map, Usage Heatmap](storage-system-analysis-part1.md)
**Index**: [docs/storage-system-analysis.md](../../../docs/storage-system-analysis.md)
**Date**: 2026-03-12

---

## 4. The "Notepad" Model

John's directive: open the topic dossier, jot things down, come back tomorrow and continue, file it away when done, find it months later.

| Notepad Action | What Happens Today | Gap / Verdict |
|---|---|---|
| **"Open the topic dossier"** | No dedicated mechanism. Closest: `unstash(component)` pulls workfiles, but only 3 workfiles exist. WCC was designed for this but `wcc_assembly.py` is absent from disk. | The dossier does not exist at runtime. WCC cannot assemble without workfiles and activities. |
| **"Jot things down"** | Three competing paths: `store_session_fact()` (Core Protocol Rule 3), `remember()` (Rule 4), `store_session_notes()` (Rule 6). `stash()` — purpose-built for cross-session component context — is not in Core Protocol at all. | Three paths with no clear split by use case. The right tool (`stash`) is invisible to Core Protocol. |
| **"Come back tomorrow"** | session_facts survive exactly 3 sessions (count-dependent, not time-based). A project running 20 sessions/day loses day-1 decisions in hours. knowledge MID survives indefinitely but with recency decay. Session notes survive (filesystem append). MEMORY.md always present for claude-family only. | Recovery is unreliable and project-dependent. No narrative continuity mechanism exists. |
| **"File it away when done"** | No closure mechanism exists. Completed features stay `in_progress`. Build tasks accumulate. No "archive completed topic" path. Auto-archive silently moves zombies — not the same as deliberate filing. | Topic closure is not modeled anywhere in the system. |
| **"Find it months later"** | vault_embeddings: reliable (HNSW, 100% coverage, semantic search). knowledge MID: retrievable but recency score approaches zero after 90 days. session_facts: gone within 3 sessions. Session notes: no semantic search. MEMORY.md: manual maintenance, single project. | After 90 days, only vault_embeddings returns reliable results — and only if someone wrote to vault docs. Most learned content is effectively unfindable after 3 months. |

**Honest verdict**: The current system is a write-everything / find-nothing model. There are 6+ write paths and no coherent read-back story for topics older than a few sessions. The notepad metaphor is aspirational. Reality is closer to a stack of sticky notes that fall on the floor after three days.

---

## 5. Dead Mechanisms Summary

Combined from all audits. Ordered by priority.

| Mechanism | Status | Action | Effort |
|---|---|---|---|
| `mcp_usage` (6,965 rows) | Zombie — all rows have NULL session_id; real usage never tracked | Truncate immediately; fix logger or remove | 5 min |
| `enforcement_log` (1,333 rows) | Zombie — process_router retired 2026-02-28; no reader or writer | Truncate; code scan then DROP | 15 min |
| `workflow_state` (0 rows) | No write path in server_v2.py | Verify vestigial; DROP | 30 min |
| `knowledge_retrieval_log` (77 rows) | Last write from retired process_router; `recall_memories()` does not log here | Add write to `tool_recall_memories` OR drop | 1h |
| BPMN: `knowledge_graph_lifecycle` | Apache AGE not installed; 18 tasks modeling unimplemented stack | Mark BPMN aspirational — never treat as active | Trivial |
| BPMN: `L1_knowledge_management` | Pre-F130 stub fully superseded by knowledge_full_cycle | Retire; replace with callout to knowledge_full_cycle | Low |
| BPMN: `working_memory` Path 3 | Duplicates precompact at lower fidelity | Remove Path 3; add cross-reference note | Low |
| Three DB validators (`validate_db_write.py`, `validate_phase.py`, `validate_parent_links.py`) | Parse CLI args; hook system passes JSON on stdin — silently fail open; zero enforcement | Fix stdin parsing or remove entirely | Medium |
| Knowledge MID junk entries (~40-50) | `agent1_complete`, `agent2_complete` and similar session artifacts stored as knowledge at confidence=65 | Bulk DELETE WHERE content matches junk patterns | Small |
| BPMN: dedup threshold mismatch | Model says 0.85; code uses 0.75; affects merge frequency | Update BPMN comment to 0.75 | Trivial |
| BPMN: MID→LONG promotion criteria | Model says `times_applied >= 3`; code uses `access_count >= 5 AND age >= 7d` | Update BPMN comment | Trivial |
| `rag_query_patterns` (0 rows) | Planned RAG learning system; never built | Decide: implement or DROP | Decision |

**Adoption-gap (built but unadopted — not dead)**:

| Mechanism | Root Cause of Non-Adoption | Fix |
|---|---|---|
| `project_workfiles` (3 rows) | `stash()` not in Core Protocol; Claude defaults to `remember()` and `store_session_fact()` | Add `stash()` to Core Protocol Rule 3 or 6 — one line change |
| `activities` (0 explicit) | No onboarding path; WCC cannot function without them | Create activities for major active projects; add to session-start guidance |
| WCC / `wcc_assembly` | Module absent from disk; silently disabled | Implement `wcc_assembly.py` OR mark all WCC BPMN aspirational |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/storage-system-analysis-part2.md
