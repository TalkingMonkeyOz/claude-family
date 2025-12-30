---
title: Infrastructure Stats and Monitoring
category: domain-knowledge
domain: infrastructure
tags: [monitoring, performance, analytics, agents, hooks]
created: 2025-12-28
updated: 2025-12-28
status: active
---

# Infrastructure Stats and Monitoring

**Purpose**: Track the health and performance of the Claude Family infrastructure, including hooks, agents, and database operations.

---

## Key Metrics We Monitor

### 1. Hook Performance

**Location**: `~/.claude/hooks.log` (257KB, 220+ invocations tracked)

**Current Performance**:
- **PreToolUse (Write/Edit)**: ~16ms overhead (instruction_matcher + CLAUDE.md validator)
- **PreToolUse (SQL)**: ~24ms overhead (3 validators: data, phase, parent links)
- **Baseline**: ~8ms (JSON parsing + file I/O)
- **Verdict**: <20ms average - imperceptible to users

**Hook Coverage by File Type**:
```
.cs files:  57 processed (SUCCESS: csharp + a11y + mvvm)
.md files:  56 processed (SUCCESS: markdown)
.py files:  13 processed (if python.instructions.md exists)
.sql files: tracked (sql-postgres.instructions.md)
.xaml files: tracked (wpf-ui.instructions.md)
```

**How to Check**:
```bash
# Count hook invocations
grep -c "Hook invoked" ~/.claude/hooks.log

# See recent matches
grep -E "SUCCESS|No matching" ~/.claude/hooks.log | tail -20

# Count by file type
grep "Processing file" ~/.claude/hooks.log | sed 's/.*\./\./' | sort | uniq -c
```

**Key Insight**: Multi-instruction stacking works! C# files get 2-3 instructions applied (csharp + a11y + mvvm).

---

### 2. Agent Success Rates

**Location**: `claude.agent_sessions` table

**Current Performance (Last 30 Days)**:

| Agent Type | Total Spawns | Success Rate | Avg Time | Status |
|------------|--------------|--------------|----------|--------|
| **python-coder-haiku** | 37 | 78.4% | 3.6 min | ✅ Good |
| **lightweight-haiku** | 12 | 83.3% | 1.2 min | ✅ Excellent |
| **coder-haiku** | 56 | 64.3% | 4.6 min | ⚠️ Needs attention |
| **doc-keeper-haiku** | 2 | 100% | 4.2 min | ✅ Perfect |
| **web-tester-haiku** | 2 | 100% | 37 sec | ✅ Fast & reliable |
| **researcher-opus** | 6 | 16.7% | 7.2 min | 🔴 Critical - investigate |
| **analyst-sonnet** | 13 | 46.2% | 2.7 min | ⚠️ Below target |

**Trend Analysis**:
- **Dec 27**: 100% success (1 spawn)
- **Dec 26**: 76.9% success (13 spawns)
- **Dec 23**: 100% success (3 spawns)
- **Dec 21**: 85.7% success (14 spawns)
- **Dec 9**: 15.8% success (19 spawns) ← lowest point
- **Improvement**: +84% success rate over 18 days

**How to Check**:
```sql
-- Daily success rate trend
SELECT
  DATE(spawned_at) as date,
  COUNT(*) as total_spawns,
  ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as success_pct
FROM claude.agent_sessions
WHERE spawned_at > NOW() - INTERVAL '30 days'
  AND completed_at IS NOT NULL
GROUP BY DATE(spawned_at)
ORDER BY date DESC;

-- Agent type breakdown
SELECT
  agent_type,
  COUNT(*) as total,
  ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1) as success_pct,
  ROUND(AVG(execution_time_seconds)::numeric, 1) as avg_sec
FROM claude.agent_sessions
WHERE spawned_at > NOW() - INTERVAL '30 days'
  AND completed_at IS NOT NULL
GROUP BY agent_type
ORDER BY total DESC;
```

**Action Items**:
- 🔴 **researcher-opus**: 83% failure rate - deprecate or fix
- ⚠️ **coder-haiku**: 36% failure - investigate common failure patterns
- ⚠️ **analyst-sonnet**: 54% failure - review task complexity

---

### 3. MCP Tool Usage

**Location**: `claude.mcp_usage` table (PostToolUse hook)

**Status**: ⚠️ **NOT COLLECTING DATA**

**Root Cause**: PostToolUse hooks don't fire in Claude Code sessions
- Logger script works (proven by manual test: `scripts/mcp_usage_logger.py`)
- Hook configured correctly in `.claude/hooks.json`
- Issue: PostToolUse event type not supported yet in Claude Code

