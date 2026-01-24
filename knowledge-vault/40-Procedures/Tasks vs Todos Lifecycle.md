---
title: Tasks vs Todos Lifecycle
created: 2026-01-24
updated: 2026-01-24
tags: [tasks, todos, session-management, workflow]
category: procedure
status: active
projects: [claude-family]
---

# Tasks vs Todos Lifecycle

## Overview

Claude Code has two work-tracking systems that serve different purposes:

| System | Scope | Persistence | Purpose |
|--------|-------|-------------|---------|
| **Tasks** | Session | In-memory | Track current session work |
| **Todos** | Cross-session | Database (`claude.todos`) | Persist incomplete work |

## The Two-Tier System

```
┌─────────────────────────────────────────────────────────────────┐
│                           TASKS                                  │
│         (Session-scoped, in-memory, ephemeral)                  │
│                                                                  │
│   Tools: TaskCreate, TaskUpdate, TaskList                       │
│   Lifecycle: Created → in_progress → completed (or abandoned)  │
│   Lost on: Session end, crash, restart                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                     /session-end converts
                     incomplete tasks to:
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                           TODOS                                  │
│         (Cross-session, database, persistent)                   │
│                                                                  │
│   Tools: TodoWrite → claude.todos (via todo_sync_hook.py)       │
│   Lifecycle: Synced to DB on every TodoWrite call               │
│   Survives: Session end, crash, restart                         │
└─────────────────────────────────────────────────────────────────┘
```

## Full Lifecycle

### Phase 1: Session Start

```
SessionStart hook fires
    ↓
Load incomplete Todos from claude.todos
    ↓
Show to user: "You have 7 pending todos"
    ↓
TaskList = empty (fresh session)
```

### Phase 2: User Input

```
User: "fix bug X, update docs, refactor Z"
    ↓
Input Processing Protocol triggers
    ↓
Claude uses TaskCreate:
  - Task #1: Fix bug X (pending)
  - Task #2: Update docs (pending)
  - Task #3: Refactor Z (pending)
```

### Phase 3: Working Session

```
Claude starts work
    ↓
TaskUpdate #1 → in_progress
    ↓
Work on Task #1...
    ↓
TaskUpdate #1 → completed
    ↓
User: "leave task 3 till later"
    ↓
Task #3 stays pending
```

### Phase 4: Session End

```
/session-end command
    ↓
Check TaskList for incomplete tasks:
  - Task #2: Update docs (pending) ← INCOMPLETE
  - Task #3: Refactor Z (pending) ← INCOMPLETE
    ↓
For each incomplete task:
  - Fuzzy match vs existing Todos
  - If no match: TodoWrite → create persistent Todo
    ↓
Normal session end (summary, learnings)
```

### Phase 5: Next Session

```
SessionStart hook fires
    ↓
Load Todos (now includes converted tasks)
    ↓
User sees: "Update docs", "Refactor Z"
    ↓
User picks work → TaskCreate
    ↓
Cycle continues
```

## Tools Reference

### Task Tools (Session-Scoped)

| Tool | Purpose | Example |
|------|---------|---------|
| `TaskCreate` | Add new task | `TaskCreate("Fix login bug", "Details...", "Fixing login bug")` |
| `TaskUpdate` | Change status/details | `TaskUpdate(taskId="1", status="in_progress")` |
| `TaskList` | Show all tasks | `TaskList()` |
| `TaskGet` | Get task details | `TaskGet(taskId="1")` |

### Todo Tools (Persistent)

| Tool | Purpose | Persistence |
|------|---------|-------------|
| `TodoWrite` | Create/update todos | Synced to `claude.todos` via hook |

## Database Schema

### claude.todos

```sql
todo_id UUID PRIMARY KEY
project_id UUID REFERENCES projects
content TEXT NOT NULL
active_form TEXT NOT NULL
status VARCHAR (pending|in_progress|completed|cancelled)
priority INTEGER (1-5)
display_order INTEGER
created_session_id UUID
completed_session_id UUID
is_deleted BOOLEAN DEFAULT false
```

## Common Scenarios

### User Says "Leave This Till Later"

```
User: "leave task 3 till later"
↓
Claude: (no action - task stays pending)
↓
At session end: Task #3 → Todo (persists)
↓
Next session: Todo appears, user can pick it up
```

### Crash Mid-Session

Without crash protection:
```
Tasks in memory → LOST
```

With session_facts (recommended for critical work):
```
store_session_fact("current_task", "Working on auth refactor", "context")
↓
Crash happens
↓
Next session: recall_previous_session_facts() shows what was in progress
```

### Task References a Todo

```
User has Todo: "Refactor auth system"
↓
User: "work on that auth refactor"
↓
Claude: TaskCreate (with reference in description)
↓
Work through task...
↓
TaskUpdate → completed
↓
At session end: Source Todo marked completed (if Task was completed)
```

## Best Practices

1. **Use Tasks for session work** - Break user requests into Tasks
2. **Use Todos for deferred work** - Don't create Todos mid-session unless explicitly persisting
3. **Run /session-end** - Always run before closing to persist incomplete work
4. **Use session_facts for crash safety** - Store critical context that shouldn't be lost

## Related

- [[Core Protocol Injection]] - Input processing protocol
- [[Session Lifecycle - Session End]] - Full session end workflow
- [[Session Handoff - Database Approach]] - How session state persists

---

**Version**: 1.0
**Created**: 2026-01-24
**Updated**: 2026-01-24
**Location**: knowledge-vault/40-Procedures/Tasks vs Todos Lifecycle.md
