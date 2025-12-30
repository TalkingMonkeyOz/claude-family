# Agent Config and Timeout Fix Summary

**Date**: 2025-12-26
**Tasks Completed**:
1. Agent timeout pattern analysis
2. Missing agent config fixes
3. Timeout override issue investigation

---

## 1. Agent Timeout Analysis

### Timeout Adjustments Made

Updated `agent_specs.json` with new timeout values based on actual execution data from 147 agent sessions:

| Agent | Old Timeout | New Timeout | Reason |
|-------|------------|-------------|--------|
| **coder-haiku** | 600s (10m) | **1200s (20m)** | P95=855s exceeded old timeout |
| **python-coder-haiku** | 600s (10m) | **900s (15m)** | Max=3343s observed, P95=582s |
| **lightweight-haiku** | 180s (3m) | **600s (10m)** | Max=470s (2.6× over old timeout) |
| **research-coordinator-sonnet** | 1800s (30m) | **600s (10m)** | Max observed only 330s, timeout was 5.5× too high |

### Success Rate Analysis

**Top Performers (80%+ success)**:
- web-tester-haiku: 100% (2 spawns)
- doc-keeper-haiku: 100% (1 spawn)
- security-sonnet: 100% (1 spawn)
- lightweight-haiku: 83.3% (12 spawns)
- python-coder-haiku: 80.6% (36 spawns)

**Poor Performers (<60% success)**:
- 🚨 **researcher-opus**: 16.7% (1/6) - CRITICAL
- ⚠️ analyst-sonnet: 50% (5/10)
- ⚠️ research-coordinator-sonnet: 50% (2/4)
- ⚠️ reviewer-sonnet: 55.6% (5/9)

### Documentation Created

- **AGENT_TIMEOUT_ANALYSIS.md** - Complete performance statistics and recommendations
- **RESEARCHER_OPUS_FAILURE_ANALYSIS.md** - Deep dive into 83% failure rate

---

## 2. Missing Agent Configs Fixed

### Issue: Roslyn MCP Reference

**Problem**: `csharp-coder-haiku.mcp.json` (used by winforms-coder-haiku) referenced Roslyn MCP which was removed as incompatible with VS 2026.

**File**: `mcp-servers/orchestrator/configs/csharp-coder-haiku.mcp.json`

**Fix**: Removed roslyn MCP server configuration

**Before**:
```json
{
  "mcpServers": {
    "filesystem": {...},
    "roslyn": {...},  // ❌ REMOVED - incompatible
    "orchestrator": {...}
  }
}
```

**After**:
```json
{
  "mcpServers": {
    "filesystem": {...},
    "orchestrator": {...}
  }
}
```

### Configs Verified

Both agent configs verified as complete:

✅ **coordinator-sonnet.mcp.json** (used by research-coordinator-sonnet):
- filesystem MCP
- postgres MCP
- sequential-thinking MCP
- orchestrator MCP

✅ **csharp-coder-haiku.mcp.json** (used by winforms-coder-haiku):
- filesystem MCP
- orchestrator MCP

---

## 3. Timeout Override Issue Discovered

### Root Causes

#### Critical: Hardcoded 300s Default in sandbox_runner.py

**File**: `mcp-servers/orchestrator/sandbox_runner.py:86`

```python
async def run_sandboxed(
    self,
    task: str,
    workspace_path: str,
    timeout: int = 300,  # ❌ HARDCODED - ignores agent specs!
    gui: bool = False,
    model: str = "claude-sonnet-4-20250514"
)
```

**Impact**: All sandboxed agents default to 300s regardless of their spec timeout

**Evidence**:
- researcher-opus (spec: 1200s) → failed at "300s timeout"
- 4 out of 5 failed researcher-opus tasks show "timed out after 300 seconds"

#### Design: Parameter Override Pattern

**File**: `mcp-servers/orchestrator/orchestrator_prototype.py:335`

```python
timeout = timeout or spec['recommended_timeout_seconds']
```

**Behavior**: Callers CAN override spec timeouts by passing explicit values

**Status**: By design, but dangerous when combined with hardcoded defaults

#### User-Reported: Project-Level Overrides

**Finding**: User reported "projects were overriding the timeouts sometimes"

**Investigation**: Searched codebase for spawn_agent calls with timeout parameters

**Result**: ✅ No current project-level overrides found in:
- claude-family project
- ATO-Tax-Agent project
- nimbus-user-loader project

**Conclusion**: User's past observation was likely from sandbox_runner.py default (300s), not explicit project overrides

### Timeout Enforcement Bug

**Problem**: Agents continue running PAST the stated timeout before being killed

**Evidence from database**:

| Task | Stated Timeout | Actual Execution | Delta |
|------|---------------|------------------|-------|
| 9b6268b0 | 300s | **635s** | +335s (212% over!) |
| dbb69cd0 | 300s | **620s** | +320s (207% over!) |
| 6c77a819 | 300s | **592s** | +292s (197% over!) |

**Impact**: Resources wasted on agents that should have been killed

### Documentation Created

- **TIMEOUT_OVERRIDE_ISSUE.md** - Complete root cause analysis and recommended fixes

---

## 4. Cleanup Actions Performed

### Incomplete Agent Sessions

Cleaned up 6 incomplete agent sessions (older than 7 days):

```sql
UPDATE claude.agent_sessions
SET completed_at = spawned_at,
    execution_time_seconds = 0,
    success = false,
    error_message = 'Agent did not complete - assumed crashed or timed out (auto-cleanup)'
WHERE completed_at IS NULL
  AND spawned_at < NOW() - INTERVAL '7 days';
```

