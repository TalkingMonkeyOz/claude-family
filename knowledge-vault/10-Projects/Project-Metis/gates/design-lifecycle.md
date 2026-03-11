---
tags:
  - project/Project-Metis
  - scope/system
  - type/process
created: 2026-02-28
updated: 2026-03-11
---

# METIS Design Lifecycle

This is the master document for the METIS development lifecycle. It defines the gate framework, the iterative methodology for progressing through gates, and tracks where METIS itself stands against each gate.

Every session should check this file to understand the lifecycle structure and current progress.

---

## 1. Gate Framework

Five gates, each a quality checkpoint that must be passed before proceeding. Gates apply universally: to building METIS, maintaining METIS, and to all work done through METIS for clients.

**Key rules:**
- Humans may skip a gate with documented justification
- AI agents cannot skip gates — they need the structure because they lack judgment to know when shortcuts are safe
- Dual-lens: same framework applies to building METIS AND to what METIS enforces for client engagements

### Gate Zero — "Do we understand the problem?" (5 documents)

Must exist before any design, BPMN, DB design, or coding starts.

| # | Document | What it answers |
|---|---|---|
| 1 | Problem Statement (incl. Scope) | "What is the question?" + what is NOT in scope. Scope is a subsection. |
| 2 | Assumptions & Constraints | Real hard limits — NOT technology choices. Tech belongs at Gate 2. |
| 3 | Stakeholders & Decision Rights | Who decides what, escalation paths for agents. |
| 4 | System Map (C4 L1/L2) | Context and Container diagrams. What exists, what connects. |
| 5 | Design Principles / Ethos | Rules before anyone builds. Readable/expandable/maintainable, no eye candy, everything adds value. |

### Gate 1 — "Do we understand the domain?" (5 documents)

Must exist before starting detailed design (BPMN, domain modelling, data modelling).

| # | Document | What it answers |
|---|---|---|
| 1 | Process Inventory | All major workflows/processes — identification, not detail. Wide coverage. |
| 2 | Actor Map | Who/what interacts: human roles, agents, external systems. Different from Stakeholders (who DECIDES vs who USES). |
| 3 | Data Entity Map | Key data objects — inventory, not full model. |
| 4 | Business Rules Inventory | Domain rules governing behaviour: escalation, validation, business logic. |
| 5 | Integration Points (high level) | External systems and patterns: API, OData, MCP. Inbound and outbound. |

### Gate 2 — "Have we designed the solution?" (12 documents)

Must exist before anyone builds databases or writes production code. The design gate — where the bulk of thinking happens.

| # | Document | What it answers |
|---|---|---|
| 1 | Detailed Process Models (BPMN) | Step-by-step process designs for every process from Gate 1 inventory. |
| 2 | C4 Level 3 Component Diagrams | Internal architecture of each container from Gate 0 System Map. |
| 3 | Domain Model (DDD) | Bounded contexts, aggregates, entity relationships. What owns what. |
| 4 | Decision Models (DMN) | Formalises Gate 1 business rules into decision tables. Testable. |
| 5 | Data Model | Actual database/storage design — tables, relationships, indexes. |
| 6 | Tech Stack Decisions | Technology choices formally captured. |
| 7 | API / Interface Design | Interfaces, contracts, data flows. |
| 8 | Security & Access Model | Authentication, role definitions, access control. |
| 9 | Test Strategy | Approach: levels, coverage targets, agent vs human testing. |
| 10 | User/Actor Journey Maps | How each actor type interacts. Each maps to at least one BPMN. |
| 11 | Deployment Architecture | Topology, hosting model, environment structure. |
| 12 | Monitoring, Logging & Observability Design | CORE. Transcripts, logs, error tracking, change impact. |

### Gate 3 — "Are we ready to build?" (8 documents)

Practical readiness before production coding starts.

| # | Document | What it answers |
|---|---|---|
| 1 | Development Standards / Coding Conventions | Naming, file structure, code style, commit format. |
| 2 | Environment Setup / Infrastructure | Dev, staging, production environments, CI/CD. |
| 3 | Build Plan / Sprint Backlog | Prioritised build sequence. |
| 4 | Definition of Done | What "finished" means per deliverable type. |
| 5 | Agent Protocols / Constraints & Skills | How agents operate: context limits, escalation, autonomy, handoff. |
| 6 | Documentation Standards | How system gets documented. Format must be RAG-readable. |
| 7 | Risk Register | Known risks, mitigations. Technical and non-technical. |
| 8 | Project Delivery Framework | Non-technical workstreams: timelines, commercial, human iteration cycles. |

