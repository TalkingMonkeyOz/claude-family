---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - type/decisions
created: 2026-03-15
updated: 2026-03-15
---

# Gate 2 — Design Decisions Summary

All 26 design decisions made across 2 interactive sessions (2026-03-14, 2026-03-15). Each stored via `remember()` with embeddings for semantic recall.

## Decision Index

| # | Cluster | Decision | Choice | Detail |
|---|---------|----------|--------|--------|
| C1-1 | Tech Stack | API Framework | Fastify | TypeScript-first, built-in schema validation, plugin DI |
| C1-2 | Tech Stack | Frontend | React + Vite + MUI | Consistent with existing MUI ecosystem, no SSR needed |
| C1-3 | Tech Stack | PostgreSQL Version | PG18 minimum | pgvector 0.8.2+ required, all cloud providers support |
| C1-4 | Tech Stack | Test Database | Testcontainers | Real PG18+pgvector Docker per test run, dev/CI only |
| C2-1 | Data Model | Core Tenant Schemas | Hybrid columns | Dedicated for queried fields + JSONB settings for config |
| C2-2 | Data Model | Scope Tag Structure | Inheritance chain | Full path always populated for single-query retrieval |
| C2-3 | Data Model | Activity Space Entity | Activities + access log | Separate activity_access_log table for co-access signal |
| C2-4 | Data Model | Workflow Instances | Rich record + step log | [[gate-two/decisions-cluster2|See Cluster 2 detail]] |
| C2-5 | Data Model | Data Retention | Tiered presets + RBAC | [[gate-two/decisions-cluster2|See Cluster 2 detail]] |
| C3-1 | Architecture | Context Assembly | Declarative recipes | [[gate-two/decisions-cluster3|See Cluster 3 detail]] |
| C3-B | Architecture | Scope Guardrails | Per-engagement + per-user | [[gate-two/decisions-cluster3|See Cluster 3 detail]] |
| C3-2 | Architecture | Multi-Product Pipeline | Hybrid | Separate ingestion, unified retrieval with scope filtering |
| C3-3 | Architecture | Products Without APIs | Unified connector adapter | API/file-drop/manual all through same interface |
| C4-1 | API & Interface | Error Responses | Consistent envelope | code + message + detail + request_id + timestamp |
| C4-2 | API & Interface | Pagination | Cursor-based | Stable under data changes, opaque base64 cursor |
| C4-3 | API & Interface | MCP Tools | Intent-level composites | ~6 tools not 13+, agents call automatically |
| C4-4 | API & Interface | LLM Abstraction | Split providers | LLMProvider (complete+classify) + EmbeddingProvider |
| C5-1 | Security | Credential Delegation | Hybrid OAuth + vault | OAuth where available, encrypted vault fallback |
| C5-2 | Security | Data Residency | Region-aware, AU first | Design for multi-region, deploy single for MVP |
| C5-3 | Security | Deployment Model | Managed SaaS | Design for customer VPC, build managed only for now |
| C5-4 | Security | DPA with Anthropic | Commercial task | Add to onboarding checklist, not design work |
| C6-1 | Operations | Monitoring Stack | Custom → Prometheus+Grafana | Custom tables for MVP, build with Prom/Grafana in mind |
| C6-2 | Operations | Token Budgets | Graduated 4-level hierarchy | Slim down → warn → reject. Configurable via admin |
| C6-3 | Operations | SLOs | Internal targets only | Configurable values, no contractual SLAs until proven |
| C6-4 | Operations | Log Retention | Tiered framework | Same retention policy model as data retention |

## Cross-Cutting Themes

1. **Configurable via admin centre** — retention, token budgets, SLOs, scope guardrails, log retention. Not hardcoded.
2. **Design for future, build for now** — region-aware but single-region, VPC-capable but managed-only, Grafana-ready but custom tables first.
3. **Consistent patterns** — retention model reused for data AND logs, RBAC controls everything, scope chain used everywhere.
4. **Platform-agnostic** — cloud TBD (Azure/AWS/Oracle), no provider lock-in in monitoring or deployment.

## Detail Files

- [[gate-two/decisions-cluster2|Cluster 2: Data Model]] — workflow_instances schema, retention policies
- [[gate-two/decisions-cluster3|Cluster 3: Architecture]] — context assembly, scope guardrails, multi-product, connectors
- [[gate-two/decisions-cluster4|Cluster 4: API & Interface]] — errors, pagination, MCP tools, LLM abstraction
- [[gate-two/decisions-cluster5-6|Clusters 5-6: Security & Operations]] — credentials, deployment, monitoring, budgets

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/decisions-summary.md
