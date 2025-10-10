-- ============================================================================
-- CLAUDE FAMILY SCHEMA - Meta-Layer for AI Assistant Coordination
-- ============================================================================
-- Purpose: Persistent identity and memory system for Claude instances
-- Database: ai_company_foundation (Diana's database)
-- Schema: claude_family (NEW - separate from projects)
-- Author: Claude Desktop & John
-- Date: 2025-10-10
-- ============================================================================

-- Connect to Diana's database
\c ai_company_foundation

-- ============================================================================
-- 1. CREATE SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS claude_family;

SET search_path TO claude_family, public;

COMMENT ON SCHEMA claude_family IS
'Meta-layer for AI assistant coordination. Contains identities, cross-project memory, and session tracking for all Claude instances (Desktop, Cursor, VS Code, etc.). Separate from project work - this is about the AI assistants themselves.';

-- ============================================================================
-- 2. CREATE TABLES
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- Table: identities
-- Purpose: Who are the Claude instances? Their roles, capabilities, traits
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS claude_family.identities (
    identity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_name VARCHAR(100) UNIQUE NOT NULL,  -- 'claude-desktop-001', 'diana', etc.
    platform VARCHAR(50) NOT NULL,  -- 'desktop', 'cursor', 'vscode', 'claude-code', 'orchestrator'
    role_description TEXT NOT NULL,  -- What is this Claude's role?
    capabilities JSONB DEFAULT '{}'::jsonb,  -- What can this Claude do?
    personality_traits JSONB DEFAULT '{}'::jsonb,  -- How does this Claude work?
    learning_style JSONB DEFAULT '{}'::jsonb,  -- Strengths, weaknesses, preferences
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'inactive', 'archived'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_identities_platform ON claude_family.identities(platform);
CREATE INDEX idx_identities_status ON claude_family.identities(status);
CREATE INDEX idx_identities_last_active ON claude_family.identities(last_active_at DESC);

COMMENT ON TABLE claude_family.identities IS 'Core identities of Claude instances. Each Claude (Desktop, Cursor, VS Code, Diana) has ONE identity that persists across all sessions and projects.';
COMMENT ON COLUMN claude_family.identities.identity_name IS 'Unique identifier like "claude-desktop-001". Stable forever.';
COMMENT ON COLUMN claude_family.identities.platform IS 'Where this Claude runs: desktop (Claude Desktop app), cursor (Cursor IDE), vscode (VS Code extension), orchestrator (Diana)';
COMMENT ON COLUMN claude_family.identities.capabilities IS 'JSONB: {"mcp_servers": [...], "can_run_commands": true, "has_own_company": true, ...}';
COMMENT ON COLUMN claude_family.identities.personality_traits IS 'JSONB: {"methodical": true, "fast_paced": false, ...}';

-- ────────────────────────────────────────────────────────────────────────────
-- Table: session_history
-- Purpose: Cross-project tracking of what each Claude did, when, where
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS claude_family.session_history (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_id UUID REFERENCES claude_family.identities(identity_id) ON DELETE CASCADE,
    project_schema VARCHAR(100),  -- 'public', 'nimbus_context', etc.
    project_name VARCHAR(200),  -- 'Nimbus User Loader', 'Tax Calculator', 'Diana AI Company', etc.
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    tasks_completed TEXT[],  -- Array of task summaries
    learnings_gained TEXT[],  -- What did this Claude learn?
    challenges_encountered TEXT[],  -- What problems arose?
    session_summary TEXT,  -- Overall what happened
    session_metadata JSONB DEFAULT '{}'::jsonb,  -- Flexible additional data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_history_identity ON claude_family.session_history(identity_id, session_start DESC);
CREATE INDEX idx_session_history_project ON claude_family.session_history(project_schema, project_name);
CREATE INDEX idx_session_history_recent ON claude_family.session_history(session_start DESC);

COMMENT ON TABLE claude_family.session_history IS 'Cross-project session tracking. Every time a Claude works on ANY project, logged here. Enables: "What did Desktop Claude do yesterday?" across all projects.';
COMMENT ON COLUMN claude_family.session_history.project_schema IS 'Which PostgreSQL schema: public (personal), nimbus_context (work), etc.';

-- ────────────────────────────────────────────────────────────────────────────
-- Table: shared_knowledge
-- Purpose: Universal patterns/learnings that apply across projects
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS claude_family.shared_knowledge (
    knowledge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learned_by_identity_id UUID REFERENCES claude_family.identities(identity_id) ON DELETE CASCADE,
    knowledge_type VARCHAR(50) NOT NULL,  -- 'pattern', 'antipattern', 'gotcha', 'technique', 'tool'
    knowledge_category VARCHAR(100),  -- 'onedrive', 'mcp', 'windows-forms', 'dotnet', 'http', etc.
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    applies_to_projects TEXT[],  -- ['all'] or ['nimbus', 'tax-calc'] - which projects is this relevant to?
    applies_to_platforms TEXT[],  -- ['all'] or ['windows', 'linux'] - platform-specific?
    confidence_level INTEGER DEFAULT 5 CHECK (confidence_level BETWEEN 1 AND 10),  -- 1=uncertain, 10=certain
    times_applied INTEGER DEFAULT 0,  -- Counter: how many times has this been successfully used?
    times_failed INTEGER DEFAULT 0,  -- Counter: how many times did this NOT work?
    code_example TEXT,  -- Optional code snippet
    related_knowledge UUID[],  -- Links to other shared_knowledge records
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_applied_at TIMESTAMP
);

CREATE INDEX idx_shared_knowledge_identity ON claude_family.shared_knowledge(learned_by_identity_id);
CREATE INDEX idx_shared_knowledge_type ON claude_family.shared_knowledge(knowledge_type, knowledge_category);
CREATE INDEX idx_shared_knowledge_confidence ON claude_family.shared_knowledge(confidence_level DESC, times_applied DESC);
CREATE INDEX idx_shared_knowledge_applies_to ON claude_family.shared_knowledge USING GIN(applies_to_projects);

COMMENT ON TABLE claude_family.shared_knowledge IS 'Universal knowledge that applies across projects. E.g., "OneDrive caches DLLs" applies to all .NET projects. NOT project-specific facts.';
COMMENT ON COLUMN claude_family.shared_knowledge.applies_to_projects IS 'Array: ["all"] = universal, or ["nimbus", "tax-calc"] = specific projects';
COMMENT ON COLUMN claude_family.shared_knowledge.confidence_level IS '1-10: How confident are we this is true? Increases with times_applied.';
COMMENT ON COLUMN claude_family.shared_knowledge.times_applied IS 'Success counter: How many times has this pattern worked?';

-- ────────────────────────────────────────────────────────────────────────────
-- Table: cross_reference_log
-- Purpose: Track when Claudes reference each other's work
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS claude_family.cross_reference_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asking_identity_id UUID REFERENCES claude_family.identities(identity_id) ON DELETE CASCADE,
    referenced_identity_id UUID REFERENCES claude_family.identities(identity_id) ON DELETE CASCADE,
    reference_type VARCHAR(50) NOT NULL,  -- 'learned_from', 'contradicts', 'builds_on', 'validates', 'questions'
    context TEXT NOT NULL,  -- What was being worked on?
    project_schema VARCHAR(100),  -- Which project was this in?
    project_name VARCHAR(200),
    reference_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cross_ref_asking ON claude_family.cross_reference_log(asking_identity_id, reference_timestamp DESC);
CREATE INDEX idx_cross_ref_referenced ON claude_family.cross_reference_log(referenced_identity_id, reference_timestamp DESC);
CREATE INDEX idx_cross_ref_type ON claude_family.cross_reference_log(reference_type);

COMMENT ON TABLE claude_family.cross_reference_log IS 'Tracks collaboration: When Claude Cursor asks "Did Desktop already do this?", logged here. Enables visibility into how Claudes coordinate.';
COMMENT ON COLUMN claude_family.cross_reference_log.reference_type IS 'learned_from (used their work), contradicts (disagrees), builds_on (extends), validates (confirms), questions (challenges)';

-- ────────────────────────────────────────────────────────────────────────────
-- Table: startup_context
-- Purpose: Critical reminders to load at Claude startup
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS claude_family.startup_context (
    context_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_id UUID REFERENCES claude_family.identities(identity_id) ON DELETE CASCADE,  -- NULL = applies to all
    context_type VARCHAR(50) NOT NULL,  -- 'constraint', 'preference', 'reminder', 'warning'
    context_text TEXT NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),  -- 1=always show, 10=rarely
    applies_to_projects TEXT[],  -- ['all'] or specific projects
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_shown_at TIMESTAMP,
    show_count INTEGER DEFAULT 0  -- How many times has this been shown?
);

CREATE INDEX idx_startup_context_identity ON claude_family.startup_context(identity_id, priority ASC);
CREATE INDEX idx_startup_context_priority ON claude_family.startup_context(priority ASC, last_shown_at DESC);
CREATE INDEX idx_startup_context_projects ON claude_family.startup_context USING GIN(applies_to_projects);

COMMENT ON TABLE claude_family.startup_context IS 'Critical context to show at Claude startup. E.g., "NEVER modify UserSDK" for all Claudes working on Nimbus.';
COMMENT ON COLUMN claude_family.startup_context.priority IS '1=always show (critical), 10=only if relevant (minor reminder)';

-- ============================================================================
-- 3. HELPER FUNCTIONS
-- ============================================================================

-- ────────────────────────────────────────────────────────────────────────────
-- Function: get_identity
-- Purpose: Load a Claude's identity by name or platform
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION claude_family.get_identity(p_identity_name VARCHAR)
RETURNS TABLE (
    identity_id UUID,
    identity_name VARCHAR,
    platform VARCHAR,
    role_description TEXT,
    capabilities JSONB,
    personality_traits JSONB,
    last_active_at TIMESTAMP
) AS $$
BEGIN
    -- Update last_active timestamp
    UPDATE claude_family.identities
    SET last_active_at = CURRENT_TIMESTAMP
    WHERE identities.identity_name = p_identity_name;

    -- Return identity
    RETURN QUERY
    SELECT
        i.identity_id,
        i.identity_name,
        i.platform,
        i.role_description,
        i.capabilities,
        i.personality_traits,
        i.last_active_at
    FROM claude_family.identities i
    WHERE i.identity_name = p_identity_name
    AND i.status = 'active';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION claude_family.get_identity IS 'Load identity and update last_active timestamp. Call at every session start.';

-- ────────────────────────────────────────────────────────────────────────────
-- Function: get_universal_knowledge
-- Purpose: Get shared knowledge that applies everywhere or to specific project
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION claude_family.get_universal_knowledge(
    p_project_name VARCHAR DEFAULT NULL,
    p_min_confidence INTEGER DEFAULT 5,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    knowledge_type VARCHAR,
    knowledge_category VARCHAR,
    title VARCHAR,
    description TEXT,
    confidence_level INTEGER,
    times_applied INTEGER,
    code_example TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sk.knowledge_type,
        sk.knowledge_category,
        sk.title,
        sk.description,
        sk.confidence_level,
        sk.times_applied,
        sk.code_example
    FROM claude_family.shared_knowledge sk
    WHERE sk.confidence_level >= p_min_confidence
    AND (
        'all' = ANY(sk.applies_to_projects)
        OR p_project_name IS NULL
        OR p_project_name = ANY(sk.applies_to_projects)
    )
    ORDER BY sk.confidence_level DESC, sk.times_applied DESC, sk.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION claude_family.get_universal_knowledge IS 'Get universal patterns/knowledge. Filters by confidence and project applicability.';

-- ────────────────────────────────────────────────────────────────────────────
-- Function: get_recent_sessions
-- Purpose: Get what a Claude (or all Claudes) did recently
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION claude_family.get_recent_sessions(
    p_identity_name VARCHAR DEFAULT NULL,
    p_days INTEGER DEFAULT 7,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    identity_name VARCHAR,
    platform VARCHAR,
    role_description TEXT,
    project_schema VARCHAR,
    project_name VARCHAR,
    session_start TIMESTAMP,
    session_end TIMESTAMP,
    tasks_completed TEXT[],
    session_summary TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.identity_name,
        i.platform,
        i.role_description,
        sh.project_schema,
        sh.project_name,
        sh.session_start,
        sh.session_end,
        sh.tasks_completed,
        sh.session_summary
    FROM claude_family.session_history sh
    JOIN claude_family.identities i ON sh.identity_id = i.identity_id
    WHERE (p_identity_name IS NULL OR i.identity_name = p_identity_name)
    AND sh.session_start >= CURRENT_TIMESTAMP - INTERVAL '1 day' * p_days
    ORDER BY sh.session_start DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION claude_family.get_recent_sessions IS 'Get recent session history. Pass identity_name for specific Claude, or NULL for all Claudes.';

-- ────────────────────────────────────────────────────────────────────────────
-- Function: log_session
-- Purpose: Log a completed session (call at end of work)
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION claude_family.log_session(
    p_identity_name VARCHAR,
    p_project_schema VARCHAR,
    p_project_name VARCHAR,
    p_session_start TIMESTAMP,
    p_session_end TIMESTAMP,
    p_tasks_completed TEXT[],
    p_learnings_gained TEXT[] DEFAULT NULL,
    p_session_summary TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_identity_id UUID;
    v_session_id UUID;
BEGIN
    -- Get identity ID
    SELECT identity_id INTO v_identity_id
    FROM claude_family.identities
    WHERE identity_name = p_identity_name;

    IF v_identity_id IS NULL THEN
        RAISE EXCEPTION 'Identity not found: %', p_identity_name;
    END IF;

    -- Insert session
    INSERT INTO claude_family.session_history (
        identity_id,
        project_schema,
        project_name,
        session_start,
        session_end,
        tasks_completed,
        learnings_gained,
        session_summary
    ) VALUES (
        v_identity_id,
        p_project_schema,
        p_project_name,
        p_session_start,
        p_session_end,
        p_tasks_completed,
        p_learnings_gained,
        p_session_summary
    )
    RETURNING session_id INTO v_session_id;

    RETURN v_session_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION claude_family.log_session IS 'Log a completed session. Returns session_id. Call at end of work session.';

-- ────────────────────────────────────────────────────────────────────────────
-- Function: get_startup_brief
-- Purpose: Generate full startup context for a Claude
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION claude_family.get_startup_brief(p_identity_name VARCHAR)
RETURNS TEXT AS $$
DECLARE
    v_identity_id UUID;
    v_identity RECORD;
    v_brief TEXT;
BEGIN
    -- Get identity
    SELECT * INTO v_identity
    FROM claude_family.identities
    WHERE identity_name = p_identity_name;

    IF v_identity.identity_id IS NULL THEN
        RETURN 'Identity not found: ' || p_identity_name;
    END IF;

    -- Build brief
    v_brief := E'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';
    v_brief := v_brief || '🤖 IDENTITY LOADED: ' || v_identity.identity_name || E'\n';
    v_brief := v_brief || E'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n';

    v_brief := v_brief || 'WHO AM I:' || E'\n';
    v_brief := v_brief || '  Platform: ' || v_identity.platform || E'\n';
    v_brief := v_brief || '  Role: ' || v_identity.role_description || E'\n\n';

    v_brief := v_brief || 'UNIVERSAL KNOWLEDGE:' || E'\n';
    v_brief := v_brief || '  (Query claude_family.get_universal_knowledge() for details)' || E'\n\n';

    v_brief := v_brief || 'RECENT SESSIONS:' || E'\n';
    v_brief := v_brief || '  (Query claude_family.get_recent_sessions(''' || p_identity_name || ''') for details)' || E'\n\n';

    v_brief := v_brief || E'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';
    v_brief := v_brief || '✅ READY TO WORK' || E'\n';
    v_brief := v_brief || E'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';

    RETURN v_brief;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION claude_family.get_startup_brief IS 'Generate formatted startup brief. Returns text ready for display. Basic version - see Python loader for full version.';

-- ============================================================================
-- 4. GRANT PERMISSIONS
-- ============================================================================

GRANT USAGE ON SCHEMA claude_family TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA claude_family TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA claude_family TO postgres;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA claude_family TO postgres;

-- ============================================================================
-- 5. SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ Claude Family Schema Created Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE 'Schema: claude_family (meta-layer for AI assistant coordination)';
    RAISE NOTICE 'Tables: identities, session_history, shared_knowledge, cross_reference_log, startup_context';
    RAISE NOTICE 'Functions: get_identity(), get_universal_knowledge(), get_recent_sessions(), log_session(), get_startup_brief()';
    RAISE NOTICE '';
    RAISE NOTICE 'Next: Run 02_seed_claude_identities.sql to create Claude instances';
    RAISE NOTICE '';
END $$;
