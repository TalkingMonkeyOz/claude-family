---
projects:
- claude-family
tags:
- entity-catalog
- progressive-disclosure
- search
- browse
- patterns
---

# Entity Catalog: Search vs Browse Pattern

How to find and navigate structured reference data in the entity catalog (523+ entities across 10 types).

---

## Decision: Search or Browse?

| I want to... | Use | Tool |
|---|---|---|
| Find something specific by keyword/meaning | **Search** | `recall_entities(query)` |
| Orient to what exists (project, domain, type) | **Browse** | `explore_entities()` |
| Store new structured data | **Write** | `catalog(entity_type, properties)` |

**Rule of thumb**: "I need to find X" = search. "Show me what's here" = browse.

---

## Search: `recall_entities(query)`

RRF fusion combining vector similarity (Voyage AI embeddings) + BM25 full-text (including JSONB property content). Returns ranked results with summaries.

```
recall_entities("MaxNodeCount batch limit")  → finds Nimbus OData API (term is in gotchas)
recall_entities("authentication bearer token") → finds auth-related entities
recall_entities(query, entity_type="odata_entity", tags=["nimbus"])  → scoped search
```

Key: BM25 searches INSIDE JSONB properties (field names, gotchas, descriptions) not just display names. Use `detail='full'` to get complete properties for specific results.

---

## Browse: `explore_entities()`

Three-stage progressive disclosure — each stage costs more tokens but gives more detail.

### Stage 1: Inventory (~150 tokens)
```
explore_entities()                    → all types + counts as ASCII tree
explore_entities(tags=["nimbus"])     → scoped to nimbus entities only
```

### Stage 2: Browse (~500 tokens)
```
explore_entities(entity_type="domain_concept")           → list all domain concepts
explore_entities(entity_type="odata_entity", page=2)     → paginated OData entities
```

### Stage 3: Detail (~500-1000 tokens)
```
explore_entities(entity_id="uuid-here")  → full properties + relationships
```

Detail stage includes **relationship walking**:
- **Explicit**: reads `entity_relationships` table (both directions)
- **Implicit OData**: resolves NavigationProperty fields to catalog entities
- **Implicit domain_concept**: resolves workfile_refs and vault_refs
- **connection_summary**: quick counts by relationship type

---

## Breadcrumb Trail (How Claudes Discover This)

```
CLAUDE.md (tool index)
  → "Reference Library" row points to catalog / recall_entities / explore_entities
  → storage-rules.md has routing table ("API endpoint, schema → catalog()")
    → This vault doc (RAG-discoverable) has the full pattern
      → Tool docstrings have parameter details
```

---

## Entity Types (Current)

| Type | Count | Example |
|---|---|---|
| odata_entity | 366 | User, Agreement, ScheduleShift |
| book_concept | 46 | Chart patterns, support/resistance |
| gate_deliverable | 40 | METIS gate requirements |
| design_document | 21 | Architecture decisions |
| tool | 14 | standards_validator, job_runner |
| decision | 13 | Design session decisions |
| api_endpoint | 12 | UserSDK, Authenticate |
| domain_concept | 7 | Nimbus OData API, UserSDK |
| book | 3 | Technical Analysis of Stock Trends |
| knowledge_pattern | 1 | Patterns |

---

**Version**: 1.0
**Created**: 2026-04-07
**Updated**: 2026-04-07
**Location**: knowledge-vault/30-Patterns/entity-catalog-progressive-disclosure.md
