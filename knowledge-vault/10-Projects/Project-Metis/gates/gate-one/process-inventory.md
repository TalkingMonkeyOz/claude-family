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

# Process Inventory

Gate One Document 1.

## Purpose

Comprehensive inventory of all processes identified across the METIS platform. This is an INVENTORY — process names, descriptions, actors, and area assignments. Detailed process design (BPMN models) is Gate 2 work.

Aliases are listed where multiple batches named the same process differently. The richest description from all sources is preserved.

## Summary

- Total processes: 54 (after deduplication from ~175 raw entries)
- Areas covered: 9/9 plus Cross-cutting
- Sources: 6 extraction batches from ~40 vault documents

---

## Area 1: Knowledge Engine

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 1.1 | Ingest Knowledge | Content received; type determined (one of 8 types); chunked at natural boundaries per type; embedded via Voyage AI (1024-dim); stored in knowledge_items with metadata, scope, and validation tier; audit trail written. Alias: Knowledge Ingestion Pipeline, Knowledge Ingestion & Validation. | Enterprise Admin, PS Consultant (senior), Knowledge Ingestion Agent | batch-a-processes, batch-b1-part1, batch-c, batch-de |
| 1.2 | Ingest Product API Knowledge | Ingest Swagger/OpenAPI or OData metadata. One knowledge item per endpoint/entity. Tier 1 auto-approved. Triggered on product release. | Ingestion Agent, API Parser | batch-b1-part1 |
| 1.3 | Ingest Product UI/UX Knowledge | Automated screen discovery (Playwright) or manual upload; semi-automated extraction; Tier 2 human review. | Playwright Agent, Human Reviewer | batch-b1-part1 |
| 1.4 | Ingest Compliance/Rule Knowledge | Human-upload plus AI-assisted extraction of regulatory documents, Enterprise Agreements, rule definitions. Tier 2 mandatory human approval. Award knowledge is compliance-critical. | Domain Expert, Human Reviewer | batch-b1-part1 |
| 1.5 | Ingest Implementation Patterns | Capture past implementations and consultant expertise using scenario/steps/rationale/gotchas template. Tier 2 senior approval required. | Senior Consultant, Approval Reviewer | batch-b1-part1 |
| 1.6 | Ingest Support Knowledge | AI extracts problem, root cause, resolution from support tickets. One item per resolution pattern. Semantic deduplication across tickets. Tier 3 auto-ingested with confidence flag. | Support Triage Agent, Ticketing System | batch-b1-part1 |
| 1.7 | Ingest Decision Records | Meeting notes and documented decisions captured. Append-only immutable storage. Tier 3 auto-ingested, flagged for review. | Meeting Notes System, Human Contributor | batch-b1-part1 |
| 1.8 | Route Knowledge to Validation Tier | Determines Tier 1–4 assignment: Tier 1 auto-approves, Tier 2 queues for senior review, Tier 3 flags low-confidence, Tier 4 always flagged. Routes the item to the appropriate review workflow. Alias: Validation Tier Routing, Knowledge Validation Workflow. | Knowledge Ingestion Agent, PS Consultant (senior), Enterprise Admin | batch-a-processes, batch-b1-part1 |
| 1.9 | Query Knowledge (Ask) | User or agent submits natural-language question; classifier gates it; vector search finds top-N chunks; optional rerank; graph walk adds structurally connected items; LLM assembles answer with citations and confidence score. Alias: Knowledge Query, Knowledge Q&A. | PS Consultant, Support Staff, Developer, Enterprise Admin, any agent | batch-a-processes, batch-b1-part1, batch-c, batch-de |
| 1.10 | Search Knowledge (Retrieve) | Semantic search returning ranked knowledge items without LLM synthesis. Faster and cheaper than Ask; used when retrieved items themselves are the output. | Agent, Knowledge Engine | batch-b1-part1, batch-de |
| 1.11 | Walk Knowledge Graph | After vector search returns top-N items, traverse 1–2 hops through knowledge_relations to surface structurally connected items not caught by direct vector similarity. Items added to LLM context at lower priority. Alias: Graph Walk / Structural Retrieval, Knowledge Relationship Walk. | System (automated) | batch-a-processes, batch-b1-part1, batch-c |
| 1.12 | Score Confidence | Aggregate similarity scores and source count into a confidence indicator returned with every answer. Flag low-confidence answers for human review. | System (automated) | batch-a-processes |
| 1.13 | Suggest Knowledge Relationships | Background analysis of newly ingested items against existing items; AI suggests typed relationships; human validates; approval rate tracked per relationship type — auto-validation unlocked above 90% over 50+ samples for that type. Alias: AI Relationship Suggestion Process. | Knowledge Quality Agent, Human Reviewer | batch-a-processes, batch-b1-part1 |
| 1.14 | Promote Knowledge | Client-specific item selected; system generates generalised version stripping client detail; senior reviewer approves; promoted item created with supersedes relationship and full audit trail. Never automatic — always requires Tier 2 validation. Alias: Knowledge Promotion Workflow. | PS Consultant (senior), Knowledge Manager, Knowledge Quality Agent | batch-a-processes, batch-b1-part1, batch-c |
| 1.15 | Detect Knowledge Staleness | Event-driven check: when a dependency changes, flag affected knowledge items for review. Not time-driven. Scheduled/event-driven scan also checks for gaps and drift. Alias: Knowledge Staleness Check, Knowledge Decay/Promotion/Freshness. | Knowledge Quality Agent, System | batch-a-processes, batch-c, batch-de |
| 1.16 | Re-embed Knowledge | Bulk re-embed all knowledge items when embedding provider is switched. Interface supports batch operations. Every item stores embedding_model and embedding_dimensions so drift is detectable. | Embedding Provider, Admin | batch-b1-part1 |
| 1.17 | Log Query and Feedback | Every query, result set, latency, similarity scores, and user feedback logged. User/agent feedback (helpful/unhelpful/wrong/incomplete) can correct or enrich knowledge items. Feeds retrieval improvement loop. Alias: Query & Feedback Logging, Query Feedback Loop. | System (automated), User, Agent | batch-a-processes, batch-b1-part1 |
| 1.18 | Evaluate Knowledge Retrieval Quality | Measure retrieval quality against a 50-question test set; three metrics tracked (precision, relevance, confidence accuracy). Separate from feedback loop — this is periodic formal evaluation. | QA Agent, Platform Builder | batch-c |

