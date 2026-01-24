**QUICK SESSION RESUME - Database-Driven Context**

Use project-tools MCP for efficient queries (consolidates multiple SQL into single calls).

---

## Execute These Steps

### Step 1: Get Project Context (ONE MCP call)

Use `mcp__project-tools__get_project_context` with project path from current directory.

This returns: project info, phase, active features, last session summary, feedback count, todo count.

### Step 2: Get Actual Todos (ONE MCP call)

Use `mcp__project-tools__get_incomplete_todos` with project name.

This returns: todo items with content, status, priority.

### Step 3: Check Messages (ONE MCP call)

Use `mcp__orchestrator__check_inbox` with project_name parameter.

### Step 4: Check Git Status

Run `git status --short` via Bash tool.

---

## Display Format

```
+==================================================================+
|  SESSION RESUME - {project_name}                                 |
+==================================================================+
|  Phase: {phase} | Status: {status}                               |
|  Last Session: {last_session.started} - {last_session.summary}   |
+------------------------------------------------------------------+
|  ACTIVE FEATURES:                                                |
|    {F-code}: {feature_name} ({status})                           |
+------------------------------------------------------------------+
|  ACTIVE TODOS ({count}):                                         |
|  In Progress:                                                    |
|    > {in_progress items}                                         |
|  Pending:                                                        |
|    [P1] {priority 1 items}                                       |
|    [P2] {priority 2 items}                                       |
|    [P3] {priority 3 items}                                       |
+------------------------------------------------------------------+
|  UNCOMMITTED: {count} files | MESSAGES: {pending count}          |
|  FEEDBACK: {pending_feedback_count} open items                   |
+==================================================================+
```

---

## Notes

- **Efficient**: Uses project-tools MCP (2 calls) instead of raw SQL (4 queries)
- **Source of truth**: Database via MCP tools
- **Auto-injection**: Session context also auto-injected by RAG hook
- **Priority icons**: P1 = critical, P2 = important, P3 = normal

---

**Version**: 3.0
**Created**: 2025-12-26
**Updated**: 2026-01-24
**Location**: .claude/commands/session-resume.md
