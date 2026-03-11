---
tags:
  - project/Project-Metis
  - type/gate-three
  - gate/three
created: 2026-03-11
updated: 2026-03-11
---

# Gate 3 — Material Index

Gate 3 = Build Readiness. 8 deliverables. Formal Gate 3 work has not started (Gate 3 follows Gate 2 completion). This index maps existing material against each deliverable and gives honest completeness estimates.

**Status key:**
- `Not started` — no material relevant to this deliverable exists in current form
- `Partial` — directional decisions exist; formal document not written
- `Near-complete` — decision and content substantially exist; writing/formalisation is the main remaining work
- `Complete (brainstorm)` — brainstorm-level completeness; needs Gate 3 formatting and validation

**Note on plan-of-attack.md:** The existing plan-of-attack.md is explicitly marked UNVALIDATED (rewrite brief written Mar 8, actual rewrite not done). Old numbers have been invalidated. Gate 3 Doc 3 requires a fresh document.

---

## Deliverable Status Table

| # | Deliverable | Status | Completeness | What Exists | What's Missing | Primary Source Files |
|---|-------------|--------|-------------|-------------|----------------|---------------------|
| 1 | Development Standards | Near-complete | ~70% | Decided: TypeScript strict ESM, pnpm, Vitest, ESLint. Naming conventions (6 element types): DB snake_case plural, API endpoints kebab-case REST, TS files camelCase, React components PascalCase, Env vars UPPER_SNAKE_CASE, Agent names PascalCase with role suffix. Data standards: ISO 8601 UTC, UUIDs, JSON camelCase API ↔ snake_case DB at boundary, versioning on mutable records, soft delete, UTF-8. Down-migrations: forward-only. BPMN-First rule for all hooks/workflows. Agent conventions (8 enforceable rules) complete and in final form. CLAUDE.md template production-ready. Code review: three-layer (CI + Agent Review Opus 4.6 + human spot-check). | Formal dev standards document not written (conventions currently spread across CLAUDE.md template, agent-conventions.md, and brainstorm files). API framework (Express vs. Fastify) not selected. Front-end framework TBD. Error code taxonomy not defined. BPMN check_alignment coverage targets not specified. | B2/claude-md-template.md, B2/agent-conventions.md, B2/phase-0-task-list.md, SH/2026-03-08-scope-reframe-actor-map.md, R/plan-of-attack-rewrite-brief.md |
| 2 | Environment Setup / Infrastructure | Partial | ~45% | Decided: Linux/platform-agnostic (no Azure specificity), separate instances per customer. 4 environments named (Local Dev, Dev/Test, Monash POC, Production) with host and access matrix. Infrastructure components: PgBouncer (connection pooling), Alembic/Flyway (migrations), table partitioning. Env var management via .env.template + .env.local (never committed). nimbus-specific cost estimate: Azure B2ms VM + PostgreSQL Flexible (~$140/month). CI/CD platform: Azure DevOps Pipelines (GitHub Actions fallback). 6 human prerequisites (P1-P6) for Day 1 readiness documented. | Provisioning runbooks not authored. VM sizing and networking specifications absent. IaC not started. Day 1 target date not set. Git provider not selected (4 options assessed, no decision). Self-hosted vs. managed vs. hybrid deployment open. Test database strategy unresolved (3 options open). | B2/README.md, B2/phase-0-task-list.md, B2/day-1-readiness.md, SH/2026-03-08-scope-reframe-actor-map.md |
| 3 | Build Plan / Sprint Backlog | Partial | ~30% | Phase structure validated: Phase 0 (Foundation), Phase 1 (Core Platform: KE + Augmentation + Intelligence + Integration basics + Eval + Basic UI + Audit), Phase 2 (First Customer Stream — streams not monolith), Phase 3+ (Expand). Feature structure: F119-F128 (area-level). Augmentation Layer must be Phase 1 (dog-fooding principle). Build order for Knowledge Engine: 6-step sequence with rationale. Phase 0: 12 ordered tasks (T1-T12) with done criteria and dependency graph. Phase 1 deliverables for KE and Integration Hub listed. Monash POC plan: 8-10 week 5-phase plan with success criteria. | plan-of-attack.md is UNVALIDATED — old numbers invalidated; fresh rewrite not done. Timeline re-estimation not done. Sprint breakdown and task estimates absent. Minimum viable pipeline undefined (which of 6 stages required for first customer?). Playwright scope for discovery not decided. BPMN sync script broken (import errors) — listed as blocking build item. feature catalogue (F119-F128) completeness unverified. | SH/2026-03-08-scope-reframe-actor-map.md, R/plan-of-attack-rewrite-brief.md, B1/knowledge-engine/README.md, B3/ps-accelerator/README.md, B2/phase-0-task-list.md |
| 4 | Definition of Done | Not started | ~5% | DoD criteria are implicit in gate enforcement rules (tests must pass, docs generated, requirements signed off). Per-task "Done when" criteria exist for Phase 0 T1-T12. Phase 0 exit criteria stated in prose: "A second developer (human or AI) can clone, build, connect, and start working." Gate framework rule: AI agents cannot skip gates; humans may with documented justification. | No consolidated Definition of Done document at any level (project, phase, or feature). Per-task criteria from B2 are specific to Phase 0 only. No project-level DoD. No feature-level DoD template. | B2/phase-0-task-list.md, ETH, SH/2026-03-06-gate-framework-complete.md |
| 5 | Agent Protocols | Partial | ~50% | Decided: supervisor pattern (Controller + Supervisors + Specialists), one controller per project, 3-4 sub-agent limit per supervisor, three-layer context hierarchy (global/project/agent), autonomy earned model. Three AI agent categories (Project / Event-Driven / System-Level). Background agent constrained deployment pattern designed (narrow scope, specific knowledge, specific tools, run/report/stop). Protocol modification: human-only, agents propose not activate. Haiku compliance judge sampling: 10% of sessions (experimental). Three-tier enforcement (SpiffWorkflow / Checklist / Prompt + conventions) confirmed. Agent conventions (8 rules) in final form. Gate framework skill installed in Claude Desktop (Mar 7). | Formal agent protocol document not written (conventions are listed, not formatted as an agent-readable enforcement document). Agent inter-messaging protocol not designed (`agent_messages` schema not specified). Supervision model for multiple simultaneous supervisors on one project open. Master AI run sheet contents open. Agent Teams timing (Phase 0 single-agent, Phase 1 introduce for parallel) noted as "recommendation, needs John's confirmation." BPMN `.bpmn` files for agent protocols not authored. | AM §2, B2/agent-conventions.md, B2/agent-compliance-drift-management.md, B2/dev-decisions-agents-workflow-handoff.md, SH/2026-03-08-scope-reframe-actor-map.md |
| 6 | Documentation Standards | Partial | ~40% | Decided: RAG-readable documentation (chunking not summarising), living documentation model (three-speed: real-time DB + ~4x daily embedding + nightly batch), platform generates docs from system state. Markdown conventions defined globally in CLAUDE.md (file size guidelines, YAML frontmatter, link strategy, required footer). Auto-generated documentation from system state (F7 equivalent) decided. Multi-format output (Word, Confluence, PDF, web) decided. Audience-appropriate templates approach decided. | Formal documentation standards document for METIS not written. Document adopted vs. adapted from Claude Family global standards not formally resolved. Format spec for RAG-readable documents not codified. Template library for documentation types not started. | R/plan-of-attack-rewrite-brief.md, B3/ps-accelerator/brainstorm, B2/claude-md-template.md, global CLAUDE.md |
| 7 | Risk Register | Not started | ~20% | Risk signals present across multiple files: AI agent gate-skipping risk, cross-client data isolation risk, knowledge drift risk, multi-agent cost risk, data residency risk, context compaction loss, protocol semantic drift, agent Teams experimental instability, IP ownership on personal GitHub, compliance dashboard deferred risk. Revenue share agreement unresolved (commercial risk). Client relationship ownership unresolved. | No consolidated risk register. Severity and mitigations not formalised. No single document. Risk signals are scattered across 7+ source files. | ETH, AM §2, SPD §11, B2/claude-data-privacy-reference.md, B2/agent-compliance-drift-management.md, B2/dev-decisions-agents-workflow-handoff.md |
| 8 | Project Delivery Framework | Not started | ~15% | Decided: operating model (no internal nimbus dev resources; separate entity; John builds after hours). Subscription pricing ($3-5K/month, 24-month terms, enhancement model). Revenue share: 20% John de Vere / 80% nimbus (proposed, not formally agreed). Build costs and scale projection to 5 clients documented. BHAG: 20%+ productivity improvement with 6 measurable KPIs. 5 user personas with interface strategy by phase. Token cost tracking approach: track actual vs. estimated token consumption per task, ROI from productivity improvement. | Non-technical workstreams (timelines, commercial, human iteration cycles) not designed. Revenue share legal agreement not in place. Separate legal entity model not structured. Client relationship ownership for AI services unresolved. Monash engagement timing uncertain. Support volume baseline data absent. Commercial model for METIS as product (deferred post-Monash). | B3/commercial/README.md, B2/user-experience.md, B3/project-governance/brainstorm |

