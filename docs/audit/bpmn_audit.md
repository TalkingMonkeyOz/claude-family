I now have all the information I need to compile the comprehensive report.

---

# Claude Family BPMN System - Technical Research Report

## Process Count Discrepancy

The task states 76 processes. The filesystem contains **63 BPMN files** across 6 categories. The README.md catalog (last updated 2026-02-20) lists only 8 processes, indicating the README is severely stale. The 76 figure likely comes from the `claude.bpmn_processes` database registry, which may include processes from other project workspaces synced separately.

---

## 1. Coverage Assessment - Process Inventory by Category

### Category: architecture (10 files)

| File | Process ID | Level | Description |
|------|-----------|-------|-------------|
| `L0_claude_family.bpmn` | `claude_process` | L0 | System-wide architecture with all subsystems |
| `L1_session_management.bpmn` | `L1_session_management` | L1 | Session startup, state, shutdown |
| `L1_work_tracking.bpmn` | `L1_work_tracking` | L1 | Features, tasks, build lifecycle |
| `L1_knowledge_management.bpmn` | `L1_knowledge_management` | L1 | RAG, vault, embeddings |
| `L1_enforcement.bpmn` | `L1_enforcement` | L1 | Hook chain, discipline, standards |
| `L1_config_management.bpmn` | `L1_config_management` | L1 | Config deployment, DB-first |
| `L1_agent_orchestration.bpmn` | `L1_agent_orchestration` | L1 | Agent spawning, delegation |
| `L1_core_claude.bpmn` | `L1_core_claude` | L1 | Core Claude model integration |
| `L1_claude_family_extensions.bpmn` | `L1_claude_family_extensions` | L1 | Family-specific extensions |
| `L1_claude_integration_map.bpmn` | `L1_claude_integration_map` | L1 | Integration mapping |
| `L1_stubs.bpmn` | `L1_stubs` | L1 | Stub processes for unimplemented subsystems |
| `L2_task_work_cycle.bpmn` | `L2_task_work_cycle` | L2 | Per-task work cycle detail |

Note: The architecture directory has 12 files total (10 BPMN + 1 README + 1 non-BPMN). Test coverage: `test_L0_claude_family.py`, `test_L1_processes.py`, `test_layered_architecture.py`, `test_core_claude.py`, `test_claude_family_extensions.py`, `test_integration_map.py`, `test_task_work_cycle.py`.

### Category: infrastructure (14 files)

| File | Process ID | Level | Description |
|------|-----------|-------|-------------|
| `hook_chain.bpmn` | `hook_chain` | L2 | Full prompt-to-tool hook execution chain |
| `precompact.bpmn` | `precompact` | L2 | PreCompact hook - context preservation before compression |
| `session_end.bpmn` | `session_end` | L2 | SessionEnd hook - auto-close DB record |
| `todo_sync.bpmn` | `todo_sync` | L2 | TodoWrite sync hook |
| `task_sync.bpmn` | `task_sync` | L2 | TaskCreate/Update sync hook |
| `content_validation.bpmn` | `content_validation` | L2 | Standards validation (PreToolUse) |
| `mcp_usage_logging.bpmn` | `mcp_usage_logging` | L2 | PostToolUse MCP logging |
| `subagent_start.bpmn` | `subagent_start` | L2 | SubagentStart hook |
| `failure_capture.bpmn` | `failure_capture` | L2 | Hook failure auto-filing |
| `bpmn_sync.bpmn` | `bpmn_sync` | L2 | BPMN registry sync to DB |
| `context_budget_management.bpmn` | `context_budget_management` | L2 | Token budget management |
| `context_preservation.bpmn` | `context_preservation` | L2 | Context preservation pattern |
| `credential_loading.bpmn` | `credential_loading` | L2 | Credential/env loading |
| `client_domain_schema.bpmn` | `client_domain_schema` | L2 | Multi-tenant domain schema |
| `database_cleanup.bpmn` | `database_cleanup` | L2 | Schema cleanup/maintenance |
| `mcp_config_deployment.bpmn` | `mcp_config_deployment` | L2 | MCP server config deployment |
| `schema_governance.bpmn` | `schema_governance` | L2 | Schema documentation + embedding |
| `system_maintenance.bpmn` | `system_maintenance` | L2 | Scheduled maintenance |