---

## Area 2: Integration Hub

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 2.1 | Manage Connector Lifecycle | connect(), health_check(), disconnect() lifecycle for each external system. Credential rotation supported without system restart. Circuit breaker opens after N failures; half-open test after timeout. Alias: Connector Connection Management. | Connector, Credential Manager | batch-b1-part1 |
| 2.2 | Read from External System | read() / batch_read() with pagination through connector interface. Business logic never calls external APIs directly. Includes time2work REST, OData, Confluence, Salesforce, Granola, and other configured connectors. Alias: External System Read. | Connector, Business Logic | batch-b1-part1, batch-c, batch-de |
| 2.3 | Write to External System | write() / batch_write() through connector interface. Bulk push with per-item error handling. Includes defect sync to Jira, config push to time2work, status updates to Slack. Alias: External System Write. | Connector, Business Logic | batch-b1-part1 |
| 2.4 | Monitor Connector Health | Regular connectivity checks per connector. Alert on failures. Circuit breaker logic. | Health Monitor, Connector | batch-b1-part1 |
| 2.5 | Discover Connector Schema | get_schema() returns available entities, fields, and types for an external system. Used at ingestion time and for mapping. | Connector, Integration Hub | batch-b1-part1 |
| 2.6 | Configure Connector for Engagement | Integration connector configured for a client's external systems (e.g., Jira, time2work API) when engagement is created. Direction (read-only / write / bidirectional) set explicitly — default read-only. Alias: Connector Configuration. | Enterprise Admin | batch-a-processes, batch-de |

