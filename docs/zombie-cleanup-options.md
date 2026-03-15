# Zombie Todo Cleanup Options

Analysis of 273 active (non-deleted, pending/in_progress) todos in claude-family.

## Key Findings

### 1. Scale and Age
- **273 total** active todos (query 3 returned 273, not 260 — slight growth since analysis started)
- **268 created in last 7 days**, 5 in the 7-14 day range — zero are older than 14 days
- No "very old" (60+ day) todos exist — this is a recency/accumulation problem, not a staleness problem

### 2. Orphaned by Completed Features (Query 1)
- **110 todos** match `Phase%`, `Step%`, or `BT%` patterns
- These are sub-task tracking todos created during multi-step feature work
- They accumulate because Claude creates them but the parent feature completion does not auto-archive them

### 3. Zombie Resurrections (Query 2)
- **12 todos** have `restore_count > 0` — items that were completed/deleted and recreated
- Top offender: "Reorganize Claude Family/ vault folder" — restored **3 times**, created 2026-03-11, still pending
- 11 others restored once each, mostly from 2026-03-14 and 2026-03-15
- These are genuinely deferred items, not errors — the restoration mechanism is working correctly

### 4. Duplicate Completions (Query 4)
- **0 todos** have an exact-match completed counterpart
- No "done but not archived" pattern — completed todos are not the issue

### 5. Content Category Breakdown
| Category | Count |
|----------|-------|
| Free-form tasks ("Other") | 238 |
| Phase tasks (`Phase%`) | 23 |
| BT task refs (`BT%`) | 7 |
| Step tasks (`Step%`) | 5 |

The 7 BT-prefixed todos reference build task codes that **no longer exist as active build_tasks** — all 7 are orphaned refs.

### 6. Root Cause
The todos are overwhelmingly recent (last 7 days) and free-form. They accumulate because:
- Claude creates many todos per session for task decomposition
- Completed tasks are deleted from the native Claude task list but the DB sync creates a permanent record
- Sessions that end without completing all tasks leave residue
- The `restore_count` mechanism re-surfaces deferred items on every session start

---

## Cleanup Options

### Option A: Bulk Archive by Age + Pattern (Lowest Risk)
SQL soft-delete (`is_deleted = true`) for:
1. All `Phase%`, `Step%`, `BT%` todos older than 7 days — **~30 todos**
2. All 7 orphaned BT todos (no matching active build_task) — **7 todos**
3. Todos with `restore_count >= 2` that haven't been touched in 3+ days — **1 todo** (vault reorganize)

**Estimated reduction**: ~38 todos. Safe because these are either sub-tasks of long-gone work or proven-deferred items.

### Option B: Session-Scoped Cleanup (Medium Impact)
Mark all todos as deleted where `created_session_id` belongs to a session that is now `closed` and the todo was never transitioned to `completed`. This cleans up session residue automatically.

**Risk**: May archive genuinely deferred items that were created in an old session but are still relevant.

**Estimated reduction**: Unknown without session status join — needs further query.

### Option C: Dedup Pass on Content (Targets Duplicates)
The free-form "Other" category (238 todos) likely contains near-duplicates from repeated sessions (e.g., "Analyze zombie todos", "Execute dedup on zombie todos" both visible in sample). A fuzzy-match pass grouping by cosine similarity of content could surface clusters to collapse.

**Estimated reduction**: 20-50 todos based on visible patterns in the sample.

### Option D: Retention Policy (Prevents Future Growth)
Add a DB constraint or hook rule: todos older than N days without `restore_count` activity are auto-archived. Suggested: 14 days for `pending`, 7 days for `in_progress` with no update.

This addresses the accumulation problem at the source rather than doing one-time cleanups.

### Option E: Todo Diet (Behavioral Change)
The real driver is Claude creating too many todos per session. Limit to max 10 active todos. The `task_discipline_hook.py` enforces todo creation — could also enforce a ceiling.

---

## Recommended Sequence

1. **Immediate**: Run Option A (safe, targeted, ~38 todos)
2. **This week**: Run Option C dedup pass (query content clusters, review, archive)
3. **Ongoing**: Implement Option D retention policy (14-day auto-archive)
4. **Consider**: Option E todo ceiling (max 15 active todos)

Option B (session-scoped) needs more investigation before running — the session status join query should be tested first.

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: C:\Projects\claude-family\docs\zombie-cleanup-options.md
