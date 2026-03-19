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

# Gate 2 Deliverable 1: Detailed Process Models (BPMN)

## Overview

Structured process models for 9 core METIS processes, written in BPMN-style markdown notation. Designed to be:
- Precise enough to generate test cases from
- Convertible to `.bpmn` XML files in Gate 3
- Aligned with the 10 bounded contexts in [[gate-two/deliverable-03-domain-model|Domain Model (DDD)]]

**Source:** 54 processes from the Gate 1 Process Inventory. These 9 are the canonical flows — the ones that, if any are wrong, the system fails. The remaining 45 processes are supporting flows derivable from these.

**Notation key:** `[Task]` = task, `<Gateway>` = decision point, `((Event))` = start/end event, `{Pool}` = lane/actor.

**Detail doc:** [[gate-two/deliverable-01-bpmn-processes-detail|Process Flow Detail]] — full step tables for all 9 processes.

---

## Process Index

| # | Process | Trigger | Bounded Context |
|---|---------|---------|----------------|
| P1 | Knowledge Ingestion | Content arrives | Knowledge Store |
| P2 | Knowledge Retrieval (RAG) | Query submitted | Knowledge Store |
| P3 | Context Assembly | Agent starts work | Agent Runtime + Work Context |
| P4 | Engagement Lifecycle | Engagement created | Tenant & Scope + Delivery Pipeline |
| P5 | Delivery Pipeline Execution | Stage entered | Delivery Pipeline |
| P6 | Connector Sync | Source data changed | Integration |
| P7 | Agent Orchestration | Work item assigned | Agent Runtime |
| P8 | Quality & Compliance Check | Config item produced | Test Assets + Defect Intelligence |
| P9 | Customer Onboarding | Contract signed | Tenant & Scope + Delivery Pipeline |

---

## P1 · Knowledge Ingestion

**Trigger:** Content submitted (upload, API event, agent capture)
**Actors:** Enterprise Admin, Ingestion Agent, Domain Expert (Tier 4 only)
**Bounded contexts:** Knowledge Store, Integration (source), Tenant & Scope (scope)

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Content type deterministic? | Route to type-specific parser | Flag for manual classification |
| G2 | Validation tier? | Tier 1 → auto-approve | Tier 2/3 → queue review |
| G3 | Semantic duplicate exists? | Merge / link | Create new item |
| G4 | Embedding succeeded? | Index item | Retry → dead-letter queue |

**End events:** `KnowledgeIngested` (success), `IngestionFailed` (dead-letter)

