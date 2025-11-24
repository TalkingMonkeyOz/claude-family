# Check Open Feedback

Display open feedback items (bugs, design issues, questions, changes) for the current project.

Execute the following steps to display open feedback items:

---

## Step 1: Detect Current Project

Determine which project you're in by checking the current working directory:

```bash
pwd
```

Map the directory to a project code using `workspaces.json` or the directory name pattern.

---

## Step 2: Get Project ID from Database

```sql
-- Find project_id for the current project
SELECT project_id, project_code, project_name
FROM claude_pm.projects
WHERE project_code ILIKE '%current-project-keyword%'
   OR project_name ILIKE '%current-project-keyword%'
LIMIT 1;
```

**Project Mapping (Quick Reference):**
- `claude-pm` → `a3097e59-7799-4114-86a7-308702115905`
- `nimbus-user-loader` → `07206097-4caf-423b-9eb8-541d4c25da6c`
- `ATO-Tax-Agent` → `7858ecf4-4550-456d-9509-caea0339ec0d`

---

## Step 3: Query Open Feedback

```sql
-- Get all open feedback for this project
SELECT
    feedback_id::text,
    feedback_type,
    status,
    description,
    created_at,
    (SELECT COUNT(*) FROM claude_pm.project_feedback_comments c
     WHERE c.feedback_id = f.feedback_id) as comments
FROM claude_pm.project_feedback f
WHERE project_id = 'PROJECT-ID-FROM-STEP-2'::uuid
  AND status IN ('new', 'in_progress')
ORDER BY
    CASE feedback_type
        WHEN 'bug' THEN 1
        WHEN 'design' THEN 2
        WHEN 'change' THEN 3
        WHEN 'question' THEN 4
    END,
    created_at ASC;
```

---

## Step 4: Display Summary

Format the results in a user-friendly summary:

```
📋 OPEN FEEDBACK - [Project Name]

🐛 Bugs (X)
  - [feedback_id] Description... (Created: date, Comments: N)

🎨 Design (X)
  - [feedback_id] Description... (Created: date, Comments: N)

🔄 Changes (X)
  - [feedback_id] Description... (Created: date, Comments: N)

❓ Questions (X)
  - [feedback_id] Description... (Created: date, Comments: N)

Total Open: X items

---
To view details: SELECT * FROM claude_pm.project_feedback WHERE feedback_id = 'id'::uuid
To add comment: INSERT INTO claude_pm.project_feedback_comments (feedback_id, author, content) VALUES ('id'::uuid, 'claude', 'your comment')
To mark fixed: UPDATE claude_pm.project_feedback SET status = 'fixed', notes = 'summary' WHERE feedback_id = 'id'::uuid
```

---

## Step 5: Optional - Show Recent Activity

If requested, also show recently fixed items:

```sql
-- Get recently resolved feedback (last 7 days)
SELECT
    feedback_id::text,
    feedback_type,
    description,
    resolved_at
FROM claude_pm.project_feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('fixed', 'wont_fix')
  AND resolved_at > NOW() - INTERVAL '7 days'
ORDER BY resolved_at DESC
LIMIT 5;
```

---

## Error Handling

**If project not found in database:**
- Check `workspaces.json` for correct project mapping
- Suggest registering project (see `C:\claude\shared\docs\feedback-system-guide.md`)

**If no open feedback:**
- Display: "✅ No open feedback items. Great work!"

**If database connection fails:**
- Remind user to check postgres MCP configuration
- Check connection: `SELECT 1;`

---

**Note:** This command is read-only. Use `/feedback-create` to add new items.
