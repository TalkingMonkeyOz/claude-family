---
tags:
  - project/Project-Metis
  - area/knowledge-engine
  - scope/system
  - type/brainstorm
  - phase/1
projects:
  - Project-Metis
created: 2026-02-23
synced: false
---

# Knowledge Engine Deep Dive — Brainstorm Capture

> The central knowledge service for The System. Ingests, stores, retrieves, and reasons over everything an organisation knows about its products, customers, and delivery.

**Date:** 2026-02-23
**Session:** Focused Chat #2 — Knowledge Engine Deep Dive

---

> **DESIGN PRINCIPLES — READ BEFORE EDITING**
>
> 1. **This is a generic product design.** The System serves any development house with a complex product and professional services arm. Do not design for nimbus specifically — nimbus is the first customer deployment.
> 2. **Clean slate.** The System is built from scratch. No legacy schemas, no inherited tables. Concepts and lessons from prior work (Claude Family RAG system) inform the design but nothing is migrated structurally.
> 3. **Provider-agnostic.** Embedding models, vector databases, and LLM providers are all pluggable. No hard dependency on any single vendor.
> 4. **Every response has provenance.** Sources, confidence scores, and validation status on every answer. Non-negotiable for audit and trust.
> 5. **Scope is always explicit.** Multi-tenant by design. Every query declares its context. The system enforces data isolation.

---

## 1. Technology Stack Validation (Feb 2026)

Validated current choices against the state of the market.

### Embedding Models

**Current choice: Voyage AI** — still top-tier for retrieval quality, but ownership has changed. MongoDB acquired Voyage AI for $220M in February 2025. The API remains available independently and via AWS/Azure Marketplaces. Voyage 4 series launched January 2026.

**Risk:** MongoDB may eventually gate best models behind Atlas. For a product that must be infrastructure-agnostic, this is a vendor dependency.

**Decision:** Use Voyage AI for initial development. Design a **pluggable embedding interface** so any customer can choose their provider. Viable alternatives: OpenAI text-embedding-3-large, Cohere embed-v4, self-hosted open-source (BGE-M3, e5 family) for data sovereignty requirements.

**Key spec:** Whatever model is chosen, track the model name and dimension count per embedding. Switching providers requires re-embedding all content — the interface must support bulk re-embed operations.

### Vector Database

**Current choice: pgvector (PostgreSQL extension)** — confirmed as the right default. Benchmarks show 470+ QPS at 99% recall on 50M vectors. Recommended for RAG applications under 50-100M vectors, which covers any customer deployment for years.

**Decision:** pgvector is the default. The architecture should not preclude swapping to a dedicated vector DB (Qdrant, Pinecone) for customers who outgrow pgvector, but this is a future concern.

### RAG Framework

**Decision:** Custom build, no framework dependency. LangChain adds complexity without benefit at this scale. LlamaIndex is the natural upgrade path for the retrieval layer if needed later.

> **Lesson from Claude Family:** A custom RAG pipeline with Voyage AI embeddings + pgvector cosine similarity + automatic context injection works well. Sub-100ms query times achieved on ~9,000 embedded documents. The infrastructure pattern is proven — what matters is knowledge quality, not framework choice.

### LLM Provider

**Decision:** Claude API as default, but the intelligence layer must use an LLM abstraction interface. Customers may need OpenAI, self-hosted models, or other providers for data sovereignty or commercial reasons.

---

## 2. Domain Structure — Multi-Tenant Knowledge Hierarchy

### Four-Level Scope Hierarchy

Every piece of knowledge in The System is scoped to one of four levels:

```
Organisation (the development house using The System)
  └── Product (their software product(s))
       └── Client (end-clients of the development house)
            └── Engagement (a specific project/implementation for a client)
```

| Level | What It Represents | Example |
|-------|--------------------|---------|
| **Organisation** | The company using The System | Any dev house or software company |
| **Product** | A software product they build/deliver | Their SaaS platform, their ERP, etc. |
| **Client** | A customer of the dev house | A university, a hospital, a retailer |
| **Engagement** | A specific project for a client | Phase 2 rollout, annual upgrade, POC |

### Where Knowledge Lives

| Knowledge | Typical Scope | Shared Downward? | Example |
|-----------|--------------|------------------|---------|
| Product API docs | Product | Yes — all clients see it | REST endpoint documentation |
| Compliance rules | Product + jurisdiction | Yes, within jurisdiction | Industry-specific regulations |
| Implementation patterns | Product | Yes — all clients benefit | "When client needs X, configure Y" |
| Client org structure | Client | No — isolated | Their departments, teams, contacts |
| Client tech landscape | Client | No — isolated | Their other systems, integration points |
| Client configuration | Client | No — isolated | Their specific setup and requirements |
| Engagement decisions | Engagement | No — engagement-specific | "Client decided X on date Y" |
| Organisation SOPs | Organisation | Yes — all products/clients | "How we run data migrations" |

