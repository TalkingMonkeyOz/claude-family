---
tags:
  - project/Project-Metis
  - area/decisions
  - scope/system
  - level/1
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Decisions Tracker

> Every decision that needs resolving before or during the build. Tracked centrally, linked back to the area it affects.

**Parent:** [[Project-Metis/README|Level 0 Map]]

## How This Works

Decisions are captured here in one place. Each decision links back to the area it belongs to. When a decision is made, mark it with ✓ and the outcome. Decisions needing management approval are marked ⏳ MGMT NEEDED.

---

## 1. Infrastructure Decisions

- [x] **INFRA — API key provisioning.** Personal Anthropic account, $40 deposit, Tier 2, $200/month cap. Migrate to nimbus org when approved. **✓ DECIDED** → [[orchestration-infra/infra-decisions-api-git-auth]]
- [x] **INFRA — Azure environment.** B2ms VM + B2ms PostgreSQL Flexible w/ pgvector. ~$140 USD/month. Australia East. **✓ DECIDED** → [[orchestration-infra/azure-infrastructure-recommendation]]
- [x] **INFRA — Git repository.** Azure DevOps (nimbus owns it). Need to confirm John has repo creation access. **✓ DECIDED** → [[orchestration-infra/infra-decisions-api-git-auth]]
- [x] **INFRA — Authentication model.** JWT + swappable auth middleware. SSO/OIDC eventually. Simple API key for dev. **✓ DECIDED** → [[orchestration-infra/infra-decisions-api-git-auth]]
- [x] **INFRA — Claude data privacy.** API data NOT used for training. 7-day retention (ZDR available). US processing — AU residency needs mgmt decision. **✓ DECIDED (partial — AU residency needs mgmt)** → [[orchestration-infra/claude-data-privacy-reference]]

## 2. Development Decisions

- [x] **DEV — Agent Teams timing.** Single-agent for Phase 0. Agent Teams from Phase 1 for parallel work. **✓ DECIDED** → [[orchestration-infra/dev-decisions-agents-workflow-handoff]]
- [x] **DEV — Pro Max carry-forward.** Keep patterns (session mgmt, crash recovery, logging). Rebuild as proper TypeScript modules. **✓ DECIDED** → [[orchestration-infra/dev-decisions-agents-workflow-handoff]]
- [x] **DEV — Development workflow.** Three-layer review: CI automation, Opus Review Agent, John spot-checks. **✓ DECIDED** → [[orchestration-infra/dev-decisions-agents-workflow-handoff]]
- [x] **DEV — Desktop-to-Code handoff.** Files as bridge: vault (long-term), CLAUDE.md (session), task spec files (per-task). **✓ DECIDED** → [[orchestration-infra/dev-decisions-agents-workflow-handoff]]
- [x] **DEV — Monash parallel/sequential.** Sequential. Platform foundation first, Monash-specific work in Phase 2. **✓ DECIDED** → [[ps-accelerator/README]]

## 3. Architecture Decisions

