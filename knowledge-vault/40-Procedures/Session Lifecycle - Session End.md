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

# Session Lifecycle - Session End

**Purpose**: Guide to session ending, state persistence, and session resumption.
**Audience**: Claude instances and developers maintaining the system

See [[Session Lifecycle - Overview]] for complete context.

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

## Manual End (/session-end command)

**File**: `.claude/commands/session-end.md`

When you run `/session-end`, the skill does:

### 1. Generate Summary

Uses your conversation history to create `session_summary`:
- What was accomplished
- What you learned
- Challenges encountered

### 2. Save State

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

### 3. Knowledge Capture

Optionally creates knowledge note in vault:
- Location: `knowledge-vault/00-Inbox/`
- Format: Markdown with frontmatter
- Content: Session insights, patterns discovered

---

## Automatic End (SessionEnd hook)

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

## Session End Sequence Diagram

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

## Related Documents

- [[Session Lifecycle - Overview]] - Overview and complete flow
- [[Session Lifecycle - Session Start]] - Startup sequence and configuration
- [[Session Lifecycle - Reference]] - Key tables, troubleshooting, best practices
- [[Database Schema - Core Tables]] - sessions, session_state table details

---

**Version**: 2.0 (split 2025-12-26)
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/40-Procedures/Session Lifecycle - Session End.md
