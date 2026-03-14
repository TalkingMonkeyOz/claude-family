---
projects:
  - Project-Metis
tags:
  - session-handoff
created: 2026-03-14
status: active
supersedes: 2026-03-14-context-hygiene-handoff.md
---

# Session Handoff — 2026-03-14 — Gate 2 Decisions Progress

## Session Starter

```
Read this handoff: C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\session-handoffs\2026-03-14-gate2-decisions-progress.md

Then: start_session(project="project-metis") and recall_memories(query="METIS Gate 2 decisions tech stack data model", budget=1000, project_name="project-metis").

Invoke /skill-load-design-session to load the interactive design protocol.

Resume at: Cluster 2, Decision 4 (workflow_instances schema).
```

---

## What Was Done

1. **Killed "send brief to CF" action item** — Claude Code handles all design work now, not Claude Family Desktop
2. **Created /skill-load-design-session skill** — interactive design session protocol for Project METIS
3. **Worked through 7 design decisions** across 2 clusters

## Decisions Made (All Confirmed)

### Cluster 1: Tech Stack (COMPLETE)
| # | Decision | Choice |
|---|----------|--------|
| 1 | API Framework | Fastify (TypeScript-first, built-in schema validation, plugin DI) |
| 2 | Frontend | React + Vite + MUI (consistent with existing MUI ecosystem, no SSR needed) |
| 3 | PostgreSQL Version | PG18 minimum (pgvector 0.8.2+ required, all cloud providers support it) |
| 4 | Test Database Strategy | Testcontainers (real PG18+pgvector Docker per test run, dev/CI only) |

### Cluster 2: Data Model (3/5 done)
| # | Decision | Choice |
|---|----------|--------|
| 1 | Core Tenant Schemas | Hybrid columns: dedicated for queried fields + JSONB settings for config |
| 2 | Scope Tag Structure | Inheritance chain: full path always populated for single-query retrieval |
| 3 | Activity Space Entity | Activities table + separate activity_access_log table for co-access signal |

## What's Next (Resume Here)

### Cluster 2 remaining (2 decisions):
- **Decision 4:** `workflow_instances` schema
- **Decision 5:** Data retention policies per customer

### Clusters 3-6 (16 decisions):
- Cluster 3: Architecture (Context Assembly Orchestrator, multi-product pipeline, products without APIs)
- Cluster 4: API & Interface (error schemas, pagination, MCP tools, LLM abstraction)
- Cluster 5: Security & Deployment (credential delegation, data residency, deployment model, DPA)
- Cluster 6: Operations (monitoring tools, token budgets, SLOs, log retention)

---

## Key Context

- **"Send brief to CF" is DEAD** — do not carry forward
- All decisions stored via `remember()` with memory_type="decision"
- Design session skill at `.claude/commands/skill-load-design-session.md`
- Follow one-topic-at-a-time brainstorm pattern from the skill

---
**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/Project-Metis/session-handoffs/2026-03-14-gate2-decisions-progress.md