### Inheritance Model

**Down = automatic.** When querying at client level, product-level knowledge is always included. When querying at engagement level, client and product knowledge are included.

**Up = controlled promotion.** Knowledge learned at client/engagement level can be promoted upward through an anonymisation and approval workflow. This is how "every client makes the system smarter" actually works.

### Scoping Implementation

Every knowledge item has nullable foreign keys to all four levels:

- `organisation_id` — always set
- `product_id` — null means org-wide (SOPs, procedures)
- `client_id` — null means product-wide (API docs, patterns)
- `engagement_id` — null means client-wide (their config, their context)

Retrieval query applies scope filter:
```
WHERE organisation_id = :org
  AND (product_id = :product OR product_id IS NULL)
  AND (client_id = :client OR client_id IS NULL)
  AND (engagement_id = :engagement OR engagement_id IS NULL)
```

This gives inheritance for free — product-level items always match because their client_id is NULL.

---

## 3. Cross-Client Learning — Knowledge Promotion

The strict scope hierarchy protects data isolation. The promotion mechanism enables cross-client learning without breaking isolation.

### How It Works

```
Engagement knowledge (raw, client-identified)
    ↓ [promote: anonymise + generalise]
Product-level pattern (available to all clients)
```

Each promotion step:
1. Strips client-specific identifiers (names, values, specific references)
2. Generalises the language into a reusable pattern
3. Requires Tier 2 validation (human review — always, for promoted knowledge)
4. Links back to the source for audit (visible to org admins only, not to other clients)

### Automatic Promotion Candidates

The system flags candidates when:
- A support resolution pattern doesn't exist at product level yet
- An implementation approach is used successfully across 2+ clients
- A defect or issue affects multiple clients with similar configurations

### What Never Promotes

- Client configuration specifics (their actual values, their data)
- Client context (org structure, contacts, tech landscape)
- Decision records (always engagement-scoped)
- Anything the client has marked as confidential

### Schema

```
knowledge_promotions
├── id (UUID)
├── source_item_id (FK → knowledge_items)
├── promoted_item_id (FK → knowledge_items)
├── promoted_by (FK → users)
├── promoted_at (timestamp)
├── anonymisation_notes (text)
├── approval_status (pending | approved | rejected)
├── approved_by (FK → users, nullable)
├── approved_at (timestamp, nullable)
```

---

## 4. Knowledge Categories — Configurable Taxonomy

### Why Not Fixed Types

The original design had eight fixed knowledge types. This is too rigid for a generic product. Different organisations will have different knowledge structures. The categories must be configurable.

### Six Default Categories

The System ships with these defaults. Organisations can add, rename, or extend.

**Category A: Product Knowledge** — about the software being implemented
- API/technical documentation
- UI/UX documentation
- Configuration options and patterns
- Release notes and changelogs

**Category B: Domain/Compliance Knowledge** — rules governing usage
- Regulatory and legal rules
- Industry standards
- Certification requirements
- Best practices and methodologies

**Category C: Delivery Knowledge** — how to implement and support
- Implementation patterns
- Support resolution patterns
- Procedures and SOPs
- Testing patterns and scenarios

