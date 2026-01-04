---
projects:
- claude-family
tags:
- database
- constraints
- reference
synced: false
---

# Database FK Constraints

All foreign key constraints in the `claude` schema. **42 total** (39 original + 3 RAG tables).

---

## Session-Related FKs (Critical Path)

These FKs reference `sessions.session_id` and cause violations when session doesn't exist:

| Table | Column | Constraint | Status |
|-------|--------|------------|--------|
| `agent_sessions` | `parent_session_id` | `fk_agent_sessions_parent` | ⚠️ 176 NULLs |
| `async_tasks` | `parent_session_id` | `fk_async_tasks_parent` | ✅ |
| `build_tasks` | `created_session_id` | `fk_build_tasks_session` | ✅ |
| `features` | `created_session_id` | `fk_features_session` | ✅ |
| `feedback` | `created_session_id` | `fk_feedback_session` | ✅ |
| `mcp_usage` | `session_id` | `fk_mcp_usage_session` | ✅ Fixed |
| `rag_usage_log` | `session_id` | `fk_session` | ✅ |
| `todos` | `created_session_id` | `todos_created_session_id_fkey` | ✅ |
| `todos` | `completed_session_id` | `todos_completed_session_id_fkey` | ✅ |

**Issue**: `mcp_usage` has TWO identical FKs on `session_id` - drop one.

---

## Project-Related FKs

| Table | Column | Constraint |
|-------|--------|------------|
| `architecture_decisions` | `project_id` | `architecture_decisions_project_id_fkey` |
| `build_tasks` | `project_id` | `fk_build_tasks_project` |
| `config_deployment_log` | `project_id` | `config_deployment_log_project_id_fkey` |
| `document_projects` | `project_id` | `document_projects_project_id_fkey` |
| `feature_usage` | `project_id` | `feature_usage_project_id_fkey` |
| `features` | `project_id` | `fk_features_project` |
| `feedback` | `project_id` | `fk_feedback_project` |
| `project_command_assignments` | `project_id` | `project_command_assignments_project_id_fkey` |
| `project_config_assignments` | `project_id` | `project_config_assignments_project_id_fkey` |
| `requirements` | `project_id` | `fk_requirements_project` |
| `todos` | `project_id` | `todos_project_id_fkey` |

---

## Identity-Related FKs

| Table | Column | Constraint |
|-------|--------|------------|
| `sessions` | `identity_id` | `fk_sessions_identity` |
| `projects` | `default_identity_id` | `fk_projects_default_identity` |
| `mcp_usage` | `identity_id` | `mcp_usage_identity_id_fkey` |

---

## RAG Self-Learning FKs

| Table | Column | Constraint |
|-------|--------|------------|
| `rag_feedback` | `log_id` | `rag_feedback_log_id_fkey` → rag_usage_log |
| `rag_feedback` | `session_id` | `rag_feedback_session_id_fkey` → sessions |

---

## Other FKs

| Table | Column | References |
|-------|--------|------------|
| `build_tasks` | `feature_id` | `features.feature_id` |
| `document_projects` | `doc_id` | `documents.doc_id` |
| `feature_usage` | `feature_id` | `features.feature_id` |
| `requirements` | `feature_id` | `features.feature_id` |
| `config_templates` | `extends_template_id` | `config_templates.template_id` |
| `config_deployment_log` | `template_id` | `config_templates.template_id` |
| `project_type_configs` | `default_hook_template_id` | `config_templates.template_id` |
| `project_config_assignments` | `template_id` | `config_templates.template_id` |
| `project_command_assignments` | `command_id` | `shared_commands.command_id` |
| `todos` | `source_message_id` | `messages.message_id` |
| Process tables (5) | Various | `process_registry.process_id` |

---

## Related

- [[Database Architecture]] - Schema overview
- [[System Functional Specification]] - Data flow
- [[Session Architecture]] - Session lifecycle

---

**Version**: 1.1
**Created**: 2026-01-04
**Updated**: 2026-01-04 (RAG Self-Learning FKs added)
**Location**: knowledge-vault/20-Domains/Database FK Constraints.md
