---
tags:
  - project/Project-Metis
  - scope/system
  - type/architecture
  - domain/security
created: 2026-03-08
updated: 2026-03-08
status: validated
---

# Security Architecture

Cross-cutting document. Covers deployment isolation, access control, agent security boundaries, integration security, and audit trail.

This document captures validated architectural decisions. Implementation detail deferred to Gate 2 (Security & Access Model, Doc 8).

---

## 1. Deployment Model — Separate Instances

Each enterprise customer gets a **complete, independent METIS deployment**. Not a shared platform with isolated databases — a fully encapsulated instance. Nimbus Server, Ford Server, Rio Tinto Server.

This eliminates cross-tenant data leakage by design. One customer's data physically cannot reach another because they are on different servers.

A lightweight admin/management layer may sit above all instances for monitoring, updates, and subscription management. The scope and design of that layer is deferred.

**Implications:**
- No multi-tenant routing logic required within the application.
- Each instance can be on a different version (useful for staggered rollouts).
- Updates must be pushed to each instance.
- Scaling means spinning up new infrastructure, not adding rows.
- At low customer counts (nimbus first, then growth), operational overhead is manageable.

---

## 2. Within-Instance Access Control

Within a single instance (e.g. nimbus), multiple clients may exist (Monash, future clients). Data access is controlled by **RBAC + project/client scoping**.

### How it works

- Every data item has **scope tags**: which client, which project, which sensitivity level.
- Every user has **role + assignments**: their actor type (from the Actor Map) and which clients/projects they are assigned to.
- The **query layer enforces the intersection**: a user can only see data that matches both their role permissions and their project/client assignments.

### Example: nimbus instance

| Actor | Sees | Does Not See |
|---|---|---|
| PS Consultant (assigned to Monash) | Monash project data, Monash knowledge, Monash configs | Contract/commercial data for Monash. Any Rio Tinto data. |
| Support Staff (assigned to Monash + Rio Tinto) | Support data for both clients, within their role scope | Commercial data, developer-level code for either client. |
| Enterprise Admin | Everything within the nimbus instance | — |

### Notes

- Aligns with the earlier decision: "simple RBAC now, full later."
- Role definitions map to the Actor Map (Gate 1 Doc 2): Platform Builder, Enterprise Admin, PS Consultant, Support Staff, Developer.
- The RBAC engine is built properly from day one — it underpins everything else in this document.

---

## 3. Agent Access Boundaries

AI agents must not be a backdoor around human access control. If a PS consultant cannot see Monash's contract spend, they cannot ask an AI agent to retrieve it for them either.

### Two rules

**Rule 1 — Agent inherits requesting human's access ceiling.** An agent can never see more than the human who initiated the work. The Augmentation Layer enforces this by propagating the human's scoped session token to every agent in the chain.

**Rule 2 — Agent is further constrained to task/project scope.** Within what the human could see, the agent only retrieves what is relevant to its current project/task assignment. This prevents "AI bleed" — agents getting confused by cross-project context.

### Phase 1: Hard scope, no elevation

In Phase 1, access boundaries are hard. If you don't have access, the agent doesn't have access. No exceptions, no elevation mechanism.

### Future: Elevated Access Gatekeeper

Designed for but not built in Phase 1. The pattern:

1. Agent or human hits an access boundary and submits a request.
2. A gatekeeper (human approver, or future gatekeeper agent) evaluates the request: is it legitimate, is the requester appropriate, does the context justify it?
3. If approved, the response comes in one of two forms:
   - **Summary**: the gatekeeper retrieves the data and sends back only what is relevant, without exposing full source material.
   - **Redacted access**: the actual documents are released with sensitive parts stripped.
4. The request, evaluation, decision, and response are all logged in the audit trail.

The architecture must accommodate this in the access control layer design so it can be added without rewriting the security model.

---

## 4. Agent Action Boundaries

Separate from what agents can see (Section 3), this covers what agents can **do**. Permissions are category-specific, aligned with the three agent categories in the Actor Map.

### Cross-cutting rules (all categories)

- **All agents access backend through the application layer, never directly to the database.** The application layer is the single enforcement point for RBAC, action validation, and audit logging. Same pattern proven in Claude Family (e.g. `start_session` vs raw SQL).
- **All deletes are soft deletes.** Nothing is permanently removed from the database. Deleted records get a flag (`is_deleted` / `deleted_at`). Supports audit trail, recovery, and accountability. Applies to all actors — human and AI.

