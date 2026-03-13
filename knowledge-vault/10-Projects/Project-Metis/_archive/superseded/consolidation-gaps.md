---
tags:
  - project/Project-Metis
  - scope/system
  - type/gap-analysis
created: 2026-03-11
updated: 2026-03-12
---

# METIS Consolidation — Gap List

## Purpose

Genuine gaps requiring decisions or documentation work, organized by gate. Sources: 6 extraction batches (A, B1, B2, B3, C, DE). Batch C decisions (110 decisions, chronological) are the master authority. Supersedence applied throughout.

## Gap Severity Key

- **genuine-decision**: John needs to make a decision. Material exists but direction not chosen.
- **needs-writing**: Decision exists but formal documentation has not been written yet.
- **minor**: Small gap; can be filled during Gate 2 work without a dedicated decision session.

---

## Gate 0 Gaps

Gate Zero is complete and validated (2026-03-08). All 5 documents confirmed.

| Gap | What's Missing | Severity | Resolution |
|-----|----------------|----------|------------|
| ~~Augmentation Layer not yet named in system-product-definition.md~~ | ~~Sections 2–3 updated to v0.3 but the Augmentation Layer is not yet explicitly named in the document body~~ | ~~minor~~ | **RESOLVED 2026-03-12**: SPD section 4.1 updated from Three-Layer Engine to Four-Layer Architecture. Augmentation Layer now fully described. |
| ~~Division-of-labour decision not in any G0 doc~~ | ~~Desktop = design with John; Claude Code = technical build is decided (Mar 10) but only in session notes, not in G0 documents~~ | ~~needs-writing~~ | **RESOLVED 2026-03-12**: Division of Labour section added to stakeholders-decision-rights.md (G0 Doc 3). |

---

## Gate 1 Gaps

Gate 1 has 5 documents. The feature catalogue and actor map are substantially complete. Three documents have material gaps.

### G1 Doc 1 — Process Inventory

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| No consolidated process inventory document | Nine area READMEs exist but no single G1 Doc 1. Content is scattered across brainstorm files. | needs-writing |
| Delivery Accelerator (Area 2) BPMN files absent | Pipeline described in detail, gate model decided, BPMN-driven architecture confirmed — but no `.bpmn` files authored | needs-writing |
| ~~Area 3 (Quality & Compliance) BPMN-to-test-case generation logic undesigned~~ | ~~Area 9 vs Area 4 responsibility unresolved~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: Area 4 (Quality) owns generation logic, Area 9 (BPMN/SOP) provides process models. Area 9 enforces compliance at design time; Area 4 is the safety net catching oversight. |
| ~~User Loader v2 PRD not in vault~~ | ~~PRD referenced in ps-accelerator/README.md~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: Nimbus-specific tool, not a platform deliverable. Generic data import/validation already covered in Delivery Accelerator. Reference removed from README. |

### G1 Doc 2 — Actor Map

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Sales and Marketing actor streams deferred | Identified but not defined; deliberately deferred | minor |
| Actor Map completeness unverified | security-architecture.md references G1 Doc 2 but the document was not present in Batch DE — cannot confirm it is fully validated | minor |

### G1 Doc 3 — Data Entity Map

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| No consolidated data entity map document | Entities are scattered across brainstorm files, area READMEs, and extraction reports. 34 entities identified in Batch A; 26 in Batch C; 17 in Batch DE — counts differ, no canonical list | needs-writing |
| Knowledge relationship type taxonomy incomplete | Only `supersedes` is named explicitly in early documents; Batch B1 resolved this to 8 default types but this needs to be surfaced in the formal entity map | needs-writing |
| Core tenant schemas absent | `orgs`, `products`, `clients`, `engagements`, `users` tables referenced throughout but never formally defined | needs-writing |

