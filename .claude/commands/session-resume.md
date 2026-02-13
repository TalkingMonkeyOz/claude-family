**QUICK SESSION RESUME - Database-Driven Context with Task Restoration**

Single consolidated call to `start_session()`, then restore outstanding tasks as live TaskCreate entries.

---

## Execute These Steps

### Step 1: Load Context (Single Call)

Use `mcp__project-tools__start_session` with the current project name.

This returns: project info, session state, todos (with `active_form` and `status`), active features, ready tasks, pending messages.

### Step 2: Git Status

```bash
git status --short
```

### Step 3: Restore Tasks

For each todo returned by `start_session()` (both `in_progress` and `pending` buckets):

1. Call `TaskCreate` with:
   - `subject`: the todo's `content`
   - `activeForm`: the todo's `active_form`
   - `description`: the todo's `content`
2. If the todo's `status` was `in_progress`:
   - Call `TaskUpdate(taskId=<new_id>, status="in_progress")`

The `task_sync_hook` will match these to existing DB todos via duplicate detection (75% similarity) and reuse the existing `todo_id` rather than creating duplicates.

### Step 4: Display Resume Box

```
+==================================================================+
|  SESSION RESUME - {project_name}                                 |
+==================================================================+
|  Last Session: {date} - {summary}                                |
|  Focus: {current_focus}                                          |
+------------------------------------------------------------------+
|  RESTORED TASKS ({count}):                                       |
|  In Progress:                                                    |
|    > {in_progress items}                                         |
|  Pending:                                                        |
|    [ ] {pending items}                                           |
+------------------------------------------------------------------+
|  ACTIVE FEATURES: {feature list with progress}                   |
+------------------------------------------------------------------+
|  UNCOMMITTED: {count} files | MESSAGES: {pending count}          |
+==================================================================+
```

---

## Notes

- **Source of truth**: Database (`claude.todos`, `claude.sessions`)
- **Why TaskCreate**: Restored tasks appear in the live task panel, not just as display text
- **Duplicate safety**: `task_sync_hook.py` uses substring + fuzzy matching (75% threshold) to detect existing DB todos and reuse their IDs
- **Priority icons**: P1 = critical, P2 = important, P3 = normal

---

**Version**: 4.0 (Consolidated: start_session() + TaskCreate restoration for live task panel)
**Created**: 2025-12-26
**Updated**: 2026-02-13
**Location**: .claude/commands/session-resume.md
