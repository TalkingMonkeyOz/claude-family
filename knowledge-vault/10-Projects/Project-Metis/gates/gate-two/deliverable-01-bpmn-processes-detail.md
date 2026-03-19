---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/1
  - type/bpmn
status: complete
---

# Gate 2 Deliverable 1: Process Flow Detail

Full step tables for all 9 processes. Parent doc: [[gate-two/deliverable-01-bpmn-processes|BPMN Processes Index]].

---

## P1 · Knowledge Ingestion {#p1}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | System | Receive content submission | Content in queue |
| 2 | Ingestion Agent | Determine content type (8 types) | Type assigned |
| 3 | Ingestion Agent | Route to type-specific parser | Parsed content |
| → G1 | — | Content type deterministic? | — |
| 4 | Ingestion Agent | Chunk at natural boundaries per type | Chunks |
| 5 | Embedding Service | Generate 1024-dim embedding (Voyage AI) | Embedding vector |
| → G4 | — | Embedding succeeded? | — |
| 6 | Ingestion Agent | Check semantic deduplication | Duplicate flag |
| → G3 | — | Semantic duplicate? | — |
| 7 | System | Assign validation tier (1–4) | Tier assigned |
| → G2 | — | Tier 1? | — |
| 8a | System | Auto-approve (Tier 1) | Status = approved |
| 8b | Domain Expert | Queue for human review (Tier 2+) | Review task created |
| 9 | System | Store KnowledgeItem + audit trail | `KnowledgeIngested` event |
| 10 | System | Suggest knowledge relationships | Relationship candidates |

---

## P2 · Knowledge Retrieval (RAG) {#p2}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | User/Agent | Submit natural-language query | Query string |
| 2 | Classifier | Gate query (in-scope check, Haiku model) | Pass/reject |
| → G1 | — | Query in scope? | — |
| 3 | Knowledge Engine | Vector search (embeddings only) — top-N chunks | Ranked chunks |
| → G2 | — | Results above similarity threshold? | — |
| 4 | Knowledge Engine | Walk graph 1–2 hops from top-N items (Apache AGE on PG18 — Phase 1) | Additional items |
| → G3 | — | Graph walk adds relevant items? | — |
| 5 | Knowledge Engine | Merge and re-rank (6-signal ranking pipeline) | Final ranked set |
| → G4 | — | LLM synthesis requested? | — |
| 6a | LLM | Assemble answer with citations | Answer + citations |
| 6b | System | Return ranked chunks (search mode) | Chunk list |
| 7 | System | Calculate confidence score | Score |
| → G5 | — | Confidence ≥ threshold? | — |
| 8 | System | Log query, result set, latency, scores | `QueryLogged` |

---

## P3 · Context Assembly {#p3}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | Platform | Receive assembly trigger (session start or new task) | Assembly request |
| 2 | Platform | Load system prompt from template + config | Component 1 |
| 3 | Platform | Load active session facts + scratchpad carry-forward | Component 2 |
| 4 | Platform | Attach user query | Component 3 |
| 5 | Platform | Execute RAG query for current task | Component 4 |
| 6 | Platform | Load task context (current work item) | Component 5 |
| 7 | Platform | Load conversation history (most recent first) | Component 6 |
| 8 | Platform | Fetch cached Tier 1 knowledge payload (≤200K tokens, droppable) | Component 7 |
| 9 | Platform | Attach core protocol rules (active version) | Component 8 |
| 10 | Token Manager | Calculate total token count | Budget assessment |
| → G1 | — | Budget exceeded? | — |
| 11 | Token Manager | Warn user with options before shedding; shed droppable components (Tier 1 cache → RAG → history, oldest first) | Trimmed context |
| 12 | Platform | Finalise and deliver assembled context | `ContextReady` |

---

## P4 · Engagement Lifecycle {#p4}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | Enterprise Admin | Create engagement record (org/product/client/engagement) | Engagement record |
| 2 | System | Emit `EngagementCreated` event | Event published |
| → G1 | — | Connector configured? | — |
| 3 | Enterprise Admin | Configure connectors (default: read-only) | ConnectorConfig |
| → G3 | — | Delivery template exists? | — |
| 4 | System | Instantiate delivery pipeline from template | Pipeline + stages |
| → G2 | — | Knowledge scope populated? | — |
| 5 | Ingestion Agent | Ingest product knowledge for this engagement | KnowledgeScope populated |
| 6 | PS Consultant | Configure engagement-specific knowledge scope | Scope finalised |
| 7 | System | Open audit trail | Audit trail open |
| 8 | Project Controller | Assign Project Controller agent | Agent registered |
| 9 | PS Consultant | Execute delivery pipeline (P5) | Pipeline running |
| → G4 | — | Engagement complete? | — |
| 10 | PS Consultant | Execute support handoff (P5 Stage 6) | `EngagementHandedOff` |

---

## P5 · Delivery Pipeline Execution {#p5}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | System | Open stage gate | Stage active |
| **Stage 1 — Requirements** | | | |
| 2 | Design Agent | Collate inputs (meetings, emails, docs) | Raw requirements |
| 3 | Design Agent | Structure requirements, flag gaps | RequirementsDoc |
| 4 | PS Consultant | Review, fill gaps, approve | RequirementsDoc validated |
| → G2 | — | All requirements validated? | — |
| **Stage 2 — Configuration** | | | |
| 5 | Coder Agent | Query Knowledge Engine for matching patterns | Pattern set |
| 6 | Coder Agent | Generate configuration (traced to requirements) | ConfigurationItem set |
| 7 | PS Consultant | Review, adjust, approve configuration | Config approved |
| → G2 | — | Human approval given? | — |
| **Stage 3 — Validation/Test** | | | |
| 8 | Test Agent | Generate test scenarios from config + BPMN | TestScenario set |
| 9 | Test Agent | Execute tests via API/Playwright | TestResult set |
| → G3 | — | Critical tests pass? | — |
| 10 | System | Log regression baseline | RegressionBaseline |
| **Stage 4 — Deployment** | | | |
| 11 | System | Push config to UAT via connector | UAT deployment |
| 12 | PS Consultant | Client UAT cycle | Sign-off received |
| 13 | System | Promote UAT → Production | Production deployment |
| **Stage 5 — Documentation** | | | |
| 14 | Documentation Agent | Read config via API, map to requirements | Living doc assembled |
| 15 | Delivery Lead | Review documentation | Doc approved |
| **Stage 6 — Support Handoff** | | | |
| 16 | PS Consultant | Transfer history + context to support via KMS | `PipelineComplete` |

