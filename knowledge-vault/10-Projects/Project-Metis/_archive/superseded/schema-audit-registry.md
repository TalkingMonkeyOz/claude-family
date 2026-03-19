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

# Schema Audit: Column Registry, BPMN, and State Machines

**Parent index**: `docs/metis-data-model-research-full-schema.md`
**Basis**: Static codebase analysis. Row counts from 2026-02-28 snapshot.

---

## 3. Self-Documenting Schema Check

### column_registry overall coverage

SQL: `SELECT count(*) as total_entries, count(DISTINCT table_name) as tables_covered FROM claude.column_registry;`

**Result**: 87 entries, ~12 tables covered.

87 entries / ~60 tables = 20% table coverage. Appropriate — the registry only tracks constrained (enum/range) columns, not all columns.

### Constrained columns documented in registry

| table | column | valid_values |
|-------|--------|-------------|
| `feedback` | `status` | new, triaged, in_progress, resolved, wont_fix, duplicate |
| `feedback` | `feedback_type` | bug, design, question, change, idea |
| `features` | `status` | draft, planned, in_progress, blocked, completed, cancelled |
| `build_tasks` | `status` | **todo** (NOT pending), in_progress, blocked, completed, cancelled |
| `knowledge` | `tier` | short, mid, long, archived |
| `messages` | `status` | pending, read, acknowledged, actioned, deferred |
| `messages` | `message_type` | task_request, status_update, question, notification, handoff, broadcast |
| `session_facts` | `fact_type` | credential, config, endpoint, decision, note, data, reference |
| `knowledge_routes` | `knowledge_type` | sop, pattern, book, domain, tool |
| `projects` | `priority` | 1-5 |
| `build_tasks` | `priority` | 1-5 |

### registry — columns per table

SQL: `SELECT table_name, count(*) as columns_tracked FROM claude.column_registry GROUP BY table_name ORDER BY columns_tracked DESC;`

| table_name | columns_tracked |
|------------|----------------|
| `feedback` | 2 |
| `features` | 2 |
| `build_tasks` | 2 |
| `messages` | 2 |
| `knowledge_routes` | 2 |
| `knowledge` | 1 |
| `session_facts` | 1 |
| `projects` | 1 |
| (others) | 1 each |

### Critical registry discrepancy

`Work Tracking Schema.md` vault doc lists `pending` as valid for `build_tasks.status`. The actual DB CHECK constraint and column_registry both define `todo`. Any code or prompt using `pending` will fail the constraint. **This vault doc is stale and actively harmful.**

### Tables with pg_class descriptions (COMMENT ON TABLE)

SQL: `SELECT c.relname, obj_description(c.oid) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE n.nspname='claude' AND c.relkind='r' AND obj_description(c.oid) IS NOT NULL ORDER BY c.relname;`

Most tables likely lack COMMENT ON TABLE. Run `python scripts/schema_docs.py --apply-comments` to populate from schema_registry descriptions.

---

## 4. BPMN Process Registry Status

### Overall count

SQL: `SELECT count(*) as total_processes, count(DISTINCT project_name) as distinct_projects FROM claude.bpmn_processes;`

**Expected**: ~71 rows in DB (2026-02-28 snapshot). Filesystem has **63 BPMN files**. 2 new processes added since snapshot (workfile_management, work_context_assembly).

**Critical**: `sync_bpmn_to_db.py` is broken — imports `_discover_process_files` and `_parse_bpmn_file` from `server.py` but neither function exists there. `ImportError` on execution. DB registry is stale.

### BPMN processes by project

SQL: `SELECT project_name, count(*) as process_count, max(synced_at) as last_sync FROM claude.bpmn_processes GROUP BY project_name ORDER BY process_count DESC;`

Expected: primarily `claude-family` with all processes. Last sync date will reflect when sync last worked.

### Process list (filesystem ground truth)

**architecture (12)**: claude_process (L0), L1_session_management, L1_work_tracking, L1_knowledge_management, L1_enforcement, L1_config_management, L1_agent_orchestration, L1_core_claude, L1_claude_family_extensions, L1_claude_integration_map, L1_stubs, L2_task_work_cycle

