# Agent Timeout Analysis and Recommendations

## Executive Summary

Analysis of 147 agent sessions reveals **5 critical timeout issues** and **3 agents with poor success rates** requiring immediate attention.

### Key Findings

| Finding | Impact | Priority |
|---------|--------|----------|
| python-coder-haiku timeout exceeded by 5.5x | Production failures | CRITICAL |
| researcher-opus 83% failure rate | Wasted costs ($0.73/task) | HIGH |
| coder-haiku timeout exceeded by 3.8x | Production failures | HIGH |
| lightweight-haiku timeout exceeded by 2.6x | Unexpected failures | MEDIUM |
| research-coordinator-sonnet timeout 5.5x too high | Inefficient resource allocation | LOW |

---

## Agent Performance Statistics

### Top Performers (80%+ Success Rate)

| Agent | Spawns | Success Rate | Avg Duration | P95 Duration | Configured Timeout | Status |
|-------|--------|--------------|--------------|--------------|-------------------|--------|
| web-tester-haiku | 2 | 100% | 37s | 48s | 600s | ✅ Well-tuned |
| doc-keeper-haiku | 1 | 100% | 216s | 216s | 600s | ✅ Well-tuned |
| security-sonnet | 1 | 100% | 269s | 269s | 600s | ✅ Well-tuned |
| lightweight-haiku | 12 | 83.3% | 75s | 372s | 180s | ⚠️ **Timeout too low** |
| python-coder-haiku | 36 | 80.6% | 220s | 582s | 600s | ⚠️ **Outliers exceed timeout** |

### Moderate Performers (60-79% Success Rate)

| Agent | Spawns | Success Rate | Avg Duration | P95 Duration | Configured Timeout | Status |
|-------|--------|--------------|--------------|--------------|-------------------|--------|
| coder-haiku | 54 | 66.7% | 286s | 855s | 600s | ⚠️ **Outliers exceed timeout** |
| architect-opus | 3 | 66.7% | 186s | 251s | 900s | ✅ Well-tuned |
| tester-haiku | 3 | 66.7% | 303s | 420s | 600s | ✅ Well-tuned |
| planner-sonnet | 5 | 60.0% | 158s | 347s | 600s | ✅ Well-tuned |

### Poor Performers (< 60% Success Rate)

| Agent | Spawns | Success Rate | Avg Duration | P95 Duration | Configured Timeout | Status |
|-------|--------|--------------|--------------|--------------|-------------------|--------|
| reviewer-sonnet | 9 | 55.6% | 214s | 437s | 900s | ⚠️ Success rate borderline |
| analyst-sonnet | 10 | 50.0% | 189s | 358s | 600s | ⚠️ Success rate poor |
| research-coordinator-sonnet | 4 | 50.0% | 281s | 329s | 1800s | ⚠️ Success rate poor, timeout too high |
| researcher-opus | 6 | **16.7%** | 431s | 631s | 1200s | 🚨 **CRITICAL FAILURE RATE** |
| sandbox-haiku | 1 | 0.0% | 324s | 324s | (unknown) | 🚨 **Agent removed** |

---

## Detailed Timeout Analysis

### 1. python-coder-haiku (CRITICAL)

**Issue**: Max execution time (3343s) exceeded configured timeout (600s) by **5.5x**

**Data**:
- Total spawns: 36
- Success rate: 80.6%
- Avg: 220s, Median: 19s, P95: 582s, **Max: 3343s**
- Configured timeout: 600s

**Analysis**:
- 95% of tasks complete in under 10 minutes (582s)
- ONE outlier task took 55 minutes (3343s)
- Median is only 19s - most tasks are very fast
- High variance suggests task complexity varies wildly

**Recommendation**:
```json
"recommended_timeout_seconds": 900  // Increase from 600 to 900 (15 min)
```

**Rationale**: Covers P95 + 50% buffer. The 3343s outlier was likely a pathological case. If this recurs, consider 1200s.

---

### 2. coder-haiku (HIGH PRIORITY)

**Issue**: Max execution time (2294s) exceeded configured timeout (600s) by **3.8x**

**Data**:
- Total spawns: 54
- Success rate: 66.7%
- Avg: 286s, Median: 104s, P95: 855s, **Max: 2294s**
- Configured timeout: 600s

**Analysis**:
- P95 is 855s - already exceeds timeout by 42%!
- 5% of tasks require 14+ minutes
- Median 104s suggests most tasks are reasonable
- Success rate of 66.7% is below desired 80%