### Gate 4 — "Are we ready to release?" (1 checklist document)

Release Readiness Checklist covering:
- UAT / Acceptance Test Results
- Documentation Updated & Complete (incl. BPMN mapped & stored)
- PVT (Post Verification Testing)
- Client Sign-off / Handover
- Support Readiness
- Training / Onboarding Materials
- Performance / Load Testing Results
- Rollback Plan

---

## 2. Iterative Methodology

Work within and across gates follows a brainstorm → consolidate cycle. This is not a one-shot process — it repeats until the gate deliverables are solid.

### The Pattern

```
Brainstorm 1 (capture ideas at high level)
    → Consolidate & reorg docs
        → Brainstorm 2 (flesh out, go deeper)
            → Consolidate & reorg docs
                → Review & validate with human
                    → Gate deliverable complete
```

### Multi-Session Continuity

Each brainstorm or consolidation cycle may span multiple chat sessions. Continuity is maintained through:

- **Session handoffs** — written at session end, read at session start. Located in `session-handoffs/`
- **Session facts** — key decisions stored incrementally via `store_session_fact()` as they happen (not batched to end)
- **Vault files** — written when a section is complete, not at session end
- **Checkpoints** — saved after completing discrete work units via `save_checkpoint()`

### Design Notation Stack

Seven perspectives used across Gate 2 design work:

1. BPMN — process flows and stage gates
2. DMN — decision logic and rules tables
3. DDD — bounded contexts, aggregates, domain boundaries
4. C4 Model (Mermaid) — system context, containers, components
5. User Journey Maps / Wireflows — actor interactions
6. Event Sourcing — immutable lifecycle history
7. Ontology / Knowledge Graph — completeness and relationships

Value Stream Mapping parked for later consideration.

### Design Coherence Checks

A cross-cutting quality process that runs after consolidation cycles. Five phases: Extract → Map → Check → Report → Resolve. Human judgment required before any resolution — the loop always breaks at Report.

Skill: `skills/design-coherence/SKILL.md`

---

## 3. METIS Progress Tracker

Where METIS itself stands against each gate. Updated per session.

### Gate Zero — COMPLETE ✅

| # | Document | Status | Notes |
|---|---|---|---|
| 1 | Problem Statement (incl. Scope) | ✅ Validated | `gate-zero/problem-statement.md` — 2026-03-07 |
| 2 | Assumptions & Constraints | ✅ Validated | `gate-zero/assumptions-constraints.md` — 2026-03-07 |
| 3 | Stakeholders & Decision Rights | ✅ Validated | `gate-zero/stakeholders-decision-rights.md` — 2026-03-07 |
| 4 | System Map (C4 L1/L2) | ✅ Validated | `gate-zero/system-map.md` — 2026-03-08 |
| 5 | Design Principles / Ethos | ✅ Done | `ethos.md` — prior session |

**Gate Zero check: Can you explain the problem to a new team member in 5 minutes without referencing the solution?** YES — problem statement, constraints, stakeholders, system boundary, and principles are all documented.

**Gate Zero gap addressed:** Security architecture conversation completed 2026-03-08. Constraint 6 (data isolation) now addressed by `security-architecture.md`. Feeds into Gate 2 Doc 8 (Security & Access Model).

### Gate 1 — DRAFT COMPLETE (5/5 documents) ✅

All 5 Gate 1 documents now exist. Consolidated from ~97 source files (2026-03-11). Ready for human review and validation.

| # | Document | Status | Notes |
|---|---|---|---|
| 1 | Process Inventory | ✅ Draft | `gate-one/process-inventory.md` — 2026-03-11. 54 processes across 9 SPD areas + cross-cutting. Deduplicated from 175 raw extractions. |
| 2 | Actor Map | ✅ Validated | `gate-one/actor-map.md` — 2026-03-08. 6 human actors, 3 AI agent categories (project/event-driven/system-level), 4 external systems. |
| 3 | Data Entity Map | ✅ Draft | `gate-one/data-entity-map.md` — 2026-03-11. 45 entities in 7 bounded contexts. Deduplicated from 132 raw extractions. |
| 4 | Business Rules Inventory | ✅ Draft | `gate-one/business-rules-inventory.md` — 2026-03-11. Rules across 7 categories (data governance, security, agent, architecture, process, commercial, quality). |
| 5 | Integration Points | ✅ Draft | `gate-one/integration-points.md` — 2026-03-11. External systems with maturity markers (proven/designed/named). |

