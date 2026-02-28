---
tags:
  - project/Project-Metis
  - scope/system
  - area/integration-hub
  - type/design
created: 2026-02-25
updated: 2026-02-26
---

# Integration Hub: Standardised Connector Interface

Agreed Feb 25 (GAP-2 resolution). Written to vault Feb 26.

## Core Interface

Every connector implements these 8 methods:

| Method | Purpose | Required |
|--------|---------|----------|
| `connect(config)` | Establish connection, authenticate | Yes |
| `health_check()` | Verify connectivity and auth status | Yes |
| `read(entity, filters, options)` | Retrieve data from external system | Yes |
| `write(entity, data, options)` | Push data to external system | Yes |
| `batch_read(entity, filters, options)` | Bulk retrieve with pagination | Yes |
| `batch_write(entity, data_list, options)` | Bulk push with error handling per item | Yes |
| `get_schema()` | Return available entities, fields, types | Yes |
| `disconnect()` | Clean up connections, release resources | Yes |

## Standard Middleware Stack

Every connector gets these middleware layers automatically:

| Middleware | What It Does |
|-----------|-------------|
| **Retry** | Exponential backoff with jitter. Configurable max retries. |
| **Rate Limiter** | Respects external API rate limits. Queues when approaching. |
| **Circuit Breaker** | Opens after N consecutive failures. Half-open test after timeout. |
| **Credential Manager** | Handles token refresh, rotation. Encrypted at rest. |
| **Audit Logger** | Logs every read/write with timestamp, user, entity, result. |
| **Health Monitor** | Regular connectivity checks. Alerts on failures. |

## Configuration

`connector_configs` table stores per-organisation configuration:

| Field | Type | Purpose |
|-------|------|---------|
| id | UUID | Primary key |
| organisation_id | UUID FK | Which org this config belongs to |
| connector_type | enum | time2work_rest, time2work_odata, jira, confluence, etc. |
| base_url | text | API base URL |
| auth_config | jsonb (encrypted) | Auth type, credentials, token endpoints |
| rate_limits | jsonb | Requests per minute/hour, burst limits |
| field_mappings | jsonb | Map external field names to internal schema |
| custom_config | jsonb | Connector-specific settings |
| is_active | boolean | Enable/disable without deleting |
| created_at | timestamp | — |
| updated_at | timestamp | — |

## Key Principles

- **Business logic NEVER calls external APIs directly.** Always through connectors.
- **Connectors are dumb pipes.** They handle connection, auth, transport. Business logic handles meaning.
- **Sync logic is a separate service** that uses connectors. Connectors don't know about sync.
- **Mockable.** Every connector interface can be mocked for testing without external dependencies.
- **Hot-swappable.** Connector configs can be updated without restart.

## First Connector: time2work REST

Priority: Phase 1. Implements all 8 methods against time2work REST API.

Auth: OAuth2 / API key (depending on what nimbus provides).
Entities: employees, timesheets, rosters, pay rules, awards, etc.
Rate limits: TBD based on nimbus API documentation.

---
*Design agreed: 2026-02-25 | Written to vault: 2026-02-26*
