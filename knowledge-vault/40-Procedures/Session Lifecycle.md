---
projects:
  - claude-family
tags:
  - session
  - procedure
  - lifecycle
  - mandatory
synced: false
---

# Session Lifecycle Guide

**Purpose**: Complete guide to how Claude sessions work from start to finish.
**Audience**: Claude instances and developers maintaining the system

This document explains every step of the session lifecycle: how sessions start, what happens during work, and how they end.

---

## Overview

### What is a Session?

A **session** is a single continuous interaction between a user and a Claude instance, tracked from launch to termination.

**Key characteristics**:
- One session = one `claude` process
- Tracked in `claude.sessions` table
- Has unique `session_id` (UUID)
- Linked to an `identity_id` (which Claude instance)
- Linked to a `project_name` (which project)

### Why Session Tracking Matters

| Benefit | Description |
|---------|-------------|
| **Context persistence** | Resume where you left off across days/weeks |
| **Knowledge capture** | Learnings don't disappear when you close terminal |
| **Cost tracking** | Understand time/money spent per project |
| **Audit trail** | Who did what, when, on which project |
| **Coordination** | Multiple Claudes can see each other's work |

### Session vs Agent Session

| Aspect | Session | Agent Session |
|--------|---------|---------------|
| **What** | Interactive Claude Code | Spawned background agent |
| **Table** | `claude.sessions` | `claude.agent_sessions` |
| **Duration** | Minutes to hours | Seconds to minutes |
| **User interaction** | Yes, continuous | No, runs autonomously |
| **Logging** | Manual + hook | Automatic via orchestrator |

---

## Session Start

When you launch Claude (via launcher or `claude` command), here's what happens:

### 1. Hook Trigger (SessionStart Event)

**File**: `C:\Projects\claude-family\.claude\hooks.json` (lines 74-84)

```json
"SessionStart": [{
  "hooks": [{
    "type": "command",
    "command": "python \"C:/Projects/claude-family/.claude-plugins/claude-family-core/scripts/session_startup_hook.py\"",
    "timeout": 30,
    "description": "Auto-log session and load state/messages"
  }]
}]
```

**When**: Fires automatically when Claude Code starts
**Purpose**: Creates session record, loads context

---

### 2. Project Detection (cwd-based)

The hook determines which project you're working on:

```python
project_name = os.path.basename(os.getcwd())
# Example: C:\Projects\claude-family → "claude-family"
```

**Limitation**: Assumes directory name = project name

**Better approach** (future): Read from CLAUDE.md frontmatter:
```yaml
---
project_id: 20b5627c-e72c-4501-8537-95b559731b59
project_name: claude-family
---
```

---

### 3. Identity Resolution

**Current behavior** (hardcoded):

```python
DEFAULT_IDENTITY_ID = 'ff32276f-9d05-4a18-b092-31b54c82fff9'  # claude-code-unified
identity = os.environ.get('CLAUDE_IDENTITY_ID', DEFAULT_IDENTITY_ID)
```

**Result**: All CLI sessions = claude-code-unified

**Target behavior** (identity per project):
1. Check CLAUDE.md for `identity_id` field
2. Check `projects.default_identity_id` in database
3. Fall back to claude-code-unified

See [[Identity System]] for full design.

---

### 4. Database Logging

**File**: `session_startup_hook.py` (lines 81-85)

```python
cursor.execute("""
    INSERT INTO claude.sessions
    (session_id, identity_id, project_name, session_start, created_at)
    VALUES (%s, %s, %s, NOW(), NOW())
    RETURNING session_id
""", (session_id, identity, project_name))
```

**What's logged**:
- `session_id`: New UUID
- `identity_id`: claude-code-unified (current) or per-project (target)
- `project_name`: From cwd
- `session_start`: Current timestamp

**What's NOT logged yet**:
- tasks_completed, learnings_gained (filled at session end)
- session_summary (generated at session end)

---

### 5. Context Loading

The hook loads saved state from previous sessions:

#### A. Session State (singleton per project)

```sql
SELECT todo_list, current_focus, next_steps, pending_actions
FROM claude.session_state
WHERE project_name = $PROJECT;
```

**Returns**:
- **todo_list**: Last saved TodoWrite state (JSONB)
- **current_focus**: What you were working on
- **next_steps**: What to do next (JSONB array)
- **pending_actions**: Deferred tasks

#### B. Recent Sessions

```sql
SELECT session_summary
FROM claude.sessions
WHERE project_name = $PROJECT
ORDER BY session_start DESC
LIMIT 3;
```

**Purpose**: Show recent work for context

#### C. Pending Messages

```sql
SELECT *
FROM claude.messages
WHERE (to_project = $PROJECT OR to_project IS NULL)
  AND status = 'pending'
ORDER BY created_at DESC;
```

**Purpose**: Check if other Claude instances sent messages