---

## Area 3: Delivery Accelerator

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 3.1 | Create Engagement | Engagement record created; client isolation established; knowledge scope created; delivery pipeline instantiated from template BPMN; stages configured (requirements, config, testing, deployment, docs); connector configured; audit trail opened. Alias: Engagement Creation. | Project Manager, Delivery Lead, Enterprise Admin | batch-a-processes |
| 3.2 | Execute Delivery Pipeline | Six-stage pipeline: Requirements → Configuration → Validation/Test → Deployment → Documentation → Support Handoff. BPMN-defined, configurable per customer within system-enforced bounds. Human checkpoint at each stage gate. Alias: Delivery Pipeline Execution (Generic). | PS Consultant, AI agent, Client | batch-b1-part1, batch-b3-part1, batch-c, batch-de |
| 3.3 | Parse and Collate Requirements | AI collates inputs from meetings, emails, and documents into structured requirements; gaps and ambiguities flagged before configuration begins; every configuration item traced back to a validated requirement. Alias: Requirements Parsing, Requirements Collation & Interpretation. | Design Agent, PS Consultant | batch-a-processes, batch-b3-part1 |
| 3.4 | Generate Configuration | Knowledge Engine queried for matching patterns; configuration generated using API schema knowledge plus implementation patterns; each item traced to source requirement; uncertainty explicitly flagged for human review. Alias: Configuration Generation. | Coder Agent, Design Agent, PS Consultant | batch-a-processes, batch-b3-part1, batch-c |
| 3.5 | Review and Approve Configuration | Consultant reviews proposed configuration, adjusts if needed, approves; approved configuration pushed to UAT. Human-in-the-loop gate — cannot be skipped by agents. Alias: Human Review of Generated Config. | PS Consultant | batch-a-processes |
| 3.6 | Push Configuration to Environment | Approved configuration pushed to target environment (UAT or production) via API connector. Includes change detection and client-visible changelog. Alias: Config Push to UAT, UAT-to-Production Promotion. | System, PS Consultant | batch-a-processes, batch-b3-part1 |
| 3.7 | Generate Living Documentation | Reads actual configuration via API; maps config to requirements; pulls test results and release history; assembles via audience-appropriate template; versions and stores output. Real-time DB writes plus periodic re-generation (~4x daily embeddings, nightly batch). Never more than a day out of date. Alias: Documentation Generation. | Documentation Agent, Delivery Lead, PS Consultant | batch-a-processes, batch-b3-part1, batch-c |
| 3.8 | Onboard Customer | 7-step sequence: product knowledge ingestion → domain capture → tool integration → deployment configuration → validation → first engagement → compound. Platform gets smarter with every subsequent engagement. Alias: Customer Onboarding Pipeline. | Enterprise Admin, PS Consultant | batch-a-processes |
| 3.9 | Hand Off to Support | Transfer full engagement history and implementation context to support team via KMS; confirm handoff completeness. | Consultant, Support | batch-b3-part1 |

---

