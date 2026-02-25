---
tags:
  - project/Project-Metis
  - area/bpmn-sop-enforcement
  - level/1
  - scope: system
projects:
  - Project-Metis
created: 2026-02-23
session: enforcement-layer-workflows
status: brainstorm-captured
---

# Area 9: BPMN / SOP & Enforcement — Brainstorm Capture

> Validation workflows, stage gates, deployment approvals, triage rules — the operational rules of the platform itself.

**Priority:** CROSS-CUTTING (touches every other area)
**Status:** Brainstorm captured — ready for consolidation pass
**Date:** February 23, 2026
**Session:** Enforcement layer & workflows discussion

---

## What This Area IS

The operational rules of the platform itself. How do we ensure Claude agents follow defined processes? How do we track compliance? How do we make the rules visible and changeable without code?

This is not a user-facing feature — it's the skeleton that keeps everything else honest. Cross-cutting concern that touches all 9 areas.

## Two Levels of Enforcement

### Level 1 — User/Business Workflows
How does work flow through the platform? The process maps for each area — "what happens and in what order" for the humans and systems using the platform.

Examples: implementation pipeline, support triage, knowledge validation, release management.

### Level 2 — AI Process Enforcement
How do we make Claude (and Claude agents) actually follow those workflows reliably instead of freestyling?

Key insight: LLMs are inherently bad at following fixed processes. They skip steps, get creative when they should be mechanical, forget context mid-process. Prompt instructions are suggestions, not hard constraints. Enforcement must be EXTERNAL to Claude.

## Existing Claude Family Assets

- **SpiffWorkflow** — already in use. Pure Python BPMN+DMN engine.
  - 3 classes used: BpmnParser, BpmnWorkflow, TaskState
  - Two usage modes: XML parsing (validation) + runtime execution (get_current_step)
  - 50 BPMN processes, 490 tests, L0/L1/L2 hierarchy
  - Key gap: **no persistence** — workflow state doesn't survive session boundaries
  - **DMN installed but not activated** — zero .dmn files, zero DMN imports
  - Recent improvement: auto-filing BPMN alignment gaps as feedback (FB147)
  - Vault reference: [[20-Domains/SpiffWorkflow Usage Guide]]
- **Other enforcement mechanisms** — MCP custom systems that constrain Claude behaviour, session management, conventions, logging

## Enforcement Approach: B/C/E Hybrid (Three Tiers)

Not everything needs the same rigour. Match enforcement to stakes.

### Tier 1 — SpiffWorkflow Runtime (High Stakes)
Full BPMN process with SpiffWorkflow tracking state. Claude is a **worker** within the workflow, not the controller. SpiffWorkflow decides what step comes next, Claude does the work for that step.

**When to use:** Processes where skipping a step has real consequences — compliance, client data, deployments.

**Candidates:**
- Knowledge validation (Tier 2+ knowledge requiring human approval)
- Deployment/release pipeline (UAT → production promotion)
- Client configuration changes (touching live systems)
- Pay scenario test cycle (compliance validation)

### Tier 2 — Checklist + Validation (Structured, Lower Stakes)
Database-backed checklist with validation gates. Each step has "done" criteria checked before the next step unlocks. Could be modelled as simple linear SpiffWorkflow or as standalone validation logic.

**When to use:** Structured processes that are mostly linear with validation checkpoints.

**Candidates:**
- Support ticket triage
- Defect capture
- Documentation generation from templates
- Standard data imports

### Tier 3 — Prompt + Conventions (Low Stakes)
System prompt, CLAUDE.md, cached knowledge provide guidance. No external state machine. User evaluates output directly.

**When to use:** Processes where enforcement overhead exceeds cost of occasional drift.

**Candidates:**
- Knowledge Q&A
- Report generation
- General search

## Three Components (Designed Together)

### Component 1: Persistent Workflow Engine
SpiffWorkflow with database-backed state persistence. Workflow instances survive across sessions, crashes, and days.

**Design questions:**
- Serialisation format: JSON (portable, debuggable) vs pickle (simpler)? Recommend JSON.
- Storage: PostgreSQL (already have it) — need workflow_instances table schema
- Resume mechanism: orchestration layer checks for pending workflows on session start
- Timeout/escalation: BPMN timer events handle natively
- Concurrent instances: yes — different clients, different knowledge items in parallel

### Component 2: DMN Decision Tables
Rules currently in prompts or Python logic → structured, executable decision tables.

