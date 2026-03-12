---
projects:
- claude-family
tags:
- design
- storage
- entities
- schema
synced: false
---

# Entities System — Schema & Type Registry

**Parent**: [entities-system.md](entities-system.md)

---

## Schema DDL

### entity_types — Type Registry

```sql
CREATE TABLE claude.entity_types (
    type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,
    json_schema JSONB NOT NULL DEFAULT '{}',
    -- Template for embedding text: "{title} by {author}: {summary}"
    embedding_template TEXT NOT NULL DEFAULT '{name}',
    name_property VARCHAR(100) NOT NULL DEFAULT 'name',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### entities — Entity Instances

```sql
CREATE TABLE claude.entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type_id UUID NOT NULL REFERENCES claude.entity_types(type_id),
    project_id UUID REFERENCES claude.projects(project_id),
    properties JSONB NOT NULL DEFAULT '{}',
    display_name VARCHAR(500) GENERATED ALWAYS AS (
        COALESCE(properties ->> 'name', properties ->> 'title', 'Unnamed')
    ) STORED,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1024),
    search_vector tsvector,
    confidence INTEGER DEFAULT 80,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,
    access_count INTEGER DEFAULT 0
);
```

### entity_relationships — Links Between Entities

```sql
CREATE TABLE claude.entity_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID NOT NULL REFERENCES claude.entities(entity_id) ON DELETE CASCADE,
    to_entity_id UUID NOT NULL REFERENCES claude.entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    strength FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT entity_rel_no_self CHECK (from_entity_id != to_entity_id)
);
```

Valid `relationship_type` values: `contains`, `references`, `implements`, `extends`, `part_of`, `authored_by`, `documented_in`, `related_to`.

---

## Indexes

```sql
CREATE INDEX idx_entities_type ON claude.entities(entity_type_id);
CREATE INDEX idx_entities_project ON claude.entities(project_id);
CREATE INDEX idx_entities_tags ON claude.entities USING gin(tags);
CREATE INDEX idx_entities_properties ON claude.entities USING gin(properties jsonb_path_ops);
CREATE INDEX idx_entities_embedding ON claude.entities
    USING ivfflat(embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_entities_search ON claude.entities USING gin(search_vector);
CREATE INDEX idx_entities_not_archived ON claude.entities(is_archived)
    WHERE NOT is_archived;

CREATE INDEX idx_entity_rel_from ON claude.entity_relationships(from_entity_id);
CREATE INDEX idx_entity_rel_to ON claude.entity_relationships(to_entity_id);
CREATE INDEX idx_entity_rel_type ON claude.entity_relationships(relationship_type);

CREATE INDEX idx_entity_types_name ON claude.entity_types(type_name);
```

---

## Search Vector Trigger

```sql
CREATE OR REPLACE FUNCTION update_entity_search_vector() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english',
        COALESCE(NEW.properties->>'name', '') || ' ' ||
        COALESCE(NEW.properties->>'title', '') || ' ' ||
        COALESCE(NEW.properties->>'description', '') || ' ' ||
        COALESCE(NEW.properties->>'summary', '') || ' ' ||
        COALESCE(array_to_string(NEW.tags, ' '), '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_entities_sv BEFORE INSERT OR UPDATE OF properties, tags
    ON claude.entities FOR EACH ROW EXECUTE FUNCTION update_entity_search_vector();
```

---

## Initial Type Registrations

6 types covering existing and planned entity categories:

| Type | Name Property | Embedding Template |
|------|---------------|-------------------|
| `book` | `title` | `{title} by {author} ({year}). {summary}` |
| `book_concept` | `concept` | `{concept}: {description}` |
| `odata_entity` | `name` | `{name} OData entity at {service_url}. {description}` |
| `api_endpoint` | `path` | `{method} {path} - {description}` |
| `knowledge_pattern` | `name` | `{name}: {problem} -> {solution}` |
| `process_model` | `name` | `{name} ({level}) - {description}` |

See [entities-tools-lifecycle.md](entities-tools-lifecycle.md) for the full INSERT statements.

---

## Embedding Template Interpolation

```python
def interpolate_template(template: str, properties: dict) -> str:
    """Replace {placeholders} with property values, skip missing."""
    import re
    def replacer(match):
        key = match.group(1)
        val = properties.get(key, '')
        return str(val) if val else ''
    return re.sub(r'\{(\w+)\}', replacer, template).strip()
```

---

## Extensibility

To add a new entity type (e.g., `database_table`):

```sql
INSERT INTO claude.entity_types (type_name, display_name, description,
    json_schema, embedding_template, name_property)
VALUES (
    'database_table', 'Database Table', 'PostgreSQL table definition',
    '{"type":"object","required":["table_name","schema"],
      "properties":{"table_name":{"type":"string"},
      "schema":{"type":"string"},"description":{"type":"string"}}}',
    '{schema}.{table_name}: {description}',
    'table_name'
);
```

No code changes needed. The `catalog()` tool validates against `json_schema` dynamically.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/design/entities-schema.md
