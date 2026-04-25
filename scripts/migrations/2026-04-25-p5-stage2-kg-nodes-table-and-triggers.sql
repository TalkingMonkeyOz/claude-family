-- =====================================================================
-- P5 Stage 2: kg_nodes physical table + dual-write triggers (DISABLED)
-- =====================================================================
-- Purpose:
--   1. Create the physical claude.kg_nodes table mirroring kg_nodes_view shape.
--   2. Backfill kg_nodes_view to include knowledge_articles (Stage 1 hole).
--   3. Install AFTER INSERT/UPDATE/DELETE triggers on the 4 source tables.
--      Triggers are SHIPPED DISABLED — flag-flip is a single ALTER TABLE.
--   4. Create kg_nodes_diff_log for the row-level diff job.
--
-- Activation (Stage 2 flag-flip):
--   ALTER TABLE claude.knowledge          ENABLE TRIGGER trg_kg_sync_knowledge;
--   ALTER TABLE claude.entities           ENABLE TRIGGER trg_kg_sync_entities;
--   ALTER TABLE claude.knowledge_articles ENABLE TRIGGER trg_kg_sync_articles;
--   ALTER TABLE claude.article_sections   ENABLE TRIGGER trg_kg_sync_article_sections;
--
-- Deactivation:
--   ALTER TABLE … DISABLE TRIGGER …;     (instant, zero data loss)
--
-- Rollback:
--   DROP TRIGGER … ; DROP FUNCTION … ; DROP TABLE claude.kg_nodes;
--
-- Notes:
--   - Trigger-based dual-write is intentionally TEMPORARY (P5 only).
--     Long-term mechanism is being designed in Project Metis. After Metis
--     ships, revisit and either replace these triggers with the Metis
--     mechanism or formalise them as canonical. Tracker: task #822.
--   - Composite PK (source_table, source_id) preserves bidirectional mapping.
--   - knowledge_articles is added to both view and trigger set to close the
--     Stage 1 omission noted on 2026-04-25.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Physical kg_nodes table
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.kg_nodes (
    source_table     text          NOT NULL,
    source_id        uuid          NOT NULL,
    node_type        text          NOT NULL,
    project_id       uuid          NULL,
    title            text          NULL,
    body             text          NULL,
    tags             text[]        NULL,
    kind             varchar       NULL,
    tier             varchar       NULL,
    status           varchar       NULL,
    confidence       integer       NULL,
    access_count     integer       NULL,
    embedding        vector(1024)  NULL,
    embedding_model  text          NULL,
    created_at       timestamptz   NULL,
    updated_at       timestamptz   NULL,
    last_accessed_at timestamptz   NULL,
    synced_at        timestamptz   NOT NULL DEFAULT now(),
    PRIMARY KEY (source_table, source_id)
);

CREATE INDEX IF NOT EXISTS kg_nodes_node_type_idx     ON claude.kg_nodes (node_type);
CREATE INDEX IF NOT EXISTS kg_nodes_project_id_idx    ON claude.kg_nodes (project_id);
CREATE INDEX IF NOT EXISTS kg_nodes_updated_at_idx    ON claude.kg_nodes (updated_at DESC);
-- Embedding ANN index intentionally deferred until Stage 4 (read flip).

COMMENT ON TABLE claude.kg_nodes IS
'P5 Stage 2 (2026-04-25): physical unified knowledge-graph node store. Populated by AFTER INSERT/UPDATE/DELETE triggers on knowledge, entities, knowledge_articles, article_sections. Triggers ship DISABLED — see migration header for activation. Temporary mechanism pending Project Metis (task #822).';

-- ---------------------------------------------------------------------
-- 2. Diff log (row-level parity tracking for Stage 3 shadow read)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.kg_nodes_diff_log (
    diff_id        bigserial PRIMARY KEY,
    checked_at     timestamptz NOT NULL DEFAULT now(),
    source_table   text        NOT NULL,
    source_id      uuid        NULL,
    diff_kind      text        NOT NULL,    -- 'missing'|'extra'|'mismatch'
    column_name    text        NULL,        -- only set for 'mismatch'
    legacy_value   text        NULL,
    kg_value       text        NULL,
    notes          text        NULL
);

