Now I have comprehensive data from the codebase. Let me compile the full structured report:

---

# Claude Family Database Schema Research Report

**Database**: PostgreSQL `ai_company_foundation`, schema `claude`
**Research Date**: 2026-03-09
**Basis**: Static code analysis of scripts, MCP server source, SQL migrations, vault documentation, and the pre-Metis cleanup reference maps.

Note: This report is derived from codebase analysis. Row counts reflect figures recorded at 2026-02-28 (the most recent documented snapshot). Live counts will differ.

---

## 1. Table Inventory with Row Counts

The schema contains **58 tables** after the pre-Metis cleanup dropped 43. Tables fall into four tiers.

### Tier 1 — Active System Tables (32 tables with live data)

| Table | Documented Rows | Health | Notes |
|-------|-----------------|--------|-------|
| `activity_feed` | 1,551 | Active | High-volume event log |
| `audit_log` | 254 | Active | WorkflowEngine transitions |
| `bpmn_processes` | 71 | Active | bpmn-engine MCP registry |
| `build_tasks` | 426 | Active | Core work-tracking |
| `column_registry` | 87 | Active | Data Gateway validator |
| `config_deployment_log` | 244 | Active | Config deploy history |
| `config_templates` | 6 | Active | 6 templates including hooks-base (id=1) |
| `conversations` | 12 | Active | Extracted session JSONL |
| `deployment_tracking` | 261 | Active | Deploy scripts |
| `document_projects` | 6,515 | Active | Vault-to-project embedding links |
| `documents` | 5,940 | Active | Embedded vault documents |
| `enforcement_log` | 1,333 | Degraded | Written by legacy process_router; code still active but process_router archived |
| `features` | 129 | Active | Core work-tracking |
| `feedback` | 155 | Active | Core work-tracking |
| `identities` | 22 | Active | Agent/human identity registry |
| `knowledge` | 717 | Active | 3-tier cognitive memory (F130) |
| `knowledge_relations` | 67 | Active | Auto-linked by `remember()` |
| `mcp_usage` | 6,965 | Degraded | All rows likely from manual tests (no session_id per monitoring doc) |
| `messages` | 187 | Active | Inter-Claude messaging |
| `projects` | 37 | Active | Project registry |
| `protocol_versions` | 8 | Active | Core Protocol v8 (injected every prompt) |
| `rag_usage_log` | 2,287 | Active | High-volume RAG hook logs |
| `scheduled_jobs` | 17 | Active | Scheduler |
| `schema_registry` | 101 | Active | Includes dropped tables; should equal 58 post-cleanup |
| `session_facts` | 394 | Active | Crash-resistant key/value store |
| `session_state` | 12 | Active | Per-project focus/next-steps |
| `sessions` | 906 | Active | Session tracking |
| `todos` | 2,711 | Active | Highest-volume work table |
| `vault_embeddings` | 9,655 | Active | Voyage AI 1024-dim vectors |
| `vocabulary_mappings` | 29 | Active | RAG query normalization |
| `workflow_transitions` | 28 | Active | State machine rules |
| `workspaces` | 24 | Active | Project workspace configs |

### Tier 2 — Active Infrastructure (18 tables)

| Table | Documented Rows | Health | Notes |
|-------|-----------------|--------|-------|
| `agent_sessions` | 43 | Active | Subagent spawn tracking |
| `audit_schedule` | 16 | Active | Compliance check schedules |
| `book_references` | 46 | Active | Semantic book references |
| `books` | 3 | Low-use | Only 3 entries; feature under-utilized |
| `coding_standards` | 20 | Active | standards_validator.py hook |
| `compliance_audits` | 1 | Low-use | Only 1 completed audit on record |
| `context_rules` | 16 | Active | context_injector_hook.py |
| `job_run_history` | 36 | Active | Scheduler run records |
| `knowledge_retrieval_log` | 77 | Active | recall function telemetry |
| `knowledge_routes` | 10 | Active | 10 seed routes; route usage not verified |
| `process_data_map` | 0 | Empty | bpmn-engine schema validation; never populated |
| `project_type_configs` | 15 | Active | Config generation defaults |
| `rag_doc_quality` | 53 | Active | RAG quality scores |
| `rag_feedback` | 265 | Active | RAG relevance signals |
| `rag_query_patterns` | 0 | Empty | Query pattern learning; never populated |
| `reviewer_runs` | 23 | Active | Auto-reviewer logs |
| `skill_content` | 26 | Active | Skill discovery for hook |
| `workflow_state` | 0 | Empty | WorkflowEngine state; never populated |