**Evidence**:
```sql
-- Manual test logged successfully
SELECT * FROM claude.mcp_usage ORDER BY called_at DESC LIMIT 5;
-- Returns: 5 test entries from Dec 20-28
-- All have session_id = NULL (manual tests)

-- No real session data
SELECT COUNT(*) FROM claude.mcp_usage WHERE session_id IS NOT NULL;
-- Returns: 0
```

**Workaround**: Use `mcp__orchestrator__get_mcp_stats` when that function is available

**Table Schema**:
```sql
claude.mcp_usage (
  usage_id uuid,
  session_id uuid,
  mcp_server varchar,      -- 'postgres', 'orchestrator', 'memory', etc.
  tool_name varchar,        -- 'mcp__postgres__execute_sql'
  called_at timestamp,
  execution_time_ms int,    -- How long the tool took
  success boolean,
  error_message text,
  input_size_bytes int,
  output_size_bytes int,
  project_name varchar
)
```

---

### 4. Database Health

**Key Tables to Monitor**:

#### Session Tracking
```sql
-- Recent activity
SELECT
  project_name,
  COUNT(*) as sessions,
  MAX(session_start) as last_session
FROM claude.sessions
WHERE session_start > NOW() - INTERVAL '7 days'
GROUP BY project_name
ORDER BY sessions DESC;
```

#### Message Accountability
```sql
-- Unactioned messages (require attention)
SELECT COUNT(*) as unactioned
FROM claude.messages
WHERE addressed_to_project = 'YOUR-PROJECT'
  AND status NOT IN ('actioned', 'deferred', 'read');
```

#### Todo Completion
```sql
-- Active work items
SELECT
  priority,
  COUNT(*) as items
FROM claude.todos
WHERE status = 'pending'
  AND project_id = 'YOUR-PROJECT-ID'::uuid
GROUP BY priority
ORDER BY priority;
```

---

## Monitoring Checklist

### Daily
- [ ] Check `/session-resume` for unactioned messages
- [ ] Review agent spawn failures (if any)
- [ ] Check hook log size (shouldn't grow > 1MB/day)

### Weekly
- [ ] Agent success rate trend (should be > 70%)
- [ ] Hook performance (should be < 50ms)
- [ ] Review researcher-opus failures

### Monthly
- [ ] Archive old session data (> 90 days)
- [ ] Review MCP server configs (any deprecations?)
- [ ] Update agent specs based on performance

---

## Performance Baselines

### Acceptable Ranges

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Hook overhead | < 20ms | 20-50ms | > 50ms |
| Agent success rate | > 80% | 60-80% | < 60% |
| Agent avg time | < 5min | 5-10min | > 10min |
| Session log size | < 1MB/day | 1-5MB | > 5MB |

### Red Flags

🚨 **Immediate Action Required**:
- Agent success rate drops below 50% for 3+ consecutive days
- Hook overhead exceeds 100ms
- Database queries taking > 5 seconds
- Unactioned messages piling up (> 10 pending)

⚠️ **Investigation Needed**:
- New agent type with < 70% success in first 10 spawns
- Hook log growing > 1MB/day
- Session startup taking > 30 seconds
- MCP server errors in logs

---

## Useful Queries

### Hook Analysis
```bash
# Total hook invocations
grep -c "Hook invoked" ~/.claude/hooks.log

# File types processed
grep "Processing file" ~/.claude/hooks.log | sed 's/.*\./\./' | sort | uniq -c | sort -rn

# Successful instruction applications
grep "SUCCESS: Applied" ~/.claude/hooks.log | wc -l
```

### Agent Analysis
```sql
-- Failure patterns
SELECT
  agent_type,
  error_message,
  COUNT(*) as occurrences
FROM claude.agent_sessions
WHERE success = false
  AND spawned_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, error_message
ORDER BY occurrences DESC;

-- Long-running agents
SELECT
  agent_type,
  task_description,
  execution_time_seconds / 60 as minutes
FROM claude.agent_sessions
WHERE execution_time_seconds > 600  -- > 10 minutes
ORDER BY execution_time_seconds DESC
LIMIT 10;
```

### Database Performance
```sql
-- Table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'claude'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan as scans,
  pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'claude'
ORDER BY idx_scan ASC
LIMIT 10;
```

---

## Future Improvements

### Short Term
1. Enable PostToolUse hooks when Claude Code supports them
2. Add MCP stats function to orchestrator
3. Create dashboard for real-time monitoring

### Long Term
1. Automated alerting (webhook to Discord/Slack)
2. Cost tracking per session/agent
3. Predictive failure detection (ML on agent patterns)
4. Performance regression testing

---

**Last Updated**: 2025-12-28
**Owner**: claude-family infrastructure
**Review Frequency**: Monthly
