---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/7
  - type/api-design
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 7: API & Interface Design

## Overview

METIS exposes two interfaces: **REST API** (granular, for developers) and **MCP server** (composite, for agents). Build order: MCP/API first, web UI second. All endpoints require JWT authentication with scope headers.

---

## 1. REST API Endpoints

### Knowledge Operations

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/ask` | Natural language question → answer with citations | User scope |
| POST | `/search` | Semantic search across knowledge base | User scope |
| POST | `/ingest` | Ingest single knowledge item | Write permission |
| POST | `/ingest/batch` | Batch ingest multiple items | Write permission |
| POST | `/validate` | Validate content against rules/constraints | User scope |
| POST | `/promote` | Promote draft/learned knowledge to validated | Admin/elevated |
| POST | `/similar` | Find semantically similar knowledge items | User scope |
| GET | `/knowledge/{id}` | Get specific knowledge item | User scope |
| GET | `/knowledge/{id}/history` | Version/change history | User scope |
| GET | `/knowledge/{id}/graph` | Related items graph | User scope |
| GET | `/categories` | List knowledge categories | User scope |
| POST | `/feedback` | Submit feedback on answers | User scope |
| GET | `/health` | System status check | Public |

### Request/Response Conventions

**All responses** follow a consistent envelope:

```json
// Success
{
  "data": { ... },
  "pagination": { "cursor": "...", "has_more": true, "limit": 20 }
}

// Error
{
  "error": {
    "code": "KNOWLEDGE_NOT_FOUND",
    "status": 404,
    "message": "Human-readable message safe to display",
    "detail": "Debug info (stripped in prod)",
    "request_id": "req_7f8a9b2c",
    "timestamp": "2026-03-15T09:30:00Z"
  }
}
```

**Scope headers** (every request):
```
X-Org-Id: uuid
X-Product-Id: uuid (optional)
X-Client-Id: uuid (optional)
X-Engagement-Id: uuid (optional)
```

### Pagination (C4-2)

Cursor-based for all list endpoints. Stable under data changes.

```
GET /categories?limit=20&after=eyJpZCI6MTIzfQ
```

---

## 2. MCP Server Tools

Intent-level composites, not 1:1 with REST (C4-3). Agents call these automatically.

| Tool | Intent | Internally Orchestrates |
|------|--------|------------------------|
| `ask` | Answer a question | search → rank → context assemble → generate → cite |
| `learn` | Ingest knowledge | classify → chunk → embed → store (single or batch) |
| `check` | Validate content | validate against rules + knowledge base |
| `find` | Discover knowledge | search + similar + graph traversal |
| `manage` | Change knowledge state | promote / archive / update / categorise |
| `status` | System health | health + metrics + active workflows |

**Design principle:** Start with ~6 composites. Split only when demonstrated need. Modelled after project-tools `remember()` pattern — one call, system figures out routing.

### MCP Tool Schema (example — `ask`)

```json
{
  "name": "ask",
  "description": "Ask a question and get an answer with citations",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": { "type": "string" },
      "scope": {
        "type": "object",
        "properties": {
          "product": { "type": "string" },
          "client": { "type": "string" },
          "engagement": { "type": "string" }
        }
      },
      "max_sources": { "type": "integer", "default": 5 },
      "include_confidence": { "type": "boolean", "default": true }
    },
    "required": ["question"]
  }
}
```

---

## 3. LLM Abstraction Layer (C4-4)

Two separate provider interfaces — different vendors, different swap-out points.

### LLMProvider

```typescript
interface LLMProvider {
  complete(request: CompletionRequest): Promise<CompletionResponse>
  classify(text: string, categories: string[]): Promise<ClassificationResponse>
  estimateTokens(text: string): number
  getModelInfo(): ModelInfo
}
```

Current implementation: Claude API (Anthropic). Handles: token counting, rate limiting, cost tracking per customer.

### EmbeddingProvider

```typescript
interface EmbeddingProvider {
  embed(texts: string[]): Promise<EmbeddingResponse>
  getDimensions(): number
  getModelInfo(): ModelInfo
}
```

Current implementation: Voyage AI. Handles: batch processing, dimension management, cost tracking.

### Why Split

- Different vendors (Claude ≠ Voyage AI)
- Different cost profiles and rate limits
- Different upgrade cycles
- A customer might swap one but not the other

---

## 4. Web UI (Phase 2)

Deployed as static React + MUI bundle (Decision C1-2). Served by Fastify or CDN.

### Key Screens (Conceptual)

| Screen | Purpose | API Calls |
|--------|---------|-----------|
| Knowledge Search | Search and browse knowledge | `/search`, `/categories` |
| Ask | Conversational Q&A | `/ask`, `/feedback` |
| Ingest | Upload/manage knowledge sources | `/ingest`, `/ingest/batch` |
| Admin — Retention | Configure retention policies | Admin API |
| Admin — Budgets | Configure token budgets | Admin API |
| Admin — Users | Manage users, roles, permissions | Admin API |
| Admin — Connectors | Configure data connectors | Admin API |

### Admin API (Not Yet Specified)

Admin endpoints for retention, token budgets, SLOs, user management, connector config. These are CRUD operations on config tables — will be specified in Gate 3.

---

## 5. Open Items (Gate 3)

- [ ] Detailed request/response schemas for each endpoint
- [ ] Admin API endpoint specifications
- [ ] MCP tool response schemas
- [ ] Rate limiting strategy (per-user, per-customer)
- [ ] WebSocket design for real-time workflow updates
- [ ] Endpoint naming consistency review
- [ ] `/knowledge/{id}/graph` performance design at scale
- [ ] API versioning strategy

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-07-api-interface.md
