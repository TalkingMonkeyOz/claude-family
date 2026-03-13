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

How to implement "open topic, jot things down, file it, find it months later."

## Existing Systems

| System | Strengths | Weaknesses |
|--------|-----------|-----------|
| **Obsidian** | Excellent linking, local-first | Manual organization |
| **Notion** | Structured + unstructured | Cloud-dependent, slow |
| **Roam Research** | Maximum composability | Steep learning curve |
| **Tana** | Best PKM integration | Newer, smaller community |
| **Our workfiles** | Project-scoped, cross-session | Undiscovered, near-zero adoption |
| **Mem0** | Zero manual effort | No "dossier" concept |

## Zettelkasten Index Note Concept

The Zettelkasten method's core is the **index note** — a topic entry linking to atomic facts:

1. **Atomic notes** — One self-contained idea per note (our `remember()` does this)
2. **Unique IDs** — Permanent address for every note (our knowledge table IDs)
3. **Links** — Notes reference each other (our `auto_link`, poorly adopted)
4. **Index notes** — Top-level topic notes linking to details (the **dossier**)
5. **No hierarchy** — Find by links and semantic search, not folders

**What we're missing**: The index note. A dossier links to individual facts. Opening it shows the index + linked facts. Filing it marks complete but remains discoverable.

## PARA Method Mapping

| PARA Category | Our Implementation | Status | Purpose |
|---------------|-------------------|--------|---------|
| **Projects** | `features` + `build_tasks` | Working | Active work with deadlines |
| **Areas** | `project_workfiles` | Underused | Ongoing responsibilities, topics |
| **Resources** | `knowledge` (tier='long') | Working | Reference material, patterns |
| **Archive** | `knowledge` (tier='archived') | Working | Completed/inactive |

**Gap**: No clean "Areas" implementation. The dossier pattern fills this gap — topics you work on over time without hard deadlines.

## Implementation

Merge workfile concept with knowledge system:

```
DOSSIER (type='dossier' in knowledge table)
  ├── Links to individual knowledge entries
  ├── Status: open / active / filed / archived
  ├── Last_accessed timestamp
  └── Searchable by topic embedding

Workflow:
  open_dossier("WCC Design")
  jot("WCC Design", "Found that RRF fusion...")
  get_dossier("WCC Design")
  file_dossier("WCC Design")
  find_dossier("context assembly") → semantic search
```

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research\dossier-topic-pattern.md
