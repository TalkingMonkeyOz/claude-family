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

## Recent Changes

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

**Version**: 3.0 (Full rewrite: added task_discipline docs, enforcement chain, GATED_TOOLS)
**Created**: 2025-12-26
**Updated**: 2026-02-18
**Location**: Claude Family/Claude Hooks.md
