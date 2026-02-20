---
projects:
- claude-family
synced: true
synced_at: '2026-02-18T12:00:00.000000'
tags:
- hooks
- quick-reference
- claude-family
- enforcement
---

# Claude Hooks

Enforcement layer for Claude Family governance.

## Active Hooks

| Order | Event | Script | Matcher | Purpose |
|-------|-------|--------|---------|---------|
| 1 | SessionStart | `session_startup_hook_enhanced.py` | (once) | Log session, load state, auto-archive stale todos, reset task map |
| 2 | UserPromptSubmit | `rag_query_hook.py` | (all) | CORE_PROTOCOL injection + RAG context + session facts |
| 3 | PreToolUse | `task_discipline_hook.py` | Write, Edit, Task, Bash | **Block** tool calls if no tasks created this session |
| 4 | PreToolUse | `context_injector_hook.py` | Write, Edit | Inject coding standards from context_rules |
| 5 | PreToolUse | `standards_validator.py` | Write, Edit | Validate content against standards |
| 6 | PostToolUse | `todo_sync_hook.py` | TodoWrite | Sync todos to claude.todos |
| 7 | PostToolUse | `task_sync_hook.py` | TaskCreate, TaskUpdate | Sync tasks to claude.todos + task map file |
| 8 | PostToolUse | `mcp_usage_logger.py` | (catch-all) | Log MCP tool usage (filters to mcp__ prefix) |
| 9 | SubagentStart | `subagent_start_hook.py` | (all) | Log agent spawns to agent_sessions |
| 10 | PreCompact | `precompact_hook.py` | manual, auto | Inject active todos, features, session state |
| 11 | SessionEnd | `session_end_hook.py` | (all) | Auto-close session in database |

### Infrastructure-Only Hooks (claude-family project)

| Event | Script | Matcher | Purpose |
|-------|--------|---------|---------|
| PreToolUse | `validate_db_write.py` | mcp__postgres__execute_sql | Validate against column_registry |
| PreToolUse | `validate_phase.py` | mcp__postgres__execute_sql | Check project phase for task creation |
| PreToolUse | `validate_parent_links.py` | mcp__postgres__execute_sql | Prevent orphan records |

## Enforcement Chain

```
User message
    ↓
UserPromptSubmit (rag_query_hook.py)
    → Injects CORE_PROTOCOL: "Break into tasks BEFORE doing anything"
    → Advisory only (cannot block)
    ↓
Claude tries to use Write/Edit/Task/Bash
    ↓
PreToolUse (task_discipline_hook.py)
    → Checks task map file for current-session tasks
    → If no tasks: BLOCKS with "Use TaskCreate first"
    → If tasks exist + session match: ALLOWS
    ↓
PreToolUse (context_injector + standards_validator)
    → Injects standards, validates content
    ↓
Tool executes
    ↓
PostToolUse (sync hooks)
    → Persist to database
```

**Key distinction**: CORE_PROTOCOL is persuasion (advisory). task_discipline_hook is enforcement (blocking).

## GATED_TOOLS (What Gets Blocked)

| Tool | Gated? | Why |
|------|--------|-----|
| Write | Yes | File creation must be planned |
| Edit | Yes | File modification must be planned |
| Task | Yes | Agent spawning must be planned |
| Bash | Yes | Shell commands often do investigation work |
| Read | No | Passive exploration - needed to assess before planning |
| Grep | No | Passive search |
| Glob | No | Passive file finding |
| MCP tools | No | Tool usage logged but not gated |

## Config Flow

```
Database (claude.config_templates id=1 "hooks-base")
    ↓
+ project_type_configs (mcp_servers, skills, instructions)
    ↓
+ workspaces.startup_config (project-specific overrides)
    ↓
generate_project_settings.py (deep_merge)
    ↓
.claude/settings.local.json (generated, DO NOT edit manually)
```

**Source of truth**: `claude.config_templates` table (template_id=1)
**Regenerate**: `python scripts/generate_project_settings.py <project-name>`
**Merge behavior**: Lists append (not replace), dicts recurse. Empty list overrides are harmless.
**Important**: Hooks MUST be in `settings.local.json`, NOT `hooks.json`!

## Task Discipline Details

