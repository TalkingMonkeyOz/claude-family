---
projects:
- claude-family
- project-metis
tags:
- audit
- storage
- overlap
- dead-weight
synced: false
---

# Storage Mechanisms Audit — Part 3: Overlap, Dead Weight, Volume

**Index**: [storage-audit index](../../../docs/audit-storage-mechanisms.md) (relative: `docs/audit-storage-mechanisms.md`)
**Part 1**: [facts, knowledge, workfiles](storage-audit-part1.md)
**Part 2**: [vault, todos, WCC, misc](storage-audit-part2.md)
**Findings**: [key findings (12 numbered)](storage-audit-findings.md)
**Audit date**: 2026-03-12

---

## Overlap Analysis

### "Things Claude Learned" — 5-Way Overlap

The same learned content can simultaneously exist in:

| Store | Content type | Trigger |
|-------|-------------|---------|
| `session_facts` (note/decision) | Discovered during session | Core Protocol Rule 3 |
| `knowledge` MID | Same content promoted | `remember()` call |
| `knowledge` LONG | If pattern/gotcha typed | `remember(type='pattern')` |
| `vault_embeddings` | If written to a vault doc | Manual vault doc + embed run |
| `MEMORY.md` | If added to memory | Built-in memory tool |
| Session notes file | If `store_session_notes()` called | Core Protocol Rule 6 |

A gotcha discovered in session may end up in all 6 stores with no cross-reference. There is no systematic pathway — content duplication is the default outcome.

### "Current Work Context" — 4-Way Overlap

| Content | Store 1 | Store 2 | Store 3 | Store 4 |
|---------|---------|---------|---------|---------|
| What is being worked on | `session_facts` (current_activity) | WCC activities table | precompact session_state | session notes file |
| Feature progress | `build_tasks` | `todos` | session notes | session_facts (reference) |
| Open questions | `session_facts` (note) | `project_workfiles` (questions) | session notes | knowledge MID |

### "Knowledge About This Project" — 3-Way Overlap

| Content | Store 1 | Store 2 | Store 3 |
|---------|---------|---------|---------|
| Project docs | `vault_embeddings` | `claude.documents` | — |
| Design decisions | `MEMORY.md` | vault docs | `knowledge` MID |
| SOPs and procedures | `vault_embeddings` (40-Procedures/) | `knowledge` LONG | — |
| CLAUDE.md content | `claude.profiles` (DB) | file on disk (generated) | — |

### Redundant Retrieval Paths

The WCC `vault_rag` source and the main RAG hook both query `claude.vault_embeddings` with the same HNSW query. When WCC is active, per-source RAG is skipped — but when WCC is inactive (99% of current sessions), both the WCC fallback path and the main RAG hook run the same query. No deduplication occurs.

---

## Dead Weight Assessment

### Structurally Dead — Safe to Remove

| Mechanism | Evidence | Action |
|-----------|----------|--------|
| `mcp_usage` (6,965 rows) | All rows have NULL session_id. `mcp_usage_logger.py` never wrote real data. | Truncate. Fix or remove the logger. |
| `enforcement_log` (1,333 rows) | Written by archived `process_router.py` (retired 2026-02-28). No consumer. | Truncate. Confirm DROP after code scan. |
| `knowledge_retrieval_log` (77 rows) | Last write from retired `process_router.py`. `recall_memories()` does not log here. | Add write in `tool_recall_memories` or drop. |
| `workflow_state` (0 rows) | No write path exists in server_v2.py. | Verify vestigial, then drop. |

### Built but Unadopted — Not Dead, But Adoption Gap

| Mechanism | Evidence | Root Cause |
|-----------|----------|------------|
| `project_workfiles` (3 rows) | 3 entries in 3 days across 24 projects | Not in Core Protocol (8 rules); `stash()` not mentioned |
| `activities` (0 explicit rows) | Zero user-created activities | No onboarding path; WCC cannot function without them |
| WCC context assembly | WCC never fires in practice | Requires both workfiles and activities; both are empty |

### Functionally Broken — Feature-Complete, Pipeline Broken

| Mechanism | Issue | Impact |
|-----------|-------|--------|
| Knowledge MID→LONG promotion | 96% stuck at MID (987/1,026 entries) | LONG tier provides no benefit; patterns not surfacing |
| `consolidate_memories()` Phase 1 | Only fires for closed sessions; excludes current session | Facts that should elevate to knowledge don't during active work |
| Duplicate promotion logic | MID→LONG criteria in `server.py:2102` AND `session_startup_hook_enhanced.py:289` | Can diverge on threshold updates |
| Edge decay formula | Uses `created_at` not `last_accessed_at` | An edge traversed yesterday but created 30 days ago is heavily penalized |
| Knowledge graph walk | Graph entries get fixed score 0.3, always ranked below direct matches | Graph contribution is effectively invisible in results |

---

## Volume Analysis

### Growing Mechanisms

| Mechanism | Growth rate | Notes |
|-----------|-------------|-------|
| `vault_embeddings` | ~2,700 new chunks on large vault update days | Fastest growing; driven by vault edits |
| `session_facts` | ~23 facts/day across all projects | Steady healthy growth |
| `knowledge` MID | ~40 entries/week (estimated) | Growing but quality declining |
| `sessions` | ~5-10 sessions/day across all projects | Linear growth |
| `todos` | High churn; 2,711 total | Grows per session; archived on completion |

### Stale or Not Growing

| Mechanism | Last meaningful activity | Assessment |
|-----------|--------------------------|------------|
| `knowledge_relations` | ~67 rows; no significant growth evidence | Auto-linking rarely fires at current `remember()` call rate |
| `knowledge` LONG | 12% of total (127/1,026); promotion broken | Should be ~20-30%; pipeline fix required |
| `messages` | 187 rows | Correct scale — intentional, low-frequency |
| `audit_log` | 254 rows | Correct scale for state machine transitions |
| Session notes files | 7 files; inconsistent entries | Sporadic use, not a growth concern |
| `project_workfiles` | 3 rows; table is 3 days old | Too new to assess; adoption is the problem |

### Storage Cost Hotspots

Based on schema-audit-indexes.md volume estimates:

| Table | Estimated storage | Notes |
|-------|------------------|-------|
| `vault_embeddings` | 50-100 MB (table + HNSW index) | Largest by far; 9,655+ × 1024 float32 vectors |
| `document_projects` | 10-30 MB | 6,515 rows with embedding refs |
| `knowledge` | 5-15 MB | 1,026 rows × 1024 float32 vectors |
| `mcp_usage` | 1-5 MB | Entirely wasted on synthetic data |
| `todos` | 1-5 MB | High-churn table with many indexes |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-part3.md
