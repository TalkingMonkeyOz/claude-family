---
projects:
  - claude-family
tags:
  - session
  - procedure
  - lifecycle
  - mandatory
  - reference
synced: false
---

# Session Lifecycle - Reference

**Purpose**: Quick reference for key tables, troubleshooting, and best practices.
**Audience**: Claude instances and developers maintaining the system

See [[Session Lifecycle - Overview]] for complete context.

---

## Key Tables Updated

| Table | When | What |
|-------|------|------|
| **sessions** | Start | INSERT new row |
| **sessions** | End | UPDATE with summary, tasks |
| **session_state** | During/End | UPSERT todo_list, focus |
| **mcp_usage** | Every MCP call | INSERT tool usage |
| **agent_sessions** | Agent spawn | INSERT agent run |
| **messages** | As needed | INSERT/UPDATE messages |

---

## Common Issues

### Issue 1: Session Not Logged

**Symptom**: Session works but no record in database

**Cause**: Database connection failure in hook

**Fix**: Check `DATABASE_URI` environment variable

```bash
echo $DATABASE_URI
# Should be: postgresql://postgres:PASSWORD@localhost/ai_company_foundation
```

---

### Issue 2: NULL identity_id

**Symptom**: Session logged but `identity_id` is NULL

**Cause**: `CLAUDE_IDENTITY_ID` environment variable not set, DEFAULT_IDENTITY_ID is None

**Fix**: Ensure DEFAULT_IDENTITY_ID is set in session_startup_hook.py

---

### Issue 3: State Not Persisting

**Symptom**: `/session-end` completes but state not loaded next time

**Cause**: `session_state` table not updated OR project_name mismatch

**Debug**:
```sql
SELECT * FROM claude.session_state WHERE project_name = 'YOUR-PROJECT';
```

**Fix**: Ensure project_name matches exactly (case-sensitive)

---

### Issue 4: MCP Usage Not Logged

**Symptom**: Using MCP tools but no records in `mcp_usage`

**Cause**: Hook not firing OR `CLAUDE_SESSION_ID` not set

**Fix**: Session hook should export `CLAUDE_SESSION_ID` to environment

---

## Best Practices

### 1. Always Run /session-end

**Why**: Preserves state for next session

**When**:
- End of work day
- Before long break
- After completing major milestone
- Multiple times per session (to checkpoint)

### 2. Use TodoWrite Frequently

**Why**: Persists your task list automatically

**How**: TodoWrite tool updates `session_state.todo_list`

### 3. Check Messages at Session Start

**Why**: Other Claude instances may have sent updates

**How**: SessionStart hook shows pending messages automatically

### 4. Meaningful Summaries

**Why**: Future you (or other Claudes) need context

**How**: `/session-end` generates summary from conversation

---

## Related Documents

- [[Session Lifecycle - Overview]] - Overview and complete flow
- [[Session Lifecycle - Session Start]] - Startup sequence and configuration
- [[Session Lifecycle - Session End]] - Ending and resuming sessions
- [[Database Schema - Core Tables]] - sessions, session_state, mcp_usage tables
- [[Identity System - Overview]] - How identity is determined
- [[Session Quick Reference]] - Single-page cheat sheet
- [[Family Rules]] - Session rules (mandatory)
- [[Session User Stories]] - Traced examples

---

**Version**: 2.0 (split 2025-12-26)
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/40-Procedures/Session Lifecycle - Reference.md
