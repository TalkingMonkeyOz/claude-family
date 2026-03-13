---
tags:
  - project/Project-Metis
  - type/handoff
  - domain/all-gates
  - target/claude-family
created: 2026-03-10
updated: 2026-03-10
from: claude-desktop (METIS project)
to: claude-family (Claude Code Console)
status: pending
priority: high
supersedes: (original version was Gate 1 only — now expanded to full consolidation)
---

# METIS Full Consolidation Task — All Gates, All Material

## What We're Trying To Do

METIS is an enterprise AI development lifecycle platform. It learns what an organisation does (their product, processes, integrations, client configurations) and uses that knowledge to accelerate real work — professional services delivery, support, development, testing, documentation.

The first target customer is nimbus (John's company, product: time2work — a staff scheduling and payroll system). We take the learnings from building Claude Family and implement a central AI knowledge system that understands the nimbus product, and becomes the heart for everything nimbus does: sales, professional services, customisations, project development, sign-off documents, developing, testing, deployment documentation.

We're designing METIS through a **5-gate framework** (Gates 0-4, 31 total deliverables). See `design-lifecycle.md` for the full framework with all 31 docs listed.

**There is a LOT of material scattered across the vault** — 35 session handoffs, 9 area directories with READMEs and brainstorm docs, feature catalogue, system product definition, 5 research papers, security architecture, BPMN process maps, knowledge DB entries, session facts across multiple sessions. Much of it was produced during brainstorm sessions before the gate framework existed.

**Your job:**
1. Read ALL source material
2. For each piece of content, identify which gate and which deliverable it belongs to
3. Assemble formal documents where enough material exists
4. For material that's partial, place it in the right gate directory with a clear "what's here / what's missing" summary
5. Come back to John and me with a **gap list** — genuine decisions that haven't been made yet, organised by gate

This is NOT just Gate 1. Material exists that feeds Gate 0 updates, Gate 1 completion, Gate 2 early inputs, and Gate 3 inputs. Place everything where it belongs.

---

## THE GATE FRAMEWORK (reference — full detail in design-lifecycle.md)

### Gate 0 — "Do we understand the problem?" — 5 docs — COMPLETE ✅
1. Problem Statement (incl. Scope)
2. Assumptions & Constraints
3. Stakeholders & Decision Rights
4. System Map (C4 L1/L2)
5. Design Principles / Ethos

**Gate 0 is done BUT** — decisions made since March 8 may require updates to these docs. Flag anything that needs updating.

### Gate 1 — "Do we understand the domain?" — 5 docs — 1 of 5 DONE
1. Process Inventory — **NEEDED** (processes implicit across brainstorms, never inventoried)
2. Actor Map — ✅ DONE (`gate-one/actor-map.md`)
3. Data Entity Map — **NEEDED** (entities scattered across sessions, never consolidated)
4. Business Rules Inventory — **NEEDED** (rules discussed extensively, never inventoried)
5. Integration Points — **NEEDED** (patterns decided, specifics not detailed)

### Gate 2 — "Have we designed the solution?" — 12 docs — NOT FORMALLY STARTED
1. Detailed Process Models (BPMN)
2. C4 Level 3 Component Diagrams
3. Domain Model (DDD)
4. Decision Models (DMN)
5. Data Model (actual DB design)
6. Tech Stack Decisions
7. API / Interface Design
8. Security & Access Model
9. Test Strategy
10. User/Actor Journey Maps
11. Deployment Architecture
12. Monitoring, Logging & Observability Design

**BUT** — significant material exists that feeds Gate 2 even though it hasn't started formally: Knowledge Engine design (6 types, storage, retrieval, ingestion, lifecycle), security architecture doc, tech stack decisions (PostgreSQL, pgvector, Voyage AI, SpiffWorkflow, custom RAG), agent architecture decisions, BPMN process maps, monitoring/alerting design, CI/CD pipeline spec, connector interface design. Place this material where it belongs.

### Gate 3 — "Are we ready to build?" — 8 docs — NOT STARTED
1. Development Standards / Coding Conventions
2. Environment Setup / Infrastructure
3. Build Plan / Sprint Backlog
4. Definition of Done
5. Agent Protocols / Constraints & Skills
6. Documentation Standards
7. Risk Register
8. Project Delivery Framework

**Some material exists**: agent conventions doc, phase-0 task list, plan-of-attack rewrite brief, day-1 readiness doc. Place where it belongs.

### Gate 4 — Release Readiness Checklist — NOT APPLICABLE YET

---

## WHERE ALL THE DATA EXISTS

### Tier 1: Formal Documents (highest signal)

| File | Relevant to |
|---|---|
| `feature-catalogue.md` | RICHEST SOURCE — 10 features with processes, actors, behind-the-scenes flows, integration points, entities. Feeds Gate 1 (all docs) and Gate 2 (journey maps, process models). |
| `system-product-definition.md` (v0.3) | 9 areas with descriptions. Feeds Gate 1 + Gate 2. |
| `design-lifecycle.md` | The gate framework itself + current progress tracker. UPDATE this when consolidation is done. |
| `gate-one/actor-map.md` | ✅ Validated. Cross-reference for all other docs. |
| `gate-zero/problem-statement.md` | Scope boundaries. Check if updates needed. |
| `gate-zero/assumptions-constraints.md` | Hard constraints → business rules. Check if updates needed. |
| `gate-zero/stakeholders-decision-rights.md` | Decision rights. Check if updates needed. |
| `gate-zero/system-map.md` + `system-map.html` | C4 L1/L2. External systems, integration flows. Also `metis-system-map.html` at vault root. |
| `ethos.md` | Design principles → business rules. |
| `security-architecture.md` | Security model → Gate 2 Doc 8 input. |
| `plan-of-attack-rewrite-brief.md` | 8 validated decisions + phase structure → Gate 3 input. |
| `plan-of-attack.md` | UNVALIDATED original — use brief as the authority, not this. |

### Tier 2: Area Brainstorms & READMEs

| Directory | Files | Feeds |
|---|---|---|
| `knowledge-engine/` | README.md, brainstorm-knowledge-engine-deep-dive.md, knowledge-graph-relationships.md | Gate 1 (entities, processes, rules) + Gate 2 (data model, component design) |
| `integration-hub/` | README.md, connector-interface-design.md | Gate 1 (integration points) + Gate 2 (API design) |
| `ps-accelerator/` | README.md, brainstorm-delivery-accelerator.md | Gate 1 (processes, rules) + Gate 2 (journey maps) |
| `quality-compliance/` | README.md, brainstorm-quality-compliance.md | Gate 1 (processes, rules) + Gate 2 (test strategy) |
| `support-defect-intel/` | README.md | Gate 1 (processes) — flagged as thin area |
| `project-governance/` | README.md, brainstorm-project-mgmt-lifecycle.md, pm-lifecycle-client-timelines.md | Gate 1 (processes, rules) + Gate 3 (delivery framework) |
| `orchestration-infra/` | README.md + 14 files including agent-conventions.md, monitoring-alerting-design.md, cicd-pipeline-spec.md, session-memory-context-persistence.md, infra-decisions-api-git-auth.md, phase-0-task-list.md, day-1-readiness.md, user-experience.md | Gate 2 (multiple docs) + Gate 3 (dev standards, environment, agent protocols) |
| `commercial/` | README.md | Gate 1 — flagged as thin area |
| `bpmn-sop-enforcement/` | README.md, brainstorm-capture-enforcement-layer.md, session-2026-02-23-design-validation.md | Gate 1 (processes, rules) + Gate 2 (BPMN, DMN) |

### Tier 3: Session Handoffs (35 files in session-handoffs/)

All 35 files. Read them all — decisions are buried throughout. Key ones:

| File | Key content |
|---|---|
| `2026-03-10-research-review-option-c.md` | Option C decision, 7 library science principles, WCC design direction |
| `2026-03-10-knowledge-engine-design.md` | 6 knowledge types, storage architecture, retrieval priority, ingestion, decay/freshness, RBAC proposal |
| `2026-03-09-interaction-model-mcp-review.md` | MCP tool review, interaction patterns |
| `2026-03-08-scope-reframe-actor-map.md` | Scope reframe, actor map decisions |
| `2026-03-08-gate-zero-complete.md` | Gate Zero completion |
| `2026-03-08-security-architecture.md` | Security decisions |
| `2026-03-07-*` | Doc review, Gate Zero session |
| `2026-03-06-*` | Gate framework creation |
| `2026-03-02-toolkit-brainstorm.md` | MCP toolkit decisions |
| `2026-02-28-*` | Sessions 7 & 8 |
| `2026-02-24-*` (8 files) | Area sweeps, consolidation, project mgmt lifecycle, session memory |
| `2026-02-23-*` (5 files) | BPMN brainstorm, design systems, knowledge engine deep dive, orchestration, stocktake |
| `handoff-2026-02-*` | Earlier gap review and design handoffs |
| `setup-chat-*` | Session setup instructions (may contain decisions) |

### Tier 4: Research Documents (5 files in research/)

| File | Feeds |
|---|---|
| `augmentation-layer-research.md` | Gate 2 (component design, architecture) |
| `library-science-research.md` | Gate 2 (knowledge engine design — 7 principles accepted) |
| `filing-records-management-research.md` | Gate 2 (knowledge lifecycle design) |
| `work-context-container-synthesis.md` | Gate 2 (augmentation layer design) |
| `work-context-container-options.md` | Gate 2 (Options A/B/C analysis — C chosen) |

### Tier 5: Knowledge Database

Query these:
- `claude.knowledge` — filter by applies_to_projects containing 'metis' or 'Project-Metis'. Stored facts, decisions, patterns, procedures.
- `claude.session_facts` — last 10+ sessions on project 'metis'. Incremental decisions.
- `claude.feedback` — any open feedback items for metis.

### Tier 6: Other Root-Level Vault Files

| File | Content |
|---|---|
| `gap-tracker.md` | Identified gaps and resolution status |
| `gap-resolution-summary.md` | How gaps were resolved |
| `stocktake-2026-02-23.md` | State assessment from Feb 23 |
| `claude-family-systems-audit.md` | CF audit summary |
| `claude-family-audit-*.md` (7 files) | Detailed CF subsystem audits — inform Gate 2 tech decisions |
| `bpmn-process-map*.md` (3 files) | BPMN process maps — Gate 2 input |

---

## DECISIONS MADE THIS SESSION (2026-03-10, not yet in vault files)

These need to be placed in the appropriate gate docs:

1. **RBAC CONFIRMED**: Tenant-level hard isolation for Client Config + Learned/Cognitive. Product Domain + API Reference shared across tenants. Process/Procedural shared with tenant-specific variants. Project/Delivery tenant-scoped. Roles: Platform Builder (all tenants), Enterprise Admin (their tenant), Enterprise Staff (work-context scoped). → Gate 1 (Business Rules) + Gate 2 (Security & Access Model)

2. **Four-layer context management architecture**: Core Protocols (always, tiny) → Session Notebook (write as you go, survives compaction) → Knowledge Retrieval (librarian, chunked, on-demand) → Persistent Knowledge (cross-session, semantic). Dynamic priority, NOT fixed token budget. → Gate 2 (Component Design)

3. **Context management = retrieval precision, not window stuffing**: Librarian model. Retrieve by chunk not book. OData metadata proof point. Every piece of knowledge in searchable chunks with token_count. → Gate 2 (Component Design)

4. **Task decomposition protocol**: Core protocol instructs model to break down every user input into tasks on every request. → Gate 2 (Component Design) + Gate 3 (Agent Protocols)

5. **Delegation model**: Desktop does design decisions/principles with John. Claude Code does technical design and build. → Gate 3 (Project Delivery Framework)

---

## OUTPUT EXPECTED

### For each gate:
- Formal documents where enough material exists to assemble them
- Partial documents with clear "what's here / what's missing" markers for items that are incomplete
- All placed in the appropriate gate directory (`gate-zero/`, `gate-one/`, `gate-two/`, `gate-three/`)

### Gap list:
- `consolidation-gaps.md` at the Project-Metis root
- Organised by gate
- For each gap: what decision is needed, what context exists, who needs to decide (John)
- Be honest — if a gap is minor (just needs writing up), say so. If it's a genuine missing decision, flag it clearly.

### Updated tracker:
- Update `design-lifecycle.md` section 3 (METIS Progress Tracker) to reflect the new state after consolidation

---

## IMPORTANT NOTES

- **Later decisions supersede earlier ones.** Session handoffs are chronological — later dates win. The plan-of-attack-rewrite-brief (2026-03-08) supersedes plan-of-attack.md (2026-02-26).
- **Don't invent.** If material doesn't exist for a deliverable, flag it as a gap. Don't write content that hasn't been decided.
- **Gate 1 is inventory, not design.** Process Inventory = list of processes, not BPMN models. Data Entity Map = list of entities, not a database schema. Keep it at the right level.
- **Gate 2 material may be early/partial.** That's fine — place it where it belongs with a status marker. It doesn't need to be complete.
- **The plan-of-attack rewrite is a SEPARATE task** — don't merge it with this consolidation. The brief (`plan-of-attack-rewrite-brief.md`) feeds into Gate 3 Doc 3 but the actual rewrite happens after this consolidation is done and gaps are filled.
- **This task is independent of the data model request (msg bcecb306) and WCC design request (msg 96f7768b)** — those produce NEW content for Gate 2. This consolidation is about organising EXISTING content.

---
*From: Claude Desktop (METIS session 2026-03-10) | Priority: High — this is the foundation for everything else*
