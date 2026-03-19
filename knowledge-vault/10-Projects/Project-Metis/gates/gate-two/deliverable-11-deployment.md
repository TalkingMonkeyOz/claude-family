---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/11
  - type/deployment
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 11: Deployment Architecture

## Overview

Separate instance per customer. Managed SaaS. Platform-agnostic. Region-aware design, single-region deploy for MVP.

---

## 1. Instance Model

Each enterprise customer gets a **complete, independent METIS deployment**:

```
┌─────────────────────────────────────┐
│  Customer Instance (e.g. Nimbus)    │
│  ┌───────────┐  ┌───────────────┐  │
│  │ Fastify   │  │ SpiffWorkflow │  │
│  │ API + MCP │  │ Engine        │  │
│  └─────┬─────┘  └───────┬───────┘  │
│        │                │          │
│  ┌─────┴────────────────┴───────┐  │
│  │ PostgreSQL 18 + pgvector     │  │
│  │ (PgBouncer connection pool)  │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ React + MUI (static bundle) │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
         │              │
    Anthropic API    Voyage AI
    (Claude)         (Embeddings)
```

**Why separate instances:**
- No cross-tenant data leakage by design
- Each instance can be on a different version (staggered rollouts)
- Simpler security model — no multi-tenant routing logic
- At low customer counts, operational overhead is manageable

---

## 2. Environments

| Environment | Purpose | Access |
|-------------|---------|--------|
| **Local Dev** | Developer workstations | Developers only |
| **Dev/Test** | CI/CD, integration tests | Automated + developers |
| **Monash POC** | First customer, proof of concept | Monash users + us |
| **Production** | Live customer instances | Customer users |

### Local Dev

- Docker Compose: Fastify + PostgreSQL 18 + pgvector
- Testcontainers for integration tests (C1-4)
- Mock LLM/embedding providers for offline development
- Hot reload via Vite (frontend) and Fastify watch (backend)

### Dev/Test

- Mirrors production topology
- Testcontainers in CI pipeline
- Automated test suite runs on every PR
- No real customer data

### Monash POC → Production

- Same deployment artifact, different config
- POC has relaxed SLOs, production has full monitoring

---

## 3. Deployment Model (C5-3)

### Current: Fully Managed SaaS

- We host everything — customer gets URL + login
- We control updates, monitoring, backups, security patches
- Single operational team manages all instances

### Future: Customer VPC (Design-Ready)

Not built yet, but architecture doesn't prevent it:
- All services containerised (Docker)
- Config externalised (environment variables, not hardcoded)
- No assumptions about network topology
- Database connection strings are config-driven
- Deployment scripts parameterised

**Trigger to build VPC path:** When a customer with strict data requirements demands it and the revenue justifies the support cost.

---

## 4. Data Residency (C5-2)

### Current: Australia (Single Region)

All infrastructure deployed in Australian region. Covers AU compliance requirements for initial customer base.

### Region-Aware Design

No hardcoded region assumptions:
- Database connection strings: config
- API endpoints for LLM/embedding providers: config
- File storage paths: config
- Deployment scripts: region as parameter

**Adding a second region = config change, not architecture change.**

### Cloud Platform: TBD

Candidates: Azure, AWS, Oracle. Decision deferred until closer to deployment. All three support:
- PostgreSQL 18 managed instances
- Linux container hosting
- Region selection
- VPC/network isolation

---

## 5. Infrastructure Components

| Component | Purpose | Notes |
|-----------|---------|-------|
| **PgBouncer** | Connection pooling | Standard for PostgreSQL at scale |
| **Alembic or Flyway** | Database migrations | TBD — Alembic if Python-heavy, Flyway if JVM tools preferred |
| **Table partitioning** | High-volume tables | workflow_step_log, activity_access_log, audit tables |
| **Container runtime** | Service packaging | Docker |
| **Reverse proxy** | TLS termination, routing | Nginx or Caddy |

### Partitioning Strategy

Tables that grow unboundedly get time-based partitioning:
- `workflow_step_log` — by month
- `activity_access_log` — by month
- Audit/log tables — by month
- Aligns with retention policies (C2-5) — drop old partitions instead of row-by-row delete

---

## 6. Update & Maintenance Strategy

| Concern | Approach |
|---------|----------|
| **Version management** | Each instance tracks its version. Staggered rollouts supported. |
| **Database migrations** | Run before app update. Backward-compatible migrations preferred. |
| **Zero-downtime** | Rolling deployment — new container up before old one down |
| **Rollback** | Previous container image retained. DB migrations must be reversible. |
| **Backup** | Automated daily PostgreSQL backups. Point-in-time recovery. |

---

## 7. Cost Estimate (Nimbus Reference)

From prior design work — nimbus-specific:

| Component | Estimated | Notes |
|-----------|-----------|-------|
| Compute (Azure B2ms or equivalent) | ~$60/month | 2 vCPU, 8GB RAM |
| PostgreSQL Flexible | ~$50/month | 2 vCPU, managed |
| Anthropic API | Variable | ~$50-200/month depending on usage |
| Voyage AI | Variable | ~$10-30/month |
| **Total per instance** | **~$140-340/month** | Excluding staff time |

Scales roughly linearly per customer. Volume discounts on API costs at scale.

---

## 8. Open Items (Gate 3)

- [ ] Cloud provider selection
- [ ] Container orchestration (Compose vs Kubernetes)
- [ ] CI/CD platform selection
- [ ] IaC tooling (Terraform vs Pulumi)
- [ ] Deployment topology diagram
- [ ] VM/resource sizing benchmarks
- [ ] Provisioning runbooks
- [ ] Backup retention and testing schedule
- [ ] Network security (firewalls, security groups)
- [ ] TLS certificate management

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-11-deployment.md
