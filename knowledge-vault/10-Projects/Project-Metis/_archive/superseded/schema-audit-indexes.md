---
projects:
- claude-family
- Project-Metis
tags:
- schema-audit
- data-model
- metis
synced: false
---

# Schema Audit: Indexes, Sizes, Spot Checks, Recommendations

**Parent index**: `docs/metis-data-model-research-full-schema.md`
**Basis**: Static codebase analysis. Row counts from 2026-02-28 snapshot.

---

## 6. Index Analysis

### Top 30 most-used indexes

SQL: `SELECT indexrelname, relname as table_name, idx_scan, idx_tup_read, idx_tup_fetch FROM pg_stat_user_indexes WHERE schemaname='claude' ORDER BY idx_scan DESC LIMIT 30;`

Expected top users based on access patterns:

| expected_indexrelname | rationale |
|-----------------------|-----------|
| `sessions_pkey` | Every hook query joins to sessions |
| `todos_pkey` | todo_sync_hook queries by id |
| `vault_embeddings` HNSW index | Every RAG query calls ivfflat/hnsw vector search |
| `knowledge_*` indexes | recall_memories() called every session start |
| `session_facts_*` indexes | store/recall called every session |
| `features_pkey`, `build_tasks_pkey` | WorkflowEngine transition lookups |
| `bpmn_processes_pkey` | bpmn-engine MCP on every search call |

### Unused indexes (idx_scan = 0)

SQL: `SELECT indexrelname, relname as table_name, idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) as index_size FROM pg_stat_user_indexes WHERE schemaname='claude' AND idx_scan = 0 ORDER BY relname, indexrelname;`

Expected unused candidates:

| likely_unused | reason |
|---------------|--------|
| All indexes on `workflow_state` | Table is empty, never queried |
| All indexes on `process_data_map` | Table is empty, never queried |
| All indexes on `rag_query_patterns` | Table is empty, never queried |
| All indexes on `instructions_versions` / `rules_versions` / `skills_versions` | Tables empty |
| Non-PK indexes on `books` | Only 3 rows — seq scan always faster |
| Non-PK indexes on `compliance_audits` | Only 1 row — seq scan always faster |

Any index on an empty table wastes storage and maintenance overhead with zero query benefit.

### Index sizes (all indexes, by size)

SQL: `SELECT indexrelname, relname as table_name, pg_size_pretty(pg_relation_size(indexrelid)) as index_size, idx_scan FROM pg_stat_user_indexes WHERE schemaname='claude' ORDER BY pg_relation_size(indexrelid) DESC;`

Expected largest indexes:

| rationale | expected_size |
|-----------|---------------|
| `vault_embeddings` HNSW index (9,655 × 1024 float32) | 50-100 MB |
| `document_projects` embedding indexes | 10-30 MB |
| `documents` text indexes | 5-20 MB |
| `knowledge` embedding indexes | 5-15 MB |
| `todos` indexes (2,711 rows, high churn) | 1-5 MB |

---

## 7. Table Size Analysis

SQL: `SELECT relname, pg_size_pretty(pg_total_relation_size(c.oid)) as total_size, pg_size_pretty(pg_relation_size(c.oid)) as table_size, pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) as index_size FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'claude' AND c.relkind = 'r' ORDER BY pg_total_relation_size(c.oid) DESC;`

Expected top storage consumers:

| table_name | rationale |
|------------|-----------|
| `vault_embeddings` | 9,655 rows × 1024 float dims; HNSW index adds 2-3x table size |
| `document_projects` | 6,515 rows, many with embedding refs |
| `mcp_usage` | 6,965 rows of synthetic data — wasted space |
| `documents` | 5,940 rows with text content |
| `rag_usage_log` | 2,287 rows with query strings |
| `todos` | 2,711 rows, high churn creates dead tuples |

---

## 8. Key Table Spot Checks

### Live query SQL

Run `scripts/run_schema_audit.py` for actual output. Key queries:

```sql
-- Projects by client domain
SELECT project_id, name, client_domain, status, project_type FROM claude.projects ORDER BY client_domain, name;

-- Feature status breakdown
SELECT status, count(*) FROM claude.features GROUP BY status ORDER BY count DESC;

-- Build task status breakdown
SELECT status, count(*) FROM claude.build_tasks GROUP BY status ORDER BY count DESC;

-- Knowledge tier distribution
SELECT tier, memory_type, count(*), AVG(confidence) FROM claude.knowledge GROUP BY tier, memory_type ORDER BY tier;

-- Active MCP tools (last 30 days)
SELECT tool_name, count(*) FROM claude.mcp_usage WHERE used_at > NOW()-INTERVAL '30 days' GROUP BY tool_name ORDER BY count DESC LIMIT 20;

-- Recent sessions
SELECT session_id, project_name, started_at, ended_at IS NOT NULL as closed FROM claude.sessions ORDER BY started_at DESC LIMIT 10;

-- Pending messages (watch for >10)
SELECT status, message_type, count(*) FROM claude.messages GROUP BY status, message_type ORDER BY count DESC;
```