### Tier 3 — Versioning System (8 tables)

These support DB-as-source-of-truth for config files. Partially activated.

| Table | Documented Rows | Health | Notes |
|-------|-----------------|--------|-------|
| `profiles` | 16 | Active | CLAUDE.md storage; `deploy_claude_md()` reads here |
| `profile_versions` | 16 | Active | Version history |
| `instructions` | 9 | Active | Auto-apply instruction files |
| `instructions_versions` | 0 | Empty | Version history not yet populated |
| `rules` | 3 | Low-use | Project rules; only 3 stored |
| `rules_versions` | 0 | Empty | Version history not yet populated |
| `skills` | 20 | Active | Skill definitions |
| `skills_versions` | 0 | Empty | Version history not yet populated |

---

## 2. Data Quality Analysis

### Sessions

- **Total documented**: 906
- **Activity**: High-frequency; every Claude Code invocation logs a session via `session_startup_hook_enhanced.py`. 60-second dedup guard prevents duplicate logging.
- **Issue — unclosed sessions**: The `session_end_hook.py` auto-closes sessions under 24 hours old. Sessions from crashes or hard-exits longer than 24 hours ago will have `session_end IS NULL` permanently. The `start_session()` MCP tool demotes orphaned in-progress todos on startup, but does not retroactively close orphaned session records.
- **Issue — project_name vs project_id**: Sessions are identified by `project_name` (VARCHAR), not `project_id` (UUID). This creates a fragile join pattern against `projects`.

### Feedback

- **Total**: 155. Open items likely a fraction of that (status IN `new`, `triaged`, `in_progress`).
- **Valid statuses**: `new`, `triaged`, `in_progress`, `resolved`, `wont_fix`, `duplicate`.
- **Issue — schema mismatch**: The Work Tracking Schema vault document lists `resolved` as the final state; CLAUDE.md documents `resolved` as the terminal state. However the `column_registry` and CHECK constraint on `feedback.status` define `wont_fix` and `duplicate` as terminal branches. These are consistent — the documentation is just abbreviated.
- **Issue — feedback_type**: `column_registry` validation for `feedback.feedback_type` defines `bug, design, question, change, idea`. CLAUDE.md documents only `bug, design, question, change` — `idea` is mentioned separately as going to `feedback` with `type='idea'`. The constraint and registry match; the documentation summary in CLAUDE.md is slightly incomplete.

### Features

- **Total**: 129. Active (non-completed, non-cancelled) is the working set.
- **Valid statuses**: `draft`, `planned`, `in_progress`, `blocked`, `completed`, `cancelled`.
- **Issue — completion gate**: The `all_tasks_done` condition (checked in WorkflowEngine) requires all build_tasks to be `completed` or `cancelled` before a feature can move to `completed`. This is correct design but means features with blocked or orphaned tasks can never complete without manual intervention.
- **Issue — draft features**: Features created by `create_feature` start at `draft`. Features stuck in `draft` (no tasks, no plan_data) represent planning debt. The count is unknown without a live query.

### Build Tasks

- **Total**: 426.
- **Valid statuses**: `todo` (NOT `pending` — this is a critical gotcha documented in MEMORY.md), `in_progress`, `blocked`, `completed`, `cancelled`.
- **Issue — orphaned tasks**: `build_tasks` must have a `feature_id` via FK. Tasks without a live feature would violate the FK, so true orphans can only exist if a feature was hard-deleted (not via WorkflowEngine). The `get_work_context` query correctly guards with `blocked_by_task_id IS NULL` to surface only unblocked tasks.
- **Issue — status mismatch with Work Tracking Schema doc**: The vault document (`Work Tracking Schema.md`) lists `pending` as a valid status for `build_tasks`. The actual DB constraint and MEMORY.md gotcha both specify `todo`. This document is stale.

### Knowledge

- **Total**: 717 entries across all tiers (`short`, `mid`, `long`, `archived`).
- **Tier distribution**: Unknown without live query. Per F130 design, `mid` is the default landing tier for `remember()`.
- **Embedding coverage**: `knowledge` has an `embedding` column. Coverage depends on Voyage AI API availability at time of storage.
- **Issue — legacy entries**: Entries created before F130 (pre-2026-02-26) were stored via `store_knowledge` (legacy tool). These will not have `tier` populated (defaults to NULL or pre-F130 schema default). The `consolidate_memories` lifecycle will not promote entries without a recognized tier.

