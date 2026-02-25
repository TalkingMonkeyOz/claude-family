---
tags:
  - project/Project-Metis
  - area/project-governance
  - scope/system
  - level/1
  - phase/3+
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Project Governance

> **Scope:** system (generic platform capability — data sources and health metrics configured per customer)
>
> **Design Principles:**
> - Platform owns its own work tracking — no external dependency for core operations
> - Single view from multiple systems — synthesise, don't duplicate
> - AI generates status reports from data, not from human input
> - BPMN enforcement at lifecycle gates — mechanical, not agent willpower
> - Work items in database for agent-fast queries; artifacts in git for version control

> Dashboards, status reports, health scoring, project management, feature lifecycle. Making the invisible visible.

**Priority:** LOW for dashboards (Phase 3+), HIGH for project management & lifecycle (cross-cutting)
**Parent:** [[Project-Metis/README|Level 0 Map]]

## What This Area Covers

Two sub-areas:

1. **Project Management & Feature Lifecycle** (HIGH — cross-cutting): Custom work tracking, lifecycle tiers, work breakdown hierarchy, git integration. Designed in Chat #9.
2. **Project Health & Dashboards** (LOW — Phase 3+): Real-time health scoring, automated status reports, resource utilisation. Depends on Integration Hub and other areas being in place first.

## Key Decisions (from Chat #9 — Feb 24, 2026)

### Custom Project Management — DECIDED
Platform builds its own work tracking. NOT GitHub Projects, NOT Azure Boards, NOT Jira. Rationale: BPMN enforcement at gates, agent-fast DB queries, no external dependency, full data model control. Integrates with customer tools (Azure DevOps, GitHub, GitLab) as connectors.

### Three Lifecycle Tiers — DECIDED
- **Tier 1 (Free-flowing):** Knowledge queries, low risk, no gates
- **Tier 2 (Structured with sign-off):** Customer deliverables, client approval is the gate, sign-off doc is what you invoice against
- **Tier 3 (Rigid pipeline):** Code and deployment, five-layer validation stack applies

Tier 2 escalates to Tier 3 if work requires code changes.

### Work Breakdown — DECIDED
Initiative → Features → Tasks. Database-backed. Parent rolls up from children. Tasks must be detailed (agents forget context).

### Git Integration — DECIDED
Hybrid: DB for tracking metadata, git for artifacts. Provider-agnostic (Azure DevOps, GitHub, GitLab, self-hosted Gitea). Work item in DB points to git path for spec file.

### Documentation — DECIDED
Platform is source of truth. Generates/maintains docs from system state. Optionally push to Confluence as integration.

> See [[project-governance/brainstorm-project-mgmt-lifecycle|Full brainstorm]] for detail on all decisions.

## Brainstorm Items: Project Health & Dashboards (from Doc 4 WS8)

### Project Health Scoring
- Aggregate signals from multiple systems into a health score
- Salesforce: timesheet data, budget burn rate
- Jira: defect count, velocity, blockers, stale tickets
- Confluence: documentation completeness
- Granola: decisions made, action items outstanding
- Red/amber/green at a glance with drill-down

### Automated Status Reports
- AI generates weekly/fortnightly project status reports
- Pulls data from all connected systems — not manually assembled
- Highlights: what's on track, what's at risk, what needs attention
- Before a project status update, AI scans everything and generates a summary

### Resource Utilisation
- Salesforce timesheet analysis
- Who's working on what, how much capacity exists
- Forecasting: upcoming resource needs based on project pipeline

### Early Warning System
- Proactive alerts when projects drift
- "This project's defect rate is climbing" or "UAT has been delayed 2 weeks"
- Pattern matching: "Projects that look like this at week 4 tend to slip at week 8"

### Management Dashboard (from Doc 1 §4)
| What | Where From | Insight |
|------|-----------|---------|
| Project health | Jira + Salesforce | On track / at risk / blocked |
| Resource utilisation | Salesforce timesheets | Capacity planning |
| Client satisfaction | Support tickets + delivery milestones | Early warning |
| Defect trends | Jira | Quality trajectory |
| Documentation coverage | Confluence + generated docs | Completeness |

## Open Items

### From Chat #9 (continue next session)
- [ ] Work types design — how feature, bug, knowledge ingestion, documentation, client onboarding map to lifecycle stages
- [ ] Decisions-as-objects — database table, link to AI outputs, audit trail
- [ ] Dashboard design — simplest useful view, CLI/API vs web UI
- [ ] CCPM evaluation — relevant for AI agent coordination?
- [ ] Cross-area integration — how PM ties into all 9 areas

### From original brainstorm
- [ ] What does the customer currently use for project visibility?
- [ ] What Salesforce reports/dashboards already exist?
- [ ] What would be the single most valuable dashboard to build first?

## Dependencies

- Project management is **cross-cutting** — every area generates work items
- Dashboards require [[integration-hub/README|Integration Hub]] — all data comes through connectors
- Dashboards require [[support-defect-intel/README|Support & Defect Intelligence]] — defect data feeds health scoring
- Informed by [[ps-accelerator/README|Delivery Accelerator]] — project delivery status
- Enforced by [[bpmn-sop-enforcement/README|BPMN/SOP & Enforcement]] — lifecycle gates

---
*Source: Doc 1 §4 | Doc 4 §3.2 WS8 | Chat #9 (Feb 24 2026) | Created: 2026-02-19 | Updated: 2026-02-24*