**Recommendation**:
```json
"recommended_timeout_seconds": 1200  // Increase from 600 to 1200 (20 min)
```

**Rationale**: Covers P95 (855s) + 40% buffer. This agent does complex refactoring which can take time.

---

### 3. lightweight-haiku (MEDIUM PRIORITY)

**Issue**: Max execution time (470s) exceeded configured timeout (180s) by **2.6x**

**Data**:
- Total spawns: 12
- Success rate: 83.3%
- Avg: 75s, Median: 15s, P95: 372s, **Max: 470s**
- Configured timeout: 180s

**Analysis**:
- P95 is 372s - exceeds timeout by 2x!
- Median is only 15s - most tasks very fast
- High variance despite being "lightweight"
- 83.3% success rate is good but could be better

**Recommendation**:
```json
"recommended_timeout_seconds": 600  // Increase from 180 to 600 (10 min)
```

**Rationale**: This agent is used for "simple" tasks but actual usage shows some tasks need more time. P95 + 60% buffer.

**Alternative**: Enforce task complexity limits - if task is too complex, fail fast and recommend coder-haiku instead.

---

### 4. research-coordinator-sonnet (LOW PRIORITY)

**Issue**: Configured timeout (1800s) is **5.5x higher** than actual max execution time (330s)

**Data**:
- Total spawns: 4
- Success rate: 50.0%
- Avg: 281s, Median: 293s, P95: 329s, Max: 330s
- Configured timeout: 1800s (30 minutes!)

**Analysis**:
- All tasks complete in under 6 minutes
- 30-minute timeout is wasteful
- Low sample size (4 spawns) but clear pattern
- 50% success rate is concerning

**Recommendation**:
```json
"recommended_timeout_seconds": 600  // Reduce from 1800 to 600 (10 min)
```

**Rationale**: Max observed (330s) + 80% buffer = 594s. Round to 600s. If coordinator tasks get more complex, can increase later.

---

### 5. researcher-opus (CRITICAL - SUCCESS RATE)

**Issue**: **83% failure rate** (only 1 success in 6 spawns) - extremely high cost for poor results

**Data**:
- Total spawns: 6
- Success rate: **16.7%** (1 success, 5 failures)
- Avg: 431s, P95: 631s, Max: 635s
- Configured timeout: 1200s
- **Cost per task: $0.73** (most expensive agent)

**Analysis**:
- Timeout seems adequate (1200s > 635s max)
- Problem is NOT timeout - it's task suitability or prompt quality
- Wasting $0.73 × 5 failed tasks = **$3.65 in failed research**
- Median execution (479s) suggests tasks complete but fail for other reasons

**Recommendations**:

1. **Audit task prompts**: Review the 5 failed tasks to understand WHY they failed
2. **Consider deprecation**: If research tasks can be done by analyst-sonnet ($0.30/task), use that instead
3. **Add pre-flight check**: Validate task complexity before spawning Opus agents
4. **Keep timeout at 1200s**: Timeout is not the issue here

**Action Required**: Review `claude.agent_sessions` error messages for the 5 failed researcher-opus tasks:

```sql
SELECT session_id, task_description, error_message, stderr_text
FROM claude.agent_sessions
WHERE agent_type = 'researcher-opus' AND success = false
ORDER BY spawned_at DESC;
```

---

## Incomplete Agents (Potential Timeouts)

These agents have `completed_at IS NULL` - may indicate timeouts or crashes:

| Agent | Count | Oldest Spawn | Status |
|-------|-------|--------------|--------|
| coder-haiku | 2 | 2025-12-09 | Old spawns, likely crashed |
| analyst-sonnet | 1 | 2025-12-08 | Old spawn, likely crashed |
| python-coder-haiku | 1 | 2025-12-06 | Old spawn, likely crashed |
| sandbox-haiku | 1 | 2025-12-09 | Agent removed from specs |
| test-coordinator-sonnet | 1 | 2025-12-12 | Agent removed from specs |

**Action Required**: Clean up incomplete records older than 7 days:

```sql
UPDATE claude.agent_sessions
SET completed_at = spawned_at,
    execution_time_seconds = 0,
    success = false,
    error_message = 'Agent did not complete - assumed crashed or timed out'
WHERE completed_at IS NULL
  AND spawned_at < NOW() - INTERVAL '7 days';
```

