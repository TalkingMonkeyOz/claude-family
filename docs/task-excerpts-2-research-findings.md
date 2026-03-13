# Task System Excerpts - Part 2: Research Findings

**Source**: `eaac8b3f-b3fa-4f16-a420-f11e3803e52b.jsonl` lines 51-66
**Index**: [task-excerpts-index.md](task-excerpts-index.md)

---

## Research Agent Findings on Native Task System (Line 66)

The assistant spawned a research agent to answer: "Is building a custom task persistence layer necessary, or does Claude Code already handle this?"

The agent's summary:

> **Tasks in Claude Code are designed to persist across sessions.** They are stored locally in your filesystem at `~/.claude/tasks/` as JSON files, not lost when a session ends.
>
> Tasks do NOT get lost when you end a session. They:
> - Persist to disk in `~/.claude/tasks/` (one subdirectory per task list)
> - Remain available when you resume a session or create new sessions
> - Survive terminal shutdowns, system crashes, and machine switches
>
> Claude Code includes a built-in mechanism for multi-session task sharing via the `CLAUDE_CODE_TASK_LIST_ID` environment variable. When Session A completes a task, Session B sees the update immediately.
>
> From the interactive mode documentation: "Tasks persist across context compactions, helping Claude stay organized on larger projects"
>
> **You can use Claude Code's native task system as-is for task persistence.** The custom syncing you've built (`task_sync_hook.py`, task restoration) adds integration with your broader work tracking system — which is valuable, but not strictly necessary for task survival across sessions.

Sources cited by the research agent:
- Claude Code Memory Documentation (code.claude.com/docs/en/memory.md)
- Claude Code Interactive Mode Reference
- VentureBeat: "Claude Code's Tasks update lets agents work longer and coordinate across sessions"
- Multi-Session Task Coordination Guide (deepwiki.com)

---

## Session-Resume Command: Before Fix (v5.1, in effect at start of session eaac8b3f)

The command instructed Claude to:

> **Step 2: Restore Tasks FIRST**
>
> IMPORTANT: Restore tasks BEFORE running any Bash commands (task_discipline_hook blocks Bash when no tasks exist).
>
> For each item in `restore_tasks`: Call `TaskCreate` with subject, activeForm, description. If status is `in_progress`: Call `TaskUpdate(taskId=<new_id>, status="in_progress")`
>
> The `task_sync_hook` will match these to existing DB todos via duplicate detection (75% similarity) and reuse the existing `todo_id` rather than creating duplicates.

---

## Session-Resume Command: After Fix (v6.0, deployed 2026-02-24)

The updated command (visible in session `4c1d9f34`, line 4) now reads:

> **Do NOT call TaskCreate to restore previous session tasks.** Claude Code natively persists tasks in `~/.claude/tasks/`. Our DB todo restoration was creating zombie tasks carried forward indefinitely.
>
> Prior session tasks are shown as **informational text** in the display box. The user decides what to work on fresh - no zombie task restoration.
>
> - **No TaskCreate**: Previous tasks are shown as reference, not restored. User creates fresh tasks based on current priorities
> - **Why no restore**: Claude Code persists tasks natively at `~/.claude/tasks/`. Our DB sync was creating a restore loop where stale tasks kept coming back as zombies across sessions

---

## DB Evidence of the Problem (Line 94 tool result)

The actual DB todos at the time of the conversation showed:

```
'Discover Windows Task Scheduler jobs'     status=pending  restore_count=1
'Check existing scheduled_jobs in DB'      status=pending  restore_count=2
'Review claude-manager-mui app ...'        status=pending  restore_count=2
'Investigate conversation storage ...'     status=pending  restore_count=2
'Design task-to-conversation linking ...'  status=pending  restore_count=2
'Update knowledge vault ...'               status=pending  restore_count=2
```

Created 2026-02-23, still pending 2026-02-24. `restore_count=2` means each had been
TaskCreate'd, synced, and re-restored at least twice without ever being marked complete.

---
**Version**: 1.0
**Created**: 2026-03-04
**Updated**: 2026-03-04
**Location**: C:\Projects\claude-family\docs\task-excerpts-2-research-findings.md
