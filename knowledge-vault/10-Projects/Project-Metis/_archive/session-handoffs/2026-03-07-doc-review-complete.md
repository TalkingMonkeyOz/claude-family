---
tags:
  - project/Project-Metis
  - type/session-handoff
  - phase/brainstorm-2
created: 2026-03-07
session: doc-review-and-gate-framework
status: complete
supersedes: 2026-03-06-gate-framework-complete.md
---

# Session Handoff: Gate Framework Complete + Doc Review Done

## Session Summary

Two-part session:
1. **Gate framework definition** (Opus) — completed full gate framework: 5 gates (0-4), 31 deliverables
2. **Doc review** (continued) — updated 3 master docs against gate framework, gave Ethos a vault home

All master docs now reference the gate framework. plan-of-attack.md deliberately not touched (UNVALIDATED).

---

## COMPLETE GATE FRAMEWORK

### Gate Zero — "Do we understand the problem?" (5 documents)
1. Problem Statement (incl. Scope)
2. Assumptions & Constraints (not tech choices)
3. Stakeholders & Decision Rights
4. System Map (C4 L1/L2)
5. Design Principles / Ethos

### Gate 1 — "Do we understand the domain?" (5 documents)
1. Process Inventory
2. Actor Map (who USES, not who DECIDES)
3. Data Entity Map
4. Business Rules Inventory
5. Integration Points (API, OData, MCP — inbound and outbound)

### Gate 2 — "Have we designed the solution?" (12 documents)
1. Detailed Process Models (BPMN)
2. C4 Level 3 Component Diagrams
3. Domain Model (DDD)
4. Decision Models (DMN)
5. Data Model
6. Tech Stack Decisions
7. API / Interface Design
8. Security & Access Model
9. Test Strategy
10. User/Actor Journey Maps
11. Deployment Architecture
12. Monitoring, Logging & Observability Design (CORE)

### Gate 3 — "Are we ready to build?" (8 documents)
1. Development Standards / Coding Conventions
2. Environment Setup / Infrastructure
3. Build Plan / Sprint Backlog
4. Definition of Done
5. Agent Protocols / Constraints & Skills
6. Documentation Standards (RAG-readable)
7. Risk Register
8. Project Delivery Framework

### Gate 4 — "Are we ready to release?" (1 checklist)
Release Readiness Checklist: UAT, docs updated (incl BPMN), PVT, sign-off, support readiness, training, performance testing, rollback plan.

---

## KEY PRINCIPLES

- Gates are universal quality checks — building METIS, maintaining METIS, all client work
- Humans may skip with justification; AI agents cannot skip gates
- Dual-lens: same framework for building METIS AND for METIS to enforce on clients
- Second-pass and consolidation are cross-gate iterative processes (brainstorm → consolidate → brainstorm deeper → consolidate), not deliverables within a specific gate
- Chicken-and-egg items (agent protocols, project delivery framework) start with initial versions, refined over time

---

## DOCS UPDATED THIS SESSION

| Doc | Change | Status |
|-----|--------|--------|
| `design-lifecycle.md` | Restructured around gate framework. 5 sections: gates, methodology, progress tracker, historical phases, references. | ✅ DONE |
| `system-product-definition.md` | Validation stack updated to 7 perspectives. New Section 10: Ethos/Design Principles. Dual-lens + gate framework referenced. | ✅ DONE |
| `feature-catalogue.md` | Gate framework reference added at top. Light touch — features unchanged. | ✅ DONE |
| `ethos.md` | NEW — Ethos document given a vault home. Gate Zero Doc 5 content formalised. | ✅ DONE |
| `plan-of-attack.md` | NOT TOUCHED — UNVALIDATED, needs conversational review with John. | ⚠️ DEFERRED |

---

## WHAT'S NEXT — PRIORITISED

### 1. Create Gate Framework Skill (FB174) — DO SOON, OPUS
The process of formalising any design through a gate-based approach in Claude AI. General skill, not METIS-specific. Captures the methodology we just used — including how to progress long design conversations across multiple chats. If we wait, the context of how we did it is lost.

John specifically noted: the skill needs to cover the full lifecycle AND understand how to progress long conversations over multiple chats. This is both a design methodology skill and a multi-session continuity skill.

### 2. Flesh Out Actor Map (Gate 1 Doc 2) — OPUS
Human roles (PS dev, consultant, PM, sales) and agent roles need defining. Flagged but not yet done.

### 3. Write Gate Zero Documents for METIS — OPUS
Start with Problem Statement (incl. scope). One question at a time, conversational.
Most critical gap — can't enforce what we haven't done ourselves.

### 4. Validate plan-of-attack.md — CONVERSATIONAL WITH JOHN
UNVALIDATED from February violation session. Must step through conversationally, topic by topic. Do not bulk update.

### 5. Pipelines of Work
Separate concern. Connects to Stakeholders (G0-D3) and Project Governance (Area 6).

### 6. Toolkit Categories 2-4
Resume after above settled.

### Still open
- Follow up on msg 67d8af18 (vault sync to claude-family)
- Update Doc 1 with expanded vision, cross-doc coherence review

---

## SESSION STARTERS

### For Opus (design/skill creation)
```
METIS Session Starter — Post Doc Review
READ FIRST: `session-handoffs/2026-03-07-doc-review-complete.md`

CONTEXT: Full gate framework defined (Gates 0-4, 31 deliverables).
Master docs updated to reflect gates. Ethos has a vault home.

PRIORITY: Create gate framework skill (FB174) — this is urgent.
It's a general skill for formalising any design through gates AND
for progressing long design conversations across multiple chats.
Must capture the methodology while it's fresh.

AFTER SKILL:
1. Flesh out Actor Map — human and agent roles
2. Write Gate Zero docs for METIS — Problem Statement first
3. Validate plan-of-attack.md conversationally
4. Pipelines of work

KEY PRINCIPLES TO CAPTURE IN SKILL:
- Gate-based checkpoints (0-4) with defined deliverables
- Iterative methodology: brainstorm → consolidate → brainstorm deeper
- Multi-session continuity: handoffs, session facts, checkpoints
- Anti-monologue: one topic at a time, get human input, capture decision
- Dual-lens: framework applies to building AND to what platform enforces
- Second-pass and consolidation are cross-gate, not within a gate
- Humans may skip gates, AI cannot

KEY FILES:
* session-handoffs/2026-03-07-doc-review-complete.md — this handoff
* design-lifecycle.md — restructured around gates
* ethos.md — Gate Zero Doc 5
* system-product-definition.md — updated
* feature-catalogue.md — updated
* plan-of-attack.md — UNVALIDATED
```

---

## KEY FILES
- This handoff: `session-handoffs/2026-03-07-doc-review-complete.md`
- Prior handoffs: `2026-03-06-gate-framework-complete.md`, `2026-03-06-gate-zero.md`
- Design lifecycle: `design-lifecycle.md` (UPDATED)
- System product definition: `system-product-definition.md` (UPDATED)
- Feature catalogue: `feature-catalogue.md` (UPDATED)
- Ethos: `ethos.md` (NEW)
- Plan of attack: `plan-of-attack.md` (UNVALIDATED)
- FB174: Gate framework skill (idea, DO SOON)

---
*Session: 2026-03-07 | Status: Docs reviewed and updated. Next: create gate framework skill, then Actor Map and Gate Zero docs.*
