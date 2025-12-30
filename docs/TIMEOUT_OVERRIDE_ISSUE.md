# Timeout Override Issue - Root Cause Analysis

## Problem Summary

Agent timeouts are being overridden in multiple places, causing agents to fail prematurely with incorrect timeout values.

---

## Root Causes Identified

### 1. Hardcoded Default in sandbox_runner.py (CRITICAL)

**File**: `mcp-servers/orchestrator/sandbox_runner.py:86`

**Issue**:
```python
async def run_sandboxed(
    self,
    task: str,
    workspace_path: str,
    timeout: int = 300,  # <-- HARDCODED 300s default!
    gui: bool = False,
    model: str = "claude-sonnet-4-20250514"
) -> Dict[str, Any]:
```

**Impact**: All sandboxed agents default to 300s timeout regardless of agent_specs.json

**Evidence from database**:
- researcher-opus (spec: 1200s) → failed at "300s timeout"
- All 5 failed researcher-opus tasks show "timed out after 300 seconds"

**Fix**:
```python
async def run_sandboxed(
    self,
    task: str,
    workspace_path: str,
    timeout: int = None,  # Changed from 300
    gui: bool = False,
    model: str = "claude-sonnet-4-20250514"
) -> Dict[str, Any]:
    # Get timeout from agent spec if not provided
    if timeout is None:
        # TODO: Pass agent_type to this method to look up spec timeout
        timeout = 600  # Safe default fallback
```

---

### 2. Parameter Override Pattern

**File**: `mcp-servers/orchestrator/orchestrator_prototype.py:335`

**Code**:
```python
# Set timeout
timeout = timeout or spec['recommended_timeout_seconds']
```

**Behavior**:
- If caller passes `timeout=X`, it OVERRIDES the agent spec
- If caller passes `timeout=None`, it uses agent spec
- This is **by design** but allows callers to override specs

**Impact**: Legitimate when caller knows better, but dangerous when caller uses wrong values

**Fix**: Add validation to warn/prevent unreasonable overrides

```python
# Set timeout with validation
requested_timeout = timeout
spec_timeout = spec['recommended_timeout_seconds']

if requested_timeout and requested_timeout < spec_timeout * 0.5:
    # Warn if override is less than 50% of recommended
    print(f"WARNING: Timeout override {requested_timeout}s is much lower than spec {spec_timeout}s",
          file=sys.stderr)

timeout = requested_timeout or spec_timeout
```

---

### 3. Project-Level Timeout Overrides (User Report)

**User Finding**: "projects were overriding the timeouts sometimes"

**Hypothesis**: Project code may be calling spawn_agent with explicit timeout values

**Places to check**:
1. Python scripts in project directories calling orchestrator MCP
2. Skills that spawn agents with hardcoded timeouts
3. Coordinator agents that spawn sub-agents

**Action Required**: Audit codebase for spawn_agent calls with timeout parameters

```bash
# Search for spawn_agent calls with timeout
grep -r "spawn_agent" --include="*.py" C:/Projects/ | grep -i timeout
```

---

## Evidence from Failed Tasks

### researcher-opus Failure Pattern

| Session | Stated Timeout | Actual Execution | Delta |
|---------|---------------|------------------|-------|
| 498d2adb | 120s | 133s | +13s |
| 9b6268b0 | 300s | 635s | +335s |
| dbb69cd0 | 300s | 620s | +320s |
| 6c77a819 | 300s | 592s | +292s |
| eee939dc | 300s | 366s | +66s |

**Analysis**:
- 4 out of 5 tasks show "300s timeout" → Points to sandbox_runner.py default
- 1 task shows "120s timeout" → Project-level override?
- Agents continued running past stated timeout → Enforcement issue

---

## Timeout Enforcement Bug

### Current Behavior

**File**: `mcp-servers/orchestrator/sandbox_runner.py:172-180`

```python
except asyncio.TimeoutError:
    proc.kill()
    await proc.wait()
    return {
        "success": False,
        "error": f"Agent timed out after {timeout} seconds",
        "output": None,
        "execution_time": timeout  # <-- Returns timeout value, not actual execution time!
    }
```

**Problem**: Returns `execution_time: timeout` instead of actual elapsed time

**Evidence**: Database shows execution_time_seconds = 635s but error says "timed out after 300s"

**This suggests TWO scenarios**:
1. ❌ The timeout handler is NOT being triggered (agent runs past timeout)
2. ❌ The execution_time is being calculated AFTER timeout occurs

**Fix Required**: Investigate why agents run past timeout. Possible causes:
- `proc.kill()` not working
- Agent process spawns child processes that aren't killed
- Timeout applied to wrong scope (only stdin/stdout, not full process)

