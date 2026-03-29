---
name: work-item-routing
description: Route work items to correct tables (feedback, features, build_tasks)
model: haiku
agent: python-coder-haiku
allowed-tools:
  - Read
  - mcp__postgres__*
hooks:
  PreToolUse:
    - matcher: mcp__postgres__execute_sql
      description: Validate work item SQL against Data Gateway rules
skill-inheritance:
  - database-operations
---

# Work Item Routing Skill

**Status**: Active

---

## Overview

Route work items to the correct tables: feedback, features, or build_tasks.

**Detailed reference**: See [reference.md](./reference.md) for SQL examples and detailed field descriptions.

---

## When to Use

- User reports a bug or issue
- User requests a new feature
- Planning feature implementation
- Breaking down features into tasks
- Managing work backlog

---

## Work Item Hierarchy

```
claude.feedback          (Ideas, bugs, questions, changes)
    ->
claude.features         (Planned features linked to feedback)
    ->
claude.build_tasks      (Implementation tasks for features)
```

---

## Routing Decision Table

| User Says | Table | Type |
|-----------|-------|------|
| "This is broken" / "Error when..." | `feedback` | `feedback_type='bug'` |
| "I think we should..." / "What if..." | `feedback` | `feedback_type='idea'` |
| "How do I..." / "Why does..." | `feedback` | `feedback_type='question'` |
| "Please change..." / "Can you update..." | `feedback` | `feedback_type='change'` |
| "Let's build..." (after discussion) | `features` | Links to feedback |
| "Implement X" (specific task) | `build_tasks` | Links to feature |

---

## MCP Tools (Preferred Over Raw SQL)

| Tool | Purpose |
|------|---------|
| `create_feedback(project, type, description)` | Create feedback item |
| `create_feature(project, name, description)` | Create feature |
| `create_linked_task(feature_code, name, desc, verification, files)` | Add task to feature (quality enforced) |
| `add_build_task(feature_id, name)` | Quick/informal task |
| `advance_status(type, id, status)` | Change status |
| `promote_feedback(feedback_id)` | Feedback -> Feature |

---

## Status Values

| Table | Valid Statuses |
|-------|---------------|
| `feedback` | new, in_progress, resolved, wont_fix, duplicate |
| `features` | draft, planned, in_progress, completed, cancelled |
| `build_tasks` | todo, in_progress, completed, blocked, cancelled |

**Always check**: `column_registry` before writing. Priority: 1=critical, 5=low.

---

## Commands

| Command | Purpose |
|---------|---------|
| `/feedback-create` | Create new feedback item |
| `/feedback-list` | List and filter feedback |
| `/feedback-check` | Show open feedback for project |

---

## Related Skills

- `database-operations` - Data Gateway pattern
- `session-management` - Session-scoped tasks
- `project-ops` - Project initialization

---

## Key Gotchas

1. **UUID array casting** — use `ARRAY[...]::uuid[]` (PostgreSQL won't auto-cast)
2. **Wrong table choice** — feedback first, then features if implementing
3. **Not checking valid values** — always query `column_registry`
4. **Priority confusion** — 1=critical, 5=low (not the other way)

---

**Version**: 2.0 (Progressive disclosure: split to SKILL.md overview + reference.md detail)
**Created**: 2025-12-26
**Updated**: 2026-03-29
**Location**: .claude/skills/work-item-routing/SKILL.md
