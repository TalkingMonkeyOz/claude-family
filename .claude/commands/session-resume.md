**QUICK SESSION RESUME - Display-Only Context (No Task Restoration)**

One MCP call returns a pre-formatted display box. You display it and check git. That's it.

**Do NOT call `get_project_context`, `get_incomplete_todos`, `execute_sql`, `check_inbox`, or any other tool to fetch session data. Everything comes from `start_session(resume=True)`.**

**Do NOT call TaskCreate to restore previous session tasks.** Claude Code natively persists tasks in `~/.claude/tasks/`. Our DB todo restoration was creating zombie tasks carried forward indefinitely.

---

## Execute These Steps

### Step 1: Load Context (Single Call)

Call `mcp__project-tools__start_session` with `project` = current project name and `resume` = `true`.

Response contains:
- `display` - Pre-formatted resume box showing prior session summary, features, and prior tasks as **reference only**.
- `git_check_needed` - If true, run git status in Step 2.

### Step 2: Git Status

```bash
git status --short
```

Mention the uncommitted file count when displaying the box.

### Step 3: Display

Print the `display` string from Step 1. Done.

Prior session tasks are shown as **informational text** in the display box. The user decides what to work on fresh - no zombie task restoration.

---

## Notes

- **One call**: `start_session(resume=True)` fetches project info, session state, todos, features, messages - and formats the box server-side
- **No TaskCreate**: Previous tasks are shown as reference, not restored. User creates fresh tasks based on current priorities
- **Why no restore**: Claude Code persists tasks natively at `~/.claude/tasks/`. Our DB sync was creating a restore loop where stale tasks kept coming back as zombies across sessions
- **Task discipline**: The task_discipline_hook requires tasks before Bash/Write/Edit. Create tasks for your current session work, don't rely on restored ones

---

**Version**: 6.0 (Removed task restoration - display-only resume. Claude Code has native task persistence.)
**Created**: 2025-12-26
**Updated**: 2026-02-24
**Location**: .claude/commands/session-resume.md
