**MANDATORY END-OF-SESSION CHECKLIST**

Complete these steps before ending your session.

---

## Step 1: Close Session in Database

```sql
-- Get current session ID
SELECT session_id::text, session_start, project_name
FROM claude.sessions
WHERE project_name = '$PROJECT_NAME'
  AND session_end IS NULL
ORDER BY session_start DESC
LIMIT 1;

-- Update session with summary (replace $SESSION_ID)
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'Brief summary of what was accomplished',
    tasks_completed = ARRAY['Task 1', 'Task 2'],
    learnings_gained = ARRAY['Key learning or pattern discovered'],
    challenges_encountered = ARRAY['Challenge and resolution']
WHERE session_id = '$SESSION_ID'::uuid
RETURNING session_id, session_end;
```

---

## Step 2: Save Session State (For Next Session)

```sql
INSERT INTO claude.session_state
(project_name, current_focus, next_steps, updated_at)
VALUES (
    '$PROJECT_NAME',
    'What should be focused on next',
    '[{"step": "Next step 1", "priority": 1}, {"step": "Next step 2", "priority": 2}]'::jsonb,
    NOW()
)
ON CONFLICT (project_name)
DO UPDATE SET
    current_focus = EXCLUDED.current_focus,
    next_steps = EXCLUDED.next_steps,
    updated_at = NOW();
```

---

## Step 3: Store Knowledge (If Applicable)

**Only if you discovered a reusable pattern:**

```sql
INSERT INTO claude.knowledge
(pattern_name, category, description, example_code, gotchas, confidence_level)
VALUES (
    'Pattern Name',
    'category',  -- csharp, mcp, git, windows, sql, etc.
    'What this solves',
    'Code example',
    'Gotchas to watch for',
    8  -- confidence 1-10
);
```

---

## Step 4: Verify

```sql
-- Confirm session closed
SELECT session_id::text, session_end, session_summary
FROM claude.sessions
WHERE session_id = '$SESSION_ID'::uuid;
```

---

## Quick Checklist

- [ ] Session closed with summary
- [ ] Session state saved for next session
- [ ] Knowledge stored (if discovered something reusable)
- [ ] Uncommitted changes handled (commit or stash)

---

## When to Use Which Command

| Situation | Command |
|-----------|---------|
| Done for the day | `/session-end` |
| Done + want to commit | `/session-commit` |
| Mid-session checkpoint | `/session-save` |
| Quick status check | `/session-status` |

---

**Version**: 2.0 (Updated to claude.* schema, removed deprecated MCPs)
**Created**: 2025-12-15
**Updated**: 2026-01-26
**Location**: .claude/commands/session-end.md
