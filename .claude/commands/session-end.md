**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, Claude MUST complete ALL of the following:

---

## 1. Generate Session Summary

Analyze conversation to create:
- **Tasks completed** (array of strings)
- **Learnings gained** (key insights, gotchas discovered)
- **Session summary** (2-3 sentences)

---

## 2. Update Database Records

### Update sessions table:

```sql
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = '[Your 2-3 sentence summary]',
    tasks_completed = ARRAY['task1', 'task2', ...],
    learnings_gained = ARRAY['learning1', 'learning2', ...]
WHERE session_id = '[CURRENT_SESSION_ID]'::uuid
  AND session_end IS NULL;
```

### Update session_state table:

```sql
INSERT INTO claude.session_state
(project_name, todo_list, current_focus, next_steps, updated_at)
VALUES (
    '[PROJECT_NAME]',
    '[CURRENT_TODOWRITE_JSON]'::jsonb,
    '[What was being worked on]',
    ARRAY['Next step 1', 'Next step 2', 'Next step 3'],
    NOW()
)
ON CONFLICT (project_name)
DO UPDATE SET
    todo_list = EXCLUDED.todo_list,
    current_focus = EXCLUDED.current_focus,
    next_steps = EXCLUDED.next_steps,
    updated_at = NOW();
```

---

## 3. Update TODO_NEXT_SESSION.md

Write/update `docs/TODO_NEXT_SESSION.md` with:

```markdown
# Next Session TODO

**Last Updated**: [TODAY'S DATE]
**Last Session**: [Brief session description]

---

## Completed This Session

- [x] Task 1
- [x] Task 2

---

## Next Steps

1. [Priority 1 item]
2. [Priority 2 item]
3. [Priority 3 item]

---

## Pending Work

- [ ] Incomplete task 1
- [ ] Incomplete task 2

---

**Version**: X.0
**Created**: [ORIGINAL DATE]
**Updated**: [TODAY]
**Location**: docs/TODO_NEXT_SESSION.md
```

---

## 4. Knowledge Capture (Optional)

If you discovered reusable patterns or gotchas:

```sql
INSERT INTO claude.knowledge
(project_id, category, title, content, created_at)
VALUES (
    '[PROJECT_UUID]'::uuid,
    'pattern',  -- or 'gotcha', 'decision', 'learning'
    '[Pattern Title]',
    '[Detailed description]',
    NOW()
);
```

---

## 5. Check for Uncommitted Changes

Run `git status` and warn user if there are uncommitted changes.

---

## Verification

Before confirming session end:

- [ ] sessions table updated with summary
- [ ] session_state table updated with todos/focus/next_steps
- [ ] TODO_NEXT_SESSION.md file updated
- [ ] Uncommitted changes noted (if any)

---

**Session ID**: Use environment variable `CLAUDE_SESSION_ID` or query latest from database.

**Project ID**: For claude-family: `20b5627c-e72c-4501-8537-95b559731b59`
