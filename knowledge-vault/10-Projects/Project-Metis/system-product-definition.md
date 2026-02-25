---
tags:
  - project/Project-Metis
  - scope/system
  - level/0
  - type/product-definition
projects:
  - Project-Metis
created: 2026-02-23
synced: false
---

# The System — Product Definition

> A full system lifecycle platform that gives development houses an AI brain that knows their product, their processes, and their customers — and gets smarter with every engagement.

**Status:** DRAFT — Brainstorm / Ideation
**Date:** 2026-02-23
**Author:** John de Vere + Claude Desktop

---

## 1. What It Is

A platform that sits alongside a development house's existing product and toolstack. It ingests everything the organisation knows — product APIs, configuration options, implementation patterns, support resolutions, compliance rules — and makes that knowledge available to every person and every process in the business.

It is not a chatbot. It is not a knowledge base. It is an AI-assisted development lifecycle platform that handles design, configuration, documentation, testing, and deployment — with humans guiding at validation checkpoints.

The platform maintains state across sessions, code changes, and years of application lifecycle. It learns from every client engagement, every support ticket, every test run. The knowledge compounds.

---

## 2. Who It's For

**Primary:** Development houses and software companies that:
- Have a complex product with deep domain knowledge
- Deliver through professional services (implementation, configuration, customisation)
- Lose knowledge when people leave
- Want to scale delivery without proportionally scaling headcount
- Need audit-ready documentation and compliance validation

**Examples:** Workforce management vendors, ERP implementers, healthcare software companies, fintech platforms, any B2B software company with a professional services arm.

**Not for:** Companies that just want a chatbot, or companies without a product to wrap knowledge around.

---

## 3. The Problem

Every software company with professional services has the same set of problems:

**Knowledge is locked in people's heads.** Senior staff leave and take years of implementation patterns, edge case knowledge, and client-specific insights with them. New hires take months to become productive.

**Implementation is manual and inconsistent.** Each consultant configures slightly differently. Testing is incomplete. Documentation is written after the fact and quickly outdated. Quality depends on which person runs the project.

**Support doesn't learn.** The same issues get diagnosed from scratch every time. Resolution knowledge is lost when tickets close. Pattern detection across clients doesn't happen.

**Scaling requires proportional hiring.** Each new client requires roughly the same manual effort. Growth is constrained by the ability to find and train experienced staff.

**AI tools don't understand your product.** Off-the-shelf AI (Copilot, Glean, Guru) is useful for general productivity but knows nothing about your specific product, your domain, your implementation methodology, or your clients' configurations.

---

## 4. Core Architecture

### 4.1 Three-Layer Engine

| Layer | What It Does | Technology |
|-------|-------------|------------|
| **Knowledge Store** | Stores all domain knowledge: product APIs, configuration docs, compliance rules, implementation patterns, client configs, support resolutions | PostgreSQL + pgvector |
| **Retrieval System** | Finds the most relevant knowledge for any question. Two-stage: vector search then reranking | Voyage AI embeddings (1024 dim) + cosine similarity |
| **Intelligence Layer** | Takes retrieved context + user question, generates answers, flags uncertainty, learns from corrections | LLM API (currently Claude, provider-agnostic) |

The architecture is modular. The embedding model, vector database, and LLM can each be swapped independently. The knowledge and processes are the assets, not the specific AI provider.

### 4.2 Constrained Deployment Pattern

The platform creates purpose-built AI assistants for each customer without building custom LLMs. Four layers of constraint:

| Layer | Mechanism | What It Does |
|-------|-----------|-------------|
| 1 | **System Prompt** | Defines the AI's identity, role, scope, boundaries. Primary control mechanism. |
| 2 | **Cached Knowledge** | Injects domain knowledge via cached prompt (up to 200K tokens). Knowledge feels "baked in" — no retrieval step visible. |
| 3 | **Input Classification** | Cheap/fast gatekeeper checks if query is on-topic before reaching main model. Off-topic rejected at minimal cost. |
| 4 | **Tool Restriction** | Only domain-specific tools available. No general web search, no file system access. Hard boundary. |

For internal staff: Layers 1-3 sufficient. For external/client-facing: all four layers.

### 4.3 Five-Layer Validation Stack

Every process, workflow, and deployment in the platform is validated through five complementary layers:

| Layer | What It Validates | How |
|-------|------------------|-----|
| **DDD (Domain-Driven Design)** | Boundaries, bounded contexts, aggregates | Are we building the right things in the right places? |
| **BPMN (Business Process Model & Notation)** | Process flow, stage gates, handoffs | Does the workflow make sense? Are approvals in the right places? |
| **DMN (Decision Model & Notation)** | Decision logic, rules tables | Are the branching decisions correct and complete? |
| **Ontology / Knowledge Graph** | Completeness, dependencies, relationships | Is anything missing? Do all the pieces connect? |
| **Event Sourcing** | Immutable lifecycle history | Can we trace every change, every decision, every outcome? |