**Candidate DMN tables:**
- Knowledge validation routing: input (knowledge type, source, confidence) → output (validation tier, approver role, auto-approve y/n)
- Support ticket triage: input (issue category, client tier, severity) → output (priority, route, SLA)
- Deployment gate decisions: input (test pass rate, environment, change type) → output (approve/block/escalate)
- Gap classification: categorise and route BPMN alignment gaps

**Design questions:**
- Creation/management: visual editor (BPMN.js has DMN support) or XML?
- Storage: vault (version controlled) for definitions, database for runtime state?
- Authority: who can change DMN rules? What approval is needed?
- Testing: every DMN table needs test cases to validate rule changes

### Component 3: Gap Detection & Compliance Metrics
Feedback loop that proves enforcement works. Measure: did processes complete as designed?

**What to log:**
- Workflow instance ID, process definition, each step entered/completed/skipped
- Time per step, who/what completed each step (Claude agent, human, system)
- Deviations from expected path

**Where it goes:** workflow_execution_log table (extends existing rag_usage_log pattern)

**Derived metrics:**
- Process completion rate (clean vs required intervention)
- Average deviation rate per process type
- Most common failure steps
- Time-to-completion vs expected
- Human intervention frequency

**Feedback loop:** When gap detection identifies patterns (Claude consistently struggles with step X) → triggers process redesign, prompt improvement, or additional training data

## How Components Interact

```
BPMN Diagram (source of truth: "how this process works")
    │
    ▼
SpiffWorkflow Runtime (Component 1)
    │
    ├── At decision points → calls DMN tables (Component 2)
    │                         "what rules apply here?"
    │
    ├── Every step → logged (Component 3)
    │                 "did it work as designed?"
    │
    └── If deviation detected → gap recorded, fed back
```

## Processes Needing BPMN Definitions

| Process | Area | Tier | Why Enforcement Needed |
|---|---|---|---|
| Knowledge ingestion & validation | Area 1 | Tier 1 | Compliance-critical for Award knowledge |
| Client configuration change | Area 3 | Tier 1 | Touches live client systems |
| Deployment/release pipeline | Area 3 | Tier 1 | UAT → prod must be gated |
| Pay scenario test cycle | Area 4 | Tier 1 | Compliance validation, can't skip steps |
| Support ticket triage | Area 5 | Tier 2 | Structured but simpler flow |
| Defect capture | Area 5 | Tier 2 | Needs completeness checking |
| Documentation generation | Area 3 | Tier 2 | Template-driven, validation at end |
| Knowledge Q&A | Area 1 | Tier 3 | Low stakes, user evaluates output |
| Report generation | Area 6 | Tier 3 | Low stakes, human reviews result |

## Relationship to Five-Layer Validation Stack

Previously identified: DDD → BPMN → DMN → Ontology → Event Sourcing

| Layer | What It Does | Status |
|---|---|---|
| DDD (boundaries) | Defines bounded contexts, what belongs where | Conceptual — needs Area 1 deep dive |
| BPMN (process flow) | Defines how processes work | Active — SpiffWorkflow in use |
| DMN (decision logic) | Defines rules at decision points | Installed, not activated |
| Ontology (completeness) | Ensures nothing is missed, impact analysis | Conceptual — future |
| Event Sourcing (lifecycle) | Full history of state changes | Conceptual — aligns with audit logging |

**Open question:** Start with BPMN + DMN for initial build, add Ontology + Event Sourcing later? Or design all five from the start?

## Technology Decision

**SpiffWorkflow chosen over Camunda.** Rationale:
- Already in use in Claude Family (proven, known)
- Pure Python (fits stack)
- Open source, LGPL v3
- Minimal dependencies (lxml only)
- Native BPMN + DMN support
- Lightweight vs Camunda's Java enterprise weight

## Open Questions for Consolidation

- How many BPMN processes does the MVP actually need vs aspirational?
- Does every area need at least one Tier 1 process, or can some areas operate entirely at Tier 2/3?
- Who maintains BPMN diagrams long-term? Process owner role?
- How does L0/L1/L2 hierarchy from Claude Family map to platform areas?
- SpiffWorkflow embedded at runtime vs design tool vs both?
- What's the minimum viable enforcement for Monash POC specifically?

---

*This is brainstorm-depth capture. Full BPMN process design happens in the "mother of all sessions" after consolidation pass across all areas.*

*Source: Enforcement layer discussion, Feb 23 2026*