### Category: lifecycle (22 files)

| File | Process ID | Level | Description |
|------|-----------|-------|-------------|
| `session_lifecycle.bpmn` | `session_lifecycle` | L2 | Full session: start → work loop → end (v3) |
| `session_continuation.bpmn` | `session_continuation` | L2 | Compact/resume/recover flow |
| `task_lifecycle.bpmn` | `task_lifecycle` | L2 | Create → discipline gate → work → complete |
| `feature_workflow.bpmn` | `feature_workflow` | L2 | Draft → plan → implement → test → review (v3) |
| `rag_pipeline.bpmn` | `rag_pipeline` | L2 | Embed path + retrieve path |
| `config_deployment.bpmn` | `config_deployment` | L2 | Config from DB to file deployment |
| `agent_lifecycle.bpmn` | `agent_lifecycle` | L2 | Agent spawn → execute → return |
| `agent_orchestration.bpmn` | `agent_orchestration` | L2 | Multi-agent coordination |
| `feedback_to_feature.bpmn` | `feedback_to_feature` | L2 | Feedback triage → feature promotion |
| `working_memory.bpmn` | `working_memory` | L2 | Session working memory |
| `knowledge_full_cycle.bpmn` | `knowledge_full_cycle` | L2 | Full knowledge ingestion/retrieval cycle |
| `knowledge_graph_lifecycle.bpmn` | `knowledge_graph_lifecycle` | L2 | Graph sync, query, decay, review |
| `cognitive_memory_capture.bpmn` | `cognitive_memory_capture` | L2 | 3-tier memory capture (explicit/auto/harvest) |
| `cognitive_memory_retrieval.bpmn` | `cognitive_memory_retrieval` | L2 | Parallel 3-tier retrieval with budget |
| `cognitive_memory_consolidation.bpmn` | `cognitive_memory_consolidation` | L2 | Promotion/decay/archive lifecycle |
| `cognitive_memory_contradiction.bpmn` | `cognitive_memory_contradiction` | L2 | Dedup/conflict resolution |
| `project_lifecycle.bpmn` | `project_lifecycle` | L2 | Project init → phase → archive |
| `project_tools_routing.bpmn` | `project_tools_routing` | L2 | MCP tool routing logic |
| `skill_discovery.bpmn` | `skill_discovery` | L2 | Skill lookup and invocation |
| `messaging.bpmn` | `messaging` | L2 | Inter-Claude messaging (send/receive/reply) |
| `crash_recovery.bpmn` | `crash_recovery` | L2 | Context loss detection and recovery |
| `design_document_lifecycle.bpmn` | `design_document_lifecycle` | L2 | Design doc phases (brainstorm/consolidate/validate) |
| `design_structural_validation.bpmn` | `design_structural_validation` | L2 | Design coherence/structural checks |

### Category: development (6 files)

| File | Process ID | Level | Description |
|------|-----------|-------|-------------|
| `system_change_process.bpmn` | `system_change_process` | L2 | BPMN-first enforcement meta-process |
| `structured_autonomy.bpmn` | `structured_autonomy` | L2 | Plan/implement/review agent delegation |
| `commit_workflow.bpmn` | `commit_workflow` | L2 | Pre-commit check → commit → verify |
| `input_decomposition.bpmn` | `input_decomposition` | L2 | Multi-part message decomposition |
| `audit_findings_pipeline.bpmn` | `audit_findings_pipeline` | L2 | BPMN gap → classify → file feedback |
| `process_governance.bpmn` | `process_governance` | L2 | BPMN lifecycle and registry governance |

### Category: nimbus (3 files)

| File | Process ID | Level | Description |
|------|-----------|-------|-------------|
| `nimbus_delivery.bpmn` | `nimbus_delivery` | L2 | Client delivery: requirements → deploy → handover |
| `knowledge_ingestion.bpmn` | `knowledge_ingestion` | L2 | 3-way source branching (API/OData/unstructured) |
| `support_triage.bpmn` | `support_triage` | L2 | AI triage → duplicate check → review |

