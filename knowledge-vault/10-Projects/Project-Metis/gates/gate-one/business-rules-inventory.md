---
tags:
  - project/Project-Metis
  - scope/system
  - type/gate-one
  - gate/one
created: 2026-03-11
updated: 2026-03-11
status: draft
---

# Business Rules Inventory

Gate One Document 4.

## Purpose

Comprehensive inventory of all business rules governing METIS platform behaviour. Covers data governance, security, agent governance, architecture principles, process rules, commercial rules, and quality. Detailed decision models (DMN) are Gate 2 work.

## Summary

- Total rules: 52
- Categories: 7
- Sources: 6 extraction batches + 5 new decisions from 2026-03-10 session

---

## Data Governance Rules

| # | Rule | Description | Status | Source Files |
|---|------|-------------|--------|--------------|
| DG-01 | Validation Tier Assignment | All knowledge items must be assigned to a validation tier (T1–T4) before storage. Tier determines approval path. | decided | SPD §6.2, brainstorm-knowledge-engine-deep-dive.md §6, stocktake-2026-02-23.md |
| DG-02 | T1 Auto-Approval | Tier 1 knowledge (system-generated: API docs, config snapshots, metadata from authoritative sources) is auto-approved with no human review required. | decided | SPD §6.2, brainstorm-knowledge-engine-deep-dive.md §6 |
| DG-03 | T2 Mandatory Human Review | Tier 2 knowledge (human-authored, compliance-critical, rules/patterns/procedures) requires human review before activation. | decided | SPD §6.2, brainstorm-knowledge-engine-deep-dive.md §6 |
| DG-04 | T3 Auto-Ingest with Confidence Flag | Tier 3 knowledge (experiential: support resolutions, decision records) is auto-ingested but tagged with low-confidence flag. Volume too high to review everything. | decided | SPD §6.2, brainstorm-knowledge-engine-deep-dive.md §6 |
| DG-05 | T4 Always Flagged, Never Auto-Trusted | Tier 4 knowledge (AI-generated) is always flagged and never auto-trusted. Always treated as a hypothesis requiring human validation. | decided | SPD §6.2, ETH, brainstorm-knowledge-engine-deep-dive.md §6 |
| DG-06 | Scope Isolation — Client Hard Boundary | Client data is strictly isolated by client_id on all queries. Client configuration specifics, context, and decision records must never promote to higher scope levels. | decided | SPD §7.3, brainstorm-knowledge-engine-deep-dive.md §3, security-architecture.md |
| DG-07 | Scope Inheritance Downward | When querying at client level, product-level knowledge is always included. When querying at engagement level, client and product knowledge are included. Automatic via NULL FK scope filter. | decided | brainstorm-knowledge-engine-deep-dive.md §2 |
| DG-08 | Scope Promotion Upward Is Controlled | Knowledge can only move upward (client → product) through anonymisation and an approval workflow. Never automatic. | decided | brainstorm-knowledge-engine-deep-dive.md §2, §3 |
| DG-09 | What Never Promotes | Client config values, client context (org structure, contacts), decision records, and anything marked confidential must never be promoted to product scope. | decided | brainstorm-knowledge-engine-deep-dive.md §3 |
| DG-10 | Promotion Always Requires T2 Validation | Every promotion step (client → product) requires human review regardless of source tier. | decided | brainstorm-knowledge-engine-deep-dive.md §3 |
| DG-11 | Supersedes Relationship on Promotion | When a client-specific item is promoted to product level, the promoted item must record a `supersedes` relationship to the original. Original remains intact. | decided | FC F9 |
| DG-12 | Soft Deletes Only | Nothing is permanently removed. All deletes are logical: `is_deleted` / `deleted_at` flag. Applies to all entities and all actors (human and AI). | decided | security-architecture.md, README.md, claude-md-template.md |
| DG-13 | Audit Log Append-Only | Audit log entries are never updated or deleted. Append-only by design. All state transitions logged to audit_log. | decided | phase-0-task-list.md T6, bpmn-sop-enforcement §Layer 5, audit-database.md |
| DG-14 | Embedding Model Tracking Mandatory | Every knowledge item stores `embedding_model` and `embedding_dimensions`. Switching providers requires bulk re-embed of all content. | decided | brainstorm-knowledge-engine-deep-dive.md §1, §5 |
| DG-15 | Event-Driven Staleness | Knowledge is flagged for review when its dependencies change (product release, API update), not on a time schedule alone. | decided | gap-resolution-summary.md GAP-6, 2026-03-10-knowledge-engine-design.md |
| DG-16 | Extract-Then-Decay | Raw T2 audit logs are processed into durable knowledge insights before they age out. Raw logs decay; insights persist. | decided | security-architecture.md |
| DG-17 | Tiered Audit Retention | Tier 1 (permanent): security events, writes/deletes, human approvals. Tier 2 (configurable 6–12 months): conversations, context assembly. Tier 3 (short/aggregated): routine reads, health checks. | decided | security-architecture.md |
| DG-18 | Defects Captured in System First | METIS is the source of truth for defects. External trackers (Jira, Azure DevOps) are synced to, not from. | decided | support-defect-intel/README.md, 2026-02-24-area-5-complete-all-areas-first-pass.md |
| DG-19 | Decisions Are First-Class Objects | Every significant decision is a DB record capturing: who requested, AI recommendation, who approved, what was tested, when, why. Compliance-flagged decisions retained indefinitely. | decided | project-governance/brainstorm, 2026-02-24-project-mgmt-lifecycle.md |
| DG-20 | Forward-Only Migrations | No down migrations. Each migration must be idempotent (`IF NOT EXISTS`). Checksum tracking detects post-apply edits. | decided | phase-0-task-list.md T4 |

