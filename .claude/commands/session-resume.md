**QUICK SESSION RESUME - Database-Driven Context**

Query DATABASE for session context - this is the source of truth, not files.

---

## Execute These Steps

### Step 1: Get Project Context (MCP)

Use `mcp__project-tools__get_project_context` with the current project name.

This returns: project info, phase, last session summary, active feature count, todo count.

### Step 2: Get Active Todos (MCP)

Use `mcp__project-tools__get_incomplete_todos` with the current project name.

### Step 3: Check Session State

```sql
SELECT current_focus, next_steps
FROM claude.session_state
WHERE project_name = '{project_name}';
```

### Step 4: Check Messages (MCP)

Use `mcp__orchestrator__check_inbox` with `project_name` parameter.

### Step 5: Check Git Status

```bash
git status --short
```

---

## Display Format

```
+==================================================================+
|  SESSION RESUME - {project_name}                                 |
+==================================================================+
|  Last Session: {date} - {summary}                                |
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

**Version**: 3.0 (Simplified: MCP tools instead of raw SQL for todos/context)
**Created**: 2025-12-26
**Updated**: 2026-02-08
**Location**: .claude/commands/session-resume.md