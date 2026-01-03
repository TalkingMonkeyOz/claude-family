# Work Tracking Compliance Plan

**Status**: Approved | **Created**: 2026-01-03

---

## Problem

Work tracking tables are **empty** (features: 0, feedback: 0, build_tasks: 0).
No FK constraints = orphaned records possible. No enforcement = not used.

**Why `todos` works**: Hook + FK + NOT NULL = 476 rows.

---

## Solution: Layered Compliance

| Layer | Purpose |
|-------|---------|
| **Database** | FK constraints prevent orphans |
| **Skills** | Easy creation via `/feature-create`, etc. |
| **Session hooks** | Soft prompts at session end |
| **Git hooks** | Link commits to work items |
| **UI** | claude-manager-mui visibility |

---

## Implementation Phases

| Phase | Scope | Docs |
|-------|-------|------|
| 1 | Database FK constraints | [[Work Tracking Schema]] |
| 2 | Skills & Data Gateway | [[Work Tracking Skills]] |
| 3 | Soft enforcement (session hooks) | [[Work Tracking Enforcement]] |
| 4 | Git integration | [[Work Tracking Git Integration]] |
| 5 | claude-manager-mui UI | [[claude-manager-mui Work Items]] |
| 6 | Hard enforcement (optional) | TBD after evaluation |

---

## Quick Reference

**Work Hierarchy:**
```
PROJECT → FEATURES → BUILD_TASKS
                  → REQUIREMENTS
        → FEEDBACK (parallel)
        → TODOS (ephemeral)
```

**Branch Convention:** `feature/F1-desc`, `fix/FB2-desc`, `task/BT3-desc`

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Features tracked | 0 | 50+ |
| Commits with work item | 0% | 80% |

---

## Next Steps

1. **Phase 1**: Run migration script (see [[Work Tracking Schema]])
2. **Phase 2**: Update skills
3. Start using work tracking in this project

---

**Version**: 1.0
**Location**: docs/WORK_TRACKING_COMPLIANCE_PLAN.md
