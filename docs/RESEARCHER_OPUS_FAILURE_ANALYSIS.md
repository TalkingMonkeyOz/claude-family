# Researcher-Opus Failure Analysis

## Critical Finding: 83% Failure Rate

Out of 6 total spawns, only 1 succeeded (16.7% success rate) at a cost of $0.73 per task.

**Total wasted cost**: 5 failures × $0.73 = **$3.65**

---

## Failed Tasks Details

All 5 failed tasks show a pattern: **timeout errors but execution exceeded the stated timeout**.

| Session ID | Task Description (Summary) | Execution Time | Error Message | Spawned Date |
|-----------|---------------------------|----------------|---------------|--------------|
| 498d2adb | Search nimbus-user-loader for OData entity names | 133s | "Timed out after 120s" | 2025-12-13 |
| 9b6268b0 | Hook Systems & Process Enforcement research | 635s | "Timed out after 300s" | 2025-12-10 |
| dbb69cd0 | Database-Driven Development Tracking research | 620s | "Timed out after 300s" | 2025-12-10 |
| 6c77a819 | AI Development Orchestration Tools research | 592s | "Timed out after 300s" | 2025-12-10 |
| eee939dc | LangChain/LlamaIndex routing patterns | 366s | "Timed out after 300s" | 2025-12-08 |

---

## Anomaly: Timeout Enforcement Issue

**CRITICAL BUG DETECTED**: Error messages claim timeouts occurred, but execution times show agents ran LONGER than stated timeouts:

| Task | Stated Timeout | Actual Execution | Delta |
|------|---------------|------------------|-------|
| 498d2adb | 120s | 133s | +13s (11% over) |
| 9b6268b0 | 300s | 635s | **+335s (212% over!)** |
| dbb69cd0 | 300s | 620s | **+320s (207% over!)** |
| 6c77a819 | 300s | 592s | **+292s (197% over!)** |
| eee939dc | 300s | 366s | +66s (22% over) |

**Implications**:
1. Timeout enforcement is not killing the agent process
2. Agent continues running but is marked as "failed" at timeout threshold
3. Resources are wasted - agents run for 2-3x the timeout limit before actually stopping
4. This explains the high failure rate - legitimate research was happening but being cut off prematurely

---

## Task Pattern Analysis

All 5 failed tasks were **comprehensive async research tasks** with these characteristics:

1. **Task Type**: Broad research questions requiring:
   - Web searches
   - Multiple source synthesis
   - Detailed documentation writing
   - Messaging back results

2. **Common Instructions**: All tasks included messaging instructions:
   ```
   IMPORTANT: When you complete this task, send your result via the messaging system:
   mcp__orchestrator__send_message(...)
   ```

3. **Timeout Context**:
   - Configured timeout for researcher-opus: **1200s (20 minutes)**
   - Actual timeouts enforced: 120s and 300s (from error messages)
   - **This suggests spawning code is overriding agent spec timeout!**

---

## Root Cause Hypothesis

### Primary Issue: Timeout Override

The orchestrator is likely spawning researcher-opus with explicit timeout values that OVERRIDE the agent spec's 1200s setting:

```python
# Suspected code pattern in orchestrator
spawn_agent(
    agent_type="researcher-opus",
    timeout=300  # <-- Hardcoded override, ignores agent_specs.json!
)
```

**Evidence**:
- Agent spec says 1200s
- All Dec 10 tasks failed at "300s timeout"
- Dec 13 task failed at "120s timeout" (even shorter!)
- Execution times show agents were working but hit artificial deadline

### Secondary Issue: Timeout Not Enforced Properly

Even with the wrong timeout values, agents continued running past the deadline:
- 300s timeout → agent ran for 635s
- 300s timeout → agent ran for 620s
- 300s timeout → agent ran for 592s

**This indicates**:
1. Timeout triggers "failure" status but doesn't kill the process
2. Agent continues consuming resources for 2-3x stated timeout
3. Results are discarded even if agent eventually completes

---

## Recommendations

### 1. Fix Timeout Override (CRITICAL)

**Action**: Audit orchestrator spawn code to ensure agent spec timeouts are respected

**Files to check**:
- `mcp-servers/orchestrator/src/spawn_agent.py` (or equivalent)
- Look for hardcoded `timeout=300` or `timeout=120` parameters
- Ensure default timeout comes from `agent_specs.json`

