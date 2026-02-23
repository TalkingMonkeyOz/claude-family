---
projects:
- claude-family
tags:
- spiffworkflow
- bpmn
- workflow-engine
- infrastructure
synced: false
---

# SpiffWorkflow Usage Guide

How the Claude Family uses SpiffWorkflow 3.1.2 as a BPMN process engine.

---

## What SpiffWorkflow Is

[SpiffWorkflow](https://github.com/sartography/SpiffWorkflow) is a Python BPMN/DMN workflow engine by Sartography. It parses standard BPMN 2.0 XML files and executes them as state machines. We use version **3.1.2** (installed via pip, dependency: `lxml`).

---

## What We Use (BPMN Only)

We use **3 classes** from SpiffWorkflow across the entire codebase:

| Class | Import | Purpose |
|-------|--------|---------|
| `BpmnParser` | `SpiffWorkflow.bpmn.parser` | Parse `.bpmn` XML files into workflow specs |
| `BpmnWorkflow` | `SpiffWorkflow.bpmn.workflow` | Create executable workflow instances from specs |
| `TaskState` | `SpiffWorkflow.util.task` | Enumerate task states (READY, COMPLETED, etc.) |

**We do NOT use**: DMN (decision tables), CMMN, serialization, persistence, or SpiffArena.

---

## Where It Lives

```
mcp-servers/bpmn-engine/
├── server.py              # MCP server (9 tools, lxml-based XML parsing + SpiffWorkflow)
├── processes/             # 50 BPMN process files organized by category
│   ├── architecture/      # L0/L1 system-level models
│   ├── development/       # Developer workflows (commit, system change, structured autonomy)
│   ├── infrastructure/    # Hook chains, sync processes, failure capture
│   ├── lifecycle/         # Session, feature, task, knowledge lifecycles
│   └── nimbus/            # Client-specific processes
└── tests/                 # 490 pytest tests (48 test files)
```

---

## Two Usage Modes

### 1. MCP Server (XML Parsing Only — No SpiffWorkflow)

The `server.py` MCP tools (`list_processes`, `get_process`, `get_subprocess`, `search_processes`, `get_dependency_tree`, `check_alignment`) use **raw lxml XML parsing** to inspect BPMN files. They do NOT execute workflows. This is fast and has zero SpiffWorkflow dependency at import time.

Key XML helpers in server.py:
- `_parse_xml(path)` — Parse BPMN file with lxml
- `_extract_process_elements(process_el)` — Extract tasks, events, gateways, flows
- `_find_bpmn_file(process_id)` — Locate .bpmn file by process ID

### 2. MCP Server (SpiffWorkflow Runtime — `get_current_step`)

The `get_current_step` tool **does** use SpiffWorkflow. It provides GPS-style workflow navigation:

```python
# Tell it where you are, it tells you where to go next
result = get_current_step(
    process_id="L2_task_work_cycle",
    completed_steps=["decompose_prompt", "sync_tasks_to_db"],
    data={"has_tasks": True}
)
# Returns: {current_tasks: [{id: "select_next_task", ...}], is_completed: False}
```

**How it works internally:**
1. `BpmnParser.add_bpmn_file()` — loads the BPMN XML
2. `parser.get_spec(process_id)` — creates a workflow specification
3. `BpmnWorkflow(spec)` — instantiates an executable workflow
4. For each completed step: finds the READY task by name, sets data, calls `task.run()`
5. `workflow.do_engine_steps()` — advances gateways and script tasks automatically
6. Returns remaining READY manual tasks

### 3. Tests (SpiffWorkflow Full Execution)

All 490 tests use SpiffWorkflow to execute complete workflow scenarios:

```python
def load_workflow(initial_data: dict) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Seed data into start event
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()  # Run to first manual task or completion
    return wf
```

**Test pattern**: Seed data → `do_engine_steps()` → Assert `is_completed()` and check which task spec names are in COMPLETED state. See [[BPMN Test Patterns]] for the full template.

---

## BPMN Element Types We Use

| BPMN Element | XML Tag | How We Use It |
|-------------|---------|---------------|
| Start Event | `startEvent` | Entry point, seeds workflow data |
| End Event | `endEvent` | Terminal states (often multiple named ends) |
| User Task | `userTask` | Manual Claude actions (decisions, reviews) |
| Script Task | `scriptTask` | Automated hook actions, DB operations |
| Service Task | `serviceTask` | MCP tool calls, external services |
| Call Activity | `callActivity` | Sub-process references (L0→L1→L2 hierarchy) |
| Exclusive Gateway | `exclusiveGateway` | Decision points with conditions |
| Parallel Gateway | `parallelGateway` | Concurrent paths |
| Sequence Flow | `sequenceFlow` | Connections with optional conditions |

**Gateway conditions** use Python expressions in `conditionExpression` elements:
```xml
<bpmn:conditionExpression>is_actionable == True and needs_planning == True</bpmn:conditionExpression>
```

SpiffWorkflow evaluates these against the workflow data dict.

---

## Process Hierarchy (L0/L1/L2)

| Level | Scope | Count | Example |
|-------|-------|-------|---------|
| L0 | Full system | 1 | `L0_claude_family` — swim lanes for all subsystems |
| L1 | Subsystem | 8 | `L1_session_management`, `L1_enforcement`, `L1_work_tracking` |
| L2 | Detailed workflow | 41 | `L2_task_work_cycle`, `session_lifecycle`, `feature_workflow` |

L0 and L1 use `callActivity` to reference child processes. The `get_dependency_tree` MCP tool walks these references.

---

## Artifact Registry & Alignment Checking

Each BPMN task element can be mapped to a real code artifact via `_ARTIFACT_REGISTRY` in server.py:

```python
_ARTIFACT_REGISTRY = {
    "task_element_id": {
        "type": "hook_script",        # or: mcp_tool, claude_behavior, command, agent,
                                      #     hook_output, bpmn_call_activity, rule_file
        "file": "scripts/my_hook.py",
        "hook_event": "PostToolUse",
    },
    ...
}
```

`check_alignment(process_id)` compares BPMN elements against this registry and reports coverage. `file_alignment_gaps(process_id)` auto-files feedback for unmapped elements.

---

## Key Gotchas

1. **SpiffWorkflow imports are lazy** in server.py (inside function bodies). This keeps MCP startup fast for XML-only tools.

2. **Script tasks auto-execute** via `do_engine_steps()`. Only `userTask` elements pause for manual completion. If your process doesn't stop where expected, check that decision points use userTask not scriptTask.

3. **Data is shared** across the workflow in a single dict (`workflow.data`). Script task expressions modify this dict. There's no task-local scope — variable naming matters.

4. **Gateway conditions** must be valid Python expressions. SpiffWorkflow uses `eval()` internally. Use `==`, `!=`, `and`, `or` — not XML-style operators.

5. **CallActivity resolution** requires all referenced BPMN files to be loaded into the same parser. The `_load_workflow` helper handles multi-file loading.

6. **Task spec names** (the `id` attribute in BPMN XML) are the stable identifiers used in `completed_steps`. The `name` attribute is human-readable but not used for matching.

7. **No persistence** — we don't use SpiffWorkflow's serialization. Workflows are stateless: recreated from scratch each time `get_current_step` is called, then replayed from `completed_steps`.

---

## DMN (Available But Unused)

SpiffWorkflow 3.1.2 includes `SpiffWorkflow.dmn.parser.DMNParser` for decision table support. We don't use it today. Potential use cases:

- Classification rules (e.g., `_classify_gap` logic as a DMN table)
- Work item routing rules (feedback type → priority mapping)
- Permission matrices (which tools require which approvals)

DMN would require `.dmn` XML files alongside BPMN files and `parser.add_dmn_file()` calls.

---

## Related Docs

- [[MCP Server Management]] — bpmn-engine server config and deployment
- [[Claude Hooks]] — Hook scripts that BPMN models describe
- `CLAUDE.md` → BPMN Process Modeling section — governance rules
- `.claude/rules/system-change-process.md` — BPMN-first rule for system changes

---

**Version**: 1.0
**Created**: 2026-02-23
**Updated**: 2026-02-23
**Location**: knowledge-vault/20-Domains/SpiffWorkflow Usage Guide.md