### Messages

- **Total**: 187 inter-Claude messages.
- **Valid statuses**: `pending`, `read`, `acknowledged`, `actioned`, `deferred`.
- **Valid types**: `task_request`, `status_update`, `question`, `notification`, `handoff`, `broadcast`.
- **Issue — column name gotcha**: `messages` uses `message_id` (not `id`) and `from_project` (not `sender_id`). This is documented in MEMORY.md and is a frequent error source.
- **Health**: `pending` messages that are not addressed accumulate. MEMORY.md flags >10 pending as a red-flag threshold.

### Audit Log

- **Total**: 254 entries.
- **Coverage**: Only captures transitions through `WorkflowEngine.execute_transition()`. Manual `UPDATE` statements bypass the log. The `end_session` tool also writes a `conversation` entry to `audit_log`. Coverage is therefore partial — not all data mutations are logged.
- **Assessment**: The 254 count is low relative to 906 sessions and 426 build tasks, suggesting most historical transitions predated the WorkflowEngine (added 2026-02-10) or were done via direct SQL.

### MCP Usage

- **Total**: 6,965 rows, but the monitoring document notes that all entries with `session_id IS NOT NULL` returned 0 as of the document date (2025-12-28). The 6,965 rows are from manual test entries. The hook fires (`mcp_usage_logger.py`) but whether PostToolUse hooks now work in Claude Code is unverified at the time of analysis.

---

## 3. Schema Health

### Known Empty Tables (Potential Dead Weight)

| Table | Rows | Risk |
|-------|------|------|
| `workflow_state` | 0 | Low — WorkflowEngine uses `workflow_transitions` for rules; `workflow_state` may be intended for persistent per-entity state. No active code writes to it. |
| `process_data_map` | 0 | Low — bpmn-engine's `validate_process_schema` tool reads it. Without data, schema validation against BPMN processes is a no-op. |
| `rag_query_patterns` | 0 | Low — Intended for query pattern learning. RAG hook was not writing patterns as of the last documented check. |
| `instructions_versions` | 0 | Low — Version history not backfilled. Safe to leave. |
| `rules_versions` | 0 | Low — Same as above. |
| `skills_versions` | 0 | Low — Same as above. |

### Schema Registry Drift

`schema_registry` has **101 rows** but the live schema has **58 tables**. The 43 dropped tables still have registry entries from before the pre-Metis cleanup (the cleanup SQL does not include deleting from `schema_registry`). Running `python scripts/schema_docs.py --sync-registry` will add missing tables but will not remove rows for dropped tables.

**Action needed**: Run `DELETE FROM claude.schema_registry WHERE table_name NOT IN (SELECT relname FROM pg_class JOIN pg_namespace ON relnamespace = oid WHERE nspname = 'claude' AND relkind = 'r');` to purge stale entries, then re-sync.

### `enforcement_log` — Degraded State

`enforcement_log` has 1,333 rows and is still being written by `process_router.py`. However, `process_router` was archived as part of ADR-005 (Skills-First). If the hook still calls it, it is a live zombie dependency. The code reference in the KEEP table map flags it as "(legacy but active)" which means it was deliberately retained in Wave 3, not dropped. This should be audited to determine if it still adds value.

### `mcp_usage` — Data Quality Issue

6,965 rows, but verified to contain only manual test data with NULL `session_id`. The table exists, is indexed, and hook code is correct — but actual MCP telemetry has never been collected automatically. Either the PostToolUse hook situation has been resolved since the 2025-12-28 document, or the table remains full of synthetic data.

---

## 4. Workflow Transitions (State Machines)

The `workflow_transitions` table has **28 rows** governing three entity types. The WorkflowEngine in `server_v2.py` reads these at transition time.

### Feedback State Machine

Documented flow based on `CLAUDE.md` and code:

```
new ──> triaged ──> in_progress ──> resolved
  └──────────────────────────────> wont_fix
  └──────────────────────────────> duplicate
```

| From | To | Condition | Side Effect |
|------|----|-----------|-------------|
| `new` | `triaged` | None | None |
| `triaged` | `in_progress` | None | None |
| `triaged` | `wont_fix` | None | None |
| `triaged` | `duplicate` | None | None |
| `in_progress` | `resolved` | None | None |
| `in_progress` | `wont_fix` | None | None |

Note: Direct `new → in_progress` is not documented as a valid transition, forcing triage.

### Features State Machine

