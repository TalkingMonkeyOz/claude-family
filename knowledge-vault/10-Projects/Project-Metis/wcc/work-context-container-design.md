---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - domain/work-context-container
  - type/design
  - domain/augmentation-layer
created: 2026-03-11
updated: 2026-03-11
status: active
---

# Work Context Container — Architecture Design

The WCC is the core mechanism of the METIS Augmentation Layer. It answers one question on every prompt: given what the user is working on right now, which knowledge should be in context?

It does not store knowledge. It assembles context from the six knowledge types based on an active Activity Space, ranks candidates across all sources, and delivers a budget-capped bundle to the Intelligence Layer.

---

## Where It Sits

```
Knowledge Engine (stores)
       ↓
Augmentation Layer
  ├── Activity Space   ← scoping: "what are we working on?"
  ├── WCC Assembler    ← ranking: "which chunks are most relevant?"
  └── Context Injector ← delivery: "put it in the prompt"
       ↓
Intelligence Layer (reasons)
```

The WCC is a C4 Level 3 sub-component of the Augmentation Layer, not a separate container. It is the connective tissue between stored knowledge and active reasoning.

---

## Four-Layer Context Management

Every prompt draws from four layers. The WCC owns Layers 3-4 and informs Layer 2.

| Layer | What | Size | WCC Role |
|-------|------|------|----------|
| **1. Core Protocols** | Task decomposition, boundaries, identity | ~500-1K tokens | Not WCC — system prompt, always present |
| **2. Session Notebook** | Facts from this session: decisions, configs, credentials | ~300-800 tokens | WCC reads this for context; doesn't manage it |
| **3. Knowledge Retrieval** | Chunked, embedded, indexed content retrieved on demand | ~2-8K tokens | WCC assembles this layer |
| **4. Persistent Knowledge** | Cross-session patterns, gotchas, decisions | ~500-2K tokens | WCC assembles this layer |

Layer 3+4 together form the assembled context bundle. Dynamic priority, not fixed allocation — the librarian selects the right chunks, not a fixed token quota per source.

---

## 6 Knowledge Types → Data Model Mapping

| # | Type | Primary Table(s) | RBAC |
|---|------|-----------------|------|
| 1 | Product Domain | `knowledge_chunks` (content_type='product_domain') | Shared across tenants |
| 2 | API/Integration Reference | `knowledge_chunks` (content_type='api_reference') | Shared across tenants |
| 3 | Client Configuration | `client_config` (hard-isolated) | Tenant-isolated |
| 4 | Process/Procedural | `knowledge_chunks` + `activity_workfiles` | Shared with tenant variants |
| 5 | Project/Delivery | `delivery_cache` (TTL-bound) | Tenant-scoped |
| 6 | Learned/Cognitive | `session_facts` + `persistent_knowledge` | Tenant-isolated |

Architecture: separate database per customer (no RLS). Within an instance, Org → Product → Client → Engagement four-tier scope hierarchy provides internal security. Shared types (1-2) are platform-level knowledge available to all scopes within the instance.

---

## 8-Level Retrieval Priority → WCC Implementation

| Level | What | WCC Action |
|-------|------|-----------|
| 1. Session facts | Credentials, decisions this session | Always inject; not ranked |
| 2. Activity Space scope | Current activity narrows all subsequent retrieval | Detect activity; filter all queries |
| 3. Cognitive/Learned | Gotchas, patterns, decisions from memory | Query `persistent_knowledge`, tier='long' first |
| 4. Knowledge graph | 2-hop relation walk from L3 seeds | Follow `explicit_relations` (contradicts/supersedes/depends_on) |
| 5. Product Domain | Product schema, business rules, entities | Query `knowledge_chunks` scoped to activity |
| 6. API Reference | Endpoints, OData entities, auth patterns | Only if activity signals integration work |
| 7. Client Config | Per-tenant configuration | Only if specific client in scope |
| 8. Project/Delivery | Jira tasks, release notes (cached, transient) | Lowest — most stale, most volatile |

Levels 3-8 all feed the single ranking pipeline. Level 2 (Activity Space) is a filter, not a retrieval source.

---

## Detail Documents

| Document | Covers |
|----------|--------|
| [[wcc-activity-space-design]] | Activity entity design, detection mechanism (embedding-based), lifecycle, scoping mechanics |
| [[wcc-ranking-design]] | Single retrieval path, 6 ranking signals, assembler algorithm, performance targets |
| [[wcc-ranking-agentic-routing]] | Agentic routing triggers and architecture, per-source budget challenge, feedback loop closure |
| [[wcc-mechanics-feedback-design]] | Four-layer session mechanics, feedback loops, co-access tracking, freshness scoring |

---

## Challenges to Accepted Decisions

These are honest findings from the CF prototype that affect the design choices made in the Knowledge Engine session.

### Challenge 1: 3 Tiers → 2 Tiers

**Decided**: Short/Mid/Long cognitive memory tiers.

**Prototype shows**: Short tier is functionally unused in CF (session_facts handles that role). Mid has 96.5% of all knowledge because promotion from Mid→Long requires `mark_knowledge_applied()` — a call nobody makes. Three named tiers with independent promotion rules is more complex than it is useful.

**Recommendation**: Two tiers. Session-scoped (replaces Short + early Mid) auto-expires at session end. Persistent (replaces Long) earned through successful retrieval, not explicit API call. The METIS four-layer framing (Session Notebook / Persistent Knowledge) already embodies this.

**Why**: Simpler rules → higher compliance. The distinction that matters is "this session only" vs "survives across sessions", not "mid-confidence" vs "high-confidence."

### Challenge 2: Word Overlap → Embedding-Based Activity Detection

**Decided (implicitly, via prototype)**: Activity detection using trigram/word-overlap matching.

**Prototype shows**: Dead constant `MIN_ACTIVITY_SIMILARITY = 0.6` declared but the detection path uses PostgreSQL trigram similarity, not embeddings. False positives on long activity names. "Authentication token management" matches "token" queries unrelated to that activity.

**Recommendation**: Embedding-based detection. Compute embedding of current prompt. Compare cosine similarity against per-activity name+description embeddings stored in `activity_embedding` column. Threshold 0.6 is correct — just implement it with actual vectors.

**Why**: Trigrams match substrings. Embeddings match semantics. "How do I cache API responses?" semantically matches the auth-token activity less than it matches a caching activity, even if "token" appears in both.

### Challenge 3: Event-Driven Promotion (Already Recommended, Mechanism Needed)

**Decided**: Event-driven staleness via source change events.

**Prototype shows**: Promotion criteria exist in code but the triggering events are never emitted. `mark_knowledge_applied()` is defined but never called. The loop is open.

**Recommendation**: Auto-promotion on two events: (a) item retrieved AND in context when the user completes a task successfully, (b) item retrieved 3+ times across different activities. No explicit API call required — the retrieval pipeline fires the events.

---

*Related: [[work-context-container-synthesis]], [[wcc-activity-space-design]], [[wcc-ranking-design]], [[wcc-mechanics-feedback-design]]*
*Research base: [[library-science-research]], [[filing-records-management-research]], [[augmentation-layer-research]]*

---

**Version**: 1.1
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/work-context-container-design.md
