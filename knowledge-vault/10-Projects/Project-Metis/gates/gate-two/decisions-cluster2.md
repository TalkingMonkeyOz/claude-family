---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - scope/data-model
created: 2026-03-15
updated: 2026-03-15
---

# Cluster 2: Data Model Decisions (Detail)

Parent: [[gate-two/decisions-summary|Gate 2 Decisions Summary]]

## C2-4: workflow_instances Schema

**Decision:** Rich record pattern with separate step log table.

**workflow_instances** — queryable state:
- `id`, `workflow_definition_id` (FK to BPMN process)
- Scope chain: `scope_org_id`, `scope_product_id`, `scope_client_id`, `scope_engagement_id`
- `triggered_by`, `triggered_by_type` (user or agent)
- `current_step` (denormalized from engine)
- `status` (pending / active / paused / completed / failed / cancelled)
- `context_data` (JSONB — input/output payload)
- `error_info`
- `started_at`, `completed_at`, `updated_at`

**workflow_step_log** — append-only history:
- `id`, `instance_id` (FK)
- `step_name`, `step_type`, `status`
- `actor_id`, `actor_type`
- `started_at`, `completed_at`
- `output_data` (JSONB)

**Write-through pattern:** Engine step completion triggers callback → updates our table. Engine owns execution internals, our table owns queryable state.

**Why rich record:** Enables engine swap-out (SpiffWorkflow is swappable), cross-scope queries without N engine calls, crash recovery (DB knows what should be running), cheap context assembly lookups.

**Why separate step log:** Append-only high-volume writes, partitionable by time, matches activity_access_log pattern (C2-3), serves audit requirements.

---

## C2-5: Data Retention Policies

**Decision:** Tiered presets with RBAC-controlled customer override.

### Model

**retention_tiers** (system-level, we control):
- `id`, `name` (standard/extended/permanent/minimal)
- `category` (knowledge/workflow_logs/sessions/agent_logs/embeddings)
- `retain_days` (null = permanent), `is_default`

**customer_retention_config** (per tenant DB):
- `id`, `category`, `tier_id`, `custom_retain_days`
- `floor_days` (set by us, immutable by customer)
- `ceiling_days` (set by us, nullable)
- `modified_by`, `modified_at`

### Default Retention

| Category | Default | Floor | Ceiling |
|----------|---------|-------|---------|
| Knowledge items | Permanent | 1 year | — |
| Workflow step logs | 3 years | 2 years | — |
| Session/activity data | 1 year | 90 days | — |
| Agent interaction logs | 90 days | 30 days | — |
| Embeddings | Match source | 0 (regenerable) | — |

### Access Control

- RBAC permission `retention.manage` controls who can modify
- Customer admins can extend OR shorten within floor/ceiling range
- Without permission, config page is read-only

### Enforcement

- Scheduled soft-delete job (or event-driven per Decision #11)
- Hard purge is separate, delayed process — recovery window
- Aligns with log retention (C6-4) using same framework

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/decisions-cluster2.md
