---
tags:
  - project/Project-Metis
  - scope/system
  - level/0
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-03-14
---

# Project METIS — Navigator

Enterprise AI platform that learns domain knowledge and does the work, not just answers questions.

**Project code**: METIS | **Vault**: `knowledge-vault/10-Projects/Project-Metis/`

---

## Gate Progress

| Gate | Status | Deliverables |
|------|--------|-------------|
| **Gate 0** | COMPLETE ✅ | 5/5 validated — problem statement, assumptions, stakeholders, system map, ethos |
| **Gate 1** | DRAFT COMPLETE ✅ | 5/5 draft — process inventory, actor map, data entity map, business rules, integration points |
| **Gate 2** | Material indexed | 12 deliverables assessed (5%–75% complete). Formal work not started |
| **Gate 3** | Material indexed | 8 deliverables assessed (5%–70% complete). Formal work not started |
| **Gate 4** | Not applicable | Release readiness — future |

**Master tracker**: `gates/design-lifecycle.md`

---

## Active Files

| File | Purpose | Status |
|------|---------|--------|
| `gates/design-lifecycle.md` | Master lifecycle + progress tracker | **Active** |
| `plan-of-attack-rewrite-brief.md` | 13 validated decisions for plan rewrite | Validated |
| `ethos.md` | Design principles | Validated |
| `security-architecture.md` | Security model, trust boundaries | Validated |
| `feature-catalogue.md` | Feature definitions (F119-F128) | Draft |
| `system-product-definition.md` | Scope, areas, architecture | v0.3 |

### Gate Folders

| Folder | Contents |
|--------|----------|
| `gates/gate-zero/` | 4 validated deliverables + system-map.html |
| `gates/gate-one/` | 5 draft deliverables (needs human review) |
| `gates/gate-two/` | README.md material index |
| `gates/gate-three/` | README.md material index |

### Design & Research

| Folder | Contents |
|--------|----------|
| `research/` | 18 research papers — schema audits, impl audits, WCC options |
| `wcc/` | 5 WCC design docs — ranking, routing, activity space, mechanics |
| `data-model/` | 2 data model docs — prototype, table assessments |
| `orchestration-infra/` | 15 infrastructure design docs |
| `bpmn-maps/` | 3 BPMN process maps |

### Supporting

| Folder | Contents |
|--------|----------|
| `knowledge-engine/` | Knowledge engine brainstorm + graph relationships |
| `integration-hub/` | Connector interface design |
| `project-governance/` | PM lifecycle, client timelines |
| `ps-accelerator/` | Delivery accelerator brainstorm |
| `quality-compliance/` | Quality & compliance brainstorm |
| `support-defect-intel/` | Support intelligence (placeholder) |
| `commercial/` | Commercial model (placeholder) |
| `skills/` | Design coherence + gate framework skills |
| `decisions/` | Decision registry (placeholder) |
| `session-handoffs/` | 1 active handoff (latest: 2026-03-14) |
| `_archive/` | 64 archived files (old handoffs, audits, superseded docs) |

---

## Entity Catalog (DB-Searchable via MCP)

All key artifacts are cataloged with Voyage AI embeddings for semantic search:

```
# 13 validated strategic decisions
recall_entities("metis decision", entity_type="decision")

# 9 gate deliverables (Gate 0 + Gate 1)
recall_entities("metis gate deliverable", entity_type="gate_deliverable")

# 3 active design documents
recall_entities("metis design document", entity_type="design_document")
```

---

## Workfile Dossiers (MCP project-tools)

Quick context loading for any Claude instance:

```
unstash("metis-active")   # Pinned navigator — what's active + where to find it
unstash("metis-gate-0")   # Gate 0 completed summary
unstash("metis-gate-1")   # Gate 1 draft complete summary
unstash("metis-gate-2")   # Gate 2 status + completeness estimates
```

---

## 13 Validated Decisions (2026-03-08)

From `plan-of-attack-rewrite-brief.md` — all validated by John:

1. **Build from zero** — clean build, not a CF fork
2. **Area-level features (F119-F128)** as organising structure
3. **Augmentation Layer is core Phase 1** — dog-fooding principle
4. **Phase 2 is streams, not monolith** — one end-to-end stream at a time
5. **Generic framing** with nimbus as lead example
6. **Platform-agnostic infrastructure** — no Azure specifics
7. **Separate DB per customer, no RLS** — Org>Product>Client>Engagement hierarchy
8. **Content-aware chunking** per content type
9. **No keyword matching** in retrieval — embeddings only
10. **Single ranking pipeline** with 6 signals
11. **Event-driven freshness**, not time-based decay
12. **MVP = one stream working end-to-end**
13. **Separate system blockers from customer blockers**

---

## What's Next

1. **Human review** of Gate 1 documents (5 drafts need validation)
2. **Plan-of-attack rewrite** using validated brief (13 decisions)
3. **Gate 2 formal design** — BPMN, DDD, data model, API design, etc.

---

**Version**: 2.0
**Created**: 2026-02-19
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/Project-Metis/README.md
