---
title: Tasks vs Todos Lifecycle
created: 2026-01-24
updated: 2026-02-09
tags: [tasks, todos, session-management, workflow, hooks]
category: procedure
status: active
projects: [claude-family]
---

# Tasks vs Todos Lifecycle

## Overview

Claude Code has two work-tracking systems. **Both sync to `claude.todos` via hooks.**

| System | Scope | Storage | Sync Mechanism |
|--------|-------|---------|----------------|
| **Tasks** (TaskCreate/Update/List) | Session | In-memory | `task_sync_hook.py` → claude.todos (immediate) |
| **Todos** (TodoWrite) | Cross-session | Database | `todo_sync_hook.py` → claude.todos (immediate) |

**Key insight**: Tasks are the primary work tracker. They sync to the DB immediately via PostToolUse hooks - NOT at session end.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  TASK DISCIPLINE ENFORCEMENT (PreToolUse)                     │
│  task_discipline_hook.py gates Write/Edit/Task                │
│  Checks: task map file exists + session_id matches            │
└──────────────────────┬───────────────────────────────────────┘
                       │ blocks until TaskCreate called
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  TASK CREATION (Claude in-memory)                             │
│  TaskCreate → in-memory task list (survives /compact)         │
│  TaskUpdate → status changes (in_progress, completed)         │
│  TaskList   → view all tasks                                  │
└──────────────────────┬───────────────────────────────────────┘
                       │ PostToolUse hook fires
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  DB SYNC (task_sync_hook.py)                                  │
│  TaskCreate → INSERT claude.todos (with duplicate detection)  │
│  TaskUpdate → UPDATE claude.todos status                      │
│  Writes task map: %TEMP%/claude_task_map_{project}.json       │
│  Map includes _session_id for session scoping                 │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  DATABASE (claude.todos)                                      │
│  Source of truth for cross-session persistence                 │
│  Loaded at session start by session_startup_hook               │
│  Preserved across /compact by precompact_hook                  │
└──────────────────────────────────────────────────────────────┘
```

## Hook Chain (Execution Order)

### On TaskCreate (PostToolUse)
1. `task_sync_hook.py` fires
2. Extracts task number from `tool_response` (JSON: `{"task": {"id": "4"}}`)
3. Checks for duplicate todos (substring + fuzzy match, 75% threshold)
4. If match found: links task to existing todo (no INSERT)
5. If no match: INSERTs new todo into `claude.todos`
6. Saves task# → todo_id mapping to temp file (with `_session_id`)

### On TaskUpdate (PostToolUse)
1. `task_sync_hook.py` fires
2. Looks up todo_id from task map file
3. UPDATEs `claude.todos` status (completed, deleted, in_progress, etc.)

### On Write/Edit/Task (PreToolUse)
1. `task_discipline_hook.py` fires FIRST in chain
2. Reads task map file
3. Checks `_session_id` matches current session
4. If match + tasks exist → **allow** (other hooks continue)
5. If stale or empty → **deny** (blocks the tool call)

## File Locations

| Component | Path |
|-----------|------|
| Task sync hook | `scripts/task_sync_hook.py` |
| Task discipline hook | `scripts/task_discipline_hook.py` |
| Todo sync hook | `scripts/todo_sync_hook.py` |
| Session startup | `.claude-plugins/claude-family-core/scripts/session_startup_hook.py` |
| PreCompact hook | `scripts/precompact_hook.py` |
| Task map file | `%TEMP%/claude_task_map_{project}.json` |
| Hook config (generated) | `.claude/settings.local.json` |
| Hook config (source) | `claude.config_templates` (template_id=1, hooks-base) |

## Session Lifecycle

### Session Start
```
SessionStart hook fires
    ↓
Load incomplete todos from claude.todos
    ↓
Display: "Active Todos: 7 total (2 in progress, 5 pending)"
    ↓
TaskList = empty (fresh session, no in-memory tasks yet)
Task map = stale from previous session (discipline hook will block)
```

### First User Request
```
User: "fix bug X, update docs"
    ↓
Core Protocol injection (RAG hook): "TaskCreate for EACH action"
    ↓