#### D. Due Reminders

```sql
SELECT *
FROM claude.reminders
WHERE trigger_condition MET
  AND status = 'pending';
```

---

### 6. CLAUDE.md Loading

Claude Code automatically reads two CLAUDE.md files:

#### Global: `~/.claude/CLAUDE.md`

**Location**: `C:\Users\johnd\.claude\CLAUDE.md`

**Contains**:
- Platform/environment info (Windows 11, Git Bash)
- Knowledge Vault location
- Database connection details
- MCP server list
- Global procedures (session start/end)
- Code style preferences

#### Project: `{project}/CLAUDE.md`

**Location**: `C:\Projects\{project}\CLAUDE.md`

**Contains**:
- Project-specific info (ID, status, phase)
- Project procedures
- Coding standards
- Key procedures

---

### Session Start Sequence Diagram

```
User                 Launcher            Claude Code         Hook Script         Database
 |                      |                      |                   |                  |
 | Click "Launch"       |                      |                   |                  |
 |--------------------->|                      |                   |                  |
 |                      |                      |                   |                  |
 |                      | wt.exe -d {path}     |                   |                  |
 |                      | claude               |                   |                  |
 |                      |--------------------->|                   |                  |
 |                      |                      |                   |                  |
 |                      |                      | SessionStart      |                  |
 |                      |                      | event fires       |                  |
 |                      |                      |------------------>|                  |
 |                      |                      |                   |                  |
 |                      |                      |                   | INSERT session   |
 |                      |                      |                   |----------------->|
 |                      |                      |                   |                  |
 |                      |                      |                   | session_id       |
 |                      |                      |                   |<-----------------|
 |                      |                      |                   |                  |
 |                      |                      |                   | SELECT           |
 |                      |                      |                   | session_state    |
 |                      |                      |                   |----------------->|
 |                      |                      |                   |                  |
 |                      |                      |                   | todo_list, focus |
 |                      |                      |                   |<-----------------|
 |                      |                      |                   |                  |
 |                      |                      |                   | SELECT messages  |
 |                      |                      |                   |----------------->|
 |                      |                      |                   |                  |
 |                      |                      |                   | pending messages |
 |                      |                      |                   |<-----------------|
 |                      |                      |                   |                  |
 |                      |                      | additionalContext |                  |
 |                      |                      | + systemMessage   |                  |
 |                      |                      |<------------------|                  |
 |                      |                      |                   |                  |
 | "Session Started"    |                      |                   |                  |
 | context displayed    |                      |                   |                  |
 |<---------------------|----------------------|                   |                  |
```

---

## During Session

### State Persistence (session_state)

As you work, Claude can persist state for future sessions:

```sql
INSERT INTO claude.session_state
(project_name, todo_list, current_focus, updated_at)
VALUES ($PROJECT, $TODO_JSON, $FOCUS, NOW())
ON CONFLICT (project_name)
DO UPDATE SET
    todo_list = EXCLUDED.todo_list,
    current_focus = EXCLUDED.current_focus,
    updated_at = NOW();
```

**When**:
- After completing major tasks
- When using TodoWrite tool
- At session end (via `/session-end`)

---

### MCP Usage Tracking

**Hook**: PostToolUse (every MCP tool call)

**File**: `scripts/mcp_usage_logger.py`

**Triggered by**: Any MCP tool call (`mcp__*`)

```
Claude calls mcp__postgres__execute_sql
         |
         v
PostToolUse hook fires
         |
         v
mcp_usage_logger.py runs
         |
         v
INSERT INTO claude.mcp_usage
(mcp_server, tool_name, session_id, success, ...)
```

**Current Issue**: ⚠️ Hook configured but not working (only 13 records, none since Dec 20)

**Root cause**: `CLAUDE_SESSION_ID` not exported to environment by session hook

---

### TodoWrite Integration

The TodoWrite tool updates `session_state`:

```
User: TodoWrite tool call
      {todos: [...]}
         |
         v
Tool creates JSON structure
         |
         v
UPSERT claude.session_state
SET todo_list = $JSON
WHERE project_name = $PROJECT
```

**Loaded at next session start** from session_state.todo_list

---

## Session End

### Manual End (/session-end command)

**File**: `.claude/commands/session-end.md`

When you run `/session-end`, the skill does:

#### 1. Generate Summary

Uses your conversation history to create `session_summary`:
- What was accomplished
- What you learned
- Challenges encountered

#### 2. Save State

```sql
-- Save session state
INSERT INTO claude.session_state
(project_name, todo_list, current_focus, next_steps, updated_at)
VALUES (...)
ON CONFLICT (project_name)
DO UPDATE SET ...;

-- Update session record
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = $SUMMARY,
    tasks_completed = $TASKS_ARRAY,
    learnings_gained = $LEARNINGS_ARRAY,
    challenges_encountered = $CHALLENGES_ARRAY
WHERE session_id = $SESSION_ID;
```