## Area 4: Quality & Compliance

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 4.1 | Generate Test Scenarios | Test scenarios (input → expected output) generated from configuration items and BPMN process maps. Alias: Test Scenario Generation. | Test Agent, Developer | batch-a-processes, batch-b3-part1 |
| 4.2 | Execute Tests | Scenarios submitted to target system (time2work) via API or Playwright for UI tests; actual outputs captured; expected vs actual compared; discrepancies flagged with severity and potential cause. Alias: Test Execution, Expected vs Actual Comparison, Validation Test Execution, UI Validation. | Test Agent, QA Agent | batch-a-processes, batch-b3-part1, batch-c |
| 4.3 | Log Regression Baseline | Test results logged to form regression baseline for future runs; regression scope automatically computed from BPMN cross-reference when a change occurs. Alias: Regression Baseline Logging, Regression Analysis (Change-Triggered). | System (automated), AI agent | batch-a-processes, batch-b3-part1 |
| 4.4 | Run Background Quality Jobs | Scheduled or event-triggered AI tasks: post-deployment regression, customer feedback pattern matching, daily lifecycle gate compliance check, weekly test coverage gap review, external rule change re-validation. Alias: Background Agent Quality Jobs. | AI agent (autonomous) | batch-b3-part1, batch-c |
| 4.5 | Discover External Rule Changes | Four signal sources: code changes (primary), API monitoring, manual triggers, scheduled scans. Flags affected knowledge items and configurations for re-validation. | System monitor, Human trigger | batch-de |

---

## Area 5: Support & Defect Intelligence

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 5.1 | Capture and Structure Defect | Natural-language description received; AI structures into steps / expected / actual / environment / module; completeness-checked before submission. Alias: Defect Capture, Defect Capture Workflow. | Support Staff, Tester, PS Consultant | batch-a-processes, batch-b1-part1, batch-c |
| 5.2 | Triage Support Issue | Client reports issue → AI asks clarifying questions based on customer config → cross-references KMS → suggests replication scenario → pre-populates structured ticket. Alias: Support Ticket Triage, Support Triage (AI-Assisted). | AI agent, Support Staff | batch-b1-part1, batch-b3-part1, batch-c |
| 5.3 | Check for Duplicate Defect | New defect checked semantically against existing defects before creating new record. Keyword matching explicitly insufficient; vector similarity required. Alias: Semantic Duplicate Check, Duplicate Detection. | Analysis Agent, AI agent | batch-a-processes, batch-b3-part1 |
| 5.4 | Check Cross-Client Impact | Defect checked for potential impact across other clients on same platform. AI must not auto-escalate; human decides: escalate to Quality, request product fix, update docs, or trigger training. Alias: Cross-Client Impact Check, Cross-Customer Pattern Detection. | Analysis Agent, Human Reviewer | batch-a-processes, batch-b3-part1 |
| 5.5 | Suggest Defect Severity | AI analyses defect impact and suggests severity rating; human confirms. | Analysis Agent | batch-a-processes |
| 5.6 | Sync Defect to External Tracker | Defect record synced bidirectionally to external Jira instance via connector. METIS is source of truth; Jira synced to, not from. Alias: Jira Sync (Defect), Defect Lifecycle Tracking. | System (automated) | batch-a-processes, batch-b3-part1 |
| 5.7 | Promote Defect Resolution to KMS | End-of-day or sprint: AI summarises resolved defects, suggests KMS candidates, drafts entry; human approves → KMS Category F Tier 3. Alias: Knowledge Promotion (Defect to KMS). | AI agent, Human Reviewer | batch-b3-part1 |
| 5.8 | Investigate Customer Scenario | Check KMS → check code → form hypotheses → test → resolve. Not just environment cloning — structured investigation with AI assistance. Alias: Customer Scenario Investigation. | Support Staff, AI investigation agent | batch-de |

---

