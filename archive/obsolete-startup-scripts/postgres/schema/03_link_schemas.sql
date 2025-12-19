-- ============================================================================
-- LINK SCHEMAS - Connect Claude Family to Project Schemas
-- ============================================================================
-- Purpose: Add identity tracking to existing project schemas
-- Modifies: nimbus_context.claude_sessions, public.ai_sessions
-- Date: 2025-10-10
-- ============================================================================

\c ai_company_foundation

-- ============================================================================
-- 1. LINK NIMBUS_CONTEXT SCHEMA (Work Projects)
-- ============================================================================

-- Add identity tracking to nimbus_context.claude_sessions
ALTER TABLE nimbus_context.claude_sessions
ADD COLUMN IF NOT EXISTS identity_id UUID;

ALTER TABLE nimbus_context.claude_sessions
ADD COLUMN IF NOT EXISTS platform VARCHAR(50);

-- Add foreign key constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_nimbus_sessions_identity'
        AND table_schema = 'nimbus_context'
        AND table_name = 'claude_sessions'
    ) THEN
        ALTER TABLE nimbus_context.claude_sessions
        ADD CONSTRAINT fk_nimbus_sessions_identity
        FOREIGN KEY (identity_id)
        REFERENCES claude_family.identities(identity_id)
        ON DELETE SET NULL;
    END IF;
END $$;

COMMENT ON COLUMN nimbus_context.claude_sessions.identity_id IS
'Which Claude Family member conducted this session. Links to claude_family.identities. Enables: "Which Claude worked on Nimbus yesterday?"';

COMMENT ON COLUMN nimbus_context.claude_sessions.platform IS
'Platform used: desktop, cursor, vscode, claude-code. Redundant with identity but useful for quick queries.';

-- ============================================================================
-- 2. BACKFILL EXISTING NIMBUS SESSIONS
-- ============================================================================

