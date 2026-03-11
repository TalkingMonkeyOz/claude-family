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

# Data Entity Map

Gate One Document 3.

## Purpose

Inventory of all key data entities identified across the METIS platform. This is an INVENTORY — entity names, descriptions, and relationships. Full data model design (column specs, constraints, indexes) is Gate 2 work.

Where multiple batches named the same entity differently, names are normalised to the most descriptive form and aliases noted.

## Summary

- Total entities: 45 (after deduplication from ~132 raw entries)
- Bounded contexts: 7 (mapped to the 9 SPD areas where possible)
- Sources: 6 extraction batches

---

## Bounded Context 1: Knowledge Store

Entities that form the core knowledge graph — what METIS knows and how it is structured.

| # | Entity | Description | Related Entities | Source Files |
|---|--------|-------------|-----------------|--------------|
| KS.1 | Knowledge Item | Core unit of stored knowledge. Content, embedding (1024-dim Voyage AI), category, source type, validation tier (1–4), validation status, confidence score, scope fields (org/product/client/engagement FKs), version, tags, supersedes_id, promoted_from_id, metadata JSONB, timestamps. 27+ columns. Single most important table. Alias: knowledge_items. | Knowledge Relation, Knowledge Type, Embedding, Knowledge Scope, Organisation, Product, Client, Engagement, Knowledge Promotion | batch-a-entities, batch-b1-entities, batch-b2, batch-c, batch-de |
| KS.2 | Knowledge Relation | Directed or undirected typed relationship between two knowledge items. Relation types (8 defaults + custom): depends_on, implements, resolves, supersedes, contradicts, relates_to, part_of, produces. Fields include strength (0.0–1.0), validated (boolean), created_by (ingestion_auto / ai_suggested / human_manual / promotion), notes. Self-reference prohibited by constraint. Alias: knowledge_relations, relationship. | Knowledge Item, Organisation, User | batch-a-entities, batch-b1-entities, batch-c, batch-de |
| KS.3 | Knowledge Type | Enumeration of the eight knowledge categories: Product API, Product UI/UX, Compliance/Rule, Implementation Pattern, Client Configuration, Support Knowledge, Decision Record, Procedure/SOP. Configurable taxonomy; extensible per org via knowledge_categories table with parent_category_id hierarchy. | Knowledge Item | batch-a-entities, batch-b1-entities |
| KS.4 | Validation Tier | Tier 1 (auto-approve) through Tier 4 (always flagged). Controls review routing for every knowledge item. Tier 4 represents AI-generated content — treated as hypothesis, never auto-trusted. | Knowledge Item | batch-a-entities, batch-b1-entities |
| KS.5 | Knowledge Promotion | Audit record for promoting client or engagement knowledge to product level. Fields: source_item_id, promoted_item_id, promoted_by, anonymisation_notes, approval_status (pending/approved/rejected), approved_by, approved_at. Every promotion requires Tier 2 human approval. | Knowledge Item, User | batch-a-entities, batch-b1-entities |
| KS.6 | Decision Record | What was decided, when, by whom, why; options considered; scope; status; source; confidence. First-class DB object — not just a note. Append-only (decisions cannot be undone, only superseded). Alias: Decision (first-class object), decision_record. | Knowledge Item, Work Item, Engagement, User | batch-a-entities, batch-b1-entities, batch-b3-part1, batch-c |
| KS.7 | Vault Document | Obsidian markdown file with YAML frontmatter stored in the knowledge vault. Embedded via Voyage AI into vault_embeddings table. Separate from operational knowledge_items — this is the design/documentation layer. | Knowledge Item, Project | batch-de |
| KS.8 | BPMN Process | Stored process model (L0/L1/L2) with Voyage AI embeddings. Two layers: .bpmn XML files (git source of truth) + bpmn_processes registry (DB, searchable). Alias: bpmn_processes. | Project, Knowledge Item, Areas | batch-c, batch-de |
| KS.9 | Query Log | Audit trail per /ask and /search query: query text, results, similarity scores, latency, feedback, session reference. Supports feedback loop. Alias: query_log. | Knowledge Item, User, Constrained Deployment | batch-a-entities, batch-b1-entities, batch-b2 |
| KS.10 | Query Feedback | User or agent feedback on /ask or /search result. Ratings: helpful/unhelpful/wrong/incomplete. Corrections promoted into new knowledge items. Alias: feedback_event. | Query Log, Knowledge Item | batch-a-entities, batch-b1-entities |

---

## Bounded Context 2: Tenant & Scope Hierarchy

Multi-tenant isolation and scope inheritance. Every knowledge item and platform action is scoped within this hierarchy.

