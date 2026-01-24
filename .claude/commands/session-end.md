**COMPLETE SESSION WORKFLOW: Task Persistence + Logging**

Before ending this session, execute ALL steps in order.

---

## Step 1: Persist Incomplete Tasks to Todos

**Check TaskList for incomplete work:**

```
Call TaskList to see all session tasks
```

For each task with status `pending` or `in_progress`:
1. Check if matching Todo already exists in `claude.todos` (fuzzy match on content)
2. If no match exists, create a new Todo using TodoWrite

**Example:**
```
TaskList shows:
  #1: Fix login bug (completed) → No action needed
  #2: Update docs (pending) → Create Todo via TodoWrite
  #3: Refactor auth (in_progress) → Create Todo via TodoWrite
```

This ensures incomplete session work persists for next session.

---

## Step 2: Update Session Record

```sql
-- Get current session ID (from SessionStart)
SELECT session_id, session_start
FROM claude.sessions
WHERE project_name = '{project_name}'
ORDER BY session_start DESC LIMIT 1;

-- Update with summary
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'Brief summary of what was accomplished',
    tasks_completed = ARRAY['task1', 'task2'],
    learnings_gained = ARRAY['learning1', 'learning2'],
    challenges_encountered = ARRAY['challenge1']
WHERE session_id = '{session_id}';
```

---

## Step 3: Update Session State

```sql
-- Save current focus and next steps for session resume
INSERT INTO claude.session_state
    (project_name, current_focus, next_steps, pending_actions, updated_at)
VALUES (
    '{project_name}',
    'What I was working on',
    '[{"content": "Next step 1", "priority": 1}, {"content": "Next step 2", "priority": 2}]'::jsonb,
    ARRAY['pending-action-1'],
    NOW()
)
ON CONFLICT (project_name) DO UPDATE SET
    current_focus = EXCLUDED.current_focus,
    next_steps = EXCLUDED.next_steps,
    pending_actions = EXCLUDED.pending_actions,
    updated_at = NOW();
```

---

## Step 4: Store Learnings (Optional)

If you discovered a reusable pattern or gotcha, store it:

```
Use project-tools MCP:
mcp__project-tools__store_knowledge(
    title="Pattern/Gotcha Title",
    content="Detailed explanation",
    knowledge_type="pattern|gotcha|learned",
    project_name="{project_name}",
    tags=["relevant", "tags"]
)
```

Or via SQL:
```sql
INSERT INTO claude.knowledge
(title, content, knowledge_type, source_project, tags, confidence_score)
VALUES (
    'Pattern Title',
    'Detailed explanation',
    'pattern',
    '{project_name}',
    ARRAY['tag1', 'tag2'],
    0.8
);
```

---

## Step 5: Verification Checklist

Before closing:

- [ ] Incomplete tasks converted to Todos (Step 1)
- [ ] Session record updated with summary (Step 2)
- [ ] Session state saved for resume (Step 3)
- [ ] Any learnings stored (Step 4, if applicable)
- [ ] No uncommitted code changes (run `git status`)

---

## Quick Reference

| What | Where | Tool |
|------|-------|------|
| Session tasks | In-memory TaskList | TaskList, TaskUpdate |
| Persistent todos | `claude.todos` | TodoWrite |
| Session record | `claude.sessions` | postgres MCP |
| Session state | `claude.session_state` | postgres MCP |
| Learnings | `claude.knowledge` | project-tools MCP |

---

## Task → Todo Lifecycle

```
Session Start: Load Todos → User picks work → TaskCreate
Mid-Session: Work tasks → TaskUpdate (in_progress/completed)
Session End: Incomplete Tasks → TodoWrite → Persist to claude.todos
Next Session: Todos reload → Cycle continues
```

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-01-24
**Location**: .claude/commands/session-end.md
