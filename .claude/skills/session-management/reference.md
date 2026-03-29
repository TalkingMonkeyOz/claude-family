# Session Management Skill — Detailed Reference

## Session Logging SQL

```sql
SELECT session_id::text, session_start, session_end, summary, identity_id::text
FROM claude.sessions
WHERE project_name = 'your-project'
ORDER BY session_start DESC LIMIT 10;
```

---

## Parent Session Tracking

```sql
SELECT agent_type, task_description, success, execution_time_seconds
FROM claude.agent_sessions
WHERE parent_session_id = 'your-session-id'
ORDER BY spawned_at DESC;
```

---

## Common Queries

```sql
-- Active sessions (no end time)
SELECT session_id::text, project_name, session_start
FROM claude.sessions
WHERE session_end IS NULL
ORDER BY session_start DESC;

-- Session duration
SELECT session_id::text, project_name,
    EXTRACT(EPOCH FROM (session_end - session_start))/3600 as hours
FROM claude.sessions
WHERE session_end IS NOT NULL
ORDER BY hours DESC LIMIT 20;

-- Sessions by identity
SELECT i.identity_name, COUNT(*) as session_count,
    AVG(EXTRACT(EPOCH FROM (s.session_end - s.session_start))/3600) as avg_hours
FROM claude.sessions s
JOIN claude.identities i ON s.identity_id = i.identity_id
GROUP BY i.identity_name ORDER BY session_count DESC;
```

---

## Message Accountability Workflow

### At Session Start

1. Check inbox for pending messages
2. Display FULL message details (not just count)
3. Identify actionable messages (task_request, question, handoff)
4. Prompt for action before continuing work

```python
# For each actionable message, choose one:
acknowledge(message_id, action='actioned', project_id='project-uuid')
acknowledge(message_id, action='deferred', defer_reason='Out of scope')
acknowledge(message_id, action='acknowledged')
```

### At Session End

1. Check for unactioned messages
2. Display WARNING if any exist (does not block)
3. Recommend actioning or deferring
4. Messages carry over to next session

**Unactioned messages will:** persist in DB, show in next session-start, appear in next session's todo list, count toward carryover metrics.

---

## Todo Persistence Workflow

### Todo Systems

| System | Scope | Use Case |
|--------|-------|----------|
| **TodoWrite** | Session-only | Active work during session |
| **claude.todos** | Cross-session | Persistent work items |
| **store_session_notes()** | Session handoff | Notes persist via MCP |

### At Session Start — Load Persistent Todos

```sql
SELECT todo_id::text, content, status, priority
FROM claude.todos
WHERE project_id = 'project-uuid'
  AND is_deleted = false
  AND status IN ('pending', 'in_progress')
ORDER BY priority, created_at;
```

**DO NOT auto-populate TodoWrite** — slash commands can't modify it.

### During Session

1. **TodoWrite** for session work (ephemeral, lost at end)
2. **`/todo` commands** for persistent work (survives sessions)

### At Session End

1. Check current TodoWrite items
2. Prompt: "Save any items to persist?"
3. User runs `/todo add` for items to keep
4. Save session notes via `store_session_notes(content, section)`

**TodoWrite items not saved = LOST**

---

## Smart Session Resume

### Resume Detection

```sql
SELECT session_id, session_start
FROM claude.sessions
WHERE project_name = 'project-name'
  AND DATE(session_start) = CURRENT_DATE
  AND session_end IS NULL;
```

**If session exists:** Show "Resuming from [time]", skip creating new session.
**If no session:** Create new record, full initialization.

| Scenario | Command | Why |
|----------|---------|-----|
| Start new session | `/session-start` | Logs to DB, loads full context |
| Quick status check | `/session-resume` | Read-only, no DB writes |
| Continue existing | `/session-start` | Detects existing session |

---

## Session End Checklist (v2.0)

1. **Messages**: Check unactioned, action or defer, or accept carryover
2. **Todos**: Save important TodoWrite items, update statuses
3. **Logging**: Update session record with summary, store knowledge via `remember()`
4. **Handoff**: Save session notes, include context for next session
