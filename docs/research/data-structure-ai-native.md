---
projects:
- claude-family
- project-metis
tags:
- research
- data-model
- ai-memory
- mem0
synced: false
---

# Data Structure Research: AI-Native Approaches

Part of [data-structure-research.md](data-structure-research.md) — Mem0, LangGraph, A-Mem, Notion, vector search.

---

## Mem0 (48.9k GitHub Stars)

Extracts entities and relationships from conversations into triplets (subject, predicate, object). Dual storage: vector DB (embeddings) + graph DB (Neo4j for triplets).

**Key insight**: Memories are NOT typed into separate stores. All memories (facts, preferences, relationships) live in the same graph + vector space. Type is implicit in the triplet structure.

Results: 26% accuracy improvement, 91% lower latency, 90% token savings.

Conflict detection + LLM-powered resolution for contradictions — the "entropy gate" pattern we already adopted.

## LangGraph / LangChain Memory

- **Short-term**: Thread-scoped checkpoints (full state snapshots)
- **Long-term**: BaseStore with namespaced JSON documents
- Cross-session via `PostgresSaver` (PostgreSQL-backed)

**Key insight**: `BaseStore` uses namespaces (like our `entity_type`) + key-value JSON (like our `properties` JSONB). This IS the hybrid model. Industry convergence.

## A-Mem (NeurIPS 2025)

Zettelkasten-style structured notes with metadata, tags, and cross-links. Each memory has: content, metadata, tags, connections to other memories.

Essentially entities with JSONB properties + entity_relationships. Validates our proposed schema.

## Notion — 200B+ Rows on PostgreSQL

Everything is a "Block" with:
1. **UUID**: Globally unique identifier
2. **Type**: Determines rendering (paragraph, heading, to-do, database row, page)
3. **Properties**: JSONB-like attributes that persist across type changes
4. **Content pointers**: Ordered child block IDs
5. **Parent pointer**: For permissions/hierarchy

**Critical insight**: Properties are decoupled from type. Converting a to-do to a heading doesn't lose the "checked" property — it's preserved but ignored.

200B+ entities on sharded PostgreSQL. Their "database" feature = filtered views over blocks with property schemas. Very similar to our type registry.

**Proves**: The hybrid model scales massively on PostgreSQL.

## Obsidian / Dataview

YAML frontmatter (key-value metadata) + markdown content + Dataview indexing. Properties are completely free-form, no schema validation.

Works for personal use but prone to inconsistency in multi-agent systems. Validates the need for schema validation (even lightweight) in our type registry.

## Vector Search over Structured Data

**Template-based embedding** (the correct approach):
- Compose natural language from structured fields using type-specific templates
- Embed the composed text, not individual fields
- All entities in same vector space for cross-type semantic search

Example templates:
```
Book: "{title}" by {properties.author}. {description}
OData: {properties.entity_set}. Fields: {properties.fields[*].name}. {description}
API: {properties.method} {properties.url_pattern}. {description}
```

**Do NOT embed fields separately** — fragments semantic space, requires multiple lookups.

The `embedding_template` in the type registry bridges structured data and semantic search. This is the key innovation.

---

## Sources

- Mem0 Paper (arXiv 2504.19413)
- Mem0 Graph Memory docs
- LangGraph Memory docs (LangChain)
- LangGraph Long-Term Memory blog post
- A-Mem: Agentic Memory for LLM Agents (NeurIPS 2025)
- Notion: The Data Model Behind Notion (blog)
- Obsidian Dataview documentation

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: docs/research/data-structure-ai-native.md
