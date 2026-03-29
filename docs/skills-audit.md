# Skills Audit Report

**Date**: 2026-03-29
**Auditor**: Claude Opus 4.6
**Scope**: All 33 skill directories in `.claude/skills/`

---

## Executive Summary

33 skills were audited. Key findings:

- **6 duplicate/near-duplicate pairs** consuming double the context
- **13 skills already hidden** (`disable-model-invocation: true`) -- good, these are user-only slash commands
- **4 skills that should be hidden** but are not (model loads them unnecessarily)
- **2 skills that could be deleted** (superseded or broken)
- **3 skills are massive context hogs** (messaging: 620 lines, session-management: 384 lines, wpf-ui: 1266 lines)
- **Total estimated context load**: ~5,500 lines from model-invocable skills alone

### Top Recommendations

1. **Hide `feature-workflow`** -- near-duplicate of `work-item-routing` plus covered by MCP tools
2. **Hide `database`** -- near-duplicate of `database-operations` (global skill)
3. **Hide `testing`** -- near-duplicate of `testing-patterns` (global skill)
4. **Hide `doc-lifecycle`** and `doc-keeper`** -- rarely needed, manual-invoke only
5. **Delete or merge `planner`** -- overlaps with both `sa-plan` and `coding-intelligence`
6. **Move `wpf-ui` and `react-expert` to global skills only** -- tech-specific, not needed in claude-family context
7. **Trim `messaging` (620 lines) and `session-management` (384 lines)** -- far too large, most content is examples

---

## Duplicate/Overlap Analysis

| Group | Skills | Issue | Recommendation |
|-------|--------|-------|----------------|
| Database patterns | `database` (project) + `database-operations` (global) | Same content, both model-invocable | Hide `database`, keep global `database-operations` |
| Testing patterns | `testing` (project) + `testing-patterns` (global) | Same content, both model-invocable | Hide `testing`, keep global `testing-patterns` |
| Work item routing | `work-item-routing` (project) + `feature-workflow` (project) | Both cover feedback/features/tasks lifecycle | Hide `feature-workflow`, keep `work-item-routing` |
| Planning | `planner` + `sa-plan` + `coding-intelligence` | Three different planning skills | Keep `coding-intelligence`, hide `planner`, keep `sa-plan` as user-only |
| Code review | `code-review` (project) + `code-review` (global) | Same name, same content | One is enough -- deduplicate in DB |
| Messaging | `messaging` (project) + `messaging` (global) | Same name, same content | One is enough -- deduplicate in DB |

---

## Full Skill Inventory

