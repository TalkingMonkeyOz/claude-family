**QUICK SESSION RESUME - Context at a Glance**

Gather context from DATABASE (source of truth) and display for user.

---

## 1. Query Last Session from Database

```sql
SELECT
    session_id::text,
    session_start,
    session_end,
    session_summary,
    tasks_completed[1:5] as recent_tasks
FROM claude.sessions
WHERE project_name = '[PROJECT_NAME]'
  AND session_end IS NOT NULL
ORDER BY session_end DESC
LIMIT 1;
```

---

## 2. Query Session State

```sql
SELECT
    current_focus,
    next_steps,
    todo_list,
    updated_at
FROM claude.session_state
WHERE project_name = '[PROJECT_NAME]';
```

---

## 3. Check Inbox for Messages

Use `mcp__orchestrator__check_inbox` with `project_name` parameter.

---

## 4. Check Uncommitted Files

Run `git status --short` and count lines.

---

## 5. Display Format

```
+==============================================================+
|  SESSION RESUME - [Project Name]                             |
+==============================================================+
|  Last Session: [session_end date/time]                       |
|  Summary: [session_summary from DB]                          |
+--------------------------------------------------------------+
|  CURRENT FOCUS: [from session_state.current_focus]           |
+--------------------------------------------------------------+
|  NEXT STEPS:                                                 |
|  1. [next_steps[0]]                                          |
|  2. [next_steps[1]]                                          |
|  3. [next_steps[2]]                                          |
+--------------------------------------------------------------+
|  UNCOMMITTED: [count] files | MESSAGES: [pending count]      |
+==============================================================+
```

---

## 6. Fallback to TODO File

If database has no session_state or last session, read `docs/TODO_NEXT_SESSION.md` as fallback.

---

## Notes

- **Source of truth**: Database (`claude.sessions`, `claude.session_state`)
- **Fallback**: `docs/TODO_NEXT_SESSION.md` file
- **Always check**: Inbox messages and git status
