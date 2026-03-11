---
projects:
- claude-family
- Project-Metis
tags:
- audit
- bpmn
- governance
synced: false
---

# Audit: BPMN Process Governance

**Parent**: [[claude-family-systems-audit]]
**Raw data**: `docs/audit/bpmn_audit.md` (19K chars)

---

## What It Is

76 BPMN process models defining how every system works. Executed by SpiffWorkflow 3.1.2, tested with pytest (~109+ tests). Models are the source of truth — code implements the model, not vice versa.

## Hierarchy

| Level | Count | Scope | Example |
|-------|-------|-------|---------|
| L0 | 1 | System-wide architecture | `L0_claude_family.bpmn` (6 swim lanes) |
| L1 | 8+ | Subsystem models | Session, Work Tracking, Knowledge, Enforcement, Config, Agents, Core, Extensions |
| L2 | 60+ | Detailed workflows | Per hook, per feature lifecycle, per memory operation |

## Process Inventory by Category

| Category | Files | Key Processes |
|----------|-------|--------------|
| **Architecture** (12) | L0 system + 8 L1 models + stubs + task work cycle | Foundation models; 7 test files |
| **Infrastructure** (18) | hook_chain, precompact, session_end, todo/task sync, mcp_usage, subagent, failure_capture, content_validation, context_budget, context_preservation, credential_loading, bpmn_sync, schema_governance, system_maintenance, db_cleanup, config deployment | Every hook has a model |
| **Lifecycle** (22) | session, task, feature, rag_pipeline, config_deployment, agent, feedback_to_feature, working_memory, knowledge_full_cycle, 4x cognitive_memory, project, project_tools_routing, skill_discovery, messaging, crash_recovery, design_document, design_structural | Most comprehensive category |
| **Development** (6) | system_change_process, structured_autonomy, commit_workflow, input_decomposition, audit_findings_pipeline, process_governance | Meta-processes (how to change the system) |
| **Nimbus** (3) | nimbus_delivery, knowledge_ingestion, support_triage | Client-specific |
| **UI** (2) | bpmn_viewer, session_monitor | UI components |

## BPMN Engine (10 MCP tools)

| Tool | Purpose | Status |
|------|---------|--------|
| `list_processes` | Discover all BPMN files | Working |
| `get_process` | Elements and flows overview | Working |
| `get_subprocess` | Element detail with in/out flows | Working |
| `validate_process` | Parse (SpiffWorkflow) + pytest | Working |
| `get_current_step` | GPS navigation (replay + ready tasks) | Working |
| `get_dependency_tree` | Recursive callActivity walker | Working |
| `search_processes` | Keyword search across all | Working |
| `check_alignment` | BPMN vs `_ARTIFACT_REGISTRY` | Partial (covers 8 processes) |
| `file_alignment_gaps` | Run alignment + auto-file feedback | Working |
| `validate_process_schema` | Check BPMN data refs vs live DB | Working |

## Validation Sample (6 key processes)

| Process | Tests | Notes |
|---------|-------|-------|
| `hook_chain` | 8 | Well-tested; v2 rewrite |
| `session_lifecycle` | 9 | v3 model; auto_archive, check_messages verified |
| `feature_workflow` | 9 | v3; per-task loop, create_build_tasks |
| `rag_pipeline` | 4 | Embed + retrieve paths |
| `cognitive_memory_capture` | 30 | 4 processes in one test file |
| `system_change_process` | 4 | Meta-process; create/update/retry paths |

## Issues

1. **Registry sync broken** — `sync_bpmn_to_db.py` imports `_discover_process_files` and `_parse_bpmn_file` which don't exist in server.py. ImportError on execution.
2. **check_alignment covers only ~8 processes** — `_ARTIFACT_REGISTRY` has ~90 entries mapping to 8 processes. Other 68 processes return 0% coverage.
3. **processes/README.md lists 8 of 63 files** — Severely outdated.
4. **`_ARTIFACT_REGISTRY` references orchestrator** — `review_code` still points to `orchestrator.spawn_agent`.
5. **20 model-vs-reality gaps documented** — 7 in task_lifecycle, 7 in session_lifecycle, 6 in feature_workflow. v3 models addressed some.
6. **process_data_map table empty** — `validate_process_schema` has no data to validate against.

## Effectiveness

BPMN-first is a **genuine differentiator**. Benefits proven:
- New Claudes understand systems by reading models (not just code)
- Process changes are validated before implementation
- Test suite catches regressions in process logic
- `system_change_process` rule enforces BPMN-first for hook/workflow changes

The 76-process coverage across 6 categories is impressive for a ~5-month project. SpiffWorkflow provides real execution semantics.

## For Metis

**Keep**: BPMN-first pattern, L0/L1/L2 hierarchy, pytest validation, GPS navigation (`get_current_step`).
**Upgrade**: Consider Camunda Platform 8 or Temporal.io for production execution (SpiffWorkflow is Python-only). Add BPMN visualization in management UI. Expand `_ARTIFACT_REGISTRY` to all processes.

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-audit-bpmn.md
