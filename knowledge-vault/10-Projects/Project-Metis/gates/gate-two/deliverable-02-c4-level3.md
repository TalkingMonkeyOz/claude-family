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

# Gate 2 Deliverable 2: C4 Level 3 Component Diagrams

## Overview

Decomposes METIS's seven logical containers into their internal components. This is a design-level view — what exists, what it owns, and how it connects. Implementation interfaces are Gate 3 work.

**Containers decomposed here:**

| Container | Technology | Bounded Context(s) |
|-----------|-----------|-------------------|
| API Gateway | Fastify (TypeScript) | Cross-cutting |
| Knowledge Engine | TypeScript + Python | Knowledge Store |
| Context Assembly Orchestrator | TypeScript | Work Context, Agent Runtime |
| Connector Hub | TypeScript | Integration |
| Agent Orchestrator | TypeScript | Agent Runtime |
| Workflow Engine | SpiffWorkflow (Python) | Work Context |
| Web UI | React 19 + MUI | Cross-cutting |

**Database layer** (PostgreSQL 18 + pgvector) is addressed in Deliverable 5. Background Workers are sub-processes of Knowledge Engine and Connector Hub, detailed in the sub-document.

Full component tables: [[deliverable-02-c4-level3-containers|Container Detail Sub-Document]]

---

## 1. API Gateway

**Technology:** Fastify (TypeScript) | **Bounded context:** Cross-cutting

The single entry point for all external traffic — REST callers, the MCP server adapter, and the Web UI. Enforces auth, routes, validates, and applies scope headers before any request reaches internal containers.

| Component | Type | Responsibility | Depends On |
|-----------|------|---------------|------------|
| RouteRegistry | Router | Declares and mounts all REST routes | — |
| AuthMiddleware | Middleware | Validates JWT, extracts user/org identity | TokenVerifier |
| TokenVerifier | Service | Verifies JWT signature, checks expiry and scope | (JWT library) |
| ScopeHeaderParser | Middleware | Parses X-Org-Id / X-Product-Id / X-Client-Id / X-Engagement-Id | AuthMiddleware |
| InputClassifier | Service | Haiku-model gatekeeper — rejects off-topic queries before KE | LLMProvider |
| RequestValidator | Middleware | JSON Schema validation on every route (Fastify built-in) | RouteRegistry |
| ResponseEnvelopeBuilder | Handler | Wraps all responses in standard `{data, pagination}` / `{error}` envelope | — |
| MCPServerAdapter | Adapter | Translates MCP tool calls into internal REST calls | RouteRegistry |
| HealthController | Controller | Exposes `/health` — no auth | — |

**Key interaction:** Every inbound request flows `AuthMiddleware → ScopeHeaderParser → InputClassifier → RouteRegistry → target container`. The InputClassifier can short-circuit with 422 before routing.

---

## 2. Knowledge Engine

**Technology:** TypeScript service + Python embedding worker | **Bounded context:** Knowledge Store

Owns all knowledge lifecycle: ingest, chunk, embed, store, retrieve, rank, and promote. The retrieval pipeline is the core of METIS's intelligence.

| Component | Type | Responsibility | Depends On |
|-----------|------|---------------|------------|
| IngestController | Controller | Handles `/ingest` and `/ingest/batch` — entry point for new knowledge | ChunkingService, ValidationRouter |
| ChunkingService | Service | Content-aware chunking: markdown, code, table, prose, mixed strategies | — |
| EmbeddingWorker | Worker | Calls EmbeddingProvider (Voyage AI), stores vectors in `knowledge_chunks` | EmbeddingProvider |
| ValidationRouter | Service | Routes items to auto-approve (T1), human review queue (T2), or confidence-flagged (T3/T4) | — |
| KnowledgeRepository | Repository | CRUD + soft-delete on `knowledge_items` and `knowledge_chunks` | PostgreSQL |
| SearchController | Controller | Handles `/search`, `/ask`, `/similar` — entry for retrieval queries | RetrievalPipeline |
| RetrievalPipeline | Service | Orchestrates: embed query → vector search → scope filter → graph walk → rerank → top-N | KnowledgeRepository, RankingService, GraphService |
| GraphService | Service | Apache AGE graph queries — knowledge relationships, graph walk for retrieval (P2 G3) | PostgreSQL (AGE extension) |
| RankingService | Service | Six-signal ranking: similarity, freshness, confidence, scope proximity, usage frequency, recency. Signal weights are configurable per deployment (table values in DT-03 are defaults). | — |
| PromotionService | Service | Promotes client-scoped knowledge to product-level; generates generalised version using suggest-and-confirm pattern (system proposes, human confirms) | KnowledgeRepository |
| FreshnessHandler | Handler | Reacts to domain events (ReleaseDeployed, SourceDataChanged) to update `freshness_score` | (Event bus) |
| LLMProvider | Interface | Abstracts Claude API: `complete()`, `classify()` | Claude API |
| EmbeddingProvider | Interface | Abstracts Voyage AI: `embed()`, batch support | Voyage AI |

**Key interaction:** `/ask` triggers `SearchController → RetrievalPipeline → RankingService`, then hands ranked chunks to the Context Assembly Orchestrator for prompt construction before calling LLMProvider.

---

## 3. Context Assembly Orchestrator

**Technology:** TypeScript | **Bounded contexts:** Work Context, Agent Runtime

Assembles the complete prompt for every AI interaction. Manages the token budget across all prompt layers and orchestrates the two-tier knowledge model (cached Tier 1 + retrieved Tier 2).