```
draft ──> planned ──> in_progress ──> completed (requires: all_tasks_done)
                  └──> blocked
                  └──> cancelled
```

| From | To | Condition | Side Effect |
|------|----|-----------|-------------|
| `draft` | `planned` | None | None |
| `planned` | `in_progress` | None | None |
| `in_progress` | `completed` | `all_tasks_done` | None |
| `in_progress` | `blocked` | None | None |
| `in_progress` | `cancelled` | None | None |
| `planned` | `cancelled` | None | None |

The `all_tasks_done` condition checks that all `build_tasks` for the feature have status `completed` or `cancelled` before allowing the feature to reach `completed`.

### Build Tasks State Machine

```
todo ──> in_progress ──> completed
     └──> blocked    └──> cancelled
```

| From | To | Condition | Side Effect |
|------|----|-----------|-------------|
| `todo` | `in_progress` | None | `set_started_at` |
| `in_progress` | `completed` | None | `check_feature_completion` |
| `in_progress` | `blocked` | None | None |
| `todo` | `cancelled` | None | None |
| `in_progress` | `cancelled` | None | None |
| `blocked` | `todo` | None | None |

The `check_feature_completion` side effect inspects remaining tasks on the parent feature and reports how many are still pending — it does NOT auto-complete the feature.

### Gap vs CLAUDE.md Documentation

CLAUDE.md documents the build_tasks state machine as `todo → in_progress → completed`. The actual table also allows `blocked` as an intermediate state and `cancelled` as a terminal from both `todo` and `in_progress`. The documentation is a simplified view, not incorrect, but incomplete.

### Total Documented Transitions: 28

The 28 transitions cover all three entity types. The WorkflowEngine explicitly rejects any transition not present in the table, so adding new valid paths requires inserting rows into `workflow_transitions`.

---

## 5. Column Registry Coverage

`column_registry` has **87 entries**. The schema has 703 columns across 58 tables (per the 2026-02-28 schema governance stats). Coverage is therefore approximately **12%** of all columns — but this is appropriate, as the registry is only meant for constrained (enum/range) columns, not all columns.

### Documented Constrained Columns

| Table | Column | Valid Values (from code/docs) |
|-------|--------|-------------------------------|
| `feedback` | `status` | `new`, `triaged`, `in_progress`, `resolved`, `wont_fix`, `duplicate` |
| `feedback` | `feedback_type` | `bug`, `design`, `question`, `change`, `idea` |
| `features` | `status` | `draft`, `planned`, `in_progress`, `blocked`, `completed`, `cancelled` |
| `build_tasks` | `status` | `todo`, `in_progress`, `blocked`, `completed`, `cancelled` |
| `knowledge` | `tier` | `short`, `mid`, `long`, `archived` |
| `messages` | `status` | `pending`, `read`, `acknowledged`, `actioned`, `deferred` |
| `messages` | `message_type` | `task_request`, `status_update`, `question`, `notification`, `handoff`, `broadcast` |
| `session_facts` | `fact_type` | `credential`, `config`, `endpoint`, `decision`, `note`, `data`, `reference` |
| `knowledge_routes` | `knowledge_type` | `sop`, `pattern`, `book`, `domain`, `tool` |
| `knowledge_routes` | `priority` | `1-5` (integer range) |
| `projects` | `priority` | `1-5` |
| `build_tasks` | `priority` | `1-5` |

### Registry Health Issues

1. **`build_tasks.status` canonical value**: Registry (and CHECK constraint) specifies `todo`. The Work Tracking Schema vault doc incorrectly lists `pending`. Any code or documentation reference to `pending` for build_tasks will silently fail the constraint. This is the most dangerous documented discrepancy.

2. **`schema_docs.py --sync-column-registry`**: This tool auto-syncs CHECK constraint values into the registry. Running it after the cleanup would rebuild the 87 entries from the live constraints. This is the authoritative reconciliation path.

3. **Registry covers all three primary entity tables** (`features`, `feedback`, `build_tasks`) with their status columns — the highest-risk constrained fields.

---

## 6. Empty / Dead Tables to Consider Dropping

### Already Dropped (43 tables via pre_metis_cleanup.sql)

All 43 tables listed in `scripts/sql/pre_metis_cleanup.sql` should now be gone. The `schema_registry` still has 101 rows including their entries — that is the cleanup gap.

### Currently Empty Tables in the 58-Table Schema

