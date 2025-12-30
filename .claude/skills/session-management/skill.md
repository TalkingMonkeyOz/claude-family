# Session Management Skill

**Status**: Active
**Last Updated**: 2025-12-26

---

## Overview

This skill provides guidance for managing Claude Code session lifecycle: starting sessions, ending sessions, resuming work, and session logging.

---

## When to Use

Invoke this skill when:
- Starting a new Claude Code session
- Ending a session and logging work
- Resuming from a previous session
- Creating session summaries
- Managing session context

---

## Quick Reference

### Session Lifecycle Commands

| Command | Purpose | When |
|---------|---------|------|
| `/session-start` | Initialize session logging | Start of every session |
| `/session-end` | Log summary and clean up | End of every session |
| `/session-status` | View project state (database-driven) | Quick status check |
| `/session-commit` | Complete session + git commit | End with git commit |

---

## Session Start Protocol

**MANDATORY at session start**:

```bash
/session-start
```

**What it does**:
1. Creates `claude.sessions` record
2. Sets `CLAUDE_SESSION_ID` environment variable
3. Records identity, project, start time
4. Enables session-scoped logging

**Skip only if**: Session already logged by automated hook

---

## Session End Protocol

**MANDATORY at session end**:

```bash
/session-end
```

**What it does**:
1. Updates `claude.sessions` with summary
2. Records `session_end` timestamp
3. Logs work completed
4. Captures key decisions

**Alternative**: Use `/session-commit` to combine session end + git commit

---

## Session Resume

When continuing work from a previous session:

```bash
/session-resume
```

**What it does**:
1. Loads previous session summary
2. Retrieves context from last session
3. Shows pending work items
4. Displays recent feedback

**Provides**:
- Session summary
- TODO list status
- Open feedback items
- Recent commits

---

## Session Logging

Sessions are automatically logged to `claude.sessions` table:

```sql
SELECT
    session_id::text,
    session_start,
    session_end,
    summary,
    identity_id::text
FROM claude.sessions
WHERE project_name = 'your-project'
ORDER BY session_start DESC
LIMIT 10;
```

---

## Session Summary Best Practices

When ending a session, provide:

1. **What was completed** - List key accomplishments
2. **What's pending** - Unfinished work, blockers
3. **Key decisions** - Architectural choices, trade-offs
4. **Next steps** - Clear continuation point

**Example**:
```
Session Summary:
- Completed: Implemented user authentication with JWT
- Pending: Need to add refresh token logic
- Decisions: Using httpOnly cookies (not localStorage) for security
- Next: Add token refresh endpoint, then test login flow
```

---

## Parent Session Tracking

When spawning agents, track parent session:

```sql
-- Agents spawned from this session
SELECT
    agent_type,
    task_description,
    success,
    execution_time_seconds
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
SELECT
    session_id::text,
    project_name,
    EXTRACT(EPOCH FROM (session_end - session_start))/3600 as hours
FROM claude.sessions
WHERE session_end IS NOT NULL
ORDER BY hours DESC
LIMIT 20;

-- Sessions by identity
SELECT
    i.identity_name,
    COUNT(*) as session_count,
    AVG(EXTRACT(EPOCH FROM (s.session_end - s.session_start))/3600) as avg_hours
FROM claude.sessions s
JOIN claude.identities i ON s.identity_id = i.identity_id
GROUP BY i.identity_name
ORDER BY session_count DESC;
```

---

## Message Accountability Workflow

**NEW in v2.0**: Messages are now integrated into session lifecycle.

### At Session Start

1. Check inbox for pending messages
2. Display FULL message details (not just count)
3. Identify actionable messages (task_request, question, handoff)
4. Prompt for action before continuing work

**Action Required**:
```python
# For each actionable message, choose one:

# Option 1: Convert to persistent todo
acknowledge(message_id, action='actioned', project_id='project-uuid')

# Option 2: Defer with reason
acknowledge(message_id, action='deferred', defer_reason='Out of scope')

# Option 3: Complete work now, then acknowledge
acknowledge(message_id, action='acknowledged')
```

### At Session End