Each layer feeds upward. DDD defines what exists. BPMN defines how it flows. DMN defines how decisions are made. Ontology checks completeness. Event sourcing provides the audit trail.

---

## 5. Platform Areas

Nine capability areas, each solving a distinct problem:

| # | Area | What It Does | Generic Description |
|---|------|-------------|-------------------|
| 1 | **Knowledge Engine** | Ingests, stores, retrieves all domain knowledge | The brain. Product APIs, compliance rules, implementation patterns, support resolutions — searchable and versioned. |
| 2 | **Integration Hub** | Connects to product APIs and external tools | The nervous system. Standardised connectors with retry, rate limiting, circuit breakers. Bidirectional — reads from systems, writes back insights. |
| 3 | **Delivery Accelerator** | AI-assisted implementation/configuration pipeline | The muscle. Requirements gathering → config generation → data validation → release management → living documentation. |
| 4 | **Quality & Compliance** | Automated testing and validation | The immune system. Scenario generation from rules, outcome comparison (expected vs actual), regression suites, compliance monitoring. |
| 5 | **Support & Defect Intelligence** | AI triage, pattern detection, defect management | The memory. Duplicate detection, resolution suggestions, cross-client pattern recognition, defect lifecycle monitoring. |
| 6 | **Project Governance** | Dashboards, health scoring, status reporting | The dashboard. Aggregates signals from all connected systems into project health views. |
| 7 | **Orchestration & Infrastructure** | Agent coordination, sessions, auth, environments | The skeleton. Database, authentication, CI/CD, agent conventions, session management, crash recovery. |
| 8 | **Commercial** | Pricing, contracts, customer onboarding model | The business model. How customers buy, deploy, and expand their use of the platform. |
| 9 | **BPMN / SOP & Enforcement** | Validation workflows, stage gates, operational rules | The rulebook. Defines how work flows through the platform, where approvals are needed, what's automated vs human-reviewed. Cross-cutting — applies to all other areas. |

---

## 6. Knowledge Model

### 6.1 Eight Knowledge Types

Not all knowledge is the same. Different types need different ingestion, validation, and retrieval:

| Type | Generic Description | Validation | Update Frequency |
|------|-------------------|-----------|-----------------|
| **Product API Knowledge** | REST endpoints, data models, request/response shapes | Auto-approved (from system) | On product release |
| **Product UI/UX Knowledge** | Screens, workflows, field meanings, navigation | Human review | On product release |
| **Compliance / Rule Knowledge** | Regulatory rules, parameters, valid combinations | MUST be human-approved | On regulation change |
| **Implementation Patterns** | "When client needs X, configure Y and Z" | Senior staff approval | Grows with every client |
| **Client Configurations** | Client-specific setup, requirements, constraints | Client-isolated, team-approved | Per engagement |
| **Support Knowledge** | Problem → cause → resolution patterns | Tiered: common auto, edge cases human | Grows with every ticket |
| **Decision Records** | What was decided, when, by whom, why | Auto-ingested, flagged for review | Append-only |
| **Procedures / SOPs** | How to do X — step by step | Human-approved, versioned | On process change |

### 6.2 Tiered Validation

| Tier | What | Validation | Why |
|------|------|-----------|-----|
| Tier 1: System-Generated | API docs, config snapshots, metadata | Auto-approved | Facts from the system itself |
| Tier 2: Structured Human Knowledge | Rules, patterns, procedures | Human review required | Accuracy is critical |
| Tier 3: Experiential Knowledge | Support resolutions, decisions, learnings | Auto-ingested with confidence flag | Volume too high to review everything |
| Tier 4: AI-Generated | Suggested configs, predicted patterns, inferred relationships | Always flagged, never auto-trusted | AI suggestions are hypotheses, not facts |

---

## 7. How Customers Deploy It

### 7.1 Customer Onboarding (Generic Pipeline)

1. **Product knowledge ingestion** — Customer provides API specs, product documentation, configuration guides. Platform ingests and indexes.
2. **Domain knowledge capture** — Implementation patterns, compliance rules, procedures. Requires human input and validation.
3. **Tool integration** — Connect to customer's toolstack: project management, CRM, documentation, communication tools.
4. **Constrained deployment configuration** — System prompt, cached knowledge payload, classifier setup, tool restrictions.
5. **Validation** — Internal staff test with real questions. Measure: correct answers? Stays on topic? Knows when it doesn't know?
6. **First engagement** — Apply to a real client engagement. The platform learns from the engagement.
7. **Compound** — Each subsequent engagement adds knowledge. The platform gets smarter.

### 7.2 What a Customer Provides

