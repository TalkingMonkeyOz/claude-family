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

# Integration Points

Gate One Document 5.

## Purpose

Inventory of all external systems and integration patterns for the METIS platform. This is high-level — system, direction, protocol, and purpose. Detailed API contracts, error taxonomies, and interface specifications are Gate 2 work.

## Summary

- Total integration points: 27
- External systems: 15
- Internal integrations: 12
- Maturity: 8 proven, 13 designed, 6 named only

Coverage check: all 4 external system categories from system-map.md C4 L1 are represented. See coverage check section at the end of this document.

---

## External Systems

| # | System | Direction | Protocols | Purpose | Maturity | Source Files |
|---|--------|-----------|-----------|---------|----------|--------------|
| EX-01 | LLM Provider (Claude API, primary) | Outbound | HTTPS REST. Provider-agnostic LLM abstraction interface. Claude default; OpenAI and self-hosted as alternatives for data sovereignty. Prompt caching for system prompts (up to 200K tokens, 70–80% cost savings). Batch API for non-urgent work (50% cost discount). Per-run cost cap enforced. | Inference — prompt completion, analysis, generation for all AI agents. | proven | SPD §4.1, AM §3, infra-decisions-api-git-auth.md, brainstorm-knowledge-engine-deep-dive.md §1 |
| EX-02 | AWS Bedrock (ap-southeast-2 Sydney) | Outbound | AWS SDK. Claude models available on Bedrock. | Alternative inference endpoint if AU data residency becomes a hard requirement. Eliminates the Anthropic US transient retention issue. | named | claude-data-privacy-reference.md |
| EX-03 | Voyage AI Embedding Service | Outbound | HTTPS REST. voyage-3 model, 1024 dimensions. Pluggable EmbeddingProvider interface — alternatives include OpenAI text-embedding-3-large, Cohere embed-v4, self-hosted BGE-M3/e5. Lazy-loaded to save latency. | Vector embedding generation for all knowledge items, vault documents, and workfiles. | proven | SPD §4.1, SPD §8, brainstorm-knowledge-engine-deep-dive.md §1, §5 |
| EX-04 | Jira (Monash instance) | Bidirectional | REST + MCP connector. 8-method standard connector interface + 6-layer middleware (rate limit, retry, circuit breaker, audit logger, credential manager, direction control). Already working. Future: event-driven via webhooks or polling. | Defect creation, status syncing, defect monitoring, cross-client impact analysis, digest generation. Autonomous triage in Phase 3+. | proven | FC F6, SPD §9.2, integration-hub/README.md, README.md, gap-resolution-summary.md GAP-2 |
| EX-05 | Jira (nimbus internal instance) | Bidirectional | REST + MCP connector. Same connector interface as EX-04. Already working. | Work item sync, defect backlog, velocity and blockers. Internal platform governance. | proven | integration-hub/README.md, day-1-readiness.md, README.md |
| EX-06 | Jira (client-facing, Mode A only) | Inbound | REST via Integration Hub. Optional — not a core dependency. Auto-detect new issues, sync status. | Client issue intake (alternative to Mode B manual capture). | designed | project-governance/pm-lifecycle-client-timelines.md |
| EX-07 | Azure DevOps Pipelines | Inbound (trigger) | Push and PR events trigger 5-stage CI pipeline. Azure DevOps YAML format. Fallback: GitHub Actions (same stages, different YAML). | CI/CD pipeline triggers: build, test, lint, security scan, deploy. | designed | cicd-pipeline-spec.md |
| EX-08 | Git Provider (Azure DevOps / GitHub / GitLab / Gitea) | Bidirectional | REST via Integration Hub. Provider-agnostic. Feature branch → develop → main strategy. Agents branch off develop, merge via PR. | Version control for artifacts (specs, ADRs, code). Commit activity feeds timeline intelligence. DB tracks work metadata; git tracks artifact content. | proven | infra-decisions-api-git-auth.md Decision 2, project-governance/brainstorm, 2026-02-24-project-mgmt-lifecycle.md |
| EX-09 | Confluence (Enterprise Toolstack) | Bidirectional | REST via Integration Hub (or MCP). Read: bulk product domain knowledge import on product release events. Write: AI-generated documentation pushed out (Confluence is a target, not source of truth). | Product domain knowledge ingestion; living documentation publishing. | designed | SPD §9.2, integration-hub/README.md, plan-of-attack.md, 2026-03-10-knowledge-engine-design.md |
| EX-10 | SharePoint | Inbound | REST via Integration Hub. Bulk import on product release events. | Product domain knowledge ingestion from SharePoint document libraries. | named | 2026-03-10-knowledge-engine-design.md |
| EX-11 | Salesforce (CRM) | Bidirectional (write deferred) | REST via Integration Hub. Read: timesheet data, project milestones, budget burn rate, client/account data, health scoring data. Write-back decision deferred (Phase 3+). | Project health scoring, client/account data, common services data layer. Platform owns truth; Salesforce is a source, not authority. | designed | SPD §9.2, AM §3, project-governance/README.md, gap-resolution-summary.md GAP-14 |
| EX-12 | Granola (meeting notes capture) | Inbound | Webhook or polling (design TBD). Meeting notes parsed for decisions, action items, issues. Mode B issue capture source. | PM alerts: unactioned items detection. Decision and action item ingestion. | named | project-governance/README.md, pm-lifecycle-client-timelines.md, 2026-02-28-session8-handoff.md |
| EX-13 | Slack (Enterprise Toolstack) | Bidirectional | MCP connector. Already working. Bidirectional: read questions and commands; write status alerts and responses. Phase 1: Q&A. Phase 2+: alert channel for monitoring. | Zero-new-tools user experience for Phase 1. AI capability surfaced inside existing Slack workspace. | proven | user-experience.md, integration-hub/README.md, monitoring-alerting-design.md |
| EX-14 | Enterprise Identity Provider (SSO/OIDC/SAML) | Inbound (auth) | Pluggable auth interface. Phase 1: simple token auth. Interface designed so SSO can be added without touching the RBAC engine. | User authentication for enterprise deployments requiring SSO. | designed | security-architecture.md |
| EX-15 | External Secrets Manager | Outbound (future) | Pluggable credential interface. Phase 1: encrypted at rest in instance DB. Future: HashiCorp Vault, AWS Secrets Manager, Azure Key Vault. | Secure credential storage for connector configurations; supports credential rotation. | designed | security-architecture.md |