### Category B — Event-Driven Agents (lowest risk)

Document Scanner, Knowledge Ingestion Agent, Notification Agent. Isolated, triggered by events, stateless per invocation.

| Action Type | Permitted | Notes |
|---|---|---|
| Read | Yes | Read incoming content within scope |
| Create | Yes | New entries, processed outputs, alerts |
| Modify | Limited | Metadata updates only (e.g. re-ingestion flags), not content |
| External | Limited | Outbound notifications only, not writing to enterprise systems |
| Delete | No | — |

### Category A — Project Agents (medium-high risk)

Controller, Supervisors, Specialists (Design, Analysis, BPMN, Test, Coder, Documentation). Doing real project work under supervision.

| Action Type | Permitted | Notes |
|---|---|---|
| Read | Yes | Within access scope (human ceiling + task scope) |
| Create | Yes | Generate documents, drafts, test scenarios, reports — new content within METIS |
| Modify | Requires human approval | Editing existing knowledge, updating project state, changing configs. Agent proposes, human confirms. |
| External | Requires human approval | Pushing to Jira, Confluence, enterprise APIs. Agent prepares the action, human approves execution. |
| Delete | Requires human approval | Soft delete only. May be restricted to Enterprise Admin via platform UI, not via agents. |

**Principle:** Agents are great at producing work. The risk comes when they change things or push things out. That is where the human checkpoint sits.

### Category C — System-Level Agents (mixed risk)

Master AI, Health Monitor, Knowledge Quality Agent. Continuous or scheduled. Monitor and maintain the system itself.

| Action Type | Permitted | Notes |
|---|---|---|
| Read | Yes | Broad read access for monitoring |
| Create | Yes | Health reports, quality flags, maintenance logs |
| Modify | Limited | Status fields only (e.g. "service degraded"). Knowledge Quality Agent flags stale entries but does not modify or delete them. |
| External | No | System agents do not interact with enterprise systems |
| Delete | No | — |

**Principle:** System agents observe and report. They do not act on what they find. Flagging for human review, not self-healing.

---

## 5. Authentication Architecture

Authentication is a **pluggable adapter behind a common auth interface**. The application layer defines a contract: credential in, authenticated identity out. Different providers plug in behind it.

### Phase 1: Simple token auth

Admin generates tokens for users. Tokens carry role and scope. Good enough for nimbus internal use and development. No external dependencies.

### Later: SSO (SAML / OIDC)

Enterprise identity provider handles login. METIS receives the authenticated identity and maps it to its internal roles and assignments. Adds SSO support without touching the RBAC engine or anything downstream.

### Future: Additional providers

API keys for system-to-system. Certificate-based auth for agents. Whatever is needed — the interface accommodates new providers.

### Key separation

- **Authentication** (who are you?) = pluggable front-end. Swap providers via config, not rewrite.
- **Authorization** (what can you do?) = RBAC engine inside the application layer. Built properly from day one. Does not change when auth providers change.

Everything downstream of the auth interface — RBAC, session tokens, agent access propagation — works with the authenticated identity, not the auth mechanism.

### Session token propagation

When a human starts work that kicks off agents, the session carries a scoped token with their identity, role, and assignments. This token propagates through the agent hierarchy: Controller → Supervisors → Specialists. Every knowledge retrieval and every action goes through the application layer with that token.

Modelled on the nimbus time2work pattern: SSO and username/password are two different front doors into the same configurable security role system.

---

## 6. External Integration Security

Covers bidirectional connections through the Integration Hub — Jira, Confluence, CRM, enterprise product APIs.

### Credential Storage

Design for an external secrets manager, start with encrypted database storage.

- **Phase 1:** Credentials encrypted at rest in the instance database. Sufficient for initial deployment.
- **Architecture:** A credential access interface abstracts the storage backend. A secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) can be plugged in later without rewriting the integration layer. Same pluggable adapter pattern as auth.

### Access Scope

Per-user delegation preferred. When METIS connects to an external system (e.g. Jira), it uses the current user's own credentials (API key, OAuth token). This inherits the enterprise's existing access controls — METIS can never see more in the external system than the human could.

Acknowledged this is optimistic for Phase 1 and depends on what each integration supports. High-level interface design needed; implementation detail deferred.

### Direction Control

Each integration connector should be configurable as read-only, write-only, or bidirectional. A customer might want METIS reading from Jira but not writing back, at least initially.

---

## 7. External API Data Handling

METIS instances call out to LLM providers (Claude API) and embedding services (Voyage AI). Enterprise data is sent to these third-party services.

- Per-instance deployment means only that customer's data goes to the API. No cross-tenant risk.
- Commercial API data handling policies (e.g. Anthropic API calls not used for training) are a factual selling point.
- **Known constraint, not a Phase 1 blocker.**
- Self-hosted or on-premise LLM option may be required for regulated industries (government, defence, healthcare) in the future. Noted for future architecture consideration, not designed now.

---

## 8. Audit Trail

Everything is logged. The audit trail serves three purposes beyond basic accountability.

### Three use cases

1. **Crash recovery.** If a session dies mid-work, the audit trail has enough state to reconstruct where things were up to — what the agent was doing, what it had completed, what was pending.
2. **Language analysis and adaptation.** Interaction history used to understand how a specific human communicates — terminology, patterns, shortcuts — feeding back into the Augmentation Layer's context assembly for that user over time.
3. **Error and drift detection.** Analysing request and conversation patterns to spot misunderstandings, confusion, repeated corrections, and context drift.

All three require **rich, structured logging**: what was requested, what context was assembled, what the agent produced, what the human's response was.

### Tiered retention

| Tier | Retention | What |
|---|---|---|
| **Tier 1 — Permanent** | Never decays | Security events (auth, access denied, elevated access requests). Write/modify/delete actions (what changed, who, when). Human approval decisions. Agent lifecycle (created, scope, outcome). |
| **Tier 2 — Medium** | Configurable (e.g. 6-12 months) | Full conversation transcripts. Context assembly logs (knowledge retrieved, prompt constructed). External system call details. |
| **Tier 3 — Short** | Weeks/months, or aggregated | Routine read access logs. Health check results. Performance metrics. |

### Extract-then-decay

Raw Tier 2 data is processed into **durable knowledge insights** before it decays. Language patterns, error signatures, and interaction learnings are extracted and stored as knowledge entries. The raw logs then age out, but the insights persist.

### Storage

PostgreSQL audit tables within the instance database. Write interface abstracted behind an audit service layer so storage can be migrated to a separate store if volume requires it. Same pluggable pattern used throughout.

---

## 9. Recurring Architecture Pattern

A consistent pattern emerges across this document: **pluggable adapters behind stable interfaces.**

| Component | Phase 1 (Simple) | Future (Pluggable) |
|---|---|---|
| Authentication | Token-based | SSO (SAML/OIDC), API keys, certificates |
| Credential storage | Encrypted DB | External secrets manager |
| Audit storage | PostgreSQL tables | Dedicated audit store if needed |
| Elevated access | Hard scope, no elevation | Gatekeeper with request/approval workflow |

The principle: define the interface first, implement the simplest provider that works, swap to more capable providers later without rewriting the consuming code. Start simple, design for growth.

---

## 10. Open Questions and Deferred Items

- [ ] Human-AI interaction model: controlled METIS UI vs MCP-exposed services vs both. Flagged for its own session — affects security boundaries for Mode 2 (external tool) interactions.
- [ ] Admin/management layer above all instances — scope and design deferred.
- [ ] Elevated access gatekeeper implementation — Phase 2+.
- [ ] Per-user delegation feasibility per integration type — depends on what each external system supports.
- [ ] Self-hosted LLM option for regulated industries — future architecture consideration.
- [ ] Data retention policies per customer (may vary by industry/regulation).
- [ ] How scope tags are structured in the data model — implementation detail for Gate 2.

---

## 11. Relationship to Other Documents

| Document | Relationship |
|---|---|
| Assumptions & Constraints (Gate 0 Doc 2) | Constraint 6 (data isolation) is now addressed by this document. |
| Actor Map (Gate 1 Doc 2) | Human actors → RBAC roles (Section 2). Agent categories → action boundaries (Section 4). |
| System Map C4 L2 (Gate 0 Doc 4) | API Layer handles auth routing. Application Services enforce RBAC. Integration Hub covered in Section 6. |
| System Product Definition | Constrained deployment pattern (Section 4.2) aligns with agent access boundaries. |
| Plan-of-Attack | Phase 1 = simple implementations throughout. Architecture designed for growth. |

---
*Security Architecture | Validated: 2026-03-08 | Author: John de Vere + Claude Desktop*