| # | Skill | Name (frontmatter) | Description | user-invocable | disable-model | model | Lines | Assessment |
|---|-------|-------------------|-------------|:-:|:-:|-------|------:|------------|
| 1 | coding-intelligence | coding-intelligence | Coding Intelligence -- Research/Plan/Implement using CKG | yes | -- | -- | 72 | **KEEP** -- core workflow skill, unique value |
| 2 | check-compliance | check-compliance | Run comprehensive compliance audit | yes | **true** | -- | 62 | KEEP (already hidden) -- user-only audit |
| 3 | agentic-orchestration | agentic-orchestration | Spawn and coordinate Claude agents | -- | -- | opus | 214 | **KEEP** -- essential for delegation |
| 4 | project-ops | project-ops | Project lifecycle operations | -- | -- | haiku | 340 | **KEEP but TRIM** -- 340 lines is too long, lots of SQL examples |
| 5 | code-review | code-review | Code review patterns and quality gates | -- | -- | sonnet | 169 | **KEEP** -- essential pre-commit skill |
| 6 | database | database-operations | PostgreSQL patterns and Data Gateway | -- | -- | haiku | 158 | **HIDE** -- duplicate of global `database-operations` |
| 7 | messaging | messaging | Inter-Claude messaging | -- | -- | sonnet | 620 | **KEEP but TRIM** -- 620 lines is extreme, cut examples to <200 |
| 8 | testing | testing-patterns | Testing patterns and requirements | -- | -- | haiku | 272 | **HIDE** -- duplicate of global `testing-patterns` |
| 9 | feature-workflow | feature-workflow | Feature development lifecycle | -- | -- | haiku | 259 | **HIDE** -- overlaps with `work-item-routing` |
| 10 | session-management | session-management | Session start/end workflows | -- | -- | haiku | 384 | **KEEP but TRIM** -- 384 lines, much is covered by hooks now |
| 11 | wpf-ui | wpf-ui | WPF UI Fluent Design applications | -- | -- | haiku | 1266 | **HIDE** -- massive (1266 lines!), tech-specific, not needed in claude-family |
| 12 | work-item-routing | work-item-routing | Route work items to correct tables | -- | -- | haiku | 270 | **KEEP** -- core routing skill |
| 13 | react-expert | react-expert | React 19.2 frontend engineering | -- | -- | sonnet | 143 | **HIDE** -- tech-specific, not needed in claude-family context |
| 14 | bpmn-modeling | bpmn-modeling | BPMN-first process design | -- | -- | -- | 202 | **KEEP** -- core infrastructure skill |
| 15 | feedback | feedback | View/filter/create feedback items | yes | **true** | -- | 168 | KEEP (already hidden) -- user-only slash command |
| 16 | ideate | ideate | Structured ideation pipeline | yes | **true** | -- | 102 | KEEP (already hidden) -- user-only slash command |
| 17 | knowledge-capture | knowledge-capture | Capture knowledge into memory or vault | yes | **true** | -- | 90 | KEEP (already hidden) -- user-only slash command |
| 18 | maintenance | maintenance | Run system maintenance health checks | yes | **true** | -- | 98 | KEEP (already hidden) -- user-only slash command |
| 19 | planner | planner | Generate structured implementation plans | -- | -- | sonnet | 123 | **HIDE** -- overlaps with `coding-intelligence` and `sa-plan` |
| 20 | phase-advance | phase-advance | Advance project to next phase | yes | **true** | -- | 103 | KEEP (already hidden) -- user-only slash command |
| 21 | retrofit-project | retrofit-project | Add governance docs to existing project | yes | **true** | -- | 64 | KEEP (already hidden) -- user-only slash command |
| 22 | review-data | review-data | Run data quality review | yes | **true** | -- | 48 | KEEP (already hidden) -- user-only slash command |
| 23 | review-docs | review-docs | Run documentation staleness review | yes | **true** | -- | 47 | KEEP (already hidden) -- user-only slash command |
| 24 | self-test | self-test | Automated Playwright app testing | yes | **true** | -- | 65 | KEEP (already hidden) -- user-only slash command |
| 25 | sa-plan | sa-plan | Structured Autonomy Phase 1 planning | yes | **true** | -- | 115 | KEEP (already hidden) -- user-only slash command |
| 26 | session-commit | session-commit | Session summary + git commit | yes | **true** | -- | 103 | KEEP (already hidden) -- user-only slash command |
| 27 | session-status | session-status | Quick read-only status check | yes | **true** | -- | 68 | KEEP (already hidden) -- user-only slash command |
| 28 | sql-optimization | sql-optimization | SQL performance tuning | -- | -- | haiku | 141 | **KEEP** -- useful for DB work, reasonable size |
| 29 | todo | todo | Manage persistent TODO items | yes | **true** | -- | 118 | KEEP (already hidden) -- user-only slash command |
| 30 | winforms | winforms | WinForms development patterns | -- | -- | haiku | 126 | **HIDE** -- tech-specific, not needed in claude-family |
| 31 | doc-lifecycle | doc-lifecycle | Feature documentation lifecycle | -- | -- | -- | 60 | **HIDE** -- niche, only needed for stream-tracked projects |
| 32 | session-save | session-save | Checkpoint session progress | yes | **true** | -- | 73 | KEEP (already hidden) -- user-only slash command |
| 33 | doc-keeper | doc-keeper | Documentation keeper | -- | -- | haiku | 104 | **HIDE** -- maintenance task, should be manual-invoke only |

