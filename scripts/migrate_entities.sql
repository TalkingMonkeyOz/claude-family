-- Entity System Migration
-- Creates entity_types, entities, entity_relationships tables
-- Registers initial types and migrates books/book_references
-- Run: psql -d ai_company_foundation -f scripts/migrate_entities.sql

BEGIN;

-- ============================================================
-- 1. Create entity_types table
-- ============================================================
CREATE TABLE IF NOT EXISTS claude.entity_types (
    type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,
    json_schema JSONB NOT NULL DEFAULT '{}',
    embedding_template TEXT NOT NULL DEFAULT '{name}',
    name_property VARCHAR(100) NOT NULL DEFAULT 'name',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_types_name ON claude.entity_types(type_name);

-- ============================================================
-- 2. Create entities table
-- ============================================================
CREATE TABLE IF NOT EXISTS claude.entities (
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

CREATE INDEX IF NOT EXISTS idx_entities_type ON claude.entities(entity_type_id);
CREATE INDEX IF NOT EXISTS idx_entities_project ON claude.entities(project_id);
CREATE INDEX IF NOT EXISTS idx_entities_tags ON claude.entities USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_entities_properties ON claude.entities USING gin(properties jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_entities_search ON claude.entities USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_entities_not_archived ON claude.entities(is_archived) WHERE NOT is_archived;

-- IVFFlat index (requires rows to exist for training; create after migration data)
-- Will be created at the end of this script

-- ============================================================
-- 3. Create entity_relationships table
-- ============================================================
CREATE TABLE IF NOT EXISTS claude.entity_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID NOT NULL REFERENCES claude.entities(entity_id) ON DELETE CASCADE,
    to_entity_id UUID NOT NULL REFERENCES claude.entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    strength FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT entity_rel_no_self CHECK (from_entity_id != to_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_rel_from ON claude.entity_relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_rel_to ON claude.entity_relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_rel_type ON claude.entity_relationships(relationship_type);

-- ============================================================
-- 4. Search vector trigger
-- ============================================================
CREATE OR REPLACE FUNCTION claude.update_entity_search_vector() RETURNS trigger AS $$
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

DROP TRIGGER IF EXISTS trg_entities_sv ON claude.entities;
CREATE TRIGGER trg_entities_sv BEFORE INSERT OR UPDATE OF properties, tags
    ON claude.entities FOR EACH ROW EXECUTE FUNCTION claude.update_entity_search_vector();

-- ============================================================
-- 5. Register initial entity types
-- ============================================================
INSERT INTO claude.entity_types (type_name, display_name, description, json_schema, embedding_template, name_property)
VALUES
('book', 'Book', 'Published book for reference library',
 '{"type":"object","required":["title","author"],"properties":{"title":{"type":"string"},"author":{"type":"string"},"isbn":{"type":"string"},"year":{"type":"integer"},"topics":{"type":"array","items":{"type":"string"}},"summary":{"type":"string"}}}',
 '{title} by {author} ({year}). {summary}', 'title'),
('book_concept', 'Book Concept', 'Concept, quote, or insight from a book',
 '{"type":"object","required":["concept"],"properties":{"concept":{"type":"string"},"chapter":{"type":"string"},"page_range":{"type":"string"},"description":{"type":"string"},"quote":{"type":"string"},"book_entity_id":{"type":"string"}}}',
 '{concept}: {description}', 'concept'),
('odata_entity', 'OData Entity', 'OData entity type from a service',
 '{"type":"object","required":["name","service_url"],"properties":{"name":{"type":"string"},"service_url":{"type":"string"},"namespace":{"type":"string"},"key_properties":{"type":"array","items":{"type":"string"}},"description":{"type":"string"}}}',
 '{name} OData entity at {service_url}. {description}', 'name'),
('api_endpoint', 'API Endpoint', 'REST API endpoint',
 '{"type":"object","required":["method","path"],"properties":{"method":{"type":"string"},"path":{"type":"string"},"base_url":{"type":"string"},"description":{"type":"string"},"auth_type":{"type":"string"}}}',
 '{method} {path} - {description}', 'path'),
('knowledge_pattern', 'Knowledge Pattern', 'Reusable architectural pattern',
 '{"type":"object","required":["name"],"properties":{"name":{"type":"string"},"problem":{"type":"string"},"solution":{"type":"string"},"context":{"type":"string"},"consequences":{"type":"string"}}}',
 '{name}: {problem} -> {solution}', 'name'),
('process_model', 'Process Model', 'BPMN process model reference',
 '{"type":"object","required":["process_id","name"],"properties":{"process_id":{"type":"string"},"name":{"type":"string"},"level":{"type":"string"},"category":{"type":"string"},"file_path":{"type":"string"},"description":{"type":"string"}}}',
 '{name} ({level}) - {description}', 'name')
ON CONFLICT (type_name) DO NOTHING;

-- ============================================================
-- 6. Migrate books → entities
-- ============================================================
INSERT INTO claude.entities (entity_type_id, properties, tags, created_at, updated_at)
SELECT
    (SELECT type_id FROM claude.entity_types WHERE type_name = 'book'),
    jsonb_build_object(
        'title', b.title,
        'author', COALESCE(b.author, ''),
        'isbn', COALESCE(b.isbn, ''),
        'year', b.year,
        'summary', COALESCE(b.summary, '')
    ),
    COALESCE(b.topics, '{}'),
    b.created_at,
    COALESCE(b.updated_at, b.created_at)
FROM claude.books b
WHERE NOT EXISTS (
    SELECT 1 FROM claude.entities e
    WHERE e.entity_type_id = (SELECT type_id FROM claude.entity_types WHERE type_name = 'book')
      AND e.properties->>'title' = b.title
);

-- ============================================================
-- 7. Migrate book_references → entities
-- ============================================================
INSERT INTO claude.entities (entity_type_id, properties, tags, embedding, created_at, updated_at)
SELECT
    (SELECT type_id FROM claude.entity_types WHERE type_name = 'book_concept'),
    jsonb_build_object(
        'concept', br.concept,
        'chapter', COALESCE(br.chapter, ''),
        'page_range', COALESCE(br.page_range, ''),
        'description', COALESCE(br.description, ''),
        'quote', COALESCE(br.quote, '')
    ),
    COALESCE(br.tags, '{}'),
    br.embedding,
    br.created_at,
    br.created_at
FROM claude.book_references br
WHERE NOT EXISTS (
    SELECT 1 FROM claude.entities e
    WHERE e.entity_type_id = (SELECT type_id FROM claude.entity_types WHERE type_name = 'book_concept')
      AND e.properties->>'concept' = br.concept
);

-- ============================================================
-- 8. Create book → concept relationships
-- ============================================================
INSERT INTO claude.entity_relationships (from_entity_id, to_entity_id, relationship_type)
SELECT DISTINCT
    book_e.entity_id,
    concept_e.entity_id,
    'contains'
FROM claude.book_references br
JOIN claude.books b ON b.book_id = br.book_id
JOIN claude.entities book_e
    ON book_e.properties->>'title' = b.title
    AND book_e.entity_type_id = (SELECT type_id FROM claude.entity_types WHERE type_name = 'book')
JOIN claude.entities concept_e
    ON concept_e.properties->>'concept' = br.concept
    AND concept_e.entity_type_id = (SELECT type_id FROM claude.entity_types WHERE type_name = 'book_concept')
WHERE NOT EXISTS (
    SELECT 1 FROM claude.entity_relationships er
    WHERE er.from_entity_id = book_e.entity_id
      AND er.to_entity_id = concept_e.entity_id
);

-- ============================================================
-- 9. Register in column_registry
-- ============================================================
INSERT INTO claude.column_registry (table_name, column_name, valid_values, description)
VALUES
('entity_relationships', 'relationship_type',
 '{"contains","references","implements","extends","part_of","authored_by","documented_in","related_to"}',
 'Valid relationship types between entities')
ON CONFLICT (table_name, column_name) DO UPDATE SET valid_values = EXCLUDED.valid_values;

-- ============================================================
-- 10. IVFFlat index (needs rows for training)
-- ============================================================
-- Only create if we have enough rows with embeddings
DO $$
DECLARE
    emb_count INTEGER;
BEGIN
    SELECT count(*) INTO emb_count FROM claude.entities WHERE embedding IS NOT NULL;
    IF emb_count >= 10 THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_entities_embedding ON claude.entities USING ivfflat(embedding vector_cosine_ops) WITH (lists = 10)';
    END IF;
END $$;

COMMIT;

-- Verify migration
SELECT 'entity_types' AS table_name, count(*) AS cnt FROM claude.entity_types
UNION ALL
SELECT 'entities', count(*) FROM claude.entities
UNION ALL
SELECT 'entity_relationships', count(*) FROM claude.entity_relationships;
