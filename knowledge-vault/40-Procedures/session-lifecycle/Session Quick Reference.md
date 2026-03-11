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

### 1. You Are Logged Automatically

The `SessionStart` hook (`session_startup_hook.py`) runs automatically:
- Creates record in `claude.sessions` table
- Assigns you a `session_id` (UUID)
- Links to `identity_id` (currently: claude-code-unified)
- Records `project_name` (from current directory)

### 2. Context Is Injected Automatically

The `UserPromptSubmit` hook (`rag_query_hook.py`) injects context when you ask:
- "where was I" / "what was I working on"
- "my todos" / "what's next"
- "resume" / "last session"

This queries `claude.todos`, `claude.sessions`, `claude.session_state` automatically.

### 3. Or Use /session-resume

Run `/session-resume` to explicitly show:
- Last session summary
- Current focus
- Active todos (with priorities)
- Pending messages
- Uncommitted files

---

## Key Tables Reference

| Need to... | Table | Key Columns |
|------------|-------|-------------|
| Log my session | `sessions` | session_id, identity_id, project_name, session_start |
| Persist state | `session_state` | project_name, current_focus, next_steps |
| Track todos | `todos` | project_id, content, status, priority |
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

### Check Active Todos

```sql
SELECT content, status, priority
FROM claude.todos t
JOIN claude.projects p ON t.project_id = p.project_id
WHERE p.project_name = '$PROJECT'
  AND t.status IN ('pending', 'in_progress')
ORDER BY priority;
```

### Check Pending Messages

```sql
SELECT * FROM claude.messages
WHERE status = 'pending'
  AND (to_project = '$PROJECT' OR to_project IS NULL);
```

---

## At Session End

### Run /session-end

**Why**: Saves summary, captures learnings, persists state

**What it does**:
1. Updates `claude.sessions` with summary
2. Saves tasks_completed, learnings_gained
3. Optionally updates `claude.session_state`

**When to run**:
- End of work day
- Before long break
- After major milestone

---

## Quick Session Workflow

```
1. Launch Claude → SessionStart hook fires
   ├─ Creates session record
   ├─ Loads saved state
   └─ Shows context

2. Ask "where was I?" → RAG hook injects context
   ├─ Queries claude.todos
   ├─ Queries claude.sessions
   └─ Queries claude.session_state

3. Work → State tracked via TodoWrite tool
   ├─ Updates claude.todos
   └─ Maintains session visibility

4. End → /session-end
   ├─ Generates summary
   ├─ Updates sessions record
   └─ Saves session_state
```

---

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/session-start` | Manual start (usually auto via hook) |
| `/session-resume` | Database-driven context display |
| `/session-end` | Save state and summary |
| `/session-commit` | Session end + git commit |
| `/session-status` | Quick read-only status check |

---

## Related Documents

- [[Session Lifecycle - Overview]] - Complete detailed guide
- [[Session Handoff - Database Approach]] - Database-driven context
- [[session End]] - End session details
- [[Slash command's]] - All slash commands
- [[Family Rules]] - Mandatory procedures

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2026-01-07
**Location**: knowledge-vault/40-Procedures/Session Quick Reference.md