---

## Security Rules

| # | Rule | Description | Status | Source Files |
|---|------|-------------|--------|--------------|
| SE-01 | RBAC Tenant-Level Hard Isolation | Client Config and Learned/Cognitive knowledge are isolated per tenant. Product Domain and API Reference knowledge are shared across tenants. Process/Procedural knowledge is shared with tenant-specific variants. Project/Delivery records are tenant-scoped. Roles: Platform Builder (all), Enterprise Admin (their tenant), Enterprise Staff (work-context scoped). | decided | 2026-03-10-decisions-and-delegation.md |
| SE-02 | Separate Instances Per Enterprise Customer | Each enterprise customer gets a complete independent METIS deployment. Not a shared multi-tenant platform. | decided | security-architecture.md, 2026-03-08-security-architecture.md |
| SE-03 | Agent Access Ceiling | An agent can never see more than the human who initiated the work. Session token propagated through the full agent hierarchy. | decided | security-architecture.md, 2026-03-08-security-architecture.md |
| SE-04 | Agent Constrained to Task/Project Scope | Within the human's access ceiling, an agent retrieves only what is relevant to its current project/task. Prevents AI bleed across client boundaries. | decided | security-architecture.md, 2026-03-08-security-architecture.md |
| SE-05 | Application Layer Is Single Enforcement Point | All agents access the backend through the application layer only — never direct database access. RBAC, action validation, and audit logging enforced here. | decided | security-architecture.md, 2026-03-08-security-architecture.md |
| SE-06 | Pluggable Auth Interface | Authentication (who?) is pluggable at the front end. Authorisation (what can they do?) is the RBAC engine inside the application layer. Auth provider swap does not change authorisation rules. | decided | security-architecture.md |
| SE-07 | Credential Storage Via Interface | Phase 1: credentials encrypted at rest in the instance DB. Architecture: pluggable secrets manager interface (HashiCorp Vault, AWS Secrets Manager as future backends). | decided | security-architecture.md |
| SE-08 | Per-User Credential Delegation | METIS uses the current user's own credentials to connect to external systems, inheriting the enterprise's existing access controls. | decided | security-architecture.md |
| SE-09 | Direction Control on Integration Connectors | Each connector is configurable as read-only, write-only, or bidirectional. Default is read-only until explicitly opened. | decided | security-architecture.md |
| SE-10 | Credentials Never Hardcoded | All secrets via environment variables. Never hardcoded. Sensitive data (passwords, tokens, credentials) must never appear in logs. | decided | claude-md-template.md, README.md |
| SE-11 | End Customer Has No Direct METIS Access | End Customer inputs arrive via enterprise channels only (tickets, docs, specs ingested by PS or Support). No direct chat or API access in initial scope. | decided | 2026-03-08-gate-zero-complete.md, system-map.md |
| SE-12 | Data Residency — Persistent Data in AU | All persistent data in Azure Australia East. Only transient API calls (prompts/responses) leave Australia. Maximum 7-day retention at Anthropic US under commercial terms. | decided | claude-data-privacy-reference.md |
| SE-13 | API Training Data Never Used | Anthropic API data is never used for model training. Contractual under Anthropic Commercial Terms. | decided | claude-data-privacy-reference.md |

