---
tags:
  - project/Project-Metis
  - type/session-handoff
  - domain/knowledge-engine
  - domain/cognitive-memory
  - domain/architecture
created: 2026-03-10
session: knowledge-engine-design
status: complete
supersedes: 2026-03-09-interaction-model-mcp-review.md
---

# Session Handoff: Knowledge Engine + Cognitive Memory Design

## Session Summary

Analysed the full Claude Family systems audit (all 7 sub-documents), mapped proven patterns to METIS, then designed the Knowledge Engine and Cognitive Memory architecture from first principles. Completed: knowledge types taxonomy, storage architecture, retrieval priority ordering, ingestion model, and decay/promotion/freshness lifecycle. RBAC scoping was proposed but not confirmed.

---

## WHAT WAS DONE

### 1. Claude Family Audit Analysis (COMPLETED)

Read all 7 detailed audit documents. Identified:

**10 proven architecture patterns to carry forward:**
1. Event-driven context injection (hooks → event bus)
2. Multi-source RAG pipeline with assembly ordering
3. 3-tier cognitive memory with promotion/decay lifecycle
4. WorkflowEngine with transition rules + audit trail
5. Column registry for data quality enforcement
6. BPMN-first process governance with L0/L1/L2 hierarchy
7. Encapsulated high-level tool operations
8. Self-healing config from DB source of truth
9. Session lifecycle (start → checkpoint → end) with fact persistence
10. Failure capture → feedback loop

