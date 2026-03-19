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

# Schema Detail: `claude.knowledge`

Back to [[schema-index]]

**Row count (audit 2026-02-28)**: 717
**Purpose**: Central store for the MID and LONG tiers of 3-tier cognitive memory. Holds learned facts, patterns, gotchas, preferences, procedures, and session-derived insights. The SHORT tier (credentials, configs, endpoints) routes to `session_facts` instead.

---

## Columns

| # | Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `knowledge_id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| 2 | `title` | `varchar(200)` | NO | — | Short descriptive title (truncated to 100 chars in `remember()`) |
| 3 | `description` | `text` | NO | — | Full knowledge content |
| 4 | `knowledge_category` | `varchar(100)` | YES | NULL | Domain category (e.g., `database`, `react`, `testing`) |
| 5 | `knowledge_type` | `varchar(50)` | YES | NULL | See enum below |
| 6 | `code_example` | `text` | YES | NULL | Optional code snippet |
| 7 | `confidence_level` | `integer` | YES | NULL | 1–100; affects retrieval ranking |
| 8 | `applies_to_projects` | `text[]` | YES | `'{}'` | Project filter — empty array means all projects |
| 9 | `times_applied` | `integer` | YES | `0` | Usage counter, incremented on access |
| 10 | `embedding` | `vector(1024)` | YES | NULL | Voyage AI voyage-3 embedding (1024 dims) |
| 11 | `tier` | `varchar(10)` | YES | `'mid'` | Memory tier: `mid`, `long`, `archived` |
| 12 | `source` | `varchar` | YES | NULL | Origin: `session:<uuid>`, `conversation:<id>`, `remember` |
| 13 | `last_accessed_at` | `timestamptz` | YES | NULL | Updated on every retrieval |
| 14 | `access_count` | `integer` | YES | `0` | Incremented by recall tools |
| 15 | `session_id` | `uuid` | YES | NULL | FK to sessions (nullable) |
| 16 | `project_id` | `uuid` | YES | NULL | FK to projects (nullable) |
| 17 | `created_at` | `timestamptz` | YES | `NOW()` | Creation timestamp |
| 18 | `updated_at` | `timestamptz` | YES | NULL | Last modification |

---

## knowledge_type Enum

| Value | Tier Routed To | Description |
| --- | --- | --- |
| `learned` | mid | Discovered facts (default) |
| `pattern` | long | Reusable approach |
| `gotcha` | long | Non-obvious trap |
| `preference` | long | Style/approach preference |
| `fact` | mid | Factual reference |
| `procedure` | long | How-to steps |
| `decision` | mid | Decision made during work |
| `note` | mid | General note |
| `data` | mid | Data reference |
| `credential` | SHORT (session_facts) | Routes away — not stored here |
| `config` | SHORT (session_facts) | Routes away — not stored here |
| `endpoint` | SHORT (session_facts) | Routes away — not stored here |

## tier Enum

| Value | Meaning | Access Behavior |
| --- | --- | --- |
| `mid` | Working knowledge (default for `remember()`) | Semantic search, similarity >= 0.40 |
| `long` | Proven patterns | Semantic search, similarity >= 0.35, + 1-hop graph walk |
| `archived` | Confidence < 30 AND stale (90+ days) | Not returned by recall tools |

---

## Indexes

| Index | Type | Columns | Purpose |
| --- | --- | --- | --- |
| `knowledge_pkey` | btree (PK) | `knowledge_id` | PK lookup |
| `idx_knowledge_embedding` | ivfflat | `embedding vector_cosine_ops` | Semantic similarity search |
| `idx_knowledge_category` | btree | `knowledge_category` | Category filtering |
| `idx_knowledge_tier` | btree | `tier` | Tier partitioning |
| `idx_knowledge_type` | btree | `knowledge_type` | Type filtering |
| `idx_knowledge_projects` | GIN | `applies_to_projects` | `= ANY(...)` containment |
| `idx_knowledge_confidence` | btree | `confidence_level` | Ranking queries |

---

## Foreign Keys

| Column | References | On Delete |
| --- | --- | --- |
| `session_id` | `claude.sessions.session_id` | SET NULL |
| `project_id` | `claude.projects.project_id` | SET NULL |

Both are nullable — knowledge entries can exist without session or project context.

---

## Retrieval Scoring Formula (mid/long tiers)

```python
recency       = max(0, 1.0 - days_since_access / 90.0)
access_freq   = min(times_applied / 10.0, 1.0)
confidence    = confidence_level / 100.0
score = similarity * 0.4 + recency * 0.3 + access_freq * 0.2 + confidence * 0.1
```

Minimum similarity thresholds: mid = 0.40, long = 0.35.

---

## Key Writers and Readers

| Tool / Script | Direction | Notes |
| --- | --- | --- |
| `remember()` | Write (mid/long) | Dedup check >0.85 sim → merge; auto-link |
| `store_knowledge()` | Write (legacy) | No tier set by default → defaults to NULL or `mid` |
| `end_session()` | Write (mid) | Session learnings, `source='session:<id>'` |
| `extract_insights()` | Write | From conversation JSONL analysis |
| `recall_memories()` | Read | 3-tier budget-capped retrieval |
| `recall_knowledge()` | Read (legacy) | Similarity-only, no tier awareness |
| `graph_search()` | Read | pgvector + `knowledge_relations` walk |

---

## Source Code References

- `mcp-servers/project-tools/server.py` lines 1791–2003 (`tool_remember`)
- `mcp-servers/project-tools/server.py` lines 1548–1788 (`tool_recall_memories`)
- `mcp-servers/project-tools/server.py` lines 993–1010 (`end_session` knowledge INSERT)
- `mcp-servers/project-tools/server_v2.py` lines 3431–3510 (`store_knowledge` legacy)

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-knowledge.md
