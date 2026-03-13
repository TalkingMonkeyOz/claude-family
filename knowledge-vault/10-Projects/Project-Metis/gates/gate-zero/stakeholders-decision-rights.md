---
tags:
  - project/Project-Metis
  - scope/system
  - type/gate-zero
  - gate/zero
created: 2026-03-07
updated: 2026-03-12
status: validated
---

# Stakeholders & Decision Rights

Gate Zero Document 3.

## METIS Platform (Current State)

| Stakeholder | Role | Decision Authority |
|---|---|---|
| John de Vere | Founder, architect, sole builder | All decisions — design, architecture, priorities, commercial |
| Claude Desktop | AI design partner (MD of Claude Family) | Proposes, drafts, analyses, recommends. Cannot decide. |
| Claude Code | AI implementation partner | Executes, builds, tests. Cannot decide. |

## nimbus Engagement (First Customer)

| Stakeholder | Role | Decision Authority |
|---|---|---|
| Grant Custance | Director | Strategic approval — "do we do this at all" |
| Harrison Custance | Managing Director | Operational go/no-go, day-to-day sponsor |
| Justin | CFO / COO | Commercial terms, budget, operational impact |
| David | CTO | Technical approval, infrastructure, security, integration |
| Sharon | Chief Customer Manager | Customer-facing impact, support readiness |

## Division of Labour

The METIS build follows a clear division of responsibility across the Claude Family:

| Role | Responsibility | When Engaged |
|---|---|---|
| **Claude Desktop** | Design decisions and principles WITH John. Brainstorming, gap closure, validation. | Every design session |
| **Claude Code (Claude Family)** | Technical design, implementation, consolidation. Reads vault material, builds, tests. | Delegated tasks requiring large-scale work — consolidation, data model design, code implementation |
| **John de Vere** | All decisions. Validates every design choice. Guides priorities. | Always — nothing is decided without John |

Claude Desktop does not delegate routine doc updates or small edits to Claude Family — those are handled directly in the Desktop session. Claude Family is brought in for architectural work, large consolidation tasks, and implementation that requires reading and synthesising many files.

---

## AI Decision Rights Model

**Initial state:** All decisions go through a human. AI agents propose, humans approve. No exceptions.

**Progressive autonomy:** Over time, through analysis of outcomes and training, AI agents can earn autonomous decision-making in areas where they demonstrate very high confidence consistently. The system learns which decisions it gets right and can gradually act on those without human approval.

**The principle:** Autonomy is earned through demonstrated competence, not granted upfront. The platform itself should track confidence and outcomes to inform which decisions can be safely delegated.

## Escalation Paths

| Situation | Escalates To |
|---|---|
| AI uncertain about any decision | Human who owns that decision area |
| nimbus day-to-day operational | Harrison (MD) |
| nimbus technical decisions | David (CTO) |
| nimbus commercial decisions | Justin (CFO/COO) |
| nimbus customer-facing impact | Sharon (Chief Customer Manager) |
| nimbus strategic / cross-cutting | Grant (Director) |
| METIS platform decisions (current) | John de Vere |

## Future State

As METIS grows beyond a one-person operation, decision rights will need to be distributed. This document should be updated as new stakeholders join — whether human team members or AI agents with earned autonomy in specific domains.

---

*Gate Zero Doc 3 | Validated: 2026-03-07 | Author: John de Vere + Claude Desktop*

---
**Version**: 1.0
**Created**: 2026-03-07
**Updated**: 2026-03-07
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-zero/stakeholders-decision-rights.md
