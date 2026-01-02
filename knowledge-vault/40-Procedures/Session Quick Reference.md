---
projects:
  - claude-family
tags:
  - quick-reference
  - session
  - mandatory
  - cheat-sheet
synced: false
---

# Session Quick Reference

**Purpose**: Single-page reference for Claude at session start
**Use when**: Every session begins

Quick answers to: "What session am I in? Where was I? What do I need to log?"

---

## At Session Start

### 1. You Are Logged Automatically ✅

The `SessionStart` hook (`session_startup_hook.py`) runs automatically:
- Creates record in `claude.sessions` table
- Assigns you a `session_id` (UUID)
- Links to `identity_id` (currently: claude-code-unified)
- Records `project_name` (from current directory)

**Your session_id**: Check the additionalContext from hook output (not currently visible)

---

### 2. Find Your Identity

**Current** (hardcoded):
```
identity: claude-code-unified
identity_id: ff32276f-9d05-4a18-b092-31b54c82fff9
```

**Target** (per-project):
Check CLAUDE.md header for:
```yaml
---
identity: claude-ato-agent
identity_id: XXXX-XXXX-XXXX
---
```

---

### 3. Check Where You Left Off

The hook loads `session_state` automatically. Look for:

**Focus**: What was I working on last?
**Todo List**: What's pending?
**Next Steps**: What should I do next?
**Pending Actions**: What needs follow-up?

---

## Key Tables Reference

| Need to... | Table | Key Columns |
|------------|-------|-------------|
| Log my session | `sessions` | session_id, identity_id, project_name, session_start |
| Persist state | `session_state` | project_name, todo_list, current_focus |
| Track tool use | `mcp_usage` | session_id, tool_name, success |
| Spawn agent | `agent_sessions` | agent_type, task_description, success |
| Send message | `messages` | to_project, body, status |

---

## Essential Queries

### Check Your Recent Sessions

```sql
SELECT session_start, session_summary
FROM claude.sessions
WHERE project_name = '$PROJECT'
ORDER BY session_start DESC
LIMIT 5;
```

### Check Pending Messages

```sql
SELECT * FROM claude.messages
WHERE status = 'pending'
  AND (to_project = '$PROJECT' OR to_project IS NULL);
```

### Get Saved State

```sql
SELECT todo_list, current_focus, next_steps
FROM claude.session_state
WHERE project_name = '$PROJECT';
```

### Update Session State

```sql
INSERT INTO claude.session_state
(project_name, todo_list, current_focus, updated_at)
VALUES ('$PROJECT', '$TODO_JSON', '$FOCUS', NOW())
ON CONFLICT (project_name)
DO UPDATE SET
    todo_list = EXCLUDED.todo_list,
    current_focus = EXCLUDED.current_focus,
    updated_at = NOW();
```

---

## At Session End

### Run /session-end

**Why**: Saves summary, captures learnings, persists state

**What it does**:
1. Generates `session_summary` from conversation
2. Extracts `tasks_completed`, `learnings_gained`
3. Updates `claude.sessions` record
4. Saves `session_state` (todo_list, focus, next_steps)

**When to run**:
- End of work day
- Before long break
- After major milestone
- Multiple times per session (to checkpoint)

---

## Environment Variables

| Variable | Value | Used By |
|----------|-------|---------|
| `CLAUDE_SESSION_ID` | (UUID) | ⚠️ NOT SET (should be by hook) |
| `CLAUDE_IDENTITY_ID` | ff32276f... | Session hook, MCP loggers |
| `CLAUDE_PROJECT_NAME` | (from cwd) | MCP loggers |
| `DATABASE_URI` | postgresql://... | All database scripts |

**Issue**: `CLAUDE_SESSION_ID` not exported → MCP usage logging broken

---

## Common Tasks

### Check Active Sessions

```sql
SELECT session_id::text, project_name, session_start,
       AGE(NOW(), session_start) as duration
FROM claude.sessions
WHERE session_end IS NULL
  AND session_start >= NOW() - INTERVAL '24 hours';
```

### Get Project Info

```sql
SELECT project_name, phase, status
FROM claude.projects
WHERE project_name = '$PROJECT';
```

### Check Column Valid Values

```sql
SELECT valid_values
FROM claude.column_registry
WHERE table_name = 'TABLE_NAME'
  AND column_name = 'COLUMN_NAME';
```

---

## Troubleshooting

### Session Not Logged?

```sql
-- Check if session exists
SELECT * FROM claude.sessions
ORDER BY session_start DESC LIMIT 1;
```

If empty: Database connection failed. Check `$DATABASE_URI`

### State Not Loading?

```sql
-- Check session_state exists
SELECT * FROM claude.session_state
WHERE project_name = '$PROJECT';
```

If empty: No state saved yet OR project_name mismatch

### Identity NULL?

```sql
-- Check your last session
SELECT identity_id FROM claude.sessions
ORDER BY session_start DESC LIMIT 1;
```

If NULL: `CLAUDE_IDENTITY_ID` not set, DEFAULT_IDENTITY_ID missing

---

## Quick Session Workflow

```
1. Launch Claude → SessionStart hook fires
   ├─ Creates session record
   ├─ Loads saved state
   └─ Shows context

2. Work → State automatically tracked
   ├─ TodoWrite → Updates session_state
   ├─ MCP tools → Logged to mcp_usage (broken)
   └─ Agent spawns → Logged to agent_sessions

3. End → /session-end
   ├─ Generates summary
   ├─ Updates sessions record
   └─ Saves session_state
```

---

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/session-start` | Manually log session (usually auto) |
| `/session-end` | Save state and summary |
| `/session-resume` | Show context at session start |
| `/session-commit` | Session end + git commit |

---

## Related Documents

- [[Session Lifecycle - Overview]] - Complete detailed guide
- [[Database Schema - Core Tables]] - Table structures
- [[Identity System - Overview]] - How identity works
- [[Family Rules]] - Mandatory procedures

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/40-Procedures/Session Quick Reference.md
