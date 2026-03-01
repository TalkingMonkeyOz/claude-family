---
tags:
  - project/Project-Metis
  - area/project-governance
  - scope/system
  - type/brainstorm
  - topic/pm-lifecycle
  - topic/client-timelines
  - topic/issue-threads
  - phase/first-pass
projects:
  - Project-Metis
created: 2026-02-28
synced: false
status: VALIDATED
---

# GAP-17: PM Lifecycle & Client Timeline Management — First Pass

> **Source:** FB157. Identified during gap review as missing from the 10-feature catalogue.
> **Scope:** system (generic platform concern — how any customer deployment manages client engagements)
> **Builds on:** Area 5 (Support & Defect Intelligence) handles individual issue management. This layer adds engagement-level project management on top.

---

## 1. The Problem

The platform's 10 features are AI-pipeline oriented — they cover knowledge ingestion, config generation, testing, deployment, documentation. None address the human project management layer: planning work across a client engagement, tracking where things actually are, dealing with real-world delays (client UAT cycles, approvals, change advisory boards, people on leave).

**Real-world pain points (from nimbus/Monash experience):**

- Project plan exists in Salesforce Lightning but drifts from reality as work progresses — becomes unrecognisable
- PM is stretched across multiple projects, can't keep plans current manually
- Defects change the nature of work — not just "behind schedule" but "scope has fundamentally changed" and the plan never absorbs this
- Disconnect between dev, PS, and client on timeframes and decisions needed
- Dual Jira tracking: client Jira + nimbus Jira, keeping them in sync, lifecycle tracking across both
- One client issue spawns multiple internal tickets (support ticket → backlog ticket → dev ticket) — hard to see the full picture
- CRs, defects, design specs, release dates, risk registers all tracked separately with no unified view

## 2. Key Design Constraint

**Cannot assume client Jira access.** Some clients (like Monash) give access. Others won't. The system must work in two modes:

- **Mode A: Direct integration** — system watches client Jira, auto-detects new issues, tracks sync status
- **Mode B: No client access** — issues arrive via meetings (Granola), email, verbal report, manual entry. System captures from whatever source is available.

The design must not depend on Mode A. Mode A is a bonus when available.

## 3. Five Capabilities (What GAP-17 Adds)

### 3.1 Issue Threads

One client issue = one thread. The thread links every ticket, in every system, that relates to that original issue.

**Example lifecycle:**
- Client reports "payroll calculation wrong for casual academics"
- Thread created (from Granola meeting notes, client Jira, email, or manual entry)
- Support ticket raised in nimbus Jira (linked to thread)
- Support verifies, closes their ticket, opens backlog ticket (linked to thread)
- Dev ticket raised from backlog (linked to thread)
- Config change ticket if needed (linked to thread)
- Test scenario ticket (linked to thread)

**Thread knows:** the issue isn't resolved until ALL child items are resolved and the fix is deployed to the client. Not just "dev closed their ticket."

**AI-assisted linking:** When a new ticket mentions related terms, the knowledge engine suggests "this looks related to thread X." But thread structure is explicit, not pure AI inference. Structured threads, AI-assisted linking, human confirmation.

### 3.2 Timeline Intelligence

A defect fix isn't just "dev time." The real elapsed time includes:

- Design time (if needed)
- Build time
- Test time
- Deploy to dev environment
- Deploy to UAT environment
- Client UAT cycle (days to weeks — human time, not AI time)
- Deploy to production
- Client verification

The system must understand that the platform can execute fast but the real world doesn't. Client UAT might take 2 weeks. Change advisory board meets monthly. Release windows are fixed.

**What the system does:**
- Tracks realistic elapsed time per stage, not just effort
- Learns from historical data — "Monash UAT typically takes 10 business days"
- Surfaces realistic delivery dates based on actual pipeline, not optimistic estimates
- Flags when a target date is unrealistic given the remaining pipeline stages

### 3.3 Proactive PM Alerts

For a PM stretched across multiple projects, the system actively surfaces what needs attention rather than requiring the PM to go looking.

**Alert types:**
- "5 defects stuck in dev for more than a week"
- "This CR has no design spec but is scheduled for next sprint"
- "Client Jira has 3 items we haven't raised internally yet" (Mode A only)
- "Release date is in 2 weeks but 4 items aren't through UAT"
- "Thread X has been open for 30 days with no progress"
- "Plan says you're in deployment phase, but you have 15 open defects"

**Not vanity metrics.** Every alert has a call to action + suggestion. Not "you have 5 stale items" but "these 5 items are stale — here's what each one needs next."

### 3.4 Plan vs Reality Reconciliation