**Gate 1 check: Can you list what processes exist, who acts, what data moves, what rules apply, and what connects?** YES — all five inventory documents exist. Needs human review for completeness and accuracy before advancing to Gate 2.

### Gate 2 — MATERIAL INDEXED (formal work not started)

Material index created 2026-03-11: `gate-two/README.md`. 12 deliverables assessed with honest completeness estimates (5%–75%). Substantial informal design exists across brainstorm files, session handoffs, and research papers. Key highlights:
- Security & Access Model: ~75% (12 validated decisions from 2026-03-08)
- Tech Stack Decisions: ~70% (most choices made, ADRs not written)
- Data Model: ~50% (substantial entity design, no DDL)
- API / Interface Design: ~45% (13 REST endpoints specified)
- Detailed Process Models (BPMN): ~15% (no `.bpmn` XML files authored for METIS)
- C4 Level 3 Diagrams: ~5% (L1/L2 complete, L3 not started)

### Gate 3 — MATERIAL INDEXED (formal work not started)

Material index created 2026-03-11: `gate-three/README.md`. 8 deliverables assessed with completeness estimates (5%–70%). Key highlights:
- Development Standards: ~70% (conventions decided, formal doc not written)
- Agent Protocols: ~50% (supervisor pattern decided, formal protocol doc not written)
- Environment Setup: ~45% (4 environments named, IaC not started)
- Documentation Standards: ~40% (RAG-readable approach decided)
- Build Plan: ~30% (phase structure validated, plan-of-attack UNVALIDATED)
- Definition of Done: ~5% (no consolidated DoD document)

### Gate 4 — NOT APPLICABLE YET

---

## 4. Historical Design Phases

The following phases were the original design discovery process before the gate framework was established. They map into the gates as context for what work has been done.

| Phase | Status | Maps to |
|---|---|---|
| First-pass brainstorm (9 areas) | ✅ DONE | Gate 0 + Gate 1 work |
| Feature catalogue (10 features) | ✅ DONE | Gate 1 (Process Inventory input) |
| Gap review | ✅ DONE | Cross-gate quality check |
| Remaining topic sessions | ✅ DONE | Gate 1 deepening |
| Second-pass iteration | ○ NOT STARTED | Cross-gate iterative process |
| Consolidation (first pass) | ✅ DONE | Cross-gate: Gate 1 docs assembled, Gate 2/3 indexed, gaps listed (2026-03-11) |
| Plan of attack | ○ DRAFT (UNVALIDATED) | Gate 3 Doc 3 (Build Plan) |
| Presentable plan | ○ NOT STARTED | Gate 3 Doc 8 (Project Delivery Framework) |
| Detailed design | ○ NOT STARTED | Gate 2 work |
| BPMN validation | ○ NOT STARTED | Gate 2 Doc 1 |
| PID / build handoff | ○ NOT STARTED | Gate 4 |

---

## 5. Key References

- Gate framework skill: `skills/gate-framework/SKILL.md`
- Gate framework handoff: `session-handoffs/2026-03-06-gate-framework-complete.md`
- Gate Zero docs: `gate-zero/` (all 5 complete)
- Gate One docs: `gate-one/` (all 5 draft — process-inventory, actor-map, data-entity-map, business-rules-inventory, integration-points)
- Gate Two material index: `gate-two/README.md` (12 deliverables assessed)
- Gate Three material index: `gate-three/README.md` (8 deliverables assessed)
- Consolidation gaps: `consolidation-gaps.md` (open decisions by gate)
- Feature catalogue: `feature-catalogue.md`
- System product definition: `system-product-definition.md`
- Plan of attack: `plan-of-attack.md` (UNVALIDATED)
- Design coherence skill: `skills/design-coherence/SKILL.md`
- Ethos document: `ethos.md`
- Security architecture: `security-architecture.md` (cross-cutting, addresses Gate 0 Constraint 6)

---
*Created: 2026-02-28 | Updated: 2026-03-11 — Gate 1 DRAFT COMPLETE (5/5 docs). Gate 2/3 material indexed. Consolidation gaps documented.*

---
**Version**: 1.0
**Created**: 2026-02-28
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/design-lifecycle.md