## Area 6: Project Governance

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 6.1 | Score Project Health | Data aggregated from pipeline, defects, tests, documentation, and KE logs; weighted health score computed. Feeds dashboard and alert generation. Alias: Health Score Calculation, Project Health Scoring. | Health Monitor, Master AI, AI agent | batch-a-processes, batch-b3-part1, batch-c |
| 6.2 | Generate Automated Status Report | AI generates project status reports by pulling data from all connected systems; highlights on-track, at-risk, needs-attention items; no manual assembly required. Alias: Alert Generation, Automated Status Report Generation. | Health Monitor, Notification Agent, AI agent | batch-a-processes, batch-b3-part1 |
| 6.3 | Manage Work Item Lifecycle | Work items flow through Initiative → Feature → Task hierarchy with BPMN-enforced gates at each tier transition; status rolls up from children. Alias: Work Item Lifecycle Management. | Platform, AI agent | batch-b3-part1, batch-c, batch-de |
| 6.4 | Route Work Item to Lifecycle Tier | Classify incoming work items into three tiers: Freeform (no gates), Structured (client sign-off gate), Pipeline (five-layer validation). Structured escalates to Pipeline if code changes are required. Alias: Work Item Routing. | AI agent, Project Manager | batch-b3-part1 |
| 6.5 | Capture Decision | Every significant decision recorded as first-class DB object: who requested, AI recommendation, who approved, what was tested. Compliance-flagged items retained indefinitely. Alias: Decision Capture and Audit Trail. | AI agent, Project Manager, Approver | batch-b3-part1, batch-c |
| 6.6 | Manage Issue Thread | One client issue = one thread linking every ticket across every system; thread not resolved until all child items are closed AND fix deployed and verified; AI-assisted linking with human confirmation. | AI agent, Project Manager, Support | batch-b3-part1, batch-c |
| 6.7 | Track Timeline Intelligence | Tracks realistic elapsed time per stage including client UAT cycles, CAB windows, and release freezes; learns from historical data; surfaces realistic delivery dates; flags unrealistic targets. | AI agent, Project Manager | batch-b3-part1, batch-c |
| 6.8 | Generate Proactive PM Alerts | Surfaces actionable alerts: stale defects, missing specs for upcoming sprints, release date risk, open threads with no progress. Every alert includes a call to action. | AI agent | batch-b3-part1, batch-c |
| 6.9 | Reconcile Plan vs Reality | Compares planned milestones against actual completion state; identifies invalidated assumptions; suggests plan adjustments; generates honest status reports from actual data. | AI agent, Project Manager | batch-b3-part1 |

---

## Area 7: Orchestration & Infrastructure

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 7.1 | Manage Agent Session Lifecycle | Start → work (update context, increment interactions) → end. Parent/child sessions for sub-agent nesting. Resume on crash via session ID. Alias: Agent Session Lifecycle, Session Lifecycle. | Lead Agent, Sub-Agents, Platform | batch-b2-part1, batch-c, batch-de |
| 7.2 | Assemble Context | Given current activity, assemble prompt from 8 ordered components: system prompt → cached knowledge (Tier 1) → session context → RAG results (Tier 2) → task context → conversation history → user query → core protocol rules. Budget-cap to fit context window. Alias: Context Assembly, Work Context Assembly. | Platform (automatic) | batch-b2-part1, batch-c, batch-de |
| 7.3 | Manage Token Budget | Active component tracks token usage across all prompt components. Sheds lowest-priority material first when budget is tight. Never drops system prompt, core protocol, current task, or carry-forward items. | Token Budget Manager (platform service) | batch-b2-part1 |
| 7.4 | Assemble Knowledge Cache | Build-time or scheduled: fetch Tier 1 knowledge items, score by priority, pack to token budget (up to 200K), store for prompt caching, log inclusions/exclusions, alert on gaps. | Cache Assembly Script | batch-b2-part1 |
| 7.5 | Hand Off Between Agents | Orchestrator creates handoff package (carry-forward scratchpad, open work items, key decisions, engagement context). Receiving agent gets clean context plus targeted package only — not full previous session history. Alias: Cross-Agent Handoff. | Orchestrator, Source Agent, Receiving Agent | batch-b2-part1 |
| 7.6 | Survive Context Compaction | Agent writes discoveries and decisions to scratchpad DB immediately → context compaction drops conversation → agent re-reads scratchpad to recover state. Periodic refresh every ~20 interactions. Alias: Compaction Survival (Write-Through Scratchpad). | Agent | batch-b2-part1 |
| 7.7 | Consolidate Cognitive Memory | SHORT session facts promoted to MID working knowledge; MID promoted to LONG proven patterns; stale items decay; low-confidence items archived. Runs on session end and 24h periodic schedule. | System (automated) | batch-c, batch-de |
| 7.8 | Configure Constrained Deployment | System prompt assembled from template plus config; knowledge scope defined; cached payload up to 200K tokens; Haiku classifier configured; tool restriction applied; 5-question validation before publishing to channel. Alias: Constrained Deployment Configuration, Constrained Deployment Setup. | Enterprise Admin, Platform Builder | batch-a-processes, batch-c |
| 7.9 | Register and Deploy Agent | New agent type registered with constrained deployment profile and capabilities. Architecture supports new agent types without structural changes. Alias: Agent Registration. | Platform Builder, Enterprise Admin | batch-a-processes |
| 7.10 | Execute CI/CD Pipeline | Push/PR triggers 5-stage pipeline: install → lint → typecheck → test (with coverage) → build. Stage failure blocks progression. Target: under 5 minutes. | Azure DevOps Pipelines | batch-b2-part1 |
| 7.11 | Execute Master AI Run Sheet | Master AI executes scheduled run sheet: checks system health, triggers maintenance tasks, monitors agent performance, escalates anomalies. Alias: Master AI Run Sheet Execution. | Master AI | batch-a-processes |
| 7.12 | Manage Feature Lifecycle | idea → design → code → test → deploy → maintain. BPMN-governed with per-task loop. Alias: Feature Lifecycle. | Developer, Claude instance | batch-de |
| 7.13 | Capture System Failure | Hook fails → log to JSONL → auto-file as feedback in DB → surface on next prompt → Claude reviews → fix or defer. Closed self-improvement loop. Alias: Failure Capture Loop. | System (automated), Claude instance | batch-de |

