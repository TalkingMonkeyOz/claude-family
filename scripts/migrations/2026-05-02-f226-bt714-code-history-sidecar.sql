-- =====================================================================
-- F226 / BT714 — claude.work_item_code_history sidecar
-- =====================================================================
-- Purpose:
--   Linear-pattern stable-id sidecar for claude.work_items. Tracks every
--   short_code that has ever resolved to a given work_item_id, so legacy
--   identifiers (FB###/F###/BT###/RM###) keep resolving forever and
--   kind promotions don't strand prior references.
--
-- Why a sidecar (not legacy_short_code on work_items):
--   - A single row can carry one canonical W### plus 0..N legacy codes
--     (e.g. promotion of an idea→feature on the same row).
--   - UNIQUE on short_code prevents collisions across the whole namespace.
--   - Indexable, append-only audit of code history per work_item.
--
-- Provided helpers:
--   - claude.work_item_resolve_legacy(text) → UUID
--     The single source of truth for resolving any short_code (canonical
--     or legacy) to a work_item_id. Returns NULL when not found. Used by
--     commit_resolve_v2 hook + future MCP wrappers.
--
-- Idempotency:
--   - CREATE TABLE / INDEX IF NOT EXISTS, CREATE OR REPLACE FUNCTION.
--   - column_registry insert ON CONFLICT (table_name, column_name) DO UPDATE.
--   - Re-running this file produces no diffs once applied.
--
-- Backfill of existing FB###/F###/BT### codes ships in BT717.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. claude.work_item_code_history table
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claude.work_item_code_history (
    history_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_item_id    UUID NOT NULL
                         REFERENCES claude.work_items(work_item_id)
                         ON DELETE CASCADE,
    short_code      TEXT NOT NULL,
    code_kind       TEXT NOT NULL,
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to        TIMESTAMPTZ,
    notes           TEXT,
    UNIQUE (short_code),
    CONSTRAINT chk_wich_code_kind CHECK (
        code_kind IN ('canonical', 'legacy', 'historical_promotion')
    ),
    CONSTRAINT chk_wich_validity_window CHECK (
        valid_to IS NULL OR valid_to >= valid_from
    )
);

COMMENT ON TABLE claude.work_item_code_history IS
    'F226 (FB316) sidecar: every short_code that has resolved to a work_item_id. Append-only. UNIQUE(short_code) is the namespace guard. ON DELETE CASCADE because deleting a work_item invalidates all its codes.';

COMMENT ON COLUMN claude.work_item_code_history.short_code IS
    'F226: short identifier — W### canonical, or legacy FB### / F### / BT### / RM### / TODO###. Globally unique across the namespace.';

COMMENT ON COLUMN claude.work_item_code_history.code_kind IS
    'F226 code provenance: canonical = the row''s primary W### code, legacy = backfilled from a pre-F226 table, historical_promotion = inherited via kind change (idea→feature).';

COMMENT ON COLUMN claude.work_item_code_history.valid_to IS
    'F226: NULL = currently active. Non-NULL = retired (e.g. when a code is reassigned, which we do not currently allow but keep representable).';

-- ---------------------------------------------------------------------
-- 2. Indexes
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_wich_work_item
    ON claude.work_item_code_history (work_item_id);

CREATE INDEX IF NOT EXISTS idx_wich_code_kind
    ON claude.work_item_code_history (code_kind);

CREATE INDEX IF NOT EXISTS idx_wich_active
    ON claude.work_item_code_history (short_code)
    WHERE valid_to IS NULL;

-- ---------------------------------------------------------------------
-- 3. Resolver function — single source of truth for short_code → uuid
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION claude.work_item_resolve_legacy(p_short_code TEXT)
RETURNS UUID
LANGUAGE sql
STABLE
AS $$
    SELECT work_item_id
      FROM claude.work_item_code_history
     WHERE short_code = p_short_code
       AND valid_to IS NULL
     LIMIT 1
$$;

COMMENT ON FUNCTION claude.work_item_resolve_legacy(TEXT) IS
    'F226 (BT714): resolve any short_code (canonical W### or legacy FB###/F###/BT###/RM###) to its work_item_id. STABLE — safe in indexes / generated columns / WHERE clauses. Returns NULL for unknown codes.';

-- ---------------------------------------------------------------------
-- 4. column_registry row for code_kind
-- ---------------------------------------------------------------------
INSERT INTO claude.column_registry
    (id, table_name, column_name, data_type, is_nullable,
     description, valid_values, default_value, constraints)
VALUES
    (gen_random_uuid(), 'work_item_code_history', 'code_kind', 'text', FALSE,
     'F226 short_code provenance — canonical W###, legacy backfill, or kind-promotion carryover.',
     '["canonical","legacy","historical_promotion"]'::jsonb,
     NULL,
     'CHECK (code_kind IN (...)) — see chk_wich_code_kind on claude.work_item_code_history')
ON CONFLICT (table_name, column_name) DO UPDATE SET
    data_type     = EXCLUDED.data_type,
    is_nullable   = EXCLUDED.is_nullable,
    description   = EXCLUDED.description,
    valid_values  = EXCLUDED.valid_values,
    default_value = EXCLUDED.default_value,
    constraints   = EXCLUDED.constraints,
    updated_at    = now();
