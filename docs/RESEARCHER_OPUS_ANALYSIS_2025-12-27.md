# researcher-opus Agent Analysis

**Date:** 2025-12-27
**Status:** FAILING - 83% failure rate
**Recommendation:** DEPRECATE or FIX TIMEOUT OVERRIDE

---

## Statistics

- **Total Sessions:** 6
- **Successful:** 1 (17%)
- **Failed:** 5 (83%)
- **Avg Execution Time:** 430 seconds (~7 minutes)
- **Total Cost:** $4.35
- **Cost Per Task:** $0.725
- **First Spawn:** 2025-12-08
- **Last Spawn:** 2025-12-13

---

## Root Cause: Timeout Configuration Mismatch

### Agent Spec Configuration
```json
"recommended_timeout_seconds": 1200  // 20 minutes
```

### Actual Timeout Behavior
- Session 498d2adb: **120 seconds** (2 minutes)
- Sessions 9b6268b0-eee939dc: **300 seconds** (5 minutes)

**PROBLEM:** The recommended_timeout_seconds is NOT being respected. An override is forcing shorter timeouts.

---

## Failed Tasks Analysis

All 5 failures were timeout-related on legitimate research tasks:

### 1. C# Codebase Search (120s timeout)
**Task:** Search nimbus-user-loader for OData entity names
**Execution:** 133 seconds
**Timeout:** 120s
**Issue:** Complex C# codebase search needs more time

### 2. Hook Systems Research (300s timeout)
**Task:** Research hook/trigger systems, process enforcement, automation
**Execution:** 635 seconds
**Timeout:** 300s
**Issue:** Comprehensive research with web searches

### 3. Database-Driven Development Research (300s timeout)
**Task:** Research dev tracking databases, data governance, schema patterns
**Execution:** 620 seconds
**Timeout:** 300s
**Issue:** Comprehensive research requiring multiple sources

### 4. AI Orchestration Tools Research (300s timeout)
**Task:** Research multi-agent AI systems, orchestration frameworks
**Execution:** 591 seconds
**Timeout:** 300s
**Issue:** Comprehensive research with citations

### 5. LangChain/LlamaIndex Research (300s timeout)
**Task:** Research LLM routing patterns in frameworks
**Execution:** 365 seconds
**Timeout:** 300s
**Issue:** Framework documentation analysis

---

## Successful Task

**Task:** Anthropic routing patterns research
**Execution:** 237 seconds (within 300s timeout)
**Result:** Successful completion

---

## Recommendations

### Option 1: FIX TIMEOUT OVERRIDE ISSUE ⭐ RECOMMENDED
**Action:** Investigate why 1200s timeout is being overridden to 120s/300s
**Files to Check:**
- `mcp-servers/orchestrator/server.py` - spawn_agent timeout logic
- `mcp-servers/orchestrator/orchestrator_prototype.py` - timeout enforcement
- Any default timeout configurations

**Expected Fix:** Respect `recommended_timeout_seconds` from agent_specs.json

### Option 2: USE RESEARCH-COORDINATOR-SONNET INSTEAD
**Rationale:**
- Research-coordinator spawns multiple researchers in parallel
- Uses Sonnet ($0.35/task) instead of Opus ($0.725/task)
- Better suited for comprehensive research tasks
- Can coordinate async research workflows

**Migration:** Replace researcher-opus calls with research-coordinator-sonnet

### Option 3: DEPRECATE RESEARCHER-OPUS
**Rationale:**
- 83% failure rate unacceptable
- Too expensive for current success rate ($0.725 per failed attempt)
- Research-coordinator-sonnet + analyst-sonnet can handle use cases
- Opus 4.5 better suited for architecture/planning (architect-opus)

**Action:**
1. Move researcher-opus to `removed_agents` in agent_specs.json
2. Archive config to configs/deprecated/
3. Update documentation recommending alternatives

---

## Decision Required

**Immediate:** Fix timeout override issue (check orchestrator code)
**Short-term:** Test with fixed timeout to validate 1200s is sufficient
**Long-term:** Consider replacing with research-coordinator pattern if timeout fix doesn't improve success rate

---

## Cost Impact

**Current:** $0.725 per task × 83% failure = wasted $3.625 of $4.35 total
**If Fixed:** Same cost, better success rate
**If Switched to research-coordinator:** $0.35 per task (52% cheaper) + coordination overhead

---

## Next Steps

1. ✅ **Complete this analysis**
2. ⏳ **Investigate timeout override in orchestrator code**
3. ⏳ **Test with corrected timeout**
4. ⏳ **Decide: Fix or Deprecate**
5. ⏳ **Update agent_specs.json accordingly**
