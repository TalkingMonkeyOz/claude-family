I now have sufficient data from all sources. Let me compile the comprehensive report.

---

# Claude Family Logging and Monitoring Systems - Research Report

Date: 2026-03-09

---

## 1. Session Logging (`session_startup_hook_enhanced.py` + `session_end_hook.py`)

### How It Works

The session startup hook fires on the `SessionStart` event. It:

1. Runs a system health check (DB, Voyage AI, env vars) - no DB query for this step
2. Inserts a new row into `claude.sessions` with a generated UUID, identity_id, project_name, and `session_start = NOW()`
3. Includes a 60-second deduplication guard: if a session for the same project started within 60 seconds and is still open, it reuses that session_id instead of creating a duplicate
4. Auto-archives stale todos (pending >7d, in_progress >3d)
5. Runs periodic memory consolidation (24h cooldown via `~/.claude/state/consolidation_state.json`)
6. Writes a fresh `claude_task_map_{project}.json` to temp dir so the discipline hook does not reject writes

Session closure is handled by `session_end_hook.py` on the `SessionEnd` event. It:
- Demotes in_progress todos back to pending
- Promotes qualifying session facts to mid-tier knowledge
- Sets `session_end = NOW()` on the current session
- Falls back to closing the most recent unclosed session for the project if no session_id is available

### Orphaned Sessions - Critical Finding

The `session_end_fallback.jsonl` file has **52 unresolved entries** spanning 2026-02-20 through 2026-03-07, all with `"replayed": false`. Every one of them is a session where the `session_end_hook.py` caught an exception and wrote a fallback entry instead of updating the DB.

This means every session in that log (from projects: claude-family, trading-intelligence, nimbus-mui, nimbus-odata-configurator, monash-nimbus-reports) has an orphaned record in `claude.sessions` with `session_end IS NULL`.

Root cause confirmed: The fallback file is written but there is no replay mechanism called from the startup hook. The `replay_fallback()` function exists in `hook_data_fallback.py` but nothing calls it for `session_end` on startup.

One entry has `"session_id": null` (line 19) and one has `"session_id": "test"` (line 22) - both indicate edge cases that triggered the fallback.

The session_end_hook does have a fallback path: if DB is unavailable it logs to the JSONL. The volume (52 entries over 17 days) strongly suggests the DB was consistently unavailable during session close, not just occasionally. The `session_startup_hook_enhanced.py` also does not replay the `session_end` fallback, so those sessions stay orphaned forever.

### Assessment

- **Status**: Partially broken
- **Value**: High - session tracking is core to all other features
- **Key gap**: 52+ unresolved session-end records; no replay mechanism for session_end fallback

---

## 2. MCP Usage Logging (`mcp_usage_logger.py` → `claude.mcp_usage`)

### How It Works

The logger fires on every `PostToolUse` event (no matcher filter - catches all tools). It uses a fast-path string check to skip non-MCP tools before doing JSON parsing. The flow:

1. Check raw input string for `"mcp__"` or `"Skill"` - returns immediately for built-in tools like Read/Write/Bash
2. Parse JSON, extract tool_name, tool_input, tool_response
3. Extract MCP server name from tool_name prefix (e.g., `mcp__postgres__execute_sql` → `postgres`)
4. Calculate input/output byte sizes
5. Insert into `claude.mcp_usage` with: mcp_server, tool_name, execution_time_ms, success, input/output sizes, session_id, project_name

The execution_time_ms is measured from hook invocation, not actual tool execution - it measures hook overhead (~2-5ms) not tool latency.

The log from Feb 13-14 confirms MCP tools being tracked: `mcp__postgres__execute_sql` calls are logged successfully. The hooks.log entries from March 7 confirm `mcp__project-tools__start_session`, `mcp__project-tools__recall_memories`, `mcp__project-tools__search_conversations` are all being logged.

Built-in tools (Read, Glob, Grep, Bash, Write) pass through the fast path and are NOT logged to the DB. The hooks.log shows these getting `tool_name=Read, HAS_DB=True` entries but no `Calling log_mcp_usage` follow-up - confirming the filter works.

