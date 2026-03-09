---
name: feature-workflow
description: Feature development lifecycle from idea to deployment
model: haiku
allowed-tools:
  - Read
  - mcp__postgres__*
---

# Feature Workflow Skill

**Status**: Active
**Last Updated**: 2026-01-08

---

## Overview

This skill guides the complete feature development lifecycle from idea to deployment.

---

## Quick Reference

### Work Item Routing

| I have... | Put it in... | Table |
|-----------|--------------|-------|
| An idea | Feedback | `claude.feedback` (type='idea') |
| A bug | Feedback | `claude.feedback` (type='bug') |
| A question | Feedback | `claude.feedback` (type='question') |
| A feature to build | Features | `claude.features` |
| A task to do | Build Tasks | `claude.build_tasks` |
| Work right now | TodoWrite | Session only |

---

## Feature Lifecycle

```
IDEA → FEEDBACK → FEATURE → TASKS → IMPLEMENTATION → REVIEW → DEPLOY
```

### 1. Capture Idea

**Preferred**: Use the MCP tool to bypass raw SQL and let WorkflowEngine handle state:

```python
mcp__project-tools__create_feedback(
    project_id="project-uuid-here",
    feedback_type="idea",  # Valid: bug, design, question, change, idea, improvement
    description="Description of the idea",
    priority=3  # 1=critical, 5=backlog
)
```

**Alternative** (raw SQL — use only when MCP unavailable):

```sql
INSERT INTO claude.feedback (
    feedback_id, project_id, feedback_type, description, priority, status
) VALUES (
    gen_random_uuid(),
    'project-uuid-here',
    'idea',  -- Valid: bug, design, question, change, idea, improvement
    'Description of the idea',
    3,  -- 1=critical, 5=backlog
    'new'
);
```

### 2. Promote to Feature

When an idea is approved for implementation:

```sql
-- Create feature
INSERT INTO claude.features (
    feature_id, project_id, feature_name, description, priority, status
) VALUES (
    gen_random_uuid(),
    'project-uuid-here',
    'Feature Name',
    'Detailed description',
    2,
    'planned'
);

-- Link and close feedback
UPDATE claude.feedback 
SET status = 'implemented', 
    resolved_at = NOW()
WHERE feedback_id = 'feedback-uuid';
```

### 3. Break Into Tasks

**Preferred**: Use the MCP tool to route through WorkflowEngine:

```python
mcp__project-tools__create_linked_task(
    feature_code="F1",  # Feature short code
    name="Create API endpoint",
    description="...",
    verification="...",
    files=[]
)
```

**Alternative** (raw SQL — valid `status` values: `todo`, `in_progress`, `blocked`, `completed`, `cancelled`):

```sql
INSERT INTO claude.build_tasks (
    task_id, feature_id, task_name, description, status
) VALUES
    (gen_random_uuid(), 'feature-uuid', 'Create API endpoint', '...', 'todo'),
    (gen_random_uuid(), 'feature-uuid', 'Add database table', '...', 'todo'),
    (gen_random_uuid(), 'feature-uuid', 'Write unit tests', '...', 'todo');
```

### 4. Track Progress

Use TodoWrite for session-level tracking:

```json
[
  {"content": "Create API endpoint", "status": "in_progress", "activeForm": "Creating API endpoint..."},
  {"content": "Add database table", "status": "pending", "activeForm": "Adding database table..."},
  {"content": "Write unit tests", "status": "pending", "activeForm": "Writing unit tests..."}
]
```

---

## Status Values

### Feedback Status
- `new` - Just created
- `in_progress` - Being worked on
- `fixed` - Issue resolved
- `wont_fix` - Won't be addressed

### Feature Status
- `planned` - Approved for development
- `in_progress` - Under active development
- `completed` - Fully implemented
- `cancelled` - Not going forward

### Task Status
- `todo` - Not started (NOT `pending` — constraint violation)
- `in_progress` - Active work
- `completed` - Done
- `blocked` - Waiting on dependency
- `cancelled` - Will not be implemented

---

## Priority Scale

| Priority | Meaning | SLA |
|----------|---------|-----|
| 1 | Critical | Immediate |
| 2 | High | This sprint |
| 3 | Medium | This quarter |
| 4 | Low | When time permits |
| 5 | Backlog | Maybe someday |

---

## Common Queries

```sql
-- Open features for a project
SELECT feature_name, status, priority 
FROM claude.features 
WHERE project_id = 'project-uuid' AND status != 'completed'
ORDER BY priority;

-- Tasks for a feature
SELECT task_name, status 
FROM claude.build_tasks 
WHERE feature_id = 'feature-uuid'
ORDER BY created_at;

-- All open work items
SELECT 'feedback' as source, description, priority 
FROM claude.feedback WHERE status IN ('new', 'in_progress')
UNION ALL
SELECT 'feature', feature_name, priority 
FROM claude.features WHERE status IN ('planned', 'in_progress')
ORDER BY priority;
```

---

## Key Patterns

### 1. Auto-TodoWrite for Workflows

When process-guidance is injected, immediately add todos:

```json
[
  {"content": "[PROC-ID] Step 1", "status": "pending", "activeForm": "Doing step 1..."},
  {"content": "[PROC-ID] Step 2", "status": "pending", "activeForm": "Doing step 2..."}
]
```

### 2. Feature Documentation

Create docs alongside features:

```markdown
# Feature: {Feature Name}

## Problem
What problem does this solve?

## Solution
How does it solve it?

## Implementation
- Step 1
- Step 2

## Testing
How to verify it works?
```

---

## Related Skills

- `database-operations` - Data storage patterns
- `testing-patterns` - Test before deploy
- `code-review` - Review process

---

**Version**: 1.1 (Fix invalid status 'pending'→'todo', add MCP tool alternatives, clarify valid feedback_type values)
**Created**: 2026-01-08
**Updated**: 2026-03-09
**Location**: .claude/skills/feature-workflow/skill.md
