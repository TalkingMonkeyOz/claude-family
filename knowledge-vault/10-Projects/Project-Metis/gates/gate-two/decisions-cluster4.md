---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - scope/api
created: 2026-03-15
updated: 2026-03-15
---

# Cluster 4: API & Interface Decisions (Detail)

Parent: [[gate-two/decisions-summary|Gate 2 Decisions Summary]]

## C4-1: Error Response Schema

**Decision:** Consistent error envelope for all endpoints.

```json
{
  "error": {
    "code": "KNOWLEDGE_NOT_FOUND",
    "status": 404,
    "message": "Knowledge item abc-123 not found in this engagement",
    "detail": "Searched scope: org=monash, product=nimbus",
    "request_id": "req_7f8a9b2c",
    "timestamp": "2026-03-15T09:30:00Z"
  }
}
```

- `code` — machine-readable enum, clients switch on this
- `message` — human-readable, safe to display to end users
- `detail` — debug info, stripped in production unless elevated permissions
- `request_id` — correlates to backend structured trace logs for debugging
- No stack traces ever exposed (security decision)

---

## C4-2: Pagination

**Decision:** Cursor-based pagination for all list endpoints.

```json
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6MTIzfQ",
    "has_more": true,
    "limit": 20
  }
}
```

Cursor-based over offset because knowledge data changes constantly (ingestion, promotion, decay). Offset pagination breaks under shifting data. Cursor is opaque base64-encoded position token.

---

## C4-3: MCP Tool Design

**Decision:** Intent-level composite tools, not 1:1 with REST.

| MCP Tool | Intent | Wraps |
|----------|--------|-------|
| `ask` | Answer my question | search → rank → assemble → generate → cite |
| `learn` | Here's something to know | classify → chunk → embed → store |
| `check` | Is this right? | validate against rules + knowledge |
| `find` | What do we know about X? | search + similar + graph |
| `manage` | Change knowledge state | promote / archive / update / categorise |
| `status` | How's the system? | health + metrics + active workflows |

~6 composite tools instead of 13+ endpoints. Agents call these automatically. REST API stays granular for developer integrations. Start with composites, split only when demonstrated need. Modelled after project-tools `remember()` auto-routing pattern.

---

## C4-4: LLM Abstraction Interface

**Decision:** Split into two separate provider interfaces.

- **LLMProvider** — `complete()` + `classify()` — for Claude (swappable)
- **EmbeddingProvider** — `embed()` — for Voyage AI (swappable)

Different swap-out points, different vendors, different cost profiles. Each handles token counting, rate limiting, cost tracking per customer. Providers that lack a capability throw "not supported."

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/decisions-cluster4.md