---

## Context Impact Analysis

### Currently Model-Invocable Skills (loaded into context on match)

These 20 skills can be auto-loaded by the model, consuming context:

| Skill | Lines | Verdict |
|-------|------:|---------|
| agentic-orchestration | 214 | Keep |
| bpmn-modeling | 202 | Keep |
| code-review | 169 | Keep |
| coding-intelligence | 72 | Keep |
| **database** | **158** | **Hide (duplicate)** |
| doc-keeper | 104 | **Hide** |
| doc-lifecycle | 60 | **Hide** |
| **feature-workflow** | **259** | **Hide (duplicate)** |
| **messaging** | **620** | **Keep but trim to ~200** |
| **planner** | **123** | **Hide (duplicate)** |
| project-ops | 340 | Keep but trim |
| **react-expert** | **143** | **Hide (tech-specific)** |
| session-management | 384 | Keep but trim |
| sql-optimization | 141 | Keep |
| **testing** | **272** | **Hide (duplicate)** |
| **winforms** | **126** | **Hide (tech-specific)** |
| work-item-routing | 270 | Keep |
| **wpf-ui** | **1266** | **Hide (tech-specific, massive)** |

**Estimated savings from hiding 9 skills**: ~3,000+ lines of context freed

### Already Hidden Skills (13) -- No Action Needed

check-compliance, feedback, ideate, knowledge-capture, maintenance, phase-advance, retrofit-project, review-data, review-docs, self-test, sa-plan, session-commit, session-status, session-save, todo

---

## Recommended Actions

### Immediate (High Impact)

1. **Add `disable-model-invocation: true` to 9 skills**: database, testing, feature-workflow, planner, wpf-ui, winforms, react-expert, doc-lifecycle, doc-keeper
2. **Deduplicate in DB**: code-review and messaging each appear twice in the skill listing (project + global scope)
3. **Trim messaging skill**: Cut from 620 to ~200 lines (remove verbose SQL examples, redundant code blocks)
4. **Trim session-management skill**: Cut from 384 to ~150 lines (hooks handle most of this now)
5. **Trim project-ops skill**: Cut from 340 to ~150 lines (remove SQL examples covered by MCP tools)

### Medium Term

6. **Move tech-specific skills to per-project scope**: wpf-ui, winforms, react-expert should only load in their respective project contexts, not in claude-family
7. **Merge `feature-workflow` content into `work-item-routing`**: One skill for all work-item operations
8. **Consider deleting `planner`**: Its value is fully covered by `coding-intelligence` (medium workflow) and `sa-plan` (structured autonomy)

### Low Priority

9. **Add `user-invocable: true` to doc-keeper**: Make it a slash command for manual invocation
10. **Review all skills for stale tool references**: Some still reference patterns from pre-MCP era

---

## Skills by Category

### Essential (Keep in context) -- 8 skills
- coding-intelligence, agentic-orchestration, code-review, bpmn-modeling, session-management, work-item-routing, messaging, sql-optimization

### User-Only Slash Commands (Already hidden) -- 14 skills
- check-compliance, feedback, ideate, knowledge-capture, maintenance, phase-advance, retrofit-project, review-data, review-docs, self-test, sa-plan, session-commit, session-status, session-save, todo

### Should Be Hidden (Currently polluting context) -- 9 skills
- database, testing, feature-workflow, planner, wpf-ui, winforms, react-expert, doc-lifecycle, doc-keeper

### Needs Trimming (Keep but reduce size) -- 3 skills
- messaging (620 -> ~200), session-management (384 -> ~150), project-ops (340 -> ~150)

---

**Version**: 1.0
**Created**: 2026-03-29
**Updated**: 2026-03-29
**Location**: docs/skills-audit.md
