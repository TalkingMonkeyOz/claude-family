---
projects:
- project-metis
- claude-family
tags:
- research
- data-model
- schema
synced: false
---

# Schema Detail: `claude.session_facts`

Back to [[schema-index]]

**Row count (audit 2026-02-28)**: 394
**Purpose**: Session-scoped notepad — the SHORT tier in the 3-tier cognitive memory model. Stores credentials, configurations, endpoints, decisions, and notes that need to survive context compaction within a session. UPSERT on `(session_id, fact_key)` ensures each key has exactly one value per session.

---

## Columns

| # | Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `fact_id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| 2 | `session_id` | `uuid` | YES | NULL | FK to sessions (nullable for orphaned facts) |
| 3 | `project_name` | `varchar` | YES | NULL | Project scope (fallback when session_id unavailable) |
| 4 | `fact_type` | `varchar` | NO | — | Enum — see below |
| 5 | `fact_key` | `varchar` | NO | — | Unique key within session (~50 chars max in practice) |
| 6 | `fact_value` | `text` | NO | — | The stored value |
| 7 | `is_sensitive` | `boolean` | YES | `false` | If true, value hidden in `list_session_facts()` |
| 8 | `created_at` | `timestamptz` | YES | `NOW()` | Creation time (updated on UPSERT) |

**Unique constraint**: `(session_id, fact_key)` — exactly one value per key per session.

Source: INSERT in `server.py` lines 2369–2380 (`tool_store_session_fact`).

---

## fact_type Enum

| Value | Description | Sensitivity | Priority in Retrieval |
| --- | --- | --- | --- |
| `credential` | API keys, passwords | Always `is_sensitive=true` | 7 (last) |
| `config` | Configuration values | Sometimes | 4 |
| `endpoint` | URLs, connection strings | Rarely | 5 |
| `decision` | Decisions made during work | No | 1 (highest) |
| `note` | General notes (default) | No | 3 |
| `data` | Data reference values | No | 6 |
| `reference` | Reference identifiers | No | 2 |

---

## Retrieval Priority in `recall_memories()`

Facts are returned in priority order within the short-tier budget (default 20% of total budget):

```sql
ORDER BY CASE fact_type
    WHEN 'decision'   THEN 1
    WHEN 'reference'  THEN 2
    WHEN 'note'       THEN 3
    WHEN 'config'     THEN 4
    WHEN 'endpoint'   THEN 5
    WHEN 'data'       THEN 6
    ELSE                   7
END, created_at DESC
LIMIT 20
```

Sensitive facts (`is_sensitive=true`) are excluded from `recall_memories()` results — they require explicit `recall_session_fact()` calls.

---

## Indexes

| Index | Type | Columns | Purpose |
| --- | --- | --- | --- |
| `session_facts_pkey` | btree (PK) | `fact_id` | PK |
| `session_facts_session_key_uq` | btree (Unique) | `(session_id, fact_key)` | UPSERT dedup |
| `idx_sf_session_id` | btree | `session_id` | Session-scoped queries |
| `idx_sf_project_name` | btree | `project_name` | Project-scoped fallback queries |
| `idx_sf_fact_type` | btree | `fact_type` | Type filtering |

---

## Foreign Keys

| Column | References | On Delete |
| --- | --- | --- |
| `session_id` | `claude.sessions.session_id` | SET NULL |

Nullable FK — allows facts to remain when the session record is closed.

---

## Integration Points

| System | Role |
| --- | --- |
| `store_session_fact()` MCP tool | Primary writer |
| `remember()` short-path | Delegates here for credential/config/endpoint types |
| `recall_memories()` short budget | Primary reader (20% of budget by default) |
| `recall_session_fact()` | Point lookup by key |
| `list_session_facts()` | All facts for current session (hides sensitive) |
| `recall_previous_session_facts()` | Scans last N sessions (default 3) |
| PreCompact hook | Important facts injected before context compaction |
| `start_session()` | Recent decisions surfaced in session context |
| WCC assembly | 10% of WCC context budget allocated here |

---

## Cross-Session Recovery Limitation

`recall_previous_session_facts()` scans back exactly N sessions (default 3) for the project. If more than 3 sessions have occurred since a fact was stored, it becomes unreachable. This is a known limitation flagged in MEMORY.md.

---

## METIS Assessment Notes

**Strength**: The upsert-on-(session_id, fact_key) pattern is robust. Repeated writes to the same key are safe and idempotent.

**Gap**: No embedding or semantic search on session_facts. Facts must be retrieved by exact key or by full scan. A user asking "what API key did I store?" must know the fact_key or scan all facts.

**Gap**: `is_sensitive=true` facts are permanently excluded from recall_memories() which means credentials stored during a session cannot be auto-surfaced in context — they require explicit lookup. This is the correct security behavior but may frustrate users expecting automatic context restoration.

**Gap**: Cross-session recovery depends on session count not time. A project with many short sessions will lose facts faster than a project with fewer long sessions.

---

## Source Code References

- `mcp-servers/project-tools/server.py` lines 2347–2395 (`tool_store_session_fact`)
- `mcp-servers/project-tools/server.py` lines 1583–1628 (short-tier read in `tool_recall_memories`)
- `mcp-servers/project-tools/server.py` lines 1807–1848 (short-path routing in `tool_remember`)

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-session-facts.md
