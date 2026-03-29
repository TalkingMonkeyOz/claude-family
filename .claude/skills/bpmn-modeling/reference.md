# BPMN Modeling Skill — Detailed Reference

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
- SpiffWorkflow evaluates ALL conditions (not short-circuit) — missing variables cause crashes
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

## Process Failure Capture

When you encounter a process failure (hook error, state machine violation, unexpected behavior):

1. File feedback: `create_feedback(type='bug', description='...')`
2. Search if the failing system is modeled in BPMN
3. Model the fix in BPMN first, then implement
4. Store the finding as knowledge: `remember(content, "gotcha")`

This creates a self-improving loop: failures drive model improvements.

---

## Current Process Inventory

**Architecture (L0/L1)**: claude_process (L0), session_management, work_tracking, knowledge_management, enforcement, agent_orchestration, config_management
**Lifecycle (L2)**: session_lifecycle, task_lifecycle, feature_workflow, config_deployment, rag_pipeline, feedback_to_feature, agent_lifecycle, session_continuation
**Development**: commit_workflow, system_change_process
**Infrastructure**: hook_chain
**Nimbus**: nimbus_delivery, support_triage, knowledge_ingestion

Use `list_processes` for the live inventory.

---

## Related

- Feature F111: BPMN Process Architecture Framework (L0/L1/L2 hierarchy)
- Feature F112: BPMN Engine MCP - Full Integration
- Feature F113: BPMN Process Coverage + Self-Enforcement
- `mcp-servers/bpmn-engine/` — Server source code
- `mcp-servers/bpmn-engine/processes/` — All BPMN files
- `mcp-servers/bpmn-engine/tests/` — All test files
