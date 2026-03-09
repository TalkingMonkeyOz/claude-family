# Check Open Feedback

Display open feedback items (bugs, design issues, questions, changes) for the current project.

**Schema is `claude.*` — never `claude_pm.*` or `claude_family.*`.**

---

## Execute These Steps

### Step 1: Detect Current Project

Determine the project name from the current working directory or `workspaces.json`:

```bash
pwd
```

Then look up the project ID:

```sql
SELECT id, project_code, project_name
FROM claude.projects
WHERE project_code ILIKE '%current-project-keyword%'
   OR project_name ILIKE '%current-project-keyword%'
LIMIT 1;
```

### Step 2: Query Open Feedback

```sql
SELECT
    f.id::text,
    f.feedback_type,
    f.status,
    f.description,
    f.created_at,
    f.updated_at
FROM claude.feedback f
WHERE f.project_id = 'PROJECT-ID-FROM-STEP-1'::uuid
  AND f.status IN ('new', 'triaged', 'in_progress')
ORDER BY
    CASE f.feedback_type
        WHEN 'bug'     THEN 1
        WHEN 'design'  THEN 2
        WHEN 'change'  THEN 3
        WHEN 'question' THEN 4
    END,
    f.created_at ASC;
```

**Valid feedback_type values**: `bug`, `design`, `question`, `change`
**Valid status values**: `new`, `triaged`, `in_progress`, `resolved`, `wont_fix`, `duplicate`

### Step 3: Display Summary

Format the results by type:

```
OPEN FEEDBACK - [Project Name]

Bugs (X)
  - [id-prefix] Description... (Created: date)

Design (X)
  - [id-prefix] Description... (Created: date)

Changes (X)
  - [id-prefix] Description... (Created: date)

Questions (X)
  - [id-prefix] Description... (Created: date)

Total Open: X items

---
To view details:  SELECT * FROM claude.feedback WHERE id = 'full-uuid'::uuid;
To advance status: mcp__project-tools__advance_status(type="feedback", id="FB-code", status="in_progress")
To resolve:        mcp__project-tools__advance_status(type="feedback", id="FB-code", status="resolved")
```

### Step 4: Optional - Show Recently Resolved

If requested, also show recently resolved items:

```sql
SELECT
    id::text,
    feedback_type,
    description,
    status,
    updated_at as resolved_at
FROM claude.feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('resolved', 'wont_fix')
  AND updated_at > NOW() - INTERVAL '7 days'
ORDER BY updated_at DESC
LIMIT 5;
```

---

## Error Handling

**If project not found:**
- Check `workspaces.json` for correct project mapping
- Query `claude.projects` to see all registered projects

**If no open feedback:**
- Display: "No open feedback items."

**If database connection fails:**
- Check postgres MCP configuration
- Test connection: `SELECT 1;`

---

## Status Transitions

Use `advance_status` (not raw SQL) to move feedback through the state machine:

```
new -> triaged -> in_progress -> resolved
                             -> wont_fix
                             -> duplicate
```

---

**Note:** This command is read-only. Use `/feedback-create` to add new items.

---

**Version**: 2.0 (Rewrote: use claude.feedback schema, advance_status for transitions, removed claude_pm.*)
**Created**: 2025-12-20
**Updated**: 2026-03-09
**Location**: .claude/commands/feedback-check.md
