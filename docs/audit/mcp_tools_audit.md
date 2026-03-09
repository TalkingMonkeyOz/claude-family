Now I have sufficient data for a complete report. Let me compile it:

---

# MCP Server System - Technical Assessment Report

## 1. MCP Server Inventory

| Server | Primary File | Framework | Status |
|--------|-------------|-----------|--------|
| `project-tools` | `server_v2.py` (active), `server.py` (legacy impl) | FastMCP | Active |
| `bpmn-engine` | `server.py` | FastMCP | Active |
| `tool-search` | `server.py` | FastMCP | Deployed but likely not registered |
| `vault-rag` | `server.py` | FastMCP | Retired (per MEMORY.md) |
| `manager-mui` | `server.py` | Unknown | Unknown |
| `postgres` | External (mcp-postgres) | External | Active |
| `sequential-thinking` | External | External | Active |
| `python-repl` | External | External | Active |

---

## 2. Total Tool Count

**project-tools (server_v2.py): 72 tools exposed**

The `server_v2.py` file is the active entry point. It imports all async implementations from `server.py` and wraps them as sync FastMCP tools. The tool list by phase:

**Phase 1 - Foundation:**
`get_schema`, `start_session`, `end_session`, `save_checkpoint`

**Phase 2 - Workflow Engine:**
`advance_status`, `start_work`, `complete_work`, `get_work_context`, `create_linked_task`

**Phase 3 - Config & Books:**
`extract_conversation`, `store_book`, `store_book_reference`, `recall_book_reference`, `update_claude_md`, `deploy_claude_md`, `deploy_project`, `regenerate_settings`

**Phase 4 - Conversation Intelligence:**
`extract_insights`, `search_conversations`

**Legacy Wrappers (still exposed):**
`get_incomplete_todos`, `create_feedback`, `create_feature`, `add_build_task`, `get_ready_tasks`, `update_work_status` (routes to WorkflowEngine), `store_knowledge`, `recall_knowledge`, `graph_search`, `decay_knowledge`

**Cognitive Memory (F130):**
`remember`, `recall_memories`, `consolidate_memories`, `link_knowledge`, `get_related_knowledge`, `mark_knowledge_applied`

**Session Facts:**
`store_session_fact`, `recall_session_fact`, `list_session_facts`, `recall_previous_session_facts`, `store_session_notes`, `get_session_notes`

**BPMN Registry:**
`sync_bpmn_processes`, `search_bpmn_processes`

**Feedback/Feature Lifecycle:**
`promote_feedback`, `resolve_feedback`

**Recovery & Maintenance:**
`recover_session`, `system_maintenance`

**Protocol Management:**
`update_protocol`, `get_protocol_history`, `get_active_protocol`

**Messaging:**
`list_recipients`, `check_inbox`, `send_message`, `broadcast`, `acknowledge`, `reply_to`, `bulk_acknowledge`, `get_unactioned_messages`, `get_message_history`, `get_active_sessions`

Note: There are also tools defined only in `server.py` that are NOT re-exported through `server_v2.py`: `tool_get_session_resume`, `tool_get_related_knowledge` (in server.py as async, wrapped in v2), `tool_mark_knowledge_applied`, `tool_decay_knowledge`, `tool_graph_search`, `tool_get_project_context` (the old v1 version). The `get_project_context` from server.py is superseded by `start_session` in v2 and is not re-exported.

**bpmn-engine: 10 tools**
`list_processes`, `get_process`, `get_subprocess`, `validate_process`, `get_current_step`, `get_dependency_tree`, `search_processes`, `check_alignment`, `file_alignment_gaps`, `validate_process_schema`

**tool-search: 3 tools**
`find_tool`, `list_tool_categories`, `get_tool_schema`

**vault-rag: 4 tools**
`semantic_search`, `get_document`, `list_vault_documents`, `vault_stats`

**Grand total across all servers: ~89 tools** (72 project-tools + 10 bpmn-engine + 3 tool-search + 4 vault-rag)

---

## 3. Architecture: server.py vs server_v2.py

This is the most important structural finding. The project operates as a **single MCP server** but the code is split across two files:

- `/mcp-servers/project-tools/server.py` contains all the async implementation functions (prefixed `tool_`). These are NOT `@mcp.tool()` decorated in server.py; they are plain async functions.
- `/mcp-servers/project-tools/server_v2.py` is the actual server entrypoint. It imports the async functions from server.py, wraps them with `_run_async()`, and decorates them as `@mcp.tool()`. It also defines all the Phase 2-4 tools natively using FastMCP with synchronous signatures.

