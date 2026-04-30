-- ============================================================================
-- 2026-04-30 — FB408 + FB410 — Workfile sections (body-weighted embeddings)
--                              + related_to UUID[] column
--
-- ADDITIVE migration. Re-runnable. Preserves all existing data.
--
-- FB408: Workfile embeddings are currently title-weighted (embed_text =
--   "<component> <title> <content[:500]>"), so body-buried content fails to
--   surface on body-shaped queries. Mirror the article_sections pattern: split
--   workfile content on `^## ` H2 headers, embed each section independently.
--
-- FB410: workfile_store lacks a `related_to: [workfile_id]` field. Add it so
--   sessions can express "see also" between two views of the same task.
-- ============================================================================

-- --- FB410: related_to UUID[] on project_workfiles -------------------------
ALTER TABLE claude.project_workfiles
    ADD COLUMN IF NOT EXISTS related_to UUID[] DEFAULT NULL;

COMMENT ON COLUMN claude.project_workfiles.related_to IS
    'FB410: optional array of related workfile_id UUIDs. Surfaced in '
    'workfile_read envelope as related_workfiles: [{workfile_id, component, title}].';

-- GIN index for fast membership / containment lookups (idempotent)
CREATE INDEX IF NOT EXISTS idx_project_workfiles_related_to
    ON claude.project_workfiles USING gin (related_to);


-- --- FB408: workfile_sections sibling table --------------------------------
-- Mirrors claude.article_sections shape (FB408 acceptance criterion).
-- Embedding column matches existing schema's vector(1024) type/dim.
CREATE TABLE IF NOT EXISTS claude.workfile_sections (
    section_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workfile_id     UUID NOT NULL REFERENCES claude.project_workfiles(workfile_id) ON DELETE CASCADE,
    section_order   INTEGER NOT NULL,
    section_slug    TEXT NOT NULL,
    section_title   TEXT NOT NULL,
    section_body    TEXT NOT NULL,
    embedding       vector(1024),
    embedding_model TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workfile_id, section_order)
);

COMMENT ON TABLE claude.workfile_sections IS
    'FB408: section-granular workfile embeddings. Sibling to article_sections. '
    'Body-weighted retrieval — workfile body content surfaces independent of title.';

-- Order/lookup indexes
CREATE INDEX IF NOT EXISTS idx_workfile_sections_workfile_order
    ON claude.workfile_sections (workfile_id, section_order);

-- Cosine ivfflat embedding index (matches article_sections shape)
CREATE INDEX IF NOT EXISTS idx_workfile_sections_embedding
    ON claude.workfile_sections USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
