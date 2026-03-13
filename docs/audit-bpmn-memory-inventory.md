---
projects:
- claude-family
tags:
- audit
- bpmn
- memory
synced: false
---

# BPMN Memory Audit — Process Inventory

**Parent**: [audit-bpmn-memory-analysis.md](audit-bpmn-memory-analysis.md)

## Process Table

| process_id | tasks | gateways | events | key actors | data stores | alignment |
|---|---|---|---|---|---|---|
| `cognitive_memory_capture` | 11 | 5 | 3 | CLAUDE, HOOK, KMS, DB | claude.knowledge, claude.knowledge_relations | 85% |
| `cognitive_memory_retrieval` | 8 | 2 | 2 | KMS, DB | claude.knowledge, claude.session_facts, claude.project_workfiles | 90% |
| `cognitive_memory_consolidation` | 10 | 5 | 2 | KMS, DB | claude.knowledge, claude.session_facts | 80% |
| `cognitive_memory_contradiction` | 9 | 4 | 2 | KMS, DB | claude.knowledge, claude.knowledge_relations | 70% |
| `working_memory` | 12 | 5 | 2 | CLAUDE, MCP, HOOK, DB | claude.session_facts, claude.project_workfiles | 90% |
| `work_context_assembly` | 13 | 5 | 3 | HOOK, DB | 6 sources: workfiles, knowledge, features, facts, vault, BPMN | 55% |
| `workfile_management` | 11 | 2 | 2 | CLAUDE, MCP, DB, AI | claude.project_workfiles | 95% |
| `knowledge_full_cycle` | 22 | 8 | 2 | CLAUDE, KM, DB, HOOK, SCRIPT | claude.knowledge, claude.book_references, claude.books, claude.conversations | 75% |
| `knowledge_graph_lifecycle` | 18 | 6 | 2 | CLAUDE, DB, AGE | claude.knowledge, claude.knowledge_relations, AGE graph | 20% |
| `rag_pipeline` | 7 | 3 | 5 | HOOK, DB, AI | vault embeddings, pgvector | 85% |
| `L1_knowledge_management` | 6 | 2 | 2 | CLAUDE, KM, DB, HOOK | claude.knowledge | 50% |
| `precompact` | 8 | 2 | 2 | TOOL, DB, FILE | claude.session_facts, claude.project_workfiles, claude.session_state | 95% |
| `context_preservation` | 10 | 5 | 6 | FILE, HOOK, DB | context_health.json, claude.session_state | 60% |

**Overall estimated alignment**: 72%

## Alignment Notes by Process

**cognitive_memory_capture** — Implemented via `server.py:tool_remember()`. Dedup threshold mismatch: model says 0.85, code uses 0.75. Contradiction check is inline in code, not a subprocess call as the model implies.

**cognitive_memory_retrieval** — Implemented via `server.py:tool_recall_memories()`. The 4-branch parallel search (short/mid/long/workfiles) matches code exactly. Budget allocation profiles (`task_specific`, `exploration`, `default`) also match.

**cognitive_memory_consolidation** — MID→LONG promotion criteria stale. Model comment says `times_applied >= 3`; code uses `access_count >= 5 AND age >= 7d`. Session-end hook performs a separate lightweight consolidation (no Voyage AI) that is not fully modeled.

**cognitive_memory_contradiction** — The four relationship types (extends, reinforces, contradicts, supersedes) and scoring heuristics are modeled correctly. In code these run inline within `tool_remember()` rather than as a separate invocation.

**working_memory** — All five action paths aligned except Path 3 (compaction) which duplicates `precompact`. See overlaps analysis.

**work_context_assembly** — WCC BPMN is well-specified. `wcc_assembly` module import in `rag_query_hook.py` silently fails with warning: "wcc_assembly module not found — WCC disabled". Module does not exist in `mcp-servers/project-tools/` or `scripts/`.

**workfile_management** — Highest fidelity model in the subsystem. All four paths (stash/unstash/list/search) match code exactly including UPSERT behaviour and Voyage AI embedding.

**knowledge_full_cycle** — Comprehensive but large (22 tasks). Paths 2 and 5a duplicate `rag_pipeline`. Path 4 (conversation mining) and Path 3 (book references) are correct but have no standalone models.

**knowledge_graph_lifecycle** — Entirely aspirational. No Apache AGE extension installed. Current graph capability is `claude.knowledge_relations` table + pgvector + recursive CTE (modeled in `cognitive_memory_retrieval` search_long path).

**rag_pipeline** — Correct and well-aligned. Duplicates `knowledge_full_cycle` Paths 2 and 5a.

**L1_knowledge_management** — Pre-F130 stub. Superseded by `knowledge_full_cycle`. Should be retired or converted to a call-reference placeholder.

**precompact** — Fully aligned. All 5 query steps, pinned workfiles, token budget cap (2000 tokens), and priority order (P0–P4) match `scripts/precompact_hook.py`.

**context_preservation** — StatusLine sensor scripts exist (`context_monitor_statusline.py`, `.sh`). Advisory and directive injection confirmed in `rag_query_hook.py:_check_context_health()`. Red-level tool blocking in `task_discipline_hook.py` (`check_context_health_gate`) — present but alignment with model unverified.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\audit-bpmn-memory-inventory.md
