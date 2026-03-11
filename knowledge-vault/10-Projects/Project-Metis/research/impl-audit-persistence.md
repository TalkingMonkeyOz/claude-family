---
projects:
- claude-family
- project-metis
tags:
- research
- implementation-audit
- task-persistence
- session
- precompact
synced: false
---

# Implementation Audit: Persistence Layer

Back to: [index](impl-audit-index.md)

Covers: precompact hook, task/todo sync, session startup.

---

## Precompact Hook — precompact_hook.py

**Source file:** `scripts/precompact_hook.py` (330 lines)

### What survives compaction

Six sources in priority order:

```
P0: in_progress todos (up to 5)                   — always included
P1: session_state.current_focus + next_steps       — only if explicitly saved
P2: in_progress features (name + task counts)      — up to 3
P3: session_facts (decision/reference/note, non-sensitive, up to 5)
P3.5: pinned workfiles (component name + title only, no content)
P4: session_notes.md (raw file read, if exists)
```

Budget: `MAX_PRECOMPACT_TOKENS = 2000` (~8000 chars).

`_apply_context_budget()` (lines 60-101): sorts sections by priority, greedily
adds until budget exhausted, tries to fit a partial section if 200+ chars remain.
Clean implementation with explicit logging of what was trimmed.

### Pinned workfiles (P3.5 — lines 210-234)

Only component name and title are stored, not content. Post-compaction instructions
say "Use unstash(component) to load full content." This is advisory text inside
`<claude-context-refresh>` XML — no enforcement that Claude actually does it.

### What the precompact cannot save you from

If P0 (in_progress todos) is empty AND P2 (in_progress features) is empty AND P3
(session facts) is empty, the output is nearly empty — just the recovery instructions.
This happens on exploratory sessions where Claude works without creating tasks.

`session_state.current_focus` (P1) is only useful if Claude explicitly called a
checkpoint. The `task_sync_hook.py` auto-checkpoints on task completion (upserts
`session_state.current_focus` with "Completed: {task_subject}") but if the last
action before compaction was not task completion, focus is stale.

**Works well:** Priority budget allocation is correct. P0 in-progress todos are
exactly what Claude needs post-compaction.

**Fragile:** P1 focus requires explicit prior checkpointing. Recovery is advisory only.
Session notes file is a raw write with no structure.

---

## Task/Todo Sync — task_sync_hook.py

**Source file:** `scripts/task_sync_hook.py` (609 lines)

### How the sync works

`PostToolUse` hook fires on `TaskCreate` and `TaskUpdate`.

On `TaskCreate` (lines 300-386):
1. Checks for an existing similar todo (substring containment >= 20 chars, or
   SequenceMatcher ratio >= 0.75 against last 50 pending/in_progress todos)
2. Inserts new todo or increments `restore_count` on existing
3. Attempts to match to an existing `build_task` by name similarity (same 0.75 threshold)
4. Stores `{todo_id, bt_code?, bt_task_id?}` in task map file

On `TaskUpdate` (lines 389-551):
- Updates todo status. If bridged to build_task, updates build_task status and inserts audit_log.
- On completion, checks if all feature build_tasks are done.
- Auto-checkpoint: upserts `session_state.current_focus` with "Completed: {task_subject}".

### The task map file

Path: `%TEMP%\claude_task_map_{project_name}.json`

Maps Claude's internal task numbers to DB todo_ids. Uses `msvcrt.locking` for
concurrent write safety (Windows only — line 115). If the lock file approach fails,
falls back to a direct write (line 149).

The `_session_id` field in the map is checked by the discipline hook to validate
tasks were created in the current session.

### Why task persistence is fundamentally limited

Claude Code's native task list is session-scoped. Each session gets a new
`~/.claude/tasks/<session-id>/` directory. Completed tasks are deleted from disk.

The sync hook is a shim over this design:

1. Task map in `%TEMP%` is lost on reboot
2. If map is lost, `handle_task_update` (line 409) cannot find `todo_id` and skips
   DB updates: "No todo mapping for task #{task_id} - may be pre-existing"
3. Compaction orphans tasks: in-progress tasks before compaction appear as duplicates
   post-compaction. `restore_count` tracks this (line 338) but does not fix it.
4. `CLAUDE_CODE_TASK_LIST_ID` shared mode requires env var in both `.env` and the
   launcher .bat — missing from either silently breaks cross-session persistence.

**Works well:** Build-task bridging (fuzzy match) is clever. Auto-checkpoint on
completion provides a passive breadcrumb. File locking is correct.

**Fragile:** Task map is not durable across reboots. Compaction orphaning is a known
bug. Shared list mode has two-location env var dependency.

---

## Session Startup Hook — session_startup_hook_enhanced.py

**Source file:** `scripts/session_startup_hook_enhanced.py` (494 lines)

### What loads at startup

Hook emits `additionalContext` with:
1. Health banner (timestamp, project, health status)
2. Session ID from DB insert
3. Auto-archive count (stale todos cleaned)
4. Outstanding todo count + reminder to call `start_session()`
5. Memory consolidation summary (if periodic ran)
6. System staleness warning (if `detect_all_staleness()` finds issues)

Full context loading is deferred to the `start_session()` MCP tool by design.

### 60-second dedup guard (lines 127-144)

Before inserting, queries for a session from the same project and identity_id
started within the last 60 seconds. If found, reuses the existing session_id.

Gap: `identity_id` is hardcoded as `'claude-code-unified'` (line 412). Two Claude
Code windows opening the same project within 60 seconds share a session_id. In
practice rare, but session facts stored in window A would be visible in window B.

### Duplicate consolidation implementation (lines 256-324)

Periodic consolidation runs the same SQL as Phase 2+3 of `tool_consolidate_memories`
directly — not by calling the function. Thresholds:
```
times_applied >= 3, confidence_level >= 80, access_count >= 5
```
These exist in two places (`server.py:2102` and `session_startup_hook_enhanced.py:289`)
and can diverge if one is updated without the other.

### Fallback session replay (lines 327-391)

If `session_end_hook` could not write to DB, it writes a JSONL fallback. Startup
replays these via `replay_fallback("session_end", _close_session)`. Clean implementation,
fails silently if the fallback module is missing.

### What is missing at startup

- No pinned workfiles are surfaced. The user has no reminder of what was being worked
  on from the previous session without calling `start_session()`.
- `detect_all_staleness()` call (line 462) is in a broad `except` — failure is silently
  swallowed to a warning log.
- Outstanding todo count is reported as a number only — Claude cannot act without a
  follow-up `start_session()` call to get the actual text.

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/impl-audit-persistence.md
