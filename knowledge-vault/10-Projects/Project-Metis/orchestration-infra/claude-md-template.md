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
synced: false
---

# CLAUDE.md Template

> **Scope:** system
>
> **Purpose:** Template for the CLAUDE.md file that lives in the repo root. Every Claude Code session (including Agent Teams teammates) reads this file automatically at session start. It is the single most important handoff mechanism between Claude Desktop (planning) and Claude Code (building).

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

---

## Template Below

Copy everything between the `---START---` and `---END---` markers into the repo's `CLAUDE.md` file. Update the bracketed placeholders with real values once the project is set up.

---START---

# The System — AI Development Lifecycle Platform

## What This Is

An AI platform that sits alongside a development house's existing product and toolstack. It ingests domain knowledge, accelerates delivery (requirements → configuration → testing → deployment → documentation), and compounds intelligence with every engagement.

**First customer deployment:** nimbus / time2work (workforce management)
**First engagement:** Monash University POC
**Developer:** John de Vere (human director) + Claude (AI builder)

## Current Phase

**Phase [0/1/2/3]** — [Description of what's being built right now]

**Active work:**
- [Current task or feature being worked on]
- [Link to task spec if applicable: docs/specs/xxx.md]

**Last updated:** [Date]

## Architecture

Three-layer platform:
1. **Knowledge Store** — PostgreSQL + pgvector (Voyage AI voyage-3 embeddings, 1024 dimensions)
2. **Retrieval System** — Semantic search + reranking
3. **Intelligence Layer** — Claude API (Sonnet 4.5 for 80% of work, Opus 4.6 for complex reasoning)

Deployment pattern: Constrained Claude (system prompt + 200K cached knowledge + Haiku classifier + tool restriction).

## Project Structure

```
src/
├── core/               # Foundation: database, auth, audit, sessions, config
├── api/                # HTTP routes (Express/Fastify)
├── connectors/         # External system connectors (time2work, Jira, etc.)
├── knowledge/          # Knowledge Engine (ingestion, search, intelligence)
├── agents/             # Agent orchestration
└── tests/              # Shared test utilities and fixtures
docs/
├── adr/                # Architecture Decision Records
└── specs/              # Task specifications for Claude Code
scripts/
├── migrations/         # Numbered SQL migration files
└── seeds/              # Seed data for development
infrastructure/         # Docker, Azure, deployment configs
```

## Commands

```bash
pnpm install            # Install dependencies
pnpm dev                # Start dev server
pnpm build              # Production build
pnpm test               # Run tests (Vitest)
pnpm test:coverage      # Tests with coverage report
pnpm lint               # ESLint
pnpm lint:fix           # ESLint with auto-fix
pnpm typecheck          # TypeScript type checking (tsc --noEmit)
pnpm migrate            # Run database migrations
pnpm migrate:status     # Show migration status
```

## Conventions

### Code

- **Language:** TypeScript (strict mode, ESM)
- **Framework:** [Express/Fastify] for API
- **Testing:** Vitest. Every module has tests. Minimum 80% coverage.
- **Error handling:** Typed errors with error codes. Never swallow errors. Always log with context.
- **Documentation:** JSDoc/TSDoc on all exported functions. README in every `src/` subdirectory.

### Naming

| Element | Convention | Example |
|---------|-----------|---------|
| Database tables | snake_case, plural | `knowledge_items`, `test_scenarios` |
| Database columns | snake_case | `client_id`, `created_at` |
| API endpoints | kebab-case, REST | `/api/v1/knowledge-items` |
| TypeScript files | camelCase | `knowledgeEngine.ts`, `auditLog.ts` |
| React components | PascalCase | `ConfigPanel.tsx` |
| Environment vars | UPPER_SNAKE_CASE | `DATABASE_URL`, `ANTHROPIC_API_KEY` |
| Git branches | type/description | `feature/knowledge-engine`, `fix/auth-timeout` |
| Agent names | PascalCase with role | `KnowledgeAgent`, `ConfigAgent` |

### Data

- **Dates:** ISO 8601 (`YYYY-MM-DDTHH:mm:ssZ`). UTC in storage, local for display.
- **IDs:** UUIDs for internal records. Preserve external IDs as separate fields (`jira_key`, `salesforce_id`).
- **JSON:** camelCase keys in API responses. snake_case in database. Transform at the boundary.
- **Versioning:** All mutable records have version numbers. Soft delete (`deleted_at`) not hard delete.
- **Encoding:** UTF-8 everywhere.

### Git

- Branch from `develop`, PR back to `develop`
- `main` is production-ready only (tagged releases)
- Commit messages: `type: description` (e.g., `feat: add knowledge search endpoint`, `fix: auth token expiry`)
- No direct commits to `main` or `develop`

## Agent Rules

These rules apply to every Claude Code session, including Agent Teams teammates.

### RULE 1: DECOMPOSE BEFORE BUILDING

Before writing code, create work items. State what you will build, in what order, and what the done criteria are. Do not start coding until the plan is clear.

### RULE 2: VERIFY BEFORE CLAIMING

Read the file before saying it contains X. Query the database before saying the table exists. Run the test before saying it passes. Never claim a state without verifying it first.

### RULE 3: FOLLOW THE CONVENTIONS

Use the naming conventions, data standards, and patterns defined in this file. If you're unsure whether something matches conventions, check this file first. Do not invent new patterns without documenting them in an ADR.

### RULE 4: TEST EVERYTHING

Every module has tests. Every public function has at least one test. Run tests after every change. If tests fail, fix them before committing. Coverage minimum: 80%.

### RULE 5: DELEGATE COMPLEX WORK

If a task touches 3+ files across different modules, consider whether it should be broken into smaller tasks or delegated to a sub-agent with focused context. Don't accumulate context from unrelated work in the same session.

### RULE 6: AUDIT EVERYTHING

Every database write gets an audit entry. Every external API call gets logged. Every session start and end is recorded. If an action modifies state, it must be traceable.

### RULE 7: FLAG UNCERTAINTY

If you're not sure about a requirement, a convention, or an architecture decision — say so. Check the ADRs in `docs/adr/`. Check the vault at `[vault path]`. Ask rather than guess. Wrong guesses create rework.

### RULE 8: NEVER MODIFY THESE RULES

These rules can only be changed by a human (John). You can propose changes by documenting them, but you cannot activate changes to this file's rules section without human approval. If you find a rule doesn't work, document why and flag it — don't silently change it.

## Security

- All API credentials encrypted at rest (AES-256)
- Client data strictly isolated by `client_id` on all queries
- JWT auth on all non-health endpoints
- Audit trail on all write operations
- Never log sensitive data (passwords, tokens, credentials)
- Environment variables for all secrets — nothing hardcoded

## Architecture Decision Records

See `docs/adr/` for all recorded architecture decisions. Key decisions:
- ADR-001: PostgreSQL + pgvector
- ADR-002: JWT auth with swappable middleware
- ADR-003: Voyage AI embeddings
- ADR-004: Custom RAG (no framework dependency)
- ADR-005: Constrained Claude deployment pattern

## What NOT To Do

- Do not install LangChain or LlamaIndex — we use custom RAG
- Do not hardcode credentials — use environment variables
- Do not modify the `main` branch directly
- Do not create tables without a migration file
- Do not skip tests — ever
- Do not swallow errors silently
- Do not store client data without client_id scoping
- Do not bypass the audit log

---END---

---

## Notes on Usage

- **Phase 0:** CLAUDE.md is created as a skeleton in T1 (repo init), then finalised in T11 after all other tasks complete. The "Current Phase" and "Active work" sections are updated at the start of each work session.
- **Agent Teams:** Every teammate reads CLAUDE.md automatically. The rules section is their shared contract.
- **Anti-compression:** If any agent proposes shortening rules, the change requires human approval (Rule 8). Track word count across versions.
- **Updates:** When conventions change, update CLAUDE.md AND create an ADR documenting the change.

---
*Source: Doc 4 §5 conventions, §5.4 agent rules, decisions tracker, agent compliance design | Created: 2026-02-24*