---

## Agent Governance Rules

| # | Rule | Description | Status | Source Files |
|---|------|-------------|--------|--------------|
| AG-01 | Autonomy Is Earned | All decisions go through a human initially. Agents gain progressive autonomy based on demonstrated competence, not by default. | decided | AM §2, ETH |
| AG-02 | AI Agents Cannot Skip Gates | Humans may skip pipeline gates with documented justification. AI agents cannot skip gates under any circumstances. | decided | ETH, 2026-03-06-gate-framework-complete.md |
| AG-03 | Task Decomposition on Every Request | Every user input must be decomposed into tasks before acting on any of them. First work_item.create must precede first code-modifying tool call. | decided | 2026-03-10-decisions-and-delegation.md, agent-conventions.md Rule 1 |
| AG-04 | Verify Before Claiming | Read the file before saying it contains X. Query the DB before asserting a table exists. Run the test before claiming it passes. Never claim state without checking. | decided | agent-conventions.md Rule 2 |
| AG-05 | Delegate Complex Work | Tasks touching 3+ files across different modules must be broken down or delegated to a sub-agent with clean context. | decided | agent-conventions.md Rule 5, 2026-03-10-decisions-and-delegation.md |
| AG-06 | Protocol Rules Modification: Human-Only | Agents may propose rule changes but cannot activate them. Requires explicit human approval. | decided | agent-conventions.md Rule 8, 2026-02-23-orchestration-build-specs.md |
| AG-07 | Anti-Compression Safeguard | If a proposed protocol change reduces word count by more than 10% without adding specificity, it must be flagged for human review. | decided | agent-compliance-drift-management.md |
| AG-08 | Specialised Agents, Not General | Agent instructions must be tightly constrained. General-purpose agents must not be used in production pipelines. | decided | AM §2, ETH |
| AG-09 | 3–4 Sub-Agent Limit Per Supervisor | Each supervisor agent may coordinate no more than 3–4 specialist sub-agents. | decided | AM §2 |
| AG-10 | One Controller Per Project | Each project has exactly one Project Controller agent as the coherence mechanism. | decided | AM §2 |
| AG-11 | Three-Layer Context Hierarchy | Every agent receives: (1) global standards, (2) project context, (3) agent-specific tightly-constrained instructions. | decided | AM §2 |
| AG-12 | External Enforcement Principle | Enforcement must be external to the LLM. Prompt instructions are suggestions, not hard constraints. BPMN/DMN govern process, not prompts alone. | decided | brainstorm-capture-enforcement-layer.md §Level 2 |
| AG-13 | Autonomous Operations — Read-Only by Default | Autonomous agents can read freely. Write operations require explicit permission config or human approval unless whitelisted. | decided | autonomous-operations.md |
| AG-14 | Cost Cap Per Autonomous Run | Each autonomous scheduled/triggered task has a maximum token budget it cannot exceed. Daily and monthly caps also enforced. | decided | autonomous-operations.md |
| AG-15 | Delegation Model — Desktop vs Code | Claude Desktop does design decisions. Claude Code does the technical build. Desktop delegates implementation after design is agreed. | decided | 2026-03-10-decisions-and-delegation.md |

