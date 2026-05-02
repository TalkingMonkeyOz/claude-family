-- =====================================================================
-- F226 / BT715 + BT716 — workflow_transitions for work_items + FB446 backfill
-- =====================================================================
-- Purpose:
--   - BT716: insert claude.workflow_transitions rows for entity_type='work_items'
--     per master design §5 (22 transitions, 8 stages). Side-effects use the
--     handlers wired up in server_v2.WorkflowEngine: set_started_at,
--     set_completed_at (chains check_parent_rollup), reopen_clear_completion.
--   - BT715: idempotent backfill for FB446 — UPDATE legacy build_tasks rows
--     where completed_at IS NULL but the row is in a closed status, using
--     updated_at as a best-effort approximation. work_items is empty at this
--     point so its backfill is a no-op (BT717 backfill seeds it correctly).
--
-- Idempotency:
--   - Transitions: ON CONFLICT (entity_type, from_status, to_status) DO UPDATE
--     so re-running converges. UNIQUE constraint added below if not already
--     present (defensive — the existing schema may already have it).
--   - Backfill: WHERE completed_at IS NULL discriminator means re-running
--     does not overwrite already-populated rows.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0a. Defensive UNIQUE on (entity_type, from_status, to_status)
--     to support ON CONFLICT below. No-op if constraint already exists.
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'claude.workflow_transitions'::regclass
          AND conname = 'uq_workflow_transitions_etype_from_to'
    ) THEN
        ALTER TABLE claude.workflow_transitions
            ADD CONSTRAINT uq_workflow_transitions_etype_from_to
            UNIQUE (entity_type, from_status, to_status);
    END IF;
END$$;

-- ---------------------------------------------------------------------
-- 0b. Extend chk_wt_entity_type to permit entity_type='work_items'.
--     Re-runnable: drop+recreate is idempotent.
-- ---------------------------------------------------------------------
ALTER TABLE claude.workflow_transitions
    DROP CONSTRAINT IF EXISTS chk_wt_entity_type;
ALTER TABLE claude.workflow_transitions
    ADD CONSTRAINT chk_wt_entity_type
    CHECK (entity_type IN ('feedback','features','build_tasks','work_items'));

-- ---------------------------------------------------------------------
-- 1. workflow_transitions rows for work_items (22 allowed transitions)
-- ---------------------------------------------------------------------
INSERT INTO claude.workflow_transitions
    (entity_type, from_status, to_status, requires_condition, side_effect, description)
VALUES
    -- from raw (4)
    ('work_items', 'raw', 'triaged',     NULL, NULL,
     'Accept into backlog after initial assessment'),
    ('work_items', 'raw', 'planned',     NULL, NULL,
     'Skip triage and commit directly to plan'),
    ('work_items', 'raw', 'dropped',     NULL, 'set_completed_at',
     'Drop without triage (duplicate / out-of-scope)'),
    ('work_items', 'raw', 'parked',      NULL, NULL,
     'Defer indefinitely without triage'),

    -- from triaged (4)
    ('work_items', 'triaged', 'planned',     NULL, NULL,
     'Promote from backlog to committed plan'),
    ('work_items', 'triaged', 'in_progress', NULL, 'set_started_at',
     'Start work directly from triage'),
    ('work_items', 'triaged', 'dropped',     NULL, 'set_completed_at',
     'Drop after triage (wont_fix / duplicate)'),
    ('work_items', 'triaged', 'parked',      NULL, NULL,
     'Park triaged item for later'),

    -- from planned (4)
    ('work_items', 'planned', 'triaged',     NULL, NULL,
     'Demote back to triage if scope unclear'),
    ('work_items', 'planned', 'in_progress', NULL, 'set_started_at',
     'Start the planned work'),
    ('work_items', 'planned', 'dropped',     NULL, 'set_completed_at',
     'Drop the planned item'),
    ('work_items', 'planned', 'parked',      NULL, NULL,
     'Park planned item without dropping'),

    -- from in_progress (3)
    ('work_items', 'in_progress', 'blocked', NULL, NULL,
     'Block on external / dependency'),
    ('work_items', 'in_progress', 'done',    NULL, 'set_completed_at',
     'Positive completion (auto check_parent_rollup chain)'),
    ('work_items', 'in_progress', 'dropped', NULL, 'set_completed_at',
     'Abandon in-flight work'),

    -- from blocked (3)
    ('work_items', 'blocked', 'in_progress', NULL, 'set_started_at',
     'Resume after blocker cleared'),
    ('work_items', 'blocked', 'dropped',     NULL, 'set_completed_at',
     'Drop while blocked'),
    ('work_items', 'blocked', 'parked',      NULL, NULL,
     'Park while blocked'),

    -- from done (1)
    ('work_items', 'done', 'in_progress', NULL, 'reopen_clear_completion',
     'Reopen completed item (clears completed_at)'),

    -- from dropped (1)
    ('work_items', 'dropped', 'triaged', NULL, 'reopen_clear_completion',
     'Resurrect dropped item back to triage'),

    -- from parked (2)
    ('work_items', 'parked', 'triaged', NULL, NULL,
     'Revisit parked item'),
    ('work_items', 'parked', 'dropped', NULL, 'set_completed_at',
     'Drop parked item permanently')
ON CONFLICT (entity_type, from_status, to_status) DO UPDATE SET
    requires_condition = EXCLUDED.requires_condition,
    side_effect        = EXCLUDED.side_effect,
    description        = EXCLUDED.description;

-- ---------------------------------------------------------------------
-- 2. FB446 backfill — completed_at on legacy closed build_tasks
-- ---------------------------------------------------------------------
-- IDEMPOTENT: WHERE completed_at IS NULL guard. Re-running this leaves
-- already-populated rows untouched. Uses updated_at as best-effort
-- approximation for historical close timestamps.
-- OVERRIDE: FB446 retroactive backfill — no MCP wrapper exists for
-- back-stamping completed_at on already-closed rows; the IS NULL guard
-- and the closed-status filter make this safe + non-destructive.
UPDATE claude.build_tasks
SET    completed_at = updated_at
WHERE  status IN ('completed', 'cancelled')
  AND  completed_at IS NULL;

-- (No legacy backfill for work_items — table is empty at this point;
--  BT717 backfill will seed completed_at correctly when migrating from
--  the source tables.)