- [x] **ARCH — Embedding model.** Keep Voyage AI (works, best-in-class, Anthropic recommended). **✓ DECIDED** → [[knowledge-engine/README]]
- [x] **ARCH — RAG framework.** Custom (already working). LlamaIndex as upgrade path if needed. **✓ DECIDED** → [[knowledge-engine/README]]
- [x] **ARCH — Knowledge validation.** BPMN-based workflow for knowledge artifacts. Tiered: Tier 1 auto → Tier 2 human → Tier 3 confidence-flagged → Tier 4 never auto-trust. **✓ DECIDED** → [[bpmn-sop-enforcement/README]]
- [x] **ARCH — Domain structure.** Hybrid: domain field for primary bucket + tags for cross-cutting search. Four-level scope: Organisation → Product → Client → Engagement. **✓ DECIDED** → [[knowledge-engine/brainstorm-knowledge-engine-deep-dive]]
- [x] **ARCH — RBAC model.** Start simple (admin/user/read-only). Design data model for full RBAC later. **✓ DECIDED** → [[orchestration-infra/README]]
- [x] **ARCH — Constrained deployment.** Four-layer architecture: system prompt + cached knowledge + Haiku classifier + tool restriction. Faster path to market. **✓ DECIDED** → Doc 6
- [x] **ARCH — Knowledge Engine API.** Six endpoints: /ask, /search, /ingest, /validate, /clients/{id}/knowledge, /health. Extended to 10+ in deep dive. **✓ DECIDED** → [[knowledge-engine/brainstorm-knowledge-engine-deep-dive]]
- [x] **ARCH — Data store.** PostgreSQL + pgvector. Hybrid: DB for structured data, vault for docs. **✓ DECIDED** → [[orchestration-infra/README]]
- [x] **ARCH — User experience target.** 20%+ productivity improvement BHAG. **✓ DECIDED** → [[orchestration-infra/user-experience]]
- [x] **ARCH — Validation stack.** Five-layer: DDD → BPMN → DMN → Ontology → Event Sourcing. **✓ DECIDED** → [[bpmn-sop-enforcement/README]]
- [x] **ARCH — LLM provider.** Claude API, but provider-agnostic architecture (can swap). **✓ DECIDED**
- [x] **ARCH — Infrastructure platform.** Linux primary. Infrastructure-agnostic at system level. **✓ DECIDED (review pending)**
- [x] **ARCH — Knowledge graph approach.** Start with relations table in PostgreSQL (already designed in KE architecture). Capture typed relationships from day one. AI-created, human-validated for important ones. Storage-engine-agnostic — can migrate to Apache AGE or graph DB if SQL can't handle traversal depth. Neo4j Community Edition rejected (GPLv3 limitations, separate infrastructure). **✓ DECIDED** → [[knowledge-engine/brainstorm-knowledge-engine-deep-dive]]

## 4. Agent Compliance Decisions (NEW — Feb 23)

- [x] **COMPLIANCE — Enforcement architecture.** Five-layer: core protocol injection, CLAUDE.md reinjection, task-driven context, sub-agent isolation, BPMN gates. **✓ DECIDED** → [[orchestration-infra/agent-compliance-drift-management]]
- [x] **COMPLIANCE — Protocol modification rights.** Human only. Agents can propose, cannot activate. **✓ DECIDED** → [[orchestration-infra/agent-compliance-drift-management]]
- [x] **COMPLIANCE — CLAUDE.md reinjection frequency.** Every 15 interactions. Measure and adjust. **✓ DECIDED (tunable)** → [[orchestration-infra/agent-compliance-drift-management]]
- [x] **COMPLIANCE — Haiku judge sampling rate.** 10% of sessions initially. **✓ DECIDED (adjustable)** → [[orchestration-infra/agent-compliance-drift-management]]
- [x] **COMPLIANCE — Native vs custom tasks.** Try native persistent tasks. Revert if no improvement after 4 weeks. **✓ DECIDED (experiment)** → [[orchestration-infra/agent-compliance-drift-management]]
- [x] **COMPLIANCE — Dashboard priority.** Phase 3. Collect data from Phase 0-2, visualise later. **✓ DECIDED** → [[orchestration-infra/agent-compliance-drift-management]]
- [x] **COMPLIANCE — Status.** Entire area marked EXPERIMENTAL. Measure, don't assume. **✓ DECIDED** → [[orchestration-infra/agent-compliance-drift-management]]

## 5. Project Management & Lifecycle Decisions (NEW — Feb 24)

- [x] **PM — Custom project management.** Platform builds its own work tracking in database. NOT GitHub Projects / Azure Boards / Jira. Integrates with customer tools as connectors. Rationale: BPMN enforcement at gates, agent-fast DB queries, no external dependency. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Lifecycle tiers.** Three tiers: Tier 1 free-flowing (knowledge queries), Tier 2 structured with sign-off (customer deliverables), Tier 3 rigid pipeline (code/deployment). Tier 2 escalates to Tier 3 if code changes needed. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Work breakdown hierarchy.** Initiative → Features → Tasks. Database-backed. Parent rolls up from children. Tasks must be detailed. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Git integration.** Hybrid: DB for tracking metadata, git for artifacts. Provider-agnostic (Azure DevOps, GitHub, GitLab, self-hosted). Work item in DB points to git path. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Documentation source of truth.** Platform generates/maintains docs from system state. Optionally push to Confluence as integration. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Commercial routing.** Commercial call determines paid vs included. Platform needs to know outcome but doesn't make the call — affects lifecycle routing. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Work types.** 8 defaults (knowledge query, bug, feature, config change, documentation, client onboarding, knowledge ingestion, investigation). Configurable/expandable per deployment. Each has default tier mapping, overridable. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Decisions-as-objects.** First-class DB objects. Two use cases: operational (decays) and compliance/legal (never decays). Configurable retention periods. Full source chain for compliance-flagged decisions. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Dashboard & interface.** Chat as major interface (constrained deployment pattern), dashboard for visual at-a-glance. Content: decisions pending/needs attention (essential), work items status (yes), recent activity (no). **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — CCPM.** Parked. Human concern, not AI-relevant. Token cost tracking per task IS relevant — actual-vs-estimated for cost management. **✓ PARKED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]
- [x] **PM — Cross-area integration.** Every area is producer and consumer of work items. Project governance is the registry, not the factory. One audit trail per request across all areas. **✓ DECIDED** → [[project-governance/brainstorm-project-mgmt-lifecycle]]

