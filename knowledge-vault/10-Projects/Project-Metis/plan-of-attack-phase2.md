---
projects:
  - Project-Metis
tags:
  - project/metis
  - type/plan
---

> **⚠️ Design Reference Only** — Execution state has moved to the build board (`get_build_board("project-metis")`). For current decisions, use `recall_entities("metis decision")`. This document captures the original design rationale.

# Phase 2: First Customer Stream

**Goal:** Prove that METIS can run one complete customer workflow end-to-end on real data, getting smarter with each interaction.

Back: [[plan-of-attack-phase1|Phase 1]] | Master: [[plan-of-attack|Plan of Attack]]

---

## Entry Criteria

- Phase 1 dog-food gate passed
- First customer contract signed (commercial context)
- Customer connectors accessible (API credentials confirmed)
- Customer knowledge available for ingestion (product docs, process docs, or equivalent)
- System blockers resolved (platform-level) — customer-specific blockers tracked separately (D13)

---

## Stream Definition

Phase 2 is not "build all features." It is one stream — one end-to-end workflow — proven on real data with a real customer.

**Lead example:** Assisted defect tracking with Jira. An AI that knows the customer's product, assists the team through defect capture, triage, deduplication, and resolution — and gets smarter with each ticket.

**Generic principle (D05):** The stream is described generically. nimbus/Monash is the lead example but not the only valid path. Any knowledge-intensive customer workflow qualifies.

---

## Deliverables

| Deliverable | Feature Area | Bounded Context | Depends On |
|-------------|-------------|----------------|------------|
| Customer onboarding flow (P9) | F120, F119 | Tenant & Scope, Knowledge Store | Phase 1 complete |
| Product knowledge ingestion | F119 | Knowledge Store | P9 step 1 |
| Domain capture (customer-specific) | F119 | Knowledge Store | P9 step 2 |
| Customer tool integration | F120 | Integration | P9 step 3 |
| Constrained deployment (customer-specific) | F128 | Commercial | P9 step 4 |
| Engagement creation (P4) | F124 | Delivery Pipeline, Tenant & Scope | Onboarding complete |
| Jira connector (read + write) | F120 | Integration | Connector interface (Phase 1) |
| IssueThread aggregate + schema | F123 | Defect Intelligence | Engagement created |
| Defect capture + AI structuring | F123 | Defect Intelligence | IssueThread |
| Semantic dedup (suggest-and-confirm) | F123 | Defect Intelligence | IssueThread + Embedding |
| Cross-client escalation guardrail | F123 | Defect Intelligence | IssueThread |
| Delivery pipeline basics (P5) | F121 | Delivery Pipeline | Engagement created |
| Pipeline gate logic (accept-and-close / accept-and-track) | F121, F122 | Delivery Pipeline, Test Assets | Delivery pipeline |
| Auto-generated test scenarios | F122 | Test Assets | Config items |
| Human first-use review flow for test scenarios | F122 | Test Assets | Test scenarios |
| Regression baseline + diff | F122 | Test Assets | Test runs |
| METIS-as-source-of-truth Jira sync | F123 | Defect Intelligence | Jira connector |
| Knowledge promotion flow (suggest-and-confirm) | F119 | Knowledge Store | Engagements running |
| Session handoff between agents | F125 | Agent Runtime | Agent orchestration |
| Supervisor + sub-agent structure (P7) | F125 | Agent Runtime | Phase 1 agent runtime |
| Configurable sub-agent cap (default 4) | F125 | Agent Runtime | Supervisor pattern |
| Project health data (raw) | F124 | Work Management | All of above |

---

## Build Order

### Step 1 — Customer onboarding (P9)

Run P9 in the correct sequence. Steps 2 and 3 can run in parallel (BC-6):

```
Step 1: Product knowledge ingestion (sequential — must complete before steps 2+3)
  └─ Ingest product docs, API specs, process docs via Phase 1 pipeline

Steps 2+3 (parallel):
  ├─ Step 2: Domain capture
  │    └─ Scope customer-specific knowledge to engagement
  └─ Step 3: Tool integration
       └─ Configure connectors, verify health checks

Step 4: Deployment configuration
  └─ Constrained deployment (L1/L2/L3) + 5-question validation before publish

Step 5: Validation
  └─ System-level smoke tests pass

Step 6: First engagement created (triggers P4)
```

**Why this order:** Knowledge must exist before the first engagement uses it. Connector health must be confirmed before the deployment is published.

---

### Step 2 — Engagement lifecycle (P4)

Once onboarding completes, create the first engagement record. This triggers:
- Tenant & Scope: engagement record with scope chain
- Delivery Pipeline: pipeline instantiated from template
- Knowledge Store: engagement-scoped knowledge scope created

**P4 gateways to implement:**
- G1: connector configured? Block if not.
- G2: knowledge scope populated? Queue product ingestion if not.
- G3: delivery template exists? Clone or build.

---

### Step 3 — Jira connector

