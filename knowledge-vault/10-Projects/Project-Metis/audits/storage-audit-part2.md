---
projects:
- claude-family
- project-metis
tags:
- audit
- storage
- data-model
synced: false
---

# Storage Mechanisms Audit — Part 2: Vault, Todos, WCC, Misc

**Index**: [storage-audit index](../../../docs/audit-storage-mechanisms.md) (relative: `docs/audit-storage-mechanisms.md`)
**Part 1**: [facts, knowledge, workfiles](storage-audit-part1.md)
**Part 3**: [overlap, dead weight, volume](storage-audit-part3.md)
**Audit date**: 2026-03-12

---

## 6. Vault Embeddings

| Attribute | Value |
|-----------|-------|
| Table | `claude.vault_embeddings` |
| Related | `claude.documents` (5,940 rows), `claude.document_projects` (6,515 rows) |
| Row count | 9,655 at 2026-02-28; ~12,345 estimated after 2026-03-11 dual re-embed (+2,690 new chunks) |
| Status | Active, growing, healthy |

**What it stores**: Chunked Voyage AI embeddings of vault markdown files. Each file split into 1,000-character chunks with 200-character overlap. Approximately 9.7+ million characters of indexed text. UNIQUE on `(doc_path, chunk_index)`.

**When triggered**: `embed_vault_documents.py` script (incremental by SHA-256 hash; only changed files re-embedded). A scheduled job for auto-embedding was added post-audit (FB134). The 2026-03-11 session notes confirm two manual re-embed runs adding 1,912 + 778 new chunks after vault reorganization.

**Retrieval**: Every user prompt passes through `rag_query_hook.py` which queries this table via HNSW index when `needs_rag()` returns True. Uses Voyage AI `"query"` input_type (asymmetric retrieval vs stored `"document"` type). Excludes `awesome-copilot` source docs.

**Design strengths**: Only semantic table with a NOT NULL constraint on `embedding` — 100% embedding coverage guaranteed. HNSW index (fastest ANN algorithm in pgvector). Incremental re-embedding on file hash change. Best-maintained semantic index in the system.

**Overlap**: The WCC `vault_rag` source (15% of 1,500-token WCC budget) re-runs the same HNSW query with an activity filter — duplicate of the main RAG hook query. No FK link from `knowledge` to `vault_embeddings` — derived insights cannot trace back to source chunks (Gap G2 from schema-assessment-gaps.md).

---

## 7. Todos

| Attribute | Value |
|-----------|-------|
| Table | `claude.todos` |
| Row count | 2,711 (2026-02-28) |
| Status | Active, high-churn, quality issues |

**What it stores**: Task records bridging Claude Code's native task system with DB tracking. Written by `todo_sync_hook.py` (TodoWrite PostToolUse) and `task_sync_hook.py` (TaskCreate/TaskUpdate PostToolUse).

**How the bridge works**: `task_sync_hook.py` maps Claude's internal task IDs to DB `todo_id` via a temp file at `%TEMP%\claude_task_map_{project}.json`. On TaskCreate, checks for similar existing todo (substring >= 20 chars OR SequenceMatcher >= 0.75). On TaskUpdate, syncs to `build_tasks` if a bridged task is found.

**Known fragility**:
- Task map in `%TEMP%` is lost on reboot; after reboot `handle_task_update` cannot find `todo_id` and silently skips DB updates
- Compaction orphans in-progress tasks — they appear as duplicates post-compaction. `restore_count` tracks this but does not fix it
- `CLAUDE_CODE_TASK_LIST_ID` shared-list mode requires env var in both `.env` AND the launcher `.bat` — missing from either silently breaks cross-session persistence

**Quality issues**: Prior research (task-excerpts-2.md) documented `restore_count=2` entries — tasks created 2026-02-23, still pending 2026-02-24, having been TaskCreate'd and re-synced at least twice without completion. Zombie task accumulation is a known issue.

**Overlap**: `claude.build_tasks` is the structured tracking layer (linked to features, workflow state machine); todos are the session-sync shim over Claude Code's native task list. The two are bridged via fuzzy name matching, not a hard FK.

---

## 8. Activities (WCC)

| Attribute | Value |
|-----------|-------|
| Table | `claude.activities` |
| Row count | ~0 explicit; auto-created via workfile component fallback |
| Table created | 2026-03-10 |
| Status | Framework built, effectively unused |

**What it stores**: Named activities with aliases for automatic detection. The WCC system detects the "current activity" from the user's prompt and assembles relevant context from 6 sources (workfiles 25%, knowledge 25%, features 15%, session_facts 10%, vault_rag 15%, BPMN/skills 10%).

