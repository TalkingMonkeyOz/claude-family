---
projects:
  - Project-Metis
tags:
  - project/metis
  - type/plan
---

> **⚠️ Design Reference Only** — Execution state has moved to the build board (`get_build_board("project-metis")`). For current decisions, use `recall_entities("metis decision")`. This document captures the original design rationale.

# METIS — Plan of Attack

METIS is an enterprise AI platform that learns what your organisation does — your domain, your processes, your history — and uses that knowledge to produce real artifacts and execute real workflows, not just answer questions. It is built clean from zero, platform-agnostic, and designed to dog-food its own capabilities from Phase 1 onward.

**This document is the master plan.** Phase detail is in the linked phase docs below.

---

## Design Principles

1. **Readable, expandable, maintainable** — the system, like code, must be all three
2. **Everything adds value** — if it's not a call to action, it's not in by default
3. **Dual-lens** — the same gate framework applies to building METIS AND to what METIS enforces for customers
4. **Humans guide, AI executes** — humans at validation checkpoints, AI does the heavy lifting between them
5. **No shortcuts for AI** — agents cannot skip gates; BPMN-enforced

---

## Decision Index

All 39 decisions (13 validated + 26 Gate 2) that constrain what and how we build.

### Foundational

| # | Decision | Phase |
|---|----------|-------|
| D01 | Build from zero — NOT a fork of Claude Family | All |
| D02 | Use area-level features F119-F128 as organising structure | All |
| D05 | Generic framing with nimbus as lead example | All |
| D06 | Platform-agnostic — no cloud provider specifics | All |
| D07 | Separate DB per customer, no RLS; Org→Product→Client→Engagement hierarchy | 0 |
| D12 | MVP = one stream working end-to-end | 2 |
| D13 | Separate system blockers from customer blockers | All |

### Knowledge & Retrieval

| # | Decision | Phase |
|---|----------|-------|
| D08 | Content-aware chunking per content type (API, OData, prose, code) | 1 |
| D09 | No keyword matching — embeddings only throughout | 1 |
| D10 | Single ranking pipeline with 6 signals (configurable weights) | 1 |
| D11 | Event-driven freshness, not time-based decay | 1 |
| C3-2 | Multi-product pipeline: separate ingestion, unified retrieval with scope filtering | 1 |
| C3-3 | Products without APIs use unified connector adapter (API/file-drop/manual) | 1 |
| AGE | Apache AGE on PG18 for knowledge graph — dog-fooding from Phase 1 | 1 |

### Architecture

| # | Decision | Phase |
|---|----------|-------|
| D03 | Augmentation Layer is core Phase 1 (dog-fooding principle) | 1 |
| D04 | Phase 2 is streams, not monolith | 2 |
| C1-1 | API framework: Fastify (TypeScript-first, schema validation, plugin DI) | 0 |
| C1-2 | Frontend: React 19 + Vite + MUI | 1 |
| C1-3 | PostgreSQL 18 minimum (pgvector 0.8.2+ required) | 0 |
| C1-4 | Integration testing: Testcontainers (real PG18 Docker per test run) | 0 |
| C3-1 | Context assembly via declarative recipes | 1 |
| C3-B | Scope guardrails per-engagement and per-user | 1 |
| C4-4 | LLM abstraction: split LLMProvider + EmbeddingProvider interfaces | 1 |

### Data Model

| # | Decision | Phase |
|---|----------|-------|
| C2-1 | Core tenant schemas: hybrid columns + JSONB settings | 0 |
| C2-2 | Scope tag structure: inheritance chain, full path always populated | 0 |
| C2-3 | Activity space entity: activities + separate co_access_log table | 1 |
| C2-4 | Workflow instances: rich record + step log (write-through pattern) | 1 |
| C2-5 | Data retention: tiered presets + RBAC controls | 1 |

### API & Interface

| # | Decision | Phase |
|---|----------|-------|
| C4-1 | Error responses: consistent envelope (code + message + detail + request_id) | 0 |
| C4-2 | Pagination: cursor-based (stable under data changes, opaque base64) | 0 |
| C4-3 | MCP tools: intent-level composites (~6 tools, not 13+) | 1 |

### Security & Operations

| # | Decision | Phase |
|---|----------|-------|
| C5-1 | Credential delegation: hybrid OAuth + vault; interface supports future managed stores | 1 |
| C5-2 | Data residency: region-aware design, Australia first | 0 |
| C5-3 | Deployment model: managed SaaS first, design for customer VPC | 1 |
| C6-1 | Monitoring: custom tables for MVP, Prometheus+Grafana path | 1 |
| C6-2 | Token budgets: graduated 4-level hierarchy; configurable via admin centre | 1 |
| C6-3 | SLOs: internal targets; configurable, no contractual SLAs until proven | 1 |
| C6-4 | Log retention: tiered framework (mirrors data retention model) | 1 |

### Behavioural Constraints (confirmed 2026-03-15)

| # | Decision | Phase |
|---|----------|-------|
| BC-1 | Most operational parameters configurable with sensible defaults via admin centre | 1 |
| BC-2 | Warn-before-shed: no silent context degradation; user gets options | 1 |
| BC-3 | Suggest-and-confirm for sensitive ops (promotion, defect dedup, cross-client escalation) | 1 |
| BC-4 | Sub-agent cap configurable (default 4); monitor coordination metrics | 1 |
| BC-5 | Known issues can pass pipeline gates with logged justification (accept-and-close or accept-and-track) | 2 |
| BC-6 | P9 onboarding steps 2 (domain capture) and 3 (tool integration) run in parallel | 2 |
| BC-7 | Auto-generated test scenarios get human review on first use | 2 |
| BC-8 | Schema changes in connectors flag existing ingested data for review | 1 |

