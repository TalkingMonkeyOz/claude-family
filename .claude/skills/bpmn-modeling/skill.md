---
name: bpmn-modeling
description: BPMN-first process design using the bpmn-engine MCP server. Use when designing new processes, fixing workflow bugs, or understanding system flows.
---

# BPMN Modeling Skill

**Status**: Active
**Last Updated**: 2026-04-11

---

## When to Use

| Situation | Action |
|-----------|--------|
| Designing a new hook, workflow, or pipeline | Model in BPMN first, test, then implement |
| Fixing a process bug (hook, state machine, lifecycle) | Query existing BPMN model, identify the gap, update model + code |
| Understanding how a system flow works | Search/get process via MCP, trace the path |
| Modifying hook scripts or workflow code | Check BPMN model first - is it modeled? Does the model match reality? |

---

## BPMN-First Design Flow (MANDATORY)

```
1. IDENTIFY ACTORS    — Who/what participates? (User, Claude, Hooks, Jobs, External Systems)
2. QUERY EXISTING     — search_processes, list_processes — is it already modeled?
3. GAP ANALYSIS       — Run the Gap Analysis Checklist (see below)
4. DESIGN the BPMN    — Follow conventions, include non-happy paths
5. TEST with pytest   — All paths, including error/edge cases
6. IMPLEMENT code     — Only after model + tests are green
7. VERIFY ALIGNMENT   — check_alignment(process_id) — does model match code?
8. SYNC REGISTRY      — sync_bpmn_processes(project) after creating/modifying .bpmn files
```

---

## Gap Analysis Checklist (CRITICAL)

Run this checklist for EVERY new or updated BPMN model. The value of BPMN is gap identification, not just documentation.

### 1. CRUD Completeness
For every data entity the process touches, verify all operations exist:
- [ ] **Create** — Can the entity be created?
- [ ] **Read** — Can it be queried/retrieved?
- [ ] **Update** — Can it be modified after creation?
- [ ] **Delete** — Can it be removed (soft or hard)?
If any operation is missing, document WHY (intentional omission vs gap).

### 2. Actor Coverage
- [ ] List ALL actors who interact with the system (not just the primary one)
- [ ] Include the **User** as an actor when they trigger or participate in flows
- [ ] Include **background jobs** and **hooks** as separate actors
- [ ] For each actor, verify they have entry points (start events or message catches)
- [ ] Check: can each actor initiate the operations they need?

### 3. Handoff Identification
For every transition between actors (e.g., Claude -> Hook, Hook -> Background Job):
- [ ] Is the handoff explicit in the model? (message flow, signal, or documented)
- [ ] What data passes across the boundary?
- [ ] What happens if the receiving actor is unavailable?
- [ ] Is there a guaranteed pickup mechanism, or is it best-effort?
- [ ] Document any timing gaps (e.g., "up to 1 hour until background job runs")

### 4. Non-Happy-Path Coverage
- [ ] What happens on failure at each step?
- [ ] What happens with invalid/malformed input?
- [ ] What happens when a dependency is unavailable?
- [ ] Are there timeout or retry mechanisms?
- [ ] Edge cases: concurrent access, cross-session conflicts, empty datasets

### 5. Alignment Verification
- [ ] Run `check_alignment(process_id)` after creating the model
- [ ] For each unmapped element, determine: tooling gap or real gap?
- [ ] For each missing artifact, determine: not yet built or wrong deployment target?
- [ ] Verify deployment target: does this model describe the RIGHT system?

### 6. User Story Cross-Reference
- [ ] Who are the users of this process? (Developer, Admin, Claude, Background System)
- [ ] For each user, can they accomplish their goal through the modeled paths?
- [ ] Reference: "Fifty Quick Ideas to Improve Your User Stories" (Gojko Adzic) for story splitting and validation techniques

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
| `check_alignment(process_id)` | Compare BPMN model against actual code artifacts |
| `file_alignment_gaps(process_id)` | Auto-file feedback for alignment gaps |

---

## Process Hierarchy

| Level | Purpose | Naming | Location |
|-------|---------|--------|----------|
| L0 | Capability map (top-level orchestration) | `L0_*.bpmn` | `processes/architecture/` |
| L1 | Process flows (one per capability) | `L1_*.bpmn` | `processes/architecture/` |
| L2 | Detailed subprocesses | Descriptive name | `processes/lifecycle/`, `processes/development/`, etc. |

**Connection**: L0 uses `<bpmn:callActivity calledElement="L1_*">` to invoke L1 processes.

---

## Actor Tags

Use `[ACTOR]` prefix in task names to indicate who/what performs the action:

| Tag | Meaning | BPMN Element |
|-----|---------|--------------|
| `[USER]` | Human user triggering or participating | `userTask` |
| `[CLAUDE]` | Claude AI instance | `userTask` |
| `[HOOK]` | Automated hook system | `scriptTask` |
| `[JOB]` | Background scheduled job | `scriptTask` |
| `[DB]` | Database operation | `scriptTask` |
| `[KMS]` | Knowledge management system | `scriptTask` |
| `[AUTOMEMORY]` | Claude Code built-in MEMORY.md | `scriptTask` |
| `[LLM:Model]` | LLM API call (e.g., `[LLM:Haiku]`) | `scriptTask` |

---

## Deployment Target (MANDATORY)

Every BPMN model must declare its deployment target in the XML header comment:
```xml
<!-- Deployment: claude-family (Windows local) -->
<!-- Deployment: metis (Linux server) -->
<!-- Deployment: all (cross-platform) -->
```
This prevents AI bleed where models for one system contaminate another (FB264).

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
- Use Python syntax in conditions (`True` not `true`, `==` not `===`)

### Script Tasks Need Bodies

```xml
<bpmn:scriptTask id="task" name="[HOOK] Do Thing" scriptFormat="python">
  <bpmn:incoming>f_in</bpmn:incoming>
  <bpmn:outgoing>f_out</bpmn:outgoing>
  <bpmn:script>
result = do_thing()
  </bpmn:script>
  <bpmn:documentation>Detailed explanation of what this task does.</bpmn:documentation>
</bpmn:scriptTask>
```

---

## Process Failure Capture

When you encounter a process failure (hook error, state machine violation, unexpected behavior):

1. File feedback: `create_feedback(type='bug', description='...')`
2. Search if the failing system is modeled in BPMN
3. Model the fix in BPMN first, then implement
4. Store the finding as knowledge: `remember(content, "gotcha")`

---

## Related

- Feature F111: BPMN Process Architecture Framework
- Knowledge: `recall_memories("BPMN gap analysis")` for past findings
- Book: "Fifty Quick Ideas to Improve Your User Stories" (Gojko Adzic) for actor/story validation
- `mcp-servers/bpmn-engine/` - Server source code
- `mcp-servers/bpmn-engine/processes/` - All BPMN files
- `mcp-servers/bpmn-engine/tests/` - All test files

---

**Version**: 2.0