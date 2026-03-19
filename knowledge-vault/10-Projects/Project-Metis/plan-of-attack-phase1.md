---
projects:
  - Project-Metis
tags:
  - project/metis
  - type/plan
---

> **⚠️ Design Reference Only** — Execution state has moved to the build board (`get_build_board("project-metis")`). For current decisions, use `recall_entities("metis decision")`. This document captures the original design rationale.

# Phase 1: Core Platform

**Goal:** Build the Knowledge Engine and Augmentation Layer so the system can answer questions, assemble context, and manage agent sessions — then dog-food it on METIS's own build before releasing to customers.

Back: [[plan-of-attack-phase0|Phase 0]] | Master: [[plan-of-attack|Plan of Attack]] | Next: [[plan-of-attack-phase2|Phase 2]]

---

## Entry Criteria

- Phase 0 exit criteria fully met
- Voyage AI API access confirmed
- Claude API (Anthropic) access confirmed
- Decision: first connector type selected (Confluence or file-drop)

---

## Deliverables

| Deliverable | Feature Area | Bounded Context | Depends On |
|-------------|-------------|----------------|------------|
| Content-aware chunking service | F119 | Knowledge Store | Phase 0 schema |
| EmbeddingProvider interface + Voyage AI impl | F119 | Knowledge Store | Chunking |
| Ingestion pipeline (P1) | F119 | Knowledge Store | Chunking + Embedding |
| Validation tier routing (T1/T2/T3/T4) | F119 | Knowledge Store | Ingestion pipeline |
| Knowledge item + chunk schema | F119 | Knowledge Store | Phase 0 schema |
| Vector search + scope filtering | F119 | Knowledge Store | Embedding worker |
| Apache AGE graph walk (P2 G3) | F119 | Knowledge Store | AGE installed (Phase 0) |
| Ranking pipeline — 6 signals | F119 | Knowledge Store | Vector search + graph |
| Event-driven freshness handler | F119 | Knowledge Store | Ranking pipeline |
| Context Assembly Orchestrator | F125 | Work Context | Knowledge Engine |
| Token budget manager + warn-before-shed | F125 | Work Context | CAO |
| Session + scratchpad persistence | F125 | Agent Runtime | Phase 0 schema |
| Cognitive memory entity | F125 | Work Context | Session persistence |
| Activity + co_access_log schema (C2-3) | F125 | Work Context | Phase 0 schema |
| Workflow instance schema (C2-4) | F125 | Work Context | Phase 0 schema |
| LLMProvider interface + Claude impl | F125 | Cross-cutting | CAO |
| /ask endpoint | F119 | Knowledge Store | Intelligence Layer |
| Constrained deployment v1 (F128) | F128 | Commercial | Intelligence Layer |
| MCP tool server (~6 intent-level tools) | F125 | Cross-cutting | Intelligence Layer |
| InputClassifier (Haiku gatekeeper) | F125 | Cross-cutting | LLMProvider |
| Web UI — basic chat interface | F119 | Cross-cutting | /ask endpoint |
| Connector adapter interface | F120 | Integration | Phase 0 schema |
| First connector (Confluence or file-drop) | F120 | Integration | Connector interface |
| Credential vault (OAuth + encrypted fallback) | F120 | Integration | Connector interface |
| Data retention configuration (C2-5) | F125 | Cross-cutting | Phase 0 schema |
| Admin centre — operational parameters | F125 | Cross-cutting | All configurable params |
| Query logging + feedback capture | F119 | Knowledge Store | /ask endpoint |
| Retrieval quality metrics (eval framework) | F119 | Knowledge Store | Query logging |
| Monitoring custom tables (C6-1) | F125 | Cross-cutting | All of above |

---

## Build Order

### Cluster A — Knowledge Engine (builds on Phase 0 DB)