---

## Architecture Principles

| # | Rule | Description | Status | Source Files |
|---|------|-------------|--------|--------------|
| AR-01 | Infrastructure Agnostic | System must be deployable on any Linux environment with PostgreSQL. Infrastructure choices are customer-specific. | decided | SPD §11 |
| AR-02 | Provider-Agnostic LLM and Embedding | Embedding model, vector database, and LLM can each be swapped independently. Knowledge and processes are the assets, not the provider choices. | decided | SPD §4.1, brainstorm-knowledge-engine-deep-dive.md §1 |
| AR-03 | Pluggable Adapters Behind Stable Interfaces | Auth, credentials, and execution engine must be swappable without changing the application layer. | decided | security-architecture.md |
| AR-04 | No Direct API Calls from Business Logic | Business logic must never call external APIs directly. Always through the connector abstraction layer. Enables mocking for testing. | decided | connector-interface-design.md, integration-hub/README.md |
| AR-05 | Connectors Are Dumb Pipes | Connectors handle connection, auth, and transport only. Business logic handles meaning. Sync logic is a separate service from connectors. | decided | connector-interface-design.md |
| AR-06 | Hot-Swappable Connector Config | Connector configurations can be updated without system restart. Credential rotation supported live. | decided | connector-interface-design.md, integration-hub/README.md |
| AR-07 | DDD Boundary Enforcement | Changes to a bounded context must not silently affect other contexts. Domain events define cross-boundary communication. Ubiquitous language enforced platform-wide. | decided | bpmn-sop-enforcement §Layer 1 |
| AR-08 | Four-Layer Context Management | Context follows a fixed priority hierarchy: (1) Core Protocols (always injected), (2) Session Notebook (session-scoped facts), (3) Knowledge Retrieval (assembled WCC), (4) Persistent Knowledge (vault/memory). Priority is dynamic — higher layers can suppress lower layers. | decided | 2026-03-10-knowledge-engine-design.md |
| AR-09 | Librarian Model — Chunks, Not Books | Knowledge is retrieved at chunk granularity, not document granularity. Every chunk has a `token_count` for budget-aware assembly. Retrieval returns the right section, not the whole source. | decided | 2026-03-10-knowledge-engine-design.md |
| AR-10 | Platform Is Source of Truth for Project Status | METIS (not Salesforce or external PM tools) is the canonical realistic status view derived from actual work data. External tools are connectors, not authorities. | decided | project-governance/pm-lifecycle-client-timelines.md |
| AR-11 | Work Items in DB, Artifacts in Git | Work tracking metadata lives in DB for agent-fast queries. Artifacts (specs, ADRs, code) live in git for version control. Bidirectional linking maintained. | decided | project-governance/brainstorm |
| AR-12 | No LangChain or LlamaIndex | Custom RAG only. No framework dependency on LangChain or LlamaIndex. | decided | claude-md-template.md |
| AR-13 | Scope Hierarchy for Multi-Product Customers | Org → Product → Client → Engagement. Rigid top levels; flexible sub-levels per engagement. | decided | gap-resolution-summary.md GAP-12 |

---

## Process Rules

