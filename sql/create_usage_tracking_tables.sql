-- =====================================================
-- Anthropic Usage & Cost Tracking Schema
-- =====================================================
-- Purpose: Track API usage and costs for budget management
-- Date: 2025-11-04
-- Author: claude-code-unified
-- =====================================================

-- =====================================================
-- 1. API Usage Data (Raw token usage from Anthropic API)
-- =====================================================

CREATE TABLE IF NOT EXISTS claude_family.api_usage_data (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Time dimensions
    bucket_start_time TIMESTAMP NOT NULL,
    bucket_end_time TIMESTAMP NOT NULL,
    bucket_width VARCHAR(10) NOT NULL, -- '1m', '1h', '1d'

    -- Grouping dimensions (nullable when not grouped)
    model VARCHAR(100),
    workspace_id VARCHAR(100),
    workspace_name VARCHAR(255),
    service_tier VARCHAR(50), -- 'standard', 'batch', 'priority'
    context_window INTEGER,
    api_key_id VARCHAR(100),

    -- Token metrics
    uncached_input_tokens BIGINT DEFAULT 0,
    cached_input_tokens BIGINT DEFAULT 0,
    cache_creation_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT GENERATED ALWAYS AS (
        uncached_input_tokens + cached_input_tokens + cache_creation_tokens + output_tokens
    ) STORED,

    -- Additional usage
    web_search_count INTEGER DEFAULT 0,
    code_execution_count INTEGER DEFAULT 0,

    -- Metadata
    identity_id UUID REFERENCES claude_family.identities(identity_id),
    project_name VARCHAR(255),
    synced_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint to prevent duplicate imports
    UNIQUE (bucket_start_time, bucket_width, model, workspace_id, service_tier, context_window, api_key_id)
);

CREATE INDEX idx_usage_time ON claude_family.api_usage_data(bucket_start_time DESC);
CREATE INDEX idx_usage_model ON claude_family.api_usage_data(model);
CREATE INDEX idx_usage_workspace ON claude_family.api_usage_data(workspace_id);
CREATE INDEX idx_usage_identity ON claude_family.api_usage_data(identity_id);
CREATE INDEX idx_usage_project ON claude_family.api_usage_data(project_name);

-- =====================================================
-- 2. API Cost Data (Financial costs from Anthropic API)
-- =====================================================

CREATE TABLE IF NOT EXISTS claude_family.api_cost_data (
    cost_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Time dimension
    date DATE NOT NULL,

    -- Grouping dimensions
    workspace_id VARCHAR(100),
    workspace_name VARCHAR(255),
    description TEXT, -- e.g., "Code Execution Usage", "Token Usage"

    -- Cost in USD (stored as cents for precision)
    cost_cents BIGINT NOT NULL,
    cost_usd DECIMAL(12, 2) GENERATED ALWAYS AS (cost_cents / 100.0) STORED,

    -- Metadata
    identity_id UUID REFERENCES claude_family.identities(identity_id),
    project_name VARCHAR(255),
    synced_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint
    UNIQUE (date, workspace_id, description)
);

CREATE INDEX idx_cost_date ON claude_family.api_cost_data(date DESC);
CREATE INDEX idx_cost_workspace ON claude_family.api_cost_data(workspace_id);
CREATE INDEX idx_cost_identity ON claude_family.api_cost_data(identity_id);
CREATE INDEX idx_cost_project ON claude_family.api_cost_data(project_name);

-- =====================================================
-- 3. Usage Summary (Aggregated views for quick access)
-- =====================================================

CREATE TABLE IF NOT EXISTS claude_family.usage_summary (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Time period
    period_type VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly'
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Aggregation dimensions
    identity_id UUID REFERENCES claude_family.identities(identity_id),
    project_name VARCHAR(255),
    model VARCHAR(100),

    -- Aggregated metrics
    total_tokens BIGINT,
    total_requests INTEGER,
    total_cost_usd DECIMAL(12, 2),

    -- Breakdown
    uncached_input_tokens BIGINT,
    cached_input_tokens BIGINT,
    cache_creation_tokens BIGINT,
    output_tokens BIGINT,

    -- Cache efficiency
    cache_hit_rate DECIMAL(5, 2), -- Percentage

    -- Metadata
    generated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (period_type, period_start, period_end, identity_id, project_name, model)
);

