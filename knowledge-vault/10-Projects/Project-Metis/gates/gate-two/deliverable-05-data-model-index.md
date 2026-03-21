---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/5-index
  - type/data-model
  - type/index
created: 2026-03-17
updated: 2026-03-17
status: draft
---

# Gate 2 Deliverable 5: Data Model — Master Index

Complete METIS database schema: **34 tables** across 4 documents. Each customer gets a separate database (D7).

## Documents

| Doc | Tables | Domain | Phase |
|-----|--------|--------|-------|
| [[deliverable-05-data-model]] | 13 | Scope hierarchy, knowledge, workflows, activities, retention | 0+1 |
| [[deliverable-05a-data-model-rbac]] | 7 | Users, roles, permissions, audit log | 0 |
| [[deliverable-05b-data-model-platform]] | 11 | Sessions, agents, LLM calls, token budgets, cognitive memory, code intelligence | 1 |
| [[deliverable-05c-data-model-integration]] | 3 | Connectors, sync history | 1 |

---

## All 32 Tables by Domain

### Tenant Core (4 tables — Doc 05)
`organisations` → `products` → `clients` → `engagements`

### Knowledge Store (3 tables — Doc 05)
`knowledge_items`, `knowledge_chunks` (vector), `knowledge_categories`

### Workflows (2 tables — Doc 05)
`workflow_instances`, `workflow_step_log`

### Activities (2 tables — Doc 05)
`activities`, `activity_access_log`

### Retention (2 tables — Doc 05)
`retention_tiers`, `customer_retention_config`

### RBAC (6 tables — Doc 05a)
`users`, `roles`, `permissions`, `role_permissions`, `user_roles` (scoped), `api_keys`

### Audit (1 table — Doc 05a)
`audit_log` (partitioned monthly, 3-tier retention)

### Sessions (3 tables — Doc 05b)
`sessions`, `session_messages`, `session_context_snapshots`

### Agent Orchestration (2 tables — Doc 05b)
`agents`, `agent_instances` (self-referencing tree)

### LLM Tracking (1 table — Doc 05b)
`llm_calls`

### Token Budgets (2 tables — Doc 05b)
`token_budgets`, `token_budget_alerts`

### Cognitive Memory (1 table — Doc 05b)
`cognitive_memory` (vector, promotion path)

### Code Intelligence (2 tables — Doc 05b)
`code_symbols` (vector, self-referencing), `code_references` (directional edges)

### Integration Hub (3 tables — Doc 05c)
`connectors`, `connector_instances`, `connector_sync_log`

---

## Relationship Map (ERD Summary)

```
TENANT CORE (scope chain — FK'd by nearly everything)
  organisations ──→ products ──→ clients ──→ engagements
       │                │            │            │
       └── denormalised scope IDs on all scoped tables ──┘

IDENTITY & ACCESS
  users ←── user_roles ──→ roles ←── role_permissions ──→ permissions
    │
    ├── api_keys (scoped ceiling)
    ├── sessions.user_id
    ├── agent_instances.spawned_by
    └── audit_log.actor_id

KNOWLEDGE PIPELINE
  connectors ──→ connector_instances ──→ connector_sync_log
                        │                       │
                        └── creates ──→ knowledge_items ──→ knowledge_chunks
                                              │                    │
                                              │              embedding (vector)
                                              │
                                        knowledge_categories

SESSION & AI
  sessions ──→ session_messages
     │     ──→ session_context_snapshots (refs knowledge_items)
     │
     ├── agent_instances ──→ agent_instances (sub-agents, self-ref)
     │         │
     │         └── llm_calls
     │
     ├── cognitive_memory ──→ knowledge_items (promotion)
     │         │
     │         └── embedding (vector, same dim as knowledge_chunks)
     │
     └── audit_log.session_id

CODE INTELLIGENCE
  code_symbols ──→ code_symbols (parent hierarchy, self-ref)
       │                │
       │           embedding (vector, same dim as knowledge_chunks)
       │
       └── code_references (from_symbol ──→ to_symbol)

WORKFLOW ENGINE
  workflow_instances ──→ workflow_step_log

ACTIVITY TRACKING
  activities ──→ activity_access_log ──→ knowledge_items (co-access signal)

BUDGETS & ALERTS
  token_budgets ──→ token_budget_alerts
       │
       └── incremented by llm_calls (application layer)

AUDIT (cross-cutting)
  audit_log ── references any entity via (resource_type, resource_id)
     │
     └── freshness events ──→ knowledge_items.freshness_score (D11)
```

---

## Cross-Cutting Patterns

| Pattern | Applied To | Reference |
|---------|-----------|-----------|
| Scope chain denormalisation | All scoped tables | Decision C2-2 |
| Hybrid columns (dedicated + JSONB) | All tables with `settings`/`config`/`metadata` | Decision C2-1 |
| Soft delete (`is_deleted`/`deleted_at`) | users, knowledge_items | Security arch |
| Supersession (self-ref) | cognitive_memory | Errata pattern |
| Actor polymorphism (`actor_id` + `actor_type`) | audit_log, workflow_step_log | — |
| Vector embeddings (HNSW index) | knowledge_chunks, cognitive_memory, code_symbols | Decision D9 |
| Self-referencing hierarchy | code_symbols (parent_symbol_id) | Code symbol nesting |
| Incremental indexing (file hash) | code_symbols | Skip unchanged files |
| Append-only + time partitioning | audit_log, workflow_step_log, connector_sync_log | — |
| Encrypted at rest | connector_instances.credentials_encrypted | Security arch |

## Indexes Summary

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| knowledge_chunks | embedding | HNSW | Vector similarity search |
| cognitive_memory | embedding | HNSW | Semantic recall |
| audit_log | (resource_type, resource_id, created_at) | btree | Entity history |
| audit_log | (actor_id, created_at) | btree | Actor history |
| llm_calls | (session_id, created_at) | btree | Session replay |
| llm_calls | (model_id, created_at) | btree | Cost analysis |
| session_messages | (session_id, message_index) | btree UNIQUE | Message ordering |
| code_symbols | embedding | HNSW | Semantic code search |
| code_symbols | (project_name, name) | btree | Symbol lookup |
| code_symbols | (file_path) | btree | File contents |
| code_symbols | (parent_symbol_id) | btree | Symbol hierarchy |
| code_references | (from_symbol_id) | btree | Outgoing refs |
| code_references | (to_symbol_id) | btree | Incoming refs |

## Apache AGE (Graph Layer)

PG18 + Apache AGE for knowledge graph queries. Not separate tables — AGE manages its own storage. Graph models:
- **Knowledge graph:** knowledge_item vertices, relationship edges (relates_to, depends_on, contradicts)
- **Activity graph:** activity → knowledge co-access patterns
- **Agent tree:** alternative to recursive CTE for agent_instances hierarchy

**NOT used for code symbol graphs.** Code references use flat tables (`code_symbols` + `code_references`) with recursive CTEs instead. Reasons: AGE has backup issues (OID-encoded graphids break on pg_dump), worse performance for sparse call graphs (1.5-3.7ms vs 0.8ms), uncertain maintenance (core dev team dismissed Oct 2024), and no AWS RDS support (violates D6 platform-agnostic). See [[coding-intelligence-design|Coding Intelligence Design]] for full analysis.

Graph schema defined at implementation time (Gate 3), not in this data model.

---

**Version**: 1.1
**Created**: 2026-03-17
**Updated**: 2026-03-22
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-05-data-model-index.md
