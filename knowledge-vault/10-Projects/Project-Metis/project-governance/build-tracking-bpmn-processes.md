---
projects:
  - Project-Metis
  - claude-family
tags:
  - bpmn
  - build-tracking
  - process-model
---

# BPMN Processes: P1 Build Planning + P2 Build Execution

Detail flows for [[build-tracking-bpmn]].

---

## P1: Build Planning (Stream → Feature → Task Decomposition)

### Lanes

| Lane | Actor | Role |
|------|-------|------|
| Human | John (domain owner) | Validates decisions, approves specs, sets priorities |
| Architect Claude | Claude with design context | Decomposes work, writes specs, sets dependencies |
| System | MCP tools + DB | Persists, validates, enforces constraints |

### Flow

```
[Start: Design deliverable ready for build]
  │
  ▼
[Architect: Identify/confirm stream]
  │ Tool: create_feature(type='stream') or recall existing
  │ Event: work_event(created)
  ▼
[Architect: Decompose stream into features]
  │ For each: create_feature(parent=stream_id)
  │ Write plan_data: {requirements, rationale, acceptance_criteria}
  │ Write vault spec linked via design_doc_path
  │ Events: work_event(created) + work_event(spec_updated)
  ▼
[Architect: Set feature dependencies]
  │ Tool: add_dependency(predecessor, successor, type)
  ▼
[Architect: Decompose features into build_tasks]
  │ For each: add_build_task(feature_id, name, desc, step_order, verification)
  │ Set files_affected (estimated)
  ▼
[Architect: Set task dependencies]
  │ Tool: add_dependency() for cross-task/cross-feature deps
  ▼
[System: Validate dependency graph]
  │ ✓ No circular dependencies (DAG validation)
  │ ✓ All tasks have verification criteria
  │ ✓ All features have acceptance_criteria
  │ ── FAIL → return to Architect with specific gaps
  ▼
[Human: Review build board]
  │ get_build_board(project) presented
  │ Human validates: structure, priority, scope
  ▼
◆ Approved?
  YES → [System: Set features status='planned'] → [End: Plan ready]
  NO  → [Human: Feedback] → Return to decomposition
```

### Data Objects

| Object | Storage | Access Tool |
|--------|---------|-------------|
| Stream definitions | claude.features (type='stream') | get_build_board() |
| Feature specs | plan_data JSONB + vault file | recall_entities() + vault RAG |
| Task definitions | claude.build_tasks | get_build_board() |
| Dependency graph | claude.task_dependencies | get_build_board() resolves |

---

## P2: Build Execution (Claim → Execute → Complete)

### Lanes

| Lane | Actor | Role |
|------|-------|------|
| Builder Claude | Any Claude instance | Claims, implements, reports |
| System | MCP tools + DB | Enforces WIP, logs events, checks deps |
| Human | John | Unblocks, reviews, validates |

### Main Flow

```
[Start: Session begins]
  ▼
[Builder: get_build_board(project)]
  │ Returns: streams, features, READY tasks (unblocked + unassigned)
  ▼
◆ Ready tasks available?
  NO → ◆ All blocked? → YES → [Message Human: all work blocked] → [End]
                       → NO  → [All assigned — assist or pick other project] → [End]
  YES ↓
  ▼
[Builder: Select task] (consider: priority, stream affinity, context)
  ▼
[Builder: start_work(build_task_id)]
  │ System validates:
  │   ✓ Not already assigned (DB row lock — first wins)
  │   ✓ Predecessors completed (dependency check)
  │   ✓ Stream WIP not exceeded (plan_data.wip_limit)
  │   ✓ Parent feature not cancelled/blocked
  │ Event: work_event(assigned + status_changed → in_progress)
  │ Loads: feature spec, stash, memories
  │ ── FAIL (conflict) → Select different task
  │ ── FAIL (blocked)  → See Blocked subprocess
  ▼
[Builder: Execute implementation]
  │ Uses all 5 storage systems. Checkpoint at milestones.
  │ ── BLOCKER FOUND → Blocked subprocess
  │ ── SESSION ENDING → Partial Completion subprocess
  ▼
[Builder: Verify against criteria]
  │ Check: build_task.verification + feature acceptance_criteria
  ▼
◆ Passed? → NO → [Fix] → loop back
           → YES ↓
  ▼
[Builder: complete_work(task_id, summary)]
  │ Event: work_event(completed)
  │ System: all sibling tasks done? → auto-advance parent feature
  ▼
[End: Task completed]
```

### Subprocess: Blocked Task

```
[Trigger: Blocker discovered]
  ▼
◆ Blocker type?
  ├── TECHNICAL → Create feedback/task for fix → add_dependency → mark blocked
  ├── DECISION  → send_message(human, question) → mark blocked
  └── EXTERNAL  → Create feedback + message relevant project → mark blocked
  ▼
[System: Monitor blocked duration — 3+ sessions → auto-escalate to Human]
  ▼
[Builder picks next available task]
```

### Subprocess: Partial Completion

```
[Trigger: Session ending, task in_progress]
  ▼
[Builder: stash(component, "wip", what_done + what_remains + gotchas)]
  ▼
[Builder: store_session_notes(progress)]
  ▼
[Task stays in_progress — next session's board shows it]
  │ Event: work_event(note_added, "session ending, partial")
```

---
**Version**: 1.0
**Created**: 2026-03-16
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/Project-Metis/project-governance/build-tracking-bpmn-processes.md