### Category: ui (2 files)

| File | Process ID | Level | Description |
|------|-----------|-------|-------------|
| `L2_bpmn_viewer.bpmn` | `L2_bpmn_viewer` | L2 | Mission Control BPMN viewer component |
| `L2_session_monitor.bpmn` | `L2_session_monitor` | L2 | Session monitor UI component |

---

## 2. BPMN Engine Analysis

### Tool Inventory (10 MCP tools exposed)

| Tool | Purpose |
|------|---------|
| `list_processes` | Discover all BPMN files by scanning processes/ directory |
| `get_process` | Return elements and flows for a process (XML parse, no execution) |
| `get_subprocess` | Zoom into a specific element with incoming/outgoing flows |
| `validate_process` | Level 1: parse via SpiffWorkflow. Level 2: run `pytest test_{id}.py` |
| `get_current_step` | GPS navigation: replay completed steps, return READY user tasks |
| `get_dependency_tree` | Walk callActivity references recursively to build hierarchy |
| `search_processes` | Keyword search across element names, process names, conditions |
| `check_alignment` | Compare BPMN tasks to `_ARTIFACT_REGISTRY`, report coverage % |
| `file_alignment_gaps` | Run `check_alignment` then INSERT gaps into `claude.feedback` |
| `validate_process_schema` | Extract [DB] task annotations, check tables exist in live schema |

### How validate_process Works

Two-level validation. Level 1 uses `SpiffWorkflow.bpmn.parser.BpmnParser` to parse and compile the BPMN XML. If that fails, returns parse errors. Level 2 looks for `tests/test_{process_id}.py` and executes it via `subprocess.run(sys.executable, "-m", "pytest", ...)` with a 60-second timeout. Parses the pytest summary line for pass/fail counts.

### Does check_alignment Actually Work?

Yes, with important caveats. The tool works by matching BPMN task element IDs (not names) against a hardcoded `_ARTIFACT_REGISTRY` dictionary in server.py (approximately 90 entries). Coverage percentage is `mapped_count / total_task_count`. Elements not in the registry are marked "unmapped" with keyword-based suggestions. Artifact existence checking only validates actual file paths for `hook_script` and `rule_file` types; all other types (`mcp_tool`, `claude_behavior`, `agent`, `command`) return `exists=True` unconditionally.

Limitation: The registry covers only a subset of processes (hook_chain, session_lifecycle, task_lifecycle, feature_workflow, L2_task_work_cycle, L1_claude_family_extensions, knowledge_graph_lifecycle, messaging). Most other processes return low or zero coverage.

### Broken Import in sync_bpmn_to_db.py

`C:/Projects/claude-family/scripts/sync_bpmn_to_db.py` imports two functions that do not exist in `server.py`:

```python
from server import _discover_process_files, _parse_bpmn_file
```

Neither `_discover_process_files` nor `_parse_bpmn_file` is defined anywhere in `server.py`. This means `sync_bpmn_to_db.py` will raise an `ImportError` on execution. The MCP tool `mcp__project-tools__sync_bpmn_processes` presumably calls this script. The DB registry sync is therefore broken.

---

## 3. Process Quality - Validation Sample

Test results are derived from reading test files; actual execution was not performed as this is a read-only research task. Based on test structure and BPMN file existence:

| Process ID | BPMN File Exists | Test File | Test Method Count | Notes |
|------------|-----------------|-----------|------------------|-------|
| `hook_chain` | Yes | `test_hook_chain.py` | 8 | Well-tested; v2 rewrite; FB141 session change fix present |
| `session_lifecycle` | Yes | `test_session_lifecycle.py` | 9 | v3 model; auto_archive, check_messages, rag_per_prompt elements verified |
| `feature_workflow` | Yes | `test_feature_workflow.py` | 9 | v3 model; per-task loop, create_build_tasks, set_in_progress tested |
| `rag_pipeline` | Yes | `test_rag_pipeline.py` | 4 | Embed+retrieve paths; no external dependencies |
| `cognitive_memory_capture` | Yes | `test_cognitive_memory.py` | 30 | 4 processes in one file; capture/retrieval/consolidation/contradiction |
| `system_change_process` | Yes | `test_system_change_process.py` | 4 | Update existing, create new, test-fail retry, alignment-fail retry |

