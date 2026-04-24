-- =====================================================================
-- P5 Stage 1: kg_nodes_view — unified virtual layer over knowledge graph
-- =====================================================================
-- Purpose: Create a read-only VIEW that unions the three knowledge graph
-- source tables (knowledge, entities, article_sections) under a common
-- shape. No data movement. No writes. Pure virtual projection.
--
-- Canary: for 7 consecutive days, assert row count parity
--   COUNT(kg_nodes_view) == COUNT(knowledge) + COUNT(entities) + COUNT(article_sections)
--
-- Rollback: DROP VIEW claude.kg_nodes_view;   (10 seconds, zero risk)
--
-- Next stages (NOT in this migration):
--   Stage 2: physical kg_nodes table + dual-write
--   Stage 3: shadow-read compare
--   Stage 4: primary read flip + legacy fallback
--   Stage 5: freeze legacy writes
-- =====================================================================

CREATE OR REPLACE VIEW claude.kg_nodes_view AS
-- === Memories (claude.knowledge) ===
SELECT
    k.knowledge_id                              AS node_id,
    'memory'::text                               AS node_type,
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
    'knowledge'::text                            AS source_table
FROM claude.knowledge k

UNION ALL

-- === Entities (claude.entities) ===
SELECT
    e.entity_id                                 AS node_id,
    'entity'::text                               AS node_type,
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
    'entities'::text                             AS source_table
FROM claude.entities e

UNION ALL

-- === Article sections (claude.article_sections) ===
SELECT
    s.section_id                                AS node_id,
    'article_section'::text                      AS node_type,
    NULL::uuid                                  AS project_id,
    s.title                                     AS title,
    s.body                                      AS body,
    NULL::text[]                                AS tags,
    NULL::varchar                               AS kind,
    NULL::varchar                               AS tier,
    'active'::varchar                            AS status,
    NULL::integer                               AS confidence,
    NULL::integer                               AS access_count,
    s.embedding                                 AS embedding,
    NULL::text                                  AS embedding_model,
    s.created_at                                AS created_at,
    s.updated_at                                AS updated_at,
    NULL::timestamptz                           AS last_accessed_at,
    'article_sections'::text                     AS source_table
FROM claude.article_sections s;

COMMENT ON VIEW claude.kg_nodes_view IS
'P5 Stage 1 (2026-04-24): read-only unified projection of knowledge + entities + article_sections. No data movement. Canary: 7-day row-count parity. Safe to DROP. See v3 deployment-strategy.';
