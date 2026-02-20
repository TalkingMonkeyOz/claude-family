# BPMN Process Library

Executable, testable process definitions for Claude Family infrastructure.

Each `.bpmn` file is a BPMN 2.0 XML document executable by SpiffWorkflow 3.x. Every process has a corresponding `test_<process_id>.py` in `../tests/`.

## Process Catalog

### lifecycle/

Processes governing how work items move through their states.

| Process ID | Name | Description | Tests |
|-----------|------|-------------|-------|
| `task_lifecycle` | Task Lifecycle | Create task -> discipline gate -> work/block loop -> completion | 3 |
| `session_lifecycle` | Session Lifecycle | Session start -> load state -> work loop (compact/continue/end) | 4 |
| `feature_workflow` | Feature Workflow | Draft -> plan -> implement (simple/complex) -> test -> review -> complete | 4 |

### infrastructure/

Processes governing system internals and enforcement mechanisms.

| Process ID | Name | Description | Tests |
|-----------|------|-------------|-------|
| `hook_chain` | Hook Chain | Prompt -> RAG -> discipline gate -> tool execution -> sync | 3 |

### development/

Processes for development workflows (planned).

| Process ID | Name | Description | Tests |
|-----------|------|-------------|-------|
| *TBD* | Code Review | Review workflow with approval/rejection loops | - |
| *TBD* | Agent Orchestration | Multi-agent coordination patterns | - |

## Usage

### Via MCP (bpmn-engine server)

```
list_processes()           # Discover all processes
get_process("task_lifecycle")  # Get process structure
validate_process("task_lifecycle")  # Parse + run tests
get_current_step("task_lifecycle", completed_steps=["create_task"], data={"has_tasks": True})
```

### Via pytest

```bash
cd mcp-servers/bpmn-engine
python -m pytest tests/ -v          # All processes
python -m pytest tests/test_task_lifecycle.py -v  # Single process
```

## Adding a New Process

1. Create `processes/<category>/<process_id>.bpmn` following existing patterns
2. Create `tests/test_<process_id>.py` with at least: happy path, error path, loop path
3. Run `python -m pytest tests/test_<process_id>.py -v` to verify
4. Add entry to this catalog

## BPMN Conventions

- `userTask` = manual step (test injects data via `task.data.update()`)
- `scriptTask` = automated step (inline Python, e.g., `status = "completed"`)
- `exclusiveGateway` = branching (conditions) or merging (multiple incoming, one outgoing)
- Gateway conditions are Python expressions evaluated against `task.data`
- Default flows use `default="flow_id"` attribute on gateway (no condition needed)
- All variables used in conditions MUST exist in `task.data` before the gateway evaluates

---
**Version**: 1.0
**Created**: 2026-02-20
**Updated**: 2026-02-20
**Location**: mcp-servers/bpmn-engine/processes/README.md
