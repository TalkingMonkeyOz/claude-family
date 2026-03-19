---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - scope/system
  - level/2
  - phase/0
projects:
  - Project-Metis
created: 2026-02-24
updated: 2026-02-24
synced: false
---

# Phase 0 Task List — Project Foundation

> **Scope:** system
>
> **Design Principles:**
> - Generic platform setup — no customer-specific content in Phase 0
> - Exit criteria: a second developer (human or AI) can clone, build, connect, and start working
> - Everything customer-specific comes in Phase 1+ when the first customer is onboarded

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

---

## What Phase 0 Produces

A working project skeleton with: source control, typed codebase, database connection, schema migration capability, authentication, session tracking, audit logging, CI pipeline, and documented conventions. Nothing user-visible. Nothing customer-specific.

**Exit criteria:** Can run agent teams, connect to database, push/pull code, all agents follow conventions, audit logging is active, CI is green.

---

## Prerequisites (Human — Before Claude Code Starts)

These require human credentials and access. Claude Code cannot do them.

| # | Task | Notes |
|---|------|-------|
| P1 | **LLM API account setup** | Create account, fund initial credits, set spend cap, create workspace |
| P2 | **Source control repo creation** | Private repo in org. Confirm developer push access. |
| P3 | **Database provisioned** | PostgreSQL with pgvector extension. Record connection string. Firewall rules. |
| P4 | **Hosting environment provisioned** | VM or container host. Linux. Connection details recorded. |
| P5 | **Environment variables documented** | `.env.template` with all required vars listed. `.env.local` with real values (never committed). |
| P6 | **Verify Claude Code access** | Confirm Claude Code can reach: repo, database, LLM API from dev machine |

---

## Phase 0 Tasks — Ordered

Tasks are sequential unless noted. Each has explicit done criteria.

### T1: Repository Initialisation

**What:** Project structure, gitignore, README, branch strategy, CLAUDE.md skeleton.

**Key decisions already made:**
- TypeScript (strict mode, ESM)
- pnpm package manager
- Git branches: `main` (production), `develop` (integration), `feature/*` and `fix/*` off develop
- Monorepo-ready structure

**Structure brainstorm:**
```
project-root/
├── CLAUDE.md              ← Agent conventions (loaded automatically)
├── README.md              ← Project overview
├── .env.template          ← Required environment variables
├── src/
│   ├── core/              ← Foundation: database, auth, audit, sessions, config
│   ├── api/               ← HTTP routes
│   ├── connectors/        ← External system connectors
│   ├── knowledge/         ← Knowledge Engine
│   ├── agents/            ← Agent orchestration
│   └── tests/             ← Shared test utilities
├── docs/
│   ├── adr/               ← Architecture Decision Records
│   └── specs/             ← Task specifications
├── scripts/
│   └── migrations/        ← Numbered SQL migration files
└── infrastructure/        ← Deployment configs
```

**Done when:** Repo has structure, branches, first commit pushed, CLAUDE.md skeleton present.

**Open questions:**
- Do we need a `packages/` or workspace structure from day one, or is a flat `src/` sufficient for Phase 0?
- Where do Playwright tests live — `src/tests/` or separate `e2e/` directory?

---

### T2: TypeScript & Tooling Setup

**What:** Dependencies, TypeScript config, linting, formatting, test runner.

**Key choices already made:**
- TypeScript strict mode with path aliases
- ESLint + Prettier
- Vitest for testing (TypeScript-native, ESM-compatible, fast)

**Done when:** `pnpm install`, `pnpm lint`, `pnpm test`, `pnpm build`, `pnpm dev` all work on an empty project.

**Gap:** No decision yet on API framework — Express (simpler, widely known) vs Fastify (faster, better TS support). Both are acceptable. Let Claude Code decide based on what it works best with.

---

### T3: Environment Configuration Module

**What:** Typed environment variable loading with validation. Fail fast if required vars are missing.

**Approach:** Zod schema validates all env vars at startup. Typed config singleton exported. Sensitive vars never logged.

**Done when:** Config loads, missing vars cause clear error, config is typed.

---

### T4: Database Connection & Migration Framework

**What:** Connection pool (with retry), SQL file-based migration runner, health check.

**Migration approach brainstorm:**
- Numbered SQL files (`001_description.sql`, `002_description.sql`)
- `_migrations` table tracks what's been applied
- Forward-only (no down migrations — simpler, forces thoughtful changes)
- Each migration should be idempotent (`IF NOT EXISTS` patterns)
- Checksum tracking to detect if applied migrations were modified
- Run manually in Phase 0. Automate in CI later.

**Open questions:**
- Do we need down migrations from the start, or is forward-only sufficient for Phase 0-2?
- Test database strategy: separate test DB? Transaction rollback? SQLite fallback for unit tests?

**Done when:** Can connect to PostgreSQL, pgvector confirmed, migration runner works, health check reports status.

---

### T5: Base Schema Deployment

**What:** Initial database schema via first migration file. Generic platform tables only — no customer-specific content.

**Tables brainstorm (system-level):**

| Table | Purpose | Notes |
|-------|---------|-------|
| `organisations` | Multi-tenant top level | Customer orgs |
| `users` | Platform users | Email, role, password hash, active flag |
| `user_org_access` | User ↔ org permissions | Role per org |
| `knowledge_items` | Domain knowledge with embeddings | Categories A-F, four-level scope, validation tiers |
| `sessions` | Agent session tracking | Parent/child for sub-agents, protocol version, interaction count |
| `work_items` | Task queue | Status state machine, priority, assignment |
| `audit_log` | Every action traced | Session, user, agent, action, target, detail |
| `protocol_versions` | Agent rule versioning | Full text stored verbatim, word count, compliance scores |
| `credentials` | Encrypted API credentials | Per-org, per-service, AES-256 |
| `documents` | Generated documentation | Per-org, versioned, format (md/html/json) |
| `_migrations` | Migration tracking | Filename, checksum, applied timestamp |

