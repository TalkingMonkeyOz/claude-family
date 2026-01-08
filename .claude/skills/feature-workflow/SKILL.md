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

```sql
INSERT INTO claude.feedback (
    feedback_id, project_id, feedback_type, description, priority, status
) VALUES (
    gen_random_uuid(),
    'project-uuid-here',
    'idea',  -- or 'design', 'question', 'change'
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

```sql
INSERT INTO claude.build_tasks (
    task_id, feature_id, task_name, description, status
) VALUES 
    (gen_random_uuid(), 'feature-uuid', 'Create API endpoint', '...', 'pending'),
    (gen_random_uuid(), 'feature-uuid', 'Add database table', '...', 'pending'),
    (gen_random_uuid(), 'feature-uuid', 'Write unit tests', '...', 'pending');
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
- `pending` - Not started
- `in_progress` - Active work
- `completed` - Done
- `blocked` - Waiting on dependency

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

**Version**: 1.0