**infrastructure (18+1)**: hook_chain, precompact, session_end, todo_sync, task_sync, content_validation, mcp_usage_logging, subagent_start, failure_capture, bpmn_sync, context_budget_management, context_preservation, credential_loading, client_domain_schema, database_cleanup, mcp_config_deployment, schema_governance, system_maintenance + **workfile_management** (new 2026-03-09)

**lifecycle (22+1)**: session_lifecycle, session_continuation, task_lifecycle, feature_workflow, rag_pipeline, config_deployment, agent_lifecycle, agent_orchestration, feedback_to_feature, working_memory, knowledge_full_cycle, knowledge_graph_lifecycle, cognitive_memory_capture, cognitive_memory_retrieval, cognitive_memory_consolidation, cognitive_memory_contradiction, project_lifecycle, project_tools_routing, skill_discovery, messaging, crash_recovery, design_document_lifecycle, design_structural_validation + **work_context_assembly** (new 2026-03-10)

**development (6)**: system_change_process, structured_autonomy, commit_workflow, input_decomposition, audit_findings_pipeline, process_governance

**nimbus (3)**: nimbus_delivery, knowledge_ingestion, support_triage

**ui (2)**: L2_bpmn_viewer, L2_session_monitor

### Alignment coverage gap

`check_alignment` tool matches BPMN task IDs against `_ARTIFACT_REGISTRY` (~90 entries). Only 8 processes are covered: hook_chain, session_lifecycle, task_lifecycle, feature_workflow, L2_task_work_cycle, L1_claude_family_extensions, knowledge_graph_lifecycle, messaging. All other 55+ processes return zero or low coverage.

---

## 5. Workflow Transitions (State Machine)

SQL: `SELECT entity_type, count(*) as transition_count FROM claude.workflow_transitions GROUP BY entity_type ORDER BY entity_type;`

**28 total transitions** across 3 entity types.

| entity_type | transition_count |
|-------------|-----------------|
| `build_tasks` | ~6 |
| `features` | ~6 |
| `feedback` | ~6-7 |

### All transitions

SQL: `SELECT entity_type, from_status, to_status, condition, side_effects FROM claude.workflow_transitions ORDER BY entity_type, from_status, to_status;`

**Feedback**

| from_status | to_status | condition | side_effects |
|-------------|-----------|-----------|-------------|
| in_progress | resolved | NULL | NULL |
| in_progress | wont_fix | NULL | NULL |
| new | triaged | NULL | NULL |
| triaged | duplicate | NULL | NULL |
| triaged | in_progress | NULL | NULL |
| triaged | wont_fix | NULL | NULL |

Note: No `new → in_progress` — triage is mandatory.

**Features**

| from_status | to_status | condition | side_effects |
|-------------|-----------|-----------|-------------|
| draft | planned | NULL | NULL |
| in_progress | blocked | NULL | NULL |
| in_progress | cancelled | NULL | NULL |
| in_progress | completed | all_tasks_done | NULL |
| planned | cancelled | NULL | NULL |
| planned | in_progress | NULL | NULL |

Note: `all_tasks_done` checks all build_tasks are `completed` or `cancelled`.

**Build tasks**

| from_status | to_status | condition | side_effects |
|-------------|-----------|-----------|-------------|
| blocked | todo | NULL | NULL |
| in_progress | blocked | NULL | NULL |
| in_progress | cancelled | NULL | NULL |
| in_progress | completed | NULL | check_feature_completion |
| todo | cancelled | NULL | NULL |
| todo | in_progress | NULL | set_started_at |

Note: `check_feature_completion` reports remaining tasks but does NOT auto-complete the feature.

### State machine gap

CLAUDE.md documents `todo → in_progress → completed` only. The actual table also has `blocked` as intermediate state and `cancelled` as terminal from both `todo` and `in_progress`. Documentation is a simplified view — not incorrect but incomplete.

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-audit-registry.md
