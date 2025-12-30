# Work Item Routing Skill

**Status**: Active
**Last Updated**: 2025-12-26

---

## Overview

This skill provides guidance for creating and routing work items to the correct tables: feedback, features, or build_tasks.

---

## When to Use

Invoke this skill when:
- User reports a bug or issue
- User requests a new feature
- Planning feature implementation
- Breaking down features into tasks
- Managing work backlog

---

## Quick Reference

### Work Item Hierarchy

```
claude.feedback          (Ideas, bugs, questions, changes)
    ↓
claude.features         (Planned features linked to feedback)
    ↓
claude.build_tasks      (Implementation tasks for features)
```

---

## Decision Tree

### I have...

| User Says | Table | Type |
|-----------|-------|------|
| "This is broken" / "Error when..." | `feedback` | `feedback_type='bug'` |
| "I think we should..." / "What if..." | `feedback` | `feedback_type='idea'` |
| "How do I..." / "Why does..." | `feedback` | `feedback_type='question'` |
| "Please change..." / "Can you update..." | `feedback` | `feedback_type='change'` |
| "Let's build..." (after discussion) | `features` | Links to feedback |
| "Implement X" (specific task) | `build_tasks` | Links to feature |

---

## Creating Feedback

Use the Data Gateway pattern:

```sql
-- 1. Check valid feedback types
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'feedback' AND column_name = 'feedback_type';
-- Result: ['bug', 'design', 'question', 'change']

-- 2. Check valid statuses
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'feedback' AND column_name = 'status';
-- Result: ['new', 'in_progress', 'resolved', 'wont_fix', 'duplicate']

-- 3. Insert feedback
INSERT INTO claude.feedback (
    project_id,
    feedback_type,
    title,
    description,
    priority,
    status,
    created_at
) VALUES (
    'project-uuid'::uuid,
    'bug',  -- From valid_values
    'Login fails with incorrect error message',
    'When credentials are wrong, shows "Server error" instead of "Invalid credentials"',
    2,  -- 1=critical, 5=low
    'new',
    NOW()
) RETURNING feedback_id;
```

### Using `/feedback-create` Command

```bash
/feedback-create type=bug priority=2 title="Login error message" description="..."
```

---

## Creating Features

Features represent planned work linked to feedback:

```sql
-- Link feature to feedback
INSERT INTO claude.features (
    feature_id,
    project_id,
    feature_name,
    description,
    status,
    priority,
    related_feedback_ids,  -- UUID array linking to feedback
    created_at
) VALUES (
    gen_random_uuid(),
    'project-uuid'::uuid,
    'Improve login error messages',
    'Show specific error messages for different failure modes',
    'planned',
    2,
    ARRAY['feedback-uuid']::uuid[],  -- Note: explicit cast required!
    NOW()
);
```

**Status values**: `planned`, `in_progress`, `completed`, `on_hold`, `cancelled`

---

## Creating Build Tasks

Tasks are implementation steps for features:

```sql
INSERT INTO claude.build_tasks (
    task_id,
    feature_id,
    task_name,
    description,
    assigned_to,
    status,
    priority,
    created_at
) VALUES (
    gen_random_uuid(),
    'feature-uuid'::uuid,
    'Update AuthService error mapping',
    'Map auth errors to user-friendly messages',
    'claude-code-unified',
    'pending',
    2,
    NOW()
);
```

**Status values**: `pending`, `in_progress`, `completed`, `blocked`

---

## Common Queries

```sql
-- Open feedback for project
SELECT
    feedback_id::text,
    feedback_type,
    title,
    priority,
    status,
    created_at
FROM claude.feedback
WHERE project_id = 'your-project-uuid'::uuid
  AND status IN ('new', 'in_progress')
ORDER BY priority ASC, created_at DESC;

-- Features with linked feedback
SELECT
    f.feature_name,
    f.status,
    f.priority,
    array_length(f.related_feedback_ids, 1) as feedback_count
FROM claude.features f
WHERE f.project_id = 'your-project-uuid'::uuid
  AND f.status != 'cancelled'
ORDER BY f.priority ASC;

-- Tasks for a feature
SELECT
    task_name,
    status,
    assigned_to,
    created_at
FROM claude.build_tasks
WHERE feature_id = 'your-feature-uuid'::uuid
ORDER BY created_at ASC;
```

---

## Commands Available

| Command | Purpose |
|---------|---------|
| `/feedback-create` | Create new feedback item |
| `/feedback-list` | List and filter feedback |
| `/feedback-check` | Show open feedback for current project |

---

## Related Skills

- `database-operations` - Data Gateway pattern
- `session-management` - Session-scoped tasks
- `project-ops` - Project initialization

---

## Key Gotchas

### 1. UUID Array Casting

**Problem**: PostgreSQL doesn't auto-cast text[] to uuid[]

```sql
-- WRONG
related_feedback_ids = ARRAY['uuid1', 'uuid2']

-- CORRECT
related_feedback_ids = ARRAY['uuid1', 'uuid2']::uuid[]
```

### 2. Wrong Table Choice

**Problem**: Creating features for bugs instead of feedback

**Solution**: Follow the hierarchy - feedback first, then features if planning to implement

### 3. Not Checking Valid Values

**Problem**: Using invalid status/type values, constraint violation

**Solution**: Always query `column_registry` before insert

### 4. Priority Confusion

**Problem**: Using high numbers for urgent (5 is LOW priority)

**Solution**: Remember 1=critical, 5=low priority

---

**Version**: 1.0
**Created**: 2025-12-26
**Location**: .claude/skills/work-item-routing/skill.md
