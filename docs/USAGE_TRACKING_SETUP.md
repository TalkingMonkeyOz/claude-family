# Anthropic Usage & Cost Tracking System

**Version**: 1.0
**Date**: 2025-11-04
**Author**: claude-code-unified

---

## 🎯 Purpose

Track your Anthropic API usage and costs to:
- **Prevent budget overruns** - Get alerts before hitting limits
- **Identify expensive operations** - See which projects/models cost the most
- **Optimize cache usage** - Monitor cache hit rates to reduce costs
- **Track project spending** - Attribute costs to specific projects
- **Prevent crashes** - Catch runaway processes before they drain your budget

---

## 📋 What Was Built

### 1. Database Schema (`sql/create_usage_tracking_tables.sql`)

Five tables to track everything:
- **`api_usage_data`** - Raw token usage from Anthropic API
- **`api_cost_data`** - Financial costs in USD
- **`budget_alerts`** - Configurable spending thresholds
- **`usage_sync_status`** - Tracks what's been imported
- Plus helper views and functions

### 2. Sync Script (`scripts/sync_anthropic_usage.py`)

Fetches data from Anthropic's API:
- Usage endpoint: `/v1/organizations/usage_report/messages`
- Cost endpoint: `/v1/organizations/cost_report`
- Incremental sync (only fetches new data)
- Duplicate prevention (won't re-import same data)
- Error logging and retry support

### 3. Viewer Console (`scripts/view_usage.py`)

Interactive console interface:
- **`summary`** - Overall spending & token usage
- **`daily`** - Daily breakdown of costs
- **`models`** - Usage by model (with cache hit rates!)
- **`projects`** - Spending by project
- **`alerts`** - Budget alert status
- **`export`** - Export to CSV for Excel/analysis

### 4. Automated Sync (Cron Job)

Registered in `ai_cron_jobs` table:
- Runs daily
- Fetches last 7 days of data
- Auto-retries on failure
- Logs all sync attempts

---

## 🚀 Setup Instructions

### Step 1: Get Your Admin API Key

1. Go to https://console.anthropic.com/settings/keys
2. Create a **new Admin API key** (starts with `sk-ant-admin...`)
3. **IMPORTANT**: Regular API keys (sk-ant-api...) won't work!
4. Copy the key

### Step 2: Set Environment Variable

**Windows (PowerShell)**:
```powershell
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_ADMIN_API_KEY', 'sk-ant-admin-...', 'User')
```

**Or add to `.env` file**:
```bash
# C:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace\.env
ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-your-key-here
```

### Step 3: Create Database Tables

Tables are already created! But if you need to recreate them:

```sql
-- Via PostgreSQL MCP
SELECT * FROM claude_family.api_usage_data LIMIT 1;
SELECT * FROM claude_family.api_cost_data LIMIT 1;
SELECT * FROM claude_family.budget_alerts;
```

### Step 4: Run Initial Sync

```bash
cd C:\Projects\claude-family
python scripts/sync_anthropic_usage.py --days 30
```

This will:
- Fetch last 30 days of usage data
- Fetch last 30 days of cost data
- Import into PostgreSQL
- Log sync status

**Expected output**:
```
================================================================================
🔄 Anthropic Usage & Cost Sync
================================================================================
✅ Admin API key loaded (starts with: sk-ant-admin...)
✅ Connected to PostgreSQL

📊 Syncing Usage Data...
   Date range: 2025-10-05 to 2025-11-04
   Fetching usage data (page: first)...
   Retrieved 30 records
   Total records fetched: 30
   ✅ Imported: 30, Skipped (duplicates): 0

💰 Syncing Cost Data...
   Date range: 2025-10-05 to 2025-11-04
   Fetching cost data (page: first)...
   Retrieved 30 records
   Total records fetched: 30
   ✅ Imported: 30, Updated/Skipped: 0

================================================================================
✅ Sync completed successfully!
================================================================================
```

### Step 5: View Your Data

```bash
# Overall summary
python scripts/view_usage.py

# Daily breakdown
python scripts/view_usage.py daily --days 30

# Usage by model
python scripts/view_usage.py models

# Usage by project
python scripts/view_usage.py projects

# Budget alerts
python scripts/view_usage.py alerts

# Export to CSV
python scripts/view_usage.py export --output my_usage.csv
```

---

## 📊 Understanding the Data

### Summary View

Shows:
- **Total Spending** (all time)
- **Recent costs** (today, 7 days, 30 days)
- **Token counts** (uncached, cached, output)
- **Cache hit rate** - Higher is better! (saves money)

**Example**:
```
================================================================================
                    📊 USAGE & COST SUMMARY
================================================================================

💰 COST SUMMARY
  Total Spending (All Time).................... $125.48
  Today.......................................... $2.15
  Last 7 Days.................................... $18.92
  Last 30 Days................................... $98.23
  Days Tracked................................... 45
  Tracking Since................................. 2025-09-20

🎯 TOKEN USAGE (Last 30 Days)
  Total Tokens................................... 15,234,567
  Uncached Input Tokens.......................... 8,123,456
  Cached Input Tokens............................ 4,567,890
  Output Tokens.................................. 2,543,221
  Total Requests................................. 1,234
  Cache Hit Rate................................. 36.0%
```

### Models View

Shows usage by model with cache efficiency:
```
  Model                          Requests     Total Tokens    Cache Hit %
  -----------------------------------------------------------------------------
  claude-sonnet-4                523          8,123,456       42.3%
  claude-opus-4                  401          5,234,123       28.1%
  claude-haiku-3.5               310          1,877,988       51.2%
```

**💡 TIP**: Higher cache hit % = more cost savings!

### Projects View

See which projects are using the most tokens:
```
  Project                        Sessions     Total Tokens    Avg/Session
  ----------------------------------------------------------------------------
  nimbus-user-loader            45           3,456,789       76,817
  claude-pm                     38           2,345,678       61,728
  claude-family                 28           1,234,567       44,092
```

### Alerts View

Monitor your budget thresholds:
```
  Alert                     Type       Current      Threshold    Status
  --------------------------------------------------------------------------
  Daily Spending Limit      daily      $2.15        $10.00       ✅ 21.5%
  Weekly Token Budget       weekly     1,234,567    1,000,000    ⚠️  123.5%
  Monthly Cost Budget       monthly    $98.23       $200.00      ✅ 49.1%
```

---

## ⚙️ Configuration

### Creating Budget Alerts

```sql
INSERT INTO claude_family.budget_alerts (
    alert_name,
    alert_type,        -- 'daily', 'weekly', 'monthly'
    threshold_type,    -- 'cost', 'tokens', 'requests'
    threshold_value,
    is_active,
    created_by_identity_id
) VALUES (
    'Hourly Token Limit',
    'hourly',
    'tokens',
    100000,  -- 100K tokens per hour
    TRUE,
    (SELECT identity_id FROM claude_family.identities WHERE identity_name = 'claude-code-unified')
);
```

**Pre-configured Alerts**:
- Daily Spending Limit: $10/day
- Weekly Token Budget: 1M tokens/week
- Monthly Cost Budget: $200/month

### Modifying Sync Schedule

The cron job is in `claude_family.ai_cron_jobs`:

```sql
-- Check current schedule
SELECT job_name, schedule, last_run, next_run, last_status
FROM claude_family.ai_cron_jobs
WHERE job_name = 'sync-anthropic-usage';

-- Change to hourly
UPDATE claude_family.ai_cron_jobs
SET schedule = 'hourly',
    updated_at = NOW()
WHERE job_name = 'sync-anthropic-usage';

-- Disable/enable
UPDATE claude_family.ai_cron_jobs
SET is_active = FALSE  -- or TRUE
WHERE job_name = 'sync-anthropic-usage';
```

---

## 🔍 Advanced Queries

### Find Most Expensive Sessions

```sql
SELECT
    bucket_start_time::date as date,
    project_name,
    model,
    total_tokens,
    ROUND((total_tokens * 0.003 / 1000), 2) as estimated_cost_usd
FROM claude_family.api_usage_data
ORDER BY total_tokens DESC
LIMIT 20;
```

### Cache Efficiency by Project

```sql
SELECT
    project_name,
    SUM(cached_input_tokens) as cached,
    SUM(uncached_input_tokens + cached_input_tokens) as total_input,
    ROUND(
        (SUM(cached_input_tokens)::DECIMAL / NULLIF(SUM(uncached_input_tokens + cached_input_tokens), 0)) * 100,
        1
    ) as cache_hit_rate_percent
FROM claude_family.api_usage_data
WHERE bucket_start_time >= NOW() - INTERVAL '30 days'
GROUP BY project_name
ORDER BY cache_hit_rate_percent DESC;
```

### Daily Cost Trend

```sql
SELECT
    date,
    SUM(cost_usd) as daily_cost,
    AVG(SUM(cost_usd)) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as rolling_7day_avg
FROM claude_family.api_cost_data
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY date
ORDER BY date DESC;
```

---

## 🚨 Troubleshooting

### "❌ ANTHROPIC_ADMIN_API_KEY environment variable not set"

**Fix**: Set the environment variable (see Step 2 above). Restart terminal after setting.

### "❌ HTTP Error: 401 Unauthorized"

**Cause**: API key is invalid or not an Admin key.

**Fix**:
1. Check key starts with `sk-ant-admin...` (not `sk-ant-api...`)
2. Verify key is valid in Anthropic Console
3. Make sure you have organization admin role

### "No data available"

**Cause**: Haven't run sync yet, or sync failed.

**Fix**:
1. Run manual sync: `python scripts/sync_anthropic_usage.py --days 30`
2. Check sync status:
   ```sql
   SELECT * FROM claude_family.usage_sync_status ORDER BY started_at DESC LIMIT 5;
   ```
3. If sync failed, check `error_message` column

### Sync Job Not Running

**Check status**:
```sql
SELECT job_name, is_active, last_run, last_status, last_error
FROM claude_family.ai_cron_jobs
WHERE job_name = 'sync-anthropic-usage';
```

**Manually trigger**:
```bash
python scripts/sync_anthropic_usage.py
```

---

## 💡 Tips & Best Practices

### 1. Check Dashboard Daily

Run this every morning:
```bash
python scripts/view_usage.py
```

See your spending at a glance.

### 2. Monitor Cache Hit Rate

**Good**: >30% cache hit rate
**Excellent**: >50% cache hit rate

Low cache hit rate? You might be:
- Not reusing prompts/system messages
- Changing context too frequently
- Not using structured outputs

### 3. Set Conservative Alerts

Start with lower thresholds and adjust up:
- Daily: $5-10
- Weekly: $50
- Monthly: $150-200

Better to get false alarms than surprise bills!

### 4. Export Monthly for Accounting

```bash
python scripts/view_usage.py export --output usage_$(date +%Y%m).csv
```

Keep monthly exports for expense tracking.

### 5. Attribute Costs to Projects

Always set `project_name` when logging sessions:
```sql
UPDATE claude_family.session_history
SET project_name = 'nimbus-user-loader'
WHERE session_id = '<your-session-id>';
```

This flows through to usage tracking!

---

## 📈 Cost Optimization Strategies

### Strategy 1: Maximize Cache Usage

- Use consistent system messages
- Reuse prompts across requests
- Enable prompt caching in your code

**Savings**: Cached tokens cost 10% of regular tokens!

### Strategy 2: Choose Right Model

- **Haiku**: Fast, cheap, good for simple tasks
- **Sonnet**: Balanced performance/cost
- **Opus**: Most capable, most expensive

Don't use Opus when Haiku will do!

### Strategy 3: Batch Operations

Instead of:
```python
for item in items:
    response = anthropic.messages.create(...)  # 100 requests
```

Do:
```python
batch_prompt = "Process these items: " + json.dumps(items)
response = anthropic.messages.create(...)  # 1 request
```

### Strategy 4: Monitor Runaway Processes

Watch for:
- Sessions with >1M tokens
- Rapid increase in daily costs
- Unexpected model usage (e.g., Opus when you meant Haiku)

Set alerts to catch these early!

---

## 🔄 Maintenance

### Weekly

1. Check budget alerts: `python scripts/view_usage.py alerts`
2. Review daily spending trends
3. Identify any anomalies

### Monthly

1. Export data for records
2. Review cost by project
3. Adjust budget thresholds
4. Optimize high-cost operations

### As Needed

1. Sync historical data: `python scripts/sync_anthropic_usage.py --days 90`
2. Clean up old alerts
3. Update thresholds based on usage patterns

---

## 📚 References

- [Anthropic Usage & Cost API Docs](https://docs.claude.com/en/api/usage-cost-api)
- [Anthropic Console](https://console.anthropic.com/)
- [Prompt Caching Guide](https://docs.anthropic.com/claude/docs/prompt-caching)

---

## 🎉 You're All Set!

Your usage tracking system is now live. You can:

✅ **View spending** in real-time
✅ **Get alerts** before budget overruns
✅ **Track projects** and attribute costs
✅ **Optimize cache** usage to save money
✅ **Export data** for accounting/analysis
✅ **Prevent crashes** from runaway processes

Run `python scripts/view_usage.py` now to see your current usage!

---

**Questions? Issues?**

Check the `usage_sync_status` table for sync errors, or run sync manually with verbose output to debug.

**Happy tracking!** 🚀
