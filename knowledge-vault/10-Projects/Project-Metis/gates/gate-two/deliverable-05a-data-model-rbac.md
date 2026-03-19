---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/5a
  - type/data-model
  - domain/rbac
  - domain/audit
created: 2026-03-16
updated: 2026-03-16
status: draft
---

# Gate 2 Deliverable 5a: Data Model — RBAC & Audit

Extension of [[deliverable-05-data-model|Deliverable 5]]. Covers the 7 tables needed for Phase 0 authentication, authorization, and audit logging.

**Key decisions informing this model:**
- Separate DB per customer, no RLS (D7) — no tenant_id column needed
- Scoped role assignments — user can be Admin in Engagement A, Viewer in Engagement B
- Agent access ceiling — agents inherit human's permissions (security-architecture.md)
- Three-tier audit retention — permanent, 6-12 months, weeks
- Event-driven freshness — audit events update knowledge freshness scores (D11)
- Soft deletes on user-facing data (security-architecture.md)

---

## 6. RBAC Tables

### `users`

Per-customer-DB. A user within this customer's system.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| email | text UNIQUE NOT NULL | Primary identifier |
| display_name | text NOT NULL | |
| status | text NOT NULL | active, suspended, deactivated |
| auth_provider | text DEFAULT 'local' | local, saml, oidc (Phase 2+ pluggable) |
| auth_provider_id | text | External ID from SSO provider |
| password_hash | text | Nullable — not needed for SSO. Use argon2id. |
| last_login_at | timestamptz | |
| settings | jsonb | Preferences, notification config |
| is_deleted | boolean DEFAULT false | Soft delete |
| deleted_at | timestamptz | |
| created_at | timestamptz DEFAULT now() | |
| updated_at | timestamptz DEFAULT now() | |

### `roles`

Predefined system roles + custom roles.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text UNIQUE NOT NULL | e.g. platform_admin, consultant, viewer |
| display_name | text NOT NULL | Human-readable |
| description | text | |
| is_system | boolean DEFAULT false | System roles: cannot delete/modify |
| is_default | boolean DEFAULT false | Auto-assigned to new users |
| created_at | timestamptz DEFAULT now() | |
| updated_at | timestamptz DEFAULT now() | |

**Seed data:** platform_admin, enterprise_admin, ps_consultant, support_staff, developer, viewer (from Actor Map).

### `permissions`

Fine-grained resource + action pairs.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text UNIQUE NOT NULL | e.g. knowledge:read, workflow:execute |
| resource_type | text NOT NULL | knowledge, workflow, agent, session, connector, admin, audit |
| action | text NOT NULL | read, create, modify, delete, execute, approve, export |
| description | text | |
| category | text | A (project), B (event-driven), C (system) — from security arch |
| created_at | timestamptz DEFAULT now() | |

**Pattern:** Permission check = `resource_type:action`. Categories drive agent constraints (B = read/create only, C = read/status only).

### `role_permissions`

Join table: which permissions each role has.

| Column | Type | Notes |
|--------|------|-------|
| role_id | uuid FK → roles | |
| permission_id | uuid FK → permissions | |
| granted_at | timestamptz DEFAULT now() | |
| granted_by | uuid FK → users | Who configured this |

**PK:** (role_id, permission_id)

### `user_roles`

Scoped assignment — the core authorization table. Users get roles within specific scope levels.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users | |
| role_id | uuid FK → roles | |
| scope_org_id | uuid FK → organisations | Null = platform-wide |
| scope_product_id | uuid FK → products | Null = org-wide |
| scope_client_id | uuid FK → clients | Null = product-wide |
| scope_engagement_id | uuid FK → engagements | Null = client-wide |
| assigned_at | timestamptz DEFAULT now() | |
| assigned_by | uuid FK → users | |
| expires_at | timestamptz | Null = permanent assignment |
| is_active | boolean DEFAULT true | |

**UNIQUE:** (user_id, role_id, scope_org_id, scope_product_id, scope_client_id, scope_engagement_id)