### Documented spot check findings

| table | finding |
|-------|---------|
| `sessions` | ~52 permanently unclosed (ended_at IS NULL, older than 24h) |
| `mcp_usage` | 6,965 rows all verified synthetic (NULL session_id per monitoring doc 2025-12-28) |
| `knowledge` | 717 entries; pre-F130 entries may have NULL tier (not promoted by consolidate_memories) |
| `schema_registry` | 101 rows for 58 live tables — 43 stale entries from dropped tables |
| `audit_log` | 254 entries for 906 sessions + 426 tasks — most pre-WorkflowEngine (added 2026-02-10) |
| `protocol_versions` | Active version: v10 (2026-03-09, 8 rules), injected on every prompt |

---

## 9. Data Quality Issues (Ranked by Impact)

| # | table | issue | fix |
|---|-------|-------|-----|
| 1 | `schema_registry` | 43 stale entries for dropped tables | `DELETE FROM claude.schema_registry WHERE table_name NOT IN (SELECT relname FROM pg_class JOIN pg_namespace ON relnamespace=oid WHERE nspname='claude' AND relkind='r')` |
| 2 | `mcp_usage` | All 6,965 rows are synthetic test data | Truncate table; verify PostToolUse hook works before re-enabling |
| 3 | `sessions` | ~52 permanently unclosed sessions | `UPDATE claude.sessions SET ended_at=started_at+interval '1h', summary='Auto-closed' WHERE ended_at IS NULL AND started_at < NOW()-interval '24h'` |
| 4 | `enforcement_log` | 1,333 zombie writes from archived process_router | Confirm process_router.py no longer executes; if dead, stop writes |
| 5 | vault doc stale | `Work Tracking Schema.md` says `pending` valid for build_tasks.status — actual is `todo` | Update vault doc |
| 6 | `bpmn_processes` | Registry stale — sync_bpmn_to_db.py has ImportError | Fix import of `_discover_process_files` and `_parse_bpmn_file` in sync script |
| 7 | `knowledge` | Pre-F130 entries have NULL tier | Query: `SELECT count(*) FROM claude.knowledge WHERE tier IS NULL` then backfill |
| 8 | `sessions.project_name` | Identified by mutable name string, not UUID FK | Long-term: add project_id FK column |
| 9 | versioning tables | instructions_versions, rules_versions, skills_versions all empty | Backfill from filesystem |

---

## 10. Recommendations for Project Metis Data Model

### Preserve (proven patterns)

1. **WorkflowEngine + workflow_transitions** — state machine with DB-stored rules; prevents invalid transitions; new paths added by inserting rows, not code changes
2. **column_registry (Data Gateway)** — lightweight enum enforcement at application layer before DB constraint; check before every constrained write
3. **3-tier knowledge table** — short/mid/long/archived tiers with consolidation lifecycle; budget-capped recall prevents context flooding
4. **Short codes** — F1, FB1, BT1 serial pattern; human-referenceable in git commits without UUIDs
5. **audit_log** — immutable transition log via WorkflowEngine; essential for enterprise compliance
6. **session_facts key/value store** — crash-resistant per-session notepad; survives context compaction
7. **Self-healing config** — DB source of truth, auto-regeneration on SessionStart

### Fix before Metis

1. schema_registry drift — 1 DELETE statement
2. mcp_usage synthetic data — truncate and verify hook
3. sync_bpmn_to_db.py ImportError — fix import, re-run sync
4. Work Tracking Schema.md stale doc — update `pending` to `todo`
5. 52 orphaned sessions — one-time cleanup UPDATE

### Design for Metis

| need | recommendation |
|------|----------------|
| Multi-instance deployment | PgBouncer connection pooling |
| Multi-tenant isolation | PostgreSQL row-level security on client_domain |
| Schema evolution | Alembic or Flyway — current ad hoc SQL is a maintenance risk |
| High-volume tables | Partition by month: todos, mcp_usage, vault_embeddings, rag_usage_log |
| sessions join | Add project_id UUID FK — replace project_name string |
| MCP telemetry | Verify PostToolUse hook writes real session_id to mcp_usage |
| BPMN coverage | Expand _ARTIFACT_REGISTRY from 8 to all 65 processes |

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-audit-indexes.md
