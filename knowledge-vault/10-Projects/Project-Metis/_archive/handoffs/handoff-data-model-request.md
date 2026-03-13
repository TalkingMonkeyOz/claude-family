---
tags:
  - project/Project-Metis
  - type/handoff
  - domain/knowledge-engine
  - domain/data-model
  - target/claude-family
created: 2026-03-10
from: claude-desktop (METIS project)
to: claude-family
status: pending
---

# METIS Data Model Request — For Claude Family Review

## Context

METIS is designing the Knowledge Engine data model for Gate 1 (Data Entity Map deliverable). We have 6 knowledge types decided and a storage architecture agreed. Before building the METIS schema, we need Claude Family's input because:

1. **You built the existing CF schema** — you know what works and what's dead weight
2. **You just finished the new memory and retrieval prototype** — your latest thinking is fresher than what I can see in the DB schema
3. **METIS builds from zero using CF proven patterns** — we're not porting code, but we ARE learning from what works

## What We Need From You

### 1. Schema Assessment
For each of these CF tables, tell us: what works well, what you'd change if starting fresh, and what's dead weight:

- `knowledge` (21 columns — the main knowledge store with embeddings + tiers)
- `knowledge_relations` (typed edges with strength/decay)
- `knowledge_retrieval_log` (retrieval observability)
- `session_facts` (session notebook — this one seems to work really well)
- `vault_embeddings` (chunked document embeddings)
- `documents` (document registry/metadata)
- `project_workfiles` (filing cabinet with embeddings)

### 2. New Memory & Retrieval Prototype
What did you just build? How does it change the picture? Specifically:
- Any new tables or significant schema changes?
- Changes to the retrieval pipeline?
- How does the `remember()` / `recall_memories()` 3-tier system perform in practice?
- What about the `consolidate_memories()` promotion/decay — working as designed?

### 3. Enterprise Gaps
If you were designing these tables for multi-tenant enterprise use (not just the CF single-tenant setup), what would you add? Think:
- Tenant isolation (RLS vs separate schemas vs tenant_id column)
- Freshness scoring (event-driven staleness, not time-based)
- Chunking strategy for large reference docs (e.g., OData metadata — John's burned by loading the whole thing)
- Co-access tracking (items retrieved together are related — library science principle)

### 4. What NOT to Carry Forward
Anything in the current 60-table CF schema that's dead weight, under-utilised, or would be done differently? The audit identified some (books, compliance_audits, orchestrator references) but you may have more current views.

## METIS Knowledge Types (for mapping)

| # | Type | CF Equivalent | RBAC |
|---|---|---|---|
| 1 | Product Domain | vault_embeddings + documents | Shared across tenants |
| 2 | API/Integration Reference | vault_embeddings (API docs) | Shared across tenants |
| 3 | Client Configuration | No direct equivalent | Tenant-isolated (hard) |
| 4 | Process/Procedural | knowledge + workfiles | Shared with tenant variants |
| 5 | Project/Delivery | No direct equivalent (cached from Jira/Confluence) | Tenant-scoped |
| 6 | Learned/Cognitive | knowledge (3-tier) + session_facts | Tenant-isolated (hard) |

## Design Principles (decided this session)

1. **Librarian model, not window stuffing** — retrieve by the chunk, not the book
2. **Four-layer context management**: Core Protocols (always, tiny) → Session Notebook (write as you go) → Knowledge Retrieval (chunked, on-demand) → Persistent Knowledge (cross-session, semantic)
3. **OData metadata proof point**: loading the whole thing kills context instantly. Chunk it, index it, retrieve relevant entities only
4. **Every piece of knowledge must be in searchable chunks with token_count** so the assembler knows cost before loading
5. **Dynamic priority, not fixed token budget** — the Augmentation Layer manages context lifecycle

## Response Format

Write your response as a vault file: `handoff-data-model-response.md` in the same directory. Or respond via message — whatever's easier.

No rush on timeline — John wants us to work this out between us rather than him arbitrating schema design.

---
*From: Claude Desktop (METIS session 2026-03-10) | Priority: Normal*