**Category D: Customer Context** — about the client organisation
- Organisational structure (divisions, teams, reporting lines)
- People and roles (key contacts, decision makers, sponsors)
- Technology landscape (other systems, integration points, data flows)
- Business context (industry, priorities, pain points, calendar, fiscal year)
- Contractual context (what they've bought, SLAs, contract dates)
- Historical context (past projects, relationship history)

**Category E: Engagement Knowledge** — about specific projects
- Decision records
- Requirements and scope
- Change log
- Risk register
- Status and progress

**Category F: Operational Knowledge** — about how the dev house itself runs
- Internal procedures
- Team capabilities and availability
- Tool configurations and access
- Commercial templates and pricing models

### Schema

```
knowledge_categories
├── id (UUID)
├── organisation_id (FK → organisations)
├── code (varchar) — e.g. "product_api", "customer_org_structure"
├── name (varchar) — human-readable
├── parent_category_id (FK → self, nullable) — allows hierarchy
├── default_scope_level (enum: org, product, client, engagement)
├── default_validation_tier (1-4)
├── description (text)
├── is_system (boolean) — true for built-in defaults
├── created_at
```

knowledge_items.category_id references this table instead of using a fixed enum.

---

## 5. Ingestion Pipelines — How Knowledge Gets In

### Generic Pipeline

Every knowledge type follows the same six stages:

```
Source → Parser → Chunker → Embedder → Validator → Store
```

1. **Source:** Where the raw data comes from
2. **Parser:** Extract structured content from the source format
3. **Chunker:** Break into knowledge-sized items
4. **Embedder:** Generate vector embedding (pluggable provider)
5. **Validator:** Apply appropriate validation tier
6. **Store:** Write to knowledge_items with metadata, scope, tags, embedding

> **Lesson from Claude Family:** Chunk size matters enormously for retrieval quality. Too big = noise drowns signal. Too small = lost context. Natural boundaries (one endpoint, one pattern, one resolution) work better than fixed token counts.

### Per-Category Pipeline Patterns

**Product API Knowledge (Category A)**
- Source: Swagger/OpenAPI JSON, OData $metadata XML, or manual upload
- Parser: Fully automated — parse endpoints, parameters, response shapes
- Chunker: One item per endpoint or entity (natural boundaries)
- Validator: **Tier 1 — auto-approved** (system-generated, authoritative source)
- Trigger: On product release or manual re-ingest

**Product UI/UX Knowledge (Category A)**
- Source: Automated screen discovery (Playwright or similar), manual documentation
- Parser: Semi-automated — extract screens, fields, workflows
- Validator: **Tier 2 — human review required**
- Note: Not every customer's product will have a crawlable web UI. Must support manual upload.

**Compliance/Rule Knowledge (Category B)**
- Source: Regulatory documents, agreements, rule definitions — human upload + AI-assisted extraction
- Validator: **Tier 2 — MUST be human-approved** (compliance critical)
- This is the hardest pipeline. AI can help structure and extract, but domain expert must validate.

**Implementation Patterns (Category C)**
- Source: Past implementations, consultant expertise, promoted client knowledge
- Template: "When [scenario], configure [steps], because [rationale], watch out for [gotchas]"
- Validator: **Tier 2 — senior staff approval**
- Highest-value pipeline long-term. Depends on the promotion mechanism.

**Customer Context (Category D)**
- Source: CRM (Salesforce etc.), manual entry, meeting notes, project kick-off docs
- Validator: **Tier 1 for CRM-pulled data, Tier 3 for AI-extracted context**
- Update frequency: Living — updated as the relationship evolves

**Support Knowledge (Category C)**
- Source: Ticketing system (Jira, ServiceNow, etc.)
- Parser: AI extracts problem, root cause, resolution steps
- Chunker: One item per resolution pattern (deduplicate across tickets)
- Validator: **Tier 3 — auto-ingested with confidence flag**

> **Lesson from Claude Family:** Word/keyword matching is poor for knowledge retrieval. Semantic search (vector similarity) dramatically outperforms keyword search for finding relevant knowledge. The System should default to semantic search for all retrieval, with optional keyword filters as refinement.

**Decision Records (Category E)**
- Source: Meeting notes, documented decisions
- Validator: **Tier 3 — auto-ingested, flagged for review**
- Storage: Append-only (immutable)

**Procedures/SOPs (Category F)**
- Source: Internal documentation, consultant knowledge
- Validator: **Tier 2 — human-approved, versioned**

### Pluggable Embedding Interface

```
EmbeddingProvider (interface)
├── generate(text) → vector
├── generate_batch(texts[]) → vectors[]
├── model_name → string
├── dimensions → int
│
├── VoyageAIProvider (voyage-3.5, voyage-4)
├── OpenAIProvider (text-embedding-3-large)
├── CohereProvider (embed-v4)
├── SelfHostedProvider (BGE-M3, e5 via local API)
```

Every knowledge item stores which model generated its embedding:
- `embedding_model` (varchar) — e.g. "voyage-3.5"
- `embedding_dimensions` (int) — e.g. 1024

Switching providers requires re-embedding all content. The interface must support bulk re-embed operations.

---

## 6. Knowledge Items Schema

Core storage table for all knowledge in The System.

```
knowledge_items
├── id (UUID, PK)
├── organisation_id (FK → organisations, NOT NULL)
├── product_id (FK → products, nullable)
├── client_id (FK → clients, nullable)
├── engagement_id (FK → engagements, nullable)
├── category_id (FK → knowledge_categories)
├── title (varchar)
├── content (text)
├── embedding (vector)
├── embedding_model (varchar)
├── embedding_dimensions (int)
├── source_type (enum: system_generated, human_authored, ai_generated, ingested)
├── validation_tier (int, 1-4)
├── validation_status (enum: pending, approved, rejected, flagged)
├── validated_by (FK → users, nullable)
├── validated_at (timestamp, nullable)
├── confidence_score (float 0-1)
├── tags (text array)
├── version (int)
├── supersedes_id (FK → self, nullable) — for versioning chains
├── promoted_from_id (FK → self, nullable) — for promotion audit trail
├── metadata (jsonb) — flexible per-category additional data
├── created_at (timestamp)
├── updated_at (timestamp)
├── created_by (FK → users)
```

### Indexes
- HNSW index on `embedding` for vector similarity search
- B-tree on `organisation_id`, `product_id`, `client_id` for scope filtering
- B-tree on `category_id` for category filtering
- GIN on `tags` for tag-based filtering
- B-tree on `validation_status` for workflow queries

### Tiered Validation Model

| Tier | What | Validation | Why |
|------|------|-----------|-----|
| 1 | System-generated | Auto-approved | Facts from authoritative systems |
| 2 | Structured human knowledge | Human review required | Accuracy is critical |
| 3 | Experiential knowledge | Auto-ingested with confidence flag | Volume too high to review everything |
| 4 | AI-generated | Always flagged, never auto-trusted | AI suggestions are hypotheses |

> **Lesson from Claude Family:** Confidence tracking on knowledge items is essential. Without it, you can't distinguish verified facts from AI-generated guesses. Every item needs a confidence score AND a validation status. They measure different things — confidence is "how sure are we this is right", validation is "has a human checked it".

---

## 7. API Contract — Knowledge Engine Interface

### Design Principles

- The Knowledge Engine is a **service with an HTTP API**. Nothing accesses the database directly.
- Every response includes **provenance** (sources, confidence, validation status).
- **Scope is always explicit** — every request declares org/product/client/engagement context.
- The API serves **both humans and agents** through the same endpoints.

### Authentication & Context

Every request carries:
- **Auth token** (JWT) — identifies user, role, permissions
- **Scope headers** — X-Scope-Org, X-Scope-Product, X-Scope-Client, X-Scope-Engagement

The API uses these to verify access and filter knowledge to visible scope.

### Endpoints

#### POST /api/v1/ask — Natural Language Question (LLM-synthesised)

Ask a question, get an answer with cited sources and confidence score.

**Request:** question, optional intent hint, max sources, confidence threshold
**Response:** answer text, confidence score, array of source items (id, title, type, scope, similarity, snippet), flags/warnings, model used, query ID for feedback

**Internal flow:**
1. Classify question (which knowledge categories are relevant?)
2. Vector search with scope filtering → top-N items
3. Optional rerank
4. Assemble prompt: system instructions + retrieved context + question
5. Call LLM (pluggable interface)
6. Extract source citations, compute confidence
7. Log to audit trail
8. Return

> **Lesson from Claude Family:** Auto-injection of retrieved context (the RAG hook pattern) works well. The user/agent doesn't need to manually search then ask — the system should handle retrieval transparently. But the response must always show what sources were used.

#### POST /api/v1/search — Knowledge Search (pure retrieval, no LLM)

Direct semantic search. Returns ranked knowledge items. No LLM synthesis.

**Request:** query text, optional filters (categories, tags, validation status, min confidence), limit, offset
**Response:** array of knowledge items with similarity scores, total count, query ID

Cheaper and faster than /ask. Used by agents that need raw knowledge, or UIs showing "related knowledge."

#### POST /api/v1/ingest — Submit Knowledge

Add new knowledge item. Used by pipelines, human contributors, and promotion workflow.

**Request:** title, content, category_id, scope (org/product/client/engagement), source_type, tags, related items, metadata
**Response:** item ID, validation status, validation tier, embedding status

Internal flow: validate → determine tier → generate embedding → store → auto-approve or create validation task → log

Auth: `ingest` permission. Different roles can ingest at different scope levels.

#### POST /api/v1/ingest/batch — Bulk Ingestion

For day-one loads, automated pipeline runs (API spec ingestion, CRM sync, historical tickets).

**Request:** array of items (same shape as single ingest)
**Response:** per-item status (created, failed, duplicate detected)

#### PATCH /api/v1/knowledge/{id}/validate — Validate Knowledge

Approve, reject, or flag knowledge items. Used by the validation workflow (BPMN, Area 9).

**Request:** action (approve/reject/flag), notes, optional confidence override
**Auth:** appropriate validation role for the item's tier

#### POST /api/v1/knowledge/{id}/promote — Promote Knowledge Up

Takes client/engagement knowledge and creates a generalised product-level version.

**Request:** target scope, anonymised title, anonymised content, tags
**Internal:** creates new item at target scope → creates promotion record → triggers approval workflow

#### POST /api/v1/knowledge/{id}/similar — Find Related Knowledge

Find knowledge items related to a given item. Used for "see also" links, gap detection, knowledge graph navigation.

**Request:** item ID, optional category/scope filters, limit
**Response:** ranked related items by vector similarity

#### GET /api/v1/knowledge/{id} — Get Single Item

Retrieve a specific knowledge item. Used for viewing, editing, linking.

#### GET /api/v1/knowledge/{id}/history — Version History

All versions of a knowledge item. Supports audit and change tracking.

#### GET /api/v1/categories — List Knowledge Categories

Returns the configurable taxonomy for the current organisation. Used by UIs and pipelines.

#### GET /api/v1/health — System Health

Dashboard data: knowledge counts by category/status, embedding provider info, retrieval latency stats, pending validations/promotions.

#### POST /api/v1/feedback — Query Feedback

After /ask or /search, provide feedback on result quality. Closes the learning loop.

**Request:** query_id, rating (helpful/unhelpful/wrong/incomplete), optional correction text, flag to create knowledge item from correction
**Effect:** corrections can become new knowledge items → validation → improved future retrieval

### Consumer Patterns

| Consumer | Primary Endpoint | Usage |
|----------|-----------------|-------|
| Chat UI (staff) | /ask | Ask question, get answer, give feedback |
| Config Agent (Delivery) | /search | Find patterns and rules for config generation |
| Testing Agent (Quality) | /search | Find test scenarios and expected outcomes |
| Support Triage | /ask + /search | "Has this been seen before?" + resolution search |
| Ingestion Pipeline | /ingest, /ingest/batch | Automated knowledge creation |
| Validation Workflow | /validate, /promote | Human review interface |
| Dashboard | /health | Monitoring and metrics |

---

## 8. Build Sequence

The System's Knowledge Engine is built from scratch. No schema migration from prior systems. Content from prior work (e.g. existing API documentation, known patterns) can be ingested through the standard /ingest/batch pipeline.

### Step 1: Schema Creation
- Create schema in PostgreSQL
- All tables: organisations, products, clients, engagements, users, knowledge_categories, knowledge_items, knowledge_promotions, query_log, feedback
- pgvector extension + HNSW index
- Seed default knowledge categories (A-F with sub-types)

### Step 2: Embedding Provider Interface
- Build pluggable EmbeddingProvider interface
- Implement first provider (Voyage AI or chosen alternative)
- Test with sample documents

### Step 3: Core API Endpoints
- /search first (simplest — pure retrieval)
- /ingest second (needed to populate)
- /ask third (adds LLM layer)
- /health alongside (monitoring from day one)

### Step 4: First Customer Data Load
- Ingest product API documentation via /ingest/batch
- Ingest known implementation patterns
- Ingest existing compliance/rule documentation
- Verify with test queries against known-correct answers

### Step 5: Remaining Endpoints
- /validate, /promote, /feedback, /similar, /ingest/batch
- These support the full lifecycle but aren't needed for initial proof

### Step 6: Integration with Constrained Deployment
- The cached system prompt (200K tokens) gets its content FROM the Knowledge Engine
- Build a script that assembles highest-priority knowledge into a prompt payload
- Bridges constrained deployment pattern with the Knowledge Engine

---

## 9. Open Questions

- [ ] **CRITICAL: Explicit knowledge relationships / knowledge graph.** Semantic search finds similar items, but the platform also needs typed structural links between knowledge items — e.g. "this API endpoint → relates to this config pattern → used in this engagement → produced this support ticket." Without explicit relationships, cross-referencing across sources relies entirely on vector similarity which won't capture causal/structural chains. Design needed: relationship types, how they're created (manual, AI-suggested, automatic from ingestion), how they're queried, and how the /ask endpoint uses them alongside vector search. This is essential to "store it and cross reference it so it's actually useful." Flagged by John Feb 24.
- [ ] What's the chunking strategy for long documents? (Fixed token, semantic boundaries, hierarchical?)
- [ ] How does the configurable taxonomy interact with the BPMN validation workflows? (Each category → different workflow?)
- [ ] Should there be a /knowledge/graph endpoint exposing typed relationships between items?
- [ ] How does knowledge expiry/staleness work? (Review cycles, freshness indicators?)
- [ ] What evaluation framework do we use? (Test questions with known answers — how many, who writes them?)
- [ ] Multi-product organisations — does knowledge ever cross product boundaries?

---

*Source: Focused Chat #2 session, 2026-02-23*
*Next: Continue with remaining focused chats per Master Tracker*
