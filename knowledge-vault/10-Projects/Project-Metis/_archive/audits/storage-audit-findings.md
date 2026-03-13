---
projects:
- claude-family
- project-metis
tags:
- audit
- storage
- findings
- recommendations
synced: false
---

# Storage Mechanisms Audit — Key Findings

**Index**: [storage-audit index](../../../docs/audit-storage-mechanisms.md) (relative: `docs/audit-storage-mechanisms.md`)
**Full analysis**: [Part 1](storage-audit-part1.md) | [Part 2](storage-audit-part2.md) | [Part 3](storage-audit-part3.md)
**Audit date**: 2026-03-12

---

## Critical Findings

**1. The knowledge promotion pipeline is broken.** 96% of knowledge entries (987 of 1,026) are stuck at MID tier. The MID→LONG criteria (`times_applied >= 3 AND confidence_level >= 80 AND access_count >= 5`) are rarely satisfied. The fix — retrieval-frequency-based promotion — was identified 2026-03-11 but not deployed. Until fixed, the LONG tier provides no meaningful benefit.

**2. The knowledge table is polluted with junk.** Session artifact strings (`agent1_complete`, `agent2_complete`) exist as knowledge entries at confidence=65. The quality gate in `remember()` (80-char minimum, junk pattern rejection, added 2026-03-11) prevents new junk but does not clean the ~40-50 existing junk entries. A data cleanup pass is required before any meaningful knowledge analysis.

**3. 6,965 rows of synthetic mcp_usage data waste storage and corrupt any usage analysis.** The `mcp_usage_logger.py` hook never wrote real session_ids — all 6,965 rows are synthetic. Any tool-usage frequency analysis using this table returns garbage. The table should be truncated immediately.

**4. The enforcement_log is a zombie.** `process_router.py` was archived 2026-02-28 but had already written 1,333 rows to `enforcement_log`. Nothing reads or writes this table. Truncate and consider DROP.

**5. WCC cannot function at current adoption levels.** The WCC architecture requires both active workfiles and a recognized activity. With 3 workfiles and 0 explicit activities, WCC never assembles and the system falls through to per-source RAG queries — the same queries the main RAG hook runs anyway. WCC is currently a no-op adding 400-600ms latency per cache miss.

---

## Adoption Findings

**6. Project workfiles (best-designed mechanism) have near-zero adoption.** Only 3 entries across 24 active projects after 3 days. Root cause: the Core Protocol (8 rules injected every prompt) does not mention `stash()`. Without protocol-level prompting, Claude defaults to `remember()` and `store_session_fact()`. Adding `stash()` to Core Protocol Rule 3 or 6 would likely drive adoption immediately.

**7. MEMORY.md is the highest-quality mechanism but exists for only 1 of 24 projects.** The claude-family MEMORY.md (232+ lines) is well-structured, always-injected, and captures exactly the content that should be in LONG-tier knowledge. Other projects have no equivalent. The patterns and gotchas in MEMORY.md are not systematically replicated to the DB.

**8. Session notes files serve 7 projects but overlap with 3 other mechanisms.** Each file is append-only, unstructured, and contains a mix of decisions, progress tracking, and findings — all of which could live in session_facts, knowledge, or workfiles. No clear protocol defines what goes in notes vs. other stores. Notes are the lowest-fidelity mechanism (no search, no embeddings, no budget management).

---

## Architecture Findings

**9. Five stores overlap for "things Claude learned."** A gotcha discovered in a session can simultaneously exist in: session_facts (note type), knowledge MID (via `remember()`), knowledge LONG (if typed as pattern), vault embeddings (if written to vault doc), MEMORY.md (if memory tool used), AND session notes file. No cross-references link these duplicates. Deduplication is manual and rare.

**10. The knowledge graph adds complexity without meaningful benefit.** 67 edges across 717+ nodes (9.3% edge:node ratio). Only the `relates_to` edge type has ever been created — the 6 other types (`extends`, `contradicts`, `supersedes`, etc.) have never been instantiated. Graph-discovered entries receive a fixed score of 0.3, ranking them below all direct matches regardless of relevance. At current scale, the 1-hop graph walk in `recall_memories()` rarely returns useful additions.

**11. Cross-session fact recovery is session-count dependent, not time-based.** `recall_previous_session_facts()` scans back exactly 3 sessions. A project running 20 sessions/day loses day-1 decisions by day 2; a project with weekly sessions retains them for weeks. The inconsistency is a design flaw. Recommended fix: add `is_important` boolean flag to session_facts, or auto-promote `decision`/`credential` facts to `knowledge` at session end.

**12. The vault embeddings system is the reference implementation.** 9,655+ chunks, 100% embedding coverage (NOT NULL constraint), HNSW index, incremental re-embedding by SHA-256 hash, clear doc_source taxonomy. All other semantic mechanisms (knowledge, workfiles, bpmn_processes) have weaker guarantees. Any redesign of the knowledge system should match vault embeddings' coverage and maintenance discipline.

---

## Recommended Priority Actions

| Priority | Action | Mechanism | Effort |
|----------|--------|-----------|--------|
| P1 | Truncate `mcp_usage` (corrupts analysis) | mcp_usage | 5 min |
| P1 | Truncate `enforcement_log` (zombie) | enforcement_log | 5 min |
| P1 | Deploy knowledge promotion fix (retrieval-frequency) | knowledge LONG | Medium |
| P1 | Add `stash()` to Core Protocol Rule 3 or 6 | project_workfiles | 15 min |
| P2 | Bulk-delete junk knowledge entries (agent_complete, etc.) | knowledge MID | Small |
| P2 | Add `knowledge_retrieval_log` write to `tool_recall_memories` | knowledge_retrieval_log | Small |
| P3 | Add `is_important` flag to session_facts for time-independent retention | session_facts | Medium |
| P3 | Create explicit activities for major active projects | activities/WCC | Small |
| P4 | Remove or reduce 1-hop graph walk from `recall_memories()` (marginal benefit) | knowledge_relations | Small |
| P4 | Add provenance FK from `knowledge` to `vault_embeddings` | knowledge/vault | Medium |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-findings.md
