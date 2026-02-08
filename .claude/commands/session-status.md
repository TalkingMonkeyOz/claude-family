**QUICK STATUS CHECK - Read-Only View**

Get instant visibility into project state. NO database writes, NO session logging.

---

## Execute These Steps

### Step 1: Get Project Context (MCP)

Use `mcp__project-tools__get_project_context` with the current project name.

This returns: project info, phase, last session summary, active feature count, todo count.

### Step 2: Get Active Todos (MCP)

Use `mcp__project-tools__get_incomplete_todos` with the current project name.

### Step 3: Check Messages (MCP)

Use `mcp__orchestrator__check_inbox` with `project_name` parameter.

### Step 4: Check Git Status

```bash
git status --short
```

---

## Display Format

```
+==================================================================+
|  STATUS CHECK - {project_name} (read-only)                       |
+==================================================================+
|  Last Session: {date} - {summary}                                |
|  Phase: {phase}                                                  |
+------------------------------------------------------------------+
|  TODOS ({count}):                                                |
|  In Progress: {items}                                            |
|  Pending: {items by priority}                                    |
+------------------------------------------------------------------+
|  MESSAGES: {count} pending                                       |
|  UNCOMMITTED: {count} files                                      |
+==================================================================+
```

---

## Notes

- **Read-only**: Does NOT create session records or log anything
- **Source of truth**: Database (claude.todos, claude.sessions)
- **For full resume with context**: Use `/session-resume` instead

---

**Version**: 3.0 (Simplified to use MCP tools instead of raw SQL)
**Created**: 2025-12-27
**Updated**: 2026-02-08
**Location**: .claude/commands/session-status.md