| # | Entity | Description | Related Entities | Source Files |
|---|--------|-------------|-----------------|--------------|
| TH.1 | Organisation | Top-level tenant boundary. The company using the METIS platform (e.g., nimbus). Every knowledge item, user, and connector is associated with an organisation. Separate instances per enterprise customer. Alias: organisations. | Product, Client, Engagement, Knowledge Item, User, Connector Config, Credential | batch-a-entities, batch-b1-entities, batch-b2, batch-c, batch-de |
| TH.2 | Product | Second scope level — the customer's software product (e.g., time2work). Product knowledge is shared across all clients under that org. Alias: products. | Organisation, Client, Knowledge Item | batch-a-entities, batch-b1-entities, batch-c |
| TH.3 | Client | Third scope level — end-client of the organisation (e.g., Monash University). Client knowledge is strictly isolated; never shared with other clients. Alias: clients. | Organisation, Product, Engagement, Knowledge Item | batch-a-entities, batch-b1-entities, batch-c |
| TH.4 | Engagement | Leaf scope level. A specific project or implementation for a client. Has its own pipeline, knowledge scope, and isolation. Most granular level. Alias: engagements, Delivery Engagement. | Client, Delivery Pipeline, Knowledge Scope, Defect, Document, Release, Requirements | batch-a-entities, batch-b1-entities, batch-b3-part1, batch-c |
| TH.5 | Knowledge Scope | Defines which knowledge is accessible; scoped at Organisation / Product / Client / Engagement level. NULL FK fields enable scope inheritance downward (engagement scope automatically includes client and product knowledge). | Engagement, Constrained Deployment, Knowledge Item | batch-a-entities |
| TH.6 | User | Platform user with roles and RBAC permissions; tenant-scoped. Authors and validators of knowledge items. Alias: users, User/Role. | Organisation, Knowledge Item (created_by, validated_by), Session, User Org Access | batch-b1-entities, batch-b2, batch-c |
| TH.7 | User Org Access | User ↔ organisation permission record. Role per org. Supports RBAC. | User, Organisation | batch-b2 |

---

## Bounded Context 3: Delivery & Project Execution

Entities that track the delivery pipeline, configurations, releases, and project work items.

| # | Entity | Description | Related Entities | Source Files |
|---|--------|-------------|-----------------|--------------|
| DE.1 | Delivery Pipeline | BPMN-governed sequence of stages (requirements, config, testing, deployment, docs, support handoff) instantiated per engagement from a template. | Engagement, Pipeline Stage, Pipeline Gate, Template | batch-a-entities, batch-b3-part1 |
| DE.2 | Pipeline Stage | A single named stage within a delivery pipeline. | Delivery Pipeline, Pipeline Gate | batch-a-entities |
| DE.3 | Pipeline Gate | Named checkpoint in the delivery pipeline with a tier (mandatory / default-on / optional) and BPMN enforcement conditions. Alias: bpmn_gate. | Pipeline Stage, Test Result, Delivery Pipeline, BPMN Process | batch-a-entities, batch-b3-part1 |
| DE.4 | Requirements Document | Structured requirements produced for an engagement; parsed into individual requirement items; gap-checked before configuration begins. Alias: Requirements (Structured). | Engagement, Requirement Item, Configuration Item | batch-a-entities, batch-b3-part1 |
| DE.5 | Requirement Item | A single requirement within a requirements document. Linked to the configuration items it drives. | Requirements Document, Configuration Item | batch-a-entities |
| DE.6 | Configuration Item | A generated configuration entry for a product; includes value, source requirement reference, reasoning, uncertainty flags. Versioned; linked to requirements and audit trail. Alias: Configuration (Product). | Requirement Item, Engagement, Test Scenario, Release | batch-a-entities, batch-b3-part1 |
| DE.7 | Release | A versioned, tested, deployable package of configuration changes. Tracks state across development → UAT → production. Includes rollback capability. | Configuration Item, Environment, Test Suite, Engagement | batch-a-entities, batch-b3-part1 |
| DE.8 | Delivery Template | Reusable configuration, document, and test frameworks stored as KMS Category C knowledge. Built from each engagement and promoted for reuse. Alias: vertical_template, Template (Delivery). | Delivery Pipeline, Knowledge Item, Engagement | batch-a-entities, batch-b3-part1 |
| DE.9 | Living Document | Client-facing documentation generated from actual system state: configuration, requirements, test results, release history. Versioned; flagged for human review before client delivery. Alias: document, documents. | Engagement, Requirements Document, Test Result, Release History | batch-a-entities, batch-b2, batch-b3-part1 |
| DE.10 | Release History | Record of all deployments and releases for an engagement. Used in documentation generation. | Engagement, Living Document | batch-a-entities |
| DE.11 | Work Item | DB-backed unit of tracked work. Typed (8 default types). Status state machine (assigned → in_progress → blocked → done). Links to git artifact path. Aggregates into Initiative → Feature → Task hierarchy with status rollup from children. Alias: work_items. | Initiative, Feature, Task, Session, Audit Log, Engagement, Decision, Git Artifact | batch-b2, batch-b3-part1, batch-c, batch-de |
| DE.12 | Initiative | Top-level work breakdown entity. Status rolls up from child Features. | Feature, Work Item | batch-b3-part1 |
| DE.13 | Feature | Mid-level work breakdown entity. A deliverable chunk within an Initiative. State machine: draft → planned → in_progress → completed. plan_data JSONB for session recovery. | Initiative, Task, Work Item, Build Task, Feedback | batch-b3-part1, batch-de |
| DE.14 | Task / Build Task | Leaf-level work breakdown entity. What an agent picks up. Must be fully specified with verification criteria. State machine: todo → in_progress → completed. Alias: task, work_items. | Feature, Agent, Git Artifact, Session | batch-b3-part1, batch-de |
| DE.15 | Client Artifact | Typed deliverable per client (persona spec, config spec, integration spec, test plan). Versioned. Linked to work items and issue threads. Alias: Artifact / Deliverable. | Client Engagement, Work Item, Issue Thread | batch-b3-part1, batch-c |
| DE.16 | Client Timeline | Per-client record of planned vs actual progress, milestone status, historical UAT cycle durations, and release window constraints. | Engagement, Issue Thread, Release | batch-b3-part1 |

