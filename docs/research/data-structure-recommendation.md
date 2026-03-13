---
projects:
- claude-family
- project-metis
tags:
- research
- data-model
- recommendation
synced: false
---

# Data Structure Research: Recommendation & Schema

Part of [data-structure-research.md](data-structure-research.md) — proposed schema, integration, migration.

---

## Proposed Schema (3 Tables)

**`claude.entity_types`**: Type registry — `type_name`, `type_schema` (JSON Schema), `embedding_template`, `display_template`.

**`claude.entities`**: Universal table — `entity_type` (FK to registry), `project_id`, `title`, `description`, `properties` (JSONB), `tags[]`, `source`, `confidence`, `embedding` (vector 1024), `search_vector` (tsvector).

**`claude.entity_relationships`**: Typed edges — `from_entity_id`, `to_entity_id`, `relationship_type`, `properties` (JSONB).

Indexes: GIN on `properties` (jsonb_path_ops), GIN on `tags`, HNSW on `embedding`, GIN on `search_vector`, B-tree on `entity_type` and `project_id`.

## Integration

| System | How |
|--------|-----|
| `recall()` RRF | Add `entity_hits` CTE alongside vault, knowledge, workfiles |
| Dossier | Remains `project_workfiles` (different concern: session-scoped) |
| `remember()` | Can route through entities with type='memory' |
| WCC | Entity search becomes a WCC source |

**One new tool**: `catalog(type, name, data, desc?)` — stores structured entities. Existing `recall()` handles retrieval via added CTE.

## Migration Path

1. Create 3 tables (additive, no breaking changes)
2. Register initial types: book, odata_entity, api_endpoint, knowledge_pattern
3. Add entity_hits CTE to recall() RRF query
4. Implement catalog() MCP tool
5. Migrate: `books` + `book_references` → entities

## Tradeoffs

- **JSONB row locking**: Concurrent field updates block. Mitigated: single-agent access.
- **GIN write overhead**: Negligible at tens of writes/day.
- **No DB-level schema**: Validate in trigger or MCP tool layer.
- **JSONB query syntax**: MCP tools abstract the `properties->>'key'` syntax.

## What NOT to Build

Apache AGE (overkill), separate embedding tables (pgvector inline sufficient), complex ontology (need 10-20 types not 827), pure EAV (condemned), per-type tables for new types (the whole point).

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: docs/research/data-structure-recommendation.md
