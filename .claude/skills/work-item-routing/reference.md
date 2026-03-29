# Work Item Routing Skill — Detailed Reference

## Creating Feedback — SQL Examples

Use the Data Gateway pattern:

```sql
-- 1. Check valid feedback types
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'feedback' AND column_name = 'feedback_type';
-- Result: ['bug', 'design', 'question', 'change', 'idea', 'improvement']

-- 2. Check valid statuses
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'feedback' AND column_name = 'status';
-- Result: ['new', 'in_progress', 'resolved', 'wont_fix', 'duplicate']

-- 3. Insert feedback
INSERT INTO claude.feedback (
    project_id, feedback_type, title, description, priority, status, created_at
) VALUES (
    'project-uuid'::uuid, 'bug',
    'Login fails with incorrect error message',
    'When credentials are wrong, shows "Server error" instead of "Invalid credentials"',
    2, 'new', NOW()
) RETURNING feedback_id;
```

---

## Creating Features — SQL Examples

```sql
INSERT INTO claude.features (
    feature_id, project_id, feature_name, description,
    status, priority, related_feedback_ids, created_at
) VALUES (
    gen_random_uuid(), 'project-uuid'::uuid,
    'Improve login error messages',
    'Show specific error messages for different failure modes',
    'planned', 2,
    ARRAY['feedback-uuid']::uuid[],  -- Note: explicit cast required!
    NOW()
);
```

**Status values**: `planned`, `in_progress`, `completed`, `cancelled`

---

## Creating Build Tasks — SQL Examples

```sql
INSERT INTO claude.build_tasks (
    task_id, feature_id, task_name, description,
    assigned_to, status, priority, created_at
) VALUES (
    gen_random_uuid(), 'feature-uuid'::uuid,
    'Update AuthService error mapping',
    'Map auth errors to user-friendly messages',
    'claude-code-unified',
    'todo',  -- Valid: todo, in_progress, blocked, completed, cancelled (NEVER 'pending')
    2, NOW()
);
```

**Status values**: `todo`, `in_progress`, `completed`, `blocked`, `cancelled`

---

## Common Queries

```sql
-- Open feedback for project
SELECT feedback_id::text, feedback_type, title, priority, status, created_at
FROM claude.feedback
WHERE project_id = 'your-project-uuid'::uuid
  AND status IN ('new', 'in_progress')
ORDER BY priority ASC, created_at DESC;

-- Features with linked feedback
SELECT f.feature_name, f.status, f.priority,
    array_length(f.related_feedback_ids, 1) as feedback_count
FROM claude.features f
WHERE f.project_id = 'your-project-uuid'::uuid
  AND f.status != 'cancelled'
ORDER BY f.priority ASC;

-- Tasks for a feature
SELECT task_name, status, assigned_to, created_at
FROM claude.build_tasks
WHERE feature_id = 'your-feature-uuid'::uuid
ORDER BY created_at ASC;
```

---

## Key Gotchas — Detailed

### 1. UUID Array Casting

```sql
-- WRONG
related_feedback_ids = ARRAY['uuid1', 'uuid2']
-- CORRECT
related_feedback_ids = ARRAY['uuid1', 'uuid2']::uuid[]
```

### 2. Wrong Table Choice

Follow the hierarchy: feedback first, then features if planning to implement.

### 3. Not Checking Valid Values

Always query `column_registry` before insert to avoid constraint violations.

### 4. Priority Confusion

1=critical, 5=low priority (not the other way around).