**Script**: `scripts/task_discipline_hook.py`
**Session scoping**: Uses `_session_id` in task map file (written by `task_sync_hook.py` on TaskCreate)
**Stale detection**: Compares map's `_session_id` with current session from hook input
**Fail-open**: Any script error → allow (never blocks workflow due to hook crash)
**Response format**: Exit 0 + JSON `permissionDecision: "deny"` (NOT exit code 2)

### 4-Way Decision Cascade (FB108 + FB109)

```
1. Tasks exist + session match → ALLOW (normal case)
2. Tasks exist + no session_id → ALLOW (edge case)
3. Empty map but recently modified (< 30s) → ALLOW (race condition)
4. Tasks exist + session mismatch + map fresh (< 2h) → ALLOW (continuation session - FB108)
5. DB fallback: query build_tasks for active tasks → ALLOW (covers MCP create_linked_task - FB109)
6. Otherwise → DENY
```

**FB108 fix**: Continuation sessions get new session_id after compaction, but tasks from prior segment are still valid if map is fresh (< 2h).
**FB109 fix**: MCP `create_linked_task` writes to DB only (not task_map file). DB fallback query catches this on the deny path only (no perf impact on normal flow).

## Failure Capture System (2026-02-20)

All hooks with fail-open catch blocks now call `capture_failure()` from `scripts/failure_capture.py`:

**Integrated hooks** (8 total): task_discipline, rag_query, context_injector, todo_sync, task_sync, precompact, session_end, standards_validator

**How it works**:
1. Hook crashes → fail-open catch block calls `capture_failure(system_name, error, source_file)`
2. Failure logged to `~/.claude/process_failures.jsonl` (survives if DB is down)
3. Auto-filed as feedback in `claude.feedback` (type=bug, title="Auto: {hook} failure")
4. Deduplication: won't re-file if identical open feedback exists
5. `rag_query_hook.py` surfaces pending failures via `get_pending_failures()` → injected into context
6. Claude sees failures on next prompt and can invoke the system-change-process to fix

**Self-improvement loop**: Failure → Auto-feedback → Claude sees it → BPMN model update → Code fix → Commit

## BPMN Process Coverage

Hooks and workflows are modeled in BPMN (SpiffWorkflow). See `mcp-servers/bpmn-engine/processes/`.

| BPMN Process | Level | What It Models |
|-------------|-------|----------------|
| `hook_chain.bpmn` | L2 | Full hook execution chain (text/tool paths) |
| `session_lifecycle.bpmn` | L2 | Fresh/resumed session + compact flow |
| `task_lifecycle.bpmn` | L2 | Task create → discipline gate → sync → complete |
| `session_continuation.bpmn` | L2 | Context compaction + session recovery |
| `rag_pipeline.bpmn` | L2 | Embedding + retrieval + self-learning |

**Alignment tool**: `check_alignment(process_id)` MCP tool compares BPMN models against actual code artifacts.

## Recent Changes

**2026-02-20**:
- FB108 resolved: Continuation session handling in discipline hook
- FB109 resolved: DB fallback for MCP-created build_tasks
- Failure capture system: auto-file failures as feedback, surface in context
- All 8 hooks integrated with failure_capture.py
- BPMN process coverage: 15 L2 processes, alignment validation tool

**2026-02-18**:
- Added `Bash` to GATED_TOOLS (was missing - 90% of investigation bypassed enforcement)
- Strengthened CORE_PROTOCOL text with explicit "actionable work" definition
- Fixed claude-family workspace startup_config (had dead empty PreToolUse/UserPromptSubmit overrides)
- Fixed nimbus-mui: was running completely outdated config without any enforcement hooks
- DB config_templates updated + all 3 projects regenerated from DB

**2026-02-07**:
- SessionEnd hook: prompt type → command type (`session_end_hook.py`)
- PreCompact hook: now queries DB for active todos, features, session state
- PostToolUse MCP logger: 68 individual matchers → catch-all pattern
- Added `context_injector_hook.py` and `subagent_start_hook.py`

---

**Version**: 4.0 (Added FB108/FB109 decision cascade, failure capture system, BPMN coverage)
**Created**: 2025-12-26
**Updated**: 2026-02-20
**Location**: Claude Family/Claude Hooks.md
