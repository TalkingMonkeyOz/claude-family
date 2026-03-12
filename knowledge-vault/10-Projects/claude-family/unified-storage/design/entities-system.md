---
projects:
- claude-family
- project-metis
tags:
- design
- storage
- entities
- unified
synced: false
---

# Unified Storage Design — Entities System

**Parent**: [README.md](../README.md)
**Status**: Design

---

## Problem

Claude Family stores structured reference data (books, OData entities, API endpoints) in ad-hoc, type-specific tables. Adding a new entity type means designing a new table, new MCP tools, and new retrieval paths — a full feature cycle for what should be a configuration change.

**Key gap**: No general-purpose catalog for structured reference entities supporting:
- Type-extensible registration (new type = INSERT, not CREATE TABLE)
- Cross-type queries ("all API endpoints for time2work monash")
- Embedding-powered semantic retrieval within the unified `recall()` CTE
- Relationship tracking between entities (book → concept, OData entity → API endpoint)

---

## Solution: 3 Tables + 2 Tools

| Table | Purpose |
|-------|---------|
| `claude.entity_types` | Type registry: JSON Schema validation, embedding templates |
| `claude.entities` | Entity instances: JSONB properties, embeddings, tags |
| `claude.entity_relationships` | Typed links between entities |

| Tool | Purpose |
|------|---------|
| `catalog(entity_type, properties)` | Store a structured entity |
| Entity CTE in `recall()` | Retrieve entities via RRF fusion |

---

## Design Documents

| Document | Covers |
|----------|--------|
| [entities-schema.md](entities-schema.md) | DDL, indexes, triggers, type registry, initial types, extensibility |
| [entities-tools-lifecycle.md](entities-tools-lifecycle.md) | catalog() tool, recall() CTE, lifecycle, data migration |
| [entities-integration.md](entities-integration.md) | Claude Code boundaries, filing alignment, session/WCC integration |

---

## Key Design Decisions

1. **JSONB properties** — Entities use flexible `properties JSONB` validated against `entity_types.json_schema`. This avoids rigid columns per type.
2. **Embedding templates** — Each type defines how to generate embedding text via `{property}` interpolation. No code change needed per type.
3. **Generated display_name** — `GENERATED ALWAYS AS` column extracts name/title from properties for display.
4. **tsvector search** — Auto-populated trigger enables BM25 full-text search alongside vector similarity.
5. **Soft delete** — `is_archived` flag, never hard delete. Access stats tracked for lifecycle management.

---

## Implementation Sequence

1. Schema DDL + indexes + triggers (see [entities-schema.md](entities-schema.md))
2. Initial type registrations (6 types)
3. `catalog()` MCP tool in server_v2.py
4. Entity CTE added to `recall()` RRF query
5. Data migration: `claude.books` + `claude.book_references` → `claude.entities`
6. BPMN model: `entity_management.bpmn`
7. Update `cognitive_memory_retrieval.bpmn` with 5th parallel search branch

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/design/entities-system.md
