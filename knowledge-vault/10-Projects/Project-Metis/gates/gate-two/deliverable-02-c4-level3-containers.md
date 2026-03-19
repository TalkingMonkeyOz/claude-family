---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/2
  - type/architecture
  - type/c4
status: complete
---

# Gate 2 Deliverable 2: C4 Level 3 — Container Detail (Sub-Document)

Continuation of [[deliverable-02-c4-level3|Main C4 Level 3 Document]]. Covers Agent Orchestrator, Workflow Engine, Web UI, and Background Workers.

---

## 5. Agent Orchestrator

**Technology:** TypeScript | **Bounded context:** Agent Runtime

Coordinates specialist AI agents for multi-step tasks. Manages agent lifecycle, task queues, inter-agent messaging, and session handoffs. Implements the two-level router+specialist hierarchy.

| Component | Type | Responsibility | Depends On |
|-----------|------|---------------|------------|
| AgentRegistry | Repository | Registers active agents; tracks role, model, scope permissions | PostgreSQL |
| TaskQueue | Service | Priority queue of claimable tasks; agents claim and mark in-progress | PostgreSQL |
| TaskDispatcher | Service | Matches open tasks to available agents by role; enforces scope restrictions | AgentRegistry, TaskQueue |
| SessionManager | Service | Creates/resumes/ends sessions; generates HandoffPackage on session end | SessionRepository |
| SessionRepository | Repository | CRUD on `sessions`, `scratchpad_entries` | PostgreSQL |
| AgentMessageBus | Service | In-process message passing between agents; logged to `agent_messages` | PostgreSQL |
| HandoffPackageBuilder | Service | Assembles carry-forward facts + open tasks + key decisions for cross-agent transfer | SessionRepository |
| ComplianceMonitor | Service | Tracks the 7 compliance metrics (task creation rate, verify-before-claim, etc.) | AuditLogger |
| AuditLogger | Service | Append-only writes to `audit_log` for every state-changing operation | PostgreSQL |
| CrashRecoveryService | Service | Detects unclean session end; reconstructs state from scratchpad + audit log | SessionRepository |

**Agent roles and model assignment:**

| Role | Model | Read Scope | Write Scope |
|------|-------|-----------|------------|
| Orchestrator | Opus | All | Orchestration only |
| KnowledgeAgent | Sonnet | Knowledge Store | Knowledge items |
| DeliveryAgent | Sonnet | Delivery Pipeline | Config, releases |
| TestingAgent | Sonnet | Test Assets | Test results |
| ReviewAgent | Opus | All | Read-only |

**Note:** Sub-agent cap is configurable (default 4). The cap is set per deployment via admin centre; coordination metrics are monitored to detect bottlenecks at the configured limit.

**Key interaction:** `TaskDispatcher` claims a task → calls `HandoffPackageBuilder` if cross-agent → `Context Assembly Orchestrator` builds the agent's prompt with handoff context injected at layer 3.

---

## 6. Workflow Engine

**Technology:** SpiffWorkflow (Python) | **Bounded context:** Work Context

Executes BPMN process definitions for governed workflows: knowledge validation, delivery pipeline gates, defect triage, knowledge promotion. METIS owns queryable state in `workflow_instances`; SpiffWorkflow owns execution internals.

| Component | Type | Responsibility | Depends On |
|-----------|------|---------------|------------|
| WorkflowInstanceRepository | Repository | CRUD on `workflow_instances` and `workflow_step_log` | PostgreSQL |
| BPMNLoader | Service | Loads `.bpmn` definitions from the process registry; validates against schema | BPMN registry |
| WorkflowRunner | Service | Drives SpiffWorkflow engine through BPMN process execution | SpiffWorkflow, WorkflowInstanceRepository |
| GateEvaluator | Service | Checks BPMN gateway conditions (e.g. test pass rate >= 95%, required signatures present) | WorkflowInstanceRepository |
| HumanTaskQueue | Service | Surfaces manual review tasks to the Web UI or API; blocks workflow until completed | PostgreSQL |
| EventPublisher | Service | Publishes domain events on workflow milestones (GatePassed, GateFailed, WorkflowCompleted) | (Event bus) |
| StepLogger | Handler | Writes append-only `workflow_step_log` entries on every step transition | PostgreSQL |
| WorkflowSwapAdapter | Adapter | Interface boundary: isolates SpiffWorkflow from the rest of METIS; enables engine swap | WorkflowRunner |

**Swap-out design:** All METIS components interact with `WorkflowRunner` only. SpiffWorkflow is contained behind `WorkflowSwapAdapter`. Replacing the engine (Camunda, Temporal) requires only implementing the adapter interface.

**Key BPMN processes modelled:**

| Process | Trigger | Gate Examples |
|---------|---------|--------------|
| Knowledge Validation | Ingest of T2/T3 knowledge | Senior review signed off |
| Delivery Pipeline | Engagement created | Requirements signed, test pass rate threshold, UAT complete |
| Defect Triage | Defect captured | Duplicates ruled out, severity confirmed, Jira synced |
| Knowledge Promotion | Promotion requested | Generalisation reviewed, senior approved |
| Constrained Deployment | Deployment configured | 5 evaluation questions pass |

---

## 7. Web UI

**Technology:** React 19 + MUI, Vite, static bundle | **Bounded context:** Cross-cutting

Admin and user interface for knowledge management, Q&A, engagement management, and platform administration. Deployed as a static bundle served by Fastify or CDN. All data flows through the API Gateway — the UI has no direct database access.

| Component | Type | Responsibility | Depends On |
|-----------|------|---------------|------------|
| AppShell | Layout | Navigation, auth state, theme, global error boundary | AuthContext |
| AuthContext | Context | Holds JWT, user identity, org scope; handles token refresh | API Gateway |
| ScopeSelector | Component | Lets user set active Product / Client / Engagement scope headers | AuthContext |
| AskScreen | Screen | Conversational Q&A: question input, answer display, source citations, feedback button | `/ask`, `/feedback` |
| SearchScreen | Screen | Knowledge browse and semantic search, category filter, result cards | `/search`, `/categories` |
| IngestScreen | Screen | Upload/paste knowledge, select type, view validation tier routing, track status | `/ingest`, `/ingest/batch` |
| HumanTaskInbox | Screen | Surfaces pending BPMN human tasks (T2 review, gate approvals) | Workflow Engine API |
| ProjectDashboard | Screen | Health score, pipeline stage status, defect summary, test coverage, doc completeness | Aggregation API |
| AdminPanel | Screen | Users, roles, connectors, retention config, token budgets, deployment config | Admin API (Gate 3) |
| APIClient | Service | Typed fetch wrapper; appends scope headers, handles envelope unwrapping, error mapping | API Gateway |
| QueryHooks | Hook | React Query hooks for each API operation; handles caching, loading, error states | APIClient |

**Phase 2 note:** Web UI is a Phase 2 deliverable. MCP server + API Gateway are built first (Phase 1). The UI surfaces what already exists in the API — no UI-specific backend logic.

---

## 8. Background Workers

Background workers are not a separate container — they are sub-processes owned by Knowledge Engine and Connector Hub that run on a schedule or event trigger, without a synchronous caller.

| Worker | Owner | Trigger | Responsibility |
|--------|-------|---------|---------------|
| EmbeddingWorker | Knowledge Engine | Ingest queue item | Calls EmbeddingProvider, stores vector, marks chunk ready |
| CacheAssembler | Context Assembly Orchestrator | KnowledgeIngested event or schedule | Rebuilds Tier 1 cached prompt for affected deployment types |
| FreshnessWorker | Knowledge Engine | SourceDataChanged / ReleaseDeployed event | Recalculates `freshness_score` on affected knowledge items |
| RelationSuggester | Knowledge Engine | Post-ingest (async) | AI-suggests relationships between new item and existing knowledge; creates graph edges in Apache AGE (T4, flagged for review) |
| RetentionEnforcer | Knowledge Engine | Daily schedule | Applies retention tier rules; soft-deletes / archives expired records |
| JiraSyncWorker | Connector Hub | DefectCreated / DefectUpdated event | Bidirectional Jira sync; METIS is source of truth |
| ComplianceMetricsWorker | Agent Orchestrator | Session end trigger | Calculates 7 compliance metrics and logs to audit |

---

## 9. Component Dependency Summary

High-level dependency directions (no circular dependencies by design):

```
Web UI → API Gateway → Knowledge Engine
                     → Context Assembly Orchestrator → Knowledge Engine
                                                     → Agent Orchestrator
                     → Workflow Engine
                     → Connector Hub → Knowledge Engine (via event)

Agent Orchestrator → Context Assembly Orchestrator
                   → Workflow Engine
                   → Connector Hub

All containers → PostgreSQL (via their own repositories)
All containers → AuditLogger (write-only)
Knowledge Engine → PostgreSQL (Apache AGE extension — graph queries)
```

**Principle:** Containers communicate via the event bus for domain events and via direct service calls only within their own bounded context. Cross-context calls go through published interfaces, not internal services.

---

**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-02-c4-level3-containers.md