Full read/write Jira connector. METIS is source of truth; Jira is synced to, not from. Sync direction: METIS creates/updates IssueThread → pushes to Jira. Jira webhooks pull changes back for awareness only.

Wire P6 (Connector Sync) for Jira. Schema change detection active: if Jira API schema changes, flag affected ingested data for review (BC-8).

---

### Step 4 — Defect Intelligence domain (IssueThread)

Implement the `Defect Intelligence` bounded context:

- `IssueThread` aggregate root with `Defect`, `DefectPattern`, `ReplicationScenario`, `JiraIssue`
- Defect capture: natural language → AI structures into steps/expected/actual/severity
- Semantic dedup: embedding-based duplicate check → suggest-and-confirm pattern (BC-3). System proposes a match, human confirms. No auto-merge.
- Cross-client escalation: system suggests when pattern appears cross-client, human decides (BC-3). Agents cannot auto-escalate.
- IssueThread resolution invariant: not resolved until ALL children closed AND fix deployed AND verified.

---

### Step 5 — Delivery pipeline basics (P5)

Implement enough of P5 for the first stream. Not all six stages — the stages needed for the chosen stream:

- Stage gate logic: agents cannot proceed past a gate without human approval
- Gate logging: every pass/fail recorded with actor and timestamp
- Accept-and-close / accept-and-track: known issues may pass a gate with logged justification (BC-5). Accept-and-close for cosmetic issues. Accept-and-track creates a deferred defect via P8.

---

### Step 6 — Test scenarios and quality checks (P8)

- Auto-generate test scenarios from config items and BPMN process models
- First-use human review: the first time an auto-generated scenario is used, a human must review it (BC-7). Subsequent uses without changes do not require re-review.
- Regression baseline established after first successful test run
- Regression diff on subsequent runs: surface delta, not just pass/fail

---

### Step 7 — Agent orchestration for stream (P7)

Wire the Supervisor + Specialist pattern for the stream's work items:

- Project Controller assigns work items to Supervisor
- Supervisor spawns specialist sub-agents (Design, Coder, Test, Docs as needed)
- Sub-agent cap: configurable (default 4); monitor coordination metrics to detect bottlenecks (BC-4)
- Context compaction recovery: scratchpad write-through (Phase 1) handles agent continuity
- Session handoff: agent assembles handoff package on session end

---

### Step 8 — Knowledge promotion

Once engagements are running and patterns emerge:

- Senior reviewer sees "Promote" action on client-scoped knowledge items
- System generates generalised version (strips client specifics, keeps pattern)
- Suggest-and-confirm: human reviews and approves before promotion (BC-3)
- Promoted items become product-level, available to future engagements
- Original client-scoped item remains (client isolation maintained)

---

## Exit Criteria

- [ ] Customer fully onboarded via P9 (all 7 steps complete)
- [ ] At least one complete defect lifecycle: captured → structured → dedup checked → linked in Jira → resolved → knowledge updated
- [ ] Suggest-and-confirm working for dedup and cross-client escalation (no auto-actions)
- [ ] At least one pipeline gate passed (including at least one accept-and-track case)
- [ ] Auto-generated test scenarios reviewed by human on first use
- [ ] Regression baseline established; regression diff working on second run
- [ ] Jira sync bidirectional; METIS is source of truth (confirmed by resolving a defect and verifying Jira reflects it)
- [ ] Sub-agent cap configurable and coordination metrics being recorded
- [ ] Knowledge promotion: at least one pattern promoted from engagement-level to product-level
- [ ] Dog-food check: has METIS helped improve METIS during this phase?

---

## What Comes Next (Phase 3+)

Phase 3+ is not a distinct phase — it is a repeating cycle:

1. Identify next stream (second workflow, same customer; or first workflow, second customer)
2. Build it using the same pattern: onboard → stream → validate → promote knowledge
3. Each stream builds out more of F121-F124
4. Core platform hardens based on what each stream reveals

The eight behavioural constraints (BC-1 through BC-8) apply to every stream. The dependency chain is the same. What changes is the domain.

---

## Key Risks

| Risk | Mitigation |
|------|------------|
| Customer data quality blocks ingestion | Agree ingestion prerequisites at contract stage; content quality check is P9 step 1 |
| Jira API changes break sync mid-stream | Schema change detection (BC-8) flags this; METIS-as-source-of-truth isolates impact |
| Suggest-and-confirm UX adds friction | Friction is intentional for sensitive operations; measure human confirmation rate, not eliminate it |
| Accept-and-track cases accumulate without resolution | Track deferred defects explicitly; surface in health data (Step 8 deliverable) |
| Sub-agent coordination overhead exceeds cap benefit | Monitor coordination metrics; adjust cap per-deployment via admin centre |
| First stream is too narrow to prove the platform | Choose a stream with enough breadth to exercise knowledge retrieval, agent orchestration, and external sync |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/plan-of-attack-phase2.md