CREATE INDEX IF NOT EXISTS kg_nodes_diff_log_checked_at_idx
    ON claude.kg_nodes_diff_log (checked_at DESC);
CREATE INDEX IF NOT EXISTS kg_nodes_diff_log_source_idx
    ON claude.kg_nodes_diff_log (source_table, source_id);

-- ---------------------------------------------------------------------
-- 3. Update kg_nodes_view to include knowledge_articles (Stage 1 hole)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW claude.kg_nodes_view AS
-- === Memories ===
SELECT
    k.knowledge_id                              AS node_id,
    'memory'::text                              AS node_type,
    NULL::uuid                                  AS project_id,
    k.title                                     AS title,
    k.description                               AS body,
    NULL::text[]                                AS tags,
    k.knowledge_type                            AS kind,
    k.tier                                      AS tier,
    k.status                                    AS status,
    k.confidence_level                          AS confidence,
    k.access_count                              AS access_count,
    k.embedding                                 AS embedding,
    k.embedding_model                           AS embedding_model,
    (k.created_at AT TIME ZONE 'UTC')           AS created_at,
    (k.updated_at AT TIME ZONE 'UTC')           AS updated_at,
    (k.last_accessed_at AT TIME ZONE 'UTC')     AS last_accessed_at,
    'knowledge'::text                           AS source_table
FROM claude.knowledge k

UNION ALL

-- === Entities ===
SELECT
    e.entity_id                                 AS node_id,
    'entity'::text                              AS node_type,
    e.project_id                                AS project_id,
    e.display_name                              AS title,
    e.summary                                   AS body,
    e.tags                                      AS tags,
    NULL::varchar                               AS kind,
    NULL::varchar                               AS tier,
    CASE WHEN e.is_archived THEN 'archived' ELSE 'active' END::varchar AS status,
    e.confidence                                AS confidence,
    e.access_count                              AS access_count,
    e.embedding                                 AS embedding,
    e.embedding_model                           AS embedding_model,
    e.created_at                                AS created_at,
    e.updated_at                                AS updated_at,
    e.last_accessed_at                          AS last_accessed_at,
    'entities'::text                            AS source_table
FROM claude.entities e

UNION ALL

-- === Articles (parents) — added Stage 2 to close Stage 1 omission ===
SELECT
    a.article_id                                AS node_id,
    'article'::text                             AS node_type,
    NULL::uuid                                  AS project_id,
    a.title                                     AS title,
    a.abstract                                  AS body,
    a.tags                                      AS tags,
    a.article_type::varchar                     AS kind,
    NULL::varchar                               AS tier,
    a.status::varchar                           AS status,
    NULL::integer                               AS confidence,
    NULL::integer                               AS access_count,
    a.embedding                                 AS embedding,
    NULL::text                                  AS embedding_model,
    a.created_at                                AS created_at,
    a.updated_at                                AS updated_at,
    NULL::timestamptz                           AS last_accessed_at,
    'knowledge_articles'::text                  AS source_table
FROM claude.knowledge_articles a

UNION ALL

-- === Article sections (children) ===
SELECT
    s.section_id                                AS node_id,
    'article_section'::text                     AS node_type,
    NULL::uuid                                  AS project_id,
    s.title                                     AS title,
    s.body                                      AS body,
    NULL::text[]                                AS tags,
    NULL::varchar                               AS kind,
    NULL::varchar                               AS tier,
    'active'::varchar                           AS status,
    NULL::integer                               AS confidence,
    NULL::integer                               AS access_count,
    s.embedding                                 AS embedding,
    NULL::text                                  AS embedding_model,
    s.created_at                                AS created_at,
    s.updated_at                                AS updated_at,
    NULL::timestamptz                           AS last_accessed_at,
    'article_sections'::text                    AS source_table
