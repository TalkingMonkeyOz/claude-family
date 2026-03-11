---
tags:
  - project/Project-Metis
  - scope/system
  - type/gate-one
  - gate/one
created: 2026-03-08
updated: 2026-03-08
status: validated
---

# Actor Map

Gate 1 Document 2.

## Purpose

Identifies every actor that interacts with or operates within METIS: human roles, AI agents, and external systems. Different from Stakeholders & Decision Rights (Gate 0 Doc 3) which defines who DECIDES — this document defines who and what USES the system.

This is a living document. New actor types (human and agent) will emerge as the system grows. The architecture must support registering, constraining, and deploying new actor types without structural changes.

---

## 1. Human Actors

Six actor types identified. These are the high-level starting set. Additional roles (e.g. Sales, Marketing) are identified but deferred — they will need their own streams when the time comes.

| Actor | Access | Primary Interaction | Maps To |
|---|---|---|---|
| **Platform Builder** | Direct | Builds and maintains METIS itself. Architecture, design, development, testing. | Cross-cutting |
| **Enterprise Admin** | Direct | Configures platform, manages knowledge, tenant setup, constrained deployments. | Platform Services (Areas 7+8) |
| **PS Consultant** | Direct | Implementation, configuration, client delivery. Day-to-day project work. | Delivery Accelerator (Area 3) |
| **Support Staff** | Direct | Triage, defect management, resolution, pattern detection across clients. | Support & Defect Intelligence (Area 5) |
| **Developer** | Direct | Customisation, testing, code-level work, quality validation. | Quality & Compliance (Area 4) |
| **End Customer** | **Indirect only** | No direct METIS access. Inputs arrive via enterprise channels (tickets, docs, specs ingested by PS). Direct chat interface is future-state possibility. | Via Integration Hub (Area 2) |

### Notes on Human Actors

- **Real people may span multiple roles.** At smaller organisations like nimbus, one person might do PS and support. The roles define interaction patterns, not job titles.
- **Enterprise Staff was deliberately split** from the C4 L1 into PS Consultant, Support Staff, and Developer because their interaction patterns, knowledge needs, and constrained deployment profiles are meaningfully different.
- **Deferred roles:** Sales, Marketing, and potentially other business functions will need their own streams. Identified but not defined here — they require fleshing out when the system extends to those areas.
- **Each actor type gets a different constrained deployment profile** — different skills, different knowledge scoping, different tool access.

---

## 2. AI Agent Actors

