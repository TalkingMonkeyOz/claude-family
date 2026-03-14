---
projects:
- claude-family
tags:
- testing
- project-tools
- mcp
synced: false
---

# Project-Tools Functional Test — Tool Detail

**Back to**: [project-tools-functional-test-2026-03-14.md](project-tools-functional-test-2026-03-14.md)

---

## Tool-by-Tool Analysis

### T1 — start_session

Lines 443-765 in `server_v2.py`. Three phases:

1. Project context + session state + last session (single CTE query)
2. Todos + features + ready tasks + feedback + message counts (joined CTE)
3. Recommended actions, recent decisions, relevant knowledge, active workfiles, entity catalog summary

Startup demotion of orphaned in_progress todos runs before phase 2 and commits
independently. Zombie archiving (`restore_count >= 4`) also runs at startup.

Return shape: `{project_name, project_id, project_context, previous_state, last_session, todos, active_features, ready_tasks, recommended_actions, pending_messages}`.

### T2 — get_work_context

Lines 1608-1780. Three scopes:
- `current`: single `status='in_progress'` build_task ordered by `updated_at DESC`
- `feature`: finds feature via in_progress task (UNION fallback to `feature.status='in_progress'`)
- `project`: all non-completed features + unblocked todo tasks + open feedback with counts

### T3 — list_session_facts

Delegates to `tool_list_session_facts` in `server.py`. Queries `claude.session_facts`
by `project_name` and `session_id`. Sensitive values shown as `[REDACTED]` unless
`include_sensitive=True`. Returns `{success, facts: [...], count}`.

### T4 — recall_memories

`server.py` lines 1549-1640. Budget profiles apply per `query_type`:
- `default`: 20% short / 40% mid / 40% long
- `task_specific`: 40% short / 40% mid / 20% long
- `exploration`: 10% short / 30% mid / 60% long

SHORT tier: `claude.session_facts` ordered by fact_type priority. MID tier:
`claude.knowledge WHERE tier='mid'` with pgvector similarity. LONG tier: same table
`tier='long'` plus 1-hop walk via `claude.knowledge_relations`. Returns error dict
if embedding generation fails (correct fail-safe).

### T5 — recall_entities

Lines 6266-6428. RRF fusion of two CTEs:
- `entity_vec`: pgvector cosine similarity on `claude.entities.embedding`
- `entity_bm25`: tsvector BM25 ranking on `claude.entities.search_vector`

Parameters correctly supplied for both CTEs (lines 6382-6389, `*filter_params` appears
twice). `filter_clause` is an f-string of static SQL fragments built from validated
inputs — no SQL injection risk. Issue: unknown `entity_type` silently returns zero rows.

### T6 — recall_knowledge (LEGACY)

Delegates to `tool_recall_knowledge` in `server.py`. Queries `claude.knowledge` with
pgvector similarity, excludes `tier='archived'`. Optional filters: `knowledge_type`,
`project`, `domain`, `source_type`, `tags`, `date_range_days`. Fully functional;
`recall_memories` is preferred but this path remains correct.

### T7 — list_workfiles

Delegates to `tool_list_workfiles` in `server.py`. Without `component`: returns
component-level metadata (name, file_count, last_updated, pinned_count). With
`component`: lists individual files in that drawer. Filtered to `is_active=True` by default.

### T8 — unstash

Delegates to `tool_unstash` in `server.py`. Retrieves from `claude.project_workfiles`
by `(project_id, component)`. Without `title`: all files in component. With `title`:
single file. Updates `access_count` and `last_accessed_at` on retrieval.

### T9 — get_ready_tasks

`server.py` lines 684-722. SQL condition: `status='todo'` AND `(blocked_by_task_id IS NULL
OR blocked_by_task_id IN (SELECT task_id ... WHERE status='completed'))`. Ordered by
`f.priority, f.short_code, bt.step_order`. Returns `{project_id, ready_tasks, tasks}`.

### T10 — get_incomplete_todos

`server.py` lines 385-424. Queries `claude.todos WHERE status IN ('pending','in_progress')
AND NOT is_deleted`. LEFT JOIN `claude.sessions` for `session_start` timestamp. Ordered
by status priority then `priority`, `display_order`.

### T11 — check_inbox

Lines 5183-5278. Recipient logic: if `project_name` provided, adds `to_project = ?`;
if `include_broadcasts=True` (default), also includes `(to_session_id IS NULL AND
to_project IS NULL)`. Status filter: `pending` only by default. Messages ordered by
priority urgency then `created_at DESC`. Limit 20.

### T12 — list_recipients

Lines 5142-5177. Queries `claude.workspaces JOIN claude.projects WHERE is_active=true`.
Subquery retrieves `last_session` from `claude.sessions MAX(created_at)`. Returns
`{count, recipients: [{project_name, description, client_domain, last_session}]}`.

### T13 — get_active_protocol (ISSUE)

Lines 5099-5133. Queries `claude.protocol_versions WHERE protocol_name='CORE_PROTOCOL'
AND is_active=true`. Implementation is correct. The data issue: MEMORY.md documents v11
(2026-03-11, 8 rules) but CLAUDE.md Recent Changes lists "Core Protocol v12" for
2026-03-13. Verify: `SELECT version, created_at FROM claude.protocol_versions WHERE is_active = true`.

### T14 — search_bpmn_processes

Lines 4134-4284. When Voyage AI available: pgvector cosine similarity on
`claude.bpmn_processes.embedding`. When unavailable: falls back to ILIKE on
`process_name` and `description` (similarity fixed at 0.5 in fallback). `client_domain`
filter adds JOIN on `claude.projects` and includes `'infrastructure'` domain. Correct
behaviour; data quality depends on `sync_bpmn_processes()` having been run.

### T15 — recall_book_reference (ISSUE)

Lines 2142-2258. Generates query embedding, then cosine similarity >= 0.5 on
`claude.book_references JOIN claude.books`. Three SQL params: embedding for SELECT,
embedding for WHERE filter, limit. Parameter count is correct.

Issue: MEMORY.md (2026-03-13) states books migrated to Entity Catalog as 49 entities.
`claude.book_references` is likely sparse post-migration. Preferred path:
`recall_entities(query, entity_type='book')`.

---

## Architecture: Import Chain

```
server_v2.py (FastMCP, sync wrappers)
  ├─ Loads ~/OneDrive/Documents/AI_projects/ai-workspace/.env at import time
  ├─ Overwrites ${...} env vars with values from .env
  ├─ Imports async tool_* functions from server.py
  └─ _run_async(): asyncio.run() or ThreadPoolExecutor if already in event loop
```

## Voyage AI Dependency Map

| Tool | Behavior without Voyage AI |
|------|---------------------------|
| `recall_memories` | Returns error dict — cannot search mid/long tiers |
| `recall_entities` | Returns error dict at entry point |
| `recall_knowledge` | Returns error dict |
| `recall_book_reference` | Returns error dict |
| `search_bpmn_processes` | Degrades to ILIKE keyword search (functional) |
| All others | Not affected |

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/Project-Metis/project-tools-functional-test-detail-2026-03-14.md
