# Timeout Fix Monitoring Plan

**Date Implemented**: 2025-12-26
**Changes**: Timeout validation, improved enforcement, updated 4 agent timeouts

---

## Changes Made

### 1. Timeout Validation (orchestrator_prototype.py:334-346)

Added warnings when timeouts are overridden:
- ⚠️ Warning if override <50% of spec timeout
- ⚠️ Warning if override >200% of spec timeout
- ℹ️ Info log when any override is used

### 2. Improved Timeout Enforcement (orchestrator_prototype.py:471-490)

Enhanced process termination:
- Try graceful `terminate()` first (5s grace period)
- Force `kill()` if process doesn't terminate
- Log timeout events to stderr
- Use actual execution time instead of timeout value

### 3. Agent Timeout Updates (agent_specs.json)

| Agent | Old | New | Reason |
|-------|-----|-----|--------|
| coder-haiku | 600s | 1200s | P95=855s exceeded old limit |
| python-coder-haiku | 600s | 900s | Max=3343s, P95=582s |
| lightweight-haiku | 180s | 600s | Max=470s (2.6× old limit) |
| research-coordinator-sonnet | 1800s | 600s | Max=330s (was 5.5× too high) |

---

## Monitoring Queries

### Query 1: Next 20 Agent Spawns (All Types)

```sql
-- Monitor next 20 agent spawns to verify timeout behavior
SELECT
    session_id::text as id,
    agent_type,
    spawned_at,
    completed_at,
    success,
    execution_time_seconds as exec_sec,
    CASE
        WHEN completed_at IS NULL THEN 'Running'
        WHEN success = true THEN 'Success'
        WHEN success = false AND error_message LIKE '%timed out%' THEN 'Timeout'
        ELSE 'Failed'
    END as status,
    SUBSTRING(error_message, 1, 100) as error
FROM claude.agent_sessions
WHERE spawned_at > '2025-12-26 00:00:00'  -- After fix deployment
ORDER BY spawned_at DESC
LIMIT 20;
```

### Query 2: Timeout-Specific Monitoring

```sql
-- Focus on agents that had timeout issues
WITH recent_spawns AS (
    SELECT
        agent_type,
        spawned_at,
        execution_time_seconds,
        success,
        error_message,
        CASE agent_type
            WHEN 'coder-haiku' THEN 1200
            WHEN 'python-coder-haiku' THEN 900
            WHEN 'lightweight-haiku' THEN 600
            WHEN 'research-coordinator-sonnet' THEN 600
            WHEN 'researcher-opus' THEN 1200
            ELSE 600
        END as spec_timeout
    FROM claude.agent_sessions
    WHERE spawned_at > '2025-12-26 00:00:00'
      AND agent_type IN ('coder-haiku', 'python-coder-haiku', 'lightweight-haiku',
                         'research-coordinator-sonnet', 'researcher-opus')
)
SELECT
    agent_type,
    COUNT(*) as spawns,
    COUNT(CASE WHEN success = true THEN 1 END) as successes,
    COUNT(CASE WHEN error_message LIKE '%timed out%' THEN 1 END) as timeouts,
    ROUND(AVG(execution_time_seconds)::numeric, 2) as avg_exec,
    ROUND(MAX(execution_time_seconds)::numeric, 2) as max_exec,
    MAX(spec_timeout) as timeout_limit,
    CASE
        WHEN MAX(execution_time_seconds) > MAX(spec_timeout) THEN '⚠️ EXCEEDED'
        WHEN MAX(execution_time_seconds) > MAX(spec_timeout) * 0.9 THEN '⚠️ CLOSE'
        ELSE '✅ OK'
    END as timeout_status
FROM recent_spawns
GROUP BY agent_type
ORDER BY spawns DESC;
```

### Query 3: researcher-opus Specific

```sql
-- Monitor researcher-opus success rate improvement
SELECT
    COUNT(*) as total_spawns,
    COUNT(CASE WHEN success = true THEN 1 END) as successes,
    COUNT(CASE WHEN success = false THEN 1 END) as failures,
    ROUND((COUNT(CASE WHEN success = true THEN 1 END)::numeric / NULLIF(COUNT(*), 0) * 100), 1) as success_pct,
    ROUND(AVG(execution_time_seconds)::numeric, 2) as avg_exec,
    ROUND(MAX(execution_time_seconds)::numeric, 2) as max_exec,
    COUNT(CASE WHEN error_message LIKE '%timed out%' THEN 1 END) as timeout_count
FROM claude.agent_sessions
WHERE agent_type = 'researcher-opus'
  AND spawned_at > '2025-12-26 00:00:00';
```