#### 3. Knowledge Capture

Optionally creates knowledge note in vault:
- Location: `knowledge-vault/00-Inbox/`
- Format: Markdown with frontmatter
- Content: Session insights, patterns discovered

---

### Automatic End (SessionEnd hook)

**File**: `.claude/hooks.json` (lines 86-108)

```json
"SessionEnd": [{
  "hooks": [
    {"command": "cleanup_mcp_processes.py"},
    {"command": "check_doc_updates.py"},
    {"prompt": "Run /session-end to preserve state"}
  ]
}]
```

**When**: When Claude Code terminates (Ctrl+C, window close, etc.)

**Purpose**:
- Cleanup: Kill orphaned MCP processes
- Reminder: Prompt to save state (if not already done)
- Documentation: Check if docs need updating

---

### Session End Sequence Diagram

```
User              Claude            Skill              Database
 |                   |                 |                   |
 | /session-end      |                 |                   |
 |------------------>|                 |                   |
 |                   |                 |                   |
 |                   | Analyze history |                   |
 |                   | Generate summary|                   |
 |                   |---------------->|                   |
 |                   |                 |                   |
 |                   |                 | UPSERT            |
 |                   |                 | session_state     |
 |                   |                 |------------------>|
 |                   |                 |                   |
 |                   |                 | UPDATE sessions   |
 |                   |                 | SET session_end,  |
 |                   |                 | summary, tasks    |
 |                   |                 |------------------>|
 |                   |                 |                   |
 |                   | "State saved"   |                   |
 |<------------------|                 |                   |
 |                   |                 |                   |
 | Close terminal    |                 |                   |
 |------------------>|                 |                   |
 |                   |                 |                   |
 |                   | SessionEnd      |                   |
 |                   | hook fires      |                   |
 |                   |---------------->|                   |
 |                   |                 |                   |
 |                   |                 | Cleanup MCP       |
 |                   |                 | Check docs        |
```

---

## Session Resume (Next Day)

When you start Claude again on the same project:

### Flow

```
1. SessionStart hook fires
   ↓
2. Loads session_state (todo_list, current_focus, next_steps)
   ↓
3. Displays context:
   "HERE'S WHERE WE LEFT OFF:
    Focus: Building governance system
    NEXT STEPS: 1. Complete hooks... 2. Test deployment...
    PENDING TODOS: [list]"
   ↓
4. User runs /session-resume (optional, for more detail)
   ↓
5. Shows recent sessions, uncommitted files, pending messages
```

### /session-resume Command

**Purpose**: Quick context at session start

**Shows**:
- Last session summary
- Next steps (top 3)
- Uncommitted files count
- Pending messages count

**File**: `.claude/commands/session-resume.md`

---

## Complete Lifecycle Flow

```
                        ┌──────────────┐
                        │ User launches│
                        │    Claude    │
                        └──────┬───────┘
                               │
                        ┌──────▼──────────┐
                        │  SessionStart   │
                        │  Hook Fires     │
                        └──────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼─────┐         ┌──────▼──────┐      ┌───────▼────────┐
  │ Create    │         │  Load saved │      │ Load CLAUDE.md │
  │ session   │         │    state    │      │   (global +    │
  │  record   │         │ (todo, focus)│      │    project)    │
  └─────┬─────┘         └──────┬──────┘      └───────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │ Display context │
                        │  to user        │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │  User works     │
                        │  (hours/days)   │
                        └──────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼─────┐         ┌──────▼──────┐      ┌───────▼────────┐
  │ TodoWrite │         │  MCP tools  │      │  Agent spawns  │
  │ persists  │         │  tracked    │      │    tracked     │
  │   state   │         │(mcp_usage)  │      │(agent_sessions)│
  └─────┬─────┘         └──────┬──────┘      └───────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │ /session-end    │
                        │   (manual)      │
                        └──────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼─────┐         ┌──────▼──────┐      ┌───────▼────────┐
  │ Generate  │         │   Update    │      │  Capture       │
  │  summary  │         │  session    │      │ knowledge      │
  │           │         │   record    │      │  (optional)    │
  └─────┬─────┘         └──────┬──────┘      └───────┬────────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                        ┌──────▼──────────┐
                        │  User closes    │
                        │    terminal     │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │  SessionEnd     │
                        │  Hook Fires     │
                        └──────┬──────────┘
                               │
                        ┌──────▼──────────┐
                        │ Cleanup MCP     │
                        │   processes     │
                        └─────────────────┘
```

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

- [[Database Schema - Core Tables]] - sessions, session_state tables
- [[Identity System]] - How identity is determined
- [[Session Quick Reference]] - Single-page cheat sheet
- [[Family Rules]] - Session rules (mandatory)
- [[Session User Stories]] - Traced examples

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/40-Procedures/Session Lifecycle.md