FROM claude.article_sections s;

COMMENT ON VIEW claude.kg_nodes_view IS
'P5 Stage 2 (2026-04-25): unified projection of knowledge + entities + knowledge_articles + article_sections. Stage 1 (2026-04-24) omitted knowledge_articles — added here. Read-only; physical mirror is claude.kg_nodes (populated by triggers).';

-- ---------------------------------------------------------------------
-- 4. Trigger functions (one per source table — different column maps)
-- ---------------------------------------------------------------------

-- knowledge → kg_nodes
CREATE OR REPLACE FUNCTION claude.kg_sync_knowledge() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM claude.kg_nodes
         WHERE source_table='knowledge' AND source_id=OLD.knowledge_id;
        RETURN OLD;
    END IF;
    INSERT INTO claude.kg_nodes (
        source_table, source_id, node_type, project_id,
        title, body, tags, kind, tier, status, confidence, access_count,
        embedding, embedding_model,
        created_at, updated_at, last_accessed_at, synced_at
    ) VALUES (
        'knowledge', NEW.knowledge_id, 'memory', NULL,
        NEW.title, NEW.description, NULL,
        NEW.knowledge_type, NEW.tier, NEW.status, NEW.confidence_level, NEW.access_count,
        NEW.embedding, NEW.embedding_model,
        NEW.created_at AT TIME ZONE 'UTC',
        NEW.updated_at AT TIME ZONE 'UTC',
        NEW.last_accessed_at AT TIME ZONE 'UTC',
        now()
    )
    ON CONFLICT (source_table, source_id) DO UPDATE SET
        title=EXCLUDED.title, body=EXCLUDED.body,
        kind=EXCLUDED.kind, tier=EXCLUDED.tier, status=EXCLUDED.status,
        confidence=EXCLUDED.confidence, access_count=EXCLUDED.access_count,
        embedding=EXCLUDED.embedding, embedding_model=EXCLUDED.embedding_model,
        updated_at=EXCLUDED.updated_at, last_accessed_at=EXCLUDED.last_accessed_at,
        synced_at=now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- entities → kg_nodes
CREATE OR REPLACE FUNCTION claude.kg_sync_entities() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM claude.kg_nodes
         WHERE source_table='entities' AND source_id=OLD.entity_id;
        RETURN OLD;
    END IF;
    INSERT INTO claude.kg_nodes (
        source_table, source_id, node_type, project_id,
        title, body, tags, kind, tier, status, confidence, access_count,
        embedding, embedding_model,
        created_at, updated_at, last_accessed_at, synced_at
    ) VALUES (
        'entities', NEW.entity_id, 'entity', NEW.project_id,
        NEW.display_name, NEW.summary, NEW.tags,
        NULL, NULL,
        CASE WHEN NEW.is_archived THEN 'archived' ELSE 'active' END,
        NEW.confidence, NEW.access_count,
        NEW.embedding, NEW.embedding_model,
        NEW.created_at, NEW.updated_at, NEW.last_accessed_at,
        now()
    )
    ON CONFLICT (source_table, source_id) DO UPDATE SET
        project_id=EXCLUDED.project_id,
        title=EXCLUDED.title, body=EXCLUDED.body, tags=EXCLUDED.tags,
        status=EXCLUDED.status, confidence=EXCLUDED.confidence,
        access_count=EXCLUDED.access_count,
        embedding=EXCLUDED.embedding, embedding_model=EXCLUDED.embedding_model,
        updated_at=EXCLUDED.updated_at, last_accessed_at=EXCLUDED.last_accessed_at,
        synced_at=now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- knowledge_articles → kg_nodes