| # | Rule | Description | Status | Source Files |
|---|------|-------------|--------|--------------|
| PR-01 | BPMN-First for High-Stakes Processes | Processes where skipping a step has real consequences (compliance, client data, deployments) must use full SpiffWorkflow runtime enforcement. Claude is a worker within the workflow, not the controller. | decided | brainstorm-capture-enforcement-layer.md, system-change-process.md |
| PR-02 | DMN for All Decision Points | Rules at decision points must be expressed as DMN tables, not embedded in prompts or ad-hoc code. Explicit, testable, auditable, versioned. | decided | bpmn-sop-enforcement §Layer 3 |
| PR-03 | Three-Tier Pipeline Gate Model | Gates are: mandatory (cannot be bypassed by anyone), default-on (customer admin can toggle), optional (platform team must build then admin enables). All gates are BPMN-driven. | decided | ps-accelerator/brainstorm, 2026-02-24-area-2-5-sweep.md |
| PR-04 | Mandatory Gates Cannot Be Bypassed | System-enforced mandatory pipeline gates cannot be disabled by any customer. BPMN process will not advance without them. | decided | ps-accelerator/brainstorm |
| PR-05 | Humans Guide at Checkpoints | AI executes between validation checkpoints. Humans must be present at all validation checkpoints in the pipeline. | decided | SPD §2, §10, ETH |
| PR-06 | Dual-Lens — Enforce What We Do Ourselves | The gate framework applies both to building METIS and to what METIS enforces for client engagements. Same rules apply internally and externally. | decided | SPD §10, ETH, 2026-03-06-gate-zero.md |
| PR-07 | Templates Are KMS Items | Delivery templates are stored in the Knowledge Engine as Category C knowledge. No separate template system. Follow the same scope hierarchy, validation tiers, and promotion mechanism. | decided | ps-accelerator/brainstorm |
| PR-08 | Tier 2 Escalates to Tier 3 if Code Required | A signed-off client deliverable that requires code changes escalates to the Pipeline tier where the five-layer validation stack applies. | decided | ps-accelerator/brainstorm, 2026-02-24-project-mgmt-lifecycle.md |
| PR-09 | Procedural Knowledge Captured Through Work | Process documentation is a byproduct of doing work. Captured iteratively, not written upfront. | decided | 2026-03-10-knowledge-engine-design.md |
| PR-10 | Dog-Fooding — Platform Uses Itself | Platform uses its own KMS, delivery pipeline, and quality tools for its own development. Same supervised agent pattern. | decided | gap-resolution-summary.md GAP-15 |
| PR-11 | Thread Not Resolved Until All Children Closed | An Issue Thread is only marked resolved when all child tickets across all systems are closed AND the fix is deployed and verified at the client. | decided | project-governance/pm-lifecycle-client-timelines.md |
| PR-12 | Human Review Before Client Documentation | All AI-generated client-facing documentation requires human approval before delivery. System generates, human confirms. | decided | ps-accelerator/brainstorm |
| PR-13 | Living Documentation Maximum Staleness | Client-facing documentation must never be more than one day out of date. Generated nightly from system state. Human review flag required before client delivery. | decided | ps-accelerator/brainstorm, 2026-02-24-area-2-5-sweep.md |
| PR-14 | AI Does Not Auto-Escalate Patterns | When the system detects a cross-customer defect pattern, it is flagged for human review only. AI must not autonomously escalate or trigger product changes. | decided | support-defect-intel/README.md |
| PR-15 | Knowledge Promotion Is Human-Driven | AI suggests resolved defects and items as KMS candidates. Human reviews and approves or rejects every candidate. No automatic promotion. | decided | support-defect-intel/README.md, 2026-02-24-area-5-complete-all-areas-first-pass.md |
| PR-16 | Full Customisation Deferred to Year 2+ | Exposing broader pipeline configurability to customers directly is a Year 2+ feature, only after the system is proven stable. | proposed | ps-accelerator/brainstorm |

---

## Commercial Rules

