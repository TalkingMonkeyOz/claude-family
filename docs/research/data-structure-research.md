---
projects:
- claude-family
- project-metis
tags:
- research
- data-model
- structured-data
- jsonb
synced: false
---

# Universal vs Per-Type Data Structures — Research Index

**Question**: Should heterogeneous knowledge types (OData, books, APIs, chemical compounds) use ONE universal structure or SEPARATE per-type structures with a linking layer?

**Constraint**: Structured data and filing/retrieval MUST be ONE integrated system.

**Recommendation**: Hybrid — shared columns + JSONB `properties` + type registry + vector embedding.

---

## Research Documents

| Document | Covers |
|----------|--------|
| [data-structure-historical.md](data-structure-historical.md) | MARC, Dublin Core, FRBR, ISO 15489, Dewey/LoC |
| [data-structure-modern-db.md](data-structure-modern-db.md) | EAV+JSONB, STI, table-per-type, JSONB+GIN, Apache AGE |
| [data-structure-knowledge-graphs.md](data-structure-knowledge-graphs.md) | Wikidata, DBpedia, JSON-LD, Schema.org, RDF/OWL |
| [data-structure-ai-native.md](data-structure-ai-native.md) | Mem0, LangGraph, A-Mem, Notion, Obsidian, vector search |
| [data-structure-recommendation.md](data-structure-recommendation.md) | Schema, integration, migration, tradeoffs, tool surface |

## Comparison Matrix

| Criterion | EAV | Wide Table | Per-Type | JSONB Hybrid |
|-----------|-----|-----------|----------|-------------|
| Storage efficiency | Poor (3x) | Poor (NULLs) | Good | Good |
| Read performance | Poor | Good | Good | Good (GIN) |
| Schema flexibility | High | Low | Low | High |
| Unified search | Yes | Yes | No | Yes |
| New type cost | None | ALTER TABLE | 2-4 hrs | INSERT (min) |
| Vector search | One space | One space | Fragmented | One space |
| Tool complexity | Low (1) | Low (1) | High (N) | Low (1-2) |
| **Score (/55)** | **28** | **40** | **40** | **49** |

## Key Finding

Both independent research agents (covering 10+ angles each) converged on the same answer: **JSONB hybrid with type registry**. Validated by Wikidata (100M+ entities), Notion (200B+ rows), Dublin Core (60+ years), Mem0, and LangGraph.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: docs/research/data-structure-research.md