---

## Phase Overview

| Phase | Goal | Key Deliverable | Gated By |
|-------|------|----------------|----------|
| **0 — Foundation** | Working skeleton with auth, schema, conventions | Deployable empty platform | Schema design complete |
| **1 — Core Platform** | Knowledge Engine + Augmentation Layer; dog-food it | /ask, constrained deployment, MCP tools | Phase 0 complete |
| **2 — First Stream** | One end-to-end customer workflow proven on real data | First stream shipped (e.g. defect tracking) | Phase 1 dog-food pass |
| **3+ — Expand** | Next streams, next customers, harden core | Progressive — each stream proves value | Phase 2 stream complete |

---

## Build Order — Dependency Chain

Each block requires those above it. This is the canonical build sequence.

```
[Phase 0]
  PG18 + pgvector + Apache AGE installed
    └─ Core tenant/scope schema (Org→Product→Client→Engagement)
         └─ Auth layer (JWT + RBAC)
              └─ Fastify API skeleton + error/pagination conventions
                   └─ Audit logging (cross-cutting — must exist from day one)

[Phase 1 — Knowledge first, Augmentation second]
  Knowledge Engine
    ├─ Chunking service (content-aware per type)
    ├─ Embedding worker (Voyage AI, EmbeddingProvider interface)
    ├─ Ingestion pipeline + validation tier routing (T1/T2/T3/T4)
    ├─ Vector search + scope filtering
    ├─ Apache AGE graph walk
    └─ Ranking pipeline (6 signals, configurable weights)
         │
  Augmentation Layer  [requires Knowledge Engine]
    ├─ Context Assembly Orchestrator (declarative recipes)
    ├─ Token budget manager + warn-before-shed
    ├─ Session + scratchpad persistence
    └─ Cognitive memory entity
         │
  Intelligence Layer  [requires Augmentation]
    ├─ /ask endpoint
    ├─ Constrained deployment v1 (F128)
    └─ MCP tool server (~6 intent-level composites)
         │
         Integration Hub basics  [requires Intelligence Layer]
           ├─ Connector adapter interface (API/file-drop/manual unified)
           ├─ First connector (Confluence or file-drop)
           └─ Credential vault (OAuth + encrypted fallback, managed-store interface)
                │
  Eval framework  [requires /ask + at least one connector]
    ├─ Query logging + feedback capture
    └─ Retrieval quality metrics

  *** Phase 1 exit gate: dog-food the platform on METIS's own build ***

[Phase 2 — First customer stream]
  Customer onboarding (P9)
    ├─ Product knowledge ingestion (step 1)
    ├─ Domain capture + tool integration (steps 2+3, parallel)
    └─ Constrained deployment config + 5-question validation (step 4)
         │
  First stream (e.g. assisted defect tracking)
    ├─ Jira connector (read/write)
    ├─ Engagement lifecycle (P4)
    ├─ Defect Intelligence domain (IssueThread, patterns, suggest-and-confirm dedup)
    └─ Delivery pipeline basics (P5 — enough for one stream)
         │
  Stream validation
    ├─ Test scenarios (auto-generated + human first-use review)
    ├─ Regression baseline established
    └─ Known-issue accept-and-close / accept-and-track flow
```

---

## Feature Area Mapping

| Feature Area | F-Code | Phase 0 | Phase 1 | Phase 2 | Phase 3+ |
|-------------|--------|---------|---------|---------|---------|
| Knowledge Engine | F119 | Schema | Core build | Customer data | Mature |
| Integration Hub | F120 | — | First connector | Customer connectors | More connectors |
| Delivery Accelerator | F121 | — | — | One stream | More streams |
| Quality & Compliance | F122 | — | — | Validation in stream | Full layer |
| Support & Defect Intel | F123 | — | — | Defect tracking | Pattern detection |
| Project Governance | F124 | — | — | Work management basics | Full governance |
| Orchestration & Infra | F125 | Skeleton | Augmentation Layer | Stream agents | Mature |
| Commercial | F126 | — | — | First contract live | Billing |
| BPMN / SOP Enforcement | F127 | — | BPMN tooling | P4/P5/P9 in stream | All 9 processes |
| Constrained Deployment | F128 | — | v1 | Customer-specific | Multi-role |

---

## Anti-Goals (Not in Scope)

- No cloud-provider specifics — infrastructure choice belongs to the customer
- No LangChain or LlamaIndex — custom RAG pipeline only
- No shared multi-tenant database — separate DB per customer, always
- No keyword matching — embeddings throughout, no exceptions
- No time-based knowledge decay — domain events drive freshness
- No big-bang Phase 2 — one stream proven before adding the next
- No agent gate-skipping — BPMN enforces; no override without a human
- No silent context shedding — warn before dropping, always

---

## Phase Detail Documents

- [[plan-of-attack-phase0|Phase 0: Foundation]] — schema, auth, project conventions
- [[plan-of-attack-phase1|Phase 1: Core Platform]] — Knowledge Engine + Augmentation Layer
- [[plan-of-attack-phase2|Phase 2: First Customer Stream]] — one stream end-to-end

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/plan-of-attack.md
