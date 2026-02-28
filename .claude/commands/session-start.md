**SESSION STARTUP PROTOCOL**

Session logging is **automatic** via the SessionStart hook. This command is for manual context loading when needed.

---

## Step 1: Start Session (MCP)

```
mcp__project-tools__start_session(project_name="current-project")
```

This logs the session to `claude.sessions`, loads active todos, and checks messages.

---

## Step 2: Recall Relevant Context

Search cognitive memory for context relevant to the current task:

```
mcp__project-tools__recall_memories(query="relevant keywords from user's request")
```

---

## Step 3: Get Work Context

Load active work items (token-budgeted):

```
mcp__project-tools__get_work_context(scope="current")
```

Returns: active feature, in-progress tasks, recent session summary.

---

## Step 4: Check Messages

```
mcp__project-tools__check_inbox(project_name="current-project")
```

---

## Step 5: Check Open Feedback (Optional)

If working on a registered project:

```sql
SELECT
    feedback_type,
    COUNT(*) as count
FROM claude.feedback f
JOIN claude.projects p ON f.project_id = p.project_id
WHERE p.project_code = 'current-project'
  AND f.status IN ('new', 'triaged', 'in_progress')
GROUP BY feedback_type;
```

If open items exist, note: "This project has X open feedback items. Use `/feedback` to view details."

---

## Checklist

Before starting work:

- [ ] Session logged (auto via hook, or `start_session` MCP)
- [ ] Recalled relevant memories
- [ ] Loaded work context (`get_work_context`)
- [ ] Checked inbox for messages
- [ ] Checked open feedback (if applicable)

---

**Remember**: Context loading prevents rediscovering known solutions. Especially use `recall_memories` before complex tasks.

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-02-28
**Location**: .claude/commands/session-start.md