CREATE OR REPLACE FUNCTION claude.kg_sync_articles() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM claude.kg_nodes
         WHERE source_table='knowledge_articles' AND source_id=OLD.article_id;
        RETURN OLD;
    END IF;
    INSERT INTO claude.kg_nodes (
        source_table, source_id, node_type, project_id,
        title, body, tags, kind, tier, status, confidence, access_count,
        embedding, embedding_model,
        created_at, updated_at, last_accessed_at, synced_at
    ) VALUES (
        'knowledge_articles', NEW.article_id, 'article', NULL,
        NEW.title, NEW.abstract, NEW.tags,
        NEW.article_type, NULL, NEW.status,
        NULL, NULL,
        NEW.embedding, NULL,
        NEW.created_at, NEW.updated_at, NULL,
        now()
    )
    ON CONFLICT (source_table, source_id) DO UPDATE SET
        title=EXCLUDED.title, body=EXCLUDED.body, tags=EXCLUDED.tags,
        kind=EXCLUDED.kind, status=EXCLUDED.status,
        embedding=EXCLUDED.embedding,
        updated_at=EXCLUDED.updated_at,
        synced_at=now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- article_sections → kg_nodes
CREATE OR REPLACE FUNCTION claude.kg_sync_article_sections() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        DELETE FROM claude.kg_nodes
         WHERE source_table='article_sections' AND source_id=OLD.section_id;
        RETURN OLD;
    END IF;
    INSERT INTO claude.kg_nodes (
        source_table, source_id, node_type, project_id,
        title, body, tags, kind, tier, status, confidence, access_count,
        embedding, embedding_model,
        created_at, updated_at, last_accessed_at, synced_at
    ) VALUES (
        'article_sections', NEW.section_id, 'article_section', NULL,
        NEW.title, NEW.body, NULL,
        NULL, NULL, 'active',
        NULL, NULL,
        NEW.embedding, NULL,
        NEW.created_at, NEW.updated_at, NULL,
        now()
    )
    ON CONFLICT (source_table, source_id) DO UPDATE SET
        title=EXCLUDED.title, body=EXCLUDED.body,
        embedding=EXCLUDED.embedding,
        updated_at=EXCLUDED.updated_at,
        synced_at=now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 5. Triggers (SHIPPED DISABLED — flip with ALTER TABLE … ENABLE TRIGGER)
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_kg_sync_knowledge        ON claude.knowledge;
CREATE TRIGGER trg_kg_sync_knowledge
    AFTER INSERT OR UPDATE OR DELETE ON claude.knowledge
    FOR EACH ROW EXECUTE FUNCTION claude.kg_sync_knowledge();
ALTER TABLE claude.knowledge DISABLE TRIGGER trg_kg_sync_knowledge;

DROP TRIGGER IF EXISTS trg_kg_sync_entities         ON claude.entities;
CREATE TRIGGER trg_kg_sync_entities
    AFTER INSERT OR UPDATE OR DELETE ON claude.entities
    FOR EACH ROW EXECUTE FUNCTION claude.kg_sync_entities();
ALTER TABLE claude.entities DISABLE TRIGGER trg_kg_sync_entities;

DROP TRIGGER IF EXISTS trg_kg_sync_articles         ON claude.knowledge_articles;
CREATE TRIGGER trg_kg_sync_articles
    AFTER INSERT OR UPDATE OR DELETE ON claude.knowledge_articles
    FOR EACH ROW EXECUTE FUNCTION claude.kg_sync_articles();
ALTER TABLE claude.knowledge_articles DISABLE TRIGGER trg_kg_sync_articles;

DROP TRIGGER IF EXISTS trg_kg_sync_article_sections ON claude.article_sections;
CREATE TRIGGER trg_kg_sync_article_sections
    AFTER INSERT OR UPDATE OR DELETE ON claude.article_sections
    FOR EACH ROW EXECUTE FUNCTION claude.kg_sync_article_sections();
ALTER TABLE claude.article_sections DISABLE TRIGGER trg_kg_sync_article_sections;