---

## Bounded Context 4: Quality & Testing

Entities representing test assets, defects, and quality intelligence.

| # | Entity | Description | Related Entities | Source Files |
|---|--------|-------------|-----------------|--------------|
| QT.1 | Test Suite | AI-generated collection of test scenarios from BPMN process maps and configuration knowledge. Expected vs actual result comparison framework. | BPMN Process, Configuration Item, Test Result | batch-b3-part1 |
| QT.2 | Test Scenario | An input/expected-output pair generated from a configuration item. Used for automated execution. Alias: test_scenario. | Configuration Item, Test Result, Test Suite | batch-a-entities |
| QT.3 | Test Result | Actual output from test execution; compared to expected; includes severity and potential cause for failures; fed back to development cycle. Alias: test_result. | Test Scenario, Test Suite, Regression Baseline, Defect, Release | batch-a-entities, batch-b3-part1 |
| QT.4 | Regression Baseline | Logged set of test results forming the historical baseline for regression detection. Alias: regression_baseline. | Test Result | batch-a-entities |
| QT.5 | Regression Scope | Computed set of features/modules needing retesting after a specific change; derived from BPMN cross-reference of what changed. | BPMN Process, Change, Test Suite | batch-b3-part1 |
| QT.6 | Defect | Structured defect record: steps to reproduce, expected vs actual, environment, module, severity, status, customer config context, related tickets. METIS is source of truth; synced to external trackers. Alias: defect, Defect/Support Ticket. | Engagement, Customer Config, Issue Thread, Defect Pattern, Jira Issue, Replication Scenario | batch-a-entities, batch-b3-part1 |
| QT.7 | Defect Pattern | Cross-customer recurring issue identified by semantic matching across defect records. Flagged for human review; never auto-escalated. | Defect, Customer, Quality Check | batch-b3-part1 |
| QT.8 | Replication Scenario | Environment-specific scenario for reproducing a defect; linked to customer environment access records (KMS Category D). | Defect, Customer Environment, Knowledge Item | batch-b3-part1 |
| QT.9 | Jira Issue | External Jira ticket synced from a METIS defect record. METIS is source of truth; Jira is synced to, not from. Alias: jira_issue. | Defect | batch-a-entities |
| QT.10 | Issue Thread | One-to-many container grouping every ticket across every system for a single client issue. Not resolved until all children are closed AND fix deployed and verified. AI-assisted linking with human confirmation. | Defect, Work Item, Client Engagement | batch-b3-part1, batch-c |
| QT.11 | Background Agent Job | Scheduled or triggered AI task with narrow scope and specific tools. Produces findings as work items, alerts, or knowledge items. Alias: Job, Scheduled Job. | Work Item, Alert, Knowledge Item, Project | batch-b3-part1, batch-c, batch-de |

---

## Bounded Context 5: Orchestration & Session

