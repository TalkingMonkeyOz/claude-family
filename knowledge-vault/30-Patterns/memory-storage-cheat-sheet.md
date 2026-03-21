---
projects:
  - claude-family
tags:
  - memory
  - storage
  - persistence
  - session
---

# Memory and Storage Cheat Sheet

**Use this when**: Deciding where to save something during or between sessions.
**Architecture overview**: See [[storage-architecture-guide]] for how the 5 systems (Notepad, Memory, Filing Cabinet, Reference Library, Vault) fit together and WHY each exists.

---

## Decision Table

| I need to...                                           | Use this                                       | Example                                |
| ------------------------------------------------------ | ---------------------------------------------- | -------------------------------------- |
| Save a credential or key for this session              | `store_session_fact(key, value, "credential")` | API key discovered mid-session         |
| Save a config value or endpoint for this session       | `store_session_fact(key, value, "config")`     | DB connection string                   |
| Record a decision made this session                    | `store_session_fact(key, value, "decision")`   | "decided to use approach B"            |
| Note a finding for this session                        | `store_session_fact(key, value, "note")`       | unexpected schema column               |
| Retrieve a session fact by key                         | `recall_session_fact(key)`                     | get back the decision                  |
| Learn a reusable pattern or gotcha for future sessions | `remember(content, "pattern")`                 | psycopg dict_row quirk                 |
| Remember a decision that future Claudes should know    | `remember(content, "decision")`                | "use advance_status not raw UPDATE"    |
| Search what was learned in past sessions               | `recall_memories(query)`                       | "how do I handle workflow transitions" |
| Store structured reference data (API, OData entity)    | `catalog(entity_type, properties)`             | OData entity with fields               |
| Search structured reference data                       | `recall_entities(query, entity_type)`          | find OData entity by name              |
| Save working notes on a component across sessions      | `stash(component, title, content)`             | design decisions for rag-hook          |
| Load component working notes                           | `unstash(component)`                           | resume work on rag-hook                |
| Browse available workfiles                             | `list_workfiles()`                             | see all active components              |
| Track a todo for this session                          | `TodoWrite` (native)                           | task list in current session           |
| Persist a todo to the DB                               | `claude.todos` via task_sync_hook              | automatic on TaskCreate                |
| Track a feature                                        | `create_feature(name, desc)`                   | new capability to build                |
| Track a build task                                     | `add_build_task(feature, name)`                | step within a feature                  |
| Persist session handoff state                          | `stash("session-handoff", date, content)`      | end-of-session stash for next Claude   |
| Record next priorities for next session                | `session_state.next_steps` via `/session-end`  | top 3 items to pick up                 |
| Write session notes mid-session                        | `store_session_notes(content, section)`        | progress tracker, survives compaction  |

---

## Storage by Lifespan

| Lifespan | Mechanism | Survives compaction? | Survives session end? |
|----------|-----------|---------------------|----------------------|
| Current prompt only | Local variable / context | No | No |
| Current session | `store_session_fact` | Yes (injected by PreCompact hook) | No |
| Current session (notes) | `store_session_notes` | Yes | No |
| Next session (priority signal) | `session_state.next_steps` | — | Yes |
| Next session (full handoff) | `stash("session-handoff")` | — | Yes |
| Component work across sessions | `stash(component, title)` | — | Yes (pinned = surfaced at start) |
| Future sessions (patterns) | `remember()` → mid/long tier | — | Yes (Memory system DB) |
| Structured reference data | `catalog()` → entity table | — | Yes (searchable via `recall_entities`) |

---

## Session Lifecycle: What Gets Saved When

### Session Start (automatic)
- Hook logs to `claude.sessions`
- `check_workfiles()` → surfaces active workfiles (Filing Cabinet)
- `surface_entities()` → surfaces cataloged entity types
- If prior state: shows "NEXT PRIORITIES" from `session_state.next_steps`
- If prior state: shows "ACTIVE WORKFILES" from `list_workfiles()`

### During Work (automatic)
- `TodoWrite` → synced to `claude.todos` by `todo_sync_hook.py`
- `TaskCreate/Update` → synced to `claude.todos` + `build_tasks` by `task_sync_hook.py`
- MCP tool calls → logged to `claude.mcp_usage`
- `store_session_fact()` → available for rest of session + survives compaction

### Context Compaction (automatic)
- `precompact_hook.py` injects: active todos, active features, session facts, session notes, pinned workfiles

### Session End (`/session-end` command)
1. Save summary + next_steps → `claude.sessions` + `claude.session_state`
2. Query unfinished tasks → `claude.todos`
3. Stash handoff → `stash("session-handoff", date, task_state + decisions + next_steps)`
4. Extract learnings → `remember()` + `consolidate_memories("session_end")`
5. Close session record

### Session Auto-Close (hook on process exit)
- `session_end_hook.py` closes `claude.sessions` row
- `consolidate_memories()` runs memory lifecycle (promote, decay, archive)

---

## Key Rules

- `store_session_fact` = this session only. `remember` = future sessions. `catalog` = structured data. `stash` = component working notes.
- Quality gate on `remember()`: minimum 80 chars, rejects task-ack junk patterns.
- `stash` UPSERT key is `(project_id, component, title)` — same component+title overwrites; use `mode="append"` to concatenate.
- `is_pinned=True` on a stash entry → auto-surfaced at next session start.
- `session_state.next_steps` is the bridge between `/session-end` and the next session's "NEXT PRIORITIES" display.

---

**Version**: 1.1
**Created**: 2026-03-14
**Updated**: 2026-03-22
**Location**: knowledge-vault/30-Patterns/memory-storage-cheat-sheet.md
