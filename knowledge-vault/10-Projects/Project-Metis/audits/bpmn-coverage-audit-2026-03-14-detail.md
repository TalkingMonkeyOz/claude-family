---
projects:
- claude-family
tags:
- bpmn
- audit
- infrastructure
synced: false
---

# BPMN Coverage Audit — Detail Tables (2026-03-14)

Parent: [[bpmn-coverage-audit-2026-03-14]]

---

## Hook-to-Model Mapping

| Hook Script | Hook Event | Dedicated BPMN | Composite Coverage | Status |
|---|---|---|---|---|
| `session_startup_hook_enhanced.py` | SessionStart | None | `session_lifecycle.bpmn` | Gap |
| `rag_query_hook.py` | UserPromptSubmit | `rag_pipeline.bpmn` | `hook_chain.bpmn` | Covered |
| `task_discipline_hook.py` | PreToolUse (Write/Edit/Task/Bash) | None | `hook_chain.bpmn` | Gap |
| `context_injector_hook.py` | PreToolUse (Write/Edit) | None | `content_validation.bpmn` | Gap |
| `standards_validator.py` | PreToolUse (Write/Edit) | `content_validation.bpmn` | `hook_chain.bpmn` | Covered |
| `sql_governance_hook.py` | PreToolUse (postgres execute_sql) | None | `schema_governance.bpmn` (partial) | Gap |
| `todo_sync_hook.py` | PostToolUse (TodoWrite) | `todo_sync.bpmn` | `hook_chain.bpmn` | Covered |
| `task_sync_hook.py` | PostToolUse (TaskCreate/TaskUpdate) | `task_sync.bpmn` | `task_lifecycle.bpmn` | Covered |
| `mcp_usage_logger.py` | PostToolUse (all) | `mcp_usage_logging.bpmn` | `hook_chain.bpmn` | Covered |
| `session_end_hook.py` | SessionEnd | `session_end.bpmn` | `session_lifecycle.bpmn` | Covered |
| `precompact_hook.py` | PreCompact | `precompact.bpmn` | `context_preservation.bpmn` | Covered |
| `subagent_start_hook.py` | SubagentStart | `subagent_start.bpmn` | `agent_lifecycle.bpmn` | Covered |
| `failure_capture.py` | (library) | `failure_capture.bpmn` | — | Covered |
| `hook_data_fallback.py` | (library) | None | `failure_capture.bpmn` (implicit) | Gap |

---

## Plugin Scripts Without BPMN Coverage

Registered in `settings.local.json` under PreToolUse for `mcp__postgres__execute_sql`. Live in `.claude-plugins/claude-family-core/scripts/`.

| Script | Purpose | Gap |
|---|---|---|
| `validate_db_write.py` | column_registry enforcement | No model |
| `validate_phase.py` | Phase-gate for build_task creation | No model |
| `validate_parent_links.py` | Orphan-prevention for work items | No model |
| `context_monitor_statusline.py` | Context budget status display | No model |

---

## Models Without Corresponding Scripts

Valid — these model MCP-layer or DB-layer processes, not standalone scripts.

| Model | Maps To |
|---|---|
| `workfile_management.bpmn` | `project-tools` MCP (`stash`/`unstash`) |
| `context_preservation.bpmn` | `precompact_hook.py` + session facts pattern |
| `credential_loading.bpmn` | `config.py` shared module |
| `schema_governance.bpmn` | DB constraints + column_registry |
| `database_cleanup.bpmn` | Manual operation |
| `client_domain_schema.bpmn` | DB schema design |
| `bpmn_sync.bpmn` | `scripts/sync_bpmn_processes.py` utility |

---

## Utility Scripts (No Model Needed)

| Script | Purpose |
|---|---|
| `install_git_hooks.py` | One-time git hook setup |
| `create_hooks.py` | Hook file generator |
| `debug_hook.py` | Diagnostic tool (dev use only) |

---

## L1/L2 Composite Models (Design Documents)

Not expected to align 1:1 with scripts — structural overviews only.

| Model | Level |
|---|---|
| `L0_claude_family.bpmn` | L0 system overview |
| `L1_session_management.bpmn`, `L1_enforcement.bpmn`, `L1_knowledge_management.bpmn` | L1 subsystems |
| `L1_agent_orchestration.bpmn`, `L1_work_tracking.bpmn`, `L1_config_management.bpmn` | L1 subsystems |
| `hook_chain.bpmn` | L2 composite — full prompt-to-response hook chain |
| `session_lifecycle.bpmn` | L2 composite — full session lifecycle |

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/Project-Metis/bpmn-coverage-audit-2026-03-14-detail.md
