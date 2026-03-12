---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- unified
- index
synced: false
---

# Unified Storage Design — Overview

**Status**: Draft (design complete, pending implementation)
**Origin**: Comprehensive audit (8 docs) + online research (filing systems, library science, external memory frameworks)
**Audit docs**: `docs/audit-*.md` (8 files covering storage, BPMN, tasks, structured data)
**Research**: See [Research Basis](#research-basis) below

---

## Problem

Claude Family has 15 storage mechanisms, most broken or unused. Knowledge is 96% stuck at MID tier (promotion broken). Workfiles have zero adoption despite best design. WCC is silently disabled (`wcc_assembly.py` doesn't exist). Task tracking enforces creation but not closure.

**Key constraint**: "It can't be 2 separate systems — they have to be integrated." All storage, retrieval, and protocol changes must work as one coherent system.

---

## Solution: 3 Tools, 7 Mechanisms

Reduce from 15 mechanisms to 7, and from ~15 MCP tools to 3 primary tools.

| Tool | Purpose | Backing Store |
|------|---------|---------------|
| `dossier(topic, note)` | Multi-session topic notepads | `project_workfiles` |
| `remember(content)` | Permanent facts/patterns | `knowledge` |
| `recall(query)` | Unified search (all sources) | RRF over vault + knowledge + workfiles |

Plus existing: `store_session_fact()` (session-scoped), `MEMORY.md` (always-loaded).

---

## Design Documents

| Document | Covers |
|----------|--------|
| [design/storage-dossier.md](design/storage-dossier.md) | Dossier pattern, storage simplification (15→7), drop/freeze decisions |
| [design/storage-tools.md](design/storage-tools.md) | 3-tool API design, principles, what each replaces |
| [design/storage-retrieval.md](design/storage-retrieval.md) | Hybrid BM25+vector RRF retrieval, tsvector schema, RAG hook redesign |
| [design/storage-ops.md](design/storage-ops.md) | Task tracking closure gate, BPMN cleanup, maintenance |
| [design-new-core-protocol.md](design-new-core-protocol.md) | Core Protocol v11→v12 changelog, proposed text |
| [design/core-protocol-detail.md](design/core-protocol-detail.md) | Rule-by-rule design rationale |
| [design/entities-system.md](design/entities-system.md) | Entities system overview, 3 tables + 2 tools |
| [design/entities-schema.md](design/entities-schema.md) | DDL, indexes, triggers, type registry |
| [design/entities-tools-lifecycle.md](design/entities-tools-lifecycle.md) | catalog() tool, recall() CTE, data migration |
| [design/entities-integration.md](design/entities-integration.md) | Claude Code boundaries, filing, session integration |

---

## Audit Findings (Summary)

| Area | Key Finding |
|------|-------------|
| Storage | 96% knowledge stuck at MID. Promotion broken. 6,965 synthetic mcp_usage rows. |
| BPMN | 13 models, 72% alignment. `wcc_assembly.py` absent. AGE graph unimplemented. |
| Tasks | Compliance theater. Creation enforced, closure never enforced. |
| Structured data | nimbus-knowledge is project-scoped (working). Non-Nimbus has zero schema infra. |

Full audit details in `docs/audit-*.md`.

---

## Research Basis

The design is grounded in three research streams conducted before the design phase:

### Filing and Records Management
**Source**: [[filing-records-management-research]] (Project Metis vault)

Key principle adopted: The `(project, component, title)` triple in `project_workfiles` maps directly to **alphanumeric classification** — project is the broadest category, component narrows to a topic, title identifies the specific item. The dossier pattern is literally a digital "file folder" from records management. Cross-cutting retrieval (the fundamental problem of subject filing) is solved by semantic search as a complementary path alongside the classification hierarchy.

### Library Science and Cataloging
**Source**: [[library-science-research]] (Project Metis vault)

Key principles adopted:
- **Faceted classification** (Ranganathan) — knowledge has multiple independent facets (topic, project, time, type). Our confidence-ranked single-table approach avoids Dewey's rigid hierarchy problems.
- **Controlled vocabulary** — the dedup/merge entropy gate (`cosine > 0.75 → merge`) acts as an automatic controlled vocabulary, preventing "staff"/"personnel"/"employees" from becoming 3 separate entries.
- **FRBR-style work/expression/manifestation** — a dossier `_index` is the "work" while entries are "expressions" of knowledge accumulated over time.

### External Memory Systems
**Source**: `docs/research/` (7 docs, [[key-findings-summary]] is entry point)

10+ frameworks evaluated. Adopted patterns:
| Pattern | Source | Where in Design |
|---------|--------|-----------------|
| Update-over-accumulate | Mem0 | Entropy gate in `remember()` |
| Semantic lossless compression | SimpleMem (26.4% F1 gain) | Dedup merge in `consolidate()` |
| Hybrid BM25+vector+RRF | pgvector + tsvector | `recall()` single retrieval path |
| Autonomous maintenance | pg_cron | Daily 3AM job, no session dependency |
| 3-5 simple tools | Industry consensus | `dossier()`, `remember()`, `recall()` |

**Not adopted** (and why): Neo4j (Zep/Graphiti requires it), Redis, external vector DBs. PostgreSQL + pgvector + Voyage AI is sufficient.

### Integration Gap: Automatic Extraction

The research recommends Mem0's pattern of **automatic fact extraction on session end** — an LLM pass over the conversation to extract key decisions/patterns without requiring manual `remember()` calls. This is NOT yet in the design and should be added as Phase 4.5 (between "Remember fix" and "Task fix" in the implementation sequence).

---

## Implementation Sequence

1. **Database cleanup** — Drop dead tables (mcp_usage, enforcement_log, activities, etc.)
2. **Schema changes** — Add tsvector columns, source column on todos, confidence backfill
3. **Dossier tool** — New MCP tool wrapping project_workfiles with _index pattern
4. **Unified recall** — RRF hybrid search replacing 3 parallel RAG paths
5. **Remember fix** — Remove tier routing, add entropy gate, confidence-only ranking
6. **Auto-extraction** — LLM pass on session end to extract facts/decisions (Mem0 pattern)
7. **Core Protocol v12** — Update protocol_versions, deploy to all projects
8. **Closure gate** — Session-end task review in session_end_hook.py
9. **BPMN model updates** — Update/create models for new workflows (dossier_lifecycle, unified_retrieval)
10. **Deprecation** — Mark old tools deprecated, 30-day grace period, then remove

---

**Version**: 1.1
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/README.md
