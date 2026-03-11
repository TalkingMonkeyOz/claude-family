---
projects:
- claude-family
tags:
- bpmn
- architecture
synced: false
---

# BPMN Processes: Architecture Category

9 files, 12 process definitions (including 8 stubs), 101 tests.

Back to: [Process Map Overview](bpmn-process-map.md)

## L0 Process

| Process ID | File | Description |
|------------|------|-------------|
| `claude_process` (+ 5 non-executable pools) | L0_claude_family.bpmn | Full swim-lane collaboration: Human, Claude, Database, Hooks, Knowledge, Agents. claude_process calls 6 L1 capabilities via callActivity. The only true system-wide view. Has BPMNDiagram layout. |

## L1 Processes

| Process ID | File | Elements | Flows | Description |
|------------|------|----------|-------|-------------|
| `L1_session_management` | L1_session_management.bpmn | ~30 | ~22 | Startup (log, reset task map, archive stale, check inbox), state load (fresh/resume), work loop (RAG + process + tools), compact path (FB108 continuation gateway), auto-close, manual /session-end |
| `L1_work_tracking` | L1_work_tracking.bpmn | ~28 | ~20 | Feature/feedback/adhoc triage. Feature path calls task_lifecycle as L2 subprocess. WorkflowEngine state machines enforced. |
| `L1_knowledge_management` | L1_knowledge_management.bpmn | ~18 | ~12 | Simplified capture (embed+store) vs retrieve (RAG+apply+track). Superseded by knowledge_full_cycle for full detail. |
| `L1_enforcement` | L1_enforcement.bpmn | ~22 | ~16 | Task discipline gate (3-way: allowed/continuation/blocked per FB108), context injection, standards validation, PostToolUse sync |
| `L1_agent_orchestration` | L1_agent_orchestration.bpmn | ~18 | ~14 | Need assessment, type selection (coder/reviewer/tester), spawn, monitor, retry/integrate |
| `L1_config_management` | L1_config_management.bpmn | ~18 | ~13 | Global vs project scope, DB update, settings generation, component deployment, validation. Database is source of truth. |
| `L1_core_claude` | L1_core_claude.bpmn | ~34 | ~26 | Single prompt-response cycle for vanilla Claude. Intent (question/conversation/action), complexity (simple/multi_step/delegation), tool loop with reflection, response composition. |
| `L1_claude_family_extensions` | L1_claude_family_extensions.bpmn | ~44 | ~34 | Extension wrapper around L1_core_claude. Full session lifecycle with hooks, RAG, and L2_task_work_cycle CallActivity. 3-layer architecture: extensions -> task work cycle -> core. |
| `L1_claude_integration_map` | L1_claude_integration_map.bpmn | ~32 | ~24 | Maps all external interface points: [CONFIG] load order (settings, MCPs, CLAUDE.md global, CLAUDE.md project, rules, instructions, skills, memory), [HOOK] events, [BUILTIN] tool execution |

## L2 Process

| Process ID | File | Elements | Flows | Description |
|------------|------|----------|-------|-------------|
| `L2_task_work_cycle` | L2_task_work_cycle.bpmn | ~32 | ~24 | Task decomposition, DB sync, discipline gate (no-tasks -> blocked), task type (build=BPMN-first, simple=direct), L1_core_claude CallActivity, outcome: completed/blocked/session_end |

## Support: Stubs

| Process IDs (8) | File | Description |
|-----------------|------|-------------|
| L1_session_management, L1_work_tracking, L1_knowledge_management, L1_enforcement, L1_agent_orchestration, L1_config_management, L1_core_claude, L1_claude_family_extensions | L1_stubs.bpmn | Minimal start-task-end stubs for SpiffWorkflow callActivity resolution during L0 tests. No real logic. |

## Key Structural Notes

- L1_claude_family_extensions and L1_session_management overlap significantly by design - extensions is the "full picture" while session_management is the L0 drill-down
- L1_core_claude models vanilla Claude (no Family infrastructure) - called by L2_task_work_cycle for individual task execution
- L1_claude_integration_map is the authoritative reference for what Claude Code hooks/config the Family controls

## Test Files

test_L0_claude_family.py (6), test_L1_processes.py (23), test_core_claude.py (9), test_claude_family_extensions.py (10), test_integration_map.py (31), test_layered_architecture.py (10), test_task_work_cycle.py (12)

---
**Version**: 1.0
**Created**: 2026-02-28
**Updated**: 2026-02-28
**Location**: knowledge-vault/10-Projects/Project-Metis/bpmn-process-map-architecture.md