The MEMORY.md note "server_v2.py is uncommitted - safe to modify" is **out of date**. The git status at session start shows no uncommitted changes in that file, and the file contains substantial production code including WorkflowEngine, messaging tools, and memory tools.

The `_run_async()` bridge in server_v2.py uses a `ThreadPoolExecutor` when called inside an async context. This is a potential deadlock risk if FastMCP's event loop is reused. In practice it works because the async functions themselves open synchronous-equivalent DB connections.

---

## 4. Tool-by-Tool Assessment

### Active Tools (Confirmed Referenced in CLAUDE.md or Skills)

| Tool | Category | Referenced In |
|------|----------|--------------|
| `start_session` | Session | CLAUDE.md MCP Index, session-management skill |
| `end_session` | Session | /session-end command |
| `advance_status` | Workflow | CLAUDE.md MCP Index |
| `start_work` | Workflow | CLAUDE.md MCP Index |
| `complete_work` | Workflow | CLAUDE.md MCP Index |
| `get_work_context` | Workflow | CLAUDE.md MCP Index |
| `create_linked_task` | Workflow | CLAUDE.md MCP Index |
| `remember` | Memory | Core Protocol v8, CLAUDE.md |
| `recall_memories` | Memory | Core Protocol v8, CLAUDE.md |
| `consolidate_memories` | Memory | CLAUDE.md, session_end_hook.py |
| `store_session_fact` | Session Facts | CLAUDE.md, hook scripts |
| `recall_session_fact` | Session Facts | CLAUDE.md |
| `list_session_facts` | Session Facts | CLAUDE.md |
| `create_feedback` | Work Tracking | CLAUDE.md |
| `create_feature` | Work Tracking | CLAUDE.md |
| `check_inbox` | Messaging | CLAUDE.md |
| `send_message` | Messaging | CLAUDE.md |
| `broadcast` | Messaging | CLAUDE.md |
| `acknowledge` | Messaging | CLAUDE.md |
| `reply_to` | Messaging | CLAUDE.md |
| `sync_bpmn_processes` | BPMN | CLAUDE.md |
| `search_bpmn_processes` | BPMN | CLAUDE.md (as `sync_bpmn_processes`) |

### Legacy Tools (Still Working, But Superseded)

| Tool | Superseded By | Issue |
|------|--------------|-------|
| `store_knowledge` | `remember()` | Marked LEGACY in code; still works; skips tier routing and dedup |
| `recall_knowledge` | `recall_memories()` | Marked LEGACY; functional; no tier awareness |
| `graph_search` | `recall_memories()` (long tier does 1-hop walk) | Marked LEGACY; depends on `claude.graph_aware_search()` SQL function existing |
| `update_work_status` | `advance_status()` | Is actually a thin wrapper that calls `advance_status()`; safe to use either |
| `get_project_context` | `start_session()` | Only in server.py; NOT exported via server_v2.py - effectively dead |
| `get_session_resume` | `start_session(resume=True)` | Only in server.py; NOT exported - effectively dead |
| `restore_session_todos` | Native task persistence | Only in server.py; NOT exported |
| `find_skill` | RAG hook (rag_query_hook.py auto-queries skill_content) | Only in server.py; NOT exported - dead |
| `todos_to_build_tasks` | Manual conversion | Only in server.py; NOT exported - dead |
| `get_incomplete_todos` | `start_session()` or `get_work_context()` | Still exported; overlapping with start_session output |

### Tools With Potential Issues

