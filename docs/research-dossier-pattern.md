---
projects:
- claude-family
- project-metis
tags:
- research
- dossier-pattern
- zettelkasten
synced: false
---

# The Dossier Pattern: Topic-Based Knowledge Organization

How existing systems solve the "open topic, jot things down, file it, find it months later" workflow.

## How Existing Systems Implement Topics

| System | Pattern | Strengths | Weaknesses |
|--------|---------|-----------|-----------|
| **Obsidian** | Daily notes + wiki-links | Excellent linking, local-first, plugins | Manual organization, no semantic search natively |
| **Notion** | Databases + properties | Structured + unstructured, views | Cloud-dependent, slow for large datasets |
| **Roam Research** | Block references + graph | Maximum composability | Steep learning curve, expensive |
| **Tana** | Supertags + dynamic views | Best PKM integration (Zettelkasten + GTD + PARA) | Newer, smaller community |
| **Our workfiles** | Component + title filing | Project-scoped, cross-session, pinned | Undiscovered feature, near-zero adoption |
| **Mem0** | Automatic memory extraction | Zero manual effort, semantic search | No "dossier" concept, flat memory space |

## Zettelkasten Index Note Concept

The Zettelkasten method's core is the **index note** — a topic entry that links to individual atomic facts/memories:

1. **Atomic notes** — Each memory is one self-contained idea (our `remember()` already does this)
2. **Unique IDs** — Every note has a permanent address (our knowledge table IDs)
3. **Links between notes** — Notes reference each other (our `auto_link` in `remember()`, poorly adopted)
4. **Index/entry points** — Top-level topic notes that link to details (the **dossier concept**)
5. **No rigid hierarchy** — Find by link traversal and semantic search, not folder navigation

**What we're missing**: The index note. A dossier should be an index note that links to individual facts. When you "open the dossier," you see the index. When you "jot something down," you create a fact and link it to the index. When you "file it," you mark complete but remain searchable. When you "find it later," semantic search finds the index with all linked facts.

## PARA Method Mapping

Tiago Forte's PARA (Projects, Areas, Resources, Archive) maps to our system:

| PARA Category | Our Implementation | Status | Purpose |
|---------------|-------------------|--------|---------|
| **Projects** | `features` + `build_tasks` | Working | Active work with deadlines |
| **Areas** | `project_workfiles` (component-scoped) | Underused | Ongoing responsibilities, topics |
| **Resources** | `knowledge` (tier='long') | Working | Reference material, patterns |
| **Archive** | `knowledge` (tier='archived') | Working | Completed/inactive knowledge |

**Gap**: We don't have a clean "Areas" implementation. The workfiles table was designed for this but adoption is near-zero. The dossier pattern is essentially PARA's "Areas" — topics you work on over time without a hard deadline.

## Recommended Dossier Implementation

Merge the workfile concept with the knowledge system:

```
DOSSIER (index entry in knowledge table, type='dossier')
  ├── Links to individual knowledge entries (facts, decisions, patterns)
  ├── Has status: open / active / filed / archived
  ├── Has last_accessed timestamp for surfacing
  └── Searchable by topic embedding

WORKFLOW:
  open_dossier("WCC Design") → creates/retrieves dossier index
  jot("WCC Design", "Found that RRF fusion...") → creates fact, links to dossier
  get_dossier("WCC Design") → returns index + all linked facts
  file_dossier("WCC Design") → marks as filed, remains searchable
  find_dossier("context assembly") → semantic search finds "WCC Design" dossier
```

This collapses `workfiles` and `knowledge` into one system with the dossier as the organizing concept.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research-dossier-pattern.md
