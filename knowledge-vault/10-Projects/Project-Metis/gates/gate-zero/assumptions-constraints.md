---
tags:
  - project/Project-Metis
  - scope/system
  - type/gate-zero
  - gate/zero
created: 2026-03-07
updated: 2026-03-11
status: validated
---

# Assumptions & Constraints

Gate Zero Document 2.

## Assumptions

These are things we believe to be true that the platform design depends on.

### 1. Third-party LLM dependency

METIS depends on third-party LLM providers. It does not build its own models. The platform is constrained by whatever the provider offers in terms of context windows, rate limits, pricing, and capabilities. Designed to be provider-agnostic, but always dependent on external AI.

### 2. Enterprise must have domain knowledge to feed the system

The platform is not magic — it learns from what you give it. If an enterprise has no documented processes, no API docs, no historical data, the platform has nothing to ingest. The assumption is that the enterprise either already has domain knowledge in some form, or is willing to create it as part of onboarding.

### 3. Useful from day one with imperfect knowledge

The platform must work with partial knowledge immediately. As part of setup (e.g. connecting pipelines), it should ingest and start helping straight away. Human and machine then train together to improve over time. This is not a big-bang knowledge dump — value starts from first connection and compounds continuously.

## Constraints

These are hard limits that shape what the platform can and cannot do.

### 4. Humans in the loop at validation checkpoints

METIS is not fully autonomous. AI does the heavy lifting, but humans approve, validate, and make final decisions. The platform assumes a human is always available at key points. No automatic escalations or knowledge promotion without human approval.

### 5. One-person build initially

Built alongside a full-time day job. This constrains pace, complexity per sprint, and means the platform must be buildable incrementally — not big-bang. Every design choice must account for this: simple beats elegant, working beats complete.

### 6. Enterprise data isolation and security

Enterprise data must stay within the enterprise's boundary. What one customer feeds in is never visible to another. Multi-tenancy must be isolated and very secure.

**Security progress (updated 2026-03-11):** Security architecture conversation completed 2026-03-08 (see `security-architecture.md`). RBAC scoping confirmed 2026-03-10: tenant-level hard isolation for Client Config and Learned/Cognitive knowledge; Product Domain and API Reference shared across tenants; Process/Procedural shared with tenant-specific variants; Project/Delivery tenant-scoped. Three roles defined: Platform Builder (all tenants), Enterprise Admin (their tenant), Enterprise Staff (work-context scoped). Full design is Gate 2 Doc 8 (Security & Access Model).

### 7. Cloud-hosted with internet connectivity

The platform assumes internet connectivity and cloud hosting in some manner. It is not an air-gapped or offline system. It needs to reach LLM providers, and ideally the enterprise's own systems (APIs, ticketing systems, repositories).

---

*Gate Zero Doc 2 | Validated: 2026-03-07 | Updated: 2026-03-11 (Constraint 6 security progress) | Author: John de Vere + Claude Desktop*

---
**Version**: 1.0
**Created**: 2026-03-07
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-zero/assumptions-constraints.md
