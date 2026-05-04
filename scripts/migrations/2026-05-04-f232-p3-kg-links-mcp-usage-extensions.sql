-- =====================================================================
-- F232.P1 / P3 — TIME × SPACE substrate
--   * knowledge.kg_links            (symbol/file/module anchoring on memories)
--   * mcp_usage extensions          (harness logging + bypass detection)
--   * mcp_usage.mcp_server          (DROP NOT NULL — harness rows have no server)
--   * claude.tool_use_metrics       (P5 nightly metrics)
-- =====================================================================
-- Purpose:
--   Phase-1 schema substrate for the Coding Intelligence Loop (F232).
--   Adds the columns + tables required by the write-time hook
--   (coding_intelligence_writetime.bpmn) and the P5 measurement
--   contract. Strictly ADDITIVE — no DROP COLUMN, no rename, no
--   destructive ALTER. Idempotent: re-running this file is a no-op.
--
-- Design baseline:
--   - workfile component=f232-coding-intelligence,
--     title="F232 architecture — TIME × SPACE axes, six-phase plan"
--     (workfile_id 4fdd80c1-…) — sections "Schema Migrations (Additive
--     Only)" and "Pain → Phase Map".
--   - workfile component=f232-coding-intelligence,
--     title="coding_intelligence_writetime.bpmn — model design draft"
--     (workfile_id 4ecd7e88-…) — section "Hook event schema".
--
-- Linked tasks: #1066 (cache helper), #1062 (P5 spec), #1063 (P6 spec).
-- BPMN: mcp-servers/bpmn-engine/processes/infrastructure/
--       coding_intelligence_writetime.bpmn (BT pending).
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. claude.knowledge.kg_links — TIME × SPACE substrate
-- ---------------------------------------------------------------------
-- Each memory carries an array of pointers to symbols, files, and modules.
-- Shape: [{"kind": "symbol"|"file"|"module", "id": "<id>" | "path": "...",
--          "weight": 0.0..1.0}, ...]
-- Empty default keeps existing rows valid; backfill is opt-in (no
-- mass UPDATE — see Memory-Update Discipline / Non-Destructive
-- Migration in storage-rules.md).
ALTER TABLE claude.knowledge
    ADD COLUMN IF NOT EXISTS kg_links JSONB DEFAULT '[]'::jsonb NOT NULL;

COMMENT ON COLUMN claude.knowledge.kg_links IS
    'F232: array of {kind, id|path, weight} pointers anchoring this memory '
    'to symbols/files/modules in the CKG. Inverse index supplied by the '
    'GIN below. Empty array means file/symbol-agnostic memory (legacy).';

-- GIN containment index — supports the write-time query
--   WHERE kg_links @> '[{"kind":"symbol","id":"…"}]'
CREATE INDEX IF NOT EXISTS idx_knowledge_kg_links_gin
    ON claude.knowledge USING gin (kg_links jsonb_path_ops);


-- ---------------------------------------------------------------------
-- 2. claude.mcp_usage extensions — harness logging + bypass detection
-- ---------------------------------------------------------------------
-- These columns let one row describe either an MCP call (existing
-- behaviour, tool_kind='mcp') or a harness call (Grep/Read/Glob/Bash/
-- Edit/Write, tool_kind='harness'). The bypass_detected / nudge_fired
-- columns power the F232.P5 measurement contract.
ALTER TABLE claude.mcp_usage
    ADD COLUMN IF NOT EXISTS tool_kind         VARCHAR(16) DEFAULT 'mcp',
    ADD COLUMN IF NOT EXISTS target_files      TEXT[],
    ADD COLUMN IF NOT EXISTS target_symbols    TEXT[],
    ADD COLUMN IF NOT EXISTS would_have_been   VARCHAR(64),
    ADD COLUMN IF NOT EXISTS bypass_detected   BOOLEAN     DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS nudge_fired       BOOLEAN     DEFAULT FALSE;

-- Harness rows have no MCP server — relax the legacy NOT NULL.
-- DO block makes the relaxation idempotent (NOT NULL may have been
-- dropped on a prior run; ALTER on an already-nullable column is fine
-- but we skip it to keep server logs clean).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_schema = 'claude'
          AND  table_name   = 'mcp_usage'
          AND  column_name  = 'mcp_server'
          AND  is_nullable  = 'NO'
    ) THEN
        ALTER TABLE claude.mcp_usage ALTER COLUMN mcp_server DROP NOT NULL;
    END IF;
END$$;