---

## Success Criteria

### Immediate (Next 20 Spawns)

- [ ] Zero timeout overrides logged (unless explicitly passed)
- [ ] Zero agents exceeding their new timeout limits
- [ ] Timeout enforcement logs appear in stderr when timeouts occur
- [ ] Execution times accurately reflect wall clock time

### Short-Term (Next 50 Spawns)

- [ ] coder-haiku: 90%+ complete within 1200s timeout
- [ ] python-coder-haiku: 90%+ complete within 900s timeout
- [ ] lightweight-haiku: 90%+ complete within 600s timeout
- [ ] research-coordinator-sonnet: 95%+ complete within 600s timeout

### Medium-Term (Next 100 Spawns)

- [ ] researcher-opus: Success rate improves to 60%+ (or decision to deprecate)
- [ ] Overall timeout-related failures: <5%
- [ ] No agents consistently running >90% of timeout limit

---

## Alert Conditions

### Critical Alerts

1. **Agent exceeds new timeout**: Any agent's execution_time_seconds > spec timeout
   - Action: Review task complexity, consider further timeout increase
   - Query: Check Query 2 for timeout_status = '⚠️ EXCEEDED'

2. **Timeout override warnings appearing**: Indicates caller is passing explicit timeouts
   - Action: Find where override is happening, determine if justified
   - Check: Orchestrator stderr logs for "WARNING: timeout override"

3. **Timeouts still not killing processes**: execution_time >> timeout value
   - Action: Process termination fix didn't work, needs investigation
   - Query: Check Query 1 for status='Timeout' with exec_sec > timeout + 60s

### Warning Conditions

1. **Agent consistently near timeout**: Max execution >90% of timeout
   - Action: Monitor for trends, may need timeout increase
   - Query: Check Query 2 for timeout_status = '⚠️ CLOSE'

2. **researcher-opus success rate still <50%**
   - Action: Review failed task prompts, consider deprecation
   - Query: Check Query 3 for success_pct

---

## Testing Checklist

Before marking monitoring as complete:

### Immediate Tests (Run After Deployment)

- [ ] Test coder-haiku spawn - verify uses 1200s timeout
- [ ] Test python-coder-haiku spawn - verify uses 900s timeout
- [ ] Test lightweight-haiku spawn - verify uses 600s timeout
- [ ] Test researcher-opus spawn - verify uses 1200s timeout (not 300s!)
- [ ] Test with explicit timeout override - verify warning is logged

### Timeout Enforcement Test

- [ ] Spawn agent with short timeout (60s) on long task
- [ ] Verify timeout occurs at 60s
- [ ] Verify process is actually killed (not running past timeout)
- [ ] Verify execution_time_seconds reflects actual time
- [ ] Check stderr logs for termination messages

### Validation Tests

- [ ] Override timeout to 50% of spec - verify warning logged
- [ ] Override timeout to 250% of spec - verify warning logged
- [ ] Override timeout to reasonable value - verify info logged (no warning)

---

## Review Schedule

| Checkpoint | When | What to Check | Action If Failed |
|------------|------|---------------|------------------|
| **First 5 spawns** | 1 hour | Any timeouts? Overrides logged? | Review logs immediately |
| **First 20 spawns** | 1 day | Success rates, timeout adherence | Adjust if needed |
| **First 50 spawns** | 3 days | Trend analysis, outliers | Document patterns |
| **First 100 spawns** | 1 week | Success criteria met? | Declare success or iterate |

---

## Rollback Plan

If critical issues occur:

1. **Revert timeout values** in `agent_specs.json`:
   ```bash
   git checkout HEAD~1 -- mcp-servers/orchestrator/agent_specs.json
   ```

2. **Revert orchestrator code** if enforcement breaks:
   ```bash
   git checkout HEAD~1 -- mcp-servers/orchestrator/orchestrator_prototype.py
   ```

3. **Document issue** in GitHub issue or feedback table
4. **Analyze failure mode** before re-attempting

---

## Expected Outcomes

### Week 1

- Timeout-related failures drop to <5%
- No agents exceed new timeout limits
- researcher-opus success rate trends upward (target: 40%+)

### Week 2

- Timeout-related failures drop to <2%
- researcher-opus success rate reaches 60%+ OR decision made to deprecate
- Confidence in timeout values established

### Month 1

- Timeout values validated through ~500 spawns
- Success rate improvements documented
- Cost savings from avoided reruns calculated

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/TIMEOUT_FIX_MONITORING.md
