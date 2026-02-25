---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - topic/user-experience
  - level/2
projects:
  - Project-Metis
created: 2026-02-19
synced: false
---

# User Experience & Productivity Target

> The platform is for nimbus staff — consultants, testers, support — not just John. It needs to make real people faster at their real jobs.

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

## The BHAG

**20%+ productivity increase** across nimbus professional services, support, and testing teams. This is the floor, not the ceiling.

For context (from Doc 1): 10% across a 20-person PS team = 2 FTEs equivalent. 20% = 4 FTEs. Without hiring, onboarding, or salary overhead.

## Who Uses It

Not just John. Real nimbus staff:
- **Consultants** — ask questions about time2work, generate configs, produce documentation
- **Testers** — run test scenarios, validate pay outcomes, regression testing
- **Support staff** — triage tickets, find resolutions, detect patterns
- **Project managers** — project health, status reports, defect summaries
- **Sales/pre-sales** — scoping, competitive intel, demo support

These people are not AI-literate. They are domain experts who want to get their work done faster. The platform must meet them where they are.

## Interface Strategy

### Phase 1-2: Integrate into existing tools (lowest friction)
- **Slack bot/integration** — ask questions, get answers, trigger actions without leaving Slack
- **Jira automation** — AI suggestions appear in Jira comments, defect triage happens inside existing workflow
- **Confluence integration** — AI-generated docs pushed directly to Confluence where people already look

### Phase 2-3: Chat interface
- Web-based chat that knows time2work — like talking to an expert colleague
- Natural language queries, follow-up questions, context-aware responses

### Phase 3+: Web dashboard
- Project health, knowledge search, configuration management
- For power users and management visibility

### Design Principle
**Zero new tools to learn for Phase 1.** AI capability shows up inside tools people already use. Adoption happens because the help is already there, not because someone learned a new system.

## Measuring the BHAG

How do we know if we're hitting 20%+?
- Implementation time per client (weeks → days for key tasks)
- Documentation generation time (hours of manual writing → minutes of review)
- Defect triage time (10+ hours/week admin → automated)
- Support resolution time (first response, escalation rate)
- Test coverage (manual scenarios → automated scenario count)
- New hire ramp time (months → weeks)

These need baselines before we start. Capture current state, then measure improvement.

---
*Source: Decision review session 2026-02-19 | Created: 2026-02-19*
