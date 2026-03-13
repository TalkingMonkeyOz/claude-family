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

# CF vs. Metis Alignment — Index

**Date**: 2026-03-12
**Scope**: Knowledge retrieval and assembly subsystem

## Document Map

| Section | File |
|---|---|
| 2-Tier vs 3-Tier, Unified Ranking, Co-Access, Event-Driven Promotion | [cf-metis-alignment-part1.md](../knowledge-vault/10-Projects/Project-Metis/audits/cf-metis-alignment-part1.md) |
| Dossier vs Workfiles, Full Alignment Score Table | [cf-metis-alignment-part2.md](../knowledge-vault/10-Projects/Project-Metis/audits/cf-metis-alignment-part2.md) |

## Overall Alignment: 35-40%

The architectural direction is correct. The gaps are implementation debt, not design misalignment.

## Critical Gaps (High Severity)

| Gap | Impact |
|---|---|
| WCC non-functional (`wcc_assembly.py` absent) | Activity-scoped retrieval silently disabled every session |
| 3 overlapping retrieval paths (no dedup) | Duplicate context; 400-600ms vs. < 200ms target |
| Task-completion promotion never fires | The most valuable promotion signal produces zero data |
| 96% of knowledge stuck at MID (promotion broken) | LONG tier provides no effective benefit |
| Workfile adoption near-zero (`stash()` not in Core Protocol) | Best-designed mechanism is invisible to Claude |

## Minimum Viable Path to Parity (8 Steps)

1. Deploy MID→LONG promotion fix — trivial code change, immediate benefit
2. Add `stash()` to Core Protocol — one line, drives adoption
3. Wire `mark_knowledge_applied()` into `complete_work()` — small, activates feedback loop
4. Replace 3 RAG paths with 1 parallel path + dedup — medium, halves latency
5. Add Activity embeddings + cosine detection — medium, fixes WCC detection
6. Ship `wcc_assembly.py` — medium, activates WCC
7. Replace `created_at` decay with `last_retrieved_at` + `freshness_score` — medium
8. Add `co_access_log` table (write only, no scoring yet) — small, starts signal accumulation

## Companion Document

Storage mechanism analysis: [storage-system-analysis.md](storage-system-analysis.md)

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\cf-metis-alignment.md