All 6 sampled processes have valid BPMN files and substantive tests exercising multiple paths. The test pattern is consistent: use SpiffWorkflow directly, no DB or network dependencies, seed data via `task.data.update()`, assert on `completed_spec_names()`.

---

## 4. Gap Analysis

### Real Systems WITHOUT BPMN Models

Based on examining scripts/ and hooks:

| System | Files | Missing Model |
|--------|-------|--------------|
| `rag_query_hook.py` | `scripts/rag_query_hook.py` | Modeled in `hook_chain.bpmn` but not a standalone process |
| `session_startup_hook_enhanced.py` | `scripts/session_startup_hook_enhanced.py` | Modeled indirectly via `session_lifecycle.bpmn` startup tasks |
| `schema_docs.py` | `scripts/schema_docs.py` | `schema_governance.bpmn` exists - likely covered |
| `embed_schema.py` | `scripts/embed_schema.py` | No dedicated model; partially in `rag_pipeline.bpmn` |
| `generate_project_settings.py` | `scripts/generate_project_settings.py` | No model |
| `embed_vault_documents.py` | `scripts/embed_vault_documents.py` | No dedicated model (rag_pipeline covers the concept) |
| `WorkflowEngine` (DB state machine) | `mcp-servers/project-tools/server_v2.py` | No BPMN model for the WorkflowEngine itself |
| Config 3-layer merge chain | `workspaces.startup_config` + `config_templates` | `config_deployment.bpmn` exists but `mcp_config_deployment.bpmn` may not cover full merge chain |
| `embed_skill_content.py` | `scripts/embed_skill_content.py` | No dedicated model |
| Vault embedding pipeline | `scripts/embed_vault_documents.py` | Only high-level path in rag_pipeline |

### Stale/Orphaned Models

| Concern | Detail |
|---------|--------|
| `bpmn_vs_reality.py` simulation uses old session_lifecycle v2 flow | Lines 244-246 call `restore_context` user task which the v3 model explicitly removes and tests verify should not exist. This simulation script is stale relative to current BPMN. |
| `processes/README.md` | Lists only 8 processes; 63 exist. Last updated 2026-02-20. Severely outdated. |
| `L1_stubs.bpmn` | Described as "stub processes for unimplemented subsystems" - purpose unclear without reading content |
| Orchestrator references | `_ARTIFACT_REGISTRY` entry for `review_code` still points to `orchestrator.spawn_agent` which was retired 2026-02-24. Should reference native Task tool. |
| `lifecycle/agent_orchestration.bpmn` AND `architecture/L1_agent_orchestration.bpmn` | Two separate agent orchestration models at different levels; potential duplication |

### Model Accuracy vs. Current Code

The `bpmn_vs_reality.py` document (an authoritative internal analysis) identified 20 documented gaps across three core processes:

**Task Lifecycle (7 gaps):** BPMN models one task; reality creates 3-5. No mid-progress update step. No multi-task loop. No feature completion cascade. Discipline gate simplified. No stale session handling. `resolve_blocker` loop in BPMN has no hook equivalent.

**Session Lifecycle (7 gaps):** Per-prompt RAG cycle is not nested in BPMN. Auto-archive on startup missing (now added in v3). Message checking missing (now added in v3). PreCompact context injection is different from checkpoint-save. `do_work` is not atomic. Hook chain is not linked. Only one end path in old model (v3 adds `auto_close`).

Note: The v3 session_lifecycle model (current) already addresses several of these gaps (auto_archive, check_messages, auto_close are now present per test assertions).

**Feature Workflow (6 gaps):** Build task creation step missing between plan and implement (v3 adds `create_build_tasks`). Per-task loop missing (v3 adds it). Testing not enforced (BPMN documents "SHOULD BE ENFORCED" but no hook blocks it). Review not enforced. Plan data richness not captured.

