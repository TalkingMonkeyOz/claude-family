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

# Schema Detail: `claude.project_workfiles`

Back to [[schema-index]]

**Row count (audit 2026-02-28)**: Not in audit (table created 2026-03-09 per CLAUDE.md changelog — post-audit).
**Purpose**: Cross-session component-scoped working context. Filing cabinet metaphor: project = cabinet, component = drawer, title = file. Replaces the pattern of re-explaining context at session start for ongoing feature work.

---

## Columns

| # | Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `workfile_id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| 2 | `project_id` | `uuid` | NO | — | FK to projects (required) |
| 3 | `component` | `varchar` | NO | — | Logical component / "drawer" name |
| 4 | `title` | `varchar` | NO | — | File title within component |
| 5 | `content` | `text` | NO | — | Working context (arbitrary markdown) |
| 6 | `workfile_type` | `varchar` | YES | `'notes'` | Type enum (see below) |
| 7 | `tags` | `text[]` | YES | NULL | Searchable tags |
| 8 | `feature_code` | `varchar` | YES | NULL | Associated feature code (e.g., `F130`) |
| 9 | `is_pinned` | `boolean` | YES | `false` | Surfaced at session start if true |
| 10 | `is_active` | `boolean` | YES | `true` | Soft-delete flag |
| 11 | `linked_sessions` | `uuid[]` | YES | `ARRAY[]::uuid[]` | Sessions that wrote to this workfile |
| 12 | `embedding` | `vector(1024)` | YES | NULL | Voyage AI voyage-3 embedding |
| 13 | `access_count` | `integer` | YES | `0` | Incremented on `unstash()` |
| 14 | `last_accessed_at` | `timestamptz` | YES | NULL | Last unstash time |
| 15 | `created_at` | `timestamptz` | YES | `NOW()` | First stash time |
| 16 | `updated_at` | `timestamptz` | YES | `NOW()` | Last stash/update time |

Total: 16 columns (matches CLAUDE.md reference).

Source: INSERT in `mcp-servers/project-tools/server.py` lines 1173–1196 (`tool_stash`).

---

## workfile_type Enum

Validated via `column_registry` in `validate_value('project_workfiles', 'workfile_type', ...)`:

| Value | Description |
| --- | --- |
| `notes` | General working notes (default) |
| `approach` | Technical approach decisions |
| `findings` | Research or investigation results |
| `questions` | Open questions or blockers |
| `context` | Background context for a feature |
| `decisions` | Decisions made |

---

## Unique Constraint

`UNIQUE(project_id, component, title)` — UPSERT on this triple. Each named file in each component drawer of each project has exactly one row. The conflict resolution updates `content`, `embedding`, `tags`, `feature_code`, `is_pinned`, and accumulates `linked_sessions` (array union).

---

## Append Mode

When `mode="append"`, `stash()` reads the existing content first:

```python
content = existing_content + "\n---\n" + new_content
```

This accumulates notes across multiple sessions without overwriting.

---

## Indexes

| Index | Type | Columns | Purpose |
| --- | --- | --- | --- |
| `project_workfiles_pkey` | btree (PK) | `workfile_id` | PK |
| `idx_pw_project_component` | btree | `(project_id, component)` | Component listing (`list_workfiles`) |
| `idx_pw_project_title` | btree | `(project_id, component, title)` | Unique lookup |
| `idx_pw_is_pinned` | btree | `is_pinned` WHERE `is_pinned=true` | Partial index — session-start query |
| `idx_pw_embedding` | ivfflat | `embedding vector_cosine_ops` | Semantic search (`search_workfiles`) |
| `idx_pw_feature_code` | btree | `feature_code` | Feature-scoped queries |
| `idx_pw_is_active` | btree | `is_active` | Active filter |

---

## Foreign Keys

| Column | References | On Delete |
| --- | --- | --- |
| `project_id` | `claude.projects.project_id` | RESTRICT (inferred — NOT NULL column) |

---

## Integration Points

| System | Role | Budget Allocation |
| --- | --- | --- |
| `stash()` MCP tool | Primary writer | — |
| `unstash()` MCP tool | Primary reader | — |
| `list_workfiles()` | Browse by component | — |
| `search_workfiles()` | Semantic search | — |
| PreCompact hook | Pinned workfiles injected before compaction | Priority 3.5 |
| `start_session()` | Active workfiles listed | Summary only |
| WCC assembly | Context source #1 | 25% of WCC budget |
| `cognitive_memory_retrieval.bpmn` | 4th parallel search branch | — |

---

## BPMN Process Coverage

This table is modeled in `mcp-servers/bpmn-engine/processes/infrastructure/workfile_management.bpmn`. The workfile lifecycle (stash, unstash, pin, search, precompact injection) is defined there. Four existing BPMN processes were also updated when workfiles were added:

- `precompact.bpmn`
- `cognitive_memory_retrieval.bpmn`
- `session_lifecycle.bpmn`
- `working_memory.bpmn`

---

## METIS Assessment Notes

**Strength**: The component/title scoping gives a natural semantic namespace for working context. The append mode enables progressive knowledge accumulation within a session chain.

**Strength**: `linked_sessions` array accumulates session IDs across all writes — enables tracing which sessions contributed to a workfile.

**Strength**: The partial index on `is_pinned=true` makes the session-start pinned-file query very fast even as the table grows.

**Opportunity**: This is the newest semantic table and has the cleanest design of the three. No deprecated columns, no FK confusion. A good candidate for METIS to extend or build patterns around.

**Gap**: No explicit `source` column. Workfiles cannot record whether content came from user input, Claude output, or an automated pipeline. This metadata may be useful for METIS trust scoring.

**Gap**: `workfile_type` is an enum validated only by `column_registry` (application layer) not a DB CHECK constraint. Invalid values could be inserted by direct SQL.

---

## Source Code References

- `mcp-servers/project-tools/server.py` lines 1129–1212 (`tool_stash`, `tool_unstash`)
- `mcp-servers/project-tools/server_v2.py` lines 700–714 (`list_workfiles` context query)
- `scripts/wcc_assembly.py` — WCC workfile retrieval
- `scripts/precompact_hook.py` — pinned workfile injection
- `mcp-servers/bpmn-engine/processes/infrastructure/workfile_management.bpmn`

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-project-workfiles.md
