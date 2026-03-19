---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - scope/system
  - level/2
  - phase/1
projects:
  - Project-Metis
created: 2026-02-24
synced: false
---

# Monitoring & Alerting Design — Brainstorm

> **Scope:** system
>
> **Design Principles:**
> - Monitor what matters, not everything — signal vs noise
> - Alerts should be actionable — if you can't act on it, don't alert on it
> - Build monitoring into the platform from Phase 0 (health checks, audit logs) but formal dashboards come later
> - Start with logs and health endpoints. Add metrics and dashboards when there's enough data to visualise.

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

---

## What We're Monitoring

Three categories of things to watch:

### 1. Platform Health (Is it working?)

| What | How | When To Alert |
|------|-----|--------------|
| Database connection | Health check endpoint polls DB | Connection lost or latency > 5s |
| pgvector extension | Health check confirms extension loaded | Extension missing after migration |
| API server responding | Health endpoint returns 200 | Non-200 for > 1 minute |
| Migration status | Health check reports applied migration count | Mismatch between environments |
| Disk/memory usage | OS-level metrics on hosting VM | Above 80% sustained |

### 2. LLM & Cost (Are we spending sanely?)

| What | How | When To Alert |
|------|-----|--------------|
| LLM API spend | Track via API billing dashboard / workspace spend | Approaching monthly cap (80%) |
| Token usage per session | Log input/output tokens per API call | Session exceeds expected range (10x average) |
| API errors / rate limits | Log non-200 responses from LLM API | Rate limit hits, 5xx errors |
| Embedding costs | Track Voyage AI API calls | Unexpected spike (bulk re-embed) |
| Cache hit rate | Track cached vs uncached prompt calls | Cache miss rate > expected (cost impact) |

### 3. Agent Compliance (Are the agents behaving?)

This overlaps heavily with the compliance metrics framework in [[orchestration-infra/agent-compliance-drift-management]]. Key signals:

| What | How | When To Alert |
|------|-----|--------------|
| Session duration | `sessions` table — time between start and end | Sessions > 4 hours (drift risk) |
| Task closure rate | `work_items` table — open vs closed at session end | Rate drops below 50% |
| BPMN gate failures | SpiffWorkflow rejection log | Failure spike (agent can't pass checkpoints) |
| Protocol version change | `protocol_versions` table | Any change by agent (requires human approval) |
| Word count drift | Protocol version word count trending | Shrinking >10% (compression/semantic drift) |

---

## Monitoring Architecture — Brainstorm

### Phase 0: Health Checks + Structured Logs

Simplest possible approach. No external monitoring tools.

- **Health endpoint** (`GET /health`) returns JSON with DB status, pgvector, migration count, uptime
- **Structured logging** to stdout (JSON format) — query with standard log tools
- **Audit log table** — queryable history of all platform actions
- **Manual checking** — John runs health check, reviews audit log periodically

### Phase 1: Add Metrics Collection

Once the platform has real activity:

- **Application metrics** — request count, latency percentiles, error rate per endpoint
- **LLM metrics** — token usage, cost per query, cache hit rate, model distribution
- **Knowledge Engine metrics** — query count, average similarity score, zero-result queries

**Open question:** Do we build custom metrics tables, or use an off-the-shelf metrics tool?

Options:
- **Custom tables** — simple, no dependencies, queryable with SQL. Suitable for low volume.
- **Prometheus + Grafana** — industry standard. Free. But adds two services to host and maintain.
- **Azure Monitor** — native to Azure. May already be available on nimbus infrastructure. Less setup.
- **Lightweight alternative** — something like Uptime Kuma for health monitoring (self-hosted, simple).

> Brainstorm note: For Phase 0-1 with a single developer, custom tables + health endpoint is sufficient. Don't add monitoring infrastructure that needs its own monitoring. Prometheus/Grafana or Azure Monitor is a Phase 2-3 decision when there are real users and real traffic patterns to observe.

### Phase 2+: Dashboards & Alerts

- **Dashboard** showing: platform health, active sessions, recent agent activity, cost tracking, compliance scores
- **Alerts** via email or Slack when thresholds are breached
- **Compliance dashboard** (per agent compliance design) — monthly report generation

---

## What Gets Logged (Structured Logging)

Every log line is JSON with consistent fields:

| Field | Always Present? | Example |
|-------|----------------|---------|
| `timestamp` | Yes | ISO 8601 UTC |
| `level` | Yes | info, warn, error |
| `message` | Yes | Human-readable description |
| `service` | Yes | api, knowledge, connector, agent |
| `sessionId` | If in session | UUID |
| `userId` | If authenticated | UUID |
| `agentName` | If agent action | KnowledgeAgent |
| `duration_ms` | For timed operations | 245 |
| `error` | If error | Error code + message (no stack in production) |

**Never logged:** passwords, tokens, credentials, full request bodies with sensitive data.

---

## Alerting Philosophy

**Phase 0-1:** No automated alerts. John checks health endpoint and logs manually. The system is not yet critical enough to warrant wake-up-at-3am alerting.

**Phase 2+:** Alerts for:
- Platform down (health check failing)
- Cost approaching cap
- Agent compliance dropping (BPMN gate failure rate spiking)
- Database storage approaching limits

**Alert channels (brainstorm):**
- Email (simplest, always works)
- Slack (if Slack MCP is connected — already is)
- In-platform notification (if we build a web UI)

---

## Gaps / Open Questions

- [ ] Monitoring tool choice — custom tables vs Prometheus/Grafana vs Azure Monitor? Defer to Phase 2.
- [ ] Log retention — how long do we keep structured logs? Audit logs are forever, but application logs?
- [ ] Cost tracking granularity — track per-session, per-agent, per-customer, or just total monthly?
- [ ] Alert thresholds — what are sensible defaults? Need real data from Phase 0-1 to calibrate.
- [ ] Who gets alerts? John only in Phase 0. Who else when platform has multiple users?

---
*Source: Orchestration README, compliance design, Doc 4 security architecture | Created: 2026-02-24*