Three categories of AI agent. The agent architecture follows the **hub-and-spoke / supervisor pattern** confirmed by industry research (Microsoft Semantic Kernel, Claude Code Agent Teams, Kore.ai Supervisor Pattern, Anthropic's own multi-agent documentation).

### Design Principles for Agents

- **Specialised agents, not one general agent.** Constrained instructions are essential to keep agents on course. A general-purpose agent drifts; a specialised agent stays on rails.
- **Three-layer context hierarchy:**
  - **Global standards** — every agent knows what it's part of, where to find knowledge, what the standards are. Non-negotiable shared DNA.
  - **Project context** — scope, decisions, current state for the specific project/engagement.
  - **Agent purpose** — tightly constrained instructions for this specific agent type.
- **One controller per project** — orchestrates specialist agents, holds the big picture, manages decomposition and handoffs. The bottleneck but also the coherence mechanism.
- **3-4 sub-agent limit per supervisor** — based on practical experience and industry guidance. More than that and the supervisor spends too much time managing rather than coordinating.
- **Autonomy is earned** — all decisions go through a human initially. Progressive autonomy based on demonstrated competence (from Gate 0 Doc 3).
- **Parallel work = decomposition problem** — break the elephant into smaller pieces, track the pieces. Work awareness and state tracking is an Augmentation Layer concern.
- **Cost awareness** — multi-agent means multiplied API calls and token overhead. Must be accounted for in commercial model and architecture.

### Category A: Project Agents (hierarchical, task-driven)

Spun up per project. Follow the supervisor pattern.

| Agent Type | Role | Spun Up By | Notes |
|---|---|---|---|
| **Project Controller** | Holds the big picture for a project. Decomposes work, kicks off supervisors, manages handoffs, tracks progress. | Human or Master AI | One per project. The coherence mechanism. |
| **Supervisor Agent** | Manages 3-4 specialist sub-agents for a specific task or workstream. | Project Controller | Multiple supervisors can run on a project if warranted. |
| **Design Agent** | Requirements analysis, solution design, architecture. | Supervisor | Specialist sub-agent |
| **Analysis Agent** | Knowledge retrieval, research, gap identification. | Supervisor | Specialist sub-agent |
| **BPMN Agent** | Process modelling, workflow validation. | Supervisor | Specialist sub-agent |
| **Test Agent** | Scenario generation, test execution, validation. | Supervisor | Specialist sub-agent |
| **Coder Agent** | Implementation, configuration generation, code. | Supervisor | Specialist sub-agent |
| **Documentation Agent** | Generates documentation from system state. | Supervisor | Specialist sub-agent |

**This is not a fixed list.** New specialist types will emerge as the system grows. The architecture must support registering new agent types with their own constrained deployment profiles.

### Category B: Event-Driven Agents (isolated, triggered)

Not part of a project hierarchy. Triggered by events, do their job, finish.

| Agent Type | Trigger | Role | Notes |
|---|---|---|---|
| **Document Scanner** | User submission | Processes submitted documents, extracts content, prepares for ingestion. | Isolated per submission. |
| **Knowledge Ingestion Agent** | New content arrival | Ingests, embeds, indexes new knowledge. | May fire frequently during initial setup. |
| **Notification Agent** | System events | Sends alerts, notifications based on configured triggers. | Event-driven, stateless per invocation. |

### Category C: System-Level Agents (persistent, operational)

Run continuously or on schedule. Monitor and maintain the system itself.

| Agent Type | Schedule | Role | Notes |
|---|---|---|---|
| **Master AI** | Continuous / scheduled | Has a run sheet of things to check. Oversees system health, triggers maintenance tasks, monitors agent performance. | The "always-on" coordinator. |
| **Health Monitor** | Continuous | Watches system performance, resource usage, error rates. Flags issues. | Operational monitoring. |
| **Knowledge Quality Agent** | Scheduled | Checks for staleness, gaps, drift in the knowledge base. Flags items for human review. | Event-driven staleness (not time-driven). |

---

## 3. External System Actors

From C4 Level 1 (Gate 0 Doc 4). These are systems that interact with METIS but are not part of it.

| System | Direction | Protocols | Role |
|---|---|---|---|
| **LLM Provider** | Outbound | HTTPS / API | Inference — prompt completion, analysis, generation. Currently Claude API, provider-agnostic by design. |
| **Embedding Service** | Outbound | HTTPS / API | Vector embedding generation for knowledge retrieval. Currently Voyage AI. |
| **Enterprise Toolstack** | Bidirectional | REST, MCP | Jira, Confluence, CRM, repos — varies per customer. Read data in, push insights out. |
| **Enterprise Product** | Bidirectional | REST, OData, MCP | Customer's own product APIs. Read product config/data, potentially write back. |

---

## 4. Actor Interaction Summary

### How the categories relate

```
Human Actors ──→ API Layer ──→ Application Services ──→ Augmentation Layer
                                                              │
                                                              ├──→ Project Agents (Category A)
                                                              │      └── Controller → Supervisors → Specialists
                                                              │
                                                              ├──→ Event-Driven Agents (Category B)
                                                              │      └── Triggered by submissions/events
                                                              │
                                                              └──→ System-Level Agents (Category C)
                                                                     └── Master AI, Health, Knowledge Quality

External Systems ←──→ Integration Hub ←──→ Augmentation Layer
```

### Key relationships

- **Human actors** interact through the API Layer and Application Services. They don't interact with agents directly — the Augmentation Layer mediates.
- **Project agents** are orchestrated through the Augmentation Layer's context assembly, skills, and session management.
- **Event-driven agents** are triggered by the Integration Hub or Application Services when content arrives.
- **System-level agents** monitor the platform itself, operating above the project level.
- **External systems** connect through the Integration Hub. Data flows bidirectionally.

---

## 5. Relationship to Other Documents

| Document | Relationship |
|---|---|
| Stakeholders & Decision Rights (Gate 0 Doc 3) | Who DECIDES. This document defines who USES. |
| System Map C4 L1 (Gate 0 Doc 4) | Human actors and external systems sourced from L1. Agent actors are new. |
| System Map C4 L2 (Gate 0 Doc 4) | Agent categories map to the Augmentation Layer (cross-cutting). |
| System Product Definition | Agent architecture aligns with constrained deployment pattern (Section 4.2). |
| Design Lifecycle | Actor types will each need User Journey Maps at Gate 2 (Doc 10). |

---

## 6. Open Questions

- [ ] What does the Master AI's "run sheet" look like? (Deferred to Gate 2)
- [ ] How do agent types get registered and deployed? (Augmentation Layer design, Gate 2)
- [ ] What's the cost model per agent type? (Commercial model, Area 8)
- [ ] How do Sales and Marketing roles differ from the current actor set? (Deferred)
- [ ] What's the supervision model when multiple supervisors run on one project? (Gate 2)

---
*Gate 1 Doc 2 | Validated: 2026-03-08 | Author: John de Vere + Claude Desktop*

---
**Version**: 1.0
**Created**: 2026-03-08
**Updated**: 2026-03-08
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-one/actor-map.md