**Authorization query pattern:**
```sql
SELECT DISTINCT p.name
FROM user_roles ur
JOIN role_permissions rp ON rp.role_id = ur.role_id
JOIN permissions p ON p.permission_id = rp.permission_id
WHERE ur.user_id = $1 AND ur.is_active = true
  AND (ur.expires_at IS NULL OR ur.expires_at > now())
  AND (ur.scope_org_id IS NULL OR ur.scope_org_id = $2)
  AND (ur.scope_product_id IS NULL OR ur.scope_product_id = $3)
  -- narrowest matching scope wins
```

### `api_keys`

Programmatic and service-to-service access.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users | Owner |
| name | text NOT NULL | Descriptive label |
| key_prefix | text NOT NULL | First 8 chars for identification (e.g. "mk_live_") |
| key_hash | text NOT NULL | argon2id hash of full key |
| scopes | text[] | Permission names — must be subset of user's permissions |
| scope_org_id | uuid FK → organisations | Scope ceiling |
| scope_product_id | uuid FK → products | |
| scope_client_id | uuid FK → clients | |
| scope_engagement_id | uuid FK → engagements | |
| last_used_at | timestamptz | |
| expires_at | timestamptz | Null = non-expiring |
| is_revoked | boolean DEFAULT false | |
| revoked_at | timestamptz | |
| created_at | timestamptz DEFAULT now() | |

**Key rotation:** Revoke old key + create new. No explicit rotation column needed.

---

## 7. Audit Log

### `audit_log`

Append-only. Range-partitioned by `created_at` (monthly). Never row-deleted — retention via partition dropping.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | |
| created_at | timestamptz NOT NULL | Partition key |
| retention_tier | smallint NOT NULL DEFAULT 2 | 1=permanent, 2=medium (6-12mo), 3=short (weeks) |
| actor_id | uuid NOT NULL | User or agent ID |
| actor_type | text NOT NULL | user, agent, system |
| session_id | uuid | FK → sessions (Phase 1) |
| action | text NOT NULL | create, read, modify, delete, approve, login, logout, export, spawn_agent |
| resource_type | text NOT NULL | knowledge_item, workflow, user, role, connector, session, agent, api_key, engagement |
| resource_id | uuid | Null for non-targeted actions (login, logout) |
| before_state | jsonb | Null for creates and reads |
| after_state | jsonb | Null for reads and deletes |
| change_summary | text | Human-readable diff summary |
| ip_address | inet | |
| user_agent | text | |
| metadata | jsonb | request_id, correlation_id, agent_chain, etc. |

**PK:** (id, created_at) — required for partitioning

**Partitioning:**
```sql
CREATE TABLE audit_log (...) PARTITION BY RANGE (created_at);
-- Create monthly: audit_log_2026_04, audit_log_2026_05, etc.
-- Pre-create 3 months ahead. Scheduled job creates future + drops expired.
```

**Indexes (per partition):**
- `(resource_type, resource_id, created_at)` — "what happened to this entity?"
- `(actor_id, created_at)` — "what did this actor do?"
- `(action, created_at)` — "all deletes this month"

**Retention job:** Monthly. For each partition older than threshold: if retention_tier 3 → drop after 4 weeks; tier 2 → drop after 12 months; tier 1 → never drop.

**Freshness integration (D11):**
Application layer: on INSERT where `action IN ('create','modify') AND resource_type = 'knowledge_item'`, update `knowledge_items.freshness_score` and `last_freshness_event`. Trigger or application code — decided at implementation.

**Retention tier assignment:**
| Action | Tier | Rationale |
|--------|------|-----------|
| login, logout, modify, delete, approve | 1 (permanent) | Security events |
| create, spawn_agent, export | 2 (6-12 months) | Operational context |
| read | 3 (weeks) | High volume, low retention value |

---

## Cross-References

| This table | References | Via |
|------------|------------|-----|
| users | → workflow_instances.triggered_by | When type='user' |
| users | → activity_access_log.accessed_by | Direct FK |
| users | → customer_retention_config.modified_by | Direct FK |
| user_roles | → organisations, products, clients, engagements | Scope chain FKs |
| api_keys | → organisations, products, clients, engagements | Scope ceiling FKs |
| audit_log | → knowledge_items (freshness) | Application-layer trigger |
| audit_log | → sessions (Phase 1) | Forward FK, nullable until sessions exist |

---

**Version**: 1.0
**Created**: 2026-03-16
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-05a-data-model-rbac.md
