---
projects:
- claude-family
tags:
- audit
- bpmn
- memory
synced: false
---

# BPMN Memory Subsystem Audit — Index

**Date**: 2026-03-12
**Scope**: 13 BPMN processes covering cognitive memory, workfile, RAG, and knowledge management

## Executive Summary

The memory subsystem is modeled across 13 BPMN processes. Core F130 cognitive memory tools (`remember`, `recall_memories`, `consolidate_memories`) and all four workfile tools are well-implemented. Three critical gaps exist: the `wcc_assembly` module referenced by `rag_query_hook.py` is absent from disk (WCC disabled at runtime), the `knowledge_graph_lifecycle` model depends on Apache AGE which is not installed, and `L1_knowledge_management` is an obsolete stub. Overall model-to-code alignment is estimated at **72%**. Two threshold values in BPMN models disagree with code (dedup: model=0.85, code=0.75), and MID→LONG promotion criteria in the consolidation model are stale.

## Document Map

| Section | File |
|---|---|
| Process Inventory (all 13 processes, element counts, alignment %) | [audit-bpmn-memory-inventory.md](audit-bpmn-memory-inventory.md) |
| Overlap Analysis (5 identified overlaps) | [audit-bpmn-memory-overlaps.md](audit-bpmn-memory-overlaps.md) |
| Data Flow Trace + Gap Analysis | [audit-bpmn-memory-gaps.md](audit-bpmn-memory-gaps.md) |
| Simplification Recommendations + Key Findings | [audit-bpmn-memory-recommendations.md](audit-bpmn-memory-recommendations.md) |

## Quick-Reference: Alignment by Process

| Process | Alignment | Status |
|---|---|---|
| `workfile_management` | 95% | Fully aligned |
| `precompact` | 95% | Fully aligned |
| `working_memory` | 90% | Well-aligned, 1 redundant path |
| `cognitive_memory_retrieval` | 90% | Well-aligned |
| `rag_pipeline` | 85% | Well-aligned, overlaps knowledge_full_cycle |
| `cognitive_memory_capture` | 85% | Well-aligned, dedup threshold stale |
| `cognitive_memory_consolidation` | 80% | Promotion criteria stale |
| `knowledge_full_cycle` | 75% | Active, overlaps rag_pipeline |
| `cognitive_memory_contradiction` | 70% | Partial impl (inline not subprocess) |
| `work_context_assembly` | 55% | wcc_assembly.py missing |
| `context_preservation` | 60% | StatusLine exists, blocking unconfirmed |
| `knowledge_graph_lifecycle` | 20% | AGE not installed — aspirational |
| `L1_knowledge_management` | 50% | Obsolete stub |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/audits/audit-bpmn-memory-analysis.md
