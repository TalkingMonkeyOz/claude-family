# Check Open Feedback

Display open feedback items (bugs, design issues, questions, changes, ideas) for the current project.

---

## Step 1: Get Project Info

Use the current working directory basename as project_name.

---

## Step 2: Query Open Feedback

```sql
SELECT
    f.feedback_id::text,
    f.feedback_type,
    f.status,
    COALESCE(f.description, '') as description,
    f.created_at,
    COALESCE(f.priority, 'medium') as priority,
    (SELECT COUNT(*) FROM claude.feedback_comments c
     WHERE c.feedback_id = f.feedback_id) as comments
FROM claude.feedback f
JOIN claude.workspaces w ON f.project_id = w.project_id
WHERE w.project_name = '{project_name}'
  AND f.status IN ('new', 'in_progress')
ORDER BY
    CASE f.feedback_type
        WHEN 'bug' THEN 1
        WHEN 'design' THEN 2
        WHEN 'change' THEN 3
        WHEN 'question' THEN 4
        WHEN 'idea' THEN 5
    END,
    f.created_at ASC;
```

---

## Step 3: Display Summary

Format results:

```
OPEN FEEDBACK - {project_name}

Bugs (X)
  - [{id}] Description... (Priority: high, Comments: N)

Design (X)
  - [{id}] Description... (Priority: medium, Comments: N)

Changes (X)
  - [{id}] Description... (Priority: low, Comments: N)

Questions (X)
  - [{id}] Description... (Priority: medium, Comments: N)

Ideas (X)
  - [{id}] Description... (Priority: low, Comments: N)

Total Open: X items
```

---

## Quick Actions

```sql
-- View details
SELECT * FROM claude.feedback WHERE feedback_id = 'uuid'::uuid;

-- Add comment
INSERT INTO claude.feedback_comments (feedback_id, author, content)
VALUES ('uuid'::uuid, 'claude', 'comment');

-- Update status
UPDATE claude.feedback SET status = 'fixed', updated_at = NOW()
WHERE feedback_id = 'uuid'::uuid;
```

---

## No Feedback?

If no open feedback: "No open feedback items for this project."

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-01-10
**Location**: .claude/commands/feedback-check.md
