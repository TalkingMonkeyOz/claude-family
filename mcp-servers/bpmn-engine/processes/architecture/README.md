# BPMN Process Architecture

Multi-level process decomposition for the Claude Family system.

## Hierarchy

```
L0: Capability Map (L0_claude_family.bpmn)
 |
 +-- L1: Session Management    (L1_session_management.bpmn)
 +-- L1: Work Tracking         (L1_work_tracking.bpmn)
 |    |
 |    +-- L2: Task Lifecycle   (lifecycle/task_lifecycle.bpmn)  [callActivity]
 |
 +-- L1: Knowledge Management  (L1_knowledge_management.bpmn)
 +-- L1: Enforcement           (L1_enforcement.bpmn)
 +-- L1: Agent Orchestration   (L1_agent_orchestration.bpmn)
 +-- L1: Config Management     (L1_config_management.bpmn)
```

## Levels

| Level | Purpose | Connection | File Pattern |
|-------|---------|------------|--------------|
| L0 | Capability map: 6 actor pools, message flows, call activities | Collaboration diagram | `L0_*.bpmn` |
| L1 | Process flows with actor attribution and gateway logic | Called by L0 via `callActivity` | `L1_*.bpmn` |
| L2 | Detailed subprocesses for specific operations | Called by L1 via `callActivity` | `lifecycle/*.bpmn` |

## L1 -> L2 Connections

| L1 Process | L1 Element | L2 Process | Connection Type |
|------------|-----------|------------|-----------------|
| L1_work_tracking | `execute_task_lifecycle` | `task_lifecycle` | callActivity (formal) |
| L1_session_management | (entire process) | `session_lifecycle` | Supersedes (L1 is more detailed) |
| L1_enforcement | (entire process) | `hook_chain` | Supersedes (L1 is more detailed) |

## Actor Conventions

L1 processes use `[ACTOR]` prefix in task names to show responsibility:

| Actor | Meaning | Examples |
|-------|---------|----------|
| `[CLAUDE]` | Claude AI decision/action | Identify work, plan feature, assess complexity |
| `[DB/WF]` | Database/WorkflowEngine | Create feature, advance status, complete |
| `[HOOK]` | Hook system (automated) | Task discipline, context injection, sync |
| `[KM]` | Knowledge system | Embedding, RAG search |
| `[ORCH]` | Orchestrator MCP | Agent spawning |
| `[FS]` | Filesystem deployment | Generate settings, deploy components |
| `[L2]` | Delegates to L2 subprocess | Execute task lifecycle |

## SpiffWorkflow Gotchas

1. **`get_subprocess_specs()`**: Must call `parser.get_subprocess_specs(process_id)` and pass result to `BpmnWorkflow(spec, subspecs)` for callActivities to resolve.

2. **Gateway condition evaluation**: ALL conditions on a gateway are evaluated (not short-circuit). Variables in ANY branch must exist in `task.data`, even for default branches.

3. **`wf.data` timing**: Empty during execution. Script task data only populates `wf.data` after the workflow completes.

4. **Non-executable processes**: `isExecutable="false"` processes raise `ValidationException` on `get_spec()`.

## Running Tests

```bash
cd mcp-servers/bpmn-engine
python -m pytest tests/test_L0_claude_family.py -v   # L0 tests (6)
python -m pytest tests/test_L1_processes.py -v        # L1 + integration (21)
python -m pytest tests/ -v                            # Full suite (53)
```

## Test Coverage

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `test_L0_claude_family.py` | 6 | L0 subprocess resolution, full sequence, partial execution |
| `test_L1_processes.py` | 21 | All 6 L1s (happy/alt/loop paths), L0->L1->L2 integration |
| `test_task_lifecycle.py` | 3 | L2 task lifecycle (happy, blocked, gate blocked) |
| `test_session_lifecycle.py` | 4 | L2 session lifecycle (fresh, resume, compact, continue) |
| `test_hook_chain.py` | 3 | L2 hook chain (text, allowed, blocked) |
| `test_feature_workflow.py` | 4 | L2 feature workflow (happy, complex, retry, review) |
| Others | 12 | Domain processes (nimbus, knowledge, support) |
