---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- unified
synced: false
---

# Unified Storage Design — Index

**Status**: Draft for review
**Author**: Claude (architect)
**Date**: 2026-03-12
**Basis**: 10 audit documents, external research (Mem0, SimpleMem, Zettelkasten, hybrid BM25+vector)

## Document Map

| Section | File |
|---------|------|
| Principles + Tool Surface (5 tools) | [design-storage-tools.md](../knowledge-vault/10-Projects/claude-family/design-storage-tools.md) |
| Dossier Pattern + Storage Simplification | [design-storage-dossier.md](../knowledge-vault/10-Projects/claude-family/design-storage-dossier.md) |
| Retrieval, Maintenance, Migration | [design-storage-retrieval.md](../knowledge-vault/10-Projects/claude-family/design-storage-retrieval.md) |
| Task Tracking Fix + BPMN Cleanup | [design-storage-ops.md](../knowledge-vault/10-Projects/claude-family/design-storage-ops.md) |
| New Core Protocol | [design-new-core-protocol.md](design-new-core-protocol.md) |

## Design Summary

**15 mechanisms become 7. 15+ tools become 5.**

| New Tool | Replaces | Purpose |
|----------|----------|---------|
| `dossier()` | stash, unstash, list/search_workfiles, session notes, activity tools | Topic-based notepad |
| `remember()` | store_knowledge, partial store_session_fact | Atomic facts/patterns |
| `recall()` | recall_memories, recall_knowledge, graph_search, search_workfiles | Hybrid BM25+vector retrieval |
| `forget()` | (new) | Explicit knowledge removal |
| `consolidate()` | consolidate_memories, decay_knowledge | Maintenance (usually pg_cron) |

**Kept unchanged**: `store_session_fact()` (session notepad), `vault_embeddings` (reference), `MEMORY.md` (native).

## Key Decisions

1. **No tiers** — confidence score (0-100) replaces SHORT/MID/LONG. Retrieval sorts by confidence + recency + relevance.
2. **Dossier = index note** — Zettelkasten pattern on `project_workfiles` table. Open topic, jot notes, file when done.
3. **Hybrid search** — tsvector + pgvector RRF fusion in single SQL query. 15-30% retrieval improvement.
4. **Entropy gate** — before storing, check similarity > 0.75 means UPDATE not INSERT (Mem0/SimpleMem pattern).
5. **pg_cron** — autonomous maintenance at 3 AM. No dependency on Claude sessions.
6. **Dossier replaces WCC** — activity detection via open dossiers, not the absent `wcc_assembly.py`.

## Migration (6 weeks)

| Phase | Week | Change |
|-------|------|--------|
| 0 | Now | Drop dead tables (mcp_usage, enforcement_log, workflow_state, activities) |
| 1 | 1 | Add tsvector columns + triggers to knowledge and workfiles |
| 2 | 2 | Deploy dossier() tool, add to Core Protocol |
| 3 | 2 | Deploy recall() with RRF fusion, simplify RAG hook |
| 4 | 3 | Fix remember() (remove tiers, add entropy gate), deploy forget() |
| 5 | 3 | Task tracking: source column, closure gate, completion ratio |
| 6 | 4 | Deprecate old tools, deploy pg_cron maintenance |

## Metis Gate 2 Value

Dossier = Activity Space. Confidence ranking = Unified ranking. RRF = Retrieval path. pg_cron = Event-driven lifecycle. CF is the working prototype.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\design-unified-storage.md
