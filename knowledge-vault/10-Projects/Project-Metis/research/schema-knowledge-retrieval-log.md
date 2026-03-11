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

# Schema Detail: `claude.knowledge_retrieval_log`

Back to [[schema-index]]

**Row count (audit 2026-02-28)**: 77
**Status**: FROZEN — no current code writes to this table. All rows were written by the retired `archive/process_router.py` (keyword-based retrieval era, pre-2026-01-17).

---

## Columns

| # | Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `log_id` | `uuid` or `serial` | NO | auto | Primary key (type inferred) |
| 2 | `prompt_excerpt` | `text` | YES | NULL | First 200 chars of the triggering prompt |
| 3 | `keywords` | `text[]` | YES | NULL | Keywords that triggered retrieval |
| 4 | `results_count` | `integer` | YES | NULL | Number of entries returned |
| 5 | `results_ids` | `uuid[]` | YES | NULL | Array of returned `knowledge_id` values |
| 6 | `retrieval_method` | `varchar` | YES | `'keyword'` | Method: `keyword` (only observed value) |
| 7 | `latency_ms` | `integer` | YES | NULL | Retrieval latency in milliseconds |
| 8 | `session_id` | `uuid` | YES | NULL | FK to sessions (nullable) |
| 9 | `created_at` | `timestamptz` | YES | `NOW()` | Log timestamp |

**Columns that may exist in live schema** (not in the archived INSERT, referenced in `server_v2.py` context):

| Column | Type | Notes |
| --- | --- | --- |
| `tiers_queried` | `text` | Which memory tiers were queried |
| `query_type` | `varchar` | Budget profile: `default`, `task_specific`, `exploration` |

Source: INSERT in `archive/process_router.py` lines 356–369. Additional columns inferred from server_v2.py variable naming.

---

## Indexes

| Index | Type | Columns | Purpose |
| --- | --- | --- | --- |
| Primary key | btree | `log_id` | PK |
| `idx_krl_session` | btree | `session_id` | Session-scoped queries |
| `idx_krl_created` | btree | `created_at` | Time-range queries |

---

## Foreign Keys

| Column | References | On Delete |
| --- | --- | --- |
| `session_id` | `claude.sessions.session_id` | SET NULL |

Documented explicitly in Database Integration Guide: `knowledge_retrieval_log.session_id → sessions.session_id (SET NULL)`.

---

## Activity Timeline

| Period | Writer | Entries |
| --- | --- | --- |
| Pre-2026-01-17 | `process_router.py` (keyword-based) | 77 total |
| 2026-01-17 onwards | Nothing (process_router retired) | 0 new |

Current cognitive memory tools (`recall_memories()`, `recall_knowledge()`) update `knowledge.last_accessed_at` and `access_count` directly rather than writing observability records. The RAG system writes to `claude.rag_usage_log` (2,287 rows per audit) instead.

---

## METIS Assessment Notes

**Critical gap**: There is currently no observability log for `recall_memories()` calls. METIS cannot answer questions like:

- Which knowledge entries are retrieved most frequently?
- What queries trigger the knowledge graph walk?
- How often does the short/mid/long tier return results vs miss?
- What is the latency distribution of 3-tier retrieval?

**Options for METIS**:

1. Reactivate `knowledge_retrieval_log` with updated columns to capture 3-tier retrieval events.
2. Add logging inside `recall_memories()` to write a new observability record per call.
3. Use an external observability store (e.g., append-only JSONL) to avoid DB write overhead on every prompt.

The `tiers_queried` and `query_type` columns suggest someone planned to extend this table for 3-tier use but may not have completed the implementation.

---

## Source Code References

- `archive/process_router.py` lines 342–378 (`log_knowledge_retrieval` function — original writer)
- `knowledge-vault/20-Domains/Database Integration Guide.md` line 281 (FK documentation)
- `knowledge-vault/20-Domains/Table Code Reference Map - KEEP.md` line 64 (row count, reference)

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-knowledge-retrieval-log.md