CREATE INDEX idx_summary_period ON claude_family.usage_summary(period_start DESC, period_type);
CREATE INDEX idx_summary_identity ON claude_family.usage_summary(identity_id);
CREATE INDEX idx_summary_project ON claude_family.usage_summary(project_name);

-- =====================================================
-- 4. Budget Alerts (Threshold monitoring)
-- =====================================================

CREATE TABLE IF NOT EXISTS claude_family.budget_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Alert configuration
    alert_name VARCHAR(255) NOT NULL UNIQUE,
    alert_type VARCHAR(50) NOT NULL, -- 'daily', 'weekly', 'monthly', 'project'
    threshold_type VARCHAR(20) NOT NULL, -- 'cost', 'tokens', 'requests'
    threshold_value DECIMAL(12, 2) NOT NULL,

    -- Scope
    identity_id UUID REFERENCES claude_family.identities(identity_id),
    project_name VARCHAR(255),

    -- Current status
    current_value DECIMAL(12, 2),
    last_checked TIMESTAMP,
    threshold_exceeded BOOLEAN DEFAULT FALSE,
    times_exceeded INTEGER DEFAULT 0,

    -- Notifications
    notify_email VARCHAR(255),
    notify_slack_webhook TEXT,
    last_notified TIMESTAMP,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_identity_id UUID REFERENCES claude_family.identities(identity_id)
);

CREATE INDEX idx_alerts_active ON claude_family.budget_alerts(is_active, alert_type);
CREATE INDEX idx_alerts_identity ON claude_family.budget_alerts(identity_id);

