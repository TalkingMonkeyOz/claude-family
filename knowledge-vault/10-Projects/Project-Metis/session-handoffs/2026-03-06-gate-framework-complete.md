---
tags:
  - project/Project-Metis
  - type/session-handoff
  - phase/brainstorm-2
created: 2026-03-06
updated: 2026-03-07
session: gate-framework-complete
status: complete
supersedes: 2026-03-06-gate-framework-continued.md
---

# Session Handoff: Gate Framework Complete

## Session Summary

Completed the full gate framework definition. 5 gates (0-4), 31 deliverables total. Built on top of last session's Gate Zero (5 docs). This session defined Gates 1-4 conversationally with John, one deliverable at a time.

Key principles established:
- Gates are universal quality checks — apply to building METIS, maintaining METIS, and all work done through METIS
- Humans may skip gates with justification; AI agents cannot skip gates
- Dual-lens: same framework for building METIS AND for METIS to enforce on clients
- Chicken-and-egg acknowledged for several items (agent protocols, project delivery framework) — initial versions good enough to start, system refines over time

---

## COMPLETE GATE FRAMEWORK

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
| 1 | Process Inventory | All major workflows/processes — identification, not detail. Wide coverage: KMS, integrations, all functional areas. |
| 2 | Actor Map | Who/what interacts: human roles (PS dev, consultant, PM), agents (QA, knowledge), external systems. Different from Stakeholders (who DECIDES vs who USES). |
| 3 | Data Entity Map | Key data objects — inventory, not full model. Consolidation of existing scattered info. |
| 4 | Business Rules Inventory | Domain rules governing behaviour: escalation, validation, award interpretation. |
| 5 | Integration Points (high level) | External systems and patterns: API, OData, MCP. Inbound and outbound. |

### Gate 2 — "Have we designed the solution?" (12 documents)
Must exist before anyone builds databases or writes production code.

| # | Document | What it answers |
|---|---|---|
| 1 | Detailed Process Models (BPMN) | Step-by-step process designs for every process from Gate 1 inventory. |
| 2 | C4 Level 3 Component Diagrams | Internal architecture of each container from Gate 0 System Map. |
| 3 | Domain Model (DDD) | Bounded contexts, aggregates, entity relationships. What owns what. |
| 4 | Decision Models (DMN) | Formalises Gate 1 business rules into decision tables. Testable. |
| 5 | Data Model | Actual database/storage design — tables, relationships, indexes. |
| 6 | Tech Stack Decisions | Technology choices formally captured. |
| 7 | API / Interface Design | Interfaces, contracts, data flows. Ambitious but right target. |
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
| 5 | Agent Protocols / Constraints & Skills | How agents operate. Chicken-and-egg: initial version, refined over time. |
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

## ALL DECISIONS THIS SESSION

1. Scope is a subsection of Problem Statement — Gate Zero stays at 5 docs
2. Tech choices at Gate 2, not Gate Zero
3. Gate 1 = "Domain Understanding" — 5 documents
4. Integration patterns = API, OData, MCP (inbound and outbound)
5. Gate 2 = "Solution Design" — 12 documents across full notation stack
6. Monitoring/logging is CORE and belongs at Gate 2, not Gate 3
7. Gate 3 = "Build Readiness" — 8 documents
8. Gate 4 = "Release Readiness" — 1 checklist document (not separate docs per item)
9. Gates are universal quality checks across all METIS activities
10. Humans may skip with justification; AI agents cannot skip gates
11. Chicken-and-egg items start with initial versions, refined over time
12. FB174: gate framework skill — create SOONER not later, it's a general skill
13. Sonnet can handle structured doc review/update tasks; Opus for brainstorm/design

---

## WHAT'S NEXT — PRIORITISED

### 1. Create Gate Framework Skill (FB174) — DO SOON
The process of formalising any design through a gate-based approach in Claude AI. General skill, not METIS-specific. Captures the methodology we just used. If we wait, the context of how we did it is lost.