---

## Additional Context: Decisions That Feed Gate 3

These Mar 10 decisions are not yet in any Gate 3 document but are confirmed input:

| Decision | Gate 3 Implication |
|----------|-------------------|
| Four-layer context management architecture (Core Protocols → Session Notebook → Knowledge Retrieval → Persistent Knowledge) with dynamic priority | Must be specified in Agent Protocols (Doc 5) and codified in Dev Standards (Doc 1) |
| Librarian model: retrieve by chunk, not book | Must be in Documentation Standards (Doc 6) and Dev Standards (Doc 1) |
| Task decomposition protocol: break every input into tasks before acting | Must be in Agent Protocols (Doc 5) and Definition of Done (Doc 4) |
| Desktop = design decisions with John; Claude Code = technical build + consolidation | Must be in Delivery Framework (Doc 8) and Build Plan (Doc 3) |
| RBAC: Platform Builder, Enterprise Admin, Enterprise Staff as the three roles | Must be in Agent Protocols (Doc 5) for access control |

---

## Gate 3 Sequencing Notes

Gate 3 deliverables have dependencies on Gate 2. The most sequencing-sensitive items:

- **Doc 1 (Dev Standards)** can be started in parallel with Gate 2 — most decisions exist
- **Doc 4 (Definition of Done)** depends on knowing what Gate 2 will produce
- **Doc 5 (Agent Protocols)** partially depends on G2 Doc 1 (BPMN Models) for enforcement model
- **Doc 3 (Build Plan)** depends on G2 Doc 5 (Data Model), G2 Doc 6 (Tech Stack), G2 Doc 11 (Deployment) being resolved
- **Doc 7 (Risk Register)** can be started in parallel — risk signals already exist
- **Doc 8 (Delivery Framework)** depends on commercial decisions and Monash engagement confirmation

---
*Index only — formal Gate 3 work not started | 2026-03-11*

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-three/README.md