1. Check for unactioned messages
2. Display WARNING if any exist (does not block)
3. Recommend actioning or deferring
4. Allow session to end (messages carry over to next session)

**Unactioned messages will:**
- Persist in database
- Show in next session-start
- Appear in TODO_NEXT_SESSION.md
- Count toward "carryover" metrics

---

## Todo Persistence Workflow

**NEW in v2.0**: Integration between TodoWrite (ephemeral) and claude.todos (persistent).

### Todo Systems

| System | Scope | Visibility | Use Case |
|--------|-------|------------|----------|
| **TodoWrite** | Session-only | Current conversation | Active work during session |
| **claude.todos** | Cross-session | Database + CFM UI | Work that persists beyond session |
| **TODO_NEXT_SESSION.md** | Session handoff | File system | Human-readable context |

### At Session Start

Load persistent todos from database:

```sql
SELECT todo_id::text, content, status, priority
FROM claude.todos
WHERE project_id = 'project-uuid'
  AND is_deleted = false
  AND status IN ('pending', 'in_progress')
ORDER BY priority, created_at;
```

Display to user but **DO NOT auto-populate TodoWrite** (slash commands can't modify TodoWrite).

### During Session

Users have two options:

1. **Use TodoWrite for session work** (ephemeral)
   - Quick, in-conversation tracking
   - Lost at session end unless saved

2. **Use /todo commands for persistent work**
   - `/todo add "content"` - Persists to database
   - `/todo list` - View from database
   - `/todo complete <id>` - Mark done
   - Survives across sessions

### At Session End

1. Check current TodoWrite items
2. Prompt user: "Save any items to persist?"
3. User manually runs `/todo add` for items to keep
4. Generate TODO_NEXT_SESSION.md with:
   - Active todos from claude.todos
   - Completed work summary
   - Unactioned messages

**TodoWrite items not saved = LOST**

---

## Smart Session Resume

**NEW in v2.0**: session-start detects if session exists for today.

### Resume Detection

```sql
-- Check for existing session today
SELECT session_id, session_start
FROM claude.sessions
WHERE project_name = 'project-name'
  AND DATE(session_start) = CURRENT_DATE
  AND session_end IS NULL;
```

**If session exists:**
- Show "Resuming session from [time]"
- Display session ID
- Skip creating new session
- Jump to messages/todos display

**If no session:**
- Create new session record
- Continue with full initialization

### When to Use Which Command

| Scenario | Command | Why |
|----------|---------|-----|
| Start new session | `/session-start` | Logs to DB, loads full context |
| Quick status check | `/session-resume` | Read-only view, no DB writes |
| Continue existing session | `/session-start` | Detects existing session automatically |

---

## Session End Checklist (v2.0)

Before ending session, verify:

1. **Messages**
   - [ ] Checked for unactioned messages
   - [ ] Actioned or deferred task_request/question/handoff messages
   - [ ] OR accepted carryover warning

2. **Todos**
   - [ ] Saved important TodoWrite items to claude.todos
   - [ ] Updated status of in-progress todos
   - [ ] OR accepted that TodoWrite items will be lost

3. **Logging**
   - [ ] Updated session record with summary
   - [ ] Stored reusable knowledge (if any)
   - [ ] Updated memory graph

4. **Handoff**
   - [ ] Generated TODO_NEXT_SESSION.md
   - [ ] Included context for next session
   - [ ] Listed unactioned messages and pending todos

---

## Related Skills

- `project-ops` - Project lifecycle management
- `messaging` - Inter-session communication
- `work-item-routing` - Creating session tasks

---

## Key Gotchas

### 1. Skipping Session Start/End

**Problem**: Missing session logging loses context for future sessions

**Solution**: Always run `/session-start` and `/session-end`

### 2. Vague Summaries

**Problem**: "Worked on the project" provides no value

**Solution**: Be specific about what changed and why

### 3. Not Tracking Parent Sessions

**Problem**: Agents spawned from session aren't linked

**Solution**: Use `parent_session_id` when spawning agents

---

**Version**: 2.0 (Added message accountability + todo persistence workflows)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: .claude/skills/session-management/skill.md
