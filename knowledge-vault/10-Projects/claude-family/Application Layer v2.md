---
projects:
- claude-family
tags:
- architecture
- workflow
- state-machine
- mcp
synced: false
---

# Project-Tools v2 Application Layer

## Overview

The v2 application layer transforms project-tools from a CRUD wrapper into a workflow-enforcing MCP server. Status changes go through a state machine, conditions are checked, side effects execute automatically, and everything is logged to an immutable audit trail.

## Architecture

```
Claude Code → MCP Tool Call → WorkflowEngine → validate_transition()
                                              → check_condition()
                                              → UPDATE status
                                              → execute_side_effect()
                                              → INSERT audit_log
```

## Key Tables

### claude.workflow_transitions

Defines all valid state transitions per entity type.

| Column | Purpose |
|--------|---------|
| entity_type | feedback, features, build_tasks |
| from_status | Current status |
| to_status | Target status |
| requires_condition | Named condition (e.g., `all_tasks_done`) |
| side_effect | Named side effect (e.g., `check_feature_completion`) |

**28 transitions total**: feedback(10), features(10), build_tasks(8).

### claude.audit_log

Immutable trail of all state changes.

| Column | Purpose |
|--------|---------|
| entity_type, entity_id, entity_code | What changed |
| from_status, to_status | The transition |
| changed_by | Session ID |
| change_source | workflow_engine, mcp_tool, start_work, complete_work |
| side_effects_executed | What side effects ran |
| metadata | Extra context (JSONB) |

## State Machines

### Feedback
```
new → triaged → in_progress → resolved
new → duplicate | wont_fix
triaged → duplicate | wont_fix
in_progress → wont_fix
resolved → in_progress (reopen)
```

### Features
```
draft → planned → in_progress → completed (requires: all_tasks_done)
planned → cancelled
in_progress → blocked → in_progress (unblock)
in_progress → cancelled
completed → in_progress (reopen)
cancelled → planned (revive)
```

### Build Tasks
```
todo → in_progress (side_effect: set_started_at)
in_progress → completed (side_effect: check_feature_completion)
in_progress → blocked → in_progress | todo
todo | in_progress | blocked → cancelled
```

## New MCP Tools

| Tool | Purpose |
|------|---------|
| `advance_status(type, id, status)` | Generic state machine transition |
| `start_work(task_code)` | todo→in_progress + load plan_data + set focus |
| `complete_work(task_code)` | in_progress→completed + feature check + next task |
| `get_work_context(scope)` | Token-budgeted context (current/feature/project) |
| `create_linked_task(feature, name)` | Add task to active feature (validates feature status) |

## WorkflowEngine Class

Located in `mcp-servers/project-tools/server_v2.py`.

Key methods:
- `_resolve_entity()` - Resolves short codes (BT3, F12) to UUIDs
- `validate_transition()` - Checks workflow_transitions table
- `check_condition()` - Evaluates named conditions (all_tasks_done, has_assignee)
- `execute_side_effect()` - Runs side effects (check_feature_completion, set_started_at)
- `execute_transition()` - Full pipeline: validate → condition → update → side_effect → audit

## Legacy Compatibility

All 22 existing tools remain functional. `update_work_status` now routes through the WorkflowEngine, so legacy callers get state machine enforcement automatically.

## Deprecated Tools

| Tool | Replacement |
|------|-------------|
| `get_project_context` | `start_session()` |
| `get_session_resume` | `start_session()` |

## Related

- [[Config Management SOP]] - How settings are generated
- [[Family Rules]] - Coordination rules
- [[MCP Registry]] - Active MCP servers

---

**Version**: 1.0
**Created**: 2026-02-10
**Updated**: 2026-02-10
**Location**: 10-Projects/claude-family/Application Layer v2.md
