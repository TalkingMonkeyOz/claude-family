**QUICK SESSION RESUME - Database-Driven Context**

Query DATABASE for session context - this is the source of truth, not files.

---

## Execute These Steps

### Step 1: Get Project Info
Use the current working directory basename as project_name.

### Step 2: Query Last Session (MCP)
```sql
SELECT session_summary, session_end, tasks_completed
FROM claude.sessions
WHERE project_name = '{project_name}' AND session_end IS NOT NULL
ORDER BY session_end DESC LIMIT 1;
```

### Step 3: Query Session State (MCP)
```sql
SELECT current_focus, next_steps
FROM claude.session_state
WHERE project_name = '{project_name}';
```

### Step 4: Query Active Todos (MCP)
```sql
SELECT content, status, priority
FROM claude.todos t
JOIN claude.projects p ON t.project_id = p.project_id
WHERE p.project_name = '{project_name}'
  AND t.is_deleted = false
  AND t.status IN ('pending', 'in_progress')
ORDER BY
  CASE status WHEN 'in_progress' THEN 1 ELSE 2 END,
  priority ASC
LIMIT 10;
```

### Step 5: Check Messages
Use `mcp__orchestrator__check_inbox` with project_name parameter.

### Step 6: Check Git Status
Run `git status --short` via Bash tool.

---

## Display Format

```
+==================================================================+
|  SESSION RESUME - {project_name}                                 |
+==================================================================+
|  Last Session: {session_end} - {session_summary}                 |
|  Focus: {current_focus}                                          |
+------------------------------------------------------------------+
|  ACTIVE TODOS ({count}):                                         |
|  In Progress:                                                    |
|    > {in_progress items}                                         |
|  Pending:                                                        |
|    [P1] {priority 1 items}                                       |
|    [P2] {priority 2 items}                                       |
|    [P3] {priority 3 items}                                       |
+------------------------------------------------------------------+
|  NEXT STEPS: {from session_state.next_steps, top 3}              |
+------------------------------------------------------------------+
|  UNCOMMITTED: {count} files | MESSAGES: {pending count}          |
+==================================================================+
```

---

## Notes

- **Source of truth**: Database (claude.todos, claude.sessions, claude.session_state)
- **Auto-injection**: Session context is also auto-injected by RAG hook on keywords like "where was I" or "my todos"
- **Priority icons**: P1 = critical, P2 = important, P3 = normal

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2026-01-07
**Location**: .claude/commands/session-resume.md
