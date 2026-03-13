---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - type/session-handoff
  - scope/system
projects:
  - Project-Metis
created: 2026-02-23
session: orchestration-build-specs-continuation
previous-session: 2026-02-23-stocktake-reframe
---

# Session Handoff: Orchestration Build Specs (Continuation)

> **For the next Claude picking this up:** Read this file first. It tells you what happened, what was decided, and what still needs doing. The vault files are the source of truth — read the relevant area folders before starting new work.

## Session Context

- **Date:** February 23, 2026 (evening session)
- **Chat:** Orchestration Build Specs (Chat #8 from Master Tracker)
- **Previous sessions same day:** Stocktake/Reframe, BPMN/SOP Enforcement, Knowledge Engine Deep Dive
- **This was the 4th focused session of the day — context limits were hit**

## What This Session Covered

### 1. Orchestration Build Specs Review
The orchestration-infra area already had substantial content from the Feb 19 session (8 vault files). This session was intended to deepen the design and capture anything missing for Phase 0 build readiness.

Most of the orchestration foundation decisions were already locked:
- API key provisioning: personal Anthropic account, $200/month cap ✓
- Azure environment: B2ms VM + PostgreSQL Flexible, ~$140/month ✓
- Git repo: Azure DevOps (nimbus owns it) ✓
- Auth: JWT + swappable middleware, SSO eventually ✓
- Agent Teams: single-agent Phase 0, teams from Phase 1 ✓
- Carry-forward: patterns from Claude Family, rebuild fresh ✓
- Review workflow: CI auto + Agent Review + human spot-check ✓
- Handoff: vault + CLAUDE.md + task spec files ✓

### 2. Agent Compliance & Drift Management (NEW)
The session went deep into a topic that emerged from the orchestration discussion: how to make AI agents follow instructions consistently over time. This was informed by:

- **Rath 2026 paper** (arXiv:2601.04170): "Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over Extended Interactions"
- **6+ months of Claude Family experience** with protocol erosion and compression

Key outputs:
- Five-layer enforcement architecture designed (injection, reinjection, task persistence, sub-agent isolation, BPMN gates)
- Compliance metrics framework with 7 measurable metrics
- Semi-automated compliance checking (automated + Haiku-as-judge + periodic human review)
- Protocol anti-compression rule (flag >10% word count reduction)
- Three new DB tables: protocol_versions, compliance_checks, compliance_summaries
- Full document produced: `nimbus_agent_compliance_drift_management.docx` (project files)
- Vault file produced: `orchestration-infra/agent-compliance-drift-management.md`

### 3. What Got Lost to Compaction
The session hit context limits and compacted. The agent drift content was captured (both as .docx and memory graph entries), but the session handoff was NOT written before the conversation ended. This file fills that gap.

## Decisions Made This Session

| Decision | Outcome | Status |
|----------|---------|--------|
| Agent drift is a real design concern | Five-layer enforcement architecture | ✓ DECIDED |
| Protocol modification rights | Human-only for now; agents can propose, not activate | ✓ DECIDED |
| CLAUDE.md reinjection frequency | Start at every 15 interactions, tune based on data | ✓ DECIDED (tunable) |
| Haiku compliance judge sampling | 10% of sessions initially | ✓ DECIDED (adjustable) |
| Native vs custom tasks | Try native persistent tasks, revert if no improvement after 4 weeks | ✓ DECIDED (experiment) |
| Compliance dashboard timing | Phase 3 — collect data from Phase 0-2, visualise later | ✓ DECIDED |
| Drift management status | EXPERIMENTAL — measure don't assume | ✓ DECIDED |

## What's Still Open for Orchestration

- [ ] Detailed Phase 0 task list for Claude Code handoff (what gets built in week 1)
- [ ] CLAUDE.md template draft (the conventions file for the repo)
- [ ] CI/CD pipeline specification (what runs, what tools, what checks)
- [ ] Database migration strategy (how schema evolves over time)
- [ ] Agent conventions as formal rules (doc 4 §5.4 into enforceable format)
- [ ] Monitoring and alerting design (what gets watched, what triggers alerts)

## What Changed in the Vault This Session

- `orchestration-infra/agent-compliance-drift-management.md` — NEW
- `session-handoffs/2026-02-23-orchestration-build-specs.md` — THIS FILE
- Memory graph updated with: Five-Layer Enforcement Architecture, Agent Drift Research, Protocol Anti-Compression Rule, Compliance Metrics Framework

## Next Recommended Session

Either:
1. **Constrained Deployment Implementation** (Chat #3) — gets closest to buildable Monash POC
2. **Integration Hub Connectors** (Chat #4) — Phase 1 critical, connector specs needed

## Irony Note

The session about agent drift hit the exact problem it was describing — context compaction caused loss of session state. The handoff wasn't written before the conversation ended. This is exhibit A for why persistent state mechanisms matter.

---
*Session end: Feb 23, 2026 | Reconstructed: Feb 24, 2026*
