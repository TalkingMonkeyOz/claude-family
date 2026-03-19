---
projects:
  - Project-Metis
  - claude-family
tags:
  - bpmn
  - build-tracking
  - governance
  - process-model
---

# BPMN Process Models: Build Tracking System — Overview

Three process models covering the full build tracking lifecycle. Fits under existing `L1_work_tracking` as `L2_build_tracking`.

## Hierarchy Position

```
L1_work_tracking
  └── L2_build_tracking
        ├── P1: Build Planning        → [Detail](build-tracking-bpmn-processes.md)
        ├── P2: Build Execution        → [Detail](build-tracking-bpmn-processes.md)
        └── P3: Build Compliance       → [Detail](build-tracking-bpmn-compliance.md)
```

## Process Summary

| Process | Lanes | Purpose |
|---------|-------|---------|
| P1: Build Planning | Human, Architect Claude, System | Decompose design → streams → features → tasks with dependencies |
| P2: Build Execution | Builder Claude, System, Human | Claim → execute → verify → complete cycle |
| P3: Build Compliance | System, Builder Claude | Awareness, interface-only access, enforcement |

## Gap Analysis Summary

| # | Gap | Resolution |
|---|-----|-----------|
| G1 | Two Claudes claim same task | `start_work()` DB row lock — first wins |
| G2 | Claude crashes mid-task | Session-end hook detects, logs event. Task claimable after timeout |
| G3 | Blocked 3+ sessions | Auto-escalate to human via message |
| G4 | Cross-stream dependency | task_dependencies supports cross-type links |
| G5 | Plan changes mid-build | plan_updated event, affected tasks flagged |
| G6 | Partial completion | stash() notes + task stays in_progress |
| G7 | Completed task found wrong | New corrective task, forward-only (no reversal) |
| G8 | WIP limit exceeded | start_work() checks plan_data.wip_limit |
| G9 | No direct SQL | Hook blocks raw SQL on tracking tables |
| G10 | Feature cancelled | Cascade: child features/tasks cancelled, events logged |

## Implementation Scope (For Claude Family)

| Phase | What |
|-------|------|
| Phase 1: Schema | Add 'stream' type, create work_events + task_dependencies tables |
| Phase 2: MCP Tools | get_build_board(), get_build_history(), add_dependency(), modify start/complete_work() |
| Phase 3: Enforcement | Rules file, pre-edit hook, startup board injection, CLAUDE.md docs |

## Related Documents

- [[build-tracking-design]] — Full design rationale, table schemas, research
- [[build-tracking-bpmn-processes]] — P1 + P2 detailed process flows
- [[build-tracking-bpmn-compliance]] — P3 compliance: awareness, usage, recall, enforcement

---
**Version**: 1.0
**Created**: 2026-03-16
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/Project-Metis/project-governance/build-tracking-bpmn.md
