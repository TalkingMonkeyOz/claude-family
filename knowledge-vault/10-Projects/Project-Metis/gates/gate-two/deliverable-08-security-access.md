---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/8
  - type/security
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 8: Security & Access Model

Builds on [[security-architecture|Security Architecture]] (validated 2026-03-08, 12 decisions). This deliverable adds implementation-level design from Gate 2 decisions.

---

## 1. Security Decision Summary

### Prior Decisions (Gate 0/1 — validated 2026-03-08)

| # | Decision | Status |
|---|----------|--------|
| 1 | Separate instances per customer | Validated |
| 2 | RBAC + project/client scoping | Validated |
| 3 | Agent inherits human access ceiling | Validated |
| 4 | Agent further constrained to task scope | Validated |
| 5 | All agents through application layer | Validated |
| 6 | All deletes are soft deletes | Validated |
| 7 | Pluggable auth adapter (JWT → SSO) | Validated |
| 8 | Audit log everything | Validated |
| 9 | Tiered retention for audit logs | Validated |
| 10 | Extract-then-decay for raw logs | Validated |
| 11 | Per-user delegation preferred | Validated |
| 12 | Pluggable credential storage | Validated |

### New Decisions (Gate 2 — confirmed 2026-03-14/15)

| # | Decision | Detail |
|---|----------|--------|
| C2-5 | Data retention policies | Tiered presets + RBAC customer override |
| C3-B | Scope guardrails | Per-engagement policy + per-user permission |
| C5-1 | Credential delegation | Hybrid OAuth + encrypted vault |
| C5-2 | Data residency | Region-aware, AU first |
| C5-3 | Deployment model | Managed SaaS, design for VPC |
| C5-4 | DPA with Anthropic | Commercial task, onboarding checklist |
| C6-4 | Log retention | Tiered framework matching data retention |

---

## 2. Credential Delegation (Implementation Design)

Expands on prior decision #11 (per-user delegation preferred).

### Hybrid Model

| External System Type | Delegation Method |
|---------------------|-------------------|
| Modern SaaS (OAuth 2.0) | OAuth delegation — store refresh tokens, obtain access tokens on-demand |
| Legacy systems (API key/basic auth) | Encrypted credential vault — per-user, per-connector |
| Systems with no auth API | Service account with logged impersonation |

### Credential Vault Design

- **Encryption**: At rest, per-tenant encryption key
- **Scope**: Credentials stored per user + per connector (not global)
- **Caching**: Short-lived access token cache to avoid vault lookup per call
- **Interface**: Abstracted behind credential access service (pluggable — vault today, secrets manager later)

### RBAC for Credential Management

| Permission | Who | What |
|------------|-----|------|
| `credentials.own.manage` | All users | Manage their own credentials |
| `credentials.all.view` | Enterprise Admin | View credential status (not values) for all users |
| `credentials.all.manage` | Platform Builder | Full credential management |

---

## 3. Scope Guardrails (Content Boundary Enforcement)

New decision — prevents METIS from being used outside its intended purpose.

### Policy Model

- **Engagement-level**: Defines domain boundary using domain tags from knowledge base
- **User-level**: RBAC permission `scope.general_access` controls off-topic use
- **No global blocklist**: Domain is the scope (adult retailer can discuss adult products)

### Enforcement

- Lightweight topic classifier checks query against engagement domain tags
- Before LLM call — reject off-topic before hitting expensive model
- Policy options per engagement: "strict domain only" or "domain-first, general allowed"

### Transparency

- Off-topic requests (allowed or blocked) logged for customer admin review
- User sees clear explanation when blocked, not silent failure

---

## 4. Data Residency & Compliance

### Current State

- Single region deployment (Australia) for MVP
- Region-aware design — no hardcoded region assumptions
- Cloud platform TBD (Azure, AWS, Oracle)

### Adding Regions

Adding a second region = config change, not architecture change:
- Database connection strings are config-driven
- Deployment scripts parameterised by region
- No region-specific code paths

### DPA Requirements

- Anthropic DPA: commercial task, prerequisite for data-sensitive customers
- Customer onboarding checklist includes: "Does this customer require a DPA?"
- LLM abstraction (C4-4) enables swap to self-hosted model if customer refuses external API

---

## 5. Data & Log Retention (Unified Framework)

Single retention framework covers both data and logs. See [[gate-two/decisions-cluster2#C2-5|Cluster 2 Decision 5]] for full model.

### RBAC Permissions

| Permission | Who | What |
|------------|-----|------|
| `retention.view` | Enterprise Admin | View current retention config |
| `retention.manage` | Granted by us | Modify retention within floor/ceiling |

### Retention Defaults

| Category | Default | Floor | Ceiling |
|----------|---------|-------|---------|
| Knowledge items | Permanent | 1 year | — |
| Workflow step logs | 3 years | 2 years | — |
| Audit logs | 3 years | 2 years | — |
| Session/activity | 1 year | 90 days | — |
| Agent interaction logs | 90 days | 30 days | — |
| LLM call logs | 30 days | 7 days | — |
| Application logs | 90 days | 30 days | — |
| Performance/metrics | 1 year | 90 days | — |
| Embeddings | Match source | 0 | — |

### Enforcement

- Soft-delete scheduled job, hard purge delayed (recovery window)
- Customer admins can extend or shorten within bounds
- Floor is immutable by customer — we set it, protects us legally

---

## 6. Deployment Security

### Managed SaaS (Current)

- We host everything — full control over security posture
- Customer gets URL + login, nothing else exposed
- Updates pushed by us, no customer-side maintenance

### Future: Customer VPC

- Containerised architecture enables deployment into customer's cloud account
- We still manage — customer's network boundary, our operations
- Not built yet, but no architectural decisions that prevent it

---

## 7. Open Items (Gate 3)

- [ ] Formal threat model document
- [ ] Elevated access gatekeeper implementation (Phase 2+)
- [ ] Self-hosted LLM option for regulated industries
- [ ] Admin/management layer above all instances
- [ ] SSO provider integration testing
- [ ] Per-integration credential delegation feasibility matrix

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-08-security-access.md
