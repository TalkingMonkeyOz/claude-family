---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/5
  - type/data-model
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 5: Data Model

## Overview

Physical data model for METIS. Each customer gets a separate database (Decision #7). Tables below exist per-tenant. No DDL yet — this captures schema design; Gate 3 produces migration scripts.

**Key decisions informing this model:**
- Separate DB per customer, no RLS (Decision #7)
- Hybrid columns: dedicated for queries + JSONB for config (C2-1)
- Scope tag inheritance chain: full path always populated (C2-2)
- Event-driven freshness, not time-based decay (Decision #11)
- Content-aware chunking per content type (Decision #8)

---

## 1. Scope Hierarchy (Tenant Core)

### `organisations`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text NOT NULL | |
| slug | text UNIQUE | URL-safe identifier |
| settings | jsonb | Feature flags, preferences |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `products`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| org_id | uuid FK → organisations | |
| name | text NOT NULL | e.g. "Nimbus" |
| slug | text UNIQUE | |
| product_type | text | erp, hr, reporting, etc. |
| settings | jsonb | Product-specific config |
| created_at / updated_at | timestamptz | |

### `clients`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| product_id | uuid FK → products | |
| org_id | uuid FK → organisations | Denormalised for scope queries |
| name | text NOT NULL | e.g. "Monash University" |
| slug | text UNIQUE | |
| settings | jsonb | |
| created_at / updated_at | timestamptz | |

### `engagements`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| client_id | uuid FK → clients | |
| product_id | uuid FK → products | Denormalised |
| org_id | uuid FK → organisations | Denormalised |
| name | text NOT NULL | |
| status | text | active, paused, completed |
| settings | jsonb | Scope guardrail policy, retention overrides |
| started_at | timestamptz | |
| completed_at | timestamptz | Nullable |
| created_at / updated_at | timestamptz | |

**Pattern:** Every child denormalises parent IDs for single-query scope filtering (C2-2).

---

## 2. Knowledge Store

### `knowledge_items`

Core table — all ingested and learned knowledge. See [[data-model/data-model-table-assessments|Table Assessments]] for design rationale.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| scope_org_id | uuid FK | Always set |
| scope_product_id | uuid FK | Nullable — org-wide knowledge |
| scope_client_id | uuid FK | Nullable |
| scope_engagement_id | uuid FK | Nullable |
| knowledge_type | text | product_domain, api_reference, client_config, learned_cognitive, process_procedural, tooling_integration |
| title | text | |
| content | text | Full content |
| content_type | text | markdown, code, table, prose, mixed |
| source_type | text | ingested, learned, promoted, manual |
| source_ref | text | Connector ID, URL, file path |
| status | text | draft, active, archived, superseded |
| confidence | float | 0-1 |
| freshness_score | float | Event-driven, not time-decay |
| last_freshness_event | timestamptz | When source last confirmed current |
| token_count | int | Estimated tokens for budget management |
| metadata | jsonb | Extensible — tags, version, author |
| is_deleted | boolean DEFAULT false | Soft delete |
| created_at / updated_at | timestamptz | |

### `knowledge_chunks`

Chunked and embedded for retrieval. One knowledge_item → many chunks.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| knowledge_item_id | uuid FK | |
| chunk_index | int | Order within item |
| content | text | Chunk text |
| content_type | text | Inherited — drives chunking strategy |
| embedding | vector(1024) | Voyage AI (pluggable dimension) |
| token_count | int | For budget management |
| created_at | timestamptz | |

**Index:** HNSW on embedding column for vector similarity search.

### `knowledge_categories`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text | |
| parent_id | uuid FK self | Hierarchical categories |
| scope_product_id | uuid FK | Category per product |
| description | text | |
| created_at / updated_at | timestamptz | |

---

## 3. Workflow Tables

See [[gate-two/decisions-cluster2#C2-4|Cluster 2 Decision 4]] for full design rationale.

### `workflow_instances`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| workflow_definition_id | text | BPMN process reference |
| scope_org/product/client/engagement_id | uuid FK | Full chain |
| triggered_by | uuid | User or agent ID |
| triggered_by_type | text | user, agent |
| current_step | text | Denormalised from engine |
| status | text | pending/active/paused/completed/failed/cancelled |
| context_data | jsonb | Input/output payload |
| error_info | text | Nullable |
| started_at / completed_at / updated_at | timestamptz | |

### `workflow_step_log`

Append-only. Partitionable by time.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| instance_id | uuid FK → workflow_instances | |
| step_name | text | |
| step_type | text | task, gateway, event |
| status | text | started/completed/failed/skipped |
| actor_id | uuid | |
| actor_type | text | user, agent, system |
| started_at / completed_at | timestamptz | |
| output_data | jsonb | |

---

## 4. Activity & Session Tables

### `activities`

See [[gate-two/decisions-summary|C2-3]] — activity space entity.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| scope_engagement_id | uuid FK | |
| name | text | |
| aliases | text[] | Authority control |
| activity_type | text | |
| status | text | active/paused/completed/archived |
| metadata | jsonb | |
| created_at / updated_at | timestamptz | |

### `activity_access_log`

Separate table for co-access signal (C2-3).

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| activity_id | uuid FK | |
| knowledge_item_id | uuid FK | |
| accessed_by | uuid | |
| accessed_at | timestamptz | |
| access_type | text | view, cite, edit |

---

## 5. Retention & Config Tables

### `retention_tiers`

System-level. See [[gate-two/decisions-cluster2#C2-5|Cluster 2 Decision 5]].

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text | standard/extended/permanent/minimal |
| category | text | knowledge/workflow_logs/sessions/etc. |
| retain_days | int | Null = permanent |
| is_default | boolean | |

### `customer_retention_config`

Per-tenant overrides within bounds.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| category | text | |
| tier_id | uuid FK → retention_tiers | |
| custom_retain_days | int | Override within floor/ceiling |
| floor_days | int | Set by us, immutable |
| ceiling_days | int | Nullable = no ceiling |
| modified_by | uuid FK | |
| modified_at | timestamptz | |

---

## 6. What's NOT in This Model (Gate 3)

- Users / roles / permissions tables (RBAC engine)
- Connector configurations (Integration Hub)
- Audit log tables (structure decided, tables not specified)
- Session management tables
- Agent registry / agent state
- LLM call log tables
- Token budget tracking tables
- Scratchpad / working memory tables

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-05-data-model.md
