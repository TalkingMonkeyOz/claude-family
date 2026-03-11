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

# Session Lifecycle - Session Start

**Purpose**: Detailed guide to the session startup process and hook configuration.
**Audience**: Claude instances and developers maintaining the system

See [[Session Lifecycle - Overview]] for complete context.

---

## Hook Trigger (SessionStart Event)

**File**: `C:\Projects\claude-family\.claude\settings.local.json` (hooks section)

```json
"SessionStart": [{
  "hooks": [{
    "type": "command",
    "command": "python \"C:/Projects/claude-family/.claude-plugins/claude-family-core/scripts/session_startup_hook.py\"",
    "timeout": 30,
    "description": "Auto-log session and load state/messages"
  }],
  "once": true
}]
```

**When**: Fires automatically when Claude Code starts
**Purpose**: Creates session record, loads context

**v2.1.0 Feature**: `"once": true` ensures hook runs only once per session (not on every interaction)

> **CRITICAL**: Hooks must be in `settings.local.json`, NOT `hooks.json`! See [[Claude Hooks]] for details.

---

## Project Detection (cwd-based)

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

## Identity Resolution

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

See [[Identity System - Overview]] for full design.

---

## Database Logging

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

## Context Loading

The hook loads saved state from previous sessions:

### A. Session State (singleton per project)

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

### B. Recent Sessions

```sql
SELECT session_summary
FROM claude.sessions
WHERE project_name = $PROJECT
ORDER BY session_start DESC
LIMIT 3;
```

**Purpose**: Show recent work for context

### C. Pending Messages

```sql
SELECT
    message_id::text,
    from_session_id::text,
    to_project,
    message_type,
    subject,
    body,
    priority,
    created_at
FROM claude.messages
WHERE (to_project = $PROJECT OR message_type = 'broadcast')
  AND status = 'pending'
ORDER BY
    CASE priority
        WHEN 'urgent' THEN 1
        WHEN 'normal' THEN 2
        WHEN 'low' THEN 3
    END,
    created_at ASC
LIMIT 10;
```

**Purpose**: Check for messages from other Claude instances and display them in startup context

**What's displayed**:
- Up to 5 messages with full details (priority, type, subject, sender, preview)
- Message IDs for acknowledgment
- Instructions for marking as read/actioned/deferred
- Count of additional messages if >5 pending

**Updated**: 2025-12-31 - Messages are now automatically surfaced in session startup (not just counted)

### D. Due Reminders

```sql
SELECT *
FROM claude.reminders
WHERE trigger_condition MET
  AND status = 'pending';
```

---

## CLAUDE.md Loading

Claude Code automatically reads two CLAUDE.md files:

### Global: `~/.claude/CLAUDE.md`

**Location**: `C:\Users\johnd\.claude\CLAUDE.md`

**Contains**:
- Platform/environment info (Windows 11, Git Bash)
- Knowledge Vault location
- Database connection details
- MCP server list
- Global procedures (session start/end)
- Code style preferences

### Project: `{project}/CLAUDE.md`

**Location**: `C:\Projects\{project}\CLAUDE.md`

**Contains**:
- Project-specific info (ID, status, phase)
- Project procedures
- Coding standards
- Key procedures

---

## Session Start Sequence Diagram

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

## Related Documents

- [[Session Lifecycle - Overview]] - Overview and complete flow
- [[Session Lifecycle - Session End]] - Ending and resuming sessions
- [[Session Lifecycle - Reference]] - Key tables, troubleshooting, best practices
- [[Database Schema - Core Tables]] - sessions table details
- [[Identity System - Overview]] - How identity is determined

---

**Version**: 2.2 (Updated hooks location to settings.local.json, added once:true)
**Created**: 2025-12-26
**Updated**: 2026-01-08
**Location**: knowledge-vault/40-Procedures/Session Lifecycle - Session Start.md
