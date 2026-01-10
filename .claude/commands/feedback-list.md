# List and Filter Feedback

Display feedback items with optional filters for status, type, and search.

---

## Step 1: Get Project Info

Use the current working directory basename as project_name.

---

## Step 2: Ask for Filters (Optional)

Use AskUserQuestion for filter options:

**Status**: All / New / In Progress / Fixed / Won't Fix
**Type**: All / Bug / Design / Question / Change / Idea
**Search**: Keywords (optional)
**Timeframe**: All / Last 7 days / Last 30 days

---

## Step 3: Query Feedback

**Default Query (All Open):**
```sql
SELECT
    f.feedback_id::text,
    f.feedback_type,
    f.status,
    COALESCE(f.description, '') as description,
    COALESCE(f.priority, 'medium') as priority,
    f.created_at,
    f.updated_at,
    (SELECT COUNT(*) FROM claude.feedback_comments c
     WHERE c.feedback_id = f.feedback_id) as comments
FROM claude.feedback f
JOIN claude.workspaces w ON f.project_id = w.project_id
WHERE w.project_name = '{project_name}'
  AND f.status IN ('new', 'in_progress')
ORDER BY f.created_at DESC;
```

**With Type Filter:**
```sql
AND f.feedback_type = 'bug'  -- bug, design, question, change, idea
```

**With Status Filter:**
```sql
AND f.status = 'fixed'  -- new, in_progress, fixed, wont_fix
```

**With Search:**
```sql
AND f.description ILIKE '%keyword%'
```

**With Timeframe:**
```sql
AND f.created_at > NOW() - INTERVAL '7 days'
```

---

## Step 4: Display Results

```
FEEDBACK LIST - {project_name}

Filters: Status: {status} | Type: {type} | Search: {search}

Total: X items

| ID       | Type   | Status  | Priority | Created    | Comments |
|----------|--------|---------|----------|------------|----------|
| a1b2c3d4 | Bug    | New     | high     | 2026-01-10 | 2        |
| b2c3d4e5 | Design | Progress| medium   | 2026-01-09 | 5        |

---
View details: SELECT * FROM claude.feedback WHERE feedback_id = 'uuid'::uuid
View comments: SELECT * FROM claude.feedback_comments WHERE feedback_id = 'uuid'::uuid
```

---

## Statistics Query

```sql
SELECT
    feedback_type,
    status,
    COUNT(*) as count
FROM claude.feedback f
JOIN claude.workspaces w ON f.project_id = w.project_id
WHERE w.project_name = '{project_name}'
GROUP BY feedback_type, status
ORDER BY feedback_type, status;
```

---

## Aging Report

```sql
SELECT
    feedback_id::text,
    feedback_type,
    status,
    EXTRACT(DAY FROM (NOW() - created_at)) as days_open
FROM claude.feedback f
JOIN claude.workspaces w ON f.project_id = w.project_id
WHERE w.project_name = '{project_name}'
  AND f.status IN ('new', 'in_progress')
ORDER BY days_open DESC;
```

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-01-10
**Location**: .claude/commands/feedback-list.md