COMMENT ON COLUMN claude.mcp_usage.tool_kind IS
    'F232: ''mcp'' | ''harness'' | ''hook''. Defaults to ''mcp'' so legacy '
    'rows preserve their semantics. Harness rows record Grep/Read/Glob/'
    'Bash/Edit/Write calls for bypass-rate measurement.';
COMMENT ON COLUMN claude.mcp_usage.target_files IS
    'F232: file paths the call targeted (Edit/Write/Read/Grep). Used for '
    'symbol-anchored memory join + bypass detection.';
COMMENT ON COLUMN claude.mcp_usage.target_symbols IS
    'F232: qualified symbol names extracted from target_files at edit lines.';
COMMENT ON COLUMN claude.mcp_usage.would_have_been IS
    'F232: name of the MCP tool that would have served this harness call '
    '(e.g. Grep-on-symbol → ''find_symbol''). NULL when no equivalent.';
COMMENT ON COLUMN claude.mcp_usage.bypass_detected IS
    'F232: TRUE when would_have_been is non-null AND tool_kind=''harness''.';
COMMENT ON COLUMN claude.mcp_usage.nudge_fired IS
    'F232.P6: TRUE when the enforcement layer surfaced a nudge for this call.';

-- Composite index for P5 nightly aggregation queries.
CREATE INDEX IF NOT EXISTS idx_mcp_usage_kind_session
    ON claude.mcp_usage (tool_kind, session_id);
CREATE INDEX IF NOT EXISTS idx_mcp_usage_bypass
    ON claude.mcp_usage (bypass_detected) WHERE bypass_detected = TRUE;


-- ---------------------------------------------------------------------
-- 3. claude.tool_use_metrics — P5 nightly aggregates
-- ---------------------------------------------------------------------
-- One row per session per nightly run. Five rates per workfile
-- 4fdd80c1 § P5. raw_counts JSONB carries the numerators/denominators
-- so a dispute can re-derive any rate without re-querying mcp_usage.
CREATE TABLE IF NOT EXISTS claude.tool_use_metrics (
    metric_id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id                  UUID,
    project_id                  UUID REFERENCES claude.projects(project_id),
    computed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    window_start                TIMESTAMPTZ,
    window_end                  TIMESTAMPTZ,

    -- Five P5 rates (NUMERIC(5,4) gives 0.0000–1.0000 precision)
    bypass_rate                 NUMERIC(5,4),
    pattern_reuse_rate          NUMERIC(5,4),
    duplication_avoidance_rate  NUMERIC(5,4),
    continuity_rate             NUMERIC(5,4),
    nudge_acceptance_rate       NUMERIC(5,4),

    -- Hawthorne-control arm (P5 design-validity gate, workfile 28c68604)
    -- TRUE = nudges computed but suppressed (control); FALSE = treatment.
    hawthorne_suppressed        BOOLEAN     DEFAULT FALSE,

    raw_counts                  JSONB       DEFAULT '{}'::jsonb
);

COMMENT ON TABLE claude.tool_use_metrics IS
    'F232.P5: nightly aggregates of bypass/reuse/avoidance/continuity/'
    'nudge rates. Hawthorne-control arm flagged so before/after and '
    'treatment/control can be separated. raw_counts holds num/denom '
    'per rate for re-derivation.';

CREATE INDEX IF NOT EXISTS idx_tool_use_metrics_session
    ON claude.tool_use_metrics (session_id, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_tool_use_metrics_window
    ON claude.tool_use_metrics (window_start, window_end);


-- ---------------------------------------------------------------------
-- 4. column_registry — register the constrained columns
-- ---------------------------------------------------------------------
-- tool_kind is the only constrained field; bypass_detected and
-- nudge_fired are plain BOOLEAN. Hawthorne flag likewise BOOLEAN.
INSERT INTO claude.column_registry
    (table_name, column_name, valid_values, description, registered_at)
VALUES
    ('mcp_usage', 'tool_kind',
     ARRAY['mcp', 'harness', 'hook'],
     'F232: source of the tool call. Defaults to ''mcp''.',
     NOW())
ON CONFLICT (table_name, column_name) DO UPDATE
    SET valid_values = EXCLUDED.valid_values,
        description  = EXCLUDED.description;


-- ---------------------------------------------------------------------
-- 5. Verification (no-op SELECTs — surface the new shape after apply)
-- ---------------------------------------------------------------------
-- Run interactively after applying:
--   \d+ claude.knowledge
--   \d+ claude.mcp_usage
--   \d+ claude.tool_use_metrics
--   SELECT column_name, valid_values
--     FROM claude.column_registry
--    WHERE table_name = 'mcp_usage' AND column_name = 'tool_kind';