The project plan (in Salesforce Lightning or wherever) says the project is at stage X. The actual work state (threads, tickets, deployments, test results) says it's at stage Y. The system reconciles these.

**What the system does:**
- Compares planned milestones against actual completion state
- Identifies where plan assumptions have been invalidated (e.g., "plan assumed 5 defects, you have 23")
- Suggests plan adjustments based on current reality
- Generates honest status reports from actual data, not manual updates

### 3.5 Cross-Workstream View

Per client engagement, one view that shows:
- All active threads (with status rollup)
- Change requests and their status
- Design documents and their completeness
- Release schedule and readiness
- Risk register items
- Upcoming dates and decisions needed

This is the "where are we actually at with Monash" view that doesn't exist today without manually assembling it.

## 4. Relationship to Existing Areas

| Area | Relationship |
|------|-------------|
| **Area 5: Support & Defect Intel** | Handles individual issue intelligence (intake, triage, duplicate detection, resolution). GAP-17 builds the engagement-level view on top. |
| **Area 6: Project Governance** | GAP-17 lives here. Dashboards, status reports, health scoring. |
| **Area 3: Delivery Accelerator** | Pipeline stages (config, test, deploy) feed into timeline intelligence. |
| **Area 2: Integration Hub** | Jira connectors (both modes), Salesforce Lightning integration, Granola for meeting capture. |
| **Area 9: BPMN/SOP** | Deployment approval workflows, release gates feed into timeline tracking. |

## 5. Salesforce Lightning Relationship

nimbus currently uses Salesforce Lightning for project tracking and timesheeting. Options (not decided):

1. **Bounce off it** — read project data from SF, present it alongside AI-derived insights, but don't write back
2. **Integrate with it** — bidirectional sync, AI updates SF project status, reads SF timesheets
3. **Partially control it** — AI manages certain SF objects (project milestones, status) while humans manage others
4. **Eventually replace it** — if the platform becomes the better PM tool, SF becomes just CRM/billing

**Note:** John mentioned he's bad at timesheeting. If the system can improve tracking via multiple ingestion points (meetings via Granola, commits, Jira activity, calendar) rather than manual timesheet entry, that's a quick win.

**Decision: DEFERRED** — needs more thought on what's realistic for Phase 1 vs later.

## 6. Open Questions

- [x] Does this become Feature 11, or fold into F6/F8? → **PARKED.** Deepens Project Governance. Exact feature slot decided during Phase 5/6 with user story modelling.
- [x] What's the minimum viable thread concept? → **Parent-child ticket grouping.** Full lifecycle tracking deferred.
- [x] How does plan vs reality work when plan is in SF, reality in Jira? → **Platform IS the source of truth.** SF is a connector, not a dependency. No reconciliation layer.
- [x] Risk registers — separate artifact or derived view? → **Derived view from real data** (stale threads, missed commitments, mounting defects). Generate formal doc if governance requires it.
- [x] Personas (client design artifacts) — where do they live? → **Client artifact type in artifact registry.** Tracked per client (version, status, linked to work items). Part of broader deliverable tracking: persona specs, config specs, integration specs, test plans.
- [x] What does PM need in Phase 1 vs aspirational? → **MVP: simple threads (parent-child), basic client satisfaction alerts, per-client view, artifact registry.** Phase 2+: timeline intelligence, full lifecycle threads, Granola capture, plan vs reality, derived risk, confidence-based auto-linking. **Design data model wide, build features narrow.**

---

## 7. Key Design Decisions (Session 8 Validation)

- **Auto-linking:** High confidence → auto-link. Doubtful → review queue service. Human confirms edge cases only.
- **Thread resolution:** Human decision, not mechanical "all children closed." System surfaces attention, human decides when done.
- **Proactive alerts reframed:** Client satisfaction risk detection, NOT internal dev metrics. Key alerts: client waiting on response, no update in X days, meeting items not ticketed, deployments not confirmed.
- **Plan vs reality:** Platform IS the realistic status view derived from actual work. Not reconciliation with Salesforce.
- **Cross-workstream view:** Presentation layer assembling Caps 1-4 per client. Not a separate capability.
- **Risk registers:** Derived view, not manually maintained artifact.
- **Personas:** Client artifact type in artifact registry, referenceable from threads and tickets.
- **Core ethos:** Every report/dashboard/alert must provide information for action. No vanity metrics. Everything adds value to the company.
- **Expandability:** Design data model for full vision, build features narrow for MVP. No data layer shortcuts.

---

*First pass: 2026-02-28 | Validated: 2026-02-28 Session 8 — conversational review with John | Status: VALIDATED | FB157 RESOLVED*
