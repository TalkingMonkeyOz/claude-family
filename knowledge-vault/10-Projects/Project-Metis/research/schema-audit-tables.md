---
projects:
- claude-family
- Project-Metis
tags:
- schema-audit
- data-model
- metis
synced: false
---

# Schema Audit: Table Inventory and Dead Weight

**Parent index**: `docs/metis-data-model-research-full-schema.md`
**Basis**: Static codebase analysis. Row counts from 2026-02-28 snapshot.

---

## 1. Full Table Inventory (60 tables)

### Active System Tables (32 + 2 new)

| table | ~rows | health | key code reference |
|-------|-------|--------|--------------------|
| `activities` | ~0 | New 2026-03-10 | wcc_assembly.py, server_v2.py |
| `activity_feed` | 1,551 | Active | server_v2.py |
| `audit_log` | 254 | Active | server_v2.py WorkflowEngine |
| `bpmn_processes` | 71 | Active | bpmn-engine MCP, sync_bpmn_processes |
| `build_tasks` | 426 | Active | server_v2.py, task_sync_hook.py |
| `column_registry` | 87 | Active | schema_docs.py, Data Gateway |
| `config_deployment_log` | 244 | Active | deploy_components.py |
| `config_templates` | 6 | Active | generate_project_settings.py |
| `conversations` | 12 | Active | server_v2.py extract_conversation |
| `deployment_tracking` | 261 | Active | deploy scripts |
| `document_projects` | 6,515 | Active | embed_vault_documents.py |
| `documents` | 5,940 | Active | embed_vault_documents.py |
| `enforcement_log` | 1,333 | Degraded | process_router.py (legacy, zombie writes) |
| `features` | 129 | Active | server_v2.py, WorkflowEngine |
| `feedback` | 155 | Active | server_v2.py, failure_capture.py |
| `identities` | 22 | Active | server_v2.py |
| `knowledge` | 717 | Active | server_v2.py remember/recall |
| `knowledge_relations` | 67 | Active | server_v2.py remember() auto-link |
| `mcp_usage` | 6,965 | Degraded | mcp_usage_logger.py (all synthetic data) |
| `messages` | 187 | Active | server_v2.py messaging tools |
| `project_workfiles` | ~0 | New 2026-03-09 | server_v2.py stash/unstash |
| `projects` | 37 | Active | server_v2.py, all project tools |
| `protocol_versions` | 8 | Active | server_v2.py update_protocol |
| `rag_usage_log` | 2,287 | Active | rag_query_hook.py |
| `scheduled_jobs` | 17 | Active | scheduler_runner.py |
| `schema_registry` | 101 | Degraded | schema_docs.py (43 stale entries) |
| `session_facts` | 394 | Active | server_v2.py store_session_fact |
| `session_state` | 12 | Active | server_v2.py, session hooks |
| `sessions` | 906 | Active | session_startup_hook_enhanced.py |
| `todos` | 2,711 | Active | todo_sync_hook.py, task_sync_hook.py |
| `vault_embeddings` | 9,655 | Active | embed_vault_documents.py, rag_query_hook.py |
| `vocabulary_mappings` | 29 | Active | rag_query_hook.py |
| `workflow_transitions` | 28 | Active | server_v2.py WorkflowEngine |
| `workspaces` | 24 | Active | generate_project_settings.py |

### Active Infrastructure Tables (18)

| table | ~rows | health | key code reference |
|-------|-------|--------|--------------------|
| `agent_sessions` | 43 | Active | subagent_start_hook.py |
| `audit_schedule` | 16 | Active | run_compliance_audit.py |
| `book_references` | 46 | Active | server_v2.py store_book_reference |
| `books` | 3 | Low-use | server_v2.py store_book |
| `coding_standards` | 20 | Active | standards_validator.py hook |
| `compliance_audits` | 1 | Low-use | check_compliance_due.py |
| `context_rules` | 16 | Active | context_injector_hook.py |
| `job_run_history` | 36 | Active | scheduler_runner.py |
| `knowledge_retrieval_log` | 77 | Active | server_v2.py recall functions |
| `knowledge_routes` | 10 | Active | server_v2.py |
| `process_data_map` | 0 | Empty | bpmn-engine validate_process_schema |
| `project_type_configs` | 15 | Active | generate_project_settings.py |
| `rag_doc_quality` | 53 | Active | rag_query_hook.py |
| `rag_feedback` | 265 | Active | rag_query_hook.py |
| `rag_query_patterns` | 0 | Empty | rag_query_hook.py (never populated) |
| `reviewer_runs` | 23 | Active | reviewer_data_quality.py |
| `skill_content` | 26 | Active | context_injector_hook.py |
| `workflow_state` | 0 | Empty | server_v2.py WorkflowEngine (no write path) |

### Versioning System Tables (8)

| table | ~rows | health | notes |
|-------|-------|--------|-------|
| `profiles` | 16 | Active | CLAUDE.md storage; deploy_claude_md() reads here |
| `profile_versions` | 16 | Active | Version history |
| `instructions` | 9 | Active | Auto-apply instruction files |
| `instructions_versions` | 0 | Empty | Backfill not done |
| `rules` | 3 | Low-use | Only 3 project rules stored |
| `rules_versions` | 0 | Empty | Backfill not done |
| `skills` | 20 | Active | Skill definitions |
| `skills_versions` | 0 | Empty | Backfill not done |

---

## 2. Dead Weight Detection

### Tables with 0 live rows

SQL: `SELECT relname, n_live_tup, seq_scan, idx_scan FROM pg_stat_user_tables WHERE schemaname='claude' AND n_live_tup = 0 ORDER BY relname;`

| relname | recommendation |
|---------|----------------|
| `instructions_versions` | Keep — versioning backfill pending |
| `process_data_map` | Keep — bpmn-engine reads it; populate via sync |
| `rag_query_patterns` | Keep — planned RAG learning system |
| `rules_versions` | Keep — versioning backfill pending |
| `skills_versions` | Keep — versioning backfill pending |
| `workflow_state` | Investigate — no active write path in server_v2.py; may be vestigial |

### Tables with < 10 rows (low-use)

| relname | ~rows | assessment |
|---------|-------|------------|
| `config_templates` | 6 | Small but CRITICAL — drives config generation for all projects |
| `protocol_versions` | 8 | Small but critical — Core Protocol injection every prompt |
| `instructions` | 9 | Small but active — 9 instruction files |
| `books` | 3 | Low adoption; consider merging into `knowledge` table |
| `rules` | 3 | Low-use; only 3 project rules stored |
| `compliance_audits` | 1 | Low-use; 1 completed audit on record |

### Degraded tables (data quality issues)

| relname | ~rows | issue |
|---------|-------|-------|
| `schema_registry` | 101 | 58 live tables but 101 rows — 43 stale entries from dropped tables |
| `mcp_usage` | 6,965 | All rows verified synthetic (NULL session_id per 2025-12-28 monitoring doc) |
| `enforcement_log` | 1,333 | Written by archived process_router — zombie data stream, no consumer |

### Dropped tables (pre-Metis cleanup, 2026-02-28)

43 tables dropped via `scripts/sql/pre_metis_cleanup.sql`. Categories:
- **Superseded (13)**: process_registry/runs/steps/triggers/dependencies/classification_log, mcp_configs, feedback_comments, feedback_screenshots, git_workflow_deployments, global_config, global_config_versions, architecture_decisions
- **Orchestrator retired (4)**: agent_commands, agent_status, agent_definitions, async_tasks
- **Never-built frameworks (26)**: config_test_*, phases, pm_tasks, programs, work_tasks, ideas, components, requirements, reminders, budget_alerts, models, doc_templates, project_docs, reviewer_specs, test_runs, procedure_registry, procedures, app_logs, tool_evaluations, shared_commands, project_command_assignments, project_config_assignments, actions

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-audit-tables.md