| Table | Rows | Recommendation |
|-------|------|----------------|
| `process_data_map` | 0 | Keep — bpmn-engine validation tool reads it; populate with `sync_bpmn_processes` |
| `workflow_state` | 0 | Investigate — no active write path found; may be vestigial from earlier WorkflowEngine design |
| `rag_query_patterns` | 0 | Keep — RAG learning system; populate requires hook instrumentation |
| `instructions_versions` | 0 | Keep — versioning backfill needed |
| `rules_versions` | 0 | Keep — versioning backfill needed |
| `skills_versions` | 0 | Keep — versioning backfill needed |

`workflow_state` is the only empty table with no clear activation path. The WorkflowEngine code in `server_v2.py` does not write to it. It could be a planned feature for per-entity workflow state persistence that was never implemented.

---

## 7. Architecture and Design Observations

### Strong Design Patterns

1. **Column Registry as Data Gateway**: The pattern of checking `column_registry` before writing to constrained columns is sound and prevents constraint violations at the application layer before they hit the database. The CHECK constraints at the DB layer provide a second enforcement line.

2. **WorkflowEngine with Audit Log**: State transitions through `workflow_transitions` with mandatory `audit_log` writes provides a clean event-sourcing pattern for three entity types. The 28-transition table is small enough to be fully human-readable.

3. **Short Codes for Human Reference**: The `short_code SERIAL` pattern on `features` (F1), `feedback` (FB1), and `build_tasks` (BT1) makes work items referenceable in git commit messages and chat without UUIDs.

4. **3-Tier Cognitive Memory**: The `knowledge` table with `tier` column (`short`/`mid`/`long`/`archived`) and the `consolidate_memories()` lifecycle is a sound alternative to unbounded knowledge graphs. Budget-capped recall prevents context flooding.

5. **Schema Governance Layer**: `schema_docs.py`, `embed_schema.py`, and `schema_registry` form a self-documenting schema system that automatically generates COMMENT ON statements and embeddings for RAG queries about the schema itself.

### Risks and Weak Points

1. **`schema_registry` drift**: 101 rows vs 58 live tables. Stale entries for dropped tables will appear in schema-RAG results, potentially misdirecting Claude about valid tables.

2. **`sessions.project_name` instead of `project_id`**: Sessions are identified by the mutable project name string. If a project is renamed in `workspaces`, historical sessions lose their JOIN path to the project record.

3. **`mcp_usage` data reliability**: 6,965 rows that are all synthetic. Any analytics on MCP tool usage frequency built on this table would produce garbage results.

4. **`enforcement_log` zombie writes**: If `process_router.py` is still executing (even in archived form called from hooks), it is writing to `enforcement_log`. This creates an orphaned data stream with no consumer.

5. **Versioning tables not backfilled**: `instructions_versions`, `rules_versions`, `skills_versions` all have 0 rows. The versioning system for DB-as-source-of-truth is partially operational.

6. **`Work Tracking Schema.md` stale**: The vault document lists `pending` as a valid `build_tasks.status`. The actual constraint is `todo`. This document will mislead any Claude reading it without also reading MEMORY.md.

---

## Key File References

| File | Purpose |
|------|---------|
| `/C:/Projects/claude-family/knowledge-vault/20-Domains/Table Code Reference Map - KEEP.md` | Authoritative 58-table inventory with row counts |
| `/C:/Projects/claude-family/knowledge-vault/20-Domains/Table Code Reference Map.md` | Dropped 43 tables with disposition |
| `/C:/Projects/claude-family/scripts/sql/pre_metis_cleanup.sql` | DROP TABLE script for 43 tables |
| `/C:/Projects/claude-family/scripts/sql/f98_schema.sql` | books, book_references, knowledge_routes creation |
| `/C:/Projects/claude-family/scripts/schema_docs.py` | Schema governance: report, comment generation, registry sync |
| `/C:/Projects/claude-family/scripts/embed_schema.py` | Schema embedding pipeline for RAG |
| `/C:/Projects/claude-family/mcp-servers/project-tools/server_v2.py` | WorkflowEngine (lines 1101-1361), state machine transitions, all v3 MCP tools |
| `/C:/Projects/claude-family/docs/standards/DATABASE_STANDARDS.md` | Naming conventions, constraint patterns, column_registry usage |
| `/C:/Projects/claude-family/knowledge-vault/20-Domains/Database/Work Tracking Schema.md` | Stale document — lists `pending` instead of `todo` for build_tasks |
| `/C:/Projects/claude-family/knowledge-vault/20-Domains/Infrastructure Stats and Monitoring.md` | mcp_usage data quality issue documented here |