| # | Rule | Description | Status | Source Files |
|---|------|-------------|--------|--------------|
| CO-01 | Revenue Share Scope | The 20%/80% (John/nimbus) revenue share applies to bespoke AI services, AI-assisted implementation subscriptions, custom workflows, and client-specific enhancements. Does not apply to internal nimbus use or generic platform features. | decided | commercial/README.md |
| CO-02 | No Core Product Dependency | Operating model requires no internal nimbus development resources and no changes to core product timelines. AI platform is built separately and integrated at API level only. | decided | commercial/README.md |
| CO-03 | Cost Awareness for Multi-Agent | Multi-agent architectures multiply API calls and token overhead. This must be accounted for in the commercial model and architecture design. | decided | AM §2 |
| CO-04 | Zero-New-Tools for Phase 1 Users | AI capability for end-users must appear inside existing tools (Slack, Jira, Confluence). No new tool to learn in Phase 1. | decided | user-experience.md |

---

## Quality Rules

| # | Rule | Description | Status | Source Files |
|---|------|-------------|--------|--------------|
| QU-01 | Provenance on Every Response | Every /ask response must include sources, confidence scores, and validation status. Non-negotiable for audit and trust. | decided | brainstorm-knowledge-engine-deep-dive.md §7 |
| QU-02 | Uncertainty Must Be Explicit | Any config item or response where the system cannot determine the correct value must be explicitly flagged as uncertain. Never silently omitted or guessed. | decided | FC F4, knowledge-engine/README.md §Design Principles |
| QU-03 | Semantic Duplicate Check Before Create | New defects must be checked semantically against existing defects before a new record is created. | decided | FC F6 |
| QU-04 | 5-Question Validation Before Publish | New constrained deployments must be tested with at least 5 evaluation questions before publishing to any channel. | decided | FC F10 |
| QU-05 | Knowledge Curation Quality Gate | 73% of RAG failures are quality issues, not technology issues. The system is only as good as knowledge quality. Months of curation required for a comprehensive Knowledge Engine. | decided | knowledge-engine/README.md §What's Hard |
| QU-06 | Natural Chunking Boundaries | Knowledge items are chunked at natural boundaries (one endpoint, one pattern, one resolution) not fixed token counts. | decided | brainstorm-knowledge-engine-deep-dive.md §5 |
| QU-07 | Semantic Search Default | System must default to semantic/vector search for all retrieval. Keyword filters are refinement only. | decided | brainstorm-knowledge-engine-deep-dive.md §5 |
| QU-08 | Everything Adds Value | Every feature, report, dashboard, and alert must provide actionable information. Decorative output excluded. | decided | ETH, SPD §10, project-governance/pm-lifecycle-client-timelines.md |
| QU-09 | Tasks Must Be Fully Detailed | Agent tasks must contain full context. Vague tasks produce wrong implementations. | decided | project-governance/brainstorm |
| QU-10 | AI Relationship Suggestions Unvalidated by Default | Relationships suggested by AI background processes are created with `validated = false`. Always require human approval before use in retrieval. | decided | knowledge-graph-relationships.md §4.2 |
| QU-11 | Auto-Validation Threshold for AI Suggestions | AI-suggested relationships may be auto-approved only after exceeding 90% human approval rate over 50+ suggestions for that specific relation type. Must be earned per type. | decided | knowledge-graph-relationships.md §4.2 |
| QU-12 | Relationship Strength Decay | Unused relationships weaken over time. Below a minimum threshold (e.g. 0.05) they are archived, not deleted. | decided | knowledge-graph-relationships.md §7 |
| QU-13 | Co-Access Tracking | Knowledge items retrieved together in the same context assembly are treated as related even if their embedding similarity is low. Used to strengthen the knowledge graph over time. | decided | 2026-03-10-research-review-option-c.md |

---

*Gate One Doc 4 | Draft: 2026-03-11 | Consolidated from 6 extraction batches + 5 new decisions (2026-03-10)*

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-one/business-rules-inventory.md