**Detection logic** (wcc_assembly.py): 4 priority levels — (1) manual session_fact override, (2) exact name/alias match, (3) word overlap (2+ shared 3-char words), (4) workfile component fallback. The word overlap is coarse: "Session Management" matches any prompt containing "session" and one other word.

**Auto-create side effect**: When a workfile component name matches the prompt, `_ensure_activity_exists()` silently creates an activity via UPSERT. This grows the activities table without explicit user action.

**Implementation gap**: `MIN_ACTIVITY_SIMILARITY = 0.6` (line 43, wcc_assembly.py) and the docstring claim trigram fuzzy matching. The actual detection function does not use trigrams or this constant — it is dead code.

**Cache invalidation unimplemented**: `invalidate_wcc_cache()` is documented as called when `stash()` or `remember()` fires, but neither function calls it. Cache expires only by TTL (5 minutes). New workfiles are invisible to WCC for up to 5 minutes.

**Functional dependency**: WCC only fires if an activity is detected AND context is assembled. With 0 explicit activities and 3 workfiles, WCC falls through to per-source RAG queries — which are the same queries the main RAG hook runs anyway. WCC is currently a no-op.

---

## 9. Session Notes Files

| Attribute | Value |
|-----------|-------|
| Location | `~/.claude/session_notes/{project_name}.md` |
| Files present | 7 (claude-family, nimbus-mui, nimbus-user-loader, nimbus-odata-configurator, monash-nimbus-reports, trading-intelligence, System32) |
| Storage type | Filesystem only (not DB) |
| Status | Active, inconsistent |

**What it stores**: Append-only progress notes per project. Arbitrary markdown with timestamps. Written by `store_session_notes()` MCP tool to a file-per-project path. Injected into precompact context at P4 priority (raw file read, no structure).

**When triggered**: Explicit `store_session_notes()` calls. Core Protocol Rule 6 says "store_session_notes(findings, 'progress') before moving on" — advisory only. In practice, session notes are written sporadically.

**Content observed** (claude-family.md): Structured session summaries, knowledge table stats with actual row counts, design decisions, and task tracking — high-quality content when written. Content quality varies by session and author.

**Overlap**: Direct functional overlap with project workfiles (same cross-session persistence use case). Also overlaps with session_facts (decisions), knowledge MID (findings and learnings). The lowest-fidelity mechanism: no semantic search, no embeddings, no structure, no budget management.

---

## 10. MEMORY.md

| Attribute | Value |
|-----------|-------|
| Location | `~/.claude/projects/C--Projects-claude-family/memory/MEMORY.md` |
| Files found | 1 (claude-family only) |
| Storage type | Filesystem (Claude Code built-in) |
| Status | Active (1 project only) |

**What it stores**: Curated project memory: architecture rules, gotchas, critical anti-patterns, system design decisions. Always injected into Claude Code context. 232+ lines, well-structured. Updated when Claude explicitly invokes Claude Code's built-in memory tool.

**Overlap**: Heavily overlaps with LONG-tier knowledge entries, vault docs in `30-Patterns/` and `40-Procedures/`, and CLAUDE.md. MEMORY.md is the highest-visibility file and most curated. Effectively the authoritative quick-reference. However, it only exists for one project — other projects have no equivalent.

---

## 11. Messages, Audit Log, Sessions

These mechanisms have clear single purposes with no significant overlap concerns.

**`claude.messages`** (187 rows): Inter-Claude communication. task_request, status_update, question, notification, handoff, broadcast types. Low-volume, correct — inter-Claude messaging is intentional and rare.

**`claude.audit_log`** (254 rows): Immutable state machine transition records from WorkflowEngine. Every `advance_status()`, `start_work()`, `complete_work()` call writes here. Append-only, no overlap.

**`claude.sessions`** (906 rows): Session records with start/end timestamps. Central FK target for session_facts, knowledge, todos, agent_sessions. Summary field is NULL for most sessions (requires manual `/session-end`).

---

## 12. Degraded and Dead Mechanisms

| Table | Rows | Issue | Recommended Action |
|-------|------|-------|--------------------|
| `mcp_usage` | 6,965 | All rows synthetic (NULL session_id). Real usage not tracked. | Truncate. Fix or remove the logger. |
| `enforcement_log` | 1,333 | Written by archived `process_router.py`. No reader or writer exists. | Truncate. Confirm DROP after code scan. |
| `knowledge_retrieval_log` | 77 | Frozen since `process_router.py` retirement. `recall_memories()` does not log here. | Add write in `tool_recall_memories` or drop. |
| `workflow_state` | 0 | No write path in server_v2.py. | Confirm vestigial, then drop. |
| `rag_query_patterns` | 0 | Planned RAG learning system, never built. | Keep for planned feature or drop. |
| `instructions_versions` / `rules_versions` / `skills_versions` | 0 each | Versioning backfill not done. | Keep — backfill pending. |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-part2.md
