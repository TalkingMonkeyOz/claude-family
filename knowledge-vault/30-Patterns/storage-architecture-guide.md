---
projects:
  - claude-family
tags:
  - memory
  - storage
  - architecture
  - filing-system
---

# Storage Architecture Guide

**Use this when**: You need to understand HOW our storage systems work and WHY they exist. For quick "which tool do I call?" reference, see [[memory-storage-cheat-sheet]].

---

## 5 Systems, One Integrated Design

### 1. Session Notepad (SHORT tier — ephemeral)

**What**: Key-value facts stored during a session. Credentials, endpoints, decisions, findings.
**Metaphor**: Post-it notes on your desk. Thrown away when you leave.
**Lifecycle**: Created mid-session -> injected into context on compaction -> gone after session ends (unless promoted).
**Tools**: `store_session_fact()`, `recall_session_fact()`, `list_session_facts()`

### 2. Memory (MID + LONG tiers — persistent)

**What**: Learned knowledge that accumulates over time. Patterns, gotchas, decisions.
**Metaphor**: Your professional expertise — things you've learned from experience.
**Lifecycle**: `remember()` stores to MID tier -> if accessed 5+ times over 7+ days, promoted to LONG -> if unused for 90 days, archived. Dedup/merge at 75% similarity. Auto-linking to related knowledge.

**Tiers**:
- **MID**: Working knowledge — decisions, learned facts. Default destination.
- **LONG**: Proven patterns — battle-tested gotchas, procedures. The stuff that's always true.

**Tools**: `remember()`, `recall_memories()`, `consolidate_memories()`

### 3. Workfiles — The Filing Cabinet

**What**: Component-scoped working notes that bridge sessions. The data type stored in the Filing Cabinet.
**Metaphor**: A physical filing cabinet.
- **Project** = the cabinet (which project are we in?)
- **Component** = the drawer (e.g., "auth-flow", "rag-hook", "session-continuity")
- **Title** = the file within the drawer (e.g., "approach notes", "open questions", "findings")

**Why it exists**: When you're working on a component over multiple sessions, you need persistent working context — design decisions, open questions, investigation findings. This isn't "learned knowledge" (memory) and it isn't "structured reference data" (catalog). It's your active working papers.

**Key features**: UPSERT on (project, component, title), `mode="append"` to add to existing file, `is_pinned=True` to auto-surface at session start, Voyage AI embeddings for semantic search.

**Tools**: `stash()`, `unstash()`, `list_workfiles()`, `search_workfiles()`

### 4. Entity Catalog — Structured Reference Data

**What**: Typed, schema-validated entities — OData definitions, API endpoints, design patterns, books. Each entity type has a JSON schema that validates properties on insert.
**Metaphor**: A reference library with card catalog. Each card has a standard format depending on the type (book card vs journal card vs map card).
**Why it exists**: Some knowledge is inherently structured. An OData entity has fields, types, navigation properties. An API endpoint has URL, method, parameters. Shoving this into free-text `remember()` loses the structure. The catalog preserves it and enables typed search.
**Search**: RRF fusion (Voyage AI vectors + PostgreSQL BM25 full-text) — best of both semantic and keyword matching.

**Tools**: `catalog()`, `recall_entities()`

### 5. Knowledge Vault — Long-Form Documentation

**What**: Markdown files with YAML frontmatter in an Obsidian vault. SOPs, domain knowledge, patterns, project docs.
**Metaphor**: The company knowledge base / wiki.
**Why it exists**: Some knowledge needs narrative form — procedures, architectural decisions, research findings. These are full documents, not one-liner memories or structured records.
**Search**: Voyage AI embeddings, automatic RAG injection via `rag_query_hook.py` on every prompt.
**Location**: `knowledge-vault/` with folders: 00-Inbox, 10-Projects, 20-Domains, 30-Patterns, 40-Procedures

---

## How They Fit Together

```
                    STRUCTURED                    UNSTRUCTURED
                    ----------                    ------------
Ephemeral      Session Facts (notepad)       Session Notes (progress)
(this session)      |                              |
                    | promote                      | extract
                    v                              v
Persistent     Entity Catalog <---- Memory (MID/LONG)
(cross-session)  (typed schemas)     (patterns, decisions, gotchas)
                    |                              |
                    |                              |
                    v                              v
Working        ---------- Filing Cabinet (Workfiles) ----------
Context          (project/component/title)
                                   |
                                   |
                                   v
Long-form      ---------- Knowledge Vault ----------
Documentation    (Obsidian: SOPs, research, architecture)
```

The key insight from library science research: **you need both prospective organization (filing cabinet structure) AND retrospective retrieval (semantic search)**. Our system has both — workfiles give you the filing structure, embeddings give you the search.

---

## Related Documents

- [[memory-storage-cheat-sheet]] — Quick-reference decision table (which tool when)
- [[filing-records-management-research]] — Library science research that informed this design
- [[work-context-container-synthesis]] — WCC automatic context assembly

---

**Version**: 1.1
**Created**: 2026-03-14
**Updated**: 2026-03-22
**Location**: knowledge-vault/30-Patterns/storage-architecture-guide.md
