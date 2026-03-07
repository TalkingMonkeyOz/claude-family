---
projects:
- claude-family
tags:
- bpmn
- processes
- architecture
synced: false
---

# BPMN Process Map: Overview

Complete inventory of all BPMN processes in the claude-family system.

## Summary Counts

| Metric | Count |
|--------|-------|
| BPMN files (.bpmn) | 59 |
| Process definitions (isExecutable=true) | 66 |
| Test files | 53 |
| Test functions | 592 |
| Process directories | 5 |
| callActivity cross-references | 9 |
| Hook scripts mapped to BPMN | 11 of 13 active hooks |

## Category Index

| Category | Processes | Files | Tests |
|----------|-----------|-------|-------|
| [Architecture](bpmn-process-map-architecture.md) | 12 definitions | 9 files | 101 tests |
| [Infrastructure](bpmn-process-map-infrastructure.md) | 16 | 16 files | 205 tests |
| [Lifecycle](bpmn-process-map-lifecycle.md) | 21 | 21 files | 198 tests |
| [Development](bpmn-process-map-development.md) | 6 | 6 files | 65 tests |
| [Nimbus](bpmn-process-map-nimbus.md) | 3 | 3 files | 12 tests |

## L0 -> L1 -> L2 Hierarchy

```
L0: L0_claude_family (claude_process)
    +-- callActivity: L1_session_management
    +-- callActivity: L1_work_tracking
    |       +-- callActivity: task_lifecycle (L2)
    +-- callActivity: L1_knowledge_management
    +-- callActivity: L1_enforcement
    +-- callActivity: L1_agent_orchestration
    +-- callActivity: L1_config_management

Architectural extension chain:
    L1_claude_family_extensions
        +-- callActivity: L2_task_work_cycle
                +-- callActivity: L1_core_claude
```

## callActivity Cross-Reference

| Source | Target | File |
|--------|--------|------|
| claude_process (L0) | L1_session_management | L0_claude_family.bpmn |
| claude_process (L0) | L1_work_tracking | L0_claude_family.bpmn |
| claude_process (L0) | L1_knowledge_management | L0_claude_family.bpmn |
| claude_process (L0) | L1_enforcement | L0_claude_family.bpmn |
| claude_process (L0) | L1_agent_orchestration | L0_claude_family.bpmn |
| claude_process (L0) | L1_config_management | L0_claude_family.bpmn |
| L1_work_tracking | task_lifecycle | L1_work_tracking.bpmn |
| L1_claude_family_extensions | L2_task_work_cycle | L1_claude_family_extensions.bpmn |
| L2_task_work_cycle | L1_core_claude | L2_task_work_cycle.bpmn |

## Hook Script to BPMN Mapping

| Hook Script | Event | BPMN Process |
|-------------|-------|--------------|
| session_startup_hook_enhanced.py | SessionStart | L1_session_management, L1_claude_family_extensions |
| rag_query_hook.py | UserPromptSubmit | hook_chain (Phase 1) |
| task_discipline_hook.py | PreToolUse(Write/Edit/Task/Bash) | hook_chain (Phase 2), L1_enforcement |
| context_injector_hook.py | PreToolUse(Write/Edit) | content_validation |
| standards_validator.py | PreToolUse(Write/Edit) | content_validation |
| todo_sync_hook.py | PostToolUse(TodoWrite) | todo_sync |
| task_sync_hook.py | PostToolUse(TaskCreate/TaskUpdate) | task_sync |
| mcp_usage_logger.py | PostToolUse(all) | mcp_usage_logging |
| precompact_hook.py | PreCompact | precompact |
| session_end_hook.py | SessionEnd | session_end |
| subagent_start_hook.py | SubagentStart | subagent_start |

`failure_capture.py` is not a hook - it is a module called from the catch blocks of all 11 hooks.

## File Locations

```
C:\Projects\claude-family\mcp-servers\bpmn-engine\processes\
    architecture\    (9 files)
    infrastructure\  (16 files)
    lifecycle\       (21 files)
    development\     (6 files)
    nimbus\          (3 files)

C:\Projects\claude-family\mcp-servers\bpmn-engine\tests\
    (53 test files, 592 test functions)
```

## Recent Model Updates

| Date | File | Change |
|------|------|--------|
| 2026-03-07 | `lifecycle/task_lifecycle.bpmn` | +5 elements: `bridge_to_build_task`, `has_more_tasks_gw`, `check_feature_completion`, `midway_status_update` (scriptTask), updated `mark_gate_blocked` + `check_staleness` names, `resolve_blocker` flow changed |
| 2026-03-07 | `lifecycle/session_lifecycle.bpmn` | +5 elements: `auto_archive`, `check_messages`, `rag_per_prompt`, `auto_close_session` (scriptTasks), `end_auto` (endEvent); `save_checkpoint` renamed |
| 2026-03-07 | `lifecycle/feature_workflow.bpmn` | +6 elements: `create_build_tasks` (userTask), `set_in_progress` (scriptTask), `next_task_gw` (gateway), `start_task`, `complete_task` (scriptTasks), `implement_task` (userTask); added enforcement `bpmn:documentation` on `run_tests`, `review_code`, `plan_feature` |

Summary counts above reflect the 2026-02-28 scan. Re-run `python scripts/sync_bpmn_to_db.py` to update.

---
**Version**: 1.1
**Created**: 2026-02-28
**Updated**: 2026-03-07
**Location**: knowledge-vault/10-Projects/Project-Metis/bpmn-process-map.md
