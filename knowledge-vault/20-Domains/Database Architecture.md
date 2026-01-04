---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T23:29:45.914906'
tags:
- database
- architecture
- reference
---

# Database Architecture

**Database**: `ai_company_foundation`
**Schema**: `claude` (76 tables)

This is the authoritative reference for the Claude Family database schema.

**Related**: [[System Functional Specification]] | [[Database FK Constraints]]

---

## Quick Reference

| Domain | Tables | Primary Use |
|--------|--------|-------------|
| [[#Sessions]] | 3 | Session tracking, state persistence |
| [[#Projects]] | 5 | Project registry, hierarchy |
| [[#Process Workflow]] | 8 | Workflow engine, process automation |
| [[#Work Items]] | 8 | Tasks, feedback, features |
| [[#Knowledge]] | 5 | Knowledge sync, documents |
| [[#RAG Self-Learning]] | 3 | Feedback capture, doc quality, patterns |
| [[#Governance]] | 8 | Data quality, audits, compliance |
| [[#MCP Orchestration]] | 5 | MCP servers, messaging |
| [[#Scheduling]] | 3 | Cron jobs, reminders |
| [[#Other]] | 7 | Identities, activity, misc |

---

## Connection

Via MCP postgres server. See [[MCP configuration]].

```sql
-- Test connection
SELECT current_database(), current_schema();
```

---

## Data Gateway Pattern

Before writing to constrained columns, always check valid values:

```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

Key constrained columns:
- `status` fields - vary by table (check registry)
- `priority` - always 1-5 (1=critical, 5=low)
- `feedback.feedback_type` - bug, design, question, change, idea

See [[Claude Hooks]] for enforcement.

---

## Sessions

Track Claude Code sessions and their state.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `sessions` | Session logging | session_id, project_name, session_start, session_end, session_summary |
| `session_state` | Persisted state | session_id, state_key, state_value |
| `agent_sessions` | Spawned agent tracking | agent_type, parent_session, status |

```sql
-- Recent sessions for a project
SELECT session_start, session_summary
FROM claude.sessions
WHERE project_name = 'claude-family'
ORDER BY session_start DESC LIMIT 5;
```

**Detailed Documentation**: See [[Database Schema - Core Tables]] for column-level details, constraints, and data quality analysis.

---

## Projects

Project registry and organizational hierarchy.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `projects` | Project registry | project_id, project_name, phase, status |
| `project_docs` | Document metadata | project_id, doc_path, doc_type |
| `programs` | Program groupings | program_id, program_name |
| `phases` | Project phases | phase_id, phase_name, sequence |
| `requirements` | Project requirements | requirement_id, project_id, status |

```sql
-- Get project with phase
SELECT project_name, phase, status
FROM claude.projects
WHERE project_name = 'claude-family';
```

---

## Process Workflow

Workflow engine for automation and enforcement.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `process_registry` | Workflow definitions | process_id, process_name, category, enforcement |
| `process_steps` | Steps within process | process_id, step_number, instruction |
| `process_triggers` | Keyword triggers | trigger_id, process_id, trigger_pattern |
| `process_runs` | Execution history | run_id, process_id, status, started_at |
| `process_dependencies` | Process interconnections | from_process, to_process, dependency_type |
| `process_classification_log` | Router decisions | request_text, matched_process |
| `workflow_state` | Active workflow state | workflow_id, current_step, context |
| `procedures` | Legacy procedures | procedure_id, name, content |

```sql
-- Active processes by category
SELECT category, COUNT(*)
FROM claude.process_registry
WHERE is_active = true
GROUP BY category;
```

---

## Work Items

Task tracking, feedback, and feature management.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `build_tasks` | Development tasks | task_id, feature_id, status |
| `work_tasks` | General work items | task_id, description, status |
| `pm_tasks` | Project management tasks | task_id, project_id, assigned_to |
| `features` | Feature registry | feature_id, project_id, status |
| `feedback` | Issue/feedback tracking | feedback_id, feedback_type, status, priority |
| `feedback_comments` | Comments on feedback | comment_id, feedback_id, content |
| `feedback_screenshots` | Screenshot attachments | screenshot_id, feedback_id, path |
| `ideas` | Idea capture | idea_id, title, status |

```sql
-- Open feedback for project
SELECT feedback_id::text, feedback_type, description, status
FROM claude.feedback
WHERE project_id = 'PROJECT-UUID'::uuid
  AND status IN ('new', 'in_progress');
```

---

## Knowledge

Knowledge persistence and document management.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `knowledge` | Synced from Obsidian vault | knowledge_id, title, knowledge_type, applies_to_projects |
| `knowledge_retrieval_log` | Query tracking | query_text, matched_knowledge, retrieved_at |
| `documents` | Document registry | document_id, title, content |
| `doc_templates` | Document templates | template_id, template_type, content |
| `document_projects` | Doc-project links | document_id, project_id |

```sql
-- Knowledge by project
SELECT title, knowledge_type
FROM claude.knowledge
WHERE 'claude-family' = ANY(applies_to_projects);
```

---

## RAG Self-Learning

Continuous improvement loop for RAG system.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `rag_feedback` | Feedback signals (explicit + implicit) | log_id, helpful, signal_type, signal_confidence, doc_path |
| `rag_doc_quality` | Doc quality tracking (miss counter) | doc_path, miss_count, hit_count, flagged_for_review, quality_score |
| `rag_query_patterns` | Learned query-doc associations | query_pattern, success_rate, suggested_docs |

```sql
-- Flagged docs needing review
SELECT doc_path, miss_count, quality_score
FROM claude.rag_doc_quality
WHERE flagged_for_review = true;

-- Recent feedback signals
SELECT signal_type, signal_confidence, doc_path, created_at
FROM claude.rag_feedback
ORDER BY created_at DESC LIMIT 10;
```

**Related**: [[System Functional Specification#Self-Learning RAG]] | [[RAG Usage Guide]]

---

## Governance

Data quality, audits, and compliance tracking.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `column_registry` | Valid values for columns | table_name, column_name, valid_values |
| `schema_registry` | Schema documentation | schema_name, description |
| `enforcement_log` | Reminder/enforcement tracking | enforcement_type, triggered_at |
| `compliance_audits` | Audit results | audit_id, project_id, audit_type, score |
| `audit_schedule` | Audit scheduling | project_id, audit_type, next_due |
| `reviewer_runs` | Auto-reviewer executions | run_id, reviewer_type, findings |
| `reviewer_specs` | Reviewer configurations | spec_id, reviewer_type, criteria |
| `test_runs` | Test execution results | run_id, test_suite, passed, failed |

```sql
-- Check valid values for a column
SELECT valid_values
FROM claude.column_registry
WHERE table_name = 'feedback' AND column_name = 'status';
```

---

## MCP Orchestration

MCP server management and inter-instance messaging.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `mcp_configs` | MCP server configurations | server_name, config_json |
| `mcp_usage` | MCP tool call tracking | tool_name, call_count, avg_duration |
| `messages` | Inter-Claude messaging | message_id, from_session, to_project, body |
| `async_tasks` | Async agent tracking | task_id, agent_type, status |
| `actions` | Shared actions for MCW | action_id, action_name, handler |

```sql
-- Check inbox
SELECT * FROM claude.messages
WHERE to_project = 'claude-family'
  AND status = 'pending';
```

---

## Scheduling

Automated job execution and reminders.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `scheduled_jobs` | Cron-like job definitions | job_id, schedule, command |
| `job_run_history` | Job execution history | run_id, job_id, status, started_at |
| `reminders` | Session reminders | reminder_id, trigger_condition, message |

```sql
-- Active scheduled jobs
SELECT job_id, schedule, command
FROM claude.scheduled_jobs
WHERE is_active = true;
```

---

## Other

Miscellaneous supporting tables.

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `identities` | Claude identity registry | identity_id, identity_name |
| `workspaces` | Workspace configurations | workspace_id, path |
| `components` | UI/system components | component_id, component_type |
| `architecture_decisions` | ADR tracking | decision_id, title, status |
| `activity_feed` | Activity stream | activity_id, activity_type, timestamp |
| `capability_usage` | Feature usage tracking | capability, usage_count |
| `feature_usage` | Feature toggle tracking | feature_name, is_enabled |

---

## Deprecated Tables (To Be Removed)

These tables exist in legacy schemas and will be dropped:

| Schema | Table | Status |
|--------|-------|--------|
| `claude_family` | `budget_alerts` | Deprecated |
| `claude_family` | `procedure_registry` | Migrated to claude.process_registry |
| `claude_family` | `tool_evaluations` | Deprecated |
| `claude_pm` | `project_feedback_comments` | Migrated to claude.feedback_comments |

---

## Known Issues (VERIFIED 2026-01-04)

| Issue | Count | Impact | Fix |
|-------|-------|--------|-----|
| ~~Duplicate FK on `mcp_usage.session_id`~~ | ✅ FIXED | Dropped `mcp_usage_session_id_fkey` | 2026-01-04 |
| Orphaned `agent_sessions` | 176 | NULL parent_session_id | Backfill or set FK nullable |
| Session continuation bypass | - | FK violations (session not in DB) | See [[System Functional Specification#Session ID Lifecycle]] |

**Full FK reference**: [[Database FK Constraints]] (39 constraints after cleanup)

---

## Related Documents

- [[System Functional Specification]] - End-to-end system flow
- [[Database FK Constraints]] - All 40 FK constraints
- [[Database Schema - Core Tables]] - Detailed core tables documentation
- [[Session Architecture]] - Session lifecycle
- [[Claude Hooks]] - Enforcement layer
- [[Data Gateway]] - Constraint patterns

---

**Version**: 1.3
**Created**: 2025-12-20
**Updated**: 2026-01-04 (RAG Self-Learning tables added)
**Location**: knowledge-vault/20-Domains/Database Architecture.md