### G1 Doc 4 — Business Rules Inventory

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| No consolidated business rules inventory | Rules are scattered across feature descriptions, brainstorm files, and DMN candidates; no single inventory document | needs-writing |
| ~~Award/EA documentation availability unknown~~ | ~~affects ingestion planning~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: Nimbus-specific. Generic answer: source formats include online docs, PDFs, Excel, PowerPoint, Word, unstructured human input. Already covered by process inventory (1.1-1.7). Defer to nimbus onboarding plan. |
| ~~Confluence space scope unknown~~ | ~~no answer recorded~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: Nimbus-specific. Defer to nimbus onboarding plan. |
| ~~Salesforce data model at nimbus unknown~~ | ~~no answer recorded~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: Nimbus-specific. Defer to nimbus onboarding plan. |

### G1 Doc 5 — Integration Points

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Integration points connector list exists but endpoint specs absent | Connector list is complete (12 integrations). Request/response schemas, auth per-integration, rate limits, and error contracts are absent | needs-writing |
| ~~time2work API rate limits unknown~~ | ~~Rate limits affect connector queue depth and burst handling design~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: Nimbus-specific. Platform handles rate limiting generically via connector middleware (rate_limits JSONB per config). Defer to nimbus onboarding. |
| ~~Implementation knowledge location unknown~~ | ~~affects ingestion effort estimation~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: Nimbus-specific. Defer to nimbus onboarding plan. |
| ~~Git provider not selected~~ | ~~Four options assessed; decision not made~~ | ~~genuine-decision~~ | **RESOLVED 2026-03-12**: GitHub probable. Architecture already provider-agnostic (EX-08). Final selection deferred to Gate 3 environment setup. |

---

## Gate 2 Gaps (for awareness — not blocking Gate 1)

Gate 2 has 12 deliverables. The table below gives an honest view of what is blocking vs. what will flow from Gate 1 completion.

### G2 Doc 1 — Detailed Process Models (BPMN)

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| No `.bpmn` files authored for any METIS process | MVP = 3 processes (ingestion validation, delivery pipeline, defect triage) decided Feb 26. None exist as files. 9 total processes identified in inventory (4x Tier 1, 4x Tier 2, 2x Tier 3). | needs-writing |
| Agent step-completion protocol for SpiffWorkflow not designed | How a Claude agent signals step completion, how SpiffWorkflow hands back the next step, error/failure handling — all undefined | genuine-decision |
| BPMN pipeline bootstrapping for new customers not designed | How the delivery pipeline BPMN definition gets created for a new customer — manual or semi-automated | genuine-decision |
| Execution engine swap-out decision deferred | SpiffWorkflow for now; Camunda/Temporal evaluation explicitly deferred to Gate 2+ | genuine-decision |

### G2 Doc 2 — C4 Level 3 Component Diagrams

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| C4 L3 not started for any of the 9 containers | C4 L1 and L2 complete; L3 decomposition of each container not begun | needs-writing |
| Context Assembly Orchestrator not yet a designed subsystem | Identified as the crux of the Augmentation Layer; currently implicit, not named or designed | genuine-decision |
| Admin/management layer above all customer instances | Architecture decided (separate instances per customer); admin layer scope deferred; not designed | genuine-decision |

### G2 Doc 3 — Domain Model (DDD)

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Bounded contexts not formally drawn | Nine areas identified; DDD bounded context map with aggregates, value objects, and domain events not produced | needs-writing |
| Multi-product customer pipeline design | Does each product get its own pipeline instance? No answer | genuine-decision |
| Products without APIs | How the platform handles products with no API access — manual configuration only vs. no deployment stage | genuine-decision |

### G2 Doc 4 — Decision Models (DMN)

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Zero DMN files authored | 7 candidate tables identified; none created. Candidates: knowledge validation routing, support ticket triage, deployment gate decisions, gap classification, award applicability, penalty rate selection, escalation rules | needs-writing |
| Validation tier routing decision logic | Knowledge type + source → T1/T2/T3/T4 tier assignment described in prose; thresholds not specified | needs-writing |
| Defect severity decision logic | "Suggested from impact analysis" — inputs, thresholds, severity levels not defined | needs-writing |
| Health score weighting | Weighted combination described; weights not specified | needs-writing |
| Duplicate detection threshold | Semantic duplicate check uses similarity; threshold value not defined | genuine-decision |

