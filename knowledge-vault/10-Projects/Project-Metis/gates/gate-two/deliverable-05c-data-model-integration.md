---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/5c
  - type/data-model
  - domain/integration
  - domain/connectors
created: 2026-03-17
updated: 2026-03-17
status: draft
---

# Gate 2 Deliverable 5c: Data Model — Integration Hub

Extension of [[deliverable-05-data-model|Deliverable 5]]. Covers 3 tables for the Integration Hub (F120): connector definitions, configured instances, and sync history.

**Key decisions informing this model:**
- Platform-agnostic infrastructure (D6) — connectors are pluggable, not hard-coded
- Event-driven freshness (D11) — connector syncs are freshness events
- Credential encryption at rest (security-architecture.md)
- Separate DB per customer (D7) — connector instances are per-tenant

---

## 13. Integration Hub

### `connectors`

Connector type definitions — what external systems METIS can integrate with.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text UNIQUE NOT NULL | e.g. jira_cloud, confluence_cloud, git_repo, file_drop |
| connector_type | text NOT NULL | issue_tracker, wiki, scm, file_system, api, erp |
| description | text | |
| version | text | Connector code version |
| config_schema | jsonb | JSON Schema for required config fields |
| capabilities | jsonb | read, write, webhook, full_sync, incremental_sync |
| auth_methods | text[] | api_key, oauth2, basic, certificate, token |
| status | text NOT NULL | active, beta, deprecated, disabled |
| created_at / updated_at | timestamptz | |

**Pattern:** `config_schema` validates `connector_instances.config` at application layer.

### `connector_instances`

Configured connector for a specific scope. One connector type → many instances.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| connector_id | uuid FK → connectors | Which type |
| scope_org_id | uuid FK → organisations | |
| scope_product_id | uuid FK → products | Nullable — org-wide connector |
| name | text NOT NULL | e.g. "Monash Jira", "Nimbus Confluence" |
| config | jsonb NOT NULL | Endpoint URL, project key, filters, etc. |
| credentials_encrypted | bytea | AES-256-GCM encrypted at rest |
| credentials_key_ref | text | Reference to key in vault/KMS |
| sync_schedule | text | Cron expression; null = manual only |
| last_sync_at | timestamptz | |
| last_sync_status | text | success, partial, error, never |
| is_active | boolean DEFAULT true | |
| created_at / updated_at | timestamptz | |

**Security:** Credentials never stored as plaintext. `credentials_key_ref` points to encryption key — supports key rotation without re-encrypting all instances.

### `connector_sync_log`

Sync operation history. Append-only.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| instance_id | uuid FK → connector_instances | |
| sync_type | text NOT NULL | full, incremental, webhook, manual |
| status | text NOT NULL | started, in_progress, completed, partial, error |
| items_discovered | int DEFAULT 0 | Items found in source |
| items_created | int DEFAULT 0 | New knowledge_items created |
| items_updated | int DEFAULT 0 | Existing items refreshed |
| items_skipped | int DEFAULT 0 | Unchanged or filtered |
| items_errored | int DEFAULT 0 | |
| error_details | jsonb | Per-item errors |
| started_at | timestamptz DEFAULT now() | |
| completed_at | timestamptz | |
| metadata | jsonb | Sync cursor/checkpoint for incremental |

**Freshness integration (D11):** `items_updated > 0` triggers freshness events on corresponding `knowledge_items` via audit_log. The chain: connector_sync_log → audit_log INSERT → knowledge_items.freshness_score update.

**Knowledge linkage:** Synced items become `knowledge_items` with `source_type = 'ingested'` and `source_ref` = connector_instance_id + source-system ID.

---

## Cross-References

| This table | References | Via |
|------------|------------|-----|
| connector_instances | → connectors | connector_id FK |
| connector_instances | → organisations, products (05) | Scope FKs |
| connector_sync_log | → connector_instances | instance_id FK |
| (application layer) | → knowledge_items (05) | source_ref linkage |
| (application layer) | → audit_log (05a) | Freshness events |

---

**Version**: 1.0
**Created**: 2026-03-17
**Updated**: 2026-03-17
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-05c-data-model-integration.md