---

## Area 8: Commercial

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 8.1 | Manage Subscription Contract | Per-client commercial agreement with base monthly price, term, enhancement line items, and billing schedule. Enhancements priced as annual uplift, adding to contract value incrementally. | Account Manager, Enterprise Admin | batch-b3-part1 |

---

## Area 9: BPMN / SOP & Enforcement

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| 9.1 | Enforce Deployment Gate (BPMN) | BPMN gate evaluated at deployment; deployment locked until critical tests pass. Applies to both knowledge ingestion and configuration deployment. Alias: BPMN Deployment Gate Enforcement. | BPMN Agent, Delivery Lead | batch-a-processes, batch-b1-part1 |
| 9.2 | Run Guided Workflow (Tier 1 SpiffWorkflow) | Full SpiffWorkflow runtime-enforced process for high-stakes operations. Claude is a worker within the workflow, not the controller. Applies to: knowledge validation, client configuration change, deployment/release, pay scenario test cycle. Alias: Knowledge Validation BPMN Workflow, Client Configuration Change Workflow, Deployment/Release Pipeline, Pay Scenario Test Cycle. | SpiffWorkflow, Claude Agent, Human Approver | batch-b1-part1 |
| 9.3 | Run Structured Checklist Workflow (Tier 2) | Database-backed checklist with validation gates for medium-stakes operations. Applies to: support ticket triage, defect capture, documentation generation, standard data import. | Defect Agent, Support Triage Agent, Documentation Agent | batch-b1-part1, batch-c |
| 9.4 | Detect BPMN Alignment Gap | Identify deviations between modelled processes and actual execution. Auto-file deviation as feedback. Trigger process redesign review. | Gap Detection Agent, BPMN Engine | batch-b1-part1 |
| 9.5 | Validate Domain Boundary (DDD Check) | Verify a proposed change respects bounded context definitions. Domain events defined for cross-boundary communication triggers. Ubiquitous language enforced. Alias: DDD Boundary Validation. | DDD Validator | batch-b1-part1 |
| 9.6 | Run Five-Layer Design Validation | Proposed change passes all five layers in sequence: DDD check → BPMN flow → DMN decision → Ontology impact → Event record. Any layer failure blocks progression. Alias: Five-Layer Validation Pipeline, Design Validation (Five-Layer Stack). | All layers, Claude Agent, Human Reviewer | batch-b1-part1, batch-de |
| 9.7 | Re-validate After Rule Change | Compliance rule change detected → flag affected knowledge items → human validates → ontology identifies affected configurations → re-validation triggered → configurations deployed (all as immutable events). Alias: Award Rule Change Re-validation. | Ontology Engine, Knowledge Engine, Compliance Reviewer | batch-b1-part1 |
| 9.8 | Monitor Internal Process Compliance | Daily check: are open work items following proper BPMN lifecycle gates? Flag non-compliance for human review. Alias: Internal Process Compliance Monitoring. | AI agent | batch-b3-part1 |
| 9.9 | Measure Agent Compliance | Three-layer cycle: automated checks every session → Haiku LLM-as-judge on 10% sample → human review monthly. Produces compliance scores per agent per period. Compliance scores stored per protocol version for A/B comparison. Alias: Agent Compliance Measurement. | Compliance System, Haiku Judge, Human Reviewer | batch-b2-part1 |
| 9.10 | Manage Protocol Version | Human creates new protocol version; agents can propose but cannot activate. Word count tracked across versions. Rule evolution requires: identify failing rule → document proposed change → create new version → A/B test → compare compliance metrics → accept/reject. | Human (John), Compliance System | batch-b2-part1 |