## 5b. Delivery Accelerator Decisions (NEW — Feb 24)

- [x] **DA — Pipeline gate model.** Three tiers: mandatory (system-enforced, can't skip), default-on (toggleable by customer admin), optional (addable). All BPMN-driven. Customer customisation Year 2+. **✓ DECIDED** → [[ps-accelerator/brainstorm-delivery-accelerator]]
- [x] **DA — Living documentation model.** Three speeds: real-time DB writes during work, periodic RAG embedding (~4x daily or on-trigger), nightly batch regeneration with human review flags. "Never more than a day out of date," not real-time magic. **✓ DECIDED** → [[ps-accelerator/brainstorm-delivery-accelerator]]
- [x] **DA — Lifecycle tier relationship.** Delivery Accelerator runs Tier 2 (structured with sign-off) and Tier 3 (rigid pipeline) work. Tier 1 (knowledge queries) bypasses it entirely. **✓ DECIDED** → [[ps-accelerator/brainstorm-delivery-accelerator]]
- [x] **DA — Templates are KMS items.** Templates live in Knowledge Engine as Category C (Delivery Knowledge). Same scope hierarchy, validation, promotion. No separate template system. **✓ DECIDED** → [[ps-accelerator/brainstorm-delivery-accelerator]]
- [x] **DA — Generic framing.** All design is generic pipeline. Customer examples (nimbus/Monash) are illustrations only. **✓ DECIDED** → [[ps-accelerator/brainstorm-delivery-accelerator]]

## 5c. Quality & Compliance Decisions (NEW — Feb 24)

- [x] **QC — Three testing capabilities.** Configuration Validation (core, API-based), UI Validation (Playwright/complementary), Customer Scenario Replication (nice-to-have, later). **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]
- [x] **QC — Regression is a mode.** Not a separate engine. Applies to both config validation and UI validation. BPMN traces impact to generate regression scope. **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]
- [x] **QC — BPMN as test generation source.** Tests generated from BPMN process maps + code, not hand-written. BPMN elevated to analysis layer, test generation, impact tracing. **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]
- [x] **QC — Quality feedback loop.** Area 4 is the quality conscience — internal compliance, test quality, customer signal clustering, change-triggered re-validation. Not just testing. **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]
- [x] **QC — Background agent jobs.** Scheduled/triggered AI tasks for analysis. Not interactive sessions, not human dashboards. **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]
- [x] **QC — Generic framing.** Configuration validation engine. Customer-specific rules (Award, pricing, scheduling) are examples, not design targets. **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]
- [x] **QC — Compliance monitoring scope.** Proactive validation lives in Area 4. Reactive resolution lives in Area 5. Area 5 feeds signals to Area 4. **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]
- [x] **QC — BPMN elevation.** BPMN is second brain alongside Knowledge Engine. KMS knows what things are. BPMN knows how things flow and connect. Critical dependency for testing. **✓ DECIDED** → [[quality-compliance/brainstorm-quality-compliance]]

## 5d. Support & Defect Intelligence Decisions (NEW — Feb 24)