### G2 Doc 5 — Data Model

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| No DDL produced | Logical model substantially designed (6 knowledge types, key schemas from B1: knowledge_items 27 cols, knowledge_relations 11 cols); physical PostgreSQL DDL not authored | needs-writing |
| workflow_instances table schema not defined | Required for persistent workflow engine; schema not specified | needs-writing |
| Scope tag structure in data model | "How scope tags are structured in the data model — implementation detail for Gate 2"; not designed | needs-writing |
| Data retention policies per customer | "May vary by industry/regulation" — not designed | genuine-decision |
| Scratchpad retention policy | How long scratchpad entries persist; encryption at rest for sensitive entries | genuine-decision |

### G2 Doc 6 — Tech Stack Decisions

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| API framework not selected | Express vs. Fastify intentionally deferred; should be documented before Phase 0 T2 sprint | genuine-decision |
| Test database strategy not decided | Three options (separate DB, transaction rollback, SQLite fallback) unresolved; blocks CI test stage design | genuine-decision |
| PostgreSQL version not specified | Primary choices made; PostgreSQL version for target deployment not stated | minor |
| Front-end framework not decided | TypeScript confirmed; front-end framework TBD | genuine-decision |

### G2 Doc 7 — API / Interface Design

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| MCP tool design not started | Paused until knowledge system designed; now unblocked but not started | needs-writing |
| Error response schemas absent | 13 endpoints sketched with request/response shapes; error schemas not designed | needs-writing |
| Endpoint versioning strategy | Beyond "v1" — not specified | needs-writing |
| Endpoint naming inconsistency | `/knowledge/{id}/graph` vs `/api/v1/knowledge/graph` inconsistency in source files | minor |
| LLM abstraction interface not specified | Requirement stated; interface not designed | needs-writing |
| Knowledge graph traversal performance design | `/knowledge/{id}/graph` with max_hops=2 has no index strategy or performance design | genuine-decision |

### G2 Doc 8 — Security & Access Model

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Security implementation detail document not written | security-architecture.md validated at architecture level and explicitly defers implementation detail to Gate 2 Doc 8; that document does not exist | needs-writing |
| Formal threat model absent | Security principles documented; OWASP categories not mapped; attack surface not analysed | needs-writing |
| RBAC scoping confirmed (Mar 10) but not formally documented | Tenant isolation for Client Config + Learned/Cognitive; Shared: Product Domain, API Ref; Roles: Platform Builder, Enterprise Admin, Enterprise Staff — decided but not in a formal document | needs-writing |
| Per-user credential delegation feasibility analysis absent | "Optimistic for Phase 1 and depends on what each integration supports" — no analysis per integration type | genuine-decision |
| Data residency decision outstanding | Whether 7-day transient US processing is acceptable or ZDR/Bedrock-Sydney required; blocks production approval | genuine-decision |
| DPA with Anthropic not initiated | Required before client-facing production use; not started | genuine-decision |

### G2 Doc 9 — Test Strategy

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Unified test strategy document absent | Test approach described per feature; no single consolidated strategy document | needs-writing |
| RAG quality metrics not defined for METIS | 50-question evaluation framework resolved (GAP-4); RAG quality dimensions (relevance, groundedness, recency, provenance, coverage) not yet translated into METIS-specific metrics | needs-writing |
| Test coverage sufficiency metric | What level of BPMN process mapping is "good enough" before test generation is reliable; no metric defined | genuine-decision |
| BPMN-to-test-case generation logic undesigned | Concept decided; the actual generation logic is not designed | genuine-decision |
| Compliance thresholds not calibrated | All 7 metrics defined; alert thresholds noted as "need Phase 0-1 data to calibrate" | minor |

### G2 Doc 10 — User/Actor Journey Maps

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Formal journey map documents not produced | 10 feature-based journeys exist in the feature catalogue as source material; none formatted as formal journey maps | needs-writing |
| Non-technical user experience design absent | "If this doesn't work with non-tech people in a contained sandbox, it's not going to work" — no UX design or prototype exists | genuine-decision |
| UX baseline metrics not captured | BHAG (20%+ productivity improvement) requires pre-platform baselines; no baseline measurement plan exists | genuine-decision |

