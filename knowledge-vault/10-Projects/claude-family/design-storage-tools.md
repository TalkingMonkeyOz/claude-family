---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- unified
synced: false
---

# Unified Storage Design — Principles and Tool Surface

**Parent**: [design-unified-storage.md](../../../docs/design-unified-storage.md)

---

## Design Principles

| Principle | Meaning |
|-----------|---------|
| Notepad first | Open topic, jot things down, come back tomorrow, file when done, find months later. |
| 3 tools, not 15 | Claude should never wonder which storage tool to use. |
| PostgreSQL is enough | pgvector + tsvector + pg_cron. No AGE, no Redis, no external vector DB. |
| Adopt proven patterns | Mem0 update-over-accumulate. SimpleMem entropy filtering. Zettelkasten index-note. |
| Fix the pipeline | Storage is fine. Extraction, dedup, consolidation, retrieval are broken. Fix those. |

---

## Tool 1: `dossier(topic, content?, action?)`

**Replaces**: stash, unstash, list_workfiles, search_workfiles, store_session_notes, all 4 activity tools, session notes files

```
dossier(topic: str, content?: str, action?: "open"|"jot"|"filed"|"list")
```

| Call | What happens | Returns |
|------|-------------|---------|
| `dossier("WCC Design")` | Open or create dossier | Index + last 3 entries |
| `dossier("WCC Design", "RRF beats naive concat")` | Jot a note | Confirmation + entry count |
| `dossier("WCC Design", action="filed")` | Mark complete | Confirmation. Still searchable. |
| `dossier(action="list")` | List open dossiers | Table with entry counts |

**Backed by**: `project_workfiles` table. `component` = topic, `title` = entry label or `_index` for metadata. One `_index` row per dossier holds status/created/summary. Embeddings generated on jot via Voyage AI.

**Why workfiles**: Best-designed mechanism (95%+ BPMN fidelity), zero adoption only because not in Core Protocol. Renaming to "dossier" and promoting fixes that.

Full dossier lifecycle design in [design-storage-dossier.md](design-storage-dossier.md).

---

## Tool 2: `remember(content, type?)`

**Replaces**: store_knowledge (legacy), partial store_session_fact

```
remember(content: str, memory_type?: "fact"|"decision"|"pattern"|"gotcha")
```

**Changes from current**:
- Remove tier routing. All entries go to `knowledge` at confidence=50.
- **Entropy gate**: check `1 - max_cosine_similarity > 0.25`. If below, UPDATE existing entry (Mem0 pattern) instead of INSERT.
- Add tsvector population on write for hybrid search.
- Quality gate stays: reject < 80 chars, reject junk patterns.
- Auto-link to open dossier if topic matches by embedding similarity to dossier `_index` rows.

**What stays unchanged**: `store_session_fact()` for session notepad (credentials, configs, decisions). That is not replaced.

---

## Tool 3: `recall(query, budget?)`

**Replaces**: recall_memories, recall_knowledge, graph_search, recall_session_fact, recall_previous_session_facts, search_workfiles

```
recall(query: str, budget?: int = 1500)
```

Single retrieval path with RRF hybrid search:

1. Generate embedding (Voyage AI) + tsquery from text
2. Parallel CTE search: vault_embeddings, knowledge, dossier entries, session facts
3. RRF fusion: `score = 1/(60 + rank_vector) + 1/(60 + rank_bm25)`
4. Budget-cap and deduplicate
5. Return ranked results with source labels `[vault]`, `[knowledge]`, `[dossier]`, `[fact]`

Full SQL pattern in [design-storage-retrieval.md](design-storage-retrieval.md).

---

## Tool 4: `forget(query_or_id)`

**New tool**. Explicitly remove outdated knowledge.

```
forget(query_or_id: str | int)
```

- Integer: archive by ID (set `tier='archived'`, `confidence=0`)
- String: search by embedding, show top 5 matches, ask confirmation before archiving
- Logs to `audit_log` for traceability

---

## Tool 5: `consolidate(scope?)`

**Replaces**: consolidate_memories, decay_knowledge

Usually automatic via pg_cron daily at 3 AM. Manual trigger for debugging.

```
consolidate(scope?: "project" | "all")
```

Operations:
1. Decay: `confidence *= 0.95` for entries not accessed in 30+ days
2. Archive: `confidence < 20` AND `last_accessed < now() - 90 days`
3. Merge near-duplicates: cosine > 0.85, merge content, keep higher confidence
4. Update dossier `_index` summaries for active dossiers

Full maintenance design in [design-storage-retrieval.md](design-storage-retrieval.md).

---

## Tool Migration Map

| Old Tool | New Tool | Notes |
|----------|----------|-------|
| `stash()` | `dossier(topic, content)` | Direct replacement |
| `unstash()` | `dossier(topic)` | Open = unstash |
| `list_workfiles()` | `dossier(action="list")` | Same data |
| `search_workfiles()` | `recall(query)` | Unified search |
| `store_session_notes()` | `dossier("session-progress", content)` | Topic dossier |
| `create_activity()` | `dossier(topic)` | Opening = activity |
| `list_activities()` | `dossier(action="list")` | Open dossiers = activities |
| `update_activity()` | `dossier(topic, action="filed")` | Filing = deactivate |
| `assemble_context()` | `recall(query)` | Unified retrieval |
| `store_knowledge()` | `remember()` | Already mapped |
| `recall_knowledge()` | `recall()` | Unified search |
| `graph_search()` | `recall()` | Graph walk removed |
| `recall_memories()` | `recall()` | Same concept |
| `consolidate_memories()` | `consolidate()` | Same concept |
| `recall_previous_session_facts()` | `recall()` | Included in unified search |

Old tools stay functional for 30 days after new tools deploy. Then soft-deprecated (log warning, still work). Then removed after 60 days.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/design-storage-tools.md