---

## Internal Integration Patterns

| # | Pattern | Description | Used By | Maturity | Source Files |
|---|---------|-------------|---------|----------|--------------|
| IN-01 | time2work REST API | Outbound to enterprise product. REST connector with OAuth2/API key auth. Full CRUD on employee, configuration, and pay rule endpoints. Retry with exponential backoff, rate limiter, circuit breaker, audit logger. Config push to UAT; config read for doc generation; test scenario submission. | Delivery Accelerator (Area 3), QA (Area 4) | proven | FC F4, F5, F7, day-1-readiness.md, integration-hub/README.md, connector-interface-design.md |
| IN-02 | time2work OData API | Inbound read. Dedicated OData connector for reporting and data extraction. Screen discovery via Playwright. Semi-automated metadata ingestion. OData metadata ingested as first knowledge load. | Knowledge Engine (Area 1), QA (Area 4) | proven | integration-hub/README.md, 2026-03-10-knowledge-engine-design.md |
| IN-03 | time2work SQL Database | Inbound read. Direct SQL access (admin privilege). Transforms Knowledge Engine from "knows the API" to "knows how the system actually works" including relationships and actual data. Requires management approval. | Knowledge Engine (Area 1) | named | knowledge-engine/README.md §Knowledge Sources |
| IN-04 | time2work Source Code (C#/.NET) | Inbound read, BHAG. Read-only codebase access. | Knowledge Engine (Area 1) | named | knowledge-engine/README.md §BHAG |
| IN-05 | Playwright (Browser Automation) | Outbound. Browser automation for screen discovery and UI test execution against time2work. Native to Claude Code. Also used for full regression suite. | QA (Area 4), Delivery Accelerator (Area 3) | proven | FC F5, README.md, day-1-readiness.md |
| IN-06 | PostgreSQL + pgvector (Knowledge Store) | Internal. Application layer only — agents never access directly. pgvector HNSW index for vector similarity search. PgBouncer needed for enterprise multi-instance. 470+ QPS at 99% recall on 50M vectors. Upgrade path to Qdrant/Pinecone identified. Row-level security for multi-tenancy. | All areas | proven | SPD §4.1, SPD §8, security-architecture.md, audit-database.md |
| IN-07 | SpiffWorkflow BPMN Engine | Internal Python library. XML parsing (validation) + runtime execution (`get_current_step`). State persistence via `workflow_instances` table. Supports concurrent instances. Gate 2+ swap-out to Camunda/Temporal identified as a future option. | Workflow Engine (Area 9), all areas | proven | brainstorm-capture-enforcement-layer.md, 2026-03-10-knowledge-engine-design.md |
| IN-08 | MCP Server (METIS-Exposed) | Outbound to Claude Desktop and Claude Code clients. METIS exposes an MCP server for L2/L3 assisted work. Enables Claude Desktop to invoke METIS capabilities during design sessions. | Intelligence Layer, Augmentation Layer | designed | 2026-03-09-interaction-model-mcp-review.md |
| IN-09 | Knowledge Engine HTTP API (Internal) | Internal REST service. 13 endpoints: /ask, /search, /ingest, /ingest/batch, /validate, /promote, /similar, /knowledge/{id}, /knowledge/{id}/history, /knowledge/{id}/graph, /categories, /health, /feedback. Also /clients/{id}/knowledge for scoped access. | All application services, all agents | designed | brainstorm-knowledge-engine-deep-dive.md §7, knowledge-graph-relationships.md §6, README.md |
| IN-10 | Excel/CSV Import | Inbound. Standardised templates with validation. Configuration sets and test scenarios. | Delivery Accelerator (Area 3) | named | integration-hub/README.md |
| IN-11 | Session Scratchpad API (Internal) | Internal REST. `GET /api/v1/session/{id}/scratchpad` — query scratchpad entries by session, scope, category, time filters. Returns ordered list for context reconstruction after context compaction. | Platform Services (Area 7), all agents | designed | session-memory-context-persistence.md §2.5 |
| IN-12 | Product Rule/Legislation Change Feed | Inbound. Webhook or polling design TBD. Detects external rule or legislation changes from the enterprise product vendor. Triggers affected-configuration re-validation queue. | Quality and Compliance (Area 4) | named | quality-compliance/README.md |

---

## Protocol Summary

| Protocol | Systems Using It | Notes |
|----------|-----------------|-------|
| HTTPS REST | EX-01, EX-02, EX-03, EX-04, EX-05, EX-06, EX-09, EX-11, IN-01, IN-09, IN-11 | Primary integration protocol. Connector abstraction normalises differences. |
| MCP (Model Context Protocol) | EX-04, EX-05, EX-13, IN-08 | Supported alongside REST for Enterprise Products and Toolstack per Gate Zero decision. Also used for METIS outbound exposure to Claude Desktop/Code. |
| OData | IN-02 | Enterprise product-specific. Dedicated OData connector in Integration Hub. |
| Git/REST | EX-07, EX-08 | Version control and CI/CD triggers. Provider-agnostic by design. |
| Webhook / Polling | EX-07, EX-12, IN-12 | Event-driven triggers where push is supported; polling fallback where not. |
| BPMN/DMN (SpiffWorkflow) | IN-07 | Internal only. Python library executing process state. Not an external protocol. |
| Browser Automation | IN-05 | Playwright for UI test execution and screen discovery. Not a data protocol. |
| SQL | IN-06, IN-03 | pgvector via application layer only. Direct SQL access to time2work is admin-tier, exceptional case. |

---

## Coverage Check

Cross-reference against system-map.md C4 L1 external system categories. Every system category from the system context diagram must appear in this inventory.

| C4 L1 External System | Coverage | Integration Points |
|----------------------|----------|-------------------|
| LLM Provider | Covered | EX-01 (Claude API, primary), EX-02 (AWS Bedrock, fallback) |
| Embedding Service | Covered | EX-03 (Voyage AI, with pluggable alternatives) |
| Enterprise Toolstack (Jira, Confluence, CRM, repos) | Covered | EX-04, EX-05, EX-06 (Jira), EX-08 (Git), EX-09 (Confluence), EX-10 (SharePoint), EX-11 (Salesforce), EX-12 (Granola), EX-13 (Slack) |
| Enterprise Product (REST, OData, MCP) | Covered | IN-01 (REST), IN-02 (OData), IN-03 (SQL), IN-04 (Source Code), IN-05 (Playwright UI) |

All 4 C4 L1 external system categories are covered. No gaps identified.

### Not-In-Scope (Existing AI Tools)

The following existing paid tools were assessed and are explicitly not integrated into METIS. They provide generic capability with no nimbus domain knowledge.

| Tool | Status | Reason |
|------|--------|--------|
| Atlassian Intelligence | Assessed, not integrated | Summarises tickets, drafts content, NL JQL. No domain knowledge. |
| Atlassian Rovo | Assessed, not integrated | Cross-tool search. Shallow reasoning, no bespoke modelling. |
| Microsoft Copilot (Corporate) | Assessed, not integrated | Email/document summarisation. General purpose only, zero nimbus expertise. |

---

*Gate One Doc 5 | Draft: 2026-03-11 | Consolidated from 6 extraction batches*

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-one/integration-points.md