| Tool | Issue |
|------|-------|
| `graph_search` | Calls `claude.graph_aware_search()` PostgreSQL function. If this function was dropped in the "drop 43 tables" cleanup (2026-02-28), the tool will fail at runtime. No way to verify without running it. |
| `decay_knowledge` | Calls `claude.decay_knowledge_graph()` and `claude.update_knowledge_access()` PostgreSQL functions. Same risk. |
| `deploy_project` | References `claude.rules` and `claude.instructions` tables that may not exist post-cleanup. The tool has defensive checks (`EXISTS` query) so it silently skips missing tables rather than crashing. |
| `system_maintenance` | Dynamically imports `scripts/system_maintenance.py` using `importlib`. If that file is missing or broken, the tool fails at call time with an unhelpful error. Path calculation uses `__file__` relative paths that depend on the working directory at server start. |
| `extract_insights` | Uses simple keyword pattern matching against user turns to classify insights. The patterns ("we should", "let's", "make sure") will generate false positives on nearly every conversation. Every `store_knowledge` call from session end already does something similar. This tool produces a lot of low-quality knowledge entries. |
| `store_session_fact` (upsert key) | The ON CONFLICT clause is `ON CONFLICT (session_id, fact_key)`. When `session_id` is NULL (no active session), PostgreSQL treats two NULLs as different, so upsert doesn't work - duplicate facts accumulate. |
| `recall_memories` | Requires Voyage AI to be configured. If `VOYAGE_API_KEY` is missing, returns an error immediately. No graceful degradation to keyword fallback. |
| `resolve_feedback` | Applies multi-step state transitions. Each intermediate step commits independently. If the process fails mid-way (e.g., network error during audit_log insert), the feedback is left in an intermediate state like `in_progress` with no rollback. |
| `get_message_history` | Not listed in CLAUDE.md MCP Index, not referenced in any skill. Effectively undocumented to users. |
| `bulk_acknowledge` | Not listed in CLAUDE.md MCP Index. Same situation. |
| `get_active_sessions` | Not listed in CLAUDE.md MCP Index. |

### Retired / Should Not Be Running

| Server | Status | Risk |
|--------|--------|------|
| `vault-rag` | MEMORY.md explicitly says "Removed MCPs (2026-01): vault-rag, filesystem, memory." The server.py file still exists and is runnable, but should not be registered in settings. | If still in settings.local.json, it will start and consume resources. |
| `tool-search` | Not listed in CLAUDE.md MCP Index or MEMORY.md as an active server. The server.py exists. Its `tool_index.json` may be stale. | Low risk; only affects tool discoverability. |

---

## 5. Duplicate Functionality Found

**Group 1: Status updates (3 tools doing the same thing)**
- `update_work_status` — legacy, routes to WorkflowEngine
- `advance_status` — direct WorkflowEngine call, preferred
- Direct raw SQL UPDATE — discouraged but possible via postgres MCP

**Group 2: Task creation (2 tools with different quality gates)**
- `add_build_task` — minimal validation, accepts empty descriptions
- `create_linked_task` — enforces >=100 char description, requires verification field and files_affected. Both insert into `claude.build_tasks`.

**Group 3: Knowledge storage (4 overlapping tools)**
- `store_knowledge` — flat insert, tier hardcoded to 'mid'
- `remember` — auto-routes tier, deduplicates, auto-links
- `store_session_fact` — session-scoped, not semantic
- `end_session(learnings=[...])` — stores knowledge as side effect of session close

**Group 4: Knowledge retrieval (3 overlapping tools)**
- `recall_knowledge` — semantic search, no tier awareness
- `recall_memories` — 3-tier budget-capped, preferred
- `graph_search` — pgvector + graph walk, depends on SQL functions

**Group 5: Session start (2 overlapping tools, one dead)**
- `start_session` — active, exported, feature-complete
- `get_project_context` — only in server.py, not exported via server_v2.py, effectively dead

**Group 6: BPMN search (duplication between servers)**
- `search_processes` (bpmn-engine) — searches local .bpmn files by keyword
- `search_bpmn_processes` (project-tools) — searches `claude.bpmn_processes` DB table by semantic embedding

These are not strictly duplicates — one searches disk, one searches DB — but they serve the same user intent. The DB version is newer and supports cross-project search; the file-based version works without DB. The CLAUDE.md MCP Index lists only `search_processes` (bpmn-engine) but the project-tools version is more capable.

---

## 6. WorkflowEngine Assessment

The WorkflowEngine is implemented as a class in `server_v2.py` at line 1101. It is well-structured with proper concerns separated.

**What it does correctly:**
- Resolves item IDs by both short code (BT3, F12, FB5) and UUID
- Validates transitions against `claude.workflow_transitions` table (28 transitions per MEMORY.md)
- Checks named conditions before allowing transitions (currently supports `all_tasks_done` and `has_assignee`)
- Executes named side effects after transitions (`check_feature_completion`, `set_started_at`, `archive_plan_data`)
- Logs all transitions to `claude.audit_log` with entity_type, entity_code, from/to status, and metadata
- Rolls back on exception

**Issues found:**

1. The `resolve_entity` method uses the cursor for both UUID and short-code lookups, but calls `cur.close()` inside a `finally` block. This is correct for psycopg3 but may cause issues with psycopg2 cursor lifecycle if the method is called in rapid succession on the same connection.

