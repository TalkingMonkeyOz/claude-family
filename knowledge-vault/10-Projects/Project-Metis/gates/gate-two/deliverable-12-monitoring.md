---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/12
  - type/operations
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 12: Monitoring, Logging & Observability

## Overview

Three monitoring categories, phased rollout, configurable everything via admin centre. Principle: measure from day one, dashboard later.

---

## 1. Monitoring Categories

| Category | What | Examples |
|----------|------|---------|
| **Platform Health** | System vitals | API latency, error rates, DB connections, queue depth |
| **LLM / Cost** | AI spend + quality | Token usage per customer, cost per query, embedding costs |
| **Agent Compliance** | Behavioural drift | Rule adherence, scope violations, hallucination rate |

---

## 2. Phased Rollout (C6-1)

| Phase | What | When |
|-------|------|------|
| **P0** | Custom monitoring tables + `/health` endpoint | MVP |
| **P1** | Prometheus metrics exposition | Post-MVP |
| **P2** | Grafana dashboards | When needed |

Build with Prometheus/Grafana in consideration — structure custom table metrics so they can be easily exposed as Prometheus counters/gauges later.

No cloud-native monitoring (platform-agnostic). No paid SaaS (Datadog etc.) until scale justifies.

---

## 3. Structured Logging

Every log entry: structured JSON with 8 always-present fields.

```json
{
  "timestamp": "2026-03-15T09:30:00.123Z",
  "level": "error",
  "service": "knowledge-engine",
  "request_id": "req_7f8a9b2c",
  "scope_org_id": "uuid",
  "scope_engagement_id": "uuid",
  "message": "Embedding generation failed",
  "context": { "item_id": "uuid", "provider": "voyage-ai", "error": "rate_limited" }
}
```

**Rules:**
- Sensitive data never logged (customer content, credentials, PII)
- `request_id` correlates user-facing errors to backend traces
- `context` is the extensible bag — structured, not free-text

---

## 4. Token Budget Management (C6-2)

### Four-Level Hierarchy

| Level | Set By | Example |
|-------|--------|---------|
| **System** | Us | 500K tokens max per request |
| **Customer** | Us / admin | 2M tokens/month for this engagement |
| **Agent** | System config | Conversational: 100K, workflow: 50K, system: 10K |
| **Request** | System config | 32K per LLM call |

### Graduated Enforcement

1. **Getting tight** (~80% budget) → slim down: shorter context, summarised knowledge, less history
2. **At limit** (~95%) → warn user + alert admin. Display: "You've reached your allocation. Contact admin to increase."
3. **Over limit** (100%) → reject with explanation, never silent failure

### Tracking

- Per-customer monthly usage table
- Per-request token count logged
- Real-time budget check before LLM call
- Admin dashboard shows usage trends (P2)

All thresholds configurable via admin centre.

---

## 5. SLOs (C6-3)

Internal targets only — no contractual commitments until proven.

| Metric | Initial Target | Measurement |
|--------|---------------|-------------|
| API availability | 99.5% | Uptime checks on `/health` |
| `ask` response (p95) | < 10s | Request duration histogram |
| `search` response (p95) | < 2s | Request duration histogram |
| `ingest` per item | < 60s | Processing time |
| Knowledge freshness | < 5min | Time from source event to embedded |

**All configurable via admin centre.** Targets are starting points — calibrate with real production data. Move to contractual SLAs only when 3+ months of sustained delivery proves capability.

---

## 6. Log Retention (C6-4)

Same tiered framework as data retention (C2-5). Configurable within floor/ceiling bounds.

| Log Type | Default | Floor | Rationale |
|----------|---------|-------|-----------|
| Application (errors/warnings) | 90 days | 30 days | Debugging value |
| Audit (who did what) | 3 years | 2 years | Regulatory |
| Agent interaction | 90 days | 30 days | High volume, debugging only |
| LLM calls (prompts/responses) | 30 days | 7 days | Highest volume, sensitive content |
| Performance/metrics | 1 year | 90 days | Trend analysis |

Enforcement: same soft-delete + delayed hard purge pattern. RBAC permission `retention.manage` controls customer admin access.

---

## 7. Compliance Metrics (Prior Design)

7 agent compliance metrics with measurement methods:

| Metric | Measurement | Threshold |
|--------|-------------|-----------|
| Rule adherence | Protocol injection check rate | TBD (needs calibration) |
| Scope violations | Off-topic classifier triggers | < 5% of requests |
| Task completion | Workflow step success rate | > 90% |
| Hallucination rate | Citation verification | < 5% |
| Context utilisation | Retrieved vs used knowledge ratio | > 60% |
| Response quality | User feedback scores | > 4.0/5.0 |
| Drift detection | Baseline comparison over time | Trend, not threshold |

---

## 8. Open Items (Gate 3)

- [ ] Specific Prometheus metric names and types
- [ ] Grafana dashboard layout design
- [ ] Alerting rules and notification channels
- [ ] Token budget hard cap numbers (need usage data)
- [ ] Compliance threshold calibration
- [ ] Log aggregation strategy (per-instance vs centralised)

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-12-monitoring.md