Entities that manage agents, sessions, context, and platform operations.

| # | Entity | Description | Related Entities | Source Files |
|---|--------|-------------|-----------------|--------------|
| OS.1 | Session | Agent work session record. Columns include: parent_id (for sub-agent nesting), protocol_version_id, interaction_count, context JSONB, summary, start/end timestamps, status. Alias: sessions. | Work Item, Audit Log, Scratchpad Entry, Protocol Version, Session Fact | batch-b2, batch-c, batch-de |
| OS.2 | Session Fact | Key-value notepad entries that survive context compaction. Written to DB immediately on discovery. Types: credential, config, endpoint, decision, note, data, reference. | Session, Knowledge Item | batch-b2, batch-c, batch-de |
| OS.3 | Scratchpad Entry | Agent working memory entries surviving context compaction. Categories: decision/discovery/blocker/context/handoff. Scopes: current_task/session/carry_forward. superseded_by_id for in-session updates. | Session, Work Item | batch-b2 |
| OS.4 | Cognitive Memory | 3-tier AI-learned knowledge: SHORT (session facts, auto), MID (working knowledge, default), LONG (proven patterns, promoted or explicit), ARCHIVED (decayed). Promotable through lifecycle. Alias: cognitive_memory. | Knowledge Item, Session | batch-c, batch-de |
| OS.5 | Activity Space | First-class entity defining current work context for WCC detection. Fields: name, aliases, knowledge_refs, workfile_refs, feature_refs, vault_queries, co_access_log, lifecycle state (created → active → semi-active → archived). Alias: Activity. | Work Context Container, Knowledge Item, Workfile, Feature | batch-c, batch-de |
| OS.6 | Work Context Container | Budget-capped bundle assembled from 6 knowledge sources for a given activity. Scoping and assembly mechanism. Not a permanent store — computed on demand and cached. | Activity, 6 source entity types | batch-c, batch-de |
| OS.7 | Workfile | Component-scoped cross-session working context. UPSERT key: (project, component, title). Voyage AI embedding for semantic search. is_pinned flag surfaces items at session start. Mode=append concatenates with separator. | Activity, Project, Session | batch-de |
| OS.8 | Agent Registration | Record of a registered agent type with its constrained deployment profile, capabilities, and tool restrictions. Alias: agent_registration. | Constrained Deployment | batch-a-entities |
| OS.9 | Agent Message | Inter-agent communication log for agent teams coordination. Schema not yet fully defined. | Session | batch-b2 |
| OS.10 | Protocol Version | Versioned agent protocol text. Stores verbatim rule text, word_count, change_reason, changed_by, diff_from_previous, compliance_scores JSONB. Agents propose; humans activate. Alias: protocol_versions. | Compliance Check, Session | batch-b2 |
| OS.11 | Compliance Check | Individual compliance check result per session. Supports automated and LLM-as-judge measurement results. | Session, Protocol Version, Compliance Summary | batch-b2 |
| OS.12 | Compliance Summary | Periodic rollup of compliance checks for dashboard and trend analysis. | Compliance Check | batch-b2 |

---

## Bounded Context 6: Integration & Security

Entities that manage external system connections, credentials, and platform security.

| # | Entity | Description | Related Entities | Source Files |
|---|--------|-------------|-----------------|--------------|
| IS.1 | Connector Config | Per-organisation configuration for each external system connector. Fields: connector_type (enum), base_url, auth_config JSONB (encrypted), rate_limits JSONB, field_mappings JSONB, custom_config JSONB, direction (read/write/bidirectional), is_active. Hot-swappable without restart. Alias: connector_configs, Connector Config. | Organisation, Credential | batch-b1-entities, batch-c, batch-de |
| IS.2 | Credential | Encrypted API credentials. Per-org, per-service. AES-256 at rest in Phase 1. Pluggable interface for future HashiCorp Vault / AWS Secrets Manager / Azure Key Vault backends. Per-user credential delegation supported. | Organisation, Connector Config | batch-b2, batch-c |
| IS.3 | Audit Log | Immutable, append-only record of every platform action. Columns: session_id, user_id, agent_id, action, target, detail, timestamp. Covers: state machine transitions, human approvals, agent actions, security events, writes/deletes. Three-tier retention: permanent (security/writes/approvals), configurable 6–12 months (conversations, context), short/aggregated (routine reads). Never updated or deleted. Alias: audit_log, audit_trail, event_store. | Session, User, All entities | batch-a-entities, batch-b2, batch-c, batch-de |
| IS.4 | Workflow Instance | SpiffWorkflow state persistence. JSON-serialised workflow state surviving across sessions and crashes. Required for Tier 1 BPMN enforcement. Schema not yet fully defined. Alias: workflow_instances. | Workflow Execution Log | batch-b1-entities |
| IS.5 | Workflow Execution Log | Step-level execution log per workflow instance. Per step: instance ID, process definition, entered/completed/skipped, time per step, actor (Claude/human/system), deviations from expected path. | Workflow Instance | batch-b1-entities |
| IS.6 | DMN Decision Table | Storage for DMN rule tables. Version-controlled definitions vault; runtime state in database. Explicit, testable, auditable — all decision points expressed here, not embedded in prompts. Schema not yet defined. Alias: dmn_decision_tables. | Workflow Instance | batch-b1-entities |

