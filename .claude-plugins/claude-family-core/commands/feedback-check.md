---
description: Check open feedback items for the current project
---

# Feedback Check

Query open feedback items for the current project.

## Step 1: Identify Project

Determine the current project and its UUID from context or:

```sql
SELECT project_id, project_name FROM claude_pm.projects;
```

**Known Projects:**
- claude-pm: a3097e59-7799-4114-86a7-308702115905
- nimbus-user-loader: 07206097-4caf-423b-9eb8-541d4c25da6c
- ATO-Tax-Agent: 7858ecf4-4550-456d-9509-caea0339ec0d
- mission-control-web: 1ec10c78-df7a-4f5b-86c5-8c18b89aea30

## Step 2: Query Feedback

```sql
SELECT
  feedback_id::text,
  feedback_type,
  title,
  description,
  status,
  created_at,
  (SELECT COUNT(*) FROM claude_pm.feedback_comments fc WHERE fc.feedback_id = pf.feedback_id) as comments
FROM claude_pm.project_feedback pf
WHERE project_id = '<project-uuid>'::uuid
  AND status IN ('new', 'in_progress')
ORDER BY
  CASE feedback_type
    WHEN 'bug' THEN 1
    WHEN 'change' THEN 2
    WHEN 'design' THEN 3
    WHEN 'question' THEN 4
  END,
  created_at DESC;
```

## Output Format

Display with type emojis:
- 🐛 Bug
- 🔄 Change
- 🎨 Design
- ❓ Question

```
📋 Open Feedback for [Project Name]

🐛 BUG-001: [Title]
   Status: in_progress | Comments: 2
   [Description snippet...]

🔄 CHG-002: [Title]
   Status: new | Comments: 0
   [Description snippet...]

Total: X open items
```
