---
name: bpmn-modeling
description: BPMN-first process design using the bpmn-engine MCP server. Use when designing new processes, fixing workflow bugs, or understanding system flows.
---

# BPMN Modeling Skill

**Status**: Active
**Last Updated**: 2026-02-20

---

## When to Use

| Situation | Action |
|-----------|--------|
| Designing a new hook, workflow, or pipeline | Model in BPMN first, test, then implement |
| Fixing a process bug (hook, state machine, lifecycle) | Query existing BPMN model, identify the gap, update model + code |
| Understanding how a system flow works | Search/get process via MCP, trace the path |
| Modifying hook scripts or workflow code | Check BPMN model first - is it modeled? Does the model match reality? |

---

## BPMN-First Design Flow

```
1. QUERY existing processes  (search_processes, list_processes)
2. IDENTIFY if the flow is already modeled
3. DESIGN the BPMN XML (follow conventions below)
4. TEST with SpiffWorkflow (pytest)
5. IMPLEMENT the actual code
6. VERIFY model matches implementation
```

---

## MCP Tools (bpmn-engine server)

| Tool | Purpose |
|------|---------|
| `list_processes` | List all BPMN processes with categories |
| `get_process(process_id)` | Get full process detail (elements, flows, conditions) |
| `get_subprocess(parent_id, subprocess_id)` | Get L2 subprocess detail |
| `validate_process(process_id)` | Validate BPMN structure |
| `get_current_step(process_id, completed, data)` | Simulate execution to find current step |
| `get_dependency_tree(process_id)` | Show L0->L1->L2 call hierarchy |
| `search_processes(query, actor, level)` | Search by keyword, actor tag, or level |

---

## Process Hierarchy

| Level | Purpose | Naming | Location |
|-------|---------|--------|----------|
| L0 | Capability map (top-level orchestration) | `L0_*.bpmn` | `processes/architecture/` |
| L1 | Process flows (one per capability) | `L1_*.bpmn` | `processes/architecture/` |
| L2 | Detailed subprocesses | Descriptive name | `processes/lifecycle/`, `processes/development/`, etc. |

**Connection**: L0 uses `<bpmn:callActivity calledElement="L1_*">` to invoke L1 processes. L1 uses callActivity to invoke L2 subprocesses.

---

## Actor Tags

Use `[ACTOR]` prefix in task names to indicate who/what performs the action:

| Tag | Meaning | BPMN Element |
|-----|---------|--------------|
| `[HOOK]` | Automated hook system | `scriptTask` |
| `[CLAUDE]` | Claude AI instance | `userTask` |
| `[DB]` | Database operation | `scriptTask` |
| `[KM]` | Knowledge system (RAG, vault) | `scriptTask` |
| `[TOOL]` | MCP tool or external service | `scriptTask` |

---

## SpiffWorkflow Conventions

### Gateway Rules (Critical)

```xml
<!-- Default flow: NO conditionExpression, referenced by gateway default= attribute -->
<bpmn:exclusiveGateway id="gw" name="Decision?" default="flow_default">
  <bpmn:incoming>f_in</bpmn:incoming>
  <bpmn:outgoing>flow_conditional</bpmn:outgoing>
  <bpmn:outgoing>flow_default</bpmn:outgoing>
</bpmn:exclusiveGateway>

<!-- Conditional flow: HAS conditionExpression -->
<bpmn:sequenceFlow id="flow_conditional" sourceRef="gw" targetRef="task_a">
  <bpmn:conditionExpression>variable == "value"</bpmn:conditionExpression>
</bpmn:sequenceFlow>

<!-- Default flow: NO conditionExpression -->
<bpmn:sequenceFlow id="flow_default" sourceRef="gw" targetRef="task_b"/>
```

### Data Propagation

- ALL variables used in ANY gateway condition must exist in `task.data` before the gateway evaluates
- SpiffWorkflow evaluates ALL conditions (not short-circuit) - missing variables cause crashes
- Script task data stays in task scope; use `completed_names` to verify path taken, not `wf.data`

### Test Pattern

```python
from tests.conftest import load_workflow, complete_user_task, completed_names

def test_happy_path(self):
    wf = load_workflow("my_process")
    complete_user_task(wf, "first_task", {"decision": "approve"})
    # Script tasks auto-execute via do_engine_steps()
    names = completed_names(wf)
    assert "expected_task" in names
    assert wf.is_completed()
```

---

## BPMN XML Template

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions
    xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
    targetNamespace="http://claude-family/bpmn/CATEGORY-PROCESS_NAME"
    id="Definitions_PROCESS_NAME">

  <bpmn:process id="process_name" name="Human Readable Name" isExecutable="true">

    <bpmn:startEvent id="start" name="Trigger">
      <bpmn:outgoing>f1</bpmn:outgoing>
    </bpmn:startEvent>

    <!-- [CLAUDE] tasks = userTask, [HOOK/DB/KM/TOOL] = scriptTask -->
    <bpmn:userTask id="do_thing" name="[CLAUDE] Do The Thing">
      <bpmn:incoming>f1</bpmn:incoming>
      <bpmn:outgoing>f2</bpmn:outgoing>
    </bpmn:userTask>

    <bpmn:endEvent id="end" name="Done">
      <bpmn:incoming>f2</bpmn:incoming>
    </bpmn:endEvent>

    <bpmn:sequenceFlow id="f1" sourceRef="start" targetRef="do_thing"/>
    <bpmn:sequenceFlow id="f2" sourceRef="do_thing" targetRef="end"/>
  </bpmn:process>
</bpmn:definitions>
```

---

## Current Process Inventory

**Architecture (L0/L1)**: claude_process (L0), session_management, work_tracking, knowledge_management, enforcement, agent_orchestration, config_management
**Lifecycle (L2)**: session_lifecycle, task_lifecycle, feature_workflow, config_deployment, rag_pipeline
**Development**: commit_workflow
**Infrastructure**: hook_chain
**Nimbus**: nimbus_delivery, support_triage, knowledge_ingestion

Use `list_processes` for the live inventory.

---

## Related

- Feature F111: BPMN Process Architecture Framework (L0/L1/L2 hierarchy)
- Feature F112: BPMN Engine MCP - Full Integration
- `mcp-servers/bpmn-engine/` - Server source code
- `mcp-servers/bpmn-engine/processes/` - All BPMN files
- `mcp-servers/bpmn-engine/tests/` - All test files

---

**Version**: 1.0
