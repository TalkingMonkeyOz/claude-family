---
name: feedback
description: "View, filter, create, and manage feedback items (bugs, ideas, changes, questions) for the current project"
user-invocable: true
disable-model-invocation: true
---

# Feedback Management

**Usage**: `/feedback [type] [status] [project]`

**Examples**:
- `/feedback` - Show all open feedback
- `/feedback bug` - Show open bugs only
- `/feedback idea in_progress` - Show in-progress ideas
- `/feedback bug new nimbus-user-loader` - Filter by type, status, and project

---

## View Feedback

### Step 1: Detect Current Project

Determine the project from the command argument or current working directory:

```bash
pwd
```

If a project argument is provided, use that. Otherwise map the directory to a project via `workspaces.json`.

Query the project_id:

```sql
SELECT project_id, project_code, project_name
FROM claude.projects
WHERE project_code ILIKE '%keyword%'
   OR project_name ILIKE '%keyword%'
LIMIT 1;
```

### Step 2: Parse Filter Arguments

| Argument | Valid Values | Default |
|----------|-------------|---------|
| type | bug, idea, change, question | all |
| status | new, triaged, in_progress, resolved | new, triaged, in_progress |
| project | project code or name | current project |

### Step 3: Query Feedback

```sql
SELECT
    f.feedback_id::text,
    f.feedback_type,
    f.status,
    f.description,
    f.created_at,
    f.updated_at
FROM claude.feedback f
JOIN claude.projects p ON f.project_id = p.project_id
WHERE p.project_id = 'PROJECT-ID'::uuid
  AND f.status IN ('new', 'triaged', 'in_progress')
ORDER BY
    CASE f.feedback_type
        WHEN 'bug' THEN 1
        WHEN 'change' THEN 2
        WHEN 'idea' THEN 3
        WHEN 'question' THEN 4
        ELSE 5
    END,
    f.created_at ASC;
```

Add filters to WHERE clause as needed:
- Type filter: `AND f.feedback_type = 'bug'`
- Status filter: `AND f.status = 'resolved'`
- Keyword: `AND f.description ILIKE '%search-keyword%'`

### Step 4: Get Summary Stats

```sql
SELECT
    feedback_type,
    status,
    COUNT(*) as count
FROM claude.feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('new', 'triaged', 'in_progress')
GROUP BY feedback_type, status
ORDER BY feedback_type, status;
```

### Step 5: Display Results

```
FEEDBACK - [Project Name]
Filters: [Type: all] [Status: open] [Search: none]

Open Items Summary:
  Bug:      X (new: N, in_progress: N)
  Change:   X
  Idea:     X
  Question: X
  Total:    X open items

--- BUGS ---
  [FB1] Description... (new, created: 2026-01-15)

--- IDEAS ---
  [FB4] Description... (new, created: 2026-01-08)
```

---

## Create Feedback

### Interactive Creation

1. Detect current project from working directory
2. Ask user for feedback type: bug, design, question, change, idea
3. Ask for description (detailed)
4. Use `mcp__project-tools__create_feedback` with project, type, description, priority
5. Confirm creation with short_code

---

## Advanced Queries

**Aging report (longest open items):**

```sql
SELECT
    feedback_id::text,
    feedback_type,
    status,
    description,
    created_at,
    EXTRACT(DAY FROM (NOW() - created_at)) as days_open
FROM claude.feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('new', 'triaged', 'in_progress')
ORDER BY days_open DESC;
```

**Most discussed (by linked build tasks):**

```sql
SELECT
    f.feedback_id::text,
    f.feedback_type,
    f.description,
    COUNT(bt.task_id) as linked_tasks
FROM claude.feedback f
LEFT JOIN claude.build_tasks bt ON bt.feedback_id = f.feedback_id
WHERE f.project_id = 'PROJECT-ID'::uuid
GROUP BY f.feedback_id, f.feedback_type, f.description
ORDER BY linked_tasks DESC
LIMIT 10;
```

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/feedback/SKILL.md
