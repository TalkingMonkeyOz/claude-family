---
name: planner
description: Generate structured implementation plans for features and refactoring
model: sonnet
agent: planner-sonnet
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task(Explore)
  - mcp__project-tools__create_feature
  - mcp__project-tools__add_build_task
  - mcp__project-tools__get_ready_tasks
---

# Implementation Planner Skill

**Status**: Active
**Last Updated**: 2026-01-24

---

## Overview

Generate deterministic, AI-executable implementation plans. Plans are structured for handoff to coder agents or human developers.

---

## Core Principles

- **No code edits** - Only generate plans, not implementations
- **Deterministic language** - Zero ambiguity
- **Machine-parseable** - Structured for automated execution
- **Self-contained** - No external dependencies for understanding

---

## Claude Family Integration

### Store Plans in Database

```python
# Create feature with plan_data
create_feature(
    project="project-name",
    feature_name="Feature Title",
    description="What this feature does",
    plan_data={
        "requirements": ["REQ-001: ...", "REQ-002: ..."],
        "constraints": ["CON-001: ..."],
        "risks": ["RISK-001: ..."],
        "phases": [
            {"goal": "Phase 1 goal", "tasks": ["TASK-001", "TASK-002"]},
            {"goal": "Phase 2 goal", "tasks": ["TASK-003", "TASK-004"]}
        ]
    }
)

# Add tasks with dependencies
add_build_task(feature_id="F{n}", task_name="TASK-001: Description")
add_build_task(feature_id="F{n}", task_name="TASK-002: Description",
               blocked_by_task_id="BT{prev}")
```

### Plan File Location

Save detailed plans to: `docs/plans/{purpose}-{component}.md`

Purpose prefixes: `feature`, `refactor`, `upgrade`, `infrastructure`

---

## Plan Structure

```markdown
# {Feature Name} - Implementation Plan

## Summary
[1-2 sentence overview]

## Requirements
- REQ-001: [Requirement]
- CON-001: [Constraint]

## Phase 1: {Goal}
| Task | Description | Files | Blocked By |
|------|-------------|-------|------------|
| TASK-001 | ... | `path/to/file.ts` | - |
| TASK-002 | ... | `path/to/file.ts` | TASK-001 |

## Phase 2: {Goal}
...

## Testing
- TEST-001: [What to verify]

## Risks
- RISK-001: [Risk and mitigation]
```

---

## Handoff Pattern

After plan creation:

1. **Store in database** - `create_feature()` + `add_build_task()`
2. **Save plan file** - `docs/plans/{name}.md`
3. **Recommend delegation** - "Spawn `coder-sonnet` for Phase 1"

---

## Related Skills

- `architect` - System design before planning
- `feature-workflow` - Feature lifecycle tracking
- `agentic-orchestration` - Spawning coder agents

---

**Version**: 1.0
**Source**: Transformed from awesome-copilot "Implementation Plan Generation Mode"