**A1. Knowledge schema**
Add `knowledge_items`, `knowledge_chunks`, `knowledge_relations`, `knowledge_promotions` tables. Every chunk stores: `content_type`, `token_count`, `embedding_model`, `embedding_dimensions`, `freshness_score`, full scope chain (C2-2). No chunk without token count.

**A2. Chunking service**
Content-aware strategies per type:
- API specs: chunk by endpoint
- OData: chunk by entity
- Prose/markdown: chunk by section
- Code: chunk by function
Max chunk size enforced; token count mandatory. Store `content_type` on every chunk.

**A3. EmbeddingProvider interface + Voyage AI implementation**
Define `EmbeddingProvider`: `embed(text): vector`, `embedBatch(texts): vector[]`. Implement for Voyage AI (1024-dim embeddings). Hot-swappable — interface must not leak Voyage specifics.

**A4. Ingestion pipeline (P1)**
Ingest controller → chunking → embedding → validation tier routing → storage.
Tier routing: T1 auto-approve, T2 human review queue, T3 confidence-flagged, T4 always flagged.
Semantic duplicate check at ingestion (G3 in P1).

**A5. Vector search + scope filtering**
pgvector cosine similarity search. Scope filter applied before returning results (never return out-of-scope items regardless of similarity score).

**A6. Apache AGE graph walk**
Implement `GraphService` using Apache AGE. Used in P2 G3: after vector search, walk 1-2 hops to find structurally related knowledge. Results merged at lower priority than direct vector matches.

**A7. Ranking pipeline**
`RankingService` with 6 signals: vector similarity (0.55), co-access frequency (0.30), task relevance boost (0.15 binary), freshness multiplier, recency multiplier, feedback multiplier. Signal weights stored in config, not hardcoded (BC-1). One dedup step, one budget cap.

**A8. Event-driven freshness**
`FreshnessHandler` reacts to domain events: `ReleaseDeployed`, `SourceDataChanged`, `DefectResolved`. Updates `freshness_score` on affected chunks. No scheduled decay jobs.

---

### Cluster B — Augmentation Layer (requires Knowledge Engine)

**B1. Session + scratchpad schema**
Add `sessions`, `session_facts`, `scratchpad_entries` tables. Write-through pattern: every scratchpad write goes to DB immediately (survives context compaction).

**B2. Context Assembly Orchestrator**
`ContextAssembler` executes assembly order (8 layers, P3). `TokenBudgetManager` tracks per-layer usage. Shedding priority: RAG results drop first, then conversation history (oldest first), then cached Tier 1 knowledge last. Before shedding, warn the user with options — never silent (BC-2).

**B3. Cognitive memory + Activity schema**
Add `cognitive_memory`, `activities`, `activity_access_log` (C2-3). Activity lifecycle: created → active → semi-active → archived. WCC computed on demand, budget-capped, cached.

**B4. Workflow instance schema**
Add `workflow_instances` + `workflow_step_log` (C2-4). Write-through: engine state is queryable from DB, engine owns execution internals.

---

### Cluster C — Intelligence Layer (requires Augmentation)

**C1. LLMProvider interface + Claude implementation**
Define `LLMProvider`: `complete(prompt): response`, `classify(text): label`. Implement for Claude API. Handles token counting, rate limiting, cost tracking internally. Hot-swappable.

**C2. /ask endpoint**
`SearchController → RetrievalPipeline → RankingService → ContextAssembler → LLMProvider`. Returns answer + source citations + confidence score. Every query logged (query logging, A-eval below).

**C3. InputClassifier**
Haiku-model gatekeeper on API gateway. Rejects off-topic queries before they reach the Knowledge Engine. Configurable scope per deployment.

**C4. Constrained deployment v1 (F128)**
Deployment configuration: system prompt template + knowledge scope + tool restrictions + audience. Cached system prompt (up to 200K tokens). 5-question validation before publish. Three constraint levels: L1 Guided, L2 Assisted, L3 Open.