- [x] **SDI — Scope.** Area 5 owns all defect/issue intelligence regardless of source. Area 4 detects problems, Area 5 manages them. Customer-reported issues skip Area 4 and land directly in Area 5. **✓ DECIDED** → [[support-defect-intel/README]]
- [x] **SDI — System as primary.** The System is the primary defect management layer. Defects captured internally first, then synced outward to customer's defect tracker (Jira, Azure DevOps, etc.). Two-way sync after creation. **✓ DECIDED** → [[support-defect-intel/README]]
- [x] **SDI — Generic framing.** Customer defect tracker is a connector via Integration Hub, not hardcoded. All design is tracker-agnostic. **✓ DECIDED** → [[support-defect-intel/README]]
- [x] **SDI — Area 4/5 feedback loop.** Pattern detected in Area 5 → flagged to human → human decides action (escalate to Area 4, product fix, documentation, training). AI surfaces, human decides. No auto-escalation. **✓ DECIDED** → [[support-defect-intel/README]]
- [x] **SDI — Knowledge promotion.** Human-driven, not automatic. End-of-day/sprint review. AI summarises resolutions, suggests KMS candidates, drafts entries. Human approves/rejects. **✓ DECIDED** → [[support-defect-intel/README]]
- [x] **SDI — Core value proposition.** Defect preparation acceleration. AI turns vague reports into structured, replicated, de-duplicated tickets. Uses customer config knowledge, KMS cross-reference, environment awareness. **✓ DECIDED** → [[support-defect-intel/README]]
- [x] **SDI — Environment awareness.** AI knows per-customer what environments exist and access levels. Variable replication environments (demo, separate instance, customer test). Stored in KMS Category D. **✓ DECIDED** → [[support-defect-intel/README]]

## 6. Partially Resolved

- [ ] **ARCH — Audit & debuggability.** Entire system must be logged, auditable, debuggable. Decisions as first-class objects. Full trace chain for AI answers. **◐ PARTIAL — baked into Orchestration area** → [[orchestration-infra/README]]

## 7. Decisions Needing Management

- [ ] **MGMT — Monash POC go-ahead.** Is Monash the right first POC? Who engages the client? **⏳ MGMT NEEDED — BLOCKING**
- [ ] **MGMT — Monash pricing.** Is $3-5K/month the right range? Who validates? **⏳ MGMT NEEDED — BLOCKING**
- [ ] **MGMT — Internal sponsor.** Who beyond John champions this internally? **⏳ MGMT NEEDED**
- [ ] **MGMT — Leadership visibility.** Who else in leadership needs to know about this initiative? **⏳ MGMT NEEDED**
- [ ] **MGMT — Hard constraints.** Security, data residency (AU processing), client confidentiality boundaries. **⏳ MGMT NEEDED — PARTIAL BLOCKING**
- [ ] **MGMT — Client relationship ownership.** Who owns AI services relationship — John or existing account manager? **⏳ MGMT NEEDED**
- [ ] **MGMT — Source code access.** Read access to time2work codebase for deep knowledge mapping. BHAG flagged. **⏳ MGMT NEEDED**

## 8. Parked

- **Revenue share structure (20/80).** Personal/commercial negotiation, not platform decision. **— PARKED**
- **Separate entity model.** Legal structure decision, not platform decision. **— PARKED**

## 9. Quick Wins

- [ ] **Enable Atlassian Intelligence.** Already paid for in Premium. Zero cost. **⚡ QUICK WIN** → [[integration-hub/README]]
- [ ] **Enable Copilot features.** Already paid for. Zero cost. **⚡ QUICK WIN** → [[integration-hub/README]]

## 10. Operational (Already Resolved)

- [x] **OPS — API/OData access.** John already has API, OData, and SQL access. **✓ RESOLVED 2026-02-19**

---

## Summary Scorecard

| Metric | Count |
|--------|-------|
| Total decisions identified | **68** |
| Decisions resolved | **61 (90%)** |
| Decisions partially resolved | **1 (1%)** |
| Decisions needing management | **7 (10%)** |
| Decisions parked | **2** |
| Quick wins pending | **2** |

*Updated: Feb 24 (Consolidation Chat #10) — Knowledge graph approach decided: start with relations table, upgrade to Apache AGE/graph DB if SQL query depth becomes bottleneck. Total now 68, 61 resolved (90%). ALL 9 AREAS BRAINSTORM-COMPLETE.*

---
*Consolidated from: Master Tracker, Memory Graph, Session Handoffs | Created: 2026-02-19 | Rebuilt: 2026-02-24 | Updated: 2026-02-24 (Chat #9 completed)*
