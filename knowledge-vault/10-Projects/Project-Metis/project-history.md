---
projects:
  - project-metis
tags:
  - history
  - architecture
  - decisions
  - reference
---

# METIS Project History

Complete history of Project METIS: genesis, design process, validated decisions, build phases, architecture choices, and gap analysis. This is the "why we did what we did" reference document.

## 1. Project Genesis

METIS is an enterprise AI platform that learns what an organisation does -- its domain, processes, and history -- and uses that knowledge to **do the work**, not just answer questions about it.

The distinction is critical: most enterprise AI tools are sophisticated search engines. METIS is designed to be a worker that understands context. It ingests organisational knowledge (documents, processes, history), builds a structured understanding, and then executes tasks within that context -- quality audits, delivery tracking, defect analysis, governance enforcement.

The project was born from experience building the Claude Family infrastructure and the Nimbus consulting platform. The recurring pattern: organisations have knowledge scattered across systems, and AI tools that can retrieve it but cannot act on it with understanding.

METIS was initiated as a clean-sheet design (not a fork of any existing system) with a gate-based methodology to ensure rigour before code.

## 2. Design Process

METIS uses a 5-gate design methodology. Each gate has defined deliverables that must be validated before proceeding.

### Gate 0: Problem Definition (COMPLETE -- 4/4 validated)

Established the core problem statement, target users, and success criteria. Validated that the "AI that works, not just answers" framing was sound and that the market gap existed.

### Gate 1: Domain Analysis (COMPLETE -- 5/5 validated, 2026-03-14)

Analysed the target domains: professional services delivery, quality/compliance, support/defects, project governance, and knowledge management. Mapped how organisations actually work in these areas and where AI could replace manual effort.

### Gate 2: Detailed Design (COMPLETE -- 26 decisions, 12/12 deliverables, 2026-03-15)

The heaviest gate. Produced 26 design decisions across 12 deliverable areas: data model, security architecture, knowledge engine, integration hub, orchestration infrastructure, and all six customer-facing areas. Every deliverable was documented as a vault file with full rationale.

### Gate 3: Build Specification (Material indexed)

Indexed all Gate 2 material into the entity catalog and build board. Created the phased build plan with features, build tasks, and dependency chains. This gate transitioned METIS from design to execution.

### Gate 4: Release Readiness (Future)

Production readiness, deployment verification, dog-food validation. Not yet started.

## 3. Thirteen Validated Decisions

All confirmed by John on 2026-03-08. These are constraints, not suggestions.

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Build from zero** | Clean architecture. Claude Family patterns are good but METIS needs its own foundation without legacy debt. |
| 2 | **Area-level features (F119-F128)** | Organising structure maps to customer value areas, not technical layers. Each feature = one business capability. |
| 3 | **Augmentation Layer is core Phase 1** | Dog-fooding principle. METIS must use its own knowledge engine to build itself. Forces quality early. |
| 4 | **Phase 2 is streams, not monolith** | One end-to-end customer stream at a time. Proves value vertically before expanding horizontally. |
| 5 | **Generic framing, Nimbus as lead example** | Platform serves any organisation. Nimbus (consulting) is the first concrete implementation, not the only one. |
| 6 | **Platform-agnostic infrastructure** | No Azure/AWS/GCP lock-in. Standard PostgreSQL, Docker, HTTP APIs. Deployable anywhere. |
| 7 | **Separate DB per customer, no RLS** | Hard tenant isolation. Hierarchy: Org > Product > Client > Engagement. RLS is fragile at scale. |
| 8 | **Content-aware chunking** | Different content types (contracts, SOPs, code, emails) need different chunking strategies. One-size-fits-all loses context. |
| 9 | **No keyword matching in retrieval** | Embeddings only. Keyword matching adds complexity and degrades when domain terminology varies across clients. |
| 10 | **Single ranking pipeline, 6 signals** | One pipeline with configurable signal weights, not multiple competing retrieval paths. Signals: semantic similarity, recency, authority, usage, scope, and freshness. |
| 11 | **Event-driven freshness** | Documents become stale when events happen (new version uploaded, process changed), not on a timer. |
| 12 | **MVP = one stream working end-to-end** | Ship when one customer area works completely, not when all areas are partially done. |
| 13 | **Separate system blockers from customer blockers** | System blockers (infra, bugs) tracked differently from customer blockers (missing data, unclear requirements). Different resolution paths. |

## 4. Build Phases

### Phase 0: Foundation (F147) -- COMPLETE

Core infrastructure: 32-table PostgreSQL schema, tenant hierarchy (Org > Product > Client > Engagement), JWT authentication with RBAC, Fastify API skeleton with conventions, and audit logging. Five child features (F150-F154), eight build tasks.

### Phase 1: Core Platform (F148) -- COMPLETE (30/32 tasks)

The platform engine: knowledge ingestion pipeline, content-aware chunking, Voyage AI embeddings with pgvector storage, semantic search with the 6-signal ranking pipeline, Jira connector (read/write), React chat UI for the /ask endpoint, and orchestration infrastructure. Child features: F119, F120, F125, F128, F155.

### Phase 2: First Customer Stream (F149) -- COMPLETE

End-to-end delivery for one customer area: delivery tracking, quality/compliance enforcement, defect intelligence, BPMN runtime for process enforcement (SOP layer), and project governance. Proved the vertical-slice approach from Decision 4. Child features: F121-F124, F126, F127.

### Phase 3: Deployment and Assembly (F167) -- PLANNED

Deploy to Oracle ARM server via Docker. Nginx reverse proxy, SSL, PostgreSQL 18 on server, environment configuration. Create the actual METIS database on the server and run all 32 migrations. MCP server packaging for Claude Code integration.

### Phase 4: Integration Testing (F168) -- PLANNED

End-to-end testing across all components. Seed data generation, API contract tests, knowledge pipeline integration tests. Verify the full path: ingest document, chunk, embed, search, rank, return.

### Phase 5: Dog-Food MVP (F169) -- PLANNED

Load real Nimbus data, connect Claude Code as the MCP client, and iterate on real usage. This is where Decision 3 (dog-fooding) and Decision 12 (one stream end-to-end) converge.

## 5. Key Architecture Choices

| Layer | Choice | Why |
|-------|--------|-----|
| **Runtime** | Fastify + TypeScript (strict mode, ES2022) | Fast, typed, good plugin ecosystem. Strict TS catches errors at compile time. |
| **Database** | PostgreSQL 18 + pgvector | Mature, reliable. pgvector provides native vector similarity search without a separate vector DB. |
| **Embeddings** | Voyage AI | Best-in-class embedding quality for retrieval at the time of selection. |
| **LLM** | Anthropic Claude | Primary LLM for generation, analysis, and orchestration tasks. |
| **Multi-tenancy** | Separate DB per customer | Hard isolation per Decision 7. Connection pooling per tenant. No cross-tenant data leakage possible. |
| **Interaction model** | MCP server (Claude Code as console) | METIS exposes tools via Model Context Protocol. Users interact through Claude Code, not a custom UI. The React chat UI exists for /ask but MCP is the primary interface. |
| **Process enforcement** | BPMN runtime | Processes modeled in BPMN, executed by the runtime. Code implements the model. SOPs are enforceable, not advisory. |

## 6. Gap Analysis (2026-03-28)

An honest assessment of where METIS stands.

### What exists

- 178 TypeScript files across all platform areas
- 32 database migrations covering the full schema
- 29 API routes for knowledge, search, tenancy, auth, and all customer areas
- BPMN runtime with SOP enforcement
- Jira connector with read/write
- React chat UI for /ask endpoint
- All Phase 0, 1, and 2 features marked complete

### What does not exist

- **No deployment.** The METIS database does not exist on any server. All code runs locally or not at all.
- **No integration tests.** Components were built individually but never tested as a system.
- **No real data.** No Nimbus (or any) organisational data has been ingested.
- **No MCP packaging.** The MCP server interface is not built.

### The honest numbers

The build board showed ~90% completion across Phases 0-2. The real progress toward a usable product is closer to 60-65%. The gap is the difference between "code exists" and "system works."

### Corrective action

Phases 3-5 were created with 28 new build tasks to bridge this gap. The work is deployment (get it running), integration testing (prove it works), and dog-fooding (prove it is useful). No new features until the existing code is deployed and validated.

---

**Version**: 1.0
**Created**: 2026-03-28
**Updated**: 2026-03-28
**Location**: knowledge-vault/10-Projects/Project-Metis/project-history.md
