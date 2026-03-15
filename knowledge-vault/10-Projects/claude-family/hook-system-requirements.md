---
projects:
- claude-family
tags:
- hooks
- requirements
- task-persistence
---

# Task Persistence Requirements

## The Scenario

It's late. We're halfway through a large piece of work. I've got 8 tasks — 5 done, 3 remaining. I close Claude Code and go to bed. Next day — or next week, or after a holiday — I open Claude Code via the bat launcher. I expect to see those 3 remaining tasks and know what they were about. I also want to know what 5 things were already finished so I don't redo them.

## How It Works Today

### What's good
- Bat launcher sets `CLAUDE_CODE_TASK_LIST_ID=claude-family` → shared task dir
- Pending/in_progress tasks survive as JSON files in `~/.claude/tasks/claude-family/`
- `task_sync_hook.py` (PostToolUse) syncs every TaskCreate/TaskUpdate to `claude.todos` in DB
- Dedup exists: substring match (20+ chars) + fuzzy match (75% threshold) before DB insert
- Task map file in temp dir bridges task numbers to DB todo_ids

### What's broken

**1. Completed tasks are deleted from disk**
Claude Code deletes the JSON file when a task is marked `completed`. Next session, `TaskList` shows nothing for those tasks. The DB has them as `completed` but nothing reads them back.

**2. Tasks lack context**
When tasks ARE restored, they often have a subject like "Fix the bug" with no description. Claude has no idea what bug, where, or why. Tasks need enough context to be self-contained.

**3. Zombie accumulation**
281 pending todos in the DB. The same task gets created 3x across sessions (e.g., "diagnose messaging system" exists 3 times from Mar 14-15). Dedup catches some but not all because subjects vary slightly.

**4. Session breaks corrupt the flow**
Hook errors (like today's `result` variable bug) cause Claude Code to restart. The task map gets reset by `_reset_task_map()` in the startup hook. The shared task dir survives, but the bridge between task numbers and DB todos is lost.

**5. No "what did we finish?" on resume**
`/session-resume` shows prior tasks as reference text from `session_state.next_steps`. If `/session-end` wasn't run, there's nothing. Even if it was, it only captures next_steps — not completed work.

**6. Auto-archive deletes tasks on holiday**
The startup hook auto-archives pending todos >7 days old. If the user goes on holiday for 2 weeks, all their tasks get wiped.

## What I Want

1. **Remaining tasks survive indefinitely** — no time-based expiry. Tasks persist until explicitly completed or archived by the user. Going on holiday doesn't lose anything.

2. **Completed tasks are visible** — I can see what was done. Not restored as active tasks, just a reference: "Last session you completed: X, Y, Z."

3. **No duplicates** — if a task already exists (pending or in_progress), don't create another one. Claude sees existing tasks and reuses them.

4. **Self-contained context** — every task has a subject AND description that tells future-Claude exactly what it's about. Minimum: what, where, why.

5. **Graceful degradation** — if the DB is down, tasks still work on disk. If a hook crashes, tasks still work. The DB is backup, not hard dependency.

## Solution: Close the DB → Session Loop

### The missing piece

We sync **session → DB** fine (task_sync_hook works on every TaskCreate/TaskUpdate). What we've never built is **DB → session**. We write tasks to the database but never read them back on startup.

### Architecture after fix

```
SESSION START (startup hook)
    │
    ├── Query claude.todos: ALL pending/in_progress for this project
    │   └── No time limit — tasks persist until done or user archives
    ├── Query claude.todos: recently completed (last closed session)
    │   └── Shows "what was finished" as reference
    ├── Inject both into additionalContext
    │   └── Claude sees existing tasks → won't create duplicates
    │
    └── _reset_task_map() (existing — preserves entries in shared mode)

DURING SESSION
    │
    ├── TaskCreate → disk JSON + task_sync_hook → DB
    │   └── Dedup: hook checks DB before inserting
    ├── TaskUpdate → disk JSON + task_sync_hook → DB
    │   └── Completed: deleted from disk, preserved in DB as completed
    │
    └── Claude sees pending tasks from startup → avoids creating duplicates

SESSION END (or close/crash)
    │
    ├── Pending/in_progress tasks survive on disk (shared dir)
    ├── All tasks preserved in DB regardless
    └── Next startup reads them back (loop closed)
```

### Changes required

**1. Startup hook: read tasks back from DB** (~30 lines in `session_startup_hook_enhanced.py`)
- Query ALL pending/in_progress todos for this project (no time limit)
- Query completed todos from the last closed session
- Format and inject into `additionalContext`
- Claude sees them → knows what exists → won't duplicate

**2. Remove time-based auto-archive** (in startup hook)
- Delete the >7 day pending / >3 day in_progress auto-archive
- Replace with: archive only when user explicitly says so, or when a todo has been restored 5+ times (restore_count >= 5, indicating it's being recreated but never worked on)

**3. Core protocol: require task descriptions** (user to vet before implementing)
- Add to task creation rule: "Every task MUST have a description: what to do, where, why"
- Draft the change, present to user for review

**4. Analyze and clean zombie todos** (in progress — agent running)
- Analyze all 281 todos: find duplicate clusters, categorize, recommend per-item actions
- Present to user for decisions — no blind archiving

### What this does NOT change
- task_sync_hook.py — works fine, no changes
- Task discipline hook — works fine, no changes
- Filing cabinet / stash — not involved
- Memory / remember — not involved
- The DB schema — no new tables or columns

## Implementation Status: COMPLETE (2026-03-15)

All changes implemented and tested (12/12 BPMN tests pass):
1. ~~Write requirements doc~~ DONE
2. ~~Analyze zombie todos~~ DONE (286 → 260, 26 archived)
3. ~~BPMN model~~ DONE (task_lifecycle.bpmn v4)
4. ~~Gap analysis~~ DONE
5. ~~Implement code changes~~ DONE (startup hook read-back + remove time archive)
6. ~~Core protocol v18~~ DONE (task descriptions required)
7. Verify on next session restart

---

**Version**: 3.1
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/claude-family/hook-system-requirements.md
