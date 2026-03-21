---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/3
  - type/ddd
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 3: Domain Model (DDD)

## Overview

10 bounded contexts, each with a single aggregate root. Event-driven communication between contexts. Evolved from Gate 1's 7-context entity map (45 entities) through restructuring for single-responsibility.

**Ethos applied:** One root, one owner, one reason to change — readable, expandable, maintainable at the domain level.

---

## 1. Bounded Context Map

### Contexts and Roots

| # | Context | Aggregate Root | Entity Count | Maps to Area |
|---|---------|---------------|-------------|-------------|
| 1 | **Knowledge Store** | `KnowledgeItem` | 12 | F119 (Knowledge Engine) |
| 2 | **Tenant & Scope** | `Organisation` | 7 | Cross-cutting |
| 3 | **Delivery Pipeline** | `DeliveryPipeline` | 9 | F121 (Delivery Accelerator) |
| 4 | **Work Management** | `Initiative` | 6 | F126 (Project Governance) |
| 5 | **Test Assets** | `TestSuite` | 5 | F124 (Quality & Compliance) |
| 6 | **Defect Intelligence** | `IssueThread` | 6 | F123 (Support & Defect Intel) |
| 7 | **Agent Runtime** | `Session` | 7 | F125 (Orchestration & Infra) |
| 8 | **Work Context** | `Activity` | 5 | F125 (Orchestration & Infra) |
| 9 | **Integration** | `ConnectorConfig` | 2 | F120 (Integration Hub) |
| 10 | **Commercial** | `SubscriptionContract` | 4 | F128 (Commercial) |

**Cross-cutting:** `AuditLog` belongs to no single context — all contexts write to it.

### Evolution from Gate 1

| Gate 1 (7 contexts) | Gate 2 (10 contexts) | Change |
|---------------------|---------------------|--------|
| Delivery & Project (16 entities) | Delivery Pipeline (9) + Work Management (6) | Split — different rates of change |
| Quality & Testing (11) | Test Assets (5) + Defect Intelligence (6) | Split — independent roots |
| Orchestration & Session (12) | Agent Runtime (7) + Work Context (5) | Split — runtime vs state |
| Integration & Security (6) | Integration (2) | Focused — workflow moved to Agent Runtime, audit cross-cutting |

---

## 2. Aggregate Root Detail

### Knowledge Store → `KnowledgeItem`

**Owns:** KnowledgeChunk, KnowledgeRelation, KnowledgePromotion, KnowledgeType, ValidationTier, DecisionRecord, VaultDocument, BPMNProcess, QueryLog, QueryFeedback, CodeSymbol, CodeReference

**Invariants:**
- Every chunk belongs to exactly one item
- Promotions require Tier 2 human approval
- Superseded items link to their replacement
- Scope chain always populated per C2-2
- Code symbols live in dedicated tables (`code_symbols`, `code_references`) but share the same embedding space and ranking pipeline as document chunks
- Code references are directional edges (calls, imports, extends) — traversed via recursive CTEs, not Apache AGE

### Tenant & Scope → `Organisation`

**Owns:** Product, Client, Engagement, User, UserOrgAccess, KnowledgeScope

**Invariants:**
- Org → Product → Client → Engagement hierarchy enforced
- Child denormalises all parent IDs (C2-2)
- Users scoped to org via UserOrgAccess

### Delivery Pipeline → `DeliveryPipeline`

**Owns:** PipelineStage, PipelineGate, RequirementsDoc, RequirementItem, ConfigurationItem, Release, DeliveryTemplate, LivingDocument, ReleaseHistory

**Invariants:**
- Pipeline instantiated from template per engagement
- Gates must pass before stage progression
- Releases bundle validated configurations only

### Work Management → `Initiative`

**Owns:** Feature, Task/BuildTask, ClientArtifact, ClientTimeline

**Invariants:**
- Initiative → Feature → Task hierarchy
- Status rolls up from children
- Tasks must be fully specified with verification criteria

### Test Assets → `TestSuite`

**Owns:** TestScenario, TestResult, RegressionBaseline, RegressionScope

**Invariants:**
- Scenarios generated from config items + BPMN
- Results compared against baseline for regression
- Regression scope computed from change impact

### Defect Intelligence → `IssueThread`

**Owns:** Defect, DefectPattern, ReplicationScenario, JiraIssue, BackgroundAgentJob

**Invariants:**
- Thread not resolved until ALL children closed AND fix deployed AND verified
- METIS is source of truth; Jira is synced to, not from
- Patterns flagged for human review, never auto-escalated

### Agent Runtime → `Session`

**Owns:** SessionFact, ScratchpadEntry, AgentRegistration, AgentMessage, ProtocolVersion, ComplianceCheck, ComplianceSummary

**Invariants:**
- Session anchors all live work
- Facts survive context compaction via DB persistence
- Protocol changes: agents propose, humans activate

### Work Context → `Activity`

**Owns:** WorkContextContainer, Workfile, CognitiveMemory, WorkflowInstance, WorkflowStepLog

**Invariants:**
- Activity lifecycle: created → active → semi-active → archived
- WCC computed on demand, budget-capped, cached
- Workflow instances use write-through pattern (C2-4)

### Integration → `ConnectorConfig`

**Owns:** Credential

**Invariants:**
- Credentials encrypted at rest, per-tenant key
- Connector direction configurable (read/write/bidirectional)
- Hot-swappable without restart

### Commercial → `SubscriptionContract`

**Owns:** Enhancement, ConstrainedDeployment, DeploymentChannel

**Invariants:**
- Enhancements priced as annual uplift
- Deployments carry system prompt + knowledge scope + tool restrictions

---

## 3. Domain Events

See [[gate-two/deliverable-03-domain-events|Domain Events Detail]] for full event catalogue.

**Communication principle:** Events flow, never direct calls between contexts. Context publishes, subscribers react. No context knows who's listening.

### Key Event Flows

```
Integration ──SourceDataChanged──→ Knowledge Store
Integration ──CodeRepositoryChanged──→ Knowledge Store (code re-index)
Knowledge Store ──KnowledgeIngested──→ Work Context, Test Assets
Knowledge Store ──CodeIndexed──→ Work Context (dossier refresh)
Delivery Pipeline ──GateFailed──→ Defect Intelligence
Delivery Pipeline ──ReleaseDeployed──→ Knowledge Store (freshness)
Test Assets ──TestFailed──→ Defect Intelligence
Defect Intelligence ──DefectResolved──→ Knowledge Store (learning)
Agent Runtime ──SessionStarted──→ Work Context (load context)
Commercial ──EngagementCreated──→ Tenant & Scope, Delivery Pipeline
```

---

## 4. Context Relationships

| Upstream | Downstream | Relationship | Pattern |
|----------|-----------|-------------|---------|
| Tenant & Scope | All | Conformist | Everyone conforms to the scope hierarchy |
| Knowledge Store | Delivery, Test, Work Context | Published Language | Standard knowledge item schema |
| Delivery Pipeline | Test Assets, Defect Intel | Customer/Supplier | Pipeline produces, quality validates |
| Agent Runtime | Work Context | Partnership | Tightly coordinated but separate ownership |
| Integration | Knowledge Store | Published Language | Connector output → standard ingest format |

---

## 5. Open Items (Gate 3)

- [ ] Value objects identification per context
- [ ] Repository interfaces per aggregate
- [ ] Event bus implementation (in-process vs message queue)
- [ ] Anti-corruption layers between contexts
- [ ] Context map diagram (visual)
- [ ] Multi-product knowledge sharing rules across contexts

---
**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-22
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-03-domain-model.md
