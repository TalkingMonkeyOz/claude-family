**MANDATORY SESSION STARTUP PROTOCOL**

Start a new working session with full context loading.

**Note**: The SessionStart hook already auto-creates a session record and loads todos. This command is for explicitly loading project context and displaying it.

---

## Execute These Steps

### Step 1: Load Project Context (Single Call)

Call `mcp__project-tools__start_session` with `project` = current project name.

Response contains:
- `display` - Pre-formatted context box. Print this verbatim.
- `restore_tasks` - Array of pending tasks to restore.
- `git_check_needed` - If true, run git status in Step 2.

### Step 2: Git Status

```bash
git status --short
```

Mention the uncommitted file count when displaying the box.

### Step 3: Restore Tasks

For each item in `restore_tasks`:

1. Call `TaskCreate` with:
   - `subject`: item's `content`
   - `activeForm`: item's `active_form`
   - `description`: item's `content`
2. If item's `status` is `in_progress`:
   - Call `TaskUpdate(taskId=<new_id>, status="in_progress")`

### Step 4: Display

Print the `display` string from Step 1. Ready to work.

---

## Notes

- **Automatic**: SessionStart hook already logs session to `claude.sessions` - this command adds explicit context display
- **vs /session-resume**: Use `/session-start` for fresh sessions, `/session-resume` when continuing previous work (adds last session summary)
- **One call**: `start_session()` fetches project info, todos, features, messages

---

**Version**: 5.0 (Uses start_session() MCP - matches session-resume pattern)
**Created**: 2025-10-21
**Updated**: 2026-02-14
**Location**: .claude/commands/session-start.md