The Skill tool IS tracked (FB140 fix) with names like `Skill:database-operations`.

There is a JSONL fallback (`~/.claude/hook_fallback/mcp_usage_fallback.jsonl`) for DB outages - this file does not currently exist, meaning all MCP usage is successfully hitting the DB.

### Assessment

- **Status**: Working
- **Value**: High for understanding which tools are actually used; data exists in `claude.mcp_usage`
- **Limitation**: Execution time is hook overhead (2-5ms), not actual tool duration

---

## 3. Audit Log (`claude.audit_log`)

### How It Works

The audit log receives entries from two sources:

**From `task_sync_hook.py`**: When a TaskUpdate changes a build_task status (bridged via task_map), an audit entry is written with: `entity_type='build_tasks'`, `entity_id`, `entity_code` (e.g., BT123), `change_source='task_sync_hook'`, `from_status`, `to_status`

**From `session_end_hook.py`**: When in_progress todos are demoted to pending, an entry is written with: `entity_type='todo_demotion'`, `entity_id=project_name`, `from_status='in_progress'`, `to_status='pending'`, `change_source='session_end_hook'`

**From the WorkflowEngine** (v3 application layer): State machine transitions via `advance_status()`, `start_work()`, `complete_work()` MCP tools all log to audit_log.

### Coverage Assessment

The audit log is NOT comprehensive. It misses:

- Direct `claude.todos` status changes that don't go through task_sync_hook
- Feature status changes not made via WorkflowEngine tools
- Session start/end events (those are in `claude.sessions`, not audit_log)
- MCP tool failures
- Knowledge create/update operations

It only captures: WorkflowEngine-mediated work item transitions and hook-triggered build_task bridges.

### Assessment

- **Status**: Working, but limited scope
- **Value**: Medium - useful for build_task lifecycle tracking; missing broad governance audit trail
- **Gap**: No single table captures all system events

---

## 4. Failure Capture (`scripts/failure_capture.py`)

### How It Works

`capture_failure()` is called from the `except` blocks of 8 hooks. It:
1. Always appends to `~/.claude/process_failures.jsonl` (survives DB outages)
2. Queries `claude.projects` for the project_id
3. Checks for existing unresolved feedback with the same title (deduplication)
4. Inserts a new `claude.feedback` record with type='bug', status='new', priority='medium'
5. Returns `{captured, feedback_id, logged}`

`get_pending_failures()` is called by `rag_query_hook.py` to surface pending failures in Claude's context. It queries `claude.feedback` for 'Auto: % failure' titles in 'new' or 'triaged' status within the last 48 hours.

### JSONL Failure Log State

The `process_failures.jsonl` has 4 entries total:
- 3 from 2026-02-20 sourced from `test_e2e_validation.py` (deliberate test, note `"filed_as_feedback": false` which is the old hardcoded field - not the DB filing result)
- 1 from 2026-03-05 sourced from `rag_query_hook.py` with error `[Errno 22] Invalid argument`

The March 5 `rag_query_hook` failure with `Invalid argument` is notable - this is a Windows file handle error, likely during log file writes. It was auto-filed as feedback in the DB.

The `"filed_as_feedback": false` field in all JSONL entries is the hardcoded default in the entry dict, not the actual DB filing result (the DB filing is tracked separately). This is a minor misleading data quality issue.

### Assessment

- **Status**: Working
- **Value**: High - self-healing loop is the right design
- **Volume**: Low (4 JSONL entries, likely more in DB). Low volume may indicate hooks are robust, or that the feedback filing deduplication is collapsing real failures
- **Gap**: The JSONL `filed_as_feedback` field is always `false` regardless of actual DB filing outcome - misleading

---

## 5. Subagent Logging (`scripts/subagent_start_hook.py` → `claude.agent_sessions`)

### How It Works

Fires on `SubagentStart` event. Extracts: `subagent_id`, `subagent_type`, `task_prompt` (truncated to 1000 chars), `parent_session_id`, `workspace_dir`. Inserts to `claude.agent_sessions` with `ON CONFLICT DO UPDATE` to handle retries.

