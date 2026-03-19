---
projects:
  - Project-Metis
tags:
  - project/metis
  - type/plan
---

> **⚠️ Design Reference Only** — Execution state has moved to the build board (`get_build_board("project-metis")`). For current decisions, use `recall_entities("metis decision")`. This document captures the original design rationale.

# Phase 0: Foundation

**Goal:** Produce a deployable skeleton — schema, auth, conventions, and project structure — that every subsequent phase builds on.

Back to master: [[plan-of-attack|Plan of Attack]] | Next: [[plan-of-attack-phase1|Phase 1]]

---

## Entry Criteria

- Gate 2 design decisions confirmed (all 26 decisions + 10 behavioural constraints validated)
- Git repository created with agreed folder structure
- Local development environment capable of running PG18 + pgvector + Apache AGE

---

## Deliverables

| Deliverable | Feature Area | Bounded Context | Depends On |
|-------------|-------------|----------------|------------|
| PostgreSQL 18 + pgvector + Apache AGE install | F125 | — | Nothing |
| Core schema — tenant/scope tables | F125 | Tenant & Scope | DB install |
| Scope inheritance chain (C2-2) | F125 | Tenant & Scope | Core schema |
| Auth layer — JWT + RBAC | F125 | Tenant & Scope | Core schema |
| Fastify API skeleton | F125 | Cross-cutting | Auth layer |
| Standard error envelope (C4-1) | F125 | Cross-cutting | Fastify skeleton |
| Cursor-based pagination (C4-2) | F125 | Cross-cutting | Fastify skeleton |
| Audit log table + write path | F125 | Cross-cutting | Core schema |
| Testcontainers integration test harness | F125 | — | DB install |
| Region-aware config (Australia first, C5-2) | F125 | — | Fastify skeleton |
| Project conventions documented | F125 | — | Nothing |

---

## Build Order

### Step 1 — Database layer
Install PostgreSQL 18. Install pgvector 0.8.2+. Install Apache AGE extension. Verify all three extensions coexist and work in the same instance.

**Why first:** Every other piece of work depends on a working database.

### Step 2 — Core schema
Create the tenant/scope tables: `organisations`, `products`, `clients`, `engagements`, `users`, `user_org_access`. Apply C2-1 (hybrid columns + JSONB settings) and C2-2 (full scope chain denormalised on every child row).

**Constraint (D07):** Org → Product → Client → Engagement hierarchy must be enforced at the schema level. Child rows always carry all parent IDs.

**Why now:** Scope chain is a cross-cutting constraint. Every other table references it.

### Step 3 — Auth layer
Implement JWT issuance and verification. Implement RBAC role table and permission checks. Wire into a Fastify plugin so all subsequent routes inherit auth by default.

**Why now:** Auth must exist before any endpoint is built. Retrofitting auth is more expensive than building it first.

### Step 4 — API skeleton
Create the Fastify application with:
- Route registry structure
- AuthMiddleware and ScopeHeaderParser middleware
- Standard error envelope (C4-1): `{code, message, detail, request_id, timestamp}`
- Cursor-based pagination (C4-2): opaque base64 cursors on all list endpoints
- `/health` endpoint (no auth)
- RequestValidator (Fastify's built-in JSON Schema, enabled on all routes)

**Why this order:** Auth first means the skeleton inherits correct security defaults. Conventions established here (error envelope, pagination) must not drift later.

### Step 5 — Audit log
Create `audit_log` table. Implement write path accessible to all bounded contexts. This is cross-cutting — every domain action must be able to emit an audit record from day one.

**Design principle:** "Everything adds value" — audit logging IS value; observability is not optional.

### Step 6 — Test harness
Set up Testcontainers: a Docker-based PG18 + pgvector + AGE container that spins up fresh for each integration test run. Wire into CI. Write one passing integration test that verifies the schema + auth stack works end to end.

**Why now:** Every feature built after this point must have an integration test. Establishing the harness before the first feature forces good habits.

### Step 7 — Project conventions
Document in the repo (not just in the vault):
- Folder structure
- TypeScript coding standards
- Python/embedding worker conventions
- Naming conventions for DB objects
- Branch naming (feature/F..., fix/FB...)
- How to write a new API route (referencing error + pagination standards)

**Why now:** Conventions established before code is written are far cheaper to enforce than conventions imposed after patterns have drifted.

---

## Exit Criteria

All of the following must be true before Phase 1 begins:

- [ ] PG18 + pgvector + Apache AGE running locally and in CI
- [ ] Core tenant/scope schema migrated and tested
- [ ] Auth layer: JWT issues, validates, RBAC enforces
- [ ] Fastify skeleton: `/health` returns 200, all other routes require auth
- [ ] Error envelope and pagination standard verified by at least one integration test
- [ ] Audit log table exists and the write path is callable
- [ ] Testcontainers harness: at least one integration test passes in CI
- [ ] Project conventions documented and agreed

---

## Key Risks

| Risk | Mitigation |
|------|------------|
| Apache AGE + pgvector extension conflicts on PG18 | Test extension coexistence in step 1 before building anything else |
| Scope chain schema harder to change later | Design C2-2 carefully; enforce with DB constraints, not just application code |
| Auth patterns drifting if not locked in early | Establish auth as a plugin, not per-route logic; review in first PR |
| Convention drift if documented but not enforced | Wire lint and format checks into CI at step 6 |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/plan-of-attack-phase0.md
