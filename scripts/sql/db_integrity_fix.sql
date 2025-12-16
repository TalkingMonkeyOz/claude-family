-- ============================================================
-- DATABASE INTEGRITY FIX SCRIPT
-- Claude Family System Redesign - December 2025
-- ============================================================

-- Run as: psql -U postgres -d ai_company_foundation -f db_integrity_fix.sql

BEGIN;

-- ============================================================
-- PHASE 1: Fix ON DELETE actions for usage tables
-- ============================================================

-- api_usage_data
ALTER TABLE claude_family.api_usage_data
DROP CONSTRAINT IF EXISTS api_usage_data_identity_id_fkey;

ALTER TABLE claude_family.api_usage_data
ADD CONSTRAINT api_usage_data_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- api_cost_data
ALTER TABLE claude_family.api_cost_data
DROP CONSTRAINT IF EXISTS api_cost_data_identity_id_fkey;

ALTER TABLE claude_family.api_cost_data
ADD CONSTRAINT api_cost_data_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- usage_summary
ALTER TABLE claude_family.usage_summary
DROP CONSTRAINT IF EXISTS usage_summary_identity_id_fkey;

ALTER TABLE claude_family.usage_summary
ADD CONSTRAINT usage_summary_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- budget_alerts (two FK columns)
ALTER TABLE claude_family.budget_alerts
DROP CONSTRAINT IF EXISTS budget_alerts_identity_id_fkey;

ALTER TABLE claude_family.budget_alerts
ADD CONSTRAINT budget_alerts_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

ALTER TABLE claude_family.budget_alerts
DROP CONSTRAINT IF EXISTS budget_alerts_created_by_identity_id_fkey;

ALTER TABLE claude_family.budget_alerts
ADD CONSTRAINT budget_alerts_created_by_identity_id_fkey
FOREIGN KEY (created_by_identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- usage_sync_status
ALTER TABLE claude_family.usage_sync_status
DROP CONSTRAINT IF EXISTS usage_sync_status_synced_by_identity_id_fkey;

ALTER TABLE claude_family.usage_sync_status
ADD CONSTRAINT usage_sync_status_synced_by_identity_id_fkey
FOREIGN KEY (synced_by_identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- ============================================================
-- PHASE 2: Add CHECK constraints for enum-like columns
-- ============================================================

-- shared_knowledge.knowledge_type
ALTER TABLE claude_family.shared_knowledge
DROP CONSTRAINT IF EXISTS knowledge_type_check;

ALTER TABLE claude_family.shared_knowledge
ADD CONSTRAINT knowledge_type_check CHECK (
    knowledge_type IN (
        'pattern', 'gotcha', 'bug-fix', 'architecture', 'technique',
        'best-practice', 'troubleshooting', 'process', 'configuration',
        'mcp-tool', 'mcp-server'
    )
);

-- startup_context.context_type (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'claude_family' AND table_name = 'startup_context') THEN
        ALTER TABLE claude_family.startup_context
        DROP CONSTRAINT IF EXISTS context_type_check;

        ALTER TABLE claude_family.startup_context
        ADD CONSTRAINT context_type_check CHECK (
            context_type IN ('constraint', 'preference', 'reminder', 'warning')
        );
    END IF;
END $$;

-- api_usage_data.bucket_width (if column exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'claude_family'
               AND table_name = 'api_usage_data'
               AND column_name = 'bucket_width') THEN
        ALTER TABLE claude_family.api_usage_data
        DROP CONSTRAINT IF EXISTS bucket_width_check;

        ALTER TABLE claude_family.api_usage_data
        ADD CONSTRAINT bucket_width_check CHECK (
            bucket_width IN ('1m', '1h', '1d')
        );
    END IF;
END $$;

-- usage_summary.period_type
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'claude_family'
               AND table_name = 'usage_summary'
               AND column_name = 'period_type') THEN
        ALTER TABLE claude_family.usage_summary
        DROP CONSTRAINT IF EXISTS period_type_check;

        ALTER TABLE claude_family.usage_summary
        ADD CONSTRAINT period_type_check CHECK (
            period_type IN ('daily', 'weekly', 'monthly')
        );
    END IF;
END $$;

-- ============================================================
-- PHASE 3: Create projects_registry table
-- ============================================================

CREATE TABLE IF NOT EXISTS claude_family.projects_registry (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(255) UNIQUE NOT NULL,
    project_schema VARCHAR(100),
    project_type VARCHAR(50) CHECK (project_type IN ('internal', 'work', 'personal', 'archived')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with known projects
INSERT INTO claude_family.projects_registry (project_name, project_schema, project_type, is_active)
VALUES
    ('claude-family', 'claude', 'internal', true),
    ('mission-control-web', 'claude', 'internal', true),
    ('nimbus-user-loader', 'nimbus_context', 'work', true),
    ('nimbus-import', 'nimbus_context', 'work', true),
    ('ATO-Tax-Agent', 'public', 'work', true)
ON CONFLICT (project_name) DO NOTHING;

-- ============================================================
-- PHASE 4: Create knowledge_relations junction table
-- ============================================================

CREATE TABLE IF NOT EXISTS claude_family.knowledge_relations (
    relation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_knowledge_id UUID NOT NULL,
    related_knowledge_id UUID NOT NULL,
    relation_type VARCHAR(50) CHECK (relation_type IN ('builds_on', 'contradicts', 'validates', 'related')),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_parent_knowledge
        FOREIGN KEY (parent_knowledge_id)
        REFERENCES claude_family.shared_knowledge(knowledge_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_related_knowledge
        FOREIGN KEY (related_knowledge_id)
        REFERENCES claude_family.shared_knowledge(knowledge_id)
        ON DELETE CASCADE,

    CONSTRAINT no_self_reference
        CHECK (parent_knowledge_id != related_knowledge_id),

    UNIQUE(parent_knowledge_id, related_knowledge_id)
);

-- ============================================================
-- PHASE 5: Create stored_tests table (for TDD feature)
-- ============================================================

CREATE TABLE IF NOT EXISTS claude.stored_tests (
    test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES claude.projects(project_id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    test_type VARCHAR(50) CHECK (test_type IN ('unit', 'integration', 'e2e', 'process', 'workflow')),
    test_definition JSONB NOT NULL,
    last_run_at TIMESTAMPTZ,
    last_result VARCHAR(20) CHECK (last_result IN ('pass', 'fail', 'skip', 'error')),
    run_count INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by_identity_id UUID REFERENCES claude_family.identities(identity_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_stored_tests_project ON claude.stored_tests(project_id);
CREATE INDEX IF NOT EXISTS idx_stored_tests_type ON claude.stored_tests(test_type);

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- List all FK constraints with their actions
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table,
    rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.table_schema = 'claude_family'
    AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;

-- List all CHECK constraints
SELECT
    table_name,
    constraint_name,
    check_clause
FROM information_schema.check_constraints
WHERE constraint_schema = 'claude_family'
ORDER BY table_name;

COMMIT;

-- ============================================================
-- POST-COMMIT: Show summary
-- ============================================================

\echo ''
\echo '=== DATABASE INTEGRITY FIX COMPLETE ==='
\echo ''
\echo 'Fixed:'
\echo '  - 6 FK constraints now have ON DELETE SET NULL'
\echo '  - 4 CHECK constraints added for enum columns'
\echo '  - projects_registry table created'
\echo '  - knowledge_relations junction table created'
\echo '  - stored_tests table created'
\echo ''
