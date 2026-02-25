# Session Handoff: Project Management & Feature Lifecycle (Chat #9)
**Date:** 2026-02-24
**Status:** IN PROGRESS — needs continuation
**Session type:** Brainstorm (Chat #9 from focused chat plan)

## What Was Covered

### Consolidation Attempt (Brief)
- Tried to review vault status against Master Tracker — only got through Area 1 (Knowledge Engine)
- Confirmed Knowledge Engine deep dive (6-category A-F model) is more current than system-product-definition.md (still has 8 knowledge types from Doc 5)
- Master Tracker is out of date (last updated Feb 23, shows all chats NOT STARTED but 3+ completed)
- John redirected to Chat #9 brainstorm

### Lifecycle Design — DECIDED
- **Not two separate lifecycles.** A spectrum of work types hitting different stages depending on what they are. Some work exits after KMS answer, some goes all the way to code deployment.
- **Three rigidity tiers:**
  - **Tier 1 (Free-flowing):** Knowledge queries, consultant questions. Low risk, no gates beyond "is answer good."
  - **Tier 2 (Structured with sign-off):** Customer deliverables, requirements analysis, sign-off docs. Client approval IS the gate. For paid custom work, sign-off doc is what you invoice against — needs traceability.
  - **Tier 3 (Rigid pipeline):** Code and deployment. Five-layer validation stack applies. No skipping tests or deploying without review.
- **Tier 2 escalates to Tier 3** if signed-off work requires code changes.
- **Commercial call** determines paid vs included. Platform needs to know outcome but doesn't make the call.

### Work Breakdown Hierarchy — DECIDED
- Initiative → Features → Tasks
- Each level has status tracking, parent rolls up from children
- Lives in database, not chat context
- Tasks must be detailed — agents forget context and build wrong thing otherwise

### Documentation — DECIDED
- Platform is source of truth, generates/maintains docs from system state
- Optionally push to Confluence as integration for non-platform users

### Project Management Tooling — DECIDED
- **Custom-built.** Platform owns its own work tracking in its database.
- NOT GitHub Projects, NOT Azure Boards, NOT Jira
- Rationale: needs BPMN enforcement at gates, fast local DB queries for agents, no external dependency, full data model control
- Can integrate with customer's existing tools (Azure DevOps, GitHub, GitLab, Jira) as connectors through Integration Hub

### Git Integration — DECIDED
- Hybrid: DB for tracking metadata, git for artifacts (specs, design docs, ADRs, code)
- Work item in DB points to git path for spec file
- Platform is git-provider-agnostic — integrates with whatever customer uses
- Self-hosted option (Gitea/Forgejo) could be embedded as default for standalone deployments

### Pricing Research — COMPLETED
- Azure DevOps: 5 free users, $6/user after. nimbus already uses it.
- GitHub: Free tier, Team $4/user, Enterprise $21/user
- Gitea/Forgejo: Free self-hosted, ~200-300MB RAM
- GitLab CE: Free self-hosted but 8-16GB RAM (heavy)

## What's Still Open (Continue Next Chat)

1. **Work types design** — how feature, bug, knowledge ingestion, documentation, client onboarding map to lifecycle stages
2. **Decisions-as-objects** — database table design, link to AI outputs, part of audit trail
3. **Dashboard design** — simplest useful view, CLI/API vs web UI
4. **CCPM evaluation** — relevant for AI agent coordination or just human PM?
5. **Cross-area integration** — how this ties into all 9 platform areas

## Vault Updates Needed
- [x] Write project-governance/brainstorm-project-mgmt-lifecycle.md with decisions above — DONE Feb 24 (next session)
- [x] Update project-governance/README.md with decisions — DONE Feb 24 (next session)
- [x] Update decisions/README.md with new decisions (custom PM, lifecycle tiers, work breakdown, git-agnostic) — DONE Feb 24 (next session). 6 new resolved, 2 new partial. Total now 41.
- [x] Update Level 0 README chat tracker — Chat #9 marked IN PROGRESS — DONE Feb 24 (next session)
- [ ] Update system-product-definition.md to reflect custom PM decision — DEFERRED (low priority, product def is still draft)

## Process Notes
- Session started as consolidation review, pivoted when John said "lets continue, we have not done any project management lifecycle stuff"
- Context compaction hit mid-session — transcript preserved at /mnt/transcripts/
- John's final direction: "i think its a custom job that we build and we look after all this" — clear decision on custom PM