### G2 Doc 11 — Deployment Architecture

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Deployment topology diagram not drawn | Separate-instances principle decided; network/hosting/container diagram not produced | needs-writing |
| VM sizing and networking not authored | 4 environments named; provisioning runbooks not authored | needs-writing |
| IaC not authored | Infrastructure as code not started | needs-writing |
| Self-hosted vs. managed vs. hybrid deployment | Open — not decided | genuine-decision |

### G2 Doc 12 — Monitoring, Logging & Observability

| Gap | What's Missing | Severity |
|-----|----------------|----------|
| Monitoring tool selection outstanding | Principles defined; custom tables + health endpoint for Phase 0-1; Prometheus/Grafana or Azure Monitor deferred to Phase 2-3; tool choice outstanding | genuine-decision |
| Token budget hard cap numbers not set | 8-level retrieval priority order decided; specific token allocations for each level not set | genuine-decision |
| SLOs and alerting thresholds absent | Observable signals identified; no formal SLOs or alert thresholds | needs-writing |
| Log retention policy missing | Application logs retention period not specified (distinct from audit_log which is kept forever) | genuine-decision |

---

## Gate 3 Gaps (for awareness — not blocking)

Gate 3 has 8 deliverables. Most have directional decisions; formal documents are largely unwritten.

| # | Deliverable | Gap | Severity |
|---|-------------|-----|----------|
| G3 Doc 1 | Development Standards | TypeScript + coding conventions decided; formal dev standards document not written | needs-writing |
| G3 Doc 1 | Development Standards | API framework choice still open (Express vs. Fastify) | genuine-decision |
| G3 Doc 1 | Development Standards | Down-migration policy (forward-only) decided; not formally documented | needs-writing |
| G3 Doc 2 | Environment Setup | Infrastructure decisions made; provisioning runbooks not authored; environment matrix (dev/staging/UAT/prod) not formally written | needs-writing |
| G3 Doc 2 | Environment Setup | Day 1 target date not set | genuine-decision |
| G3 Doc 3 | Build Plan / Sprint Backlog | plan-of-attack.md is UNVALIDATED (rewrite brief written Mar 8; actual rewrite not done) | needs-writing |
| G3 Doc 3 | Build Plan | Timeline re-estimation not done; rewrite brief explicitly states "don't carry over old numbers" | genuine-decision |
| G3 Doc 3 | Build Plan | Playwright scope for discovery: "all screens or key workflows first?" — no answer | genuine-decision |
| G3 Doc 3 | Build Plan | Monash engagement timing — is 8-10 week POC timeline realistic? Who initiates client conversation? | genuine-decision |
| G3 Doc 3 | Build Plan | Minimum viable pipeline undefined — which of 6 stages are required for first customer? | genuine-decision |
| G3 Doc 4 | Definition of Done | No design at all; DoD criteria are implicit in gate enforcement rules but never consolidated into a document | needs-writing |
| G3 Doc 5 | Agent Protocols | Formal agent protocol document not written; conventions are listed but not formatted as an agent-readable enforcement document | needs-writing |
| G3 Doc 5 | Agent Protocols | Supervision model when multiple supervisors run on one project — deferred to Gate 2 | genuine-decision |
| G3 Doc 5 | Agent Protocols | Master AI run sheet contents — deferred to Gate 2; still open | genuine-decision |
| G3 Doc 5 | Agent Protocols | Agent Teams timing — single-agent Phase 0, introduce Phase 1 for parallel tasks — noted as "recommendation, needs John's confirmation" | genuine-decision |
| G3 Doc 6 | Documentation Standards | RAG-readable documentation principle decided; formal doc standards document not written | needs-writing |
| G3 Doc 7 | Risk Register | Multiple risk signals identified across 5+ source files; no single consolidated risk register | needs-writing |
| G3 Doc 7 | Risk Register | Revenue share formal agreement — 20/80 split proposed; no legal agreement; separate entity model not legally structured | genuine-decision |
| G3 Doc 7 | Risk Register | Client relationship ownership for AI services — John de Vere vs. existing account manager; unresolved | genuine-decision |
| G3 Doc 8 | Project Delivery Framework | Non-technical workstreams (timelines, commercial, human iteration cycles) not designed | needs-writing |
| G3 Doc 8 | Project Delivery Framework | Commercial model for METIS as product — SaaS vs. per-seat vs. licensing; deferred post-Monash | genuine-decision |
| G3 Doc 8 | Project Delivery Framework | Support volume baseline data absent — how many support tickets/month? escalation rate? | genuine-decision |

