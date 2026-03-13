---
tags:
  - project/Project-Metis
  - type/session-handoff
  - phase/brainstorm-2
created: 2026-03-06
session: gate-framework-continued
status: in-progress
supersedes: 2026-03-06-gate-zero.md
---

# Session Handoff: Gate Framework (Continued)

## Session Summary

Continuing from the Gate Zero session. This session is working through the full gate framework — defining what deliverables must exist at each gate before proceeding to the next phase. Gate Zero was locked last session (5 docs). This session is defining Gates 1, 2, and 3.

Plan for session: finish gate framework top-down, then circle back to rebuild/verify existing master docs against the completed framework.

---

## COMPLETE GATE FRAMEWORK (as decided)

### Gate Zero — "Do we understand the problem?"
Must exist before any design, BPMN, DB design, or coding starts.

| # | Document | What it answers |
|---|---|---|
| 1 | Problem Statement (incl. Scope) | "What is the question?" + what is NOT in scope. Scope is a subsection, not a separate doc. |
| 2 | Assumptions & Constraints | Real hard limits — NOT technology choices. Tech stack belongs at a later gate. |
| 3 | Stakeholders & Decision Rights | Who decides what, escalation paths for agents. |
| 4 | System Map | C4 Level 1 (Context) + Level 2 (Containers). |
| 5 | Design Principles / Ethos | Rules before anyone builds. Readable/expandable/maintainable, no eye candy, everything adds value. |

### Gate 1 — "Do we understand the domain?"
Must exist before starting detailed design (BPMN, domain modelling, data modelling).

| # | Document | What it answers |
|---|---|---|
| 1 | Process Inventory | What are all the major workflows/processes? Not detailed BPMN, just identification. Wide — covers KMS, integrations, all functional areas. |
| 2 | Actor Map | Who/what interacts with the system? Human roles (PS dev, consultant, PM), agents (QA agent, knowledge agent), external systems. Different from Gate Zero Stakeholders (who DECIDES vs who USES). |
| 3 | Data Entity Map | What are the key data objects? Not a full data model, just inventory. Much already exists scattered — this is consolidation work. |
| 4 | Business Rules Inventory | Domain rules that govern behaviour. Escalation rules, validation rules, award interpretation. Shapes process design, data validation, agent behaviour. |
| 5 | Integration Points (high level) | What external systems connect and through what patterns? Three main patterns: API, OData, MCP. Covers inbound and outbound. Specific endpoint detail is later gate work. |

### Gate 2 — "Have we designed the solution?"
**IN PROGRESS — defining deliverables this session**

Confirmed so far:
| # | Document | What it answers |
|---|---|---|
| 1 | Detailed Process Models (BPMN) | Step-by-step process designs for every process from Gate 1 inventory. |
| 2 | C4 Level 3 Component Diagrams | Internal architecture of each container. Goes deeper than Gate Zero System Map. |
| 3 | Domain Model (DDD) | TBD — was about to discuss when session paused for handoff update. |

Still to discuss: remaining Gate 2 docs, Gate 3 definition.

---

## DECISIONS MADE THIS SESSION (new)

1. **Scope is a subsection of Problem Statement** — not a separate Gate Zero document. Gate Zero remains 5 docs.
2. **Tech choices belong at a later gate** — confirmed again, not at Gate Zero.
3. **Gate 1 = "Domain Understanding"** — 5 documents as listed above.
4. **Integration patterns = API, OData, MCP** — covers both inbound and outbound.
5. **Gate 2 framing = "Solution Design"** — before anyone builds databases or writes code. Detailed design artifacts across the notation stack (BPMN, C4, DDD, DMN, etc).

---

## DECISIONS FROM PRIOR SESSION (carried forward)

- Gate Zero framework — 5 documents (locked)
- Dual-lens principle — same framework for building METIS AND for METIS to enforce on clients
- Hybrid methodology — SDLC discipline at planning/architecture, Agile at execution, stage-gates between
- Honest gap — all Gate Zero docs incomplete for METIS itself

---

## WHAT'S NEXT (when session resumes)

1. **Finish Gate 2 deliverables** — Domain Model (DDD) was next, plus DMN, tech stack decisions, data model, test strategy?
2. **Define Gate 3** — "Ready to build?" Before coding starts.
3. **Circle back** — rebuild/verify master docs against completed gate framework
4. **Write Gate Zero docs for METIS** — Problem Statement first
5. **Capture gate framework as a METIS skill/process** — John requested this be formalised

---

## SKILL/PROCESS CAPTURE REQUEST

John asked for the gate framework design process to be captured as a skill or process workflow. This means:
- The process of defining gates, their deliverables, and validation criteria
- Should be reusable — both for METIS internal use and for client engagements
- Not yet written — flagged for creation once the full framework is finalised

---

## KEY FILES
- Previous handoff: `session-handoffs/2026-03-06-gate-zero.md`
- Toolkit brainstorm: `session-handoffs/2026-03-02-toolkit-brainstorm.md`
- Feature catalogue: `feature-catalogue.md`
- Design lifecycle: `design-lifecycle.md`
- Plan of attack: `plan-of-attack.md` (UNVALIDATED — do not bulk update)
- Ethos document: shared by John (needs vault home)

---
*Session: 2026-03-06 (continued) | Status: Gate framework in progress — Gate 0 locked, Gate 1 locked, Gate 2 partially defined*
