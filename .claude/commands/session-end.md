**COMPLETE SESSION WORKFLOW: Logging + Git**

Execute these steps to properly close the session. Session was auto-logged at start via hook.

---

## Step 1: Update Session Summary (MCP)

```sql
-- Update the current session with summary
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'Brief description of what was accomplished',
    tasks_completed = ARRAY['Task 1', 'Task 2', 'Task 3']
WHERE project_name = '{project_name}'
  AND session_end IS NULL
ORDER BY session_start DESC
LIMIT 1;
```

---

## Step 2: Capture Knowledge (if applicable)

**Only if you discovered something reusable:**

```sql
INSERT INTO claude.knowledge
(title, content, category, project_id, created_by)
VALUES (
    'Pattern/Gotcha Title',
    'Description of the pattern, solution, or gotcha',
    'pattern',  -- or: 'gotcha', 'procedure', 'reference'
    (SELECT project_id FROM claude.workspaces WHERE project_name = '{project_name}'),
    'claude'
);
```

---

## Step 3: Update Session State

```sql
UPDATE claude.session_state
SET
    current_focus = 'What we were working on',
    next_steps = ARRAY['Next step 1', 'Next step 2']
WHERE project_name = '{project_name}';
```

---

## Step 4: Check Git Status

Run `git status` and commit if there are meaningful changes.

---

## Quick Checklist

- [ ] Session summary updated
- [ ] Knowledge captured (if any)
- [ ] Session state updated for next time
- [ ] Changes committed (if applicable)

---

**Note**: Session logging is automatic via SessionStart hook. This command focuses on closing out cleanly.

---

**Version**: 3.0
**Created**: 2025-10-21
**Updated**: 2026-01-10
**Location**: .claude/commands/session-end.md
