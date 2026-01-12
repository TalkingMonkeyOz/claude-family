-- Config Centralization Schema (ADR-006)
-- Database as single source of truth for all configuration

-- ============================================
-- CORE TABLES
-- ============================================

-- Global configuration (key-value store)
CREATE TABLE IF NOT EXISTS claude.global_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Skills (domain expertise definitions)
CREATE TABLE IF NOT EXISTS claude.skills (
    skill_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    scope VARCHAR(20) NOT NULL CHECK (scope IN ('global', 'project_type', 'project')),
    scope_ref VARCHAR(100), -- NULL for global, project_type name, or project_id
    content TEXT NOT NULL,
    description TEXT,
    file_pattern VARCHAR(255), -- For file-triggered skills
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, scope, scope_ref)
);

-- Instructions (auto-apply .instructions.md files)
CREATE TABLE IF NOT EXISTS claude.instructions (
    instruction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL, -- e.g., 'csharp', 'wpf-ui'
    scope VARCHAR(20) NOT NULL CHECK (scope IN ('global', 'project_type', 'project')),
    scope_ref VARCHAR(100),
    applies_to TEXT NOT NULL, -- Glob pattern e.g., '**/*.cs'
    content TEXT NOT NULL,
    priority INT DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, scope, scope_ref)
);

-- Rules (enforcement rules from .claude/rules/)
CREATE TABLE IF NOT EXISTS claude.rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    scope VARCHAR(20) NOT NULL CHECK (scope IN ('global', 'project_type', 'project')),
    scope_ref VARCHAR(100),
    content TEXT NOT NULL,
    rule_type VARCHAR(50), -- 'commit', 'database', 'testing', etc.
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, scope, scope_ref)
);

-- ============================================
-- VERSION HISTORY TABLES
-- ============================================

CREATE TABLE IF NOT EXISTS claude.global_config_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES claude.global_config(config_id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    value JSONB NOT NULL,
    changed_by VARCHAR(100),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claude.skills_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID REFERENCES claude.skills(skill_id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    content TEXT NOT NULL,
    changed_by VARCHAR(100),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claude.instructions_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instruction_id UUID REFERENCES claude.instructions(instruction_id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    content TEXT NOT NULL,
    changed_by VARCHAR(100),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claude.rules_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES claude.rules(rule_id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    content TEXT NOT NULL,
    changed_by VARCHAR(100),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_skills_scope ON claude.skills(scope, scope_ref);
CREATE INDEX IF NOT EXISTS idx_instructions_scope ON claude.instructions(scope, scope_ref);
CREATE INDEX IF NOT EXISTS idx_rules_scope ON claude.rules(scope, scope_ref);
CREATE INDEX IF NOT EXISTS idx_skills_active ON claude.skills(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_instructions_active ON claude.instructions(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_rules_active ON claude.rules(is_active) WHERE is_active = true;

-- ============================================
-- HELPER FUNCTION: Get effective config with inheritance
-- ============================================

CREATE OR REPLACE FUNCTION claude.get_effective_skills(
    p_project_id UUID DEFAULT NULL,
    p_project_type VARCHAR DEFAULT NULL
) RETURNS TABLE (
    skill_id UUID,
    name VARCHAR,
    scope VARCHAR,
    content TEXT,
    effective_scope VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH ranked_skills AS (
        SELECT
            s.skill_id,
            s.name,
            s.scope,
            s.content,
            s.scope AS effective_scope,
            CASE s.scope
                WHEN 'project' THEN 1
                WHEN 'project_type' THEN 2
                WHEN 'global' THEN 3
            END as priority
        FROM claude.skills s
        WHERE s.is_active = true
          AND (
              (s.scope = 'global')
              OR (s.scope = 'project_type' AND s.scope_ref = p_project_type)
              OR (s.scope = 'project' AND s.scope_ref = p_project_id::text)
          )
    )
    SELECT DISTINCT ON (rs.name)
        rs.skill_id, rs.name, rs.scope, rs.content, rs.effective_scope
    FROM ranked_skills rs
    ORDER BY rs.name, rs.priority;
END;
$$ LANGUAGE plpgsql;
