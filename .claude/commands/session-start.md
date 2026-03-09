**MANUAL SESSION START - Load Context for Current Project**

Use this command when you want to explicitly load session context at the start of a session. The SessionStart hook handles this automatically, so `/session-start` is optional — use it to refresh context mid-session or get a clean display of current state.

**Do NOT call legacy scripts, query `claude_family.*` or `claude_pm.*` tables, or use `mcp__memory__*` tools. Everything comes from `start_session()`.**

---

## Execute These Steps

### Step 1: Load Context (Single Call)

Call `mcp__project-tools__start_session` with `project` = current project name and `resume` = `false`.

Response contains:
- `display` - Pre-formatted session box showing current features, active tasks, open messages, and recent session summary
- `git_check_needed` - If true, run git status in Step 2
- `messages_pending` - If true, check inbox in Step 3

### Step 2: Git Status

```bash
git status --short
```

Mention uncommitted file count when displaying the session box.

### Step 3: Check Inbox (If Messages Pending)

If `messages_pending` was true in Step 1, call:

```
mcp__project-tools__check_inbox()
```

Summarise any pending messages to the user.

### Step 4: Display

Print the `display` string from Step 1.

---

## Notes

- **One call**: `start_session(resume=False)` fetches project info, active features, open todos, pending messages — and formats the box server-side
- **Automatic**: The SessionStart hook already runs this on every session open. Use `/session-start` to refresh or get a clean display
- **No legacy schemas**: `claude_family.*`, `claude_pm.*`, and `mcp__memory__*` are all retired
- **Task discipline**: The `task_discipline_hook` requires tasks before Bash/Write/Edit. Create tasks for your current session work

---

**Version**: 2.0 (Rewrote: use mcp__project-tools__start_session, removed retired schemas and tools)
**Created**: 2025-12-20
**Updated**: 2026-03-09
**Location**: .claude/commands/session-start.md
