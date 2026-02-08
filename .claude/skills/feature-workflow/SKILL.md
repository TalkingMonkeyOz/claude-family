---
name: feature-workflow
description: Feature development lifecycle from idea to deployment
model: haiku
allowed-tools:
  - Read
  - Task
  - mcp__project-tools__*
  - mcp__postgres__*
---

# Feature Workflow Skill

**Status**: Active
**Last Updated**: 2026-02-08

---

## Overview

Complete feature development lifecycle using MCP tools (not raw SQL).

---

## Lifecycle

```
IDEA → FEEDBACK → FEATURE → BUILD TASKS → IMPLEMENT → REVIEW → DEPLOY
 FB{n}              F{n}      BT{n}...     Agents      reviewer
```

### Work Item Routing

| I have... | Create... | Tool |
|-----------|-----------|------|
| An idea | Feedback | `create_feedback(type='idea')` |
| A bug | Feedback | `create_feedback(type='bug')` |
| A feature to build | Feature | `create_feature()` |
| Tasks for a feature | Build Tasks | `add_build_task()` |
| Work right now | Todos | `TodoWrite` (session only) |

---

## Key MCP Tools

### Create Feedback
```
mcp__project-tools__create_feedback(
    project_path="current-project",
    feedback_type="idea",  -- idea, bug, design, question, change
    description="Description of the idea",
    priority=3
)
```

### Create Feature
```
mcp__project-tools__create_feature(
    project_path="current-project",
    feature_name="Dark Mode Support",
    description="Add theme toggle with light/dark modes",
    priority=2,
    plan_data={"requirements": [...], "approach": "...", "risks": [...]}
)
```

### Add Build Task
```
mcp__project-tools__add_build_task(
    feature_id="F93",  -- use short code
    task_name="Create ThemeContext provider",
    description="...",
    step_order=1,
    files_affected=["src/contexts/ThemeContext.tsx"]
)
```

### Get Ready Tasks
```
mcp__project-tools__get_ready_tasks(project_path="current-project")
```
Returns unblocked tasks ready to start.

### Update Status
```
mcp__project-tools__update_work_status(
    item_type="build_task",  -- feedback, feature, build_task
    item_id="BT305",
    new_status="completed"
)
```

---

## Status Values (from column_registry)

| Table | Valid Statuses |
|-------|---------------|
| feedback | new, in_progress, resolved, implemented, wont_fix, duplicate |
| features | planned, in_progress, completed, cancelled |
| build_tasks | **todo**, in_progress, blocked, completed, cancelled |

**Warning**: Build tasks use `todo` NOT `pending`.

---

## Priority Scale

| Priority | Meaning |
|----------|---------|
| 1 | Critical - immediate |
| 2 | High - this sprint |
| 3 | Medium - this quarter |
| 4 | Low - when time permits |
| 5 | Backlog - someday |

---

## Implementation Pattern

Once tasks are created, follow this cycle per task:

1. **Pick**: Get ready tasks, choose lowest step_order
2. **Start**: Update status to `in_progress`
3. **Implement**: Do the work (or delegate to agent)
4. **Review**: Spawn reviewer-sonnet before marking complete
5. **Complete**: Update status to `completed`
6. **Next**: Check if blocked tasks are now unblocked

### Agent Delegation

```
# Simple task: delegate to Haiku
Task(subagent_type="coder-haiku", prompt="Implement BT305: [description]")

# Complex task: delegate to Sonnet
Task(subagent_type="coder-sonnet", prompt="Implement BT306: [description]")

# Review: always before marking complete
Task(subagent_type="reviewer-sonnet", prompt="Review changes for BT305")
```

---

## Short Codes

| Prefix | Table | Example |
|--------|-------|---------|
| FB | feedback | FB45 |
| F | features | F93 |
| BT | build_tasks | BT305 |

Use in: commits (`feat(F93): Add theme [BT305]`), branches (`feature/F93-dark-mode`).

---

## Related

- `/ideate` - Guided ideation workflow (idea → feature → tasks)
- `code-review` skill - Pre-commit review
- `agentic-orchestration` skill - Agent delegation

---

**Version**: 2.0 (Rewritten to use MCP tools, corrected status values)
**Created**: 2025-12-26
**Updated**: 2026-02-08
**Location**: .claude/skills/feature-workflow/skill.md