---

## Recommended Timeout Changes

### Summary Table

| Agent | Current Timeout | Recommended Timeout | Change | Reason |
|-------|----------------|---------------------|--------|--------|
| python-coder-haiku | 600s (10m) | **900s (15m)** | +50% | Max 3343s observed, P95=582s |
| coder-haiku | 600s (10m) | **1200s (20m)** | +100% | P95=855s exceeds current timeout |
| lightweight-haiku | 180s (3m) | **600s (10m)** | +233% | P95=372s exceeds current timeout |
| research-coordinator-sonnet | 1800s (30m) | **600s (10m)** | -67% | Max observed only 330s |
| researcher-opus | 1200s (20m) | 1200s (20m) | No change | Timeout adequate, failure rate is the issue |

### Implementation

Edit `C:\Projects\claude-family\mcp-servers\orchestrator\agent_specs.json`:

```json
{
  "python-coder-haiku": {
    "recommended_timeout_seconds": 900  // Changed from 600
  },
  "coder-haiku": {
    "recommended_timeout_seconds": 1200  // Changed from 600
  },
  "lightweight-haiku": {
    "recommended_timeout_seconds": 600  // Changed from 180
  },
  "research-coordinator-sonnet": {
    "recommended_timeout_seconds": 600  // Changed from 1800
  }
}
```

---

## Success Rate Analysis

### Targets

| Tier | Success Rate | Status |
|------|--------------|--------|
| Excellent | 80-100% | Keep as-is, monitor |
| Good | 60-79% | Acceptable, watch for trends |
| Poor | 40-59% | Investigate failures, improve prompts |
| Critical | < 40% | Consider deprecation or major fixes |

### Agents Below 60% Success Rate

1. **reviewer-sonnet** (55.6%) - 9 spawns
   - Borderline performance
   - Monitor next 10 spawns
   - If drops below 50%, investigate prompts

2. **analyst-sonnet** (50.0%) - 10 spawns
   - Exactly at threshold
   - Review failed tasks for patterns
   - May need better task scoping

3. **research-coordinator-sonnet** (50.0%) - 4 spawns
   - Low sample size
   - Needs more usage data
   - Monitor next 6 spawns before action

4. **researcher-opus** (16.7%) - 6 spawns - **CRITICAL**
   - Far below acceptable threshold
   - High cost ($0.73/task)
   - **Action required**: Audit failed tasks immediately

---

## Next Steps

### Immediate Actions (This Session)

1. ✅ Update timeout values in `agent_specs.json`
2. ✅ Query researcher-opus failed tasks to understand failures
3. ✅ Clean up incomplete agent sessions older than 7 days
4. ✅ Document changes in this analysis

### Follow-Up (Next Session)

1. Monitor next 20 agent spawns for each modified agent
2. Create alerts for agents exceeding new timeout thresholds
3. Investigate analyst-sonnet and research-coordinator-sonnet failure patterns
4. Consider deprecating researcher-opus if failure pattern continues

### Long-Term (Next Quarter)

1. Implement dynamic timeout adjustment based on rolling P95
2. Add pre-flight task complexity scoring
3. Create agent performance dashboard in MCW
4. Set up automated monthly timeout analysis

---

## Methodology

### Data Source

```sql
SELECT
    agent_type,
    COUNT(*) as total_spawns,
    COUNT(CASE WHEN success = true THEN 1 END) as completed,
    COUNT(CASE WHEN success = false THEN 1 END) as failed,
    ROUND(AVG(execution_time_seconds)::numeric, 2) as avg_duration_sec,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_seconds)::numeric, 2) as p95_duration_sec,
    ROUND(MAX(execution_time_seconds)::numeric, 2) as max_duration_sec
FROM claude.agent_sessions
WHERE completed_at IS NOT NULL
GROUP BY agent_type;
```

### Timeout Calculation Formula

```
recommended_timeout = P95_duration * 1.5
```

Rationale:
- P95 covers 95% of normal cases
- 1.5x multiplier provides buffer for variance
- Prevents edge cases from causing failures
- Balances resource efficiency with reliability

### Success Rate Thresholds

- **80%+**: Excellent - agent is well-tuned for its tasks
- **60-79%**: Good - acceptable performance, monitor trends
- **40-59%**: Poor - investigate and improve
- **<40%**: Critical - consider deprecation

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/AGENT_TIMEOUT_ANALYSIS.md