---

## 5. BPMN Registry Sync Status

### sync_bpmn_to_db.py is broken

The script at `/C:/Projects/claude-family/scripts/sync_bpmn_to_db.py` will fail immediately with `ImportError` because it imports `_discover_process_files` and `_parse_bpmn_file` from `server.py`, neither of which exist. The script was written against a different version of the server API.

The sync logic itself is correct: it uses SHA-256 file hashing for change detection, upserts into `claude.bpmn_processes` by `process_id`, and determines level from the process_id prefix convention (`L0_`, `L1_`, `L2_`).

### Embedding Status

The DB table `claude.bpmn_processes` has an `embedding` column (from the schema governance layer described in MEMORY.md). Whether embeddings are current is unknown without DB access. Given the sync script is broken, the registry may be out of date with the 63 files on disk.

### process_data_map

The `validate_process_schema` tool references `claude.process_data_map` which tracks process-to-table mappings. Population status unknown.

---

## 6. Engine Health Summary

| Component | Status | Notes |
|-----------|--------|-------|
| SpiffWorkflow 3.1.2 | Healthy | Installed globally in system Python (C:\Python313) |
| server.py | Functional | 10 tools, all well-implemented |
| BPMN parsing (lxml) | Functional | XML namespace handling correct |
| validate_process | Functional | Spawns pytest subprocess, 60s timeout |
| check_alignment | Partially functional | Works for ~8 processes in registry; 0% coverage for most others |
| file_alignment_gaps | Functional when DB reachable | Requires DATABASE_URI env var |
| validate_process_schema | Functional when DB reachable | Requires DATABASE_URI env var |
| sync_bpmn_to_db.py | Broken | ImportError on two missing functions |
| processes/README.md | Stale | Only 8 of 63 processes documented |

---

## 7. Recommendations

**Priority 1 - Fix the broken sync script.** The `sync_bpmn_to_db.py` import of `_discover_process_files` and `_parse_bpmn_file` must be corrected. The replacement should use the existing `list_processes()` function and `_parse_xml()` / `_extract_process_elements()` which do exist in `server.py`.

**Priority 2 - Fix the stale artifact registry entry.** The `review_code` entry in `_ARTIFACT_REGISTRY` references `orchestrator.spawn_agent` (retired 2026-02-24). Change `agent` field to reference native `Task` tool.

**Priority 3 - Update bpmn_vs_reality.py simulation.** Lines 239-246 call `restore_context` which is a removed user task in v3 session_lifecycle. The script will fail if executed as a test runner.

**Priority 4 - Update processes/README.md.** The catalog is at 12% coverage (8 of 63 processes). The README template for adding a process is correct and useful; apply it to all 63 files.

**Priority 5 - Extend _ARTIFACT_REGISTRY.** Only ~8 processes have alignment coverage. Priority candidates: `rag_pipeline`, `cognitive_memory_*` (4 processes), `messaging`, `schema_governance`, `structured_autonomy`, `commit_workflow`.

**Priority 6 - Model the WorkflowEngine state machine.** The DB-level workflow engine (`claude.workflow_transitions` table with 28 transitions) has no BPMN representation. Adding it would complete the "BPMN as source of truth" goal.

---

## Key File Locations

- Server: `/C:/Projects/claude-family/mcp-servers/bpmn-engine/server.py`
- Processes directory: `/C:/Projects/claude-family/mcp-servers/bpmn-engine/processes/`
- Tests directory: `/C:/Projects/claude-family/mcp-servers/bpmn-engine/tests/`
- Broken sync script: `/C:/Projects/claude-family/scripts/sync_bpmn_to_db.py`
- BPMN vs Reality analysis: `/C:/Projects/claude-family/mcp-servers/bpmn-engine/tests/bpmn_vs_reality.py`
- Stale catalog: `/C:/Projects/claude-family/mcp-servers/bpmn-engine/processes/README.md`
- Artifact registry (inline): lines 853-1290 of `server.py`