**What's NOT in Phase 0 schema:**
- Customer product-specific tables (config snapshots, test scenarios, etc.) — these come when the first customer is onboarded
- Compliance check tables — Phase 1+ when enforcement is active

**Open questions:**
- `clients` vs `engagements` vs `projects` as the sub-org level — needs alignment with the four-level scope hierarchy (Organisation → Product → Client → Engagement)
- Do we need all four scope levels as tables, or just Organisation + a generic `scope` JSONB?

> Lesson from Claude Family: Start with fewer tables than you think you need. Adding tables is easy. Removing them or merging them is painful. The Knowledge Engine deep dive defined the scope hierarchy — implement that, don't over-extend.

**Done when:** Migration runs, all tables created, pgvector working, indexes created.

---

### T6: Audit Logging Module

**What:** Structured logging for every platform action.

**Design:**
- Every database write MUST have an audit entry
- External API calls SHOULD be audited
- Session lifecycle MUST be audited
- Sensitive data NEVER in audit detail
- Fire-and-forget writes (don't block caller), failures logged to stderr
- Append-only (never update/delete audit entries)

**Done when:** Can write audit entries, convenience functions for common patterns, sensitive data filtering tested.

---

### T7: Authentication Module

**What:** JWT-based auth with role checking. Designed as swappable middleware.

**Roles (Phase 0 — simple RBAC as decided):**
- admin — everything
- developer — read/write knowledge, configs, tests. Cannot manage users.
- viewer — read-only
- client — read-only, scoped to their organisation only

**Key design principle:** Auth is ONE middleware file. Swapping to OAuth2/SSO later means replacing that file, not rewriting the app.

**Done when:** Register, login, JWT flow works. Role checks work. Org scoping works. Tests cover happy and unhappy paths.

---

### T8: Session Management Module

**What:** Database-backed session lifecycle for agent tracking.

> Lesson from Claude Family: Session management is the foundation. Without it, no audit trail, no crash recovery, no compliance measurement.

**Lifecycle:** start → work (update context, increment interactions) → end (status, timestamp)
- Parent/child sessions for sub-agent isolation
- Context JSONB for session state (equivalent of Claude Family's "session facts")
- Resume capability for crash recovery

**Done when:** Full lifecycle, nested sessions, resume, audit entries on start/end.

---

### T9: Basic API Server

**What:** HTTP server with health check, auth routes, foundational CRUD.

**Initial routes brainstorm:**
- `GET /health` — DB status, pgvector, migration count (no auth)
- `POST /auth/login` — returns JWT
- `GET /auth/me` — current user
- `GET /organisations` — list orgs (admin)
- `POST /organisations` — create org (admin)
- `GET /sessions` — list sessions

**Middleware stack:** Request logging → CORS → body parser → auth → error handler

**Error format:** Typed errors with codes. Never expose stack traces. Consistent JSON shape.

**Done when:** Server starts, health check works, login flow end-to-end, error handling consistent.

---

### T10: CI/CD Pipeline

**What:** Automated quality checks. See [[orchestration-infra/cicd-pipeline-spec]] for detail.

**Summary:** Five stages (install → lint → typecheck → test → build). Triggers on push and PR. Quality gates: zero errors, coverage threshold. Target: under 5 minutes.

**Done when:** Pipeline runs on push, all stages execute, failed stage blocks.

---

### T11: CLAUDE.md Finalisation

**What:** Update CLAUDE.md skeleton with real content now that the project exists.

**Done when:** A new Claude Code session can read CLAUDE.md and immediately understand the project. No stale content.

---

### T12: Architecture Decision Records

**What:** Record all resolved decisions as formal ADRs in `docs/adr/`.

Cover: data store choice, auth approach, embedding model, RAG framework, constrained deployment, branching strategy, language choice.

**Done when:** Every resolved architecture decision has an ADR. CLAUDE.md references ADR directory.

---

## Task Dependencies

```
Prerequisites (P1-P6, human)
    │
    T1: Repo init
    T2: Tooling ──────────┐
    T3: Config             │
    T4: DB connection ─────┤
    T5: Schema             │
    T6: Audit ─────────────┤
    T7: Auth               │
    T8: Sessions           │
    T9: API server ────────┘
    T10: CI/CD
    T11: CLAUDE.md final
    T12: ADRs
```

T1-T5 are roughly sequential. T6-T8 can be parallel once T5 is done. T9 depends on T6-T8. T10-T12 are cleanup/documentation after code tasks.

## Estimated Effort

3-5 days of Claude Code time (single-agent). Not calendar days — actual working time.

---

## Gaps / Open Questions

- [ ] API framework choice (Express vs Fastify) — let Claude Code decide?
- [ ] Test database strategy — separate DB, transaction rollback, or SQLite fallback?
- [ ] Scope hierarchy table design — all four levels as tables, or org + scope JSONB?
- [ ] Down migrations — needed from start or forward-only sufficient?
- [ ] Playwright test directory — with unit tests or separate?

---
*Source: Doc 4 §7 Phase 0, decisions tracker, session handoff 2026-02-24 | Created: 2026-02-24 | Rewritten to generic system level: 2026-02-24*
