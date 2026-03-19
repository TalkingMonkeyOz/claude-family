---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - scope/security
  - scope/operations
created: 2026-03-15
updated: 2026-03-15
---

# Clusters 5-6: Security & Operations Decisions (Detail)

Parent: [[gate-two/decisions-summary|Gate 2 Decisions Summary]]

## Cluster 5: Security & Deployment

### C5-1: Per-User Credential Delegation

**Decision:** Hybrid OAuth + encrypted credential vault.

- OAuth delegation where available (modern SaaS) — stores refresh tokens, obtains access tokens on-demand
- Encrypted credential vault as fallback for legacy systems without OAuth
- Integration method depends on what external system supports (often out of our control)
- Vault: encryption at rest (per-tenant key), scoped to user + connector, short-lived token caching
- Agents impersonate user with their exact permissions for per-user audit trail

### C5-2: Data Residency

**Decision:** Single region (Australia) now, region-aware design.

- No hardcoded region assumptions in config, deployment scripts, or DB connections
- Adding a second region = config change, not architecture change
- Cloud platform TBD (Azure, AWS, Oracle — all candidates)
- Aligns with platform-agnostic decision (#6)

### C5-3: Deployment Model

**Decision:** Fully managed SaaS, design for customer VPC.

- We host everything for MVP — can't afford support cost of self-hosting with small team
- Containerise properly so customer VPC deployment is feasible when demanded
- Don't build VPC path yet, just don't prevent it architecturally
- Aligns with MVP = one stream end-to-end (#12)

### C5-4: DPA with Anthropic

**Decision:** Commercial task, not design work.

- Customer data hits Anthropic API in every LLM call
- LLM abstraction (C4-4) enables swap to self-hosted model if customer refuses external API
- DPA initiation is prerequisite for data-sensitive customers
- Add to customer onboarding checklist

---

## Cluster 6: Operations

### C6-1: Monitoring Stack

**Decision:** Custom tables for MVP, Prometheus + Grafana when ready.

- P0: Custom monitoring tables + health endpoint (sufficient for single customer)
- P1: Expose Prometheus metrics
- P2: Grafana dashboards
- Build with Prometheus/Grafana in consideration — structure metrics for easy exposure
- No cloud-native monitoring (platform-agnostic), no paid SaaS until scale justifies

### C6-2: Token Budget Hard Caps

**Decision:** Graduated 4-level hierarchy, all configurable.

| Level | Controls |
|-------|----------|
| System | Absolute ceiling |
| Customer | Monthly allocation per engagement |
| Agent | Per-invocation cap by agent type |
| Request | Single LLM call ceiling |

**Graduated enforcement:**
1. Getting tight → slim down (shorter context, summarised knowledge)
2. At limit → warn user + alert admin (option to increase)
3. Over limit → reject with explanation, never silent failure

Set by us (system/defaults) or customer admin (within allocation). Same RBAC pattern as retention.

### C6-3: SLOs

**Decision:** Internal targets only, configurable via admin centre.

| Metric | Initial Target (TBC) |
|--------|---------------------|
| Availability | 99.5% |
| `ask` p95 | < 10s |
| `search` p95 | < 2s |
| `ingest` per item | < 60s |
| Knowledge freshness | < 5min |

All targets need real-world calibration. No contractual SLAs until 3+ months production data. Move to contractual only when confident in sustained delivery.

### C6-4: Log Retention

**Decision:** Same tiered framework as data retention (C2-5).

| Log Type | Default | Floor |
|----------|---------|-------|
| Application (errors/warnings) | 90 days | 30 days |
| Audit (who did what) | 3 years | 2 years |
| Agent interaction | 90 days | 30 days |
| LLM calls (prompts/responses) | 30 days | 7 days |
| Performance/metrics | 1 year | 90 days |

Configurable via admin centre within floor/ceiling bounds.

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/decisions-cluster5-6.md