**C5. MCP tool server**
~6 intent-level composite tools (C4-3). Agents call tools by intent, not by raw API. MCP server adapter translates tool calls to internal REST calls via API gateway.

**C6. Basic web UI**
React 19 + Vite + MUI. Chat interface for /ask. Auth-gated. No SSR. Static bundle served by Fastify. Confidence badge, source citations, feedback button.

---

### Cluster D — Integration Hub (requires Cluster C)

**D1. Connector adapter interface**
`ConnectorConfig` aggregate + `Credential` entity. Unified interface for API/file-drop/manual connectors (C3-3). Connector direction configurable (read/write/bidirectional). Hot-swappable without restart.

**D2. Credential vault**
Hybrid OAuth + encrypted vault fallback (C5-1). Interface designed to support future managed stores (HashiCorp Vault, AWS Secrets Manager) — add the abstraction now. Per-tenant encryption key.

**D3. First connector**
Confluence (preferred) or file-drop. Triggers P6 (Connector Sync): `SourceDataChanged` event → ingestion pipeline. Schema change detection: if connector schema changes, flag existing ingested data for review (BC-8).

---

### Cluster E — Eval + Operations (requires /ask + first connector)

**E1. Query logging + feedback capture**
Every /ask call logs: query text, retrieved chunks with scores, user feedback (thumbs/rating). Foundation for retrieval quality measurement.

**E2. Retrieval quality metrics**
Precision@K, MRR against a small human-labelled test set. Run after each deployment to confirm retrieval has not degraded. Gate for Phase 1 exit.

**E3. Admin centre — operational parameters**
Web UI section (or API) exposing configurable parameters: token budget levels (C6-2), retention presets (C2-5), SLO targets (C6-3), log retention tiers (C6-4), ranking signal weights, sub-agent cap (BC-4). Sensible defaults for all; no hardcoded operational constants.

**E4. Monitoring custom tables**
Structured logging to DB tables first (C6-1). Schema designed with Prometheus+Grafana export in mind. Token usage, latency, error rates, retrieval scores captured.

---

## Dog-Food Gate

Before Phase 2 begins, the platform must be used to help build itself:

- Use /ask to answer questions about METIS's own design (ingest Gate 2 deliverables)
- Use MCP tools from a Claude session to query METIS knowledge
- Use constrained deployment to create an internal assistant for the build team
- Document what breaks, what's slow, what's missing
- Fix critical issues before Phase 2 starts

**Principle (D03):** If the Augmentation Layer cannot help build METIS, it cannot help build anything else.

---

## Exit Criteria

- [ ] /ask returns accurate, cited answers with confidence scores
- [ ] Ingestion pipeline handles at least two content types correctly
- [ ] Apache AGE graph walk returns related items in retrieval (P2 G3)
- [ ] Context Assembly respects token budget; warns before shedding
- [ ] Constrained deployment v1 published and validated with 5-question check
- [ ] MCP tool server operational; at least one agent task completed via MCP
- [ ] First connector syncing; connector schema change detection working (BC-8)
- [ ] Retrieval quality metrics baseline established
- [ ] Admin centre exposes all configurable operational parameters
- [ ] Dog-food gate: platform used on METIS build; critical issues resolved

---

## Key Risks

| Risk | Mitigation |
|------|------------|
| Augmentation Layer complexity delays /ask | Build Knowledge Engine first, wire /ask without full CAO, then upgrade |
| Apache AGE adds complexity without clear retrieval benefit | Measure graph walk contribution at E2; only keep if it improves metrics |
| Warn-before-shed UX is hard to get right | Prototype in web UI before finalising; user must understand options clearly |
| MCP tools too granular or too composite | Start with ~6 intent tools; expand only if agents demonstrate need |
| Dog-food gate reveals architectural issues | Build dog-food gate early (mid-phase), not at the end, to allow course correction |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/plan-of-attack-phase1.md
