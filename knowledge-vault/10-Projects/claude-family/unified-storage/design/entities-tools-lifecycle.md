---
projects:
- claude-family
tags:
- design
- storage
- entities
- tools
synced: false
---

# Entities System — Tools, Lifecycle & Migration

**Parent**: [entities-system.md](entities-system.md)

---

## catalog() Tool

```python
def catalog(
    entity_type: str,       # e.g., 'book', 'api_endpoint'
    properties: dict,       # JSONB properties (validated against json_schema)
    project: str = "",      # Project scope (optional)
    tags: list[str] = [],   # Tags for filtering
    relationships: list[dict] = [],  # [{to_entity_id, relationship_type}]
) -> dict:
    """Store a structured entity in the catalog.

    1. Look up entity_type → get json_schema + embedding_template
    2. Validate properties against json_schema
    3. Generate embedding from template interpolation
    4. INSERT into claude.entities
    5. Create relationships if provided
    6. Return {success, entity_id, entity_type, display_name}
    """
```

### Validation

Uses `jsonschema.validate()` against the type's `json_schema`. Missing required properties are rejected with a clear error listing what's needed.

### Deduplication

Before INSERT, check for existing entities with same type + matching key properties:

```sql
SELECT entity_id FROM claude.entities
WHERE entity_type_id = %s
  AND properties @> %s  -- Contains the key properties
  AND NOT is_archived
LIMIT 1;
```

If found, UPSERT (merge properties, refresh embedding).

---

## recall() Entity CTE

Entities integrate into the unified `recall()` retrieval as an additional CTE in the RRF query:

```sql
entity_hits AS (
    SELECT
        e.entity_id::text AS id,
        'entity' AS source,
        et.type_name || ': ' || e.display_name AS title,
        COALESCE(e.properties->>'description', e.properties->>'summary',
                 jsonb_pretty(e.properties)) AS content,
        ROW_NUMBER() OVER (ORDER BY e.embedding <=> $1) AS rank_vec,
        ROW_NUMBER() OVER (
            ORDER BY ts_rank(e.search_vector, to_tsquery('english', $2)) DESC
        ) AS rank_bm25
    FROM claude.entities e
    JOIN claude.entity_types et ON e.entity_type_id = et.type_id
    WHERE NOT e.is_archived
      AND (e.embedding <=> $1 < 0.7
           OR e.search_vector @@ to_tsquery('english', $2))
    LIMIT 20
)
```

This joins the `fused` CTE alongside vault_hits, knowledge_hits, and dossier_hits:

```sql
-- Added to fused UNION ALL
UNION ALL
SELECT source, content,
    1.0/(60 + rank_vec), 1.0/(60 + rank_bm25)
FROM entity_hits
```

---

## Entity Lifecycle

### Creation Triggers

| Trigger | Action | Tool |
|---------|--------|------|
| User says "catalog this" | Explicit creation | `catalog()` |
| `store_book()` called (legacy) | Auto-creates book entity | Migration shim |
| `store_book_reference()` called | Auto-creates book_concept | Migration shim |
| Session insight extraction | Auto-catalog structured data | Future |

### Access Tracking

Every retrieval updates access stats:

```sql
UPDATE claude.entities
SET last_accessed_at = NOW(), access_count = access_count + 1
WHERE entity_id = ANY($1);
```

### Archival

Entities are archived (not deleted) when no longer relevant:

```sql
UPDATE claude.entities SET is_archived = TRUE, updated_at = NOW()
WHERE entity_id = $1;
```

---

## Initial Type INSERT Statements