### 2. Review & Update Master Docs (SONNET-SUITABLE)
Compare each doc against the completed gate framework. One at a time with John:
- `design-lifecycle.md` — gate framework should restructure this
- `system-product-definition.md` — absorb Ethos, dual-lens, gate structure
- `feature-catalogue.md` — check if gate framework changes anything
- `plan-of-attack.md` — UNVALIDATED, step through conversationally

### 3. Write Gate Zero Documents for METIS
Start with Problem Statement (incl. scope). One question at a time.
Most critical gap — can't enforce what we haven't done ourselves.

### 4. Flesh Out Actor Map (Gate 1 Doc 2)
Roles need defining — human roles (PS dev, consultant, PM, sales) and agent roles. This was flagged but not yet done.

### 5. Pipelines of Work
Separate concern. Connects to Stakeholders (G0-D3) and Project Governance (Area 6).

### 6. Toolkit Categories 2-4
Resume after above settled.

### Still open
- Validate unvalidated vault output (February violation session)
- Follow up on msg 67d8af18 (vault sync to claude-family)
- Ethos document needs a vault home
- Update Doc 1 with expanded vision, cross-doc coherence review

---

## SESSION STARTERS

### For Opus (brainstorm/design)
```
METIS Session Starter — Post Gate Framework
READ FIRST: `session-handoffs/2026-03-06-gate-framework-complete.md`

CONTEXT: Full gate framework defined (Gates 0-4, 31 deliverables).
FB174 (gate framework skill) should be created soon — general skill
for formalising any design through gates. Actor roles need fleshing out.

WHAT'S NEXT — PICK ONE:
1. Create gate framework skill (FB174) — capture the methodology
2. Flesh out Actor Map — human and agent roles
3. Write Gate Zero docs for METIS — Problem Statement first
4. Pipelines of work

KEY FILES:
* session-handoffs/2026-03-06-gate-framework-complete.md
* design-lifecycle.md, system-product-definition.md, feature-catalogue.md
* plan-of-attack.md — UNVALIDATED
```

### For Sonnet (structured doc review)
```
METIS Session Starter — Doc Review (Sonnet)
READ FIRST: `session-handoffs/2026-03-06-gate-framework-complete.md`

CONTEXT: Full gate framework was defined (Gates 0-4, 31 deliverables).
Master docs need updating to reflect the gate framework.

TASK: Review and update master docs one at a time. For each:
1. Read the current doc
2. Compare against the gate framework in the handoff
3. Present gaps/changes to John for validation
4. Update only after John confirms

ORDER:
1. design-lifecycle.md — gate framework restructures this significantly
2. system-product-definition.md — absorb Ethos + dual-lens + gates
3. feature-catalogue.md — check if gates add/change anything

DO NOT TOUCH: plan-of-attack.md — UNVALIDATED, needs conversational
review with John, not a structured update.

RULES:
- One doc at a time
- Present changes to John before writing
- Anti-monologue: don't dump a complete rewrite, discuss changes
- Store decisions with store_session_fact() as they happen

KEY FILES:
* session-handoffs/2026-03-06-gate-framework-complete.md — full framework
* design-lifecycle.md, system-product-definition.md, feature-catalogue.md
```

---

## KEY FILES
- This handoff: `session-handoffs/2026-03-06-gate-framework-complete.md`
- Prior handoffs: `2026-03-06-gate-zero.md`, `2026-03-02-toolkit-brainstorm.md`
- Feature catalogue: `feature-catalogue.md`
- Design lifecycle: `design-lifecycle.md`
- Plan of attack: `plan-of-attack.md` (UNVALIDATED)
- Ethos document: shared by John (needs vault home)
- FB174: Gate framework skill (idea, priority raised — do soon)

---
*Session: 2026-03-06/07 | Status: Gate framework COMPLETE. Next: create skill, review docs, write Gate Zero docs for METIS.*
