**QUICK SESSION RESUME - Database-Driven Context with Task Restoration**

One MCP call returns a pre-formatted display box + task list. You display it and restore tasks. That's it.

**Do NOT call `get_project_context`, `get_incomplete_todos`, `execute_sql`, `check_inbox`, or any other tool to fetch session data. Everything comes from `start_session(resume=True)`.**

---

## Execute These Steps

### Step 1: Load Context (Single Call)

Call `mcp__project-tools__start_session` with `project` = current project name and `resume` = `true`.

Response contains:
- `display` - Pre-formatted resume box. Print this verbatim.
- `restore_tasks` - Array of tasks to restore (each has `content`, `active_form`, `status`, `priority`).
- `git_check_needed` - If true, run git status in Step 3.

### Step 2: Restore Tasks FIRST

**IMPORTANT**: Restore tasks BEFORE running any Bash commands (task_discipline_hook blocks Bash when no tasks exist).

For each item in `restore_tasks`:

1. Call `TaskCreate` with:
   - `subject`: item's `content`
   - `activeForm`: item's `active_form`
   - `description`: item's `content`
2. If item's `status` is `in_progress`:
   - Call `TaskUpdate(taskId=<new_id>, status="in_progress")`

The `task_sync_hook` will match these to existing DB todos via duplicate detection (75% similarity) and reuse the existing `todo_id` rather than creating duplicates.

### Step 3: Git Status (After Tasks Exist)

```bash
git status --short
```

Mention the uncommitted file count when displaying the box.

### Step 4: Display

Print the `display` string from Step 1. Done.

---

## Notes

- **One call**: `start_session(resume=True)` fetches project info, session state, todos, features, messages - and formats the box server-side
- **Why TaskCreate**: Restored tasks appear in the live task panel, not just as display text
- **Why tasks before git**: `task_discipline_hook` blocks Bash when no tasks exist - restore tasks first to avoid the error
- **Duplicate safety**: `task_sync_hook.py` uses substring + fuzzy matching (75% threshold)

---

**Version**: 5.1 (Fixed: restore tasks BEFORE git status to avoid task_discipline_hook blocking)
**Created**: 2025-12-26
**Updated**: 2026-02-20
**Location**: .claude/commands/session-resume.md
