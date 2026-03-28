---
projects:
- claude-family
tags:
- audit
- task-tracking
- todos
- features
synced: false
---

# Task Tracking System Audit

**Date**: 2026-03-12
**Scope**: `claude.todos`, `claude.features`, `claude.build_tasks`, `claude.feedback`, sync hooks, discipline enforcement

---

## Executive Summary

Task tracking is structurally sound but functionally broken in three specific ways. The mechanisms exist. The hooks fire. The data flows into the database. The problem is that none of the tracking leads to closure.

The core issue is motivational, not technical: Claude creates tasks because the discipline hook blocks file writes without them. Once tasks exist, there is no pressure to close them. The system rewards task creation but imposes no cost for leaving tasks open. The result is an ever-growing pile of `pending` todos, perpetually `in_progress` features, and a feedback table that functions as a write-only log.

**Honest verdict**: The system produces task compliance theater, not task tracking.

---

## Todo Analysis

**Two overlapping systems** both write to `claude.todos` with no distinguishing column:
- `todo_sync_hook.py` — fires on every `TodoWrite`, upserts Claude's in-context task list
- `task_sync_hook.py` — fires on `TaskCreate`, inserts discipline-hook-required tasks

These have different semantics and lifecycles. The 75% fuzzy dedup catches some but not all overlaps. The table is a mix of volatile working-list items and tracking records, making meaningful completion rates impossible to calculate.

**Auto-archive hides the problem**: The startup hook archives pending todos older than 7 days and in-progress todos older than 3 days. This keeps the active count low but silently accumulates abandoned work in archive. The zombie problem exists; it just moves.

**Completion rate**: Low. The discipline hook creates pressure to create tasks; nothing creates pressure to close them. The session_end_hook demotes `in_progress` back to `pending` but does not prompt closure.

---

## Feature Pipeline

Features are created and rarely completed. The `all_tasks_done` gate for feature completion is meaningful but almost never triggered in practice because:

1. Build tasks are rarely created via `create_linked_task` (the path that establishes the `feature_id` FK required for completion checking)
2. Native `TaskCreate` tasks bridge to build tasks via 75% fuzzy match, which fails silently when task subjects don't closely match build task names
3. Even when all tasks complete, `task_sync_hook.py` returns an advisory message suggesting `advance_status` — Claude sees it and ignores it

The feature table is a graveyard of completed work that was never formally closed. Features implemented months ago likely still show `in_progress`.

---

## Build Task Analysis

Build tasks are created via two paths:
1. `create_linked_task` MCP tool — proper, establishes `feature_id` FK, enables completion tracking
2. `TaskCreate` hook trigger — creates only a `claude.todos` row, optionally bridges to build_tasks via fuzzy match

Path 2 is the common path and is unreliable. Most native tasks are never connected to `build_tasks` records. Most build tasks are abandoned in `todo` or `in_progress` state when sessions end. Build tasks as a tracking mechanism are theatre — they satisfy the structural requirement (work is tracked) without providing actual visibility.

---

## Feedback Pipeline

`failure_capture.py` auto-files bugs on hook failures. Nothing auto-triages them. The state machine (`new → triaged → in_progress → resolved`) exists but nobody drives it.

The `rag_query_hook.py` surfaces pending failures on each prompt, which creates awareness. But awareness without a forced resolution workflow produces reminder fatigue. Feedback accumulates at `new` status.

---

## Task Sync Mechanism

**Hybrid persistence** (`CLAUDE_CODE_TASK_LIST_ID`): Correctly configured in `.env` and `Launch-Claude-Code-Console.bat`. Tasks survive context compaction and session restarts. The persistence mechanism works. The problem is not persistence — it is accumulation without completion.

**The discipline hook creates a perverse incentive**: Tasks are created as a prerequisite to doing anything. They are created quickly with generic titles to satisfy the hook. They are never completed because they are never specific enough to be actionable. The hook achieves task creation compliance at the cost of task quality.

**The 5-way cascade weakens enforcement**: The discipline hook has 6 fallback paths before denying (shared list mode, session match, no session_id, race condition, continuation session, DB fallback). In shared list mode — which is always active on this project — the hook allows all tool calls unconditionally once any tasks exist. Enforcement is weaker than it appears.

---

## Technical Bugs Found

| # | Bug | Location | Severity |
|---|-----|----------|----------|
| 1 | `session_end_hook.py` queries `session_end IS NOT NULL` before setting it — current-session facts never promoted | `session_end_hook.py` lines 292-310 | Significant |
| 2 | `task_sync_hook.py` never stores `subject` in the task map — completion checkpoints always read "Completed: Task #N" | `task_sync_hook.py` line 457 | Minor |
| 3 | Three DB validators (`validate_db_write.py`, `validate_phase.py`, `validate_parent_links.py`) parse CLI args for SQL but hook system passes JSON on stdin — silently fail open | `.claude-plugins/` (deprecated, removed 2026-03-28; migrated to `scripts/`) | Critical (no enforcement) |
| 4 | `todo_sync_hook.py` fuzzy match has no minimum length guard (task_sync_hook has 20-char min) — false positives on short todos | `todo_sync_hook.py` line 172 | Minor |

---

## Root Cause Analysis

**Root cause 1 — No closure culture**: Task creation is enforced (discipline hook blocks writes). Task closure is never enforced. No equivalent hook exists for closing work. The enforcement architecture is entirely oriented toward task creation.

**Root cause 2 — Two overlapping todo systems**: `TodoWrite` and `TaskCreate` produce separate records in the same table. They have different semantics and no distinguishing column. The table is noise.

**Root cause 3 — Feature tracking requires deliberate MCP calls that never happen**: Properly closing a feature requires `create_linked_task`, then `complete_work` per task, then `advance_status`. Claude forgets step 1 (using `TaskCreate` instead), breaking the chain.

**Root cause 4 — Enforcement was optimized away**: `CLAUDE_CODE_TASK_LIST_ID` shared list mode + the 5-way cascade means the discipline hook almost never blocks anything after the first task is created in a project's history. Once tasks exist in the shared list, the hook allows everything indefinitely.

**Root cause 5 — Session boundary is the wrong enforcement point**: Enforcing task creation at session start does not address the real problem: work not closing out. The effective enforcement point is session end — requiring demonstration that tasks were advanced, not just created.

---

## Key Findings (Summary)

1. Auto-archive hides the zombie todo problem by moving abandoned work to archive silently
2. `CLAUDE_CODE_TASK_LIST_ID` is correctly configured — persistence works, closure does not
3. The discipline hook rarely denies in practice on any active project
4. Two todo systems overlap in the same table with no distinguishing column
5. Build task bridging at 75% fuzzy is unreliable — most native tasks never connect to `build_tasks`
6. Three DB validators are non-functional as configured (no enforcement)
7. Feature completion advisory is ignored — `advance_status` is never called
8. Feedback accumulates at `new` status with no triage workflow
9. The session_end_hook fact-promotion ordering bug means current-session facts are never promoted
10. The fix is a session-end closure gate + human-visible completion ratio, not more creation-side enforcement

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/task-tracking-audit.md
