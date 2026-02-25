---
tags:
  - project/Project-Metis
  - area/bpmn-sop-enforcement
  - area/design-validation
  - level/1
  - phase/cross-cutting
projects:
  - Project-Metis
created: 2026-02-23
synced: false
---

# Design Validation & Enforcement (Area 9)

> The operational rules of the platform. How we validate that what Claude builds is correct, complete, and coherent — and stays that way across years of changes.

**Priority:** HIGH — Cross-cutting (touches every other area)
**Parent:** [[Project-Metis/README|Level 0 Map]]
**Status:** ✓ BRAINSTORM-COMPLETE (Chat #1 brainstorm + consolidation review)

## What This Area Covers

This is the validation and enforcement layer for the entire platform. It ensures that:

- Designs Claude produces are complete, correct, and follow established patterns
- Decision logic within processes is explicit, testable, and auditable
- Domain boundaries are respected and knowledge is properly scoped
- Changes don't break existing dependencies or create gaps
- The full history of decisions and state changes is preserved across the application lifecycle — potentially years or decades of iterations

This area is NOT about testing code (that's Quality & Compliance, Area 4). This is about validating *designs, decisions, processes, and knowledge* before and during implementation, and maintaining coherence as the system evolves.

## The Core Problem

The nimbus AI Platform is designed so that Claude does the heavy lifting — design, configuration, documentation, testing — with humans providing guidance and validation at checkpoints. For this to work reliably across multiple domains, multiple clients, and multiple years of evolution, Claude's work needs to be continuously validated against:

- Process completeness (are all steps present?)
- Decision correctness (given these inputs, is the output right?)
- Domain integrity (does this change respect boundaries?)
- Knowledge completeness (are all affected entities accounted for?)
- Historical consistency (does this contradict previous decisions?)

No single system handles all of these. The solution is a layered stack of complementary design systems, each handling a different type of validation.

## The Five-Layer Validation Stack

Five design systems work together. Each handles a different concern. Together they provide end-to-end validation from domain structure through to lifecycle state management.

```
┌─────────────────────────────────────────────────┐
│  5. EVENT SOURCING                              │
│     Lifecycle state — what happened, when, why  │
├─────────────────────────────────────────────────┤
│  4. ONTOLOGY / KNOWLEDGE GRAPH PATTERNS         │
│     Completeness — are all dependencies covered │
├─────────────────────────────────────────────────┤
│  3. DMN (Decision Model & Notation)             │
│     Logic — given inputs X, output should be Y  │
├─────────────────────────────────────────────────┤
│  2. BPMN (Business Process Model & Notation)    │
│     Flow — are all steps present and sequenced  │
├─────────────────────────────────────────────────┤
│  1. DDD (Domain-Driven Design)                  │
│     Boundaries — what belongs where             │
└─────────────────────────────────────────────────┘
```

Each layer feeds the one above it. DDD without BPMN gives structure but no flow. BPMN without DMN gives flow but no decision rigour. All of them without event sourcing gives point-in-time validation but no lifecycle memory.

---

### Layer 1: Domain-Driven Design (DDD)

**What it does:** Defines the domain boundaries — what belongs together, what doesn't cross boundaries, what the key entities and relationships are within each domain.

**How it's applied in nimbus:**
- Bounded contexts map to platform areas: Award rules are one context, time2work configuration is another, client engagement is another
- Aggregates define what gets validated together (e.g. an Award configuration is an aggregate — you validate all its parts as a unit, not individually)
- Domain events define what triggers cross-boundary communication (e.g. "Award rule changed" triggers re-validation in Quality & Compliance)
- Ubiquitous language enforces consistent terminology across the platform — "rule type" means the same thing everywhere

**Why it matters:** Without clear boundaries, Claude will mix concerns. A configuration change in one domain might silently break something in another. DDD makes those boundaries explicit and enforceable.

**Directly supports:** The hybrid domain+tags architecture decision already made. Domain field = bounded context. Tags = cross-cutting concerns that span contexts.

**Nimbus examples:**
- Award/EA interpretation is a bounded context — it has its own rules, its own validation, its own approval chain
- time2work API integration is a separate context — it has its own auth, its own rate limits, its own error handling
- Client configuration spans both but respects their boundaries — it uses Award knowledge and API knowledge but doesn't blur them together

**Open questions for focused session:**
- [ ] What are the definitive bounded contexts for the nimbus platform?
- [ ] What domain events cross boundaries and trigger re-validation?
- [ ] How does this map to the existing vault folder structure?
- [ ] Should DDD concepts be explicit in the knowledge schema (domain field, aggregate references)?

---

### Layer 2: BPMN (Business Process Model & Notation)

**What it does:** Orchestrates processes — defines what steps happen in what order, who does them, what gates must pass before proceeding, and where processes branch or converge.

**How it's applied in nimbus:**
- Validates process completeness in designs Claude produces — are all steps present? Are there gaps between steps?
- Defines stage gates for knowledge validation (Tier 1-4 from Doc 5) — auto-approve, human review, senior sign-off
- Models deployment workflows — dev → test → UAT → production with approval gates at each transition
- Defines triage processes for support tickets — classify, route, escalate paths
- Currently being used to validate Claude's designs and is already identifying gaps in process

**Why it matters:** BPMN is the backbone of process validation. It's already working for gap detection. Everything else layers on top of it.

**Architecture decision:** BPMN-based workflow for knowledge artifacts — ✓ DECIDED. Concept captured, detail deferred to this area.

**Current status:** Being used informally for design validation. Needs formalisation — define the standard BPMN processes that every design must pass through.

**Nimbus examples:**
- Implementation pipeline: requirements → architecture → configuration → testing → release → documentation (from Doc 2)
- Knowledge ingestion: receive → classify tier → validate (auto or human) → embed → store → make searchable
- Defect triage: report → AI classify → check duplicates → route → resolve → learn

**Open questions for focused session:**
- [ ] What standard BPMN processes should exist for the platform?
- [ ] How does BPMN validation run — manually triggered or automatic on every design?
- [ ] What tooling? Camunda, custom engine, or lightweight notation-only approach?
- [ ] How do BPMN processes get versioned as the platform evolves?

---

### Layer 3: DMN (Decision Model & Notation)

**What it does:** Handles decision logic within processes. Where BPMN says "at this point a decision is made," DMN provides the decision table that codifies "given inputs X and Y, the correct output is Z." DMN is the companion specification to BPMN — they were literally designed to work together.

**How it's applied in nimbus:**
- Award rule validation: given an employee type + work pattern + EA clause, what rule configuration is correct? Decision tables codify this.
- Configuration validation: given a client's requirements, which time2work settings should be applied? Decision tables capture the mapping.
- Triage routing: given issue type + severity + client tier, where does it route? Decision table, not hardcoded logic.
- Quality gates: given test results + coverage level + confidence score, does the build pass? Decision table.

**Why it matters:** Without DMN, decision logic lives in Claude's head or in ad-hoc code. With DMN, it's explicit, testable, auditable, and versioned. You can look at a decision table and verify the logic without reading code. When Award rules change, you update the decision table and the system automatically applies the new logic.

**Relationship to BPMN:** BPMN models reference DMN decision tables at decision points. The BPMN process says "evaluate Award applicability here" and DMN provides the actual logic table. They're linked, not separate.

**Nimbus examples:**
- Award applicability: employee type × employment basis × location → applicable Award/EA (decision table)
- Penalty rate selection: day of week × time of day × employee classification → penalty rate multiplier (decision table)
- Tier classification for knowledge: source type × domain × confidence level → validation tier (decision table matching Doc 5 Tier 1-4)
- Escalation rules: issue age × severity × failed auto-resolution attempts → escalation level (decision table)

**Open questions for focused session:**
- [ ] What are the highest-value decision tables to build first?
- [ ] How do decision tables get authored — Claude drafts, human validates?
- [ ] What format? Standard DMN XML, simplified JSON tables, or database-stored?
- [ ] How do decision tables version when Award rules change?
- [ ] Should decision tables be part of the Knowledge Engine or separate?

---

### Layer 4: Ontology / Knowledge Graph Patterns

**What it does:** Validates completeness and relationships. Maps the dependencies between concepts, entities, and knowledge items. When something changes, the ontology tells you what else is affected. When a design is proposed, the ontology checks whether all required dependencies have been addressed.

**How it's applied in nimbus:**
- Impact analysis: "If I change this Award rule type, what configurations, test scenarios, and documentation are affected?" The ontology knows the dependency chain.
- Completeness checking: "This implementation design covers modules A and B but module C depends on both — has C been addressed?" The ontology flags the gap.
- Knowledge relationship validation: "This support resolution references a configuration pattern that was deprecated last month." The ontology catches the stale reference.
- Cross-domain awareness: "This client configuration change in the Award context affects pay calculation in the compliance context." The ontology knows the cross-boundary dependency.

**Why it matters:** BPMN checks process flow. DMN checks decision logic. But neither checks whether the *right things* are being processed. The ontology layer answers "is anything missing?" and "what else is affected?" — the questions that catch gaps before they become production issues.

**Relationship to existing Knowledge Engine:** Doc 5 already defines knowledge relations (extends, contradicts, supports) and a knowledge taxonomy. The ontology layer formalises these into a validation mechanism — not just "these items are related" but "if you change this item, these other items MUST be reviewed."

**Nimbus examples:**
- Award rule X uses rule type Y with parameters Z₁, Z₂, Z₃ → changing rule type Y means all configurations using it must be re-validated
- Client Monash has EA₁ and EA₂ → EA₁ references casual academic rates → casual academic rates also appear in leave calculations → changing rates triggers re-validation of both
- time2work API endpoint /employees changed response shape → all connectors, tests, and documentation referencing that endpoint need updating → ontology identifies all of them

**Relationship to DDD:** DDD defines boundaries. Ontology maps relationships within and across those boundaries. DDD says "these are separate contexts." Ontology says "but they share this dependency, so changes here affect there."

**Open questions for focused session:**
- [ ] How lightweight can we make this? Full OWL ontology vs simple dependency graph in PostgreSQL?
- [ ] Does this extend the existing knowledge_relations table or need new infrastructure?
- [ ] How are dependencies captured — manually, inferred by Claude, or extracted from system metadata?
- [ ] What's the validation trigger — on every change, on demand, or at stage gates?

---

### Layer 5: Event Sourcing / Lifecycle State Management

**What it does:** Maintains the complete history of every decision, change, and state transition across the entire lifecycle of the application. Nothing is overwritten — every change is an immutable event appended to the log. You can reconstruct the state at any point in time. You can answer "why is this configured this way?" by tracing the event chain.

**How it's applied in nimbus:**
- Architecture Decision Records (ADRs) are events — "on this date, we decided X because of Y, superseding previous decision Z"
- Configuration changes are events — "Monash Award rule updated from config A to config B, triggered by EA amendment, approved by consultant X"
- Knowledge changes are events — "Knowledge item updated, previous version preserved, change reason recorded"
- Design validations are events — "BPMN validation run on design X, gaps found: [list], resolved by: [actions]"
- Session state is events — "Claude Code session started, context loaded, tasks assigned, work completed, session summary recorded"

**Why it matters:** This is the system's memory across years. Without event sourcing, you have current state but no history. When John comes back in 18 months and asks "why did we configure Monash this way?" the event log has the complete answer. When a new consultant picks up an existing client, the event history tells them everything — not just what is, but why.

**Critical for the platform vision:** The platform must maintain state across multiple sessions, multiple code changes, multiple team members, across the entire lifecycle of an application. Event sourcing is how you do that without losing anything.

**Relationship to existing systems:** Doc 4 already defines audit_log table. Doc 5 has rag_usage_log. These are event stores already — they just need to be recognised as part of a deliberate event sourcing pattern and extended to cover all state changes, not just queries and agent actions.

**Nimbus examples:**
- Monash implementation event chain: requirements gathered (event) → architecture approved (event) → config generated (event) → test scenario X passed (event) → test scenario Y failed (event) → config adjusted (event) → all tests passed (event) → UAT approved (event) → deployed to production (event)
- Award rule change chain: legislation changed (event) → knowledge item flagged for review (event) → human validated new interpretation (event) → affected configurations identified via ontology (event) → re-validation triggered (event) → updated configs deployed (event)
- Cross-session state: Claude Code session 1 built module A (events) → session 2 built module B with dependency on A (events) → session 47 six months later modifies A → event history shows B depends on A → re-validation triggered

**Open questions for focused session:**
- [ ] Event store technology — extend existing PostgreSQL audit_log or dedicated event store?
- [ ] Event schema — what fields are mandatory for every event?
- [ ] Retention policy — keep everything forever or archive after threshold?
- [ ] How does event sourcing interact with the vault's git history? Complementary or redundant?
- [ ] State reconstruction — do we need point-in-time snapshots or is replaying events sufficient?

---

## How the Layers Interact

The five layers are not independent — they form a validation pipeline:

1. **A change is proposed** (new design, configuration update, knowledge addition)
2. **DDD checks boundaries** — does this change respect domain contexts? Is it scoped correctly?
3. **BPMN validates the process** — does the workflow for implementing this change have all steps? Are stage gates defined?
4. **DMN evaluates decisions** — at each decision point in the process, do the decision tables produce correct outputs for this change?
5. **Ontology checks impact** — what other entities depend on what's changing? Are they all addressed?
6. **Event sourcing records everything** — the change, the validation results, the approvals, the deployment — all as immutable events

If any layer flags an issue, it feeds back before proceeding. BPMN identifies a gap → ontology identifies what's missing → DMN determines the correct resolution → BPMN re-validates the updated design → event sourcing records the iteration.

## Relationship to Other Areas

| Area | How Area 9 Connects |
|------|-------------------|
| Knowledge Engine (1) | Ontology layer extends knowledge relations. DMN tables may be stored as knowledge items. Event sourcing extends audit logging. |
| Integration Hub (2) | BPMN defines connector deployment and validation workflows. DDD defines integration boundaries. |
| PS Accelerator (3) | BPMN validates implementation pipeline. DMN codifies configuration decisions. Event sourcing tracks full implementation history. |
| Quality & Compliance (4) | DMN codifies Award rule logic for test scenario generation. Ontology identifies test coverage gaps. |
| Support & Defect Intel (5) | DMN codifies triage routing. BPMN defines escalation workflows. Ontology identifies cross-client impact. |
| Project Governance (6) | Event sourcing provides the data for project health dashboards. BPMN defines governance workflows. |
| Orchestration & Infra (7) | Event sourcing extends the audit_log. BPMN defines agent coordination workflows. DDD defines agent scope boundaries. |
| Commercial (8) | BPMN defines client onboarding and engagement workflows. |

## Implementation Approach

This area is cross-cutting — it doesn't get built in one phase. Instead:

- **Phase 0-1:** Formalise BPMN processes for knowledge validation and design review. Lightweight only.
- **Phase 1-2:** Add DMN decision tables for highest-value decisions (Award rule validation, triage routing). Extend knowledge_relations for basic ontology.
- **Phase 2-3:** Event sourcing pattern applied to implementation pipeline (Monash POC generates the event chain). DDD boundaries formalised.
- **Phase 3+:** Full ontology-based impact analysis. Decision tables for all major decision points. Event sourcing across all platform operations.

## Focused Session Objective

The focused chat for this area should:
1. Validate or adjust this five-layer model
2. Prioritise which layers to build first for maximum value with minimum overhead
3. Define the concrete BPMN processes the platform needs
4. Identify the first 5-10 decision tables worth building
5. Decide how lightweight vs formal the ontology needs to be
6. Define the event schema for event sourcing
7. Determine tooling choices for each layer

---
*Source: Conversation 2026-02-23 (design systems analysis) | Master Tracker Area 9 | Created: 2026-02-23*
