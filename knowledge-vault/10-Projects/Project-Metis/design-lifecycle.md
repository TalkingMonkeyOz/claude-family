---
tags:
  - project/Project-Metis
  - scope/system
  - type/process
created: 2026-02-28
updated: 2026-03-07
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

### Gate Zero — PARTIALLY DONE

| # | Document | Status | Notes |
|---|---|---|---|
| 1 | Problem Statement (incl. Scope) | ◐ Scattered | Discussed across many sessions, never consolidated into one doc. |
| 2 | Assumptions & Constraints | ◐ Implicit | In conversations, not written as standalone doc. |
| 3 | Stakeholders & Decision Rights | ○ Not written | "John decides everything" is not a document. |
| 4 | System Map (C4 L1/L2) | ◐ Partial | 9 areas exist as a list, no actual C4 diagram drawn. |
| 5 | Design Principles / Ethos | ◐ Started | Ethos content shared by John, not formalised in vault. |

### Gate 1 — PARTIALLY DONE (scattered)

| # | Document | Status | Notes |
|---|---|---|---|
| 1 | Process Inventory | ◐ Scattered | 9 areas brainstormed, processes implicit, no formal inventory. |
| 2 | Actor Map | ○ Not written | Actors mentioned across sessions but never mapped. |
| 3 | Data Entity Map | ◐ Scattered | Entities exist across brainstorm sessions, not consolidated. |
| 4 | Business Rules Inventory | ◐ Scattered | Rules discussed but not inventoried. |
| 5 | Integration Points | ◐ Partial | API, OData, MCP patterns decided. Specifics not mapped. |

### Gate 2 — NOT STARTED (some informal work exists)

Some work exists informally:
- Working PostgreSQL schema (58 tables, 762 columns) — but evolved, not designed
- Tech stack decisions made informally (PostgreSQL, Voyage AI, custom RAG) — not captured as formal doc
- Some BPMN processes exist in Claude Family (62 models) — not validated against METIS design
- SpiffWorkflow chosen over Camunda — decision made but not in a tech stack doc

### Gate 3 — NOT STARTED

Some coding conventions exist informally. Agent protocols partially defined through project-tools MCP usage patterns.

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
| Consolidation (first pass) | ◐ DONE | Cross-gate iterative process |
| Plan of attack | ○ DRAFT (UNVALIDATED) | Gate 3 Doc 3 (Build Plan) |
| Presentable plan | ○ NOT STARTED | Gate 3 Doc 8 (Project Delivery Framework) |
| Detailed design | ○ NOT STARTED | Gate 2 work |
| BPMN validation | ○ NOT STARTED | Gate 2 Doc 1 |
| PID / build handoff | ○ NOT STARTED | Gate 4 |

---

## 5. Key References

- Gate framework handoff: `session-handoffs/2026-03-06-gate-framework-complete.md`
- Feature catalogue: `feature-catalogue.md`
- System product definition: `system-product-definition.md`
- Plan of attack: `plan-of-attack.md` (UNVALIDATED)
- Design coherence skill: `skills/design-coherence/SKILL.md`
- Ethos document: shared by John (needs vault home)

---
*Created: 2026-02-28 | Updated: 2026-03-07 — Restructured around gate framework*
