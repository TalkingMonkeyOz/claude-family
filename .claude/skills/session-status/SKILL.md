---
name: session-status
description: "Quick read-only status check showing work context, todos, messages, and git state"
user-invocable: true
disable-model-invocation: true
---

# Session Status (Read-Only)

Get instant visibility into project state. NO database writes, NO session logging.

---

## Step 1: Get Work Context (MCP)

Use `mcp__project-tools__get_work_context` with `scope="current"`.

This returns: active feature, in-progress tasks, last session summary, todo count.

## Step 2: Get Active Todos (MCP)

Use `mcp__project-tools__get_incomplete_todos` with the current project name.

## Step 3: Check Messages (MCP)

Use `mcp__project-tools__check_inbox` with `project_name` parameter.

## Step 4: Check Git Status

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

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/session-status/SKILL.md