---

## Recommended Fixes

### Priority 1: Fix sandbox_runner.py Default (CRITICAL)

```python
# Before
async def run_sandboxed(
    self,
    task: str,
    workspace_path: str,
    timeout: int = 300,  # WRONG
    ...
)

# After
async def run_sandboxed(
    self,
    task: str,
    workspace_path: str,
    agent_type: str,  # ADD THIS
    timeout: int = None,  # CHANGE THIS
    ...
):
    # Get timeout from spec if not provided
    if timeout is None:
        spec = load_agent_spec(agent_type)
        timeout = spec.get('recommended_timeout_seconds', 600)
```

### Priority 2: Add Timeout Override Validation

```python
def validate_timeout_override(agent_type: str, requested_timeout: int, spec_timeout: int) -> int:
    """Validate and warn about timeout overrides."""
    if requested_timeout < spec_timeout * 0.5:
        print(f"⚠️ WARNING: {agent_type} timeout override {requested_timeout}s is <50% of spec {spec_timeout}s",
              file=sys.stderr)

    if requested_timeout > spec_timeout * 2:
        print(f"⚠️ WARNING: {agent_type} timeout override {requested_timeout}s is >200% of spec {spec_timeout}s",
              file=sys.stderr)

    return requested_timeout
```

### Priority 3: Fix Timeout Enforcement

**Investigate why agents run past timeout**:
1. Check if `proc.kill()` is effective
2. Verify child processes are killed
3. Consider using process groups

**Potential fix**:
```python
# Use process group to kill all child processes
import os
import signal

# When spawning process
proc = await asyncio.create_subprocess_exec(
    *cmd,
    preexec_fn=os.setsid,  # Create new process group
    ...
)

# When timeout occurs
try:
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # Kill entire process group
    await asyncio.sleep(5)  # Grace period
    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # Force kill
except ProcessLookupError:
    pass  # Already dead
```

### Priority 4: Audit Project-Level Overrides

**Action**: Search for spawn_agent calls with timeout parameters

```bash
# Find all spawn_agent calls
grep -rn "spawn_agent" C:/Projects/claude-family/ --include="*.py" | grep -v "def spawn_agent"

# Look for timeout parameters
grep -rn "timeout\s*=" C:/Projects/claude-family/ --include="*.py" | grep -i spawn
```

**Expected findings**: Scripts or skills that hardcode timeouts

**Resolution**: Remove hardcoded timeouts, let agent specs dictate defaults

---

## Testing Plan

### 1. Verify sandbox_runner.py Fix

```python
# Test case: Spawn researcher-opus (spec: 1200s)
result = await orchestrator.spawn_agent(
    agent_type="researcher-opus",
    task="Test task",
    workspace_dir="/tmp/test",
    timeout=None  # Should use 1200s from spec
)
# Verify: timeout used should be 1200s, not 300s
```

### 2. Verify Timeout Enforcement

```python
# Test case: Spawn agent with short timeout
result = await orchestrator.spawn_agent(
    agent_type="coder-haiku",
    task="while True: pass",  # Infinite loop
    workspace_dir="/tmp/test",
    timeout=5  # 5 second timeout
)
# Verify: Process killed at 5s, not allowed to run indefinitely
```

### 3. Monitor Next 20 Spawns

After fixes:
- Track timeout values used
- Track actual execution times
- Verify no agents exceed their timeout limits

---

## Impact Assessment

### Agents Affected

| Agent | Spec Timeout | Likely Override | Impact |
|-------|-------------|----------------|--------|
| researcher-opus | 1200s | 300s (sandbox default) | 83% failure rate |
| All sandboxed agents | Varies | 300s (sandbox default) | Premature failures |

### Cost Impact

**researcher-opus failures**:
- 5 failed tasks × $0.73 = **$3.65 wasted**
- Tasks actually completed work (ran 300-635s) but marked as failed
- Research was discarded even though valuable

**Opportunity cost**:
- If tasks had completed, they would have provided value
- Instead, user had to spawn new agents or abandon work

---

## Conclusion

The timeout override issue has **three root causes**:

1. **Hardcoded 300s default in sandbox_runner.py** (confirmed)
2. **Parameter override design allows callers to override specs** (by design, but abused)
3. **Project-level code may be passing explicit timeouts** (user-reported, needs audit)

**Fixes required**:
1. Change sandbox_runner.py default from 300s to None, look up spec
2. Add validation/warnings for timeout overrides
3. Fix timeout enforcement (agents run past timeout)
4. Audit project code for hardcoded timeout values

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/TIMEOUT_OVERRIDE_ISSUE.md