**Dead weight (don't port):** stdin/stdout hook transport, server.py/v2 split, 6 broken slash commands, 6 stale skills, 52 orphaned sessions, under-utilised subsystems (books, compliance_audits), Windows-only file locking, orchestrator references.

**Enterprise gaps to fill:** Token budget management, RAG retrieval quality metrics, multi-tenancy (RLS), migration tooling, structured logging + monitoring, tool namespacing + dynamic loading, REST/gRPC alongside MCP, freshness scoring.

**BPMN enterprise concern:** SpiffWorkflow proves the pattern; production execution engine (Camunda/Temporal) is a Gate 2+ swap-out decision. Not a blocker.

### 2. Knowledge Types Taxonomy (DECIDED — 6 types)

1. **Product Domain** — what time2work is (schema, entities, business rules)
2. **API/Integration Reference** — endpoints, OData, connections, auth patterns
3. **Client Configuration** — customer-specific setups, per-tenant, sensitive
4. **Process/Procedural** — how to get things done (step-by-step know-how, currently in people's heads)
5. **Project/Delivery** — Jira, release notes, active work (transient)
6. **Learned/Cognitive** — AI-discovered gotchas, patterns, decisions (CF 3-tier memory)

### 3. Storage Architecture (DECIDED)

PostgreSQL + pgvector for all six knowledge types:

| Knowledge Type | Primary Storage | Retrieval |
|---|---|---|
| Product Domain | Docs table + pgvector embeddings | Vector similarity + BM25 hybrid |
| API/Integration Reference | Structured tables | Exact match + keyword |
| Client Configuration | Structured with RLS | Exact match, tenant-scoped |
| Process/Procedural | Docs + knowledge graph relations | HybridRAG (vector + graph walk) |
| Project/Delivery | Cached from external systems | Time-scoped, project-filtered |
| Learned/Cognitive | Knowledge table with tiers + embeddings | 3-tier retrieval, budget-capped |

**Work Context Container** = scoping/assembly mechanism in Augmentation Layer, not a storage type. Pulls slices from all six types based on active work context.

**Research validated:** PostgreSQL + pgvector is industry consensus for 2026. HybridRAG (vector + graph) improves factual correctness by ~8% over vector-only. CF's 3-tier cognitive memory is more sophisticated than any off-the-shelf option (Mem0, Zep, Letta). No dedicated graph DB or vector DB needed at our scale.

### 4. Retrieval Priority Order (DECIDED)

Token-budgeted, each level fires only if budget remaining:

1. Session facts (always, small, critical)
2. Work context container scope (narrows everything else)
3. Cognitive memory/learned (gotchas, patterns)
4. Knowledge graph relations (2-hop walk)
5. Product domain docs (vector similarity)
6. API/Integration reference (only if integration work)
7. Client config (only if specific client)
8. Project/Delivery (Jira/Confluence, lowest — most transient)

Hard cap on total tokens injected.

### 5. Ingestion Model (DECIDED)

1. **Product Domain** — bulk import from Confluence/SharePoint/codebase, release-event triggered
2. **API/Integration** — semi-automated from OData metadata/OpenAPI specs + manual from discovery
3. **Client Config** — manual at project setup, human-validated, tenant-scoped from entry
4. **Process/Procedural** — iterative capture through work (work IS the documentation), refined each iteration
5. **Project/Delivery** — live sync from Jira/Confluence via Integration Hub, cached not owned
6. **Learned/Cognitive** — auto-captured during work via remember() pattern, enters short-term, promotes through tiers

**Key insight from John:** Procedural knowledge forms through iterative work, not documentation events. Example: parallel pay run — round 1 was rough discovery, round 2 refined using round 1 as input. The process doc is a byproduct of doing the work. METIS must capture this naturally.

### 6. Decay, Promotion, and Freshness (DECIDED)

Three mechanisms:

**Cognitive Memory promotion/decay:**
- Short → Mid: during session if referenced/acted on (fix CF ordering bug)
- Mid → Long: after 3+ uses across different contexts
- Long → Archived: when contradicted or invalidated by change event

**Document freshness scoring:**
- Every doc gets score based on: last verified date, change events, retrieval feedback
- Stale docs deprioritised in retrieval, not deleted

**Event-driven staleness (NOT time-driven):**
- Product release flags affected Product Domain and API Reference docs
- Client config change flags that client's procedural knowledge
- Time alone does not cause decay

### 7. RBAC Scoping (PROPOSED — NOT CONFIRMED)

Proposal presented but session closed before John confirmed:

- **Tenant-level hard isolation:** Client Config + Learned/Cognitive tenant-scoped by default
- **Shared across tenants:** Product Domain, API/Integration Reference
- **Shared with tenant variants:** Process/Procedural
- **Tenant-scoped:** Project/Delivery
- **Roles:** Platform Builder (all tenants), Enterprise Admin (their tenant), Enterprise Staff (work-context scoped)

⚠️ **NEEDS CONFIRMATION** at start of next session.

---

## KEY DECISIONS THIS SESSION

| # | Decision | Status |
|---|---|---|
| 1 | CF audit: 10 patterns carry forward, dead weight + enterprise gaps identified | ✅ Confirmed |
| 2 | BPMN enterprise engine is Gate 2+ swap-out, not a blocker | ✅ Confirmed |
| 3 | 6 knowledge types taxonomy | ✅ Confirmed |
| 4 | PostgreSQL + pgvector for all types, no dedicated graph/vector DB | ✅ Confirmed |
| 5 | Work Context Container is Augmentation Layer scoping, not storage | ✅ Confirmed |
| 6 | 8-level retrieval priority order with token budget | ✅ Confirmed |
| 7 | Ingestion model for all 6 types | ✅ Confirmed |
| 8 | Procedural knowledge = iterative capture through work | ✅ Confirmed |
| 9 | 3-mechanism decay/promotion/freshness lifecycle | ✅ Confirmed |
| 10 | RBAC scoping model | ⚠️ PROPOSED, not confirmed |

---

## CF DEVELOPMENTS NOTED

- CF actively developing/testing a filing system for KMS + memory — work context containers. "I'm working on security" pulls related sessions, facts, memory files, KMS files. Directly relevant to METIS Augmentation Layer.
- CF actively addressing gaps identified in audit (hooks, consolidation bug, etc.)

---

## WHAT'S NEXT — PRIORITISED

### 1. Confirm RBAC scoping (quick — just needs John's yes/no)

### 2. Token budget design
Hard cap decided in principle but specific numbers not set. What's the budget? How does it flex based on constraint level (L1/L2/L3)?

### 3. Knowledge Engine data model
Translate the 6 knowledge types + storage architecture into actual PostgreSQL table designs. This is the Gate 1 Data Entity Map deliverable.

### 4. Retrieval quality metrics
How does METIS measure whether injected context actually helped? Implicit feedback (rephrasing, "that's wrong"), explicit feedback, A/B retrieval comparison.

### 5. Work Context Container design
Formalise how scoping works — how does the system know what you're working on, and how does it assemble the right context from all six types?

### 6. Still open from prior sessions
- MCP tool design (paused until knowledge system designed — may be ready now)
- Hand plan-of-attack-rewrite-brief.md to Claude Code
- Remaining Gate 1 docs (Process Inventory, Data Entity Map, Business Rules, Integration Points)
- Follow up on msg 67d8af18 (vault sync to claude-family)

---

## KEY FILES

| File | Status |
|---|---|
| `session-handoffs/2026-03-10-knowledge-engine-design.md` | NEW — this file |
| `session-handoffs/2026-03-09-interaction-model-mcp-review.md` | Previous handoff |
| `claude-family-systems-audit.md` | Reviewed this session |
| `claude-family-audit-*.md` (7 files) | All read and analysed |
| `security-architecture.md` | Unchanged |
| `gate-one/actor-map.md` | Unchanged |
| `gate-zero/` | All 5 docs complete |

---

## SESSION STARTER FOR NEXT CHAT

```
METIS Session Starter — Post Knowledge Engine Design
READ FIRST: `session-handoffs/2026-03-10-knowledge-engine-design.md`

CONTEXT: Knowledge Engine + Cognitive Memory design mostly complete.
6 knowledge types, storage architecture, retrieval priority, ingestion,
decay/promotion/freshness — all decided.

ACTION NEEDED: Confirm RBAC scoping (proposed but not confirmed last session).

PRIORITY: Token budget design + Knowledge Engine data model (→ Gate 1 Data Entity Map)

AFTER THAT:
1. Retrieval quality metrics design
2. Work Context Container formalisation
3. MCP tool design (knowledge system now designed — can resume)
4. Hand plan-of-attack-rewrite-brief.md to Claude Code
5. Remaining Gate 1 docs
6. Follow up on msg 67d8af18 (vault sync to claude-family)

KEY FILES:
* session-handoffs/2026-03-10-knowledge-engine-design.md
* claude-family-systems-audit.md (reviewed)
* claude-family-audit-*.md (7 files, all analysed)
* security-architecture.md (validated)
* system-product-definition.md (v0.3)
* gate-one/actor-map.md (validated)
* gate-zero/ — all 5 docs complete
```

---
*Session: 2026-03-10 | Status: Knowledge Engine + Cognitive Memory design complete (RBAC pending confirmation). Next: token budget + data model.*