**Expected fix**:
```python
# BEFORE (suspected)
timeout = request.timeout or 300  # Default 300s

# AFTER (correct)
agent_spec = load_agent_spec(agent_type)
timeout = request.timeout or agent_spec["recommended_timeout_seconds"]
```

---

### 2. Fix Timeout Enforcement (HIGH)

**Action**: Ensure timeout actually kills the agent process

**Current behavior**:
- Sets `error_message = "Agent timed out after X seconds"`
- Agent continues running

**Expected behavior**:
- Send SIGTERM to agent process
- After 5s grace period, send SIGKILL
- Immediately return failure to caller

**Implementation**:
```python
import signal

# Set up timeout handler
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(timeout_seconds)

try:
    result = agent.run(task)
finally:
    signal.alarm(0)  # Cancel alarm
```

---

### 3. Reevaluate Task Suitability (MEDIUM)

**Question**: Are these tasks appropriate for researcher-opus?

**Current tasks** (all comprehensive research):
- 4-5 different research questions per task
- Requires web search, synthesis, documentation
- Expected to message results back
- Takes 10-20 minutes (based on execution times)

**Alternative approach**:
1. Use **research-coordinator-sonnet** ($0.35/task) to:
   - Break research into smaller questions
   - Spawn multiple analyst-sonnet agents ($0.30/task) in parallel
   - Synthesize results
2. Reserve researcher-opus for:
   - Single, deep research questions
   - Complex architectural analysis
   - Tasks where Opus reasoning is essential

**Cost comparison**:
- Current: researcher-opus ($0.73) × 1 task = **$0.73** (but 83% fail)
- Alternative: research-coordinator-sonnet ($0.35) + 3× analyst-sonnet ($0.30) = **$1.25** (better success rate)

---

### 4. Monitor Success Rate After Fixes (LOW)

After implementing fixes 1-2, monitor next 10 researcher-opus spawns:

**Target metrics**:
- Success rate: 80%+ (up from 16.7%)
- Avg execution time: Under 800s (well below 1200s timeout)
- Max execution time: Under 1000s

**If success rate remains below 60%**:
- Consider deprecating researcher-opus
- Use research-coordinator-sonnet + analyst-sonnet pattern instead

---

## Immediate Actions Taken

### 1. ✅ Cleaned Up Incomplete Sessions

Cleaned up 6 incomplete agent sessions (older than 7 days):
- 1× python-coder-haiku (2025-12-06)
- 1× analyst-sonnet (2025-12-08)
- 2× coder-haiku (2025-12-09)
- 1× sandbox-haiku (2025-12-09)
- 1× test-coordinator-sonnet (2025-12-12)

All marked as failed with error: "Agent did not complete - assumed crashed or timed out (auto-cleanup)"

### 2. ✅ Updated Agent Timeouts (Other Agents)

Updated timeout values in `agent_specs.json` for 4 agents based on execution data analysis:

| Agent | Old Timeout | New Timeout | Reason |
|-------|------------|-------------|--------|
| python-coder-haiku | 600s | **900s** | Max observed 3343s, P95=582s |
| coder-haiku | 600s | **1200s** | P95=855s exceeded old timeout |
| lightweight-haiku | 180s | **600s** | P95=372s exceeded old timeout |
| research-coordinator-sonnet | 1800s | **600s** | Max observed only 330s |

**researcher-opus timeout kept at 1200s** - timeout is adequate, enforcement is the issue.

---

## Next Steps

### For User

**Decision required**: Should we continue using researcher-opus given:
1. 83% failure rate
2. $0.73 per task (most expensive)
3. Tasks seem better suited for research-coordinator + analyst pattern

**Options**:
A. Fix timeout issues and retry with same task types
B. Switch to research-coordinator-sonnet for comprehensive research
C. Reserve researcher-opus for single, focused deep-dive questions only

### For Implementation

1. **Audit orchestrator spawn code** - Check for timeout override bug
2. **Implement proper timeout enforcement** - Kill process at timeout
3. **Add pre-flight validation** - Warn if task seems too complex for agent
4. **Create test case** - Spawn researcher-opus with known-good task to verify fixes

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/RESEARCHER_OPUS_FAILURE_ANALYSIS.md