### Data Quality Issues

The hooks.log reveals a significant problem: multiple entries show:

```
Agent spawned: type=unknown, id=N/A..., parent=92a4e46e...
```

The `subagent_id` is coming through as empty string or None, and `subagent_type` as 'unknown'. This means the `SubagentStart` hook input fields (`subagent_id`, `subagent_type`) are not being populated by Claude Code, or the field names differ from what the script expects.

With `if subagent_id:` gating the DB insert, all `id=N/A` entries are silently dropped - they never make it to `claude.agent_sessions`.

The `~/.claude/projects/` directory contains 100+ subagent JSONL files organized by session and agent ID, confirming significant agent activity that is NOT being captured in `claude.agent_sessions`.

### Assessment

- **Status**: Broken - most spawns not logged to DB
- **Value**: Low in current state (data is not being captured)
- **Root cause**: `hook_input.get('subagent_id', '')` returns empty - the Claude Code SubagentStart hook event likely does not pass `subagent_id` as documented, or the field name differs
- **Alternative data**: The JSONL files at `~/.claude/projects/*/subagents/agent-*.jsonl` are the actual ground truth for agent activity

---

## 6. Task Sync (`scripts/task_sync_hook.py` + `scripts/todo_sync_hook.py`)

### TodoWrite Sync (`todo_sync_hook.py`)

Fires on PostToolUse for `TodoWrite` tool. Reads the todos array from `tool_input`, then for each todo:
- Finds an existing matching todo by content similarity (75% threshold)
- Updates existing or inserts new, tracking `created_session_id` and `completed_session_id`
- Maps `deleted` status to `archived` to preserve audit trail
- Does NOT auto-delete todos missing from the call (prevents accidental deletion)

### TaskCreate/TaskUpdate Sync (`task_sync_hook.py`)

Fires on PostToolUse for `TaskCreate` and `TaskUpdate`. For TaskCreate:
- Extracts task number from tool_response JSON
- Checks for duplicate todos (substring containment + 75% fuzzy threshold)
- Inserts new todo or increments `restore_count` on existing
- Checks for matching `build_tasks` by name similarity and stores bridge in the task_map JSON

For TaskUpdate:
- Looks up the task_map for the task_number
- Updates the todo status in DB
- If bridged to a build_task, also updates build_task status and writes audit_log
- Auto-checkpoints `claude.session_state` on task completion

### Reliability Assessment

The task_sync hook uses `msvcrt` Windows file locking for the task_map JSON - correct for this Windows environment. The 60-second dedup guard in session startup correctly resets the task_map.

One known issue (from MEMORY.md): "Context compaction orphans tasks: Pre-compaction in_progress tasks get duplicated post-compaction." This is a known unfixed bug.

The `get_current_session_id()` query in task_sync uses `session_end IS NULL` - on startup before the new session is logged, this could briefly return the old session's ID (before the 60-second dedup fires).

### Assessment

- **Status**: Working (with known compaction edge case)
- **Value**: High - bridges Claude's in-memory task system to persistent DB
- **Reliability**: Good, with the build_task bridge adding useful automation

---

## Data Volumes and Freshness Summary

| System | Storage | Freshness | Volume |
|---|---|---|---|
| Session logging | `claude.sessions` | Active (last log: 2026-03-07) | Unknown DB count, 52 orphaned in fallback |
| MCP usage | `claude.mcp_usage` | Active (per-prompt) | Unknown, estimated thousands of rows |
| Audit log | `claude.audit_log` | Active (on transitions) | Unknown, limited to WorkflowEngine scope |
| Failure capture | `process_failures.jsonl` + `claude.feedback` | Low activity (4 JSONL entries) | 4 JSONL, unknown DB count |
| Subagent logging | `claude.agent_sessions` | Broken (no valid IDs) | 100+ JSONL files unlogged |
| Todo sync | `claude.todos` | Active (every TodoWrite) | Unknown |
| hooks.log | `~/.claude/hooks.log` | Active (77,000+ lines) | ~77K lines, unrotated |