Claude calls TaskCreate("Fix bug X", ...)
    ↓
PostToolUse: task_sync_hook inserts todo + writes map with _session_id
    ↓
Claude calls TaskCreate("Update docs", ...)
    ↓
PostToolUse: task_sync_hook inserts todo + updates map
    ↓
Task map now has 2 entries + current _session_id
    ↓
Discipline hook will ALLOW Write/Edit/Task from now on
```

### Working Phase
```
TaskUpdate(#1, status="in_progress")
    ↓
PostToolUse: task_sync_hook UPDATEs claude.todos status
    ↓
Claude writes code (discipline hook allows - session matches)
    ↓
TaskUpdate(#1, status="completed")
    ↓
PostToolUse: task_sync_hook sets completed_at, completed_session_id
```

### Context Compaction
```
/compact or auto-compact
    ↓
PreCompact hook injects: active todos, features, session state
    ↓
Compaction preserves task context
    ↓
TaskList survives (built-in, persists across compact)
Task map survives (on disk, not in context)
```

### Session End
```
Session closes (user exits or /session-end)
    ↓
SessionEnd hook auto-closes session in claude.sessions
    ↓
Todos already in DB (synced on every TaskCreate/Update)
    ↓
No conversion needed at session end
    ↓
Next session: Todos reload from claude.todos automatically
```

## Duplicate Detection

`task_sync_hook.py` prevents duplicate todos using two strategies:

| Strategy | How | Example |
|----------|-----|---------|
| **Substring** | One string contains the other (min 20 chars) | "Fix login bug" ⊂ "Fix login bug in auth module" |
| **Fuzzy match** | SequenceMatcher ratio ≥ 75% | "Refactor auth" ≈ "Refactor authentication" |

When a duplicate is found, the task links to the existing todo instead of creating a new one.

## Session Scoping

The task map file includes `_session_id` to prevent stale tasks from a previous session being treated as current tasks.

| Scenario | Map Session | Current Session | Result |
|----------|-------------|-----------------|--------|
| Same session | ABC | ABC | **Allow** |
| New session, stale map | ABC | XYZ | **Deny** (stale) |
| No map file | - | XYZ | **Deny** (no tasks) |
| No session_id available | ABC | (empty) | **Allow** (edge case) |

## Critical Implementation Details

### PostToolUse field name
The hook receives `tool_response` (NOT `tool_output`). This was a bug that prevented task sync from working until 2026-02-09.

### TaskCreate tool_response format
```json
{"task": {"id": "4", "subject": "Fix login bug"}}
```
NOT the text format "Task #4 created successfully".

### PreToolUse deny pattern
Must use exit code 0 + JSON `permissionDecision: "deny"`. Exit code 2 ignores JSON and only shows stderr.

### Config persistence
Settings in `.claude/settings.local.json` are generated from `claude.config_templates` (template_id=1). The hook config is stored in the database and regenerated on SessionStart.

## Database Schema

### claude.todos
```sql
todo_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
project_id UUID NOT NULL REFERENCES claude.projects
created_session_id UUID REFERENCES claude.sessions
completed_session_id UUID REFERENCES claude.sessions
content TEXT NOT NULL          -- Task subject becomes todo content
active_form TEXT NOT NULL      -- Present-continuous form for spinners
status VARCHAR(20)             -- pending, in_progress, completed, cancelled, archived
priority INTEGER DEFAULT 3    -- 1 (critical) to 5 (low)
display_order INTEGER DEFAULT 0
is_deleted BOOLEAN DEFAULT false
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()
completed_at TIMESTAMPTZ       -- Set when status → completed
```

## Related Documents

- [[Core Protocol Injection]] - Task discipline prompt injection
- [[Claude Code Hooks]] - Hook system overview
- [[Config Management SOP]] - How settings.local.json is generated
- [[Session Lifecycle - Overview]] - Full session lifecycle

---

**Version**: 2.0 (Complete rewrite: reflects task_sync_hook.py, discipline enforcement, session scoping)
**Created**: 2026-01-24
**Updated**: 2026-02-09
**Location**: knowledge-vault/40-Procedures/Tasks vs Todos Lifecycle.md
