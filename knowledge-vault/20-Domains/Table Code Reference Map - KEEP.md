---
projects:
- claude-family
tags:
- schema
- cleanup
- reference
synced: false
---

# Table-to-Code Reference Map - KEEP Tables (58)

Companion to [[Table Code Reference Map]]. Details all 58 retained tables.

## Active System Tables (32 with data)

| Table | Rows | Key Code References |
|-------|------|---------------------|
| `activity_feed` | 1551 | server_v2.py |
| `audit_log` | 254 | server_v2.py WorkflowEngine |
| `bpmn_processes` | 71 | bpmn-engine MCP, sync_bpmn_processes |
| `build_tasks` | 426 | server_v2.py, task_sync_hook.py |
| `column_registry` | 87 | schema_docs.py, Data Gateway |
| `config_deployment_log` | 244 | deploy_components.py |
| `config_templates` | 6 | generate_project_settings.py |
| `conversations` | 12 | server_v2.py extract_conversation |
| `deployment_tracking` | 261 | deploy scripts |
| `document_projects` | 6515 | embed_vault_documents.py |
| `documents` | 5940 | embed_vault_documents.py |
| `enforcement_log` | 1333 | process_router.py (legacy but active) |
| `features` | 129 | server_v2.py, WorkflowEngine |
| `feedback` | 155 | server_v2.py, failure_capture.py |
| `identities` | 22 | server_v2.py |
| `knowledge` | 717 | server_v2.py remember/recall |
| `knowledge_relations` | 67 | server_v2.py remember() auto-link |
| `mcp_usage` | 6965 | mcp_usage_logger.py hook |
| `messages` | 187 | server_v2.py messaging tools |
| `projects` | 37 | server_v2.py, all project tools |
| `protocol_versions` | 8 | server_v2.py update_protocol |
| `rag_usage_log` | 2287 | rag_query_hook.py |
| `scheduled_jobs` | 17 | scheduler_runner.py |
| `schema_registry` | 101 | schema_docs.py, embed_schema.py |
| `session_facts` | 394 | server_v2.py store_session_fact |
| `session_state` | 12 | server_v2.py, session hooks |
| `sessions` | 906 | session_startup_hook.py |
| `todos` | 2711 | todo_sync_hook.py, task_sync_hook.py |
| `vault_embeddings` | 9655 | embed_vault_documents.py, rag_query_hook.py |
| `vocabulary_mappings` | 29 | rag_query_hook.py |
| `workflow_transitions` | 28 | server_v2.py WorkflowEngine |
| `workspaces` | 24 | generate_project_settings.py |

## Active Infrastructure (18 tables, code refs exist)

| Table | Rows | Referenced By |
|-------|------|---------------|
| `agent_sessions` | 43 | subagent_start_hook.py |
| `audit_schedule` | 16 | run_compliance_audit.py |
| `book_references` | 46 | server_v2.py store_book_reference |
| `books` | 3 | server_v2.py store_book |
| `coding_standards` | 20 | standards_validator.py hook |
| `compliance_audits` | 1 | check_compliance_due.py, run_compliance_audit.py |
| `context_rules` | 16 | context_injector_hook.py |
| `job_run_history` | 36 | scheduler_runner.py |
| `knowledge_retrieval_log` | 77 | server_v2.py recall functions |
| `knowledge_routes` | 10 | server_v2.py |
| `process_data_map` | 0 | bpmn-engine validate_process_schema |
| `project_type_configs` | 15 | generate_project_settings.py |
| `rag_doc_quality` | 53 | rag_query_hook.py |
| `rag_feedback` | 265 | rag_query_hook.py |
| `rag_query_patterns` | 0 | rag_query_hook.py |
| `reviewer_runs` | 23 | reviewer_data_quality.py, reviewer_doc_staleness.py |
| `skill_content` | 26 | context_injector_hook.py, rag_query_hook.py |
| `workflow_state` | 0 | server_v2.py WorkflowEngine |

## Versioning System (8 tables, DB-centralized, activate post-cleanup)

| Table | Rows | Code Reference |
|-------|------|----------------|
| `profiles` | 16 | server_v2.py deploy_claude_md() |
| `profile_versions` | 16 | FK to profiles |
| `instructions` | 9 | server_v2.py deploy_project() |
| `instructions_versions` | 0 | FK to instructions |
| `rules` | 3 | server_v2.py deploy_project() |
| `rules_versions` | 0 | FK to rules |
| `skills` | 20 | server_v2.py, skill_discovery BPMN |
| `skills_versions` | 0 | FK to skills |

**Post-cleanup task**: Populate version tables from filesystem to complete DB-as-source-of-truth.

---

**Version**: 1.0
**Created**: 2026-02-28
**Updated**: 2026-02-28
**Location**: knowledge-vault/20-Domains/Table Code Reference Map - KEEP.md
