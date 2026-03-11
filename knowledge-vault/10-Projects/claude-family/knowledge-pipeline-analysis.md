---
projects:
- claude-family
tags:
- knowledge-pipeline
- analysis
- cognitive-memory
synced: false
---

# Knowledge Pipeline Analysis — Index

Complete analysis of knowledge ingestion, storage, retrieval, and lifecycle in
the Claude Family project. Written 2026-03-11.

## Document Map

| Part | File | Contents |
|------|------|----------|
| 1 | [[knowledge-pipeline-ingest]] | store_knowledge, remember — ingestion path and quality gates |
| 2 | [[knowledge-pipeline-recall]] | recall_knowledge, recall_memories, RAG hook injection |
| 3 | [[knowledge-pipeline-lifecycle]] | consolidate_memories, mark_knowledge_applied, session_end_hook |
| 4 | [[knowledge-pipeline-gaps]] | Gap analysis, root cause of junk storage, recommendations |

## Architecture Overview

Three storage tiers backed by a single `claude.knowledge` table (discriminated
by `tier` column), plus `claude.session_facts` for ephemeral session data.

```
INGEST                    STORE                     RETRIEVE
------                    -----                     --------
remember()           -->  session_facts (SHORT)  <-- recall_memories()
store_session_fact() -->  knowledge.tier='mid'   <-- query_knowledge_graph()
store_knowledge()    -->  knowledge.tier='long'  <-- recall_knowledge()
consolidate_memories() -- promotes SHORT->MID, MID->LONG
```

## File Locations

| Component | File | Lines |
|-----------|------|-------|
| All `tool_*` async implementations | `mcp-servers/project-tools/server.py` | ~2700 |
| MCP wrappers (thin sync layer) | `mcp-servers/project-tools/server_v2.py` | ~3800 |
| RAG injection hook | `scripts/rag_query_hook.py` | ~2240 |
| Session-end fact promotion | `scripts/session_end_hook.py` | ~200 |

`server_v2.py` imports all `tool_*` functions from `server.py` at line 3218.
The MCP-visible tool definitions in `server_v2.py` are thin sync wrappers around
the async implementations.

## Key Line Numbers (server.py)

| Function | Start Line |
|----------|-----------|
| `tool_store_knowledge` | 934 |
| `tool_recall_knowledge` | 1007 |
| `tool_recall_memories` | 1548 |
| `tool_remember` | 1791 |
| `tool_consolidate_memories` | 2008 |
| `tool_mark_knowledge_applied` | 2582 |

## Critical Findings Summary

1. **No content quality gate** — any string, including "agent1_complete", is stored
   as mid-tier knowledge with no validation.
2. **mark_knowledge_applied() is never called** — the MID->LONG promotion path
   requires `times_applied >= 3`, which never happens organically.
3. **Session_end_hook inserts embedding-less rows** — facts promoted at session end
   are invisible to all semantic search queries permanently.
4. **Periodic consolidation never runs** — Phase 2 (MID->LONG) and Phase 3
   (decay/archive) require trigger="periodic" which no code calls automatically.

---
**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/claude-family/knowledge-pipeline-analysis.md
