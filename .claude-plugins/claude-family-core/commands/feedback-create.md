---
description: Create a new feedback item for the current project
---

# Create Feedback

Create a new feedback item in the Claude PM system.

## Step 1: Gather Information

Prompt the user for:
- **Type**: bug, change, design, or question
- **Title**: Brief description (required)
- **Description**: Detailed explanation (required)
- **Related files**: Optional file paths or code references

## Step 2: Identify Project

Get the current project UUID. If not a registered project, ask if user wants to register it.

## Step 3: Insert Feedback

```sql
INSERT INTO claude_pm.project_feedback (
  project_id,
  feedback_type,
  title,
  description,
  status,
  created_at,
  reported_by
)
VALUES (
  '<project-uuid>'::uuid,
  '<type>',
  '<title>',
  '<description>',
  'new',
  NOW(),
  '<your-identity-name>'
)
RETURNING feedback_id::text, created_at;
```

## Step 4: Confirm

```
✅ Feedback Created

Type: 🐛 Bug (or appropriate emoji)
ID: [feedback_id]
Title: [title]

Use /feedback-check to see all open items.
```

## Type Reference

| Type | Emoji | Use When |
|------|-------|----------|
| bug | 🐛 | Something is broken |
| change | 🔄 | Feature modification request |
| design | 🎨 | UI/UX improvement |
| question | ❓ | Need clarification |