**Cleaned sessions**:
- 1× python-coder-haiku (2025-12-06)
- 1× analyst-sonnet (2025-12-08)
- 2× coder-haiku (2025-12-09)
- 1× sandbox-haiku (2025-12-09)
- 1× test-coordinator-sonnet (2025-12-12)

---

## 5. Recommended Next Steps

### Immediate (Requires Code Changes)

1. **Fix sandbox_runner.py default timeout** (CRITICAL)
   - Change `timeout: int = 300` to `timeout: int = None`
   - Add `agent_type` parameter to look up spec timeout
   - Use spec timeout if not explicitly provided

2. **Fix timeout enforcement**
   - Investigate why `proc.kill()` doesn't immediately stop agents
   - Consider using process groups to kill all child processes
   - Ensure execution_time reflects actual time, not timeout value

3. **Add timeout override validation**
   - Warn if override is <50% of spec timeout
   - Warn if override is >200% of spec timeout
   - Log overrides for monitoring

### Follow-Up (Monitoring)

1. **Monitor next 20 agent spawns** for each modified agent
   - Verify new timeout values are appropriate
   - Track success rates for improvement
   - Watch for new timeout issues

2. **Investigate poor performers**
   - researcher-opus: 16.7% success → Audit task prompts
   - analyst-sonnet: 50% success → Review failed tasks for patterns
   - research-coordinator-sonnet: 50% success → May need better task scoping

3. **Consider deprecating researcher-opus**
   - High cost ($0.73/task)
   - Poor success rate (16.7%)
   - Alternative: use research-coordinator-sonnet ($0.35) + analyst-sonnet ($0.30)

---

## 6. Files Modified

### Configuration Files

- ✅ `mcp-servers/orchestrator/agent_specs.json` - Updated 4 agent timeouts
- ✅ `mcp-servers/orchestrator/configs/csharp-coder-haiku.mcp.json` - Removed roslyn MCP

### Documentation Created

- ✅ `docs/AGENT_TIMEOUT_ANALYSIS.md` - Performance analysis and timeout recommendations
- ✅ `docs/RESEARCHER_OPUS_FAILURE_ANALYSIS.md` - Investigation of 83% failure rate
- ✅ `docs/TIMEOUT_OVERRIDE_ISSUE.md` - Root cause analysis of timeout bugs
- ✅ `docs/AGENT_CONFIG_AND_TIMEOUT_FIX_SUMMARY.md` - This file

### Database Changes

- ✅ Cleaned up 6 incomplete agent_sessions records

---

## 7. Cost Impact

### Wasted Costs (researcher-opus failures)

- 5 failed tasks × $0.73 = **$3.65 wasted**
- Tasks actually completed valuable work (300-635s execution) but were marked as failed
- Research output was discarded

### Expected Savings (after fixes)

**coder-haiku timeout increase (600s → 1200s)**:
- Current: Tasks timing out prematurely, requiring reruns
- After: Tasks complete successfully on first run
- Estimated savings: **$0.14 per avoided rerun** (4 agents × $0.035)

**python-coder-haiku timeout increase (600s → 900s)**:
- Current: Tasks timing out prematurely
- After: Tasks complete successfully
- Estimated savings: **$0.18 per avoided rerun** (4 agents × $0.045)

**Total estimated savings**: **$0.30-0.50 per avoided failure** + improved developer experience

---

## 8. Success Metrics

### Before Fixes

| Metric | Value |
|--------|-------|
| Agent spawns analyzed | 147 |
| Timeout-related failures | Unknown (conflated with other failures) |
| researcher-opus success rate | 16.7% |
| Average timeout accuracy | Poor (multiple agents exceeding limits) |

### After Fixes (Target)

| Metric | Target |
|--------|--------|
| Timeout-related failures | <5% |
| researcher-opus success rate | 60%+ (or deprecate) |
| Agent timeout adherence | 95%+ complete within timeout |
| Override warnings logged | 100% |

---

## 9. Testing Checklist

Before deploying fixes to sandbox_runner.py:

- [ ] Test researcher-opus with new default (should use 1200s from spec)
- [ ] Test coder-haiku with increased timeout (1200s)
- [ ] Test python-coder-haiku with increased timeout (900s)
- [ ] Test lightweight-haiku with increased timeout (600s)
- [ ] Verify timeout enforcement actually kills processes
- [ ] Verify execution_time reflects actual time, not timeout value
- [ ] Test timeout override with explicit value (should log warning if unreasonable)

---

## 10. Conclusion

**Problems identified**:
1. ✅ Agent timeout values were outdated (FIXED - specs updated)
2. ✅ Agent configs had stale references (FIXED - roslyn removed)
3. ⚠️ Timeout override bug in sandbox_runner.py (DOCUMENTED - needs code fix)
4. ⚠️ Timeout enforcement bug (processes run past timeout) (DOCUMENTED - needs code fix)

**Immediate value delivered**:
- Updated timeout specs for 4 agents
- Cleaned up 6 orphaned sessions
- Removed incompatible Roslyn MCP reference
- Comprehensive documentation of root causes

**Next session priorities**:
1. Fix sandbox_runner.py hardcoded timeout
2. Fix timeout enforcement (kill processes properly)
3. Add timeout override validation/logging
4. Test all fixes and monitor results

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/AGENT_CONFIG_AND_TIMEOUT_FIX_SUMMARY.md
