# Feedback: View and Filter Feedback Items

Display feedback items for the current project with optional filters. Replaces `/feedback-check` and `/feedback-list`.

**Usage**: `/feedback [type] [status] [project]`

**Examples**:
- `/feedback` - Show all open feedback
- `/feedback bug` - Show open bugs only
- `/feedback idea in_progress` - Show in-progress ideas
- `/feedback bug new nimbus-user-loader` - Filter by type, status, and project

---

## Step 1: Detect Current Project

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

---

## Step 2: Parse Filter Arguments

Extract optional filters from the command arguments:

| Argument | Valid Values | Default |
|----------|-------------|---------|
| type | bug, idea, change, question | all |
| status | new, triaged, in_progress, resolved | new, triaged, in_progress |
| project | project code or name | current project |

---

## Step 3: Query Feedback

Build and execute the query based on filters:

**Default (all open feedback):**

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

**With type filter** — add to WHERE clause:
```sql
AND f.feedback_type = 'bug'  -- or 'idea', 'question', 'change'
```

**With status filter** — replace status list:
```sql
AND f.status = 'resolved'  -- or 'new', 'triaged', 'in_progress'
```

**With keyword search** — add to WHERE clause:
```sql
AND f.description ILIKE '%search-keyword%'
```

---

## Step 4: Get Summary Stats

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

---

## Step 5: Display Results

Format the output:

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
  [FB2] Description... (in_progress, created: 2026-01-10)

--- CHANGES ---
  [FB3] Description... (triaged, created: 2026-01-12)

--- IDEAS ---
  [FB4] Description... (new, created: 2026-01-08)

---
View item: SELECT * FROM claude.feedback WHERE feedback_id = 'id'::uuid
Create new: /feedback-create
```

**If no results:**
```
No feedback items match your filters.
- Broaden status filter (include resolved items)
- Remove type filter
- Check project name
```

---

## Step 6: Offer Actions

After displaying results, present options:

```
Next actions:
1. View details of a specific item (provide ID)
2. Create new feedback: /feedback-create
3. Show recently resolved (last 7 days)
```

**Recently resolved query (if requested):**

```sql
SELECT
    feedback_id::text,
    feedback_type,
    description,
    updated_at as resolved_at
FROM claude.feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status = 'resolved'
  AND updated_at > NOW() - INTERVAL '7 days'
ORDER BY updated_at DESC
LIMIT 10;
```

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

## Error Handling

**Project not found:**
- Check `workspaces.json` for correct project mapping
- Query `SELECT project_code, project_name FROM claude.projects ORDER BY project_name`

**No open feedback:**
- Display: "No open feedback items for this project."

**Database connection fails:**
- Check postgres MCP configuration
- Test: `SELECT 1;`

---

**Version**: 1.0
**Created**: 2026-02-28
**Updated**: 2026-02-28
**Location**: .claude/commands/feedback.md