---

## Cross-cutting

| # | Process | Description | Actors | Source Files |
|---|---------|-------------|--------|--------------|
| X.1 | Manage Three-Layer Code Review | CI automated checks → Agent Review (checks diff against conventions, security, ADRs) → Human spot-check (reviews the review output, not raw code). | CI Pipeline, Review Agent (Opus 4.6), John | batch-b2-part1 |
| X.2 | Execute Dog-Fooding Loop | Platform uses itself — KMS stores self-knowledge, pipeline tracks own releases, quality tools test own code. Same supervised, gate-enforced pattern applied to building METIS as to client work. Dual-lens principle. Alias: Dog-Fooding Loop. | All platform agents | batch-de |
| X.3 | Enforce Continuous Cross-Session State | Event chain captures work across sessions. Module modified months later → event history shows dependencies → re-validation triggered. Enables cross-session dependency tracking and longitudinal audit. Alias: Cross-Session State Continuity. | Event Store, Ontology Engine | batch-b1-part1 |

---

## Coverage Check

| Area | Process Count | Notes |
|------|--------------|-------|
| 1 — Knowledge Engine | 18 | Full coverage including ingestion subtypes, retrieval, promotion, staleness, evaluation |
| 2 — Integration Hub | 6 | Connector lifecycle, read/write, health, schema, per-engagement config |
| 3 — Delivery Accelerator | 9 | Full pipeline plus onboarding and handoff |
| 4 — Quality & Compliance | 5 | Test generation, execution, regression, background jobs, external rule change |
| 5 — Support & Defect Intelligence | 8 | Full triage, capture, dedup, cross-client, severity, sync, promote, investigate |
| 6 — Project Governance | 9 | Health scoring, status reports, work item lifecycle, issue threads, timelines, PM alerts |
| 7 — Orchestration & Infrastructure | 13 | Session, context, cache, handoff, compaction, memory, deployment, CI/CD, run sheet |
| 8 — Commercial | 1 | Subscription management; detailed commercial processes deferred |
| 9 — BPMN / SOP & Enforcement | 10 | Gate enforcement, guided workflows, gap detection, DDD, five-layer, agent compliance |
| Cross-cutting | 3 | Code review, dog-fooding, cross-session continuity |
| **Total** | **54** | All 9 areas covered |

---

*Gate One Doc 1 | Draft: 2026-03-11 | Consolidated from 6 extraction batches (batch-a, batch-b1, batch-b2, batch-b3, batch-c, batch-de)*

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-one/process-inventory.md
