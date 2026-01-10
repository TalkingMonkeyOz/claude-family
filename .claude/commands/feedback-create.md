# Create New Feedback

Create a new feedback item (bug, design, question, change, idea) for the current project.

---

## Step 1: Get Project Info

```sql
-- Get project_id from current project
SELECT project_id, project_name
FROM claude.workspaces
WHERE project_name = '{project_name}';
```

---

## Step 2: Use AskUserQuestion Tool

Ask user for:

**Question 1: Feedback Type**
- bug - Something broken or not working
- design - UI/UX issue or design question
- question - Need clarification or information
- change - Feature request or enhancement
- idea - Suggestion for future consideration

**Question 2: Description**
Prompt for detailed description.

**Question 3: Priority (1-5)**
- 1 = Critical (blocking work)
- 2 = High (important)
- 3 = Medium (normal)
- 4 = Low (minor)
- 5 = Very Low (nice to have)

---

## Step 3: Validate Feedback Type

```sql
-- Check valid feedback types
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'feedback' AND column_name = 'feedback_type';
-- Returns: bug, design, question, change, idea
```

---

## Step 4: Create Feedback

```sql
INSERT INTO claude.feedback (
    feedback_id,
    project_id,
    feedback_type,
    description,
    status,
    priority,
    created_at
)
VALUES (
    gen_random_uuid(),
    '{project_id}'::uuid,
    '{feedback_type}',
    '{description}',
    'new',
    '{priority}',  -- critical, high, medium, low, very_low
    NOW()
)
RETURNING feedback_id, created_at;
```

---

## Step 5: Confirm Creation

```
Feedback Created!

Type: {feedback_type}
ID: {feedback_id}
Priority: {priority}
Description: {description}

Next Steps:
- View all feedback: /feedback-check
- Add comment: /feedback-list
```

---

## Priority Mapping

| Input | Value |
|-------|-------|
| 1 | critical |
| 2 | high |
| 3 | medium |
| 4 | low |
| 5 | very_low |

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-01-10
**Location**: .claude/commands/feedback-create.md