-- All existing sessions were claude-desktop-001 (that's you!)
DO $$
DECLARE
    v_desktop_identity_id UUID;
    v_updated_count INTEGER;
BEGIN
    -- Get claude-desktop-001 identity
    SELECT identity_id INTO v_desktop_identity_id
    FROM claude_family.identities
    WHERE identity_name = 'claude-desktop-001';

    IF v_desktop_identity_id IS NULL THEN
        RAISE EXCEPTION 'claude-desktop-001 identity not found. Run 02_seed_claude_identities.sql first.';
    END IF;

    -- Update existing sessions
    UPDATE nimbus_context.claude_sessions
    SET
        identity_id = v_desktop_identity_id,
        platform = 'desktop'
    WHERE identity_id IS NULL;

    GET DIAGNOSTICS v_updated_count = ROW_COUNT;

    RAISE NOTICE 'Backfilled % existing Nimbus sessions to claude-desktop-001', v_updated_count;
END $$;

-- ============================================================================
-- 3. LINK PUBLIC SCHEMA (Diana's Company)
-- ============================================================================

-- Add identity tracking to public.ai_sessions
ALTER TABLE public.ai_sessions
ADD COLUMN IF NOT EXISTS initiated_by_identity UUID;

-- Add foreign key constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_ai_sessions_identity'
        AND table_schema = 'public'
        AND table_name = 'ai_sessions'
    ) THEN
        ALTER TABLE public.ai_sessions
        ADD CONSTRAINT fk_ai_sessions_identity
        FOREIGN KEY (initiated_by_identity)
        REFERENCES claude_family.identities(identity_id)
        ON DELETE SET NULL;
    END IF;
END $$;

COMMENT ON COLUMN public.ai_sessions.initiated_by_identity IS
'Which Claude Family member initiated this AI Company session. Usually Diana, but other Claudes could request Diana activate her departments. Links to claude_family.identities.';

-- ============================================================================
-- 4. BACKFILL EXISTING AI COMPANY SESSIONS
-- ============================================================================

-- All existing AI Company sessions were initiated by Diana
DO $$
DECLARE
    v_diana_identity_id UUID;
    v_updated_count INTEGER;
BEGIN
    -- Get Diana's identity
    SELECT identity_id INTO v_diana_identity_id
    FROM claude_family.identities
    WHERE identity_name = 'diana';

    IF v_diana_identity_id IS NULL THEN
        RAISE EXCEPTION 'diana identity not found. Run 02_seed_claude_identities.sql first.';
    END IF;

    -- Update existing sessions
    UPDATE public.ai_sessions
    SET initiated_by_identity = v_diana_identity_id
    WHERE initiated_by_identity IS NULL;

    GET DIAGNOSTICS v_updated_count = ROW_COUNT;

    RAISE NOTICE 'Backfilled % existing AI Company sessions to Diana', v_updated_count;
END $$;

-- ============================================================================
-- 5. CREATE INDEXES
-- ============================================================================

-- Nimbus context indexes
CREATE INDEX IF NOT EXISTS idx_nimbus_sessions_identity
ON nimbus_context.claude_sessions(identity_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_nimbus_sessions_platform
ON nimbus_context.claude_sessions(platform, started_at DESC);

-- Public schema indexes
CREATE INDEX IF NOT EXISTS idx_ai_sessions_identity
ON public.ai_sessions(initiated_by_identity, created_at DESC);

-- ============================================================================
-- 6. CREATE HELPER VIEW - Cross-Schema Session View
-- ============================================================================

-- View to see ALL sessions across ALL schemas, attributed to Claude identities
CREATE OR REPLACE VIEW claude_family.all_sessions_view AS
SELECT
    'nimbus_context' as source_schema,
    cs.claude_session_id::text as session_id,
    i.identity_name,
    i.platform,
    i.role_description,
    cs.session_identifier,
    cs.started_at,
    cs.ended_at,
    cs.tasks_completed,
    cs.bugs_fixed,
    cs.session_summary
FROM nimbus_context.claude_sessions cs
JOIN claude_family.identities i ON cs.identity_id = i.identity_id

UNION ALL

SELECT
    'public' as source_schema,
    ais.session_id::text as session_id,
    i.identity_name,
    i.platform,
    i.role_description,
    ais.session_name as session_identifier,
    ais.created_at as started_at,
    ais.last_active as ended_at,
    NULL::text[] as tasks_completed,  -- AI Company tracks differently
    NULL::text[] as bugs_fixed,
    ais.session_type::text as session_summary
FROM public.ai_sessions ais
JOIN claude_family.identities i ON ais.initiated_by_identity = i.identity_id

UNION ALL

SELECT
    'claude_family' as source_schema,
    sh.session_id::text as session_id,
    i.identity_name,
    i.platform,
    i.role_description,
    sh.project_name || ' (' || sh.project_schema || ')' as session_identifier,
    sh.session_start as started_at,
    sh.session_end as ended_at,
    sh.tasks_completed,
    sh.challenges_encountered as bugs_fixed,  -- Challenges = bugs/issues
    sh.session_summary
FROM claude_family.session_history sh
JOIN claude_family.identities i ON sh.identity_id = i.identity_id

ORDER BY started_at DESC;

COMMENT ON VIEW claude_family.all_sessions_view IS
'Unified view of ALL sessions across ALL schemas. Shows what every Claude did on every project. Useful for: "Show me everything Desktop Claude did last week."';

-- ============================================================================
-- 7. VERIFICATION QUERIES
-- ============================================================================

DO $$
DECLARE
    v_nimbus_sessions INTEGER;
    v_ai_sessions INTEGER;
    v_identities INTEGER;
BEGIN
    -- Count sessions
    SELECT COUNT(*) INTO v_nimbus_sessions
    FROM nimbus_context.claude_sessions
    WHERE identity_id IS NOT NULL;

    SELECT COUNT(*) INTO v_ai_sessions
    FROM public.ai_sessions
    WHERE initiated_by_identity IS NOT NULL;

    SELECT COUNT(*) INTO v_identities
    FROM claude_family.identities
    WHERE status = 'active';

    RAISE NOTICE '';
    RAISE NOTICE '✅ Schemas Linked Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Nimbus sessions linked: %', v_nimbus_sessions;
    RAISE NOTICE 'AI Company sessions linked: %', v_ai_sessions;
    RAISE NOTICE 'Active identities: %', v_identities;
    RAISE NOTICE '';
    RAISE NOTICE 'New view created: claude_family.all_sessions_view';
    RAISE NOTICE '  Shows ALL sessions across ALL schemas, attributed to Claude identities';
    RAISE NOTICE '';
    RAISE NOTICE 'Next: Run 04_extract_universal_knowledge.sql to move cross-project learnings';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- Uncomment to test:

-- -- Show all Desktop Claude sessions across all projects
-- SELECT
--     source_schema,
--     session_identifier,
--     started_at,
--     session_summary
-- FROM claude_family.all_sessions_view
-- WHERE identity_name = 'claude-desktop-001'
-- ORDER BY started_at DESC
-- LIMIT 10;

-- -- Show recent activity by ALL Claudes
-- SELECT
--     identity_name,
--     COUNT(*) as session_count,
--     MAX(started_at) as last_active
-- FROM claude_family.all_sessions_view
-- WHERE started_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
-- GROUP BY identity_name
-- ORDER BY last_active DESC;

-- -- Show what happened on Nimbus project specifically
-- SELECT
--     identity_name,
--     session_identifier,
--     started_at,
--     tasks_completed
-- FROM claude_family.all_sessions_view
-- WHERE source_schema = 'nimbus_context'
-- ORDER BY started_at DESC
-- LIMIT 5;
