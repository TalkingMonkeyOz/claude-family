---
projects:
- claude-family
- Project-Metis
tags:
- audit
- database
- schema
synced: false
---

# Audit: Database Schema (Persistence Layer)

**Parent**: [[claude-family-systems-audit]]
**Raw data**: `docs/audit/database_audit.md` (22K chars)

---

## What It Is

PostgreSQL schema `claude` in `ai_company_foundation` with 58 tables storing all persistent state. Uses pgvector extension for embeddings. WorkflowEngine enforces state transitions via `workflow_transitions` table.

## Table Inventory (58 tables, 4 tiers)

### Tier 1 — Core System (32 tables, all with live data)

| Table | ~Rows | Health | Purpose |
|-------|-------|--------|---------|
| `sessions` | 906 | Active | Every Claude invocation |
| `todos` | 2,711 | Active | Highest-volume work table |
| `build_tasks` | 426 | Active | Feature implementation steps |
| `features` | 129 | Active | Feature tracking |
| `feedback` | 155 | Active | Bugs, ideas, improvements |
| `knowledge` | 717 | Active | 3-tier cognitive memory |
| `vault_embeddings` | 9,655 | Active | Voyage AI 1024-dim vectors |
| `documents` | 5,940 | Active | Embedded vault documents |
| `document_projects` | 6,515 | Active | Vault-to-project links |
| `messages` | 187 | Active | Inter-Claude messaging |
| `audit_log` | 254 | Active | WorkflowEngine transitions |
| `mcp_usage` | 6,965 | Degraded | May be largely synthetic data |
| `rag_usage_log` | 2,287 | Active | RAG hook telemetry |
| `session_facts` | 394 | Active | Crash-resistant key/value |
| `workflow_transitions` | 28 | Active | State machine rules |
| `column_registry` | 87 | Active | Data Gateway validator |
| `config_templates` | 6 | Active | Config generation |
| `protocol_versions` | 8 | Active | Core Protocol history |
| `projects` | 37 | Active | Project registry |
| `workspaces` | 24 | Active | Project workspace configs |
| Other 12 tables | Various | Active | activity_feed, bpmn_processes, config_deployment_log, deployment_tracking, enforcement_log, identities, knowledge_relations, rag_feedback, scheduled_jobs, schema_registry, session_state, vocabulary_mappings |

### Tier 2 — Infrastructure (18 tables)

Includes: agent_sessions (43 rows), audit_schedule, book_references (46), books (3), coding_standards (20), compliance_audits (1), context_rules (16), job_run_history, knowledge_retrieval_log, knowledge_routes, process_data_map (0), project_type_configs (15), rag_doc_quality, rag_query_patterns (0), reviewer_runs, skill_content (26), workflow_state (0).

### Tier 3 — Versioning (8 tables)

profiles (16), profile_versions (16), instructions (9), skills (20), rules (3) + 3 empty `_versions` tables.

## State Machines (28 transitions)

### Feedback: new → triaged → in_progress → resolved
Also: triaged → wont_fix, triaged → duplicate, in_progress → wont_fix.
**Note**: No direct new → in_progress. Forces triage.

### Features: draft → planned → in_progress → completed
`completed` requires `all_tasks_done` condition. Also: in_progress → blocked, in_progress/planned → cancelled.

### Build Tasks: todo → in_progress → completed
Side effects: `set_started_at` on start, `check_feature_completion` on complete. Also: in_progress → blocked, blocked → todo, todo/in_progress → cancelled.

## Data Quality Issues

1. **schema_registry drift** — 101 entries vs 58 live tables. 43 stale entries from pre-cleanup.
2. **52 orphaned sessions** — `session_end IS NULL` permanently from fallback failures.
3. **enforcement_log zombie** — 1,333 rows still written by archived process_router.
4. **mcp_usage data quality** — 6,965 rows may be synthetic test data.
5. **Empty tables** — workflow_state, process_data_map, rag_query_patterns never populated.
6. **4 empty version tables** — instructions/rules/skills_versions never backfilled.
7. **column_registry says `idea` is valid for feedback_type** but some docs omit it.

## Column Registry (Data Gateway)

87 entries covering constrained columns. Key constraints:
- `feedback.status`: new, triaged, in_progress, resolved, wont_fix, duplicate
- `feedback.feedback_type`: bug, design, question, change, idea, improvement
- `features.status`: draft, planned, in_progress, blocked, completed, cancelled
- `build_tasks.status`: **todo** (NOT pending), in_progress, blocked, completed, cancelled
- `messages.status`: pending, read, acknowledged, actioned, deferred

## For Metis

PostgreSQL is the right choice. Enterprise needs:
- **Connection pooling** (PgBouncer) for multi-instance
- **Row-level security** for multi-tenancy
- **Migration tooling** (Alembic/Flyway) — currently ad hoc SQL scripts
- **Table partitioning** for high-volume tables (todos, mcp_usage, vault_embeddings)
- **Preserve**: WorkflowEngine + column_registry pattern — genuine innovation for AI data governance

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-audit-database.md
