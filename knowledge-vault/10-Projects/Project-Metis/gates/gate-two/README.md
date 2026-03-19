---
tags:
  - project/Project-Metis
  - type/gate-two
  - gate/two
created: 2026-03-11
updated: 2026-03-15
---

# Gate 2 — Material Index

Gate 2 = Solution Design. 12 deliverables. **Gate 1 review COMPLETE (2026-03-15).** 26 design decisions made across 6 clusters. All 12 deliverables written as formal documents in `gate-two/`. Human review notes applied to BPMN, C4 L3, and DMN deliverables (2026-03-15).

**Status key:**
- `Not started` — no material relevant to this deliverable exists in current form
- `Partial` — material exists but is at brainstorm or design-intent level, not a deliverable-ready document
- `Near-complete` — substantive design decisions made; writing/formalisation is the remaining work
- `Complete (design)` — design is resolved; Gate 3 work handles implementation detail

**Source file abbreviations:**
- SPD = system-product-definition.md
- FC = feature-catalogue.md
- AM = actor-map.md
- ETH = ethos.md
- KE-DD = brainstorm-knowledge-engine-deep-dive.md
- EL = brainstorm-capture-enforcement-layer.md
- BSOP = bpmn-sop-enforcement/README.md
- CID = connector-interface-design.md
- KGR = knowledge-graph-relationships.md
- B2/* = orchestration-infra/ files (Batch B2)
- B3/* = ps-accelerator, quality-compliance, project-governance files (Batch B3)
- SH/* = session handoff files (Batch C)
- R/* = research files (Batch DE)

---

## Deliverable Status Table

| # | Deliverable | Status | Completeness | Document | What's Left |
|---|-------------|--------|-------------|----------|-------------|
| 1 | Detailed Process Models (BPMN) | **Complete (design)** | ~85% | [[gate-two/deliverable-01-bpmn-processes]] | Convert to .bpmn XML files in Gate 3. Apply review notes (7 process-level changes from human review). |
| 2 | C4 Level 3 Component Diagrams | **Complete (design)** | ~80% | [[gate-two/deliverable-02-c4-level3]] | Sequence diagrams and anti-corruption layers are Gate 3. Apply review notes (Apache AGE, configurable params). |
| 3 | Domain Model (DDD) | **Complete (design)** | ~90% | [[gate-two/deliverable-03-domain-model]] | 10 bounded contexts, single aggregate roots, 25+ domain events. Value objects and repository interfaces are Gate 3. |
| 4 | Decision Models (DMN) | **Complete (design)** | ~85% | [[gate-two/deliverable-04-dmn-decisions]] | Weight calibration post-production. Apply review notes (configurable thresholds, rule order fix). |
| 5 | Data Model | **Complete (design)** | ~85% | [[gate-two/deliverable-05-data-model]] | Tenant schemas, knowledge store, workflow, activity, retention tables all specified. DDL is Gate 3. |
| 6 | Tech Stack Decisions | **Complete (design)** | ~95% | [[gate-two/deliverable-06-tech-stack]] | All technology choices made. ADR files are Gate 3 formalisation. |
| 7 | API / Interface Design | **Complete (design)** | ~80% | [[gate-two/deliverable-07-api-interface]] | 13 endpoints, error schema, pagination, MCP tools, LLM abstraction. Detailed request/response schemas are Gate 3. |
| 8 | Security & Access Model | **Complete (design)** | ~90% | [[gate-two/deliverable-08-security-access]] | 12 prior + 7 new decisions. Credential delegation, scope guardrails, retention, residency. Threat model is Gate 3. |
| 9 | Test Strategy | **Complete (design)** | ~80% | [[gate-two/deliverable-09-test-strategy]] | RAG metrics, BPMN-to-test iterative loop, coverage dimensions. Evaluation suite questions are Gate 3. |
| 10 | User/Actor Journey Maps | **Complete (design)** | ~70% | [[gate-two/deliverable-10-journey-maps]] | 7 journeys mapped inc. tool-builder. Wireflows and UX design are Gate 3. |
| 11 | Deployment Architecture | **Complete (design)** | ~75% | [[gate-two/deliverable-11-deployment]] | Instance model, environments, residency, cost estimates. IaC and provisioning are Gate 3. |
| 12 | Monitoring & Observability | **Complete (design)** | ~80% | [[gate-two/deliverable-12-monitoring]] | Monitoring stack, token budgets, SLOs, log retention, structured logging. Alerting rules are Gate 3. |

---

## Additional Gate 2 Material (beyond the 12 core deliverables)

These design areas have substantial material and are Gate 2 in scope but sit between or across the 12 formal deliverables.

| Area | Status | What Exists | Source |
|------|--------|-------------|--------|
| Knowledge Engine Architecture | Near-complete | 6 knowledge types, 8-level retrieval priority, ingestion model per type, decay/promotion/freshness lifecycle (event-driven). Library science principles (Ranganathan 5 Laws, FRBR, OAIS, authority control, collocation, literary warrant) adopted as design foundation. | SH/2026-03-10-knowledge-engine-design.md, R/library-science-research.md |
| Work Context Container (WCC) | Partial | Option C (Smart Context Assembly) accepted as target; Option B (Activity Space) as Phase 1 implementation. Activity entity schema proposed: aliases (authority control), typed refs, co_access_log, lifecycle states. 6 signal types for multi-signal ranking specified (Phase 3). Dossier model adopted. | R/wcc-synthesis.md, R/wcc-options.md, SH/2026-03-10-research-review-option-c.md |
| Augmentation Layer Architecture | Partial | CoALA memory framework adopted as conceptual foundation. Context Engineering 5-layer model adopted as structural reference. Dual-source pattern (static knowledge + dynamic memory) confirmed. Context Assembly Orchestrator identified as required named subsystem. | R/augmentation-layer-research.md, SH/2026-03-08-gate-zero-complete.md |
| Agent Architecture | Partial | Supervisor pattern confirmed: Controller + Supervisors + Specialists. Three AI agent categories (Project / Event-Driven / System-Level). One controller per project; 3-4 sub-agent limit per supervisor. Three-layer context hierarchy (global/project/agent). Autonomy earned model. | AM §2, SH/2026-03-08-scope-reframe-actor-map.md |
| Interaction Model | Complete (design) | Three constraint levels (L1 Guided, L2 Assisted, L3 Open). Dual interface (web UI + MCP server) confirmed. Build order (MCP/API first, web UI second) decided. Coding lifecycle (L1 process wrapping L2/3 dev work) defined. | SH/2026-03-09-interaction-model-mcp-review.md |
| Commercial Model | Partial | Subscription pricing ($3-5K/month), 24-month terms, enhancement model, 20%/80% revenue share structure, scale projection to 5 clients. Management pitch deck exists (not in vault). | B3/commercial/README.md |

---

## Design Decision Documents

All 26 design decisions documented across 2 interactive sessions (2026-03-14/15):

- [[gate-two/decisions-summary|Decisions Summary]] — Full index of all 26 decisions
- [[gate-two/decisions-cluster2|Cluster 2: Data Model]] — workflow_instances, retention policies
- [[gate-two/decisions-cluster3|Cluster 3: Architecture]] — context assembly, scope guardrails, multi-product, connectors
- [[gate-two/decisions-cluster4|Cluster 4: API & Interface]] — errors, pagination, MCP tools, LLM abstraction
- [[gate-two/decisions-cluster5-6|Clusters 5-6: Security & Operations]] — credentials, deployment, monitoring, budgets

---
*Gate 2 design decisions complete, 12/12 deliverables written | 2026-03-15*

---
**Version**: 2.1
**Created**: 2026-03-11
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/README.md
