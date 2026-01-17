---
projects:
- claude-family
tags:
- pattern
- work-tracking
- features
- planning
synced: false
---

# Feature Planning System

Database-backed feature and task tracking that persists across sessions.

**Problem**: Plans created mid-session get lost. Next session, context is gone.

**Solution**: Store plans in DB, surface in session resume, enable RAG queries.

---

## How It Works

```
/feature-plan ──▶ features (DB) ──▶ build_tasks (DB)
                       │                  │
                       ▼                  ▼
                 Session Resume      /feature-next
                       │
                       ▼
                 RAG Embeddings
```

---

## Key Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `claude.features` | Feature plans | short_code, plan_data (jsonb), status |
| `claude.build_tasks` | Implementation steps | step_order, files_affected, blocked_by_task_id |

**New columns added**: `plan_data`, `step_order`, `files_affected`, `verification`

---

## Commands

| Command | Purpose |
|---------|---------|
| `/feature-plan {name}` | Create feature + tasks in DB |
| `/feature-status [F{n}]` | View progress (all or specific) |
| `/feature-next [F{n}]` | Get next unblocked task |
| `/feature-task BT{n} {action}` | Update task: start, done, block |

**Details**: See command files in `.claude/commands/feature-*.md`

---

## Ready Task Logic

A task is "ready" when:
- Status = `pending`
- No blocker, OR blocker is `completed`

```sql
SELECT * FROM claude.build_tasks
WHERE status = 'pending'
  AND (blocked_by_task_id IS NULL
       OR blocked_by_task_id IN (SELECT task_id WHERE status = 'completed'));
```

---

## Session Resume Integration

Session resume now shows active features and ready tasks:

```
ACTIVE FEATURES (2):
  [F12] Dark Mode Toggle    [▓▓▓▓▓▓░░░░] 3/5
  [F15] User Auth           [▓▓░░░░░░░░] 2/10

READY TASKS (2):
  [BT48] Wire toggle to navbar (F12)
  [BT55] Create login form (F15)
```

---

## RAG Integration

Embed features for semantic search:

```bash
python scripts/embed_features.py --all
```

Enables: "what was I working on?", "dark mode status"

---

## Git Integration

- **Branches**: `feature/F12-dark-mode`, `task/BT45-wire-toggle`
- **Commits**: `feat(F12): description [BT45]`

See [[Work Tracking Git Integration]] for hooks.

---

## vs File-Based Plans

| File-Based (sa-plan) | DB-Based (feature-plan) |
|---------------------|-------------------------|
| `plans/feature/plan.md` | `claude.features` + `build_tasks` |
| Not in session resume | Shows active features |
| Manual "what's next" | `/feature-next` query |
| No dependency tracking | `blocked_by_task_id` |

---

## Related

- [[Work Tracking Schema]] - Full schema docs
- [[Session Quick Reference]] - Session commands
- [[Structured Autonomy Workflow]] - Plan → Generate → Implement

---

**Version**: 1.0
**Created**: 2026-01-14
**Location**: knowledge-vault/30-Patterns/Feature Planning System.md