**Constraints:** Every item stores embedding_model + embedding_dimensions. Tier 2 requires human approval — no exception. See [[deliverable-01-bpmn-processes-detail#p1|P1 step table]].

---

## P2 · Knowledge Retrieval (RAG)

**Trigger:** Natural-language query from user or agent
**Actors:** Querying agent or user, Knowledge Engine (automated)
**Bounded contexts:** Knowledge Store, Work Context (consumer)

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Classifier: query in scope? | Proceed | Reject with reason |
| G2 | Top-N results above threshold? | Continue to graph walk | Return low-confidence flag |
| G3 | Graph walk adds items? (Apache AGE on PG18 — Phase 1) | Merge at lower priority | Skip graph step |
| G4 | LLM synthesis requested? | Assemble answer + citations | Return ranked chunks only |
| G5 | Confidence score ≥ threshold? | Return answer | Flag for human review |

**End events:** `AnswerReturned` (with confidence score), `LowConfidenceFlagged`

**Constraints:** No keyword matching — embeddings only (Decision #9). Every query logged with scores and user feedback. See [[deliverable-01-bpmn-processes-detail#p2|P2 step table]].

---

## P3 · Context Assembly

**Trigger:** Agent session starts or new work item assigned
**Actors:** Platform (automated), Agent Runtime
**Bounded contexts:** Agent Runtime, Work Context, Knowledge Store

**Assembly order (fixed):**

| Priority | Component | Source | Droppable? |
|----------|-----------|--------|------------|
| 1 | System prompt | Template + config | No |
| 2 | Session context | Active session facts | No |
| 3 | User query | Runtime | No |
| 4 | RAG results | Live query | Yes (budget) |
| 5 | Task context | Current work item | No |
| 6 | Conversation history | Session DB | Yes (oldest first) |
| 7 | Cached Tier 1 knowledge | Knowledge cache (≤200K tokens) | Yes (droppable) |
| 8 | Core protocol rules | Protocol version | No |

**Note:** Cached Tier 1 knowledge is droppable as a last resort. Before shedding, the system warns the user with options to avoid degradation (no silent shedding).

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Token budget exceeded? | Shed droppable components | Finalise prompt |
| G2 | Scratchpad has carry-forward items? | Include at priority 2 | Skip |

**End events:** `ContextReady`, `BudgetExceeded` (drops lowest-priority droppable items, re-evaluates)

**Constraints:** System prompt, core protocol, current task, carry-forward items are never dropped. See [[deliverable-01-bpmn-processes-detail#p3|P3 step table]].

---

## P4 · Engagement Lifecycle

**Trigger:** Enterprise Admin creates engagement record
**Actors:** Enterprise Admin, PS Consultant, Project Controller agent
**Bounded contexts:** Tenant & Scope, Delivery Pipeline, Integration, Knowledge Store

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Connector configured? | Continue to scope creation | Block — connector required |
| G2 | Knowledge scope populated? | Instantiate pipeline | Queue product knowledge ingestion |
| G3 | Delivery template exists? | Clone template | Build new pipeline structure |
| G4 | Engagement complete? | Hand off to support | Continue pipeline |

**End events:** `EngagementCreated`, `EngagementHandedOff`, `EngagementArchived`

**Emits events:** `EngagementCreated` → Tenant & Scope + Delivery Pipeline (Decision #2 event flow). See [[deliverable-01-bpmn-processes-detail#p4|P4 step table]].

---

## P5 · Delivery Pipeline Execution

**Trigger:** Stage gate opened (human or system)
**Actors:** PS Consultant, Design Agent, Coder Agent, Test Agent, Documentation Agent
**Bounded contexts:** Delivery Pipeline, Test Assets, Knowledge Store, Work Management

**Stages (sequential, human gate between each):**

| Stage | Primary Actor | Gate Condition |
|-------|---------------|---------------|
| 1 Requirements | Design Agent + PS Consultant | All requirements validated, no open gaps |
| 2 Configuration | Coder Agent + PS Consultant | Config items traced to requirements |
| 3 Validation/Test | Test Agent | Critical tests pass |
| 4 Deployment | System + PS Consultant | UAT sign-off received |
| 5 Documentation | Documentation Agent | Living doc generated and reviewed |
| 6 Support Handoff | PS Consultant + Support | Handoff completeness confirmed |

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Stage gate passes? | Advance to next stage | Block — surface blockers |
| G2 | Human approval given? | Continue | Wait (agent cannot proceed) |
| G3 | Regression scope clean? | Release approved | Defect raised → P8 (known issues may pass with logged justification: accept-and-close for cosmetic issues, or accept-and-track which creates a deferred defect via P8) |

**End events:** `StagePassed`, `StageFailed`, `PipelineComplete`

**Constraints:** Agents cannot skip human gate — BPMN-enforced (Decision #13). See [[deliverable-01-bpmn-processes-detail#p5|P5 step table]].

---

## P6 · Connector Sync

**Trigger:** `SourceDataChanged` event OR scheduled health check
**Actors:** Connector (automated), Integration Hub, Knowledge Ingestion Agent
**Bounded contexts:** Integration, Knowledge Store

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Connector healthy? | Read data | Circuit breaker → alert |
| G2 | Data changed since last sync? | Queue for ingestion | No-op |
| G3 | Schema changed? | Re-discover schema + flag existing ingested data for review | Use cached schema |
| G4 | Write-back configured? | Push updates to source | Read-only exit |

**End events:** `SyncComplete`, `ConnectorFailed` (circuit breaker open)

**Emits events:** `SourceDataChanged` → triggers P1 (Knowledge Ingestion). See [[deliverable-01-bpmn-processes-detail#p6|P6 step table]].

---

## P7 · Agent Orchestration

**Trigger:** Work item assigned to agent pool (Project Controller)
**Actors:** Project Controller, Supervisor Agent, Specialist sub-agents (Design/Coder/Test/Docs)
**Bounded contexts:** Agent Runtime, Work Context, Work Management

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Work item complexity ≥ threshold? | Spawn Supervisor + sub-agents | Single agent handles |
| G2 | Context compaction detected? | Write-through scratchpad recovery | Continue |
| G3 | Sub-agent count ≤ cap? | Assign sub-agent | Queue (supervisor bottleneck) |
| G4 | Work item complete? | Return to Controller | Continue work cycle |
| G5 | Handoff required? | Assemble handoff package | Close session |

**End events:** `WorkComplete`, `WorkHandedOff`, `SessionEnded`

**Constraints:** Sub-agent cap is configurable (default 4). Monitor coordination metrics to detect bottlenecks. Agents propose protocol changes, humans activate. See [[deliverable-01-bpmn-processes-detail#p7|P7 step table]].

---

## P8 · Quality & Compliance Check

**Trigger:** Configuration item produced OR deployment gate reached
**Actors:** Test Agent, QA Agent, Analysis Agent, PS Consultant (approval)
**Bounded contexts:** Test Assets, Defect Intelligence, Delivery Pipeline

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Test scenarios exist for config? (auto-generated scenarios get human review on first use) | Execute tests | Generate scenarios first |
| G2 | All critical tests pass? | Advance gate | Raise defect |
| G3 | Semantic duplicate defect? (suggest-and-confirm: system suggests match, human confirms) | Link to existing | Create new IssueThread |
| G4 | Cross-client impact possible? (suggest-and-confirm: system suggests escalation, human confirms) | Flag for human review | Resolve within engagement |
| G5 | Regression baseline established? | Run regression diff | Log as new baseline |

**End events:** `GatePassed`, `DefectRaised`, `ComplianceViolation`

**Constraints:** Human decides on cross-client escalation — agents cannot auto-escalate (Process 5.4). Defects sync to Jira; METIS is source of truth. See [[deliverable-01-bpmn-processes-detail#p8|P8 step table]].

---

## P9 · Customer Onboarding

**Trigger:** SubscriptionContract activated
**Actors:** Enterprise Admin, PS Consultant, Knowledge Ingestion Agent
**Bounded contexts:** Tenant & Scope, Knowledge Store, Integration, Delivery Pipeline

**Stages (7-step sequence):**

| Step | Action | Gate |
|------|--------|------|
| 1 | Product knowledge ingestion | Tier 1 knowledge populated |
| 2 | Domain capture (can run in parallel with step 3) | Customer-specific knowledge scoped |
| 3 | Tool integration (can run in parallel with step 2) | Connectors configured and health-checked |
| 4 | Deployment configuration | Constrained deployment validated (5-question check) |
| 5 | Validation | System-level smoke tests pass |
| 6 | First engagement | Delivery pipeline instantiated |
| 7 | Compound | Knowledge grows with every subsequent engagement |

**Gateways:**

| Gateway | Condition | True Path | False Path |
|---------|-----------|-----------|------------|
| G1 | Product knowledge available? | Auto-ingest | Manual upload |
| G2 | All connectors healthy? | Proceed to deployment config | Block and notify |
| G3 | Validation tests pass? | First engagement | Remediate and re-validate |

**End events:** `OnboardingComplete` → `EngagementCreated` (P4 triggered)

**Constraints:** Constrained deployment requires 5-question validation before publish (Process 7.8). See [[deliverable-01-bpmn-processes-detail#p9|P9 step table]].

---

## Coverage Map

| Bounded Context | Processes |
|----------------|-----------|
| Knowledge Store | P1, P2, P6 |
| Agent Runtime | P3, P7 |
| Work Context | P3, P7 |
| Delivery Pipeline | P4, P5, P9 |
| Tenant & Scope | P4, P9 |
| Test Assets | P8 |
| Defect Intelligence | P8 |
| Integration | P6, P4 |
| Work Management | P5, P7 |
| Commercial | P9 (trigger) |

---

**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-01-bpmn-processes.md
