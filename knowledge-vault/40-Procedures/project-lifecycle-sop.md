---
projects:
- claude-family
tags:
- project-lifecycle
- phases
- gates
- sop
---

# Project Lifecycle SOP

## Purpose

Defines the unified 7-stage project phase model used across all Claude Family projects. This replaces the previous conflicting models (5-phase in project-ops, 6-phase in phase-advance/column_registry).

## The 7-Stage Model

```
idea -> planning -> design -> implementation -> testing -> production -> archived
```

Every project in `claude.projects` has a `phase` column. New projects start at `idea`. The phase tracks where a project is in its lifecycle.

## Stage Definitions

### 1. Idea

**Question**: Is this worth exploring?

| Aspect | Detail |
|--------|--------|
| Focus | Problem identification, initial scoping |
| Entry | Project need identified |
| Exit to Planning | Problem statement exists, stakeholder identified, project registered |
| Deliverables | Rough problem description |

### 2. Planning

**Question**: Do we understand the problem well enough to design a solution?

| Aspect | Detail |
|--------|--------|
| Focus | Requirements gathering, feasibility, constraints |
| Entry | From idea (problem worth pursuing) |
| Exit to Design | PROBLEM_STATEMENT.md complete, success criteria defined, constraints documented, at least one feature created |
| Deliverables | PROBLEM_STATEMENT.md, success criteria, constraint list |
| Gate overlay | Gate 0 (understand problem), Gate 1 (understand domain) |

### 3. Design

**Question**: Have we designed a solution that addresses the problem?

| Aspect | Detail |
|--------|--------|
| Focus | Architecture, API design, technical decisions |
| Entry | From planning (problem well understood) |
| Exit to Implementation | CLAUDE.md current, ARCHITECTURE.md exists, features have build tasks |
| Deliverables | ARCHITECTURE.md, ADRs, wireframes/mockups |
| Gate overlay | Gate 2 (solution designed) |

### 4. Implementation

**Question**: Is the core functionality built and working?

| Aspect | Detail |
|--------|--------|
| Focus | Writing code, building features, creating tests |
| Entry | From design (architecture defined) |
| Exit to Testing | Core functionality complete, unit tests exist and pass, no critical bugs |
| Deliverables | Working features, test coverage, code reviews |
| Gate overlay | Gate 3 (ready to build — all built) |

### 5. Testing

**Question**: Is it ready for production use?

| Aspect | Detail |
|--------|--------|
| Focus | QA, integration testing, performance, user acceptance |
| Entry | From implementation (core features done) |
| Exit to Production | All tests passing, docs updated, critical features complete, user approved |
| Deliverables | Test reports, bug fixes, performance benchmarks |
| Gate overlay | Gate 4 (ready to release) |

### 6. Production

**Question**: Is it serving its purpose well?

| Aspect | Detail |
|--------|--------|
| Focus | Live operation, monitoring, maintenance, incremental improvement |
| Entry | From testing (approved for production) |
| Exit to Archived | User decides to retire, final docs updated |
| Deliverables | Live system, monitoring, operational documentation |
| Gate overlay | None (operational, not developmental) |

### 7. Archived

**Question**: Is the project properly closed out?

| Aspect | Detail |
|--------|--------|
| Focus | Retirement, knowledge preservation |
| Entry | From any phase (user decision) |
| Exit | Terminal state |
| Deliverables | Final documentation, archive reason, lessons learned |

## Gate Overlay (Optional)

Gates are quality checkpoints from the Metis design framework. They are **orthogonal to phases** — a project can be in production while addressing Gate 2 gaps. Not all projects use gates.

| Gate | Question | Phase Context |
|------|----------|---------------|
| Gate 0 | Do we understand the problem? | Planning |
| Gate 1 | Do we understand the domain? | Planning |
| Gate 2 | Have we designed the solution? | Design |
| Gate 3 | Are we ready to build? | Implementation |
| Gate 4 | Are we ready to release? | Testing |

## How to Advance Phases

Use the `/phase-advance` skill or manual SQL:

```sql
-- Check current phase
SELECT project_name, phase FROM claude.projects WHERE project_name = 'my-project';

-- Advance (after verifying requirements)
UPDATE claude.projects SET phase = 'design', updated_at = NOW()
WHERE project_name = 'my-project';
```

**Enforcement**: Option C (Hybrid) — `claude.column_registry` validates values, skill documents transitions. No WorkflowEngine enforcement (phases change too rarely to warrant it).

## Valid Transitions

| From | Valid Targets | Notes |
|------|-------------|-------|
| idea | planning | Normal progression |
| planning | design | Requirements complete |
| design | implementation | Architecture defined |
| implementation | testing | Core features built |
| testing | production | All tests passing |
| testing | implementation | Bugs found, need fixes |
| production | archived | Project retired |
| any | archived | Early termination |

**Skip-back**: Only `testing -> implementation` is a standard backward transition. Other skip-backs should be rare and documented with rationale.

## BPMN Model

The project lifecycle is modeled in BPMN at:
- `lifecycle/project_lifecycle.bpmn` — main process (init, work, phase advance, retire)
- `phase_advancement` — subprocess (requirements checks per phase)

## Migration History

| Date | Change |
|------|--------|
| 2026-03-22 | Unified to 7-stage model (F157). Replaced 3 conflicting models. |
| Prior | DB had 6 phases (idea, research, planning, implementation, maintenance, archived) |
| Prior | project-ops had 5 phases (planning, design, implementation, testing, production) |
| Prior | phase-advance matched DB's 6 phases |

**Deprecated phases**: `research` (merged into planning), `maintenance` (merged into production)

---

**Version**: 1.0
**Created**: 2026-03-22
**Updated**: 2026-03-22
**Location**: knowledge-vault/40-Procedures/project-lifecycle-sop.md