**The hooks.log has no rotation configured** - it has grown to at least 77,395 lines covering 2026-02-13 through 2026-03-07. It will grow unboundedly.

---

## Missing Monitoring Gaps

1. **No session duration tracking** - `session_end IS NULL` orphans accumulate without any automatic cleanup job. The session_end hook failure (52 fallback entries) means the duration of most sessions is unknown in the DB.

2. **No replay of session_end fallback** - The `hook_data_fallback.py` `replay_fallback()` function exists but nothing calls it for `session_end`. Those 52 sessions will never be auto-closed.

3. **Subagent activity is invisible** - 100+ agent spawns are happening (evidenced by JSONL files) but `claude.agent_sessions` gets nothing due to the empty `subagent_id` field issue.

4. **No hooks.log rotation** - 77K+ lines in a single file. There is no logrotate config for this file.

5. **No cross-project dashboard** - MCP usage, session data, and todos are per-project in practice (via `project_name` filter) but there is no aggregate view of system health across all Claude instances.

6. **RAG query outcomes not surfaced** - `rag_query_hook.py` logs RAG results to DB but there is no report of RAG hit/miss rates or which queries are consistently returning nothing.

7. **No hook execution latency tracking** - The `execution_time_ms` in `claude.mcp_usage` measures hook overhead (2-5ms), not actual MCP tool execution time. Real tool latency is unknown.

---

## Recommendations

### Keep and Improve

**Session logging**: The design is correct. Fix the orphan problem by adding a `replay_fallback("session_end", ...)` call at the top of `session_startup_hook_enhanced.py`. This would close the 52 pending records on next startup. Also add a SQL job or startup check that closes sessions older than 24 hours that still have `session_end IS NULL`.

**MCP usage logging**: Working well. The execution time measurement is misleading - rename the column to `hook_overhead_ms` or add a comment clarifying what is measured.

**Task sync**: Working well. The compaction duplication bug should be addressed - the `task_discipline_hook.py` should clear in_progress tasks from the task_map after compaction rather than carrying them forward.

**Failure capture**: Working. Fix the `filed_as_feedback` misleading field - either remove it from the JSONL entry dict or populate it correctly with the actual DB filing outcome.

### Fix Urgently

**Subagent logging**: The `subagent_id` field is not being received. The hook script should log the full raw hook_input to hooks.log when `subagent_id` is empty, to diagnose the actual field names Claude Code sends. Until fixed, this table provides no value.

**hooks.log rotation**: Add a log rotation configuration. At 77K lines with no rotation, this will become a maintenance problem and slow hook startup.

**Session fallback replay**: Add `replay_fallback("session_end", ...)` to the startup hook to recover the 52+ orphaned sessions.

### Consider Dropping

**Audit log as a governance tool**: The current audit_log only captures a subset of transitions (WorkflowEngine-mediated + task_sync bridge). It is useful for the specific cases it covers but does not provide system-wide governance visibility. Either expand it to all tables via triggers or document its scope clearly and stop treating it as a full audit trail.

---

## Relevant File Paths

- `/C:/Projects/claude-family/scripts/session_startup_hook_enhanced.py`
- `/C:/Projects/claude-family/scripts/session_end_hook.py`
- `/C:/Projects/claude-family/scripts/mcp_usage_logger.py`
- `/C:/Projects/claude-family/scripts/failure_capture.py`
- `/C:/Projects/claude-family/scripts/subagent_start_hook.py`
- `/C:/Projects/claude-family/scripts/task_sync_hook.py`
- `/C:/Projects/claude-family/scripts/todo_sync_hook.py`
- `/C:/Projects/claude-family/scripts/hook_data_fallback.py`
- `/C:/Projects/claude-family/scripts/precompact_hook.py`
- `/C:/Users/johnd/.claude/hooks.log` (77,000+ lines, no rotation)
- `/C:/Users/johnd/.claude/process_failures.jsonl` (4 entries)
- `/C:/Users/johnd/.claude/hook_fallback/session_end_fallback.jsonl` (52 unresolved entries)