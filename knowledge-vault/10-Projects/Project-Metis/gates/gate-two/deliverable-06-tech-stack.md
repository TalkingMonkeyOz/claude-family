---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/6
  - type/tech-stack
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 6: Tech Stack Decisions

## Overview

Technology choices for METIS, organised by layer. Each decision includes rationale and swap-out points where applicable. All decisions confirmed by John (2026-03-14/15).

**Governing constraints:** Platform-agnostic (Decision #6), build from zero (Decision #1), TypeScript primary + Python for data/ML (prior decision).

---

## Backend

| Component | Choice | Swap-out? |
|-----------|--------|-----------|
| **API Framework** | Fastify | No — foundational |
| **Primary Language** | TypeScript (Node.js) | No — foundational |
| **Data/ML Language** | Python | No — ecosystem requirement |
| **Database** | PostgreSQL 18+ | No — foundational |
| **Vector Search** | pgvector 0.8.2+ | Replaceable (dedicated vector DB) |
| **Workflow Engine** | SpiffWorkflow | Yes — designed for swap-out |
| **Authentication** | JWT + RBAC | Pluggable adapter |

### Fastify (over Express)

- First-class TypeScript support
- Built-in JSON Schema validation on routes
- Encapsulated plugin system with dependency injection
- ~2x performance headroom for RAG orchestration workloads
- Aligns with ethos: readable, expandable, maintainable

### PostgreSQL 18

- Minimum version: PG18 (pgvector 0.8.2+ requires it)
- All major cloud providers support PG18
- pgvector for vector similarity search (embeddings stored alongside relational data)
- No separate vector database needed at MVP scale

### SpiffWorkflow

- BPMN execution engine for Python
- Designed as swappable — our `workflow_instances` table owns queryable state, engine owns execution internals
- Swap-out candidates: Camunda, Temporal (if scaling demands)

---

## Frontend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Framework** | React 19+ | Standard, large ecosystem |
| **Build Tool** | Vite | Fast HMR, simple config |
| **Component Library** | MUI | Consistent with existing projects (nimbus-mui, claude-manager-mui, finance-mui) |
| **Deployment** | Static bundle | Served by Fastify or CDN, no SSR needed |

Not Next.js — no SSR required for enterprise tool behind auth. Marketing site (if needed) is separate.

---

## AI / ML Layer

| Component | Choice | Swap-out? |
|-----------|--------|-----------|
| **LLM Provider** | Claude API (Anthropic) | Yes — via LLMProvider interface |
| **Embedding Provider** | Voyage AI | Yes — via EmbeddingProvider interface |
| **RAG Framework** | Custom (no LangChain/LlamaIndex) | N/A |

### Provider Abstraction (Decision C4-4)

Two separate interfaces — different vendors, different swap-out points:

- **LLMProvider**: `complete()` + `classify()` — handles token counting, rate limiting, cost tracking
- **EmbeddingProvider**: `embed()` — handles batch processing, dimension management

### Custom RAG (Decision #8-9)

No LangChain or LlamaIndex. Custom retrieval pipeline because:
- Embeddings only, no keyword matching (Decision #9)
- Single ranking pipeline with 6 signals (Decision #10)
- Content-aware chunking per content type (Decision #8)
- Full control over retrieval quality and debugging

---

## Testing

| Component | Choice | Scope |
|-----------|--------|-------|
| **Integration DB** | Testcontainers | Real PG18+pgvector Docker per test run |
| **Unit Tests** | Vitest (TS) / pytest (Python) | No DB, mocked dependencies |

Testcontainers gives perfect fidelity with complete isolation. No shared state between runs. Dev/CI only, not customer-facing.

---

## Infrastructure (Design Decisions)

| Concern | Decision | Detail |
|---------|----------|--------|
| **Hosting** | Managed SaaS (C5-3) | We host, design for customer VPC later |
| **Cloud** | TBD — platform-agnostic | Azure, AWS, Oracle all candidates |
| **Region** | Australia first (C5-2) | Region-aware design, single deploy for MVP |
| **Monitoring** | Custom → Prometheus+Grafana (C6-1) | Custom tables for MVP, Prom/Grafana when dashboards needed |
| **Connection Pooling** | PgBouncer | Standard for PostgreSQL |
| **Migrations** | Alembic (Python) or Flyway (JVM) | TBD based on team preference |
| **OS** | Linux primary | Platform-agnostic target |

---

## What's NOT Decided (Gate 3)

- Specific PostgreSQL migration tool (Alembic vs Flyway)
- Container orchestration (Docker Compose vs Kubernetes)
- CI/CD platform (GitHub Actions vs GitLab CI vs etc.)
- CDN provider for frontend assets
- Specific cloud provider and instance sizing
- IaC tooling (Terraform vs Pulumi vs cloud-native)

---

## ADR Cross-Reference

These decisions should be formalised as ADRs during Gate 3:

| ADR | Topic | Status |
|-----|-------|--------|
| ADR-001 | Fastify over Express | Decision made, ADR not authored |
| ADR-002 | Custom RAG over frameworks | Decision made, ADR not authored |
| ADR-003 | pgvector over dedicated vector DB | Decision made, ADR not authored |
| ADR-004 | Split LLM/Embedding provider interfaces | Decision made, ADR not authored |
| ADR-005 | Testcontainers for integration tests | Decision made, ADR not authored |

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-06-tech-stack.md
