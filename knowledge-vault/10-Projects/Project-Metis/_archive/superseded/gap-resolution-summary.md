---
tags:
  - project/Project-Metis
  - scope/system
  - type/gap-resolution
created: 2026-02-26
updated: 2026-02-28
---

# Gap Review — Complete Resolution Summary

All gaps from the original session prep doc, resolved Feb 25-26 across two sessions.

## Critical Gaps (Red)

| Gap | Area | Resolution | Status |
|-----|------|-----------|--------|
| GAP-1: Knowledge Graph | Area 1 | 8 relationship types, knowledge_relations table, graph walk for /ask, AI-suggested links | ✅ RESOLVED Feb 25 |
| GAP-2: Integration Hub design | Area 2 | Standardised 8-method connector interface + 6 middleware layers + connector_configs table | ✅ RESOLVED Feb 25 |
| GAP-3: Session Memory | Area 7 | Parked. Claude Code building cognitive memory (3-tier, PostgreSQL). John gave 5 decisions. | ⏸️ PARKED |
| GAP-4: Evaluation Framework | Area 1 | 50 test questions (4 categories), 3 metrics (precision >80%, correctness >85%, hallucination <5%), regression alerts | ✅ RESOLVED Feb 26 |

## Important Gaps (Yellow)

| Gap | Area | Resolution | Status |
|-----|------|-----------|--------|
| GAP-5: Chunking Strategy | Area 1 | Natural boundaries per knowledge type. Tune during Phase 1 based on eval metrics. | ✅ RESOLVED Feb 26 |
| GAP-6: Knowledge Staleness | Area 1 | Event-driven dependency tracking. Knowledge linked to what it depends on; when dependency changes, system flags affected items for review. Not time-based. | ✅ RESOLVED Feb 27 (FB148) |
| GAP-7: BPMN for MVP | Area 9 | 3 processes: knowledge ingestion/validation, delivery pipeline stage gate, defect triage | ✅ RESOLVED Feb 26 |
| GAP-8: Two-Way Sync | Area 5 | Intelligent triage layer, not dumb field sync. Pull changes from external → AI classifies → route to appropriate handler. Last-write-wins + conflict log for MVP. | ✅ RESOLVED Feb 27 (FB149) |
| GAP-9: Background Job Scheduling | Area 4+7 | Jobs table + simple cron runner. Phase 2 deliverable. | ✅ RESOLVED Feb 26 |
| GAP-10: External Rule Discovery | Area 4 | 4 signal sources: code changes (primary), API monitoring, manual triggers, scheduled scans. Code access is management decision. | ✅ RESOLVED Feb 27 (FB150) |
| GAP-11: Commercial Model (System) | Area 8 | Monthly subscription direction. Detail deferred to customer #2. Platform needs basic usage metering hooks from day one. | ⏸️ PARKED with direction (FB151) |

## Cross-Area Alignment

| Issue | Resolution | Status |
|-------|-----------|--------|
| CROSS-1: BPMN → Quality test gen interface | BPMN registry (bpmn_processes table) already queryable. Test generator consumes it. | ✅ RESOLVED |
| CROSS-2: Two-way sync ownership | Sync service uses connectors (business logic), not built into connectors (transport). Full sync deferred. | ✅ RESOLVED |
| CROSS-3: Job scheduling for background agents | See GAP-9. Jobs table + cron runner. | ✅ RESOLVED |
| CROSS-4: Knowledge tier → BPMN routing | Single BPMN process (ingestion/validation) with tier-based conditional routing. Not 4 separate processes. | ✅ RESOLVED |

## Additional Gaps (Identified & Resolved Feb 26-27)

| Gap | Area | Resolution | Status |
|-----|------|-----------|--------|
| GAP-12: Multi-Product Customers | Area 7 | Scope hierarchy: Org → Product → Client → Engagement. Rigid top levels, flexible sub-levels. | ✅ RESOLVED Feb 27 (FB152) |
| GAP-13: Customer Scenario Replication | Area 4 | AI-assisted investigation flow, not just env cloning. Multi-step: check KMS → check code → form hypotheses → test → resolve. | ✅ RESOLVED Feb 27 (FB153) |
| GAP-14: Generic Integration Catalogue | Area 2 | Common services data layer with integration categories, not exhaustive catalogue. Core vs optional connectors. | ✅ RESOLVED Feb 27 (FB154) |
| GAP-15: Dog-Fooding Loop | All | Platform uses itself — same supervised pattern. KMS stores self-knowledge, pipeline tracks own releases, quality tools test own code. | ✅ RESOLVED Feb 27 (FB155) |
| GAP-16: Client-Facing Self-Service Portal | Area 3/6 | Future-phase. Groundwork in scope hierarchy (GAP-12) + constrained deployment (Doc 6, all 4 layers for untrusted users). | ✅ RESOLVED Feb 27 (FB156) |

## Scorecard

| Category | Resolved | Parked | Total |
|----------|----------|--------|-------|
| Critical (Red) | 3 | 1 (Session Memory) | 4 |
| Important (Yellow) | 7 | 0 | 7 |
| Cross-Area | 4 | 0 | 4 |
| Additional (Feb 27) | 4 | 1 (Commercial) | 5 |
| **TOTAL** | **18** | **2** | **20** |

All gaps resolved or parked with clear direction. No open questions blocking Phase 0 or Phase 1.

---
*Created: 2026-02-26 | Updated: 2026-02-28*