| Customer Provides | Platform Provides |
|------------------|------------------|
| Product API access / documentation | Knowledge ingestion and indexing |
| Domain expertise (rules, patterns, procedures) | Structured capture and validation workflows |
| Toolstack credentials (PM, CRM, docs) | Integration connectors |
| Client engagement data | AI-assisted delivery pipeline |
| Human review at validation checkpoints | Everything else |

### 7.3 Multi-Tenant Architecture

The platform supports multiple levels of isolation:

| Level | What | Example |
|-------|------|---------|
| **Organisation** | The development house using the platform | "Acme Software Ltd" |
| **Product** | The customer's product(s) the platform knows about | "AcmeHR" |
| **Client** | End-clients of the development house | "University of Melbourne" |
| **Engagement** | A specific project/implementation for a client | "AcmeHR Phase 2 rollout" |

Knowledge can be scoped at any level. Product knowledge is shared across all clients. Client knowledge is isolated. Engagement knowledge is contained within its project.

---

## 8. What's Proven vs Aspirational

### Proven (working today)
- ✅ Voyage AI embeddings + pgvector semantic search (290+ knowledge entries, sub-100ms queries)
- ✅ RAG auto-injection (query hook fires on every prompt, injects relevant context)
- ✅ Knowledge storage with confidence tracking and relations
- ✅ RAG usage logging (queries, results, latency, similarity scores)
- ✅ Session management, crash recovery, interaction logging
- ✅ Jira integration via MCP (search, create, update across multiple instances)
- ✅ Constrained deployment pattern (industry-standard, well-documented)
- ✅ Five-layer validation stack (design validated conceptually)
- ✅ Claude API with prompt caching (production-ready, cost-effective)

### Designed but not yet built
- ◐ Multi-user API layer (/ask, /search, /ingest, /validate endpoints)
- ◐ Multi-tenant organisation/client isolation
- ◐ Agent orchestration (task queues, shared state, inter-agent messaging)
- ◐ Delivery pipeline (requirements → config → test → release → docs)
- ◐ Input classification gatekeeper
- ◐ BPMN/DMN validation workflows

### Aspirational (future capability)
- ○ Self-maintaining platform (builds and maintains its own features)
- ○ Cross-client pattern detection at scale
- ○ Predictive support (identifying issues before clients report them)
- ○ Autonomous agent teams for parallel development
- ○ Client-facing self-service portal

---

## 9. Reference Implementations

### 9.1 POC: Claude Family Building Itself
The platform's first test is building itself. Claude (AI) does the design, configuration, documentation, and testing. John (human) provides guidance at validation checkpoints. The vault is the persistent knowledge store. Each session adds to the platform's capability.

This is the dog-fooding loop: the system builds itself, then maintains itself, then gets deployed to customers.

### 9.2 First Customer: nimbus / time2work
nimbus is a workforce management software company with 20 years of domain knowledge. Their product (time2work) schedules staff and creates payroll files. They have deep domain expertise in Australian Award compliance, a professional services team, and an existing client base.

The platform would be deployed with:
- time2work API and product knowledge ingested
- Australian Award/EA compliance rules as the compliance knowledge type
- Existing nimbus toolstack integrated (Jira, Confluence, Salesforce)
- Monash University as the first client engagement

Full nimbus-specific documentation exists in companion documents (Docs 1-6).

### 9.3 First Engagement: Monash University POC
Within the nimbus deployment, Monash University is the first client engagement — proving the delivery pipeline works on a real, complex implementation. 8-10 week timeline from approval to production.

Full Monash-specific scope exists in Doc 2 (Monash POC Proposal).

---

## 10. Infrastructure (Deferred)

Infrastructure decisions are deliberately deferred at this stage. The platform should be infrastructure-agnostic at the system level.

**Requirements:**
- Linux as primary platform (containers, standard tooling)
- PostgreSQL with pgvector extension
- Ability to host in customer's preferred cloud or on-premises
- Data residency compliance (configurable per customer/jurisdiction)

**Previous conversations** have explored Azure (nimbus's existing infrastructure), but this is a customer-specific choice, not a system-level decision. The System should run on any Linux environment with PostgreSQL.

---

## 11. What This Document Does NOT Cover

- nimbus-specific commercial terms (see Doc 3)
- Monash engagement scope and timeline (see Doc 2)
- Detailed architecture per area (see area READMEs in vault)
- Build phases and task breakdown (see Doc 4)
- Pricing model for The System itself (TBD)

---

## 12. Open Questions

- [ ] What is the commercial model for The System? (SaaS subscription? Per-seat? Licensing?)
- [ ] Self-hosted vs managed vs hybrid deployment?
- [ ] How does the dog-fooding loop formally work? (Claude Family building itself)
- [ ] What's the minimum viable deployment for a new customer? (Fastest path to value)
- [ ] How do we handle customers with multiple products?
- [ ] What's the generic integration catalogue? (Standard connectors every customer needs)

---
*Product Definition v0.1 | Created: 2026-02-23 | Next: Review, then continue area deep-dives with generic framing*
