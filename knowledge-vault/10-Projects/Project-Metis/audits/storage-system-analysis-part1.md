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

# Storage System Analysis — Overlap Map, Gap Map, Usage Heatmap

**Part 2**: [Notepad Model + Dead Mechanisms](storage-system-analysis-part2.md)
**Index**: [docs/storage-system-analysis.md](../../../docs/storage-system-analysis.md)
**Synthesized from**: storage-audit-part1/2/3, bpmn-memory audits, task-tracking-audit, audit-structured-data
**Date**: 2026-03-12

---

## 1. Overlap Map

The same content type can exist in multiple stores simultaneously. This maps every mechanism, identifies the authoritative one, and flags the redundant paths.

| Content Type | All Mechanisms | Authoritative | Redundant / Problem |
|---|---|---|---|
| **Credentials** | session_facts (credential type), knowledge MID (if `remember()` called), MEMORY.md | session_facts | knowledge MID is noise for credentials |
| **Decisions** | session_facts (decision), knowledge MID, session notes, MEMORY.md, vault docs | session_facts → knowledge LONG | 5-way overlap; no auto-pathway |
| **Learned facts / gotchas** | session_facts (note), knowledge MID, knowledge LONG, vault_embeddings, MEMORY.md, session notes | knowledge LONG + MEMORY.md | 6-way overlap; no cross-reference; deduplication is manual and rare |
| **Patterns / procedures** | knowledge LONG, vault (30-Patterns/, 40-Procedures/), MEMORY.md | vault_embeddings (100% coverage) + knowledge LONG | MEMORY.md is highest-fidelity but single-project only |
| **Work context (what is being done)** | session_facts (current_activity), activities table, precompact session_state, session notes | session_facts override → WCC (non-functional) | WCC disabled at runtime; 4-way overlap |
| **Feature / task progress** | build_tasks, todos, session notes, session_facts (reference) | build_tasks | todos–build_tasks bridge unreliable (75% fuzzy) |
| **Open questions** | session_facts (note), project_workfiles, session notes, knowledge MID | project_workfiles (designed for this) | workfiles have 3 rows; effectively unused |
| **Structured reference (Nimbus OData)** | nimbus_context schema (366 entities), vault 20-Domains/APIs/ | nimbus_context schema | Nimbus-only; no equivalent for other domains |
| **Structured reference (non-Nimbus APIs)** | vault 20-Domains/APIs/ (4 gotcha docs only), knowledge MID (narrative) | No authoritative home | Gap — no schema-level store exists |
| **Project documentation** | vault_embeddings, claude.documents, CLAUDE.md (DB + file) | vault_embeddings | CLAUDE.md has DB-file split requiring extra maintenance |
| **Cross-session component context** | project_workfiles (designed for this), session notes (used for this) | project_workfiles | session notes pre-date workfiles; overlap unresolved |
| **Inter-Claude messages** | claude.messages | claude.messages | Clean; no overlap |
| **State machine transitions** | claude.audit_log | claude.audit_log | Clean; no overlap |

**Worst overlap**: "Learned facts / gotchas" — 6 mechanisms, no automatic cross-reference, no deduplication. Default outcome is content duplication across all 6.

---

## 2. Gap Map

Content types with no adequate home in the current system.

| Content Type | Gap Description | Root Cause |
|---|---|---|
| **Structured reference (non-Nimbus)** | API schemas, OData definitions, integration contracts have no schema-queryable store. vault 20-Domains/ holds 4 narrative gotcha docs only. | CF was built around Nimbus; no generic API schema layer exists |
| **Inter-session narrative continuity** | No mechanism assembles "what happened on this topic over the last week." session_facts expire within 3 sessions. Session notes are append-only/unstructured. MEMORY.md is manually maintained. | Designed for within-session recall, not topic narrative |
| **Feedback triage workflow state** | `failure_capture.py` auto-files bugs. Nothing triages them. Feedback accumulates at `new` status with no driver. | No triage protocol; state machine exists but nobody drives it |
| **Task closure enforcement** | Tasks are created (discipline hook enforces). Tasks are never closed. No hook or protocol enforces task completion. Auto-archive moves zombies silently. | Enforcement oriented entirely toward creation, not closure |
| **Cross-project knowledge sharing** | 24 active projects share one `claude.knowledge` table with no project partitioning. Nimbus payroll data sits next to CF infrastructure patterns. | No tenant/project scoping on knowledge table; cross-project bleed uncontrolled |
| **Activity-scoped retrieval** | WCC was designed to pre-scope retrieval to current activity. `wcc_assembly.py` is absent from disk. WCC silently disabled every session. | WCC module never shipped |

---

## 3. Usage Heatmap

Ordered by actual impact on Claude's effectiveness.

| Mechanism | Row Count | Growth | Quality | Impact |
|---|---|---|---|---|
| `vault_embeddings` | ~12,345 chunks | ~2,700/large update | High — 100% embedding coverage, HNSW index | Highest — primary RAG source every prompt |
| `session_facts` | ~676 | ~23/day | Medium — note/decision healthy; cross-session recovery fragile | High — sole reliable cross-session notepad |
| `knowledge` MID | ~930 | ~40/week | Low — 40-50 junk entries; cross-project bleed; fixed confidence=65 | Medium — noisy but surface area is large |
| `todos` | 2,711 | High churn | Low — two overlapping systems; zombie accumulation | Medium via discipline hook; zero tracking value |
| `sessions` | ~906 | ~5-10/day | Medium — summary NULL for most | Low direct; FK anchor for other tables |
| `knowledge` LONG | ~127 | Very slow (pipeline broken) | High potential; low current (96% MID stuck) | Low current; high if promotion fixed |
| MEMORY.md | 232 lines | Sporadic | High — curated, always-injected | High for claude-family; zero for 23 other projects |
| `build_tasks` | Unknown | Low | Poor — fuzzy bridge fails silently | Low — tracking theatre |
| `audit_log` | 254 | Low | High — immutable, correct | Low frequency; high fidelity when used |
| `project_workfiles` | 3 | Near-zero | High design quality; zero population | Near-zero current; high potential |
| Session notes files | 7 files | Sporadic | Low — append-only, no search | Low; fills gaps sporadically |
| `activities` / WCC | 0 explicit | None | N/A — wcc_assembly.py absent | Zero current impact |
| `knowledge_relations` | 67 edges | Very slow | Low — 9.3% edge:node ratio; fixed 0.3 score | Near-zero; adds latency without benefit |
| `mcp_usage` | 6,965 | Frozen | None — all synthetic NULL session_id | Negative — corrupts usage analysis |
| `enforcement_log` | 1,333 | Frozen | None — process_router retired | Negative — wasted storage |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/storage-system-analysis-part1.md
