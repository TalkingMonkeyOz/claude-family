---
projects:
- claude-family
tags:
- bpmn
- infrastructure
- hooks
synced: false
---

# BPMN Processes: Infrastructure Category

16 files, 16 processes, 205 tests. These map directly to hook scripts and automated pipelines. Highest-fidelity category - code and model must stay in sync.

Back to: [Process Map Overview](bpmn-process-map.md)

## Hook-Backed Processes

| Process ID | Hook Script | Elements | Flows | Description |
|------------|-------------|----------|-------|-------------|
| `hook_chain` | rag_query_hook.py + task_discipline_hook.py | 40 | 25 | Combined UserPromptSubmit + PreToolUse + PostToolUse. Session change check, RAG query, skill suggestions, context injection, discipline gate (pass/continuation/block), execute tool, post-tool sync. Shared state: task_map file. 3 end events. |
| `session_end` | session_end_hook.py | 32 | 23 | Auto-saves state on Claude Code exit. Demotes in_progress todos to pending. Marks session closed. |
| `precompact` | precompact_hook.py | ~30 | ~20 | Injects systemMessage with active todos, session_state, active features before context compaction. Preserves narrative context and user intent across compaction boundary. |
| `todo_sync` | todo_sync_hook.py | ~25 | ~18 | Fuzzy matching (SequenceMatcher >= 75%) syncs TodoWrite output to claude.todos. INSERT new, UPDATE existing. |
| `task_sync` | task_sync_hook.py | ~28 | ~20 | Bridges TaskCreate/TaskUpdate to claude.todos + claude.build_tasks. Dedup via substring (min 20 chars) + fuzzy match (75% threshold). Updates task_map file. |
| `content_validation` | context_injector_hook.py + standards_validator.py | ~30 | ~22 | Two PreToolUse hooks: context_injector (adds standards from claude.context_rules, always allows), standards_validator (validates content against claude.coding_standards, can block). |
| `mcp_usage_logging` | mcp_usage_logger.py | ~20 | 15 | Catch-all PostToolUse. Filters to mcp__ prefix only. Logs tool name, server, execution time, success, input/output sizes to claude.mcp_usage. |
| `subagent_start` | subagent_start_hook.py | ~18 | ~14 | Logs agent spawns to claude.agent_sessions. Validates subagent_id. Upserts on conflict. |

## Pipeline Processes

| Process ID | Script(s) | Elements | Flows | Description |
|------------|-----------|----------|-------|-------------|
| `failure_capture` | scripts/failure_capture.py (called by all hooks) | 36 | 21 | Self-improvement loop: hook fails -> log to JSONL (always) -> (DB up?) file as feedback with dedup -> surface on next prompt via rag_query_hook -> Claude sees -> fix now or defer. 3 exit points. |
| `system_maintenance` | schema_docs.py, embed_schema.py, embed_vault_documents.py, server_v2.py | 48 | 43 | 4-phase: Detect (5 parallel checks: schema, vault, BPMN, memory, column registry) -> Decide (fast-path skip if clean) -> Repair (5 conditional parallel repairs) -> Summary. Parallel gateways for fan-out/join. |
| `schema_governance` | scripts/schema_docs.py + embed_schema.py | 38 | 26 | 3-layer pipeline. Layer 1: introspect pg_catalog, COMMENT ON, sync registries. Layer 2: Voyage AI embeddings (voyage-3, 1024d) for changed tables. Layer 3: BPMN data ref validation, process_data_map update. 4 pipeline modes (full/embed-only/validate-only/incremental). |
| `bpmn_sync` | server_v2.py sync_bpmn_processes | ~25 | ~18 | Walks processes/**/*.bpmn, parses process metadata, UPSERTs into claude.bpmn_processes with Voyage AI embeddings. Hybrid: files=git source of truth, DB=runtime registry. |
| `credential_loading` | Used by all MCP servers + hooks | ~22 | ~16 | Priority-ordered .env search: scripts/.env -> project root .env -> ~/.env -> legacy. Used by every PostgreSQL connection. |
| `mcp_config_deployment` | generate_project_settings.py | ~30 | ~22 | Two-tier: Global (~/.claude/mcp.json, manual) + Project (.mcp.json, DB-driven from workspaces.startup_config.mcp_configs). |
| `client_domain_schema` | DB schema migration | ~25 | ~18 | Adds client_domain to claude.projects for multi-tenancy. BPMN search inherits client context through project_name join. Domains: infrastructure, nimbus, ato, claude-tools, finance, personal. |
| `context_budget_management` | Advisory (CORE_PROTOCOL + task discipline) | ~35 | ~28 | Classify tasks by context weight, estimate total cost vs remaining budget, delegation decision, checkpoint planning. Prevents context exhaustion crashes (385 tool calls, ~1.2M tokens was the trigger event). |
| `database_cleanup` | Manual procedure | ~30 | ~22 | Safety-first table drop: verify empty -> check internal FK deps -> check external FK deps -> drop in order -> verify success. |

## Test Files

test_hook_chain.py (8), test_discipline_hook.py (18), test_hook_lifecycle.py (10), test_session_end.py (6), test_precompact.py (32), test_todo_sync.py (9), test_todo_task_sync.py (11), test_content_validation.py (6), test_mcp_usage_logging.py (5), test_subagent_start.py (5), test_failure_capture.py (6), test_system_maintenance.py (21), test_bpmn_sync.py (9), test_credential_loading.py (19), test_mcp_config_deployment.py (14), test_client_domain_schema.py (20), test_context_budget.py (24), test_database_cleanup.py (18)

---
**Version**: 1.0
**Created**: 2026-02-28
**Updated**: 2026-02-28
**Location**: knowledge-vault/10-Projects/Project-Metis/bpmn-process-map-infrastructure.md
