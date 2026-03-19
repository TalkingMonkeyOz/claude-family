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

# CI/CD Pipeline — Brainstorm

> **Scope:** system
>
> **Design Principles:**
> - Fast feedback — target under 5 minutes for a typical change
> - Fail fast — cheap checks (lint) before expensive ones (test)
> - Phase 0 is quality gates only — no automated deployment yet
> - Platform-agnostic design — same stages whether Azure DevOps, GitHub Actions, or something else

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

---

## What the Pipeline Does

Automated quality checks on every code change. Catches broken code before it reaches shared branches.

## Pipeline Stages (Ordered)

| Stage | What | Fails If |
|-------|------|----------|
| 1. Install | `pnpm install --frozen-lockfile` | Lockfile out of date |
| 2. Lint | ESLint | Any errors (warnings OK) |
| 3. Type Check | `tsc --noEmit` | Any TypeScript errors |
| 4. Test | Vitest with coverage | Any test fails, or coverage below threshold |
| 5. Build | Compile TypeScript | Build errors |

## Triggers

| Event | Runs Pipeline? |
|-------|---------------|
| Push to any branch | Yes |
| PR to `develop` or `main` | Yes + coverage report on PR |
| Tag creation | No (no deployment automation in Phase 0) |
| Schedule/nightly | No (add when test suite is large enough) |

## Quality Gates

| Gate | Phase 0 | Phase 1+ Target |
|------|---------|-----------------|
| Lint errors | 0 | 0 |
| TypeScript errors | 0 | 0 |
| Test failures | 0 | 0 |
| Test coverage minimum | 60% | 80% |

## Platform

Decided: **Azure DevOps Pipelines** (repo is in Azure DevOps).

Fallback: GitHub Actions if Azure DevOps isn't ready. Same stages, different YAML. Migration is trivial.

## What's NOT in Phase 0

These are future additions, captured here so we don't forget:

| Addition | When | Why Wait |
|----------|------|----------|
| Automated deployment | Phase 2+ | Deployment is rare and manual in Phase 0 |
| Docker builds | Phase 2+ | Not using containers yet |
| Security scanning (`npm audit`) | Phase 1+ | Dependency count is small |
| Agent Review stage (Opus code review on PRs) | Phase 1+ | High value but high cost — budget needs confirming |
| Nightly regression runs | Phase 2+ | Test suite too small to warrant it |
| Performance/load testing | Phase 2+ | No endpoints under real load yet |

## Open Questions

- [ ] Test database in CI — does the pipeline need a real PostgreSQL, or can we mock/SQLite for CI tests?
- [ ] Pipeline minutes budget — Azure DevOps gives 1800 free minutes/month for private repos. Enough for Phase 0?
- [ ] PR merge policy — require pipeline pass + one reviewer (agent or human)?

---
*Source: Dev decisions (three-layer review), Doc 4 §5.2 code standards | Created: 2026-02-24 | Trimmed to brainstorm level: 2026-02-24*
