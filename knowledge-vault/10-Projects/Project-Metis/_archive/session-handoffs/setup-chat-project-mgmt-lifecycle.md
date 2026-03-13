---
tags:
  - project/Project-Metis
  - session-handoff
  - area/project-governance
  - area/orchestration-infra
  - topic/feature-lifecycle
  - topic/project-management
created: 2026-02-24
session: pending-chat-project-mgmt
---

# Session Setup: Project Management & Feature Lifecycle

**STATUS: ✓ DONE** — Completed as Chat #9 (Feb 24). Brainstorm file: [[project-governance/brainstorm-project-mgmt-lifecycle]]. All items resolved.

**Chat Topic:** How work flows through the platform — from idea to deployed feature to maintained capability. How this ties into the other areas (orchestration, BPMN enforcement, knowledge engine).

**Area(s):** Project Governance (Area 6) + Orchestration (Area 7) — cross-cutting

**Level:** Brainstorm — capture ideas, flag gaps, don't spec implementation

## Why This Matters for Consolidation

This area is the connective tissue. It answers "how does a piece of work move through the system?" Every other area is a capability; this area is the flow that connects them. Without it, the BPMN validation pass won't have a process to validate against.

## Read These First

1. `project-governance/README.md` — existing brainstorm on dashboards, health scoring, status reports
2. `orchestration-infra/README.md` — agent orchestration, task queue, shared state
3. `orchestration-infra/agent-conventions.md` — Rule 1 (decompose before building), work items
4. `orchestration-infra/phase-0-task-list.md` — how Phase 0 work is structured (example of feature lifecycle in practice)
5. `bpmn-sop-enforcement/README.md` — validation stack, stage gates, enforcement tiers
6. `decisions/README.md` — three partially resolved decisions: project mgmt approach, feature lifecycle, audit & debuggability
7. `system-product-definition.md` — generic platform framing

## What's Already Captured (Partially Resolved)

From the decisions tracker:

### Project Management Approach (◐ PARTIAL)
- Git-native + Jira/DevOps hybrid. Keep PM layer agnostic.
- Git likely core infrastructure (code, configs, ADRs, specs all version-controlled)
- Evaluate CCPM (Critical Chain Project Management) pattern
- John mentioned potential to replace Jira with Claude Code's Git integration for internal dev
- But keep the PM layer agnostic — don't lock to any single tool

### Feature Lifecycle (◐ PARTIAL)
- Track: idea → design → code → test → deploy → maintain
- Belongs in Project Governance area
- Dashboard view for at-a-glance status
- No design exists yet

### Audit & Debuggability (◐ PARTIAL)
- Entire system must be logged, auditable, debuggable
- Decisions as first-class objects
- Full trace chain for AI-generated answers
- Baked into Orchestration area — audit_log table exists in schema
- But the "decisions as first-class objects" concept isn't designed

## What's NOT Designed (The Gaps)

### 1. Feature Lifecycle Flow
What are the actual stages a piece of work goes through?

Initial brainstorm from previous sessions:
```
Idea → Design → Code → Test → Deploy → Maintain
```

But this is too simple. Questions:
- Where do requirements fit? Before design or part of it?
- Where does review happen? Between code and test? Between test and deploy?
- Where do human approval gates sit? (Ties into BPMN enforcement)
- What about rejected/parked/deferred work? Not everything moves forward linearly.
- How does this map to the work_items table status: pending → assigned → in_progress → completed → failed → blocked?
- Is this the same lifecycle for all work types? (Feature, bug fix, knowledge ingestion, documentation, client onboarding)

### 2. Work Types
Not all work is the same. The lifecycle may differ:

| Work Type | Example | Different Because |
|-----------|---------|------------------|
| Feature | New API endpoint | Full lifecycle: design → code → test → deploy |
| Bug fix | Auth token expiry | May skip design, faster cycle |
| Knowledge ingestion | Ingest new API spec | No code, different validation (knowledge tiers) |
| Documentation | Generate release notes | AI-generated, human-reviewed, different output |
| Client onboarding | Set up new org | Configuration, not code. Deployment = data setup |
| Enhancement | Client requests new report | May touch multiple areas |

Do they all share one lifecycle, or do we need type-specific flows?

### 3. Decisions as First-Class Objects
From the decisions tracker — this was flagged but not designed.

Current state: decisions are tracked in a markdown file in the vault (decisions/README.md). This works for planning but doesn't scale to runtime.

Questions:
- Should decisions be a database table? (id, title, status, outcome, made_by, made_at, context, related_work_items)
- Should every AI-generated output link back to the decisions that shaped it?
- Is this part of the audit trail, or separate?
- How does this tie into the BPMN validation stack? (decisions feed into DMN decision tables?)

### 4. Dashboard / Status View
Project governance README mentions dashboards but doesn't design them.

Questions:
- What's the simplest useful view? (List of work items by status? Kanban board? Timeline?)
- Does this need a web UI, or is a CLI/API query sufficient for Phase 0-1?
- What data sources feed it? (work_items table, sessions table, audit_log, external Jira/Salesforce?)
- Is this the "single pane of glass" for John to see what's happening across all agents?

### 5. How This Ties Into Other Areas

This is the critical part — the lifecycle flow should map cleanly to:

| Area | Lifecycle Stage | How It Connects |
|------|----------------|----------------|
| Knowledge Engine (Area 1) | All stages | Knowledge retrieval informs every stage |
| Integration Hub (Area 2) | Code, Deploy | Connectors used for deployment and data sync |
| Delivery Accelerator (Area 3) | Requirements → Deploy | The customer-facing lifecycle IS the delivery pipeline |
| Quality & Compliance (Area 4) | Test | Test stage feeds into quality validation |
| Support & Defect Intel (Area 5) | Maintain | Post-deployment issues feed back as new work |
| Orchestration (Area 7) | All stages | Agent coordination, session management, work items |
| BPMN Enforcement (Area 9) | Stage gates | Validation at each transition |

The feature lifecycle is the THREAD that runs through all 9 areas. If this isn't designed well, the consolidation pass won't have a clear picture of how they connect.

### 6. CCPM Evaluation
Critical Chain Project Management was mentioned as something to evaluate. Questions:
- Is CCPM relevant for AI agent coordination, or is it a human project management methodology?
- Does the concept of "buffer management" apply to AI work? (probably not directly)
- Or was this more about how John manages the overall platform build, not how agents manage individual tasks?

## Claude Family Lessons to Discuss

- **Work items are the weakest link.** Tasks go stale, don't get closed. This is a known problem. Whatever lifecycle design we build needs to handle stale work gracefully.
- **Session summaries on end.** The pattern of writing a summary when a session ends is valuable — it captures what was done. But it doesn't capture what SHOULD be done next. The lifecycle needs a "next action" mechanism.
- **Cross-session continuity is hard.** Agent A does work, session ends. Agent B starts — how does it know where A left off? The lifecycle flow needs explicit handoff points.

## Outcome Expected

A brainstorm vault file covering feature lifecycle design and project management approach. Should answer: what stages work goes through, how different work types are handled, how this connects to the other 8 areas, where human gates sit, and how status is visible. Decisions-as-objects concept either designed or explicitly deferred with reasoning.

---
*Setup doc for next chat session — created 2026-02-24*