---

## P6 · Connector Sync {#p6}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | System | Trigger: `SourceDataChanged` event or health check | Trigger received |
| → G1 | — | Connector healthy? | — |
| 2 | Connector | health_check() | Health status |
| 3 | Connector | get_schema() — check for schema changes | Schema |
| → G3 | — | Schema changed? | — |
| 4 | Integration Hub | Update schema cache; flag existing ingested data for review | Schema updated, review tasks queued |
| 5 | Connector | batch_read() with pagination | Raw data |
| → G2 | — | Data changed since last sync? | — |
| 6 | System | Queue changed items for ingestion | Ingestion queue |
| 7 | Ingestion Agent | Execute P1 (Knowledge Ingestion) per item | `KnowledgeIngested` |
| → G4 | — | Write-back configured? | — |
| 8 | Connector | batch_write() updates to source system | Write confirmation |
| 9 | System | Log sync result | `SyncComplete` |

---

## P7 · Agent Orchestration {#p7}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | Project Controller | Receive work item from Work Management | Work item |
| → G1 | — | Complexity ≥ threshold? | — |
| 2a | Project Controller | Spawn Supervisor Agent | Supervisor active |
| 2b | Project Controller | Handle directly (single-agent) | Work executed |
| 3 | Supervisor | Decompose work into sub-tasks (≤ configurable cap, default 4) | Sub-task set |
| → G3 | — | Sub-agent count ≤ cap? | — |
| 4 | Supervisor | Spawn specialist sub-agents (Design/Coder/Test/Docs) | Sub-agents active |
| 5 | Sub-agents | Execute work cycle (query KE, implement, return) | Outputs |
| → G2 | — | Context compaction detected? | — |
| 6 | Agent | Recover from scratchpad DB | State restored |
| 7 | Supervisor | Collect sub-agent outputs, validate | Consolidated output |
| → G4 | — | Work item complete? | — |
| → G5 | — | Handoff to another agent required? | — |
| 8 | Supervisor | Assemble handoff package (scratchpad + open items + decisions) | Handoff package |
| 9 | Project Controller | Update Work Management status | `WorkComplete` |

---

## P8 · Quality & Compliance Check {#p8}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | System | Trigger: config item produced or deployment gate reached | Check triggered |
| → G1 | — | Test scenarios exist for this config? (auto-generated scenarios require human review on first use) | — |
| 2 | Test Agent | Generate test scenarios from config items + BPMN | TestScenario set |
| 3 | Test Agent | Execute test scenarios (API + Playwright) | TestResult set |
| → G2 | — | All critical tests pass? | — |
| 4 | Analysis Agent | Structured defect capture (steps/expected/actual/env) | Defect draft |
| → G3 | — | Semantic duplicate defect exists? (suggest-and-confirm: system suggests match, human confirms) | — |
| 5a | System | Link to existing IssueThread | Linked |
| 5b | System | Create new IssueThread | IssueThread created |
| 6 | Analysis Agent | Check cross-client impact (semantic pattern match) | Impact assessment |
| → G4 | — | Cross-client impact possible? (suggest-and-confirm: system suggests escalation, human confirms) | — |
| 7 | Human Reviewer | Decide: escalate / request fix / update docs | Decision logged |
| 8 | Analysis Agent | Suggest severity rating | Severity |
| 9 | PS Consultant | Confirm severity | Severity confirmed |
| 10 | System | Sync defect to Jira via connector | Jira issue created |
| → G5 | — | Regression baseline established? | — |
| 11 | System | Log regression baseline or run diff | `GatePassed` or `DefectRaised` |

---

## P9 · Customer Onboarding {#p9}

| Step | Actor | Action | Output |
|------|-------|--------|--------|
| 1 | System | `SubscriptionContract` activated | Trigger |
| → G1 | — | Product knowledge already in system? | — |
| 2 | Ingestion Agent | Auto-ingest product API + UI/UX knowledge (Tier 1) | Product knowledge base |
| 3 | Enterprise Admin | Upload domain-specific knowledge (steps 3 and 4 can run in parallel with step 5) | Domain knowledge |
| 4 | PS Consultant | Define knowledge scope for this customer | KnowledgeScope |
| → G2 | — | All connectors healthy? | — |
| 5 | Enterprise Admin | Configure connectors (Jira, time2work, Confluence, etc.) (can run in parallel with steps 3–4) | ConnectorConfig |
| 6 | Enterprise Admin | Configure constrained deployment (system prompt + scope + tools) | Deployment draft |
| 7 | System | 5-question validation of constrained deployment | Validation report |
| → G3 | — | Validation tests pass? | — |
| 8 | Enterprise Admin | Publish constrained deployment to channel | Deployment active |
| 9 | PS Consultant | Execute smoke tests | Smoke results |
| 10 | System | Trigger P4 (Engagement Lifecycle) for first engagement | `OnboardingComplete` |

---

**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-01-bpmn-processes-detail.md