| Component | Type | Responsibility | Depends On |
|-----------|------|---------------|------------|
| ContextAssembler | Service | Sequences all prompt layers in defined assembly order | TokenBudgetManager, all layer sources |
| TokenBudgetManager | Service | Tracks token usage per layer; enforces shedding priority when budget is tight | — |
| SystemPromptLoader | Service | Loads system prompt + core protocol rules for the deployment | DeploymentRepository |
| CachedKnowledgeLoader | Service | Loads Tier 1 cached knowledge payload for the deployment type | DeploymentRepository |
| ScratchpadReader | Repository | Reads session scratchpad entries for the active session | PostgreSQL |
| ScratchpadWriter | Repository | Writes scratchpad entries (write-through — DB immediately) | PostgreSQL |
| RAGInjector | Service | Injects Tier 2 retrieved chunks into prompt at correct position | RetrievalPipeline |
| SessionContextLoader | Service | Loads active session state, carry-forward facts, open work items | SessionRepository |
| DeploymentRepository | Repository | Reads `constrained_deployments`, system prompt config, tool restrictions | PostgreSQL |
| CacheAssembler | Service | Build-time: assembles Tier 1 cached prompt from knowledge base per deployment type | KnowledgeRepository |

**Assembly order (position in prompt):**
1. System prompt (identity, role, boundaries)
2. Session context (scratchpad + carry-forward facts)
3. User query
4. Retrieved knowledge — Tier 2 (RAG results, per query)
5. Task context (current work item spec)
6. Conversation history
7. Cached knowledge — Tier 1 (domain knowledge, ~120K tokens, droppable — TokenBudgetManager warns user before shedding, no silent drops)
8. Core protocol rules (injected last — recency bias)

---

## 4. Connector Hub

**Technology:** TypeScript | **Bounded context:** Integration

Manages all outbound connections to external systems. Bidirectional: reads from external systems into the Knowledge Engine, writes back approved outputs. Credentials encrypted per-tenant.

| Component | Type | Responsibility | Depends On |
|-----------|------|---------------|------------|
| ConnectorRegistry | Service | Registers available connector types; hot-swap without restart | — |
| ConnectorConfigRepository | Repository | CRUD on `connector_configs` + encrypted `credentials` | PostgreSQL |
| ConnectorExecutor | Service | Executes connector calls with retry, rate limiting, circuit breaker | ConnectorRegistry |
| JiraConnector | Connector | Read/write Jira issues; bidirectional sync | ConnectorExecutor |
| ConfluenceConnector | Connector | Read Confluence pages for knowledge ingestion | ConnectorExecutor |
| ProductAPIConnector | Connector | Read customer product APIs (e.g. time2work API) | ConnectorExecutor |
| WebhookReceiver | Handler | Receives inbound webhooks from external systems (event-driven freshness) | (Event bus) |
| CredentialVault | Service | AES-256 encryption/decryption of connector credentials, per-tenant keys. Interface supports future managed stores (HashiCorp Vault, AWS Secrets Manager). | — |
| SchemaChangeDetector | Service | Detects schema changes on connector sources; flags existing ingested data for review when schema changes | ConnectorExecutor, (Event bus) |
| IngestBridge | Service | Transforms external source data into `KnowledgeItem` ingest format; publishes SourceDataChanged event | (Event bus) |

**Key interaction:** External events arrive via `WebhookReceiver`, pass through `IngestBridge`, and publish `SourceDataChanged` to trigger freshness updates in the Knowledge Engine.

---

See [[deliverable-02-c4-level3-containers|Container Detail Sub-Document]] for Agent Orchestrator, Workflow Engine, and Web UI component tables, plus cross-container interaction flows.

---

## 5. Key Cross-Container Interactions

### Ask Flow (Feature 1)
```
API Gateway (auth + classify) → Knowledge Engine (retrieve + rank)
  → Context Assembly Orchestrator (assemble prompt)
  → Knowledge Engine (LLMProvider.complete)
  → API Gateway (envelope response)
```

### Ingest Flow (Feature 2)
```
API Gateway → Knowledge Engine (chunk + embed + validate)
  → (if T2) Workflow Engine (human review BPMN)
  → Knowledge Engine (store + index)
  → Context Assembly Orchestrator (invalidate/rebuild Tier 1 cache if needed)
```

### Agent Task Flow (Delivery Pipeline)
```
Agent Orchestrator (spawn agent, assign task)
  → Context Assembly Orchestrator (build context from session + task)
  → Knowledge Engine (retrieve domain knowledge)
  → Connector Hub (call product API)
  → Workflow Engine (record step, check BPMN gate)
  → Agent Orchestrator (task complete / hand off)
```

### Defect Capture Flow (Feature 6)
```
API Gateway → Knowledge Engine (semantic duplicate check)
  → Workflow Engine (BPMN routing: triage → assign → Jira sync)
  → Connector Hub (JiraConnector.create)
  → Knowledge Engine (FreshnessHandler on DefectResolved event)
```

---

## 6. Open Items (Gate 3)

- [ ] Sequence diagrams for each key flow (swimlane, not just text)
- [ ] Repository interfaces per aggregate (Gate 3 — Deliverable 3 open item)
- [ ] Event bus design: in-process EventEmitter vs message queue (RabbitMQ, etc.)
- [ ] Component-level error boundaries and fallback behaviour
- [ ] Tier 1 cache invalidation trigger design (when does CacheAssembler re-run?)
- [ ] InputClassifier prompt design and threshold tuning
- [ ] Anti-corruption layers between bounded contexts

---

**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-02-c4-level3.md