-- =====================================================
-- 5. Sync Status (Track what's been imported)
-- =====================================================

CREATE TABLE IF NOT EXISTS claude_family.usage_sync_status (
    sync_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What was synced
    sync_type VARCHAR(20) NOT NULL, -- 'usage', 'cost'
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,

    -- Sync results
    records_imported INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,

    -- Status
    sync_status VARCHAR(20) NOT NULL, -- 'success', 'partial', 'failed'
    error_message TEXT,

    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Metadata
    synced_by_identity_id UUID REFERENCES claude_family.identities(identity_id)
);

CREATE INDEX idx_sync_status_type ON claude_family.usage_sync_status(sync_type, sync_status);
CREATE INDEX idx_sync_status_date ON claude_family.usage_sync_status(end_date DESC);

-- =====================================================
-- 6. Useful Views
-- =====================================================

-- Daily spending summary
CREATE OR REPLACE VIEW claude_family.v_daily_spending AS
SELECT
    date,
    SUM(cost_usd) as total_cost_usd,
    COUNT(DISTINCT workspace_id) as workspaces_used,
    STRING_AGG(DISTINCT workspace_name, ', ') as workspace_names
FROM claude_family.api_cost_data
GROUP BY date
ORDER BY date DESC;

-- Token usage by model (last 30 days)
CREATE OR REPLACE VIEW claude_family.v_usage_by_model AS
SELECT
    model,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens,
    SUM(uncached_input_tokens) as uncached_input,
    SUM(cached_input_tokens) as cached_input,
    SUM(output_tokens) as output,
    ROUND(
        CASE
            WHEN SUM(uncached_input_tokens + cached_input_tokens) > 0
            THEN (SUM(cached_input_tokens)::DECIMAL / SUM(uncached_input_tokens + cached_input_tokens)) * 100
            ELSE 0
        END,
        2
    ) as cache_hit_rate_percent
FROM claude_family.api_usage_data
WHERE bucket_start_time >= NOW() - INTERVAL '30 days'
GROUP BY model
ORDER BY total_tokens DESC;

-- Project spending (mapped from session history)
CREATE OR REPLACE VIEW claude_family.v_spending_by_project AS
SELECT
    project_name,
    COUNT(*) as sessions,
    SUM(total_tokens) as total_tokens,
    AVG(total_tokens) as avg_tokens_per_session
FROM claude_family.api_usage_data
WHERE project_name IS NOT NULL
GROUP BY project_name
ORDER BY total_tokens DESC;

-- Active budget alerts
CREATE OR REPLACE VIEW claude_family.v_active_alerts AS
SELECT
    alert_name,
    alert_type,
    threshold_type,
    threshold_value,
    current_value,
    ROUND((current_value / threshold_value) * 100, 1) as percent_of_threshold,
    threshold_exceeded,
    last_checked
FROM claude_family.budget_alerts
WHERE is_active = TRUE
ORDER BY percent_of_threshold DESC;

-- =====================================================
-- 7. Helper Functions
-- =====================================================

-- Function to calculate cache efficiency
CREATE OR REPLACE FUNCTION claude_family.calculate_cache_efficiency(
    p_start_date TIMESTAMP,
    p_end_date TIMESTAMP,
    p_model VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    model VARCHAR,
    total_input_tokens BIGINT,
    cached_tokens BIGINT,
    cache_hit_rate DECIMAL,
    estimated_savings_usd DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.model,
        SUM(u.uncached_input_tokens + u.cached_input_tokens) as total_input,
        SUM(u.cached_input_tokens) as cached,
        CASE
            WHEN SUM(u.uncached_input_tokens + u.cached_input_tokens) > 0
            THEN ROUND((SUM(u.cached_input_tokens)::DECIMAL / SUM(u.uncached_input_tokens + u.cached_input_tokens)) * 100, 2)
            ELSE 0
        END as hit_rate,
        -- Cached tokens cost 10% of regular tokens (approximate)
        ROUND((SUM(u.cached_input_tokens) * 0.9 * 0.003 / 1000), 2) as savings
    FROM claude_family.api_usage_data u
    WHERE u.bucket_start_time >= p_start_date
      AND u.bucket_start_time < p_end_date
      AND (p_model IS NULL OR u.model = p_model)
    GROUP BY u.model;
END;
$$ LANGUAGE plpgsql;

-- Function to check budget alerts
CREATE OR REPLACE FUNCTION claude_family.check_budget_alerts()
RETURNS TABLE (
    alert_id UUID,
    alert_name VARCHAR,
    threshold_exceeded BOOLEAN,
    current_value DECIMAL,
    threshold_value DECIMAL
) AS $$
BEGIN
    -- Update current values for all active alerts
    UPDATE claude_family.budget_alerts a
    SET
        current_value = (
            SELECT
                CASE
                    WHEN a.threshold_type = 'cost' THEN SUM(c.cost_usd)
                    WHEN a.threshold_type = 'tokens' THEN SUM(u.total_tokens)
                    WHEN a.threshold_type = 'requests' THEN COUNT(*)
                END
            FROM claude_family.api_usage_data u
            LEFT JOIN claude_family.api_cost_data c ON DATE(u.bucket_start_time) = c.date
            WHERE
                (a.alert_type = 'daily' AND DATE(u.bucket_start_time) = CURRENT_DATE)
                OR (a.alert_type = 'weekly' AND u.bucket_start_time >= DATE_TRUNC('week', CURRENT_DATE))
                OR (a.alert_type = 'monthly' AND u.bucket_start_time >= DATE_TRUNC('month', CURRENT_DATE))
                AND (a.identity_id IS NULL OR u.identity_id = a.identity_id)
                AND (a.project_name IS NULL OR u.project_name = a.project_name)
        ),
        last_checked = NOW(),
        threshold_exceeded = current_value > threshold_value,
        times_exceeded = CASE WHEN current_value > threshold_value THEN times_exceeded + 1 ELSE times_exceeded END
    WHERE a.is_active = TRUE;

    -- Return alerts that exceeded threshold
    RETURN QUERY
    SELECT
        a.alert_id,
        a.alert_name,
        a.threshold_exceeded,
        a.current_value,
        a.threshold_value
    FROM claude_family.budget_alerts a
    WHERE a.is_active = TRUE AND a.threshold_exceeded = TRUE;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 8. Grant Permissions
-- =====================================================

-- Grant access to postgres user (adjust as needed)
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA claude_family TO postgres;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA claude_family TO postgres;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA claude_family TO postgres;

-- =====================================================
-- Completed!
-- =====================================================

-- Verify tables created
SELECT tablename FROM pg_tables WHERE schemaname = 'claude_family' AND tablename LIKE '%usage%' OR tablename LIKE '%cost%' OR tablename LIKE '%budget%';
