---
tags:
  - project/Project-Metis
  - type/export
  - auto-generated
created: 2026-03-14
updated: 2026-03-14
---

# METIS Entity Catalog Export

Auto-generated from `claude.entities` table. For live queries use MCP tools:
```
recall_entities("query", entity_type="decision|gate_deliverable|design_document")
```

---

## Validated Decisions (13)

All validated 2026-03-08 by John de Vere. Source: `plan-of-attack-rewrite-brief.md`

| # | Decision | Impact Areas | Rationale |
|---|----------|-------------|-----------|
| 1 | Build from zero | architecture, codebase | Clean build, not CF fork. CF = lessons learned, not codebase |
| 2 | Area-level features (F119-F128) | planning, work-tracking | Old F1-F10 retired. DB features as organising structure |
| 3 | Augmentation Layer is core Phase 1 | phase-1, augmentation-layer | Dog-fooding: if tools can't help build METIS, they can't help anything |
| 4 | Phase 2 is streams, not monolith | phase-2, delivery | ONE stream end-to-end, incremental value, not big-bang |
| 5 | Generic framing, nimbus as lead example | scope, documentation | Generic phases, nimbus/Monash as concrete example |
| 6 | Platform-agnostic infrastructure | infrastructure, deployment | No Azure specifics. Any Linux + PostgreSQL + pgvector |
| 7 | Separate DB per customer, no RLS | database, multi-tenancy | Separate instances. Org>Product>Client>Engagement hierarchy |
| 8 | Content-aware chunking | knowledge-engine, chunking | Different strategies per content type. Token count mandatory |
| 9 | No keyword matching in retrieval | retrieval, routing | Embeddings only. 4-level activity detection hierarchy |
| 10 | Single ranking pipeline, 6 signals | retrieval, ranking | vector(0.55) + co-access(0.30) + task(0.15) + freshness + recency + feedback |
| 11 | Event-driven freshness | knowledge-engine, freshness | Stale through change events, not time. freshness_score 0.0-1.0 |
| 12 | MVP = one stream end-to-end | scope, mvp, delivery | AI knows domain, assists workflow, gets smarter with each interaction |
| 13 | System vs customer blockers | planning, risk-management | Separate platform blockers from deployment-specific blockers |

---

## Gate Deliverables (9)

### Gate 0 — COMPLETE ✅

| Deliverable | Status | Source File |
|-------------|--------|------------|
| Problem Statement | validated | `gates/gate-zero/problem-statement.md` |
| Assumptions & Constraints | validated | `gates/gate-zero/assumptions-constraints.md` |
| Stakeholders & Decision Rights | validated | `gates/gate-zero/stakeholders-decision-rights.md` |
| System Map (C4 L1/L2) | validated | `gates/gate-zero/system-map.md` |

### Gate 1 — DRAFT COMPLETE

| Deliverable | Status | Source File |
|-------------|--------|------------|
| Actor Map | draft | `gates/gate-one/actor-map.md` |
| Process Inventory | draft | `gates/gate-one/process-inventory.md` |
| Data Entity Map | draft | `gates/gate-one/data-entity-map.md` |
| Business Rules Inventory | draft | `gates/gate-one/business-rules-inventory.md` |
| Integration Points | draft | `gates/gate-one/integration-points.md` |

---

## Design Documents (3)

| Document | Status | Description |
|----------|--------|-------------|
| Security Architecture | validated | Trust boundaries, auth, data isolation, audit logging |
| Ethos - Design Principles | validated | Knowledge compounds, augmentation not replacement, dog-fooding |
| Feature Catalogue | draft | F119-F128 feature definitions across 9+1 areas |

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/Project-Metis/CATALOG_EXPORT.md