---

## Superseded Decisions (for reference)

These decisions are listed here so they can be recognized and not re-raised.

| Original Decision | Date | Superseded By | Date |
|---|---|---|---|
| Linux primary; Azure is customer choice | 2026-02-23 | Platform-agnostic (no Azure specificity at system level) | 2026-03-08 |
| Five-layer validation stack: DDD→BPMN→DMN→Ontology→Event Sourcing | 2026-02-23 | 7-perspective design notation stack (BPMN, DMN, DDD, C4, Journey Maps, Event Sourcing, Ontology) | 2026-03-02 |
| Four-layer 200K cached prompt / two-tier context model | 2026-02-23/24 | Lean context model (~10-25K total); single retrieval model with priority levels | 2026-02-28 |
| Six A–F knowledge categories (configurable defaults) | 2026-02-23 | Six named types taxonomy: Product Domain / API Reference / Client Config / Process-Procedural / Project-Delivery / Learned-Cognitive | 2026-03-10 |
| "Design COMPLETE" declaration | 2026-02-26 | Gate framework restart; all pre-gate-framework design is input material, not output | 2026-03-06 |
| CLAUDE.md reinjection every ~15 interactions | 2026-02-23 | Lean context model; four-layer context management architecture (Core Protocols → Session Notebook → Knowledge Retrieval → Persistent Knowledge) with dynamic priority | 2026-02-28 / 2026-03-10 |
| Fixed token budget caps | pre-2026-03-10 | Four-layer dynamic context management architecture with priority shedding order | 2026-03-10 |

---

## Resolved Gaps (for completeness — do not re-open)

The following numbered gaps from earlier tracking are resolved and should not appear in open gap lists.

| Gap ID | Description | Resolution Date |
|--------|-------------|-----------------|
| GAP-1 | Knowledge Graph Relationships | RESOLVED 2026-02-25: 8 relationship types, knowledge_relations table |
| GAP-2 | Integration Hub Connector Interface | RESOLVED 2026-02-25: 8-method interface + 6 middleware layers |
| GAP-3 | Session Memory | PARKED: working 3-tier implementation exists in Claude Family; METIS rebuilds from scratch |
| GAP-4 | Evaluation Framework | RESOLVED 2026-02-26: 50 test questions, 3 metrics |
| GAP-5 | Chunking Strategy | RESOLVED 2026-02-26: natural boundaries per knowledge type |
| GAP-6 | Knowledge Staleness | RESOLVED 2026-02-27: event-driven dependency tracking |
| GAP-7 | BPMN for MVP | RESOLVED 2026-02-26: 3 processes identified |
| GAP-8 | Two-Way Sync Conflict Resolution | RESOLVED 2026-02-27: intelligent triage layer; last-write-wins + conflict log for MVP |
| GAP-9 | Background Job Scheduling | RESOLVED 2026-02-26: jobs table + cron runner, Phase 2 |
| GAP-10 | External Rule/Change Discovery | RESOLVED 2026-02-27: 4 signal sources |
| GAP-12 | Multi-Product Customers | RESOLVED 2026-02-27: Org → Product → Client → Engagement |
| GAP-13 | Customer Scenario Replication | RESOLVED 2026-02-27: AI-assisted investigation flow |
| GAP-14 | Generic Integration Catalogue | RESOLVED 2026-02-27: common services data layer |
| GAP-15 | Dog-Fooding Loop | RESOLVED 2026-02-27: platform uses itself, same supervised pattern |
| GAP-17 | PM Lifecycle & Client Timelines | FIRST PASS (FB157): issue threads, timeline intelligence, proactive PM alerts |

---
*Consolidated from 6 extraction batches (A, B1, B2, B3, C, DE) | Master authority: Batch C (110 decisions, chronological) | 2026-03-11*

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/consolidation-gaps.md
