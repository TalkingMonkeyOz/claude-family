I now have a comprehensive picture of the entire hook system. Let me compile the full report.

---

# Claude Family Hook System - Research Report

## Overview

The hook system consists of 11 active hook configurations registered in `C:\Projects\claude-family\.claude\settings.local.json`, backed by 13 Python scripts in `C:\Projects\claude-family\scripts\` plus 3 plugin scripts in `.claude-plugins\claude-family-core\scripts\`. All primary hooks are covered by BPMN models. The system uses a shared `config.py` module for DB connectivity and a `failure_capture.py` module for self-reporting errors.

---

## Hook Inventory

### Hook 1: session_startup_hook_enhanced.py

**File**: `C:\Projects\claude-family\scripts\session_startup_hook_enhanced.py`  
**Event**: `SessionStart` (once=true, fires once per launch)  
**Status**: Working

**What it does**:
- Detects system health (DB, Voyage AI, env vars)
- Inserts or reuses a session row in `claude.sessions` (60-second dedup guard prevents duplicate sessions on restart)
- Auto-archives stale todos: pending items older than 7 days, in_progress items older than 3 days
- Counts active todos and prompts Claude to restore them
- Runs periodic memory consolidation (24-hour cooldown): promotes `mid` tier knowledge to `long`, decays old edges in `claude.knowledge_relations`, archives low-confidence entries
- Calls `system_maintenance.detect_all_staleness()` and alerts if any subsystem is stale
- Resets the task map file (`/tmp/claude_task_map_{project}.json`) to the new session ID, preserving task entries if `CLAUDE_CODE_TASK_LIST_ID` is set (shared list mode)

**DB Tables**: `claude.sessions`, `claude.todos`, `claude.projects`, `claude.knowledge`, `claude.knowledge_relations`

**Error handling**: All DB operations individually try/except. Fails open on every error. No `failure_capture` call in the startup hook (notable gap — it cannot fail-open to failure_capture cleanly since that would require a working DB).

**BPMN coverage**: Referenced by `session_lifecycle.bpmn`, `L1_session_management.bpmn`. No dedicated L2 BPMN for startup. The `hook_chain.bpmn` does not model the session startup lifecycle.

**Issues**:
- `check_system_health()` calls `get_db_connection()` before `get_db_connection` is defined lower in the file. This works only because `check_system_health` is not called until `main()`, but the ordering is fragile for readability.
- The `session_id` from `log_session_start()` is a string returned via `RETURNING session_id::text`, but the code calls `result['session_id']` which requires the psycopg `dict_row` row factory — this is correct since `_config_get_db_connection` uses `dict_row`.
- No `failure_capture` integration (all other hooks have it).

---

### Hook 2: rag_query_hook.py

**File**: `C:\Projects\claude-family\scripts\rag_query_hook.py`  
**Event**: `UserPromptSubmit` (no matcher, fires on every user message)  
**Status**: Working (large, 93KB, most complex hook in the system)

**What it does**:
- Injects `CORE_PROTOCOL` on every prompt (loaded from `scripts/core_protocol.txt`, fallback to hardcoded 8 rules)
- Queries `claude.knowledge` (mid/long tier) for relevant learned patterns
- Queries vault embeddings via Voyage AI for relevant documentation
- Injects periodic reminders at set interaction count intervals (inbox check every 15, git check every 10, tool awareness every 8, context budget every 12)
- Evaluates context health from `~/.claude/state/context_health.json` (written by StatusLine) and injects graduated urgency messages (yellow/orange/red)
- Surfaces pending process failures from `claude.feedback` (failures filed by `failure_capture.py`)
- Injects session facts (the "notepad") into context
- Manages interaction count state in `~/.claude/state/rag_hook_state.json`

**DB Tables**: `claude.knowledge`, `claude.sessions`, `claude.session_facts`, `claude.session_state`, `claude.feedback`

**Error handling**: Comprehensive. Each section individually wrapped. Calls `failure_capture` in the outer catch block. Lazy-loads voyageai to save ~100ms on non-RAG prompts.

**BPMN coverage**: `rag_pipeline.bpmn` exists in `lifecycle/`. The `hook_chain.bpmn` models the classify/RAG/skip-RAG decision. Coverage is good.

**Issues**:
- Periodic reminder at interaction 8 emits emoji characters (`📬`, `📚`, `🔀`, `🔧`). The CLAUDE.md global standard says to avoid emojis. These appear in injected context, not written files, so no validator catches them.
- The `_check_recent_checkpoint` function uses `os.path.basename(os.getcwd())` rather than the git-root resolution used in `task_discipline_hook.py` and `task_sync_hook.py`. This could produce wrong project names in subdirectory sessions.

---

### Hook 3: task_discipline_hook.py

**File**: `C:\Projects\claude-family\scripts\task_discipline_hook.py`  
**Event**: `PreToolUse`, matchers: `Write`, `Edit`, `Task`, `Bash`  
**Status**: Working

**What it does**:
- Blocks `Write`, `Edit`, `Task`, `Bash` if no tasks have been created this session
- Whitelists read-only Bash prefixes (`git status`, `ls`, `cat`, `echo`, etc.) — these pass through without task requirement
- Applies a Context Health Gate: if `~/.claude/state/context_health.json` shows red level and no recent checkpoint, denies gated tools to force state preservation
- Tracks unique files edited per session and issues a one-time delegation advisory at 3+ unique files
- Uses a 5-way cascade: shared list mode → session match → no session_id edge case → race condition (map modified < 30s) → continuation session (map fresh < 2h) → DB fallback for MCP-created tasks → deny
- Uses Windows `msvcrt` file locking to safely merge delegation tracking into the task map
- Git-root resolution for project name (handles subdirectory cwd)

**DB Tables**: `claude.build_tasks`, `claude.features`, `claude.projects`, `claude.session_state`  
**State files**: `/tmp/claude_task_map_{project}.json`

**Error handling**: Outer `try/except` with fail-open allow. Calls `failure_capture`. Uses `import msvcrt` which is Windows-only — will fail on Linux/Mac if ever cross-platform deployed.

**BPMN coverage**: Modeled in `hook_chain.bpmn` (discipline check step). Also referenced in `task_lifecycle.bpmn`. The context health gate is modeled in `hook_chain.bpmn`.

**Issues**:
- `msvcrt` import is Windows-only. There is no fallback for non-Windows environments. This is currently acceptable given the environment (Windows 11) but worth noting.
- The DB fallback `check_db_for_recent_tasks` uses a string-formatted interval: `INTERVAL '%s hours'` with a Python `%s` parameter. The `max_age_hours` value (default 2) is passed as the second parameter. This is valid for psycopg but visually confusing — the `%s` in the INTERVAL string is parameterized, not directly substituted.
- `_has_recent_checkpoint()` also uses `os.getcwd()` (not git-root resolution) for project name. Inconsistent with `_get_project_name()` used elsewhere in the same file.

---

### Hook 4: context_injector_hook.py

**File**: `C:\Projects\claude-family\scripts\context_injector_hook.py`  
**Event**: `PreToolUse`, matchers: `Write`, `Edit`  
**Status**: Working (partially — `inject_vault_query` is an unimplemented TODO)

**What it does**:
- Queries `claude.context_rules` for rules matching the tool name and file path
- Loads standard files from `~/.claude/standards/`, `~/.claude/instructions/`, `~/.claude/skills/`
- Loads database-stored skill content via `claude.skill_content` table
- Composes `additionalContext` injection before Write/Edit executes

**DB Tables**: `claude.context_rules`, `claude.skill_content`

**Error handling**: Fail-open with `failure_capture` on outer exception.

**BPMN coverage**: Referenced in `hook_chain.bpmn` as "inject_tool_context" step. No dedicated BPMN process.

**Issues**:
- `inject_vault_query` is explicitly a TODO at lines 18, 223, and 268. The RAG vault query from context_rules is never executed. Any rules that set this field have no effect.
- Standards truncated at 1500 chars, skill content at 4000 chars. These limits are hardcoded, not configurable.
- If `claude.context_rules` table has no active rules, the hook adds no overhead — but there is a DB connection opened on every Write/Edit regardless, costing ~5ms per call.
- No dedicated BPMN model for this hook's decision logic.

---

### Hook 5: standards_validator.py

**File**: `C:\Projects\claude-family\scripts\standards_validator.py`  
**Event**: `PreToolUse`, matchers: `Write`, `Edit`  
**Status**: Working

**What it does**:
- Queries `claude.coding_standards` for standards matching the file path glob patterns
- Validates proposed file content against those standards
- Currently only implements `max_lines_by_type` and `default_max_lines` validation (line count limit)
- Can either `deny` (block) or `ask` with `updatedInput` (middleware suggestion pattern)
- For `Edit` operations, validates only the `new_string` (not the resulting file), which means it cannot check the total post-edit line count

**DB Tables**: `claude.coding_standards`

**Error handling**: Fail-open with `failure_capture`.

**BPMN coverage**: `content_validation.bpmn` exists in `infrastructure/`.

**Issues**:
- For `Edit` (not `Write`), only `new_string` is validated. This means an edit that takes a 280-line file and adds 30 lines won't be caught — the validator only sees the `new_string` snippet, not the resulting file size. The TODO comments at line 231 (`forbidden_patterns`, `required_patterns`, `naming_checks`) indicate incomplete implementation.
- The `ask+updatedInput` pattern is implemented but the `validate_content` function only calls `deny` via `block_with_reason`. The auto-correction suggestion path is never exercised by current validation logic.

---

### Hook 6: todo_sync_hook.py

**File**: `C:\Projects\claude-family\scripts\todo_sync_hook.py`  
**Event**: `PostToolUse`, matcher: `TodoWrite`  
**Status**: Working

**What it does**:
- Intercepts every `TodoWrite` call and syncs the full todo list to `claude.todos`
- Uses fuzzy matching (SequenceMatcher, 75% threshold) to identify existing todos and update them vs. insert new ones
- Tracks `completed_at` and `completed_session_id` on status transitions
- Maps `deleted` status to `archived` (preserves audit trail)
- Deliberately does NOT auto-delete todos absent from the current `TodoWrite` call (prevents accidental deletion when working with subsets)

**DB Tables**: `claude.todos`, `claude.projects`, `claude.sessions`

**Error handling**: Fail-open with `failure_capture`. Validates UUID formats before DB calls. Handles missing session (falls back to NULL FK).

**BPMN coverage**: `todo_sync.bpmn` exists in `infrastructure/`.

**Issues**:
- Lines 119–122 show a psycopg version branch with identical code on both sides (`if PSYCOPG_VERSION == 2: ... else: ...` both call `cur.fetchall()`). This is dead code duplication from a prior refactor.
- Lines 259–261 have the same pattern for `cur.fetchone()['todo_id']`.
- Fuzzy matching at 75% could produce false positives for short similar todo texts. The minimum match length check in `task_sync_hook.py` (20 chars) is absent here.

---

### Hook 7: task_sync_hook.py

**File**: `C:\Projects\claude-family\scripts\task_sync_hook.py`  
**Event**: `PostToolUse`, matchers: `TaskCreate`, `TaskUpdate`  
**Status**: Working

**What it does**:
- On `TaskCreate`: inserts a todo in `claude.todos`, optionally bridges to a matching `claude.build_task` via similarity matching (75% threshold, with 20-char minimum for substring strategy)
- On `TaskUpdate`: updates todo status, propagates to bridged build_task, writes audit log entries, auto-checkpoints on task completion
- Writes task number → `{todo_id, bt_code?, bt_task_id?}` mapping to `/tmp/claude_task_map_{project}.json` with Windows file locking
- Extracts task number from `tool_response` JSON (`{"task": {"id": "4"}}`) with regex fallback
- Returns `additionalContext` when all build tasks for a feature are complete (surfaces completion notice to Claude)

**DB Tables**: `claude.todos`, `claude.projects`, `claude.sessions`, `claude.build_tasks`, `claude.features`, `claude.audit_log`, `claude.session_state`  
**State files**: `/tmp/claude_task_map_{project}.json`

**Error handling**: Fail-open with `failure_capture`. File locking uses `msvcrt` (Windows-only). Separate rollback on DB failure.

**BPMN coverage**: `task_sync.bpmn` exists in `infrastructure/`. Also modeled in `task_lifecycle.bpmn`.

**Issues**:
- `msvcrt` import is Windows-only (same as `task_discipline_hook.py`).
- The `handle_task_update` function for `new_status == 'completed'` closes the connection early (before returning the feature completion message) on one path but not others — slight inconsistency but not a bug since `conn.close()` is called before the return and the message string doesn't need the connection.
- `map_entry.get('subject', ...)` in `handle_task_update` (line 457): the `subject` key is never stored in the map entry — only `todo_id`, `bt_code`, `bt_task_id`. So `task_subject` always falls back to `f'Task #{task_id}'`.

---

### Hook 8: mcp_usage_logger.py

**File**: `C:\Projects\claude-family\scripts\mcp_usage_logger.py`  
**Event**: `PostToolUse` (no matcher — catch-all)  
**Status**: Working

**What it does**:
- Fires on every PostToolUse event (no matcher registered)
- Quick-exits for non-MCP, non-Skill tools using a fast raw string check before JSON parsing (avoids full parse cost for the ~70% of calls that are built-ins like Read/Write/Edit)
- Logs to `claude.mcp_usage`: tool name, server, execution time (approximation from hook call time, not actual tool time), success flag, input/output sizes, session ID, project name
- Lazy session creation: if session doesn't exist in DB, creates it to satisfy FK constraint
- Tracks `Skill` tool invocations as `Skill:{skill_name}` (FB140)
- Skips `mcp__memory__search_nodes` (hardcoded noise filter)
- Falls back to `hook_data_fallback` JSONL on DB failure

**DB Tables**: `claude.mcp_usage`, `claude.sessions`

**Error handling**: Best-effort, fail-open. JSONL fallback on DB failure.

**BPMN coverage**: `mcp_usage_logging.bpmn` exists in `infrastructure/`.

**Issues**:
- The "execution time" measurement is the time from when the hook itself starts to when the DB insert completes, not the actual MCP tool execution time. It measures hook overhead, not tool performance. The field is misleading.
- Project name extraction at lines 251–253 is fragile: it splits on the string `'Projects'` and takes the next path segment. This will fail for any project not under a `Projects` directory (e.g., paths containing `Projects` in a different position).
- `skip_tools` list (line 221) only contains `mcp__memory__search_nodes` which references a retired MCP (memory MCP was removed per MEMORY.md). This could be cleaned up.

---

### Hook 9: subagent_start_hook.py

**File**: `C:\Projects\claude-family\scripts\subagent_start_hook.py`  
**Event**: `SubagentStart` (no matcher)  
**Status**: Working (with a caveat — see issues)

**What it does**:
- Logs subagent spawns to `claude.agent_sessions`
- Extracts `subagent_id`, `subagent_type`, `task_prompt`, `parent_session_id` from hook input
- Truncates task_prompt to 1000 chars
- Uses upsert (ON CONFLICT) to handle duplicate spawn events
- Falls back to JSONL via `hook_data_fallback`

**DB Tables**: `claude.agent_sessions`

**Error handling**: JSONL fallback on DB failure. No `failure_capture` call (notable gap).

**BPMN coverage**: `subagent_start.bpmn` exists in `infrastructure/`.

**Issues**:
- No `failure_capture` integration in the outer exception handler. The outer `try` in `main()` only calls `logging.error`. This is inconsistent with all other hooks.
- The `subagent_type` field in the hook input may not actually be populated by Claude Code — per MEMORY.md, spawned agents have `disableAllHooks: true`, meaning the `SubagentStart` hook may not fire for all spawned agents. This could make the `agent_sessions` table incomplete.

---

### Hook 10: precompact_hook.py

**File**: `C:\Projects\claude-family\scripts\precompact_hook.py`  
**Event**: `PreCompact`, matchers: `manual`, `auto`  
**Status**: Working

**What it does**:
- Fires before context compaction (both manual `/compact` and auto-compact triggers)
- Queries DB for: active todos (up to 10), current focus and next steps from `claude.session_state`, active features (up to 3 most recently updated), current session facts (up to 5 most recent non-sensitive)
- Injects a structured recovery protocol into `systemMessage` with post-compaction steps
- Injects session notes from `~/.claude/session_notes.md` (if present, truncated at 500 chars)
- Warns via log (FB137 fix) when more than 5 facts exist and truncation occurs
- Falls back to a minimal message if DB is unavailable

**DB Tables**: `claude.todos`, `claude.projects`, `claude.session_state`, `claude.features`, `claude.build_tasks`, `claude.session_facts`, `claude.sessions`

**Error handling**: Outer `try/except` with fail-open (minimal systemMessage). Calls `failure_capture`.

**BPMN coverage**: `precompact.bpmn` exists in `infrastructure/`. Also modeled conceptually in `session_continuation.bpmn`.

**Issues**:
- Session facts are limited to 5 most recent. If Claude stored 10+ facts in a long session, only 5 survive compaction. The FB137 log warning fires but the data is still lost from the injected context. The MEMORY.md documents this as a known issue.
- `get_session_state_for_compact` fetches `active_tasks` count with a correlated subquery for each feature row. For features with many tasks, this is fine, but the query structure mixes row-level and aggregate data in a single SELECT without a GROUP BY — the correlated subquery works correctly but is slower than a join approach.

---

### Hook 11: session_end_hook.py

**File**: `C:\Projects\claude-family\scripts\session_end_hook.py`  
**Event**: `SessionEnd` (no matcher)  
**Status**: Working

**What it does**:
- Demotes `in_progress` todos back to `pending` (per task_lifecycle BPMN: in_progress tasks should not persist across sessions)
- Logs the demotion to `claude.audit_log`
- Promotes qualifying `session_facts` to mid-tier `claude.knowledge` (F130: facts with type decision/reference/note, length >= 50 chars, not already promoted)
- Marks `session_end` timestamp on the session row
- Falls back to closing the most recent unclosed session (< 24h) if no `session_id` is provided
- Falls back to JSONL on DB failure
- Outputs a reminder to run `/session-end` for full summary

**DB Tables**: `claude.sessions`, `claude.todos`, `claude.projects`, `claude.audit_log`, `claude.session_facts`, `claude.knowledge`

**Error handling**: Outer `try/except` with `failure_capture`. JSONL fallback.

**BPMN coverage**: `session_end.bpmn` exists in `infrastructure/`.

**Issues**:
- `consolidate_session_facts` queries `session_facts` joined to `sessions` with a condition `s.session_end IS NOT NULL`, but the session end timestamp is set later in the same function (`auto_save_session` calls `demote_in_progress_todos` first, then `consolidate_session_facts`, then sets `session_end`). So the fact consolidation query will never find facts from the current session because the session isn't closed yet when the query runs. This is a logical ordering bug — the promotion effectively only catches facts from previous sessions.
- The promotion inserts into `claude.knowledge` without embeddings. The comment notes this is intentional (embeddings added by `consolidate_memories()` MCP tool later), but if `consolidate_memories()` is never called, these knowledge entries have no semantic search capability.

---

## Plugin Hook Scripts (`.claude-plugins`)

Three hooks registered in `settings.local.json` under the `mcp__postgres__execute_sql` matcher point to `.claude-plugins\claude-family-core\scripts\`:

### validate_db_write.py
**Status**: Broken by design for its configured usage

This script expects SQL as `sys.argv[2:]` or via stdin (`sys.stdin.isatty()` check). However, the hook configuration passes it as: `python "...validate_db_write.py" "mcp__postgres__execute_sql"`. The SQL is not passed as an argument — it would need to come from stdin. The hook event input (the full JSON including the SQL) is sent to the hook's stdin, but this script reads raw stdin as SQL text (not JSON). It does not parse the hook input JSON format. The validator will likely receive the full JSON blob and fail to extract a valid SQL statement from it. Additionally, it uses its own `get_db_connection()` function (reads `DATABASE_URL` env var directly, not through `config.py`), so any `.env` file loading from `config.py` would be skipped.

**BPMN coverage**: None dedicated. Referenced in `hook_chain.bpmn` conceptually.

### validate_phase.py
**Status**: Same input-parsing issue as validate_db_write.py

Expects SQL as `sys.argv[1:]`. The hook config passes no SQL arguments. The script would receive empty `sys.argv` beyond index 0 and immediately return `allow`.

### validate_parent_links.py
**Status**: Same input-parsing issue

Same pattern: reads SQL from `sys.argv[1:]` or stdin, but the hook doesn't pass SQL that way.

**Effective status of these three**: They fail open (return allow immediately), providing no enforcement. They are vestigial from an older hook architecture where SQL was passed as arguments. The current Claude Code hook event passes the full JSON on stdin, which none of these scripts parse.

---

## Auxiliary Scripts (Not Registered Hooks)

- **`debug_hook.py`**: Diagnostic-only script that logs all stdin and always allows. Not registered in settings. Safe for manual testing.
- **`hook_data_fallback.py`**: Support module (JSONL write-ahead log). Called by multiple hooks on DB failure. No DB dependencies. Works as designed.
- **`failure_capture.py`**: Support module for automated failure filing. Writes to `~/.claude/process_failures.jsonl` and `claude.feedback`. Works as designed.

---

## BPMN Coverage Matrix

| Hook | Dedicated BPMN | In hook_chain.bpmn | Status |
|------|---------------|-------------------|--------|
| session_startup_hook_enhanced.py | No dedicated model | Referenced in session_lifecycle.bpmn | Partial |
| rag_query_hook.py | `lifecycle/rag_pipeline.bpmn` | Yes (RAG phases 1) | Covered |
| task_discipline_hook.py | No dedicated model | Yes (discipline check) | Covered via chain |
| context_injector_hook.py | No dedicated model | Yes (inject_tool_context step) | Partial |
| standards_validator.py | `infrastructure/content_validation.bpmn` | Implied in chain | Covered |
| todo_sync_hook.py | `infrastructure/todo_sync.bpmn` | Yes (post_tool_sync) | Covered |
| task_sync_hook.py | `infrastructure/task_sync.bpmn` | Yes (post_tool_sync) | Covered |
| mcp_usage_logger.py | `infrastructure/mcp_usage_logging.bpmn` | Yes (post_tool_sync) | Covered |
| subagent_start_hook.py | `infrastructure/subagent_start.bpmn` | No | Covered |
| precompact_hook.py | `infrastructure/precompact.bpmn` | No (separate event) | Covered |
| session_end_hook.py | `infrastructure/session_end.bpmn` | No (separate event) | Covered |
| validate_db_write.py | No | No | Not covered |
| validate_phase.py | No | No | Not covered |
| validate_parent_links.py | No | No | Not covered |

---

## Deprecated Schema Check

No hook in `C:\Projects\claude-family\scripts\` references `claude_family.*` or `claude_pm.*` schemas. All active hooks use `claude.*`. The two references found (`orchestrate_mission_control_build.py`, `show_startup_notification.py`) are in non-hook utility scripts that are not part of the active hook chain and appear to be legacy/inactive scripts.

Plugin scripts in `.claude-plugins\` also contain no deprecated schema references.

---

## Issues Summary

### Critical
1. **validate_db_write.py / validate_phase.py / validate_parent_links.py**: All three plugin validators are non-functional as configured. They expect SQL as CLI arguments but the hook system passes the full event JSON on stdin. They fail open silently, providing zero enforcement of column_registry constraints, phase validation, or orphan prevention for direct SQL calls.

### Significant
2. **session_end_hook.py consolidate_session_facts ordering bug**: The query checking `session_end IS NOT NULL` runs before `session_end` is set. Session facts from the current session are never promoted by this hook. Only facts from prior sessions (within 7 days) are candidates.

3. **task_sync_hook.py task_subject not stored**: The `subject` field is never saved in the task map entry, so completion checkpoint messages always read "Completed: Task #N" rather than the actual task name.

4. **rag_query_hook.py uses cwd basename (not git root) for checkpoint check**: Inconsistent with task_sync and task_discipline which use git-root resolution. Will use wrong project name in subdirectory sessions.

### Minor
5. **context_injector_hook.py inject_vault_query unimplemented**: Three TODO markers for vault RAG in context injection. Context rules with this field set have no effect.

6. **todo_sync_hook.py psycopg version branch dead code**: Lines 119–122 and 259–261 have identical code on both if/else branches.

7. **mcp_usage_logger.py execution_time_ms misleading**: Measures hook overhead (typically < 5ms), not the actual MCP tool execution time. The field name implies the latter.

8. **mcp_usage_logger.py skip_tools references retired MCP**: `mcp__memory__search_nodes` refers to the memory MCP server which was removed per MEMORY.md. The entry is harmless but stale.

9. **subagent_start_hook.py no failure_capture**: Missing integration with the self-improvement loop. Consistent with all other hooks except this one.

10. **session_startup_hook_enhanced.py no failure_capture**: Same gap.

11. **msvcrt Windows-only in task_discipline_hook.py and task_sync_hook.py**: File locking uses `import msvcrt`. Acceptable for the current Windows 11 environment, but would fail if deployed on Linux or Mac.

---

## Vault Documentation Accuracy

The vault document at `C:\Projects\claude-family\knowledge-vault\Claude Family\Claude Hooks.md` (version 4.1, updated 2026-03-04) is accurate and matches the actual implementation:
- The 11-hook active table is correct
- The 3 infrastructure-only validators are listed
- The decision cascade in "Task Discipline Details" matches the code exactly (including FB108/FB109/shared list)
- The failure capture integration list of 8 hooks is accurate (misses subagent_start and session_startup, which is correct — those two lack the integration)

The MEMORY.md entry for "Common Gotchas" is accurate on all hook-related entries checked.

---

## Effectiveness Assessment

| Hook | Value | Notes |
|------|-------|-------|
| session_startup_hook_enhanced.py | High | Auto-session logging, stale todo cleanup, memory consolidation — all working |
| rag_query_hook.py | High | Core Protocol injection is the single most effective governance mechanism; RAG context adds relevant knowledge |
| task_discipline_hook.py | High | Real enforcement mechanism; the 5-way cascade handles edge cases well |
| context_injector_hook.py | Medium | Adds coding standards pre-Write, but vault RAG injection is a TODO gap |
| standards_validator.py | Low-Medium | Only line count validation implemented; Edit validation checks only new_string not final file |
| todo_sync_hook.py | High | Solves the fundamental TodoWrite persistence problem |
| task_sync_hook.py | High | Task→DB bridge and build_task sync is working well; the task map shared state is the linchpin of the discipline system |
| mcp_usage_logger.py | Medium | Analytics value; execution_time measurement is misleading |
| subagent_start_hook.py | Low-Medium | May not fire for all agents (disableAllHooks note); data completeness uncertain |
| precompact_hook.py | High | Context continuity after compaction is critical and well-implemented |
| session_end_hook.py | High | Auto-close and todo demotion work correctly; fact consolidation has the ordering bug |
| validate_db_write.py | None | Non-functional as configured |
| validate_phase.py | None | Non-functional as configured |
| validate_parent_links.py | None | Non-functional as configured |