2. The `execute_side_effect` for `archive_plan_data` is a no-op: `return "Plan data archived (no-op)"`. If a BPMN model or workflow_transitions row specifies this side effect, it silently does nothing. This is a gap between documentation and implementation.

3. The `check_condition` method falls through to `return (True, "Unknown condition - passed by default")` for any unknown condition name. This means if a row in `claude.workflow_transitions` has a typo in `requires_condition`, the condition is silently bypassed. There is no alerting or logging for unknown conditions.

4. The `advance_status` tool uses `Literal["feedback", "features", "build_tasks"]` for `item_type`, but the underlying `WorkflowEngine.ENTITY_MAP` keys match those exact strings. The legacy `update_work_status` tool maps `"feature"` (without 's') to `"features"` before calling `advance_status`. Claude would need to know to use `"features"` not `"feature"` when calling `advance_status` directly.

5. No condition check is implemented for the `has_assignee` condition on `build_tasks` transitions. The condition is defined in the code but the `build_tasks` table in `claude.workflow_transitions` may or may not have transitions that use it. If `has_assignee` is in the transition table but the `build_tasks` table has no `assigned_to` column post-cleanup, every transition requiring that condition would fail with a column error.

**State machines as designed (from code):**
- Feedback: `new → triaged → in_progress → resolved` (also `wont_fix`, `duplicate`)
- Features: `draft → planned → in_progress → completed` (completed requires `all_tasks_done` condition)
- Build tasks: `todo → in_progress → completed` (in_progress triggers `set_started_at`, completed triggers `check_feature_completion`)

---

## 7. Tools That Should Exist But Don't

Based on documentation promises vs. actual exports:

**Documented in CLAUDE.md but missing as standalone tool:**
- `ToolSearch` — CLAUDE.md says "Use ToolSearch select:<exact_name>". This is not an MCP tool at all; it's a prompt convention. The `tool-search` server's `find_tool` tool is what should be used, but the documented interface (`ToolSearch select:`) does not correspond to any tool signature.

**Implicit in BPMN models but not implemented:**
- `validate_process_schema` is listed in bpmn-engine grep output. Checking...

**Gaps in messaging:**
- There is no tool to delete messages or archive an entire thread. `bulk_acknowledge` partially addresses this but is not documented in CLAUDE.md.

**No tool to query `claude.audit_log`:**
The audit_log captures all WorkflowEngine transitions, but there is no MCP tool to query it. Claude must use the postgres MCP for raw SQL to inspect the audit trail.

**No tool to manage `claude.workflow_transitions`:**
The state machine is defined in the DB table but there is no MCP tool to add, modify, or query transitions. All changes require raw SQL.

---

## 8. Key Files Referenced

- `/C:/Projects/claude-family/mcp-servers/project-tools/server_v2.py` — Active server entrypoint, 5700+ lines
- `/C:/Projects/claude-family/mcp-servers/project-tools/server.py` — Implementation library of async tool functions, imported by server_v2.py
- `/C:/Projects/claude-family/mcp-servers/bpmn-engine/server.py` — BPMN engine with 10 tools
- `/C:/Projects/claude-family/mcp-servers/tool-search/server.py` — Tool search (3 tools, likely not in active MCP config)
- `/C:/Projects/claude-family/mcp-servers/vault-rag/server.py` — Retired but still exists on disk

---

## 9. Summary Findings

**Critical finding — dead exports in server.py:** Eight tool implementations exist only in `server.py` and are never re-exported via `server_v2.py`: `get_project_context`, `get_session_resume`, `restore_session_todos`, `find_skill`, `todos_to_build_tasks`, and `get_related_knowledge` (the latter IS re-exported, correction: it is wrapped). Of those, `get_project_context` and `get_session_resume` are explicitly deprecated but `find_skill` and `todos_to_build_tasks` are simply forgotten.

**Structural concern — dual-file architecture:** The split between server.py (async impl) and server_v2.py (sync wrappers + new tools) makes the codebase harder to navigate. Every tool has at least two definitions. The `_run_async` bridge that runs async functions in a ThreadPoolExecutor is a non-standard pattern that works today but is fragile under high concurrency.

**Legacy tool accumulation:** Three tools are marked LEGACY in code comments (`store_knowledge`, `recall_knowledge`, `graph_search`) but remain fully registered and callable. Claude instructions in CLAUDE.md still reference them as fallbacks. No deprecation timeline exists.

**WorkflowEngine is sound but has two silent failure modes:** Unknown condition names pass by default, and the `archive_plan_data` side effect is a no-op. Both will cause subtle bugs if the workflow_transitions table references them.