```sql
INSERT INTO claude.entity_types
    (type_name, display_name, description, json_schema,
     embedding_template, name_property)
VALUES
('book', 'Book', 'Published book for reference library',
 '{"type":"object","required":["title","author"],"properties":{
   "title":{"type":"string"},"author":{"type":"string"},
   "isbn":{"type":"string"},"year":{"type":"integer"},
   "topics":{"type":"array","items":{"type":"string"}},
   "summary":{"type":"string"}}}',
 '{title} by {author} ({year}). {summary}', 'title'),

('book_concept', 'Book Concept', 'Concept, quote, or insight from a book',
 '{"type":"object","required":["concept"],"properties":{
   "concept":{"type":"string"},"chapter":{"type":"string"},
   "page_range":{"type":"string"},"description":{"type":"string"},
   "quote":{"type":"string"},
   "book_entity_id":{"type":"string"}}}',
 '{concept}: {description}', 'concept'),

('odata_entity', 'OData Entity', 'OData entity type from a service',
 '{"type":"object","required":["name","service_url"],"properties":{
   "name":{"type":"string"},"service_url":{"type":"string"},
   "namespace":{"type":"string"},
   "key_properties":{"type":"array","items":{"type":"string"}},
   "description":{"type":"string"}}}',
 '{name} OData entity at {service_url}. {description}', 'name'),

('api_endpoint', 'API Endpoint', 'REST API endpoint',
 '{"type":"object","required":["method","path"],"properties":{
   "method":{"type":"string"},"path":{"type":"string"},
   "base_url":{"type":"string"},"description":{"type":"string"},
   "auth_type":{"type":"string"}}}',
 '{method} {path} - {description}', 'path'),

('knowledge_pattern', 'Knowledge Pattern', 'Reusable architectural pattern',
 '{"type":"object","required":["name"],"properties":{
   "name":{"type":"string"},"problem":{"type":"string"},
   "solution":{"type":"string"},"context":{"type":"string"},
   "consequences":{"type":"string"}}}',
 '{name}: {problem} -> {solution}', 'name'),

('process_model', 'Process Model', 'BPMN process model reference',
 '{"type":"object","required":["process_id","name"],"properties":{
   "process_id":{"type":"string"},"name":{"type":"string"},
   "level":{"type":"string","enum":["L0","L1","L2"]},
   "category":{"type":"string"},"file_path":{"type":"string"},
   "description":{"type":"string"}}}',
 '{name} ({level}) - {description}', 'name');
```

---

## Data Migration: Books → Entities

Preserves all 3 books and 46 book_references. Run as a transaction:

```sql
BEGIN;

-- Step 1: Migrate books
INSERT INTO claude.entities (entity_type_id, properties, tags, created_at, updated_at)
SELECT
    (SELECT type_id FROM claude.entity_types WHERE type_name = 'book'),
    jsonb_build_object(
        'title', b.title, 'author', b.author, 'isbn', b.isbn,
        'year', b.year, 'summary', b.summary
    ),
    b.topics, b.created_at, b.updated_at
FROM claude.books b;

-- Step 2: Migrate book_references (preserving embeddings)
INSERT INTO claude.entities (entity_type_id, properties, tags, embedding,
                             created_at, updated_at)
SELECT
    (SELECT type_id FROM claude.entity_types WHERE type_name = 'book_concept'),
    jsonb_build_object(
        'concept', br.concept, 'chapter', br.chapter,
        'page_range', br.page_range, 'description', br.description,
        'quote', br.quote
    ),
    br.tags, br.embedding, br.created_at, br.created_at
FROM claude.book_references br;

-- Step 3: Create book → concept relationships
INSERT INTO claude.entity_relationships (from_entity_id, to_entity_id, relationship_type)
SELECT
    book_e.entity_id, concept_e.entity_id, 'contains'
FROM claude.book_references br
JOIN claude.books b ON b.book_id = br.book_id
JOIN claude.entities book_e ON book_e.properties->>'title' = b.title
    AND book_e.entity_type_id = (SELECT type_id FROM claude.entity_types
                                  WHERE type_name = 'book')
JOIN claude.entities concept_e ON concept_e.properties->>'concept' = br.concept
    AND concept_e.entity_type_id = (SELECT type_id FROM claude.entity_types
                                     WHERE type_name = 'book_concept');

COMMIT;
```

After migration, legacy `store_book()` and `store_book_reference()` route to `catalog()`.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/design/entities-tools-lifecycle.md