---

## Bounded Context 7: Commercial

Entities supporting the commercial and subscription model.

| # | Entity | Description | Related Entities | Source Files |
|---|--------|-------------|-----------------|--------------|
| CM.1 | Subscription Contract | Per-client commercial agreement: base monthly price, term (typically 24 months), enhancement line items, billing schedule. | Client, Enhancement, Revenue Share | batch-b3-part1 |
| CM.2 | Enhancement | Named capability addition to a subscription. Priced as annual uplift; adds to contract value incrementally. Alias: enhancement. | Subscription Contract, Feature | batch-b3-part1 |
| CM.3 | Constrained Deployment | A configured AI deployment: system prompt, knowledge scope, cached payload (up to 200K tokens), Haiku input classifier, tool restrictions, deployment channel. Used for both internal staff and external/client-facing deployments. Alias: constrained_deployment. | Knowledge Scope, System Prompt, Deployment Channel, Agent Registration | batch-a-entities |
| CM.4 | Deployment Channel | Channel through which a constrained deployment is published: web UI, Slack, API. Alias: deployment_channel. | Constrained Deployment | batch-a-entities |

---

## Entity Relationship Overview

The bounded contexts interact through five primary dependency chains:

**Tenant Hierarchy is the root.** Every entity in every other bounded context carries a scope reference (org_id, product_id, client_id, engagement_id). Knowledge items, sessions, connectors, and credentials all anchor to Organisation at minimum.

**Knowledge Store feeds Delivery & Project Execution.** Configuration generation queries knowledge_items; implementation patterns drive config generation; decision records link to work items. The Knowledge Engine is the source of context for all other areas.

**Delivery Execution produces Quality inputs.** Configuration items produce test scenarios; pipeline gates require test results to pass; releases bundle validated configurations. The delivery bounded context creates the artifacts that Quality validates.

**Quality outputs feed back to Knowledge.** Test results, defect resolutions, and defect patterns become KMS candidates via the knowledge promotion process. Support knowledge is the primary growth vector for the knowledge base over time.

**Orchestration & Session is the runtime layer.** Sessions anchor all live work; audit logs record all transitions; scratchpad entries preserve state across context boundaries. The session and cognitive memory entities are infrastructure that all other bounded contexts depend on at runtime.

**Integration & Security enforces the perimeter.** All external system access flows through connector configs and credentials. The audit log is the shared immutable record for all bounded contexts — it has no foreign key limitations and records events from every other context.

---

## Coverage Check

| Area | Entity Count | Notes |
|------|-------------|-------|
| 1 — Knowledge Engine | 10 (KS context) | Core knowledge store fully represented |
| 2 — Integration Hub | 2 (IS.1, IS.2) | Connector config and credential; connector lifecycle is process, not entity |
| 3 — Delivery Accelerator | 16 (DE context) | Full pipeline entity set including work hierarchy |
| 4 — Quality & Compliance | 11 (QT context) | Test, defect, and pattern entities |
| 5 — Support & Defect Intelligence | Covered by QT.6–QT.10 | Defect, pattern, replication, issue thread |
| 6 — Project Governance | DE.11–DE.16 | Work items, timeline, artifacts |
| 7 — Orchestration & Infrastructure | 12 (OS context) | Session, memory, context, agent entities |
| 8 — Commercial | 4 (CM context) | Contract, enhancement, deployment, channel |
| 9 — BPMN / SOP & Enforcement | IS.4–IS.6, KS.8, OS.10–12 | Workflow instances, DMN, protocol, compliance |
| Security / Cross-cutting | IS.3 (Audit Log) | Single audit log serves all areas |

---

*Gate One Doc 3 | Draft: 2026-03-11 | Consolidated from 6 extraction batches (batch-a, batch-b1, batch-b2, batch-b3, batch-c, batch-de)*

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-one/data-entity-map.md
