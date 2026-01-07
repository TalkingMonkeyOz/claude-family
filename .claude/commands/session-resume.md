**QUICK SESSION RESUME - Database-Driven Context**

Query DATABASE for session context - this is the source of truth.

---

## Execute These Steps

### Step 1: Get Project Name
Use the current working directory basename as project_name.

### Step 2: Query Active Todos (MCP)
```
mcp__postgres__execute_sql with:
SELECT content, status, priority
FROM claude.todos t
JOIN claude.projects p ON t.project_id = p.project_id
WHERE p.project_name = '{project_name}'
  AND t.is_deleted = false
  AND t.status IN ('pending', 'in_progress')
ORDER BY CASE status WHEN 'in_progress' THEN 1 ELSE 2 END, priority
LIMIT 10;
```

### Step 3: Query Last Session (MCP)
```
mcp__postgres__execute_sql with:
SELECT session_summary, session_end
FROM claude.sessions
WHERE project_name = '{project_name}' AND session_end IS NOT NULL
ORDER BY session_end DESC LIMIT 1;
```

### Step 4: Query Session State (MCP)
```
mcp__postgres__execute_sql with:
SELECT current_focus, next_steps
FROM claude.session_state
WHERE project_name = '{project_name}';
```

### Step 5: Check Messages
Use `mcp__orchestrator__check_inbox` with project_name parameter.

### Step 6: Check Git Status
Run `git status --short` via Bash tool.

---

## Display Format

```
╔══════════════════════════════════════════════════════════════╗
║  SESSION RESUME - {project_name}                             ║
╠══════════════════════════════════════════════════════════════╣
║  Last Session: {session_end} - {session_summary}             ║
║  Focus: {current_focus}                                      ║
╠══════════════════════════════════════════════════════════════╣
║  ACTIVE TODOS ({count}):                                     ║
║  → {in_progress items}                                       ║
║  ○ {pending items}                                           ║
╠══════════════════════════════════════════════════════════════╣
║  NEXT STEPS: {from session_state.next_steps}                 ║
╠══════════════════════════════════════════════════════════════╣
║  UNCOMMITTED: {count} files | MESSAGES: {pending count}      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Notes

- **Source of truth**: Database (claude.todos, claude.sessions, claude.session_state)
- **Auto-injection**: Session context is also auto-injected by RAG hook when you ask "where was I" or similar
- **Alternative**: Just ask "what was I working on?" - the RAG hook will inject context automatically
