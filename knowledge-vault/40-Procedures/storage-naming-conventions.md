---
projects:
- claude-family
tags:
- storage
- naming
- conventions
- decision
---

# Storage System Naming Conventions

## The 5 Systems — Canonical Names

| System Name | Data Type | Tool(s) | DB Table | Scope |
|------------|-----------|---------|----------|-------|
| **Notepad** | Session facts | `store_session_fact()` / `recall_session_fact()` | `claude.session_facts` | This session only |
| **Memory** | Knowledge entries | `remember()` / `recall_memories()` | `claude.knowledge` | Cross-session, 3-tier |
| **Filing Cabinet** | Workfiles | `stash()` / `unstash()` | `claude.project_workfiles` | Cross-session, component-scoped |
| **Reference Library** | Entities | `catalog()` / `recall_entities()` | `claude.entities` | Permanent, structured |
| **Vault** | Documents | Write to `knowledge-vault/` | N/A (files + embeddings) | Permanent, long-form |

## Naming Rules

1. **System name** (Notepad, Memory, etc.) — used in all operational guidance and prose
2. **Data type** (session facts, knowledge, workfiles, entities, documents) — used when discussing what's stored
3. **DB table** — used only in technical/schema discussions
4. **Tool names** — never renamed, always use exact tool name in code references

## Retired Terms

| Retired Term | Was Used For | Replaced By | Why Retired |
|-------------|-------------|-------------|-------------|
| Session Facts (as system name) | Notepad system | "Notepad" | Confusing — "facts" sounds permanent, but this is session-scoped |
| Dossiers | Filing Cabinet workfiles | "Workfiles" | Unnecessary synonym, added confusion |
| Project Workfiles (as system name) | Filing Cabinet | "Filing Cabinet" | Too technical for operational guidance |
| Cognitive Memory System | Memory system | "Memory" | Feature name (F130), not user-facing |
| Knowledge Graph | Memory system | "Memory" | Pre-redesign name, now misleading (3-tier, not graph) |
| Knowledge (as system name) | Memory system | "Memory" | Confusing — conflicts with knowledge-vault |

## Why We Standardized (2026-03-22)

The coherence audit found 4+ names for several systems across 50+ docs. This caused:
- Claudes storing data in the wrong system (thinking "dossiers" and "workfiles" were different)
- Docs contradicting each other on terminology
- New Claudes unable to build a mental model of 5 systems when they had 12 names

**Design principle**: One friendly name per system (the metaphor), one technical name (the DB table). Nothing else.

## The Pattern

```
System Name (friendly)  →  used in prose and guidance
Data Type (technical)    →  used when discussing what's inside
DB Table (schema)        →  used only in SQL/schema context
Tool Name (exact)        →  used in code, never renamed
```

---

**Version**: 1.0
**Created**: 2026-03-22
**Updated**: 2026-03-22
**Location**: knowledge-vault/40-Procedures/storage-naming-conventions.md
