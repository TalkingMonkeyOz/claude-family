---
tags:
  - project/Project-Metis
  - type/gate-two
  - gate/two
created: 2026-03-11
updated: 2026-03-11
---

# Gate 2 — Material Index

Gate 2 = Solution Design. 12 deliverables. Formal Gate 2 work has not started (pending Gate 1 completion). This index maps existing material against each deliverable and gives honest completeness estimates.

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

| # | Deliverable | Status | Completeness | What Exists | What's Missing | Primary Source Files |
|---|-------------|--------|-------------|-------------|----------------|---------------------|
| 1 | Detailed Process Models (BPMN) | Partial | ~15% | MVP 3 processes decided (Feb 26): ingestion validation, delivery pipeline, defect triage. Process inventory: 9 processes (4x T1, 4x T2, 2x T3). 5 additional process types described in prose (customer onboarding, knowledge promotion, constrained deployment config, coding lifecycle, compliance measurement cycle). | No `.bpmn` XML files authored for any process. Swim lanes, task assignments, BPMN-specific elements (gateways, error events, signal events) not defined. Agent step-completion signalling not designed. Execution engine swap-out decision (SpiffWorkflow → Camunda/Temporal) deferred. | SH/handoff-2026-02-26-design-complete.md, FC, B2/agent-compliance-drift-management.md, SH/2026-03-09 |
| 2 | C4 Level 3 Component Diagrams | Not started | ~5% | C4 L1 and L2 are complete and validated (Mar 8). Nine top-level containers named. Augmentation Layer identified as subsystem group 3 with 5 internal subsystems named (Cognitive Memory, RAG Pipeline, Skills System, Session Management, Context Assembly Orchestrator). | No C4 L3 diagrams for any of the 9 containers. Context Assembly Orchestrator is currently implicit — needs formal design. Admin/management layer above all customer instances is in scope but deferred. | SH/2026-03-08-gate-zero-complete.md, R/augmentation-layer-research.md |
| 3 | Domain Model (DDD) | Partial | ~40% | Scope hierarchy locked (Org → Product → Client → Engagement with inheritance rules). 34+ entities identified across batches. Six knowledge types resolved (Mar 10). Bounded contexts named for 6 areas. Issue Thread data model designed. Decision as first-class DB object designed. Work breakdown (Initiative → Feature → Task) decided. | Bounded context map with aggregates, value objects, and domain events not drawn. Multi-product pipeline design unresolved. Products without APIs design unresolved. KOS (knowledge organisation system) at folksonomy level; thesaurus target not yet designed. | KE-DD, KGR, B3/project-governance, SH/2026-03-10-knowledge-engine-design.md |
| 4 | Decision Models (DMN) | Not started | ~10% | DMN installed in SpiffWorkflow. 7 candidate tables identified with input/output columns sketched. Logic for 4 tables described in prose (validation tier routing, severity suggestion, health score weighting, deployment gate criteria). | Zero `.dmn` files authored. No thresholds specified for any table. DMN authoring tool, storage pattern, and versioning not decided. All 7 tables need formal design. | EL, BSOP, SPD §6.2, FC F6, FC F8 |
| 5 | Data Model | Partial | ~50% | Substantial design: `knowledge_items` (27 cols), `knowledge_categories` (9 cols), `knowledge_promotions` (9 cols), `knowledge_relations` (11 cols), `connector_configs`, `scratchpad_entries` (full column spec), `sessions`, `work_items`. Scope hierarchy tables referenced. 15+ core tables named. Physical data model for Batch B2 orchestration-infra tables also exists. | No PostgreSQL DDL produced. `workflow_instances` schema not defined. Core tenant schemas (orgs, products, clients, engagements, users) not formally designed. Scope tag structure not specified. Data retention policies per customer not designed. `activity_space` entity schema (from WCC Option B/C) not specified. | KE-DD §3, KGR §3, B2/session-memory-context-persistence.md, R/wcc-synthesis.md |
| 6 | Tech Stack Decisions | Partial | ~70% | Decided: PostgreSQL + pgvector, Voyage AI (pluggable), Claude API (pluggable), Custom RAG (no LangChain/LlamaIndex), SpiffWorkflow (swap-out), JWT + RBAC (pluggable), Git-agnostic, TypeScript primary + Python for data/ML. Deployment: Linux/platform-agnostic, separate instances per customer, PgBouncer, Alembic/Flyway, table partitioning. | API framework not selected (Express vs. Fastify). Test database strategy not decided (3 options open). Front-end framework TBD. Execution engine swap-out point not formally documented. PostgreSQL version not specified. ADR files (ADR-001 through ADR-005 listed) not authored. | KE-DD §1, EL, B2/phase-0-task-list.md, SH/2026-03-08-scope-reframe-actor-map.md, R/audit-alternatives.md |
| 7 | API / Interface Design | Partial | ~45% | 13 REST endpoints specified with request/response shapes and auth model (JWT + scope headers): `/ask`, `/search`, `/ingest`, `/ingest/batch`, `/validate`, `/promote`, `/similar`, `/knowledge/{id}`, `/knowledge/{id}/history`, `/knowledge/{id}/graph`, `/categories`, `/health`, `/feedback`. Dual interface (MCP server + web UI) confirmed. Build order: MCP/API first, web UI second. Three constraint levels (Guided/Assisted/Open) decided. | Error response schemas absent. Pagination details not specified. MCP tool design not started. LLM abstraction interface not specified. `/knowledge/{id}/graph` performance design at scale absent. Endpoint naming inconsistency between source files. | KE-DD §7, KGR §6, SH/2026-03-09-interaction-model-mcp-review.md |
| 8 | Security & Access Model | Near-complete (design) | ~75% | 12 security architecture decisions validated (Mar 8): separate instances per customer, RBAC + project/client scoping, agent access rules (inherits human ceiling, further constrained to task), all agents through application layer, all deletes soft, pluggable auth adapter, audit log everything with tiered retention. RBAC scoping clarified Mar 10: tenant isolation for Client Config + Learned/Cognitive; shared for Product Domain + API Ref. | Security implementation detail document (Gate 2 Doc 8) not written — security-architecture.md explicitly defers to it. Formal threat model not authored. Per-user credential delegation feasibility analysis absent. Data residency management decision outstanding. DPA with Anthropic not initiated. | SH/2026-03-08-security-architecture.md, SH/2026-03-10-decisions-and-delegation.md |
| 9 | Test Strategy | Partial | ~35% | Evaluation framework decided (GAP-4): 50 test questions across 4 categories, 3 metrics (precision >80%, correctness >85%, hallucination <5%). BPMN as test generation source decided. Regression is a mode (not a separate engine) decided. Three testing capabilities decided (Config Validation core, UI Validation complementary, Customer Scenario Replication later). 5-stage CI/CD pipeline with quality gates designed. | Unified test strategy document absent. RAG quality metrics (relevance, groundedness, recency, provenance, coverage) not translated to METIS-specific metrics. BPMN-to-test-case generation logic not designed. Test coverage sufficiency metric not defined. Compliance thresholds need Phase 0-1 data to calibrate. | SH/handoff-2026-02-26-design-complete.md, B3/quality-compliance/brainstorm, B2/cicd-pipeline-spec.md |
| 10 | User/Actor Journey Maps | Partial | ~25% | User Journey Mapping adopted as priority technique (Mar 2). 10 feature-based journeys exist in feature catalogue as source material. 6 actor types defined. 5 user personas identified with interface strategy by phase. Three interaction scenarios modelled in prose (simple query, multi-step task, cross-agent handoff). | No formal journey map documents produced. No wireflows. No UX design or prototype for non-technical users. UX baseline metrics not captured. | FC (all features), AM §1, B2/user-experience.md, SH/2026-03-02-toolkit-brainstorm.md |
| 11 | Deployment Architecture | Partial | ~30% | Key decisions: separate instances per customer, platform-agnostic (no Azure specificity), Linux primary. Four environments named (Local Dev, Dev/Test, Monash POC, Production) with access matrix. Infrastructure components decided: PgBouncer, Alembic/Flyway, table partitioning for high-volume tables. nimbus-specific estimate: Azure B2ms VM + PostgreSQL Flexible (~$140/month). | Deployment topology diagram not drawn. Container networking not designed. VM/resource sizing not specified. IaC not authored. Self-hosted vs. managed vs. hybrid deployment open. Provisioning runbooks not authored. | SPD §11, SH/2026-03-08-scope-reframe-actor-map.md, SH/2026-03-08-security-architecture.md, B2/README.md |
| 12 | Monitoring, Logging & Observability | Partial | ~40% | Decided: audit log everything, tiered retention, extract-then-decay. Three monitoring categories designed (platform health, LLM/cost, agent compliance). 7 compliance metrics defined with measurement methods. Structured log format (8 always-present JSON fields). Phased approach: P0 custom tables + health endpoint → P1 metrics → P2+ dashboards. Sensitive-data-never-logged rule. | Monitoring tool selection outstanding. Token budget hard cap numbers not set. SLOs not defined. Alerting thresholds not calibrated. Log retention period not specified. Dashboard Phase 3 (explicitly deferred). | SH/2026-03-08-security-architecture.md, B2/monitoring-alerting-design.md, B2/agent-compliance-drift-management.md |

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
*Index only — formal Gate 2 work not started | 2026-03-11*

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/README.md
