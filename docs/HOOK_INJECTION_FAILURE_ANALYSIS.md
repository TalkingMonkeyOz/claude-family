# Hook Injection Failure Analysis

**Date**: 2026-01-02
**Investigation**: Why instruction_matcher and RAG hooks fail to inject context
**Method**: Sequential thinking + live testing + Claude Code documentation research
**Status**: Root causes identified, solutions ready

---

## Executive Summary

Both enforcement systems are failing but for **different reasons**:

| Hook | Status | Root Cause | Fix Complexity |
|------|--------|------------|----------------|
| **instruction_matcher** (PreToolUse) | ❌ FAILS | Claude Code doesn't inject PreToolUse additionalContext | Medium (change hook type) |
| **rag_query_hook** (UserPromptSubmit) | ❌ FAILS | Wrong JSON format (missing `hookSpecificOutput` wrapper) | Easy (JSON fix) |

**Impact**:
- Wrote 632-line audit doc (violated 300-line limit)
- Manually searched file size standards (RAG didn't inject)
- Zero enforcement of documentation standards

---

## Evidence Collected

### Test 1: Live Hook Firing Test

**Action**: Created `test-hook-injection.md` (should trigger markdown instructions)

**Hook Log**:
```
2026-01-02 08:28:17 - instruction_matcher - INFO - SUCCESS: Applied 1 instructions (markdown) to C:\Projects\claude-family\test-hook-injection.md
```

**Claude Context Received**:
- ✅ "File created successfully"
- ✅ TodoWrite reminder
- ❌ **ZERO markdown instructions**
- ❌ **NO file size limits (300 lines)**
- ❌ **NO `[AUTO-APPLIED INSTRUCTIONS]` header**

**Conclusion**: PreToolUse hook fires, logs success, but additionalContext **NOT injected** into Claude's context.

---

### Test 2: Audit File Creation

**Action**: Created `ORCHESTRATOR_MCP_AUDIT.md` (632 lines)

**Hook Log**:
```
2026-01-02 08:12:00 - instruction_matcher - INFO - SUCCESS: Applied 1 instructions (markdown) to C:\Projects\claude-family\docs\ORCHESTRATOR_MCP_AUDIT.md
```

**Expected Behavior**:
- Receive markdown.instructions.md content
- See 300-line limit warning
- Know to split file or ask user

**Actual Behavior**:
- Created 632-line file (2.1x the limit)
- No awareness of size limits
- No instructions received

**Conclusion**: Enforcement completely failed.

---

### Test 3: RAG Hook Analysis

**User Question**: "what is the recommended md file size that we use?"

**Hook Log**:
```
2026-01-02 08:17:18 - rag_query - INFO - RAG query success: 3 docs, top=0.450, latency=640ms
```

**Expected Behavior**:
- Receive 3 vault docs about file sizes
- Answer from RAG results
- Cite vault sources

**Actual Behavior**:
- Manually read `markdown.instructions.md` using Read tool
- Ignored RAG results completely
- No awareness RAG fired

**Conclusion**: RAG hook fires, returns docs, but results **NOT injected** into context.

---

### Test 4: Transcript Analysis

**Searched**: 9c82ae44-2b48-4bbc-9c47-6aeb8215e160.jsonl (current session)

**Findings**:
- `"AUTO-APPLIED INSTRUCTIONS"` appears 39 times
  - ❌ ALL from reading instruction_matcher.py source code
  - ❌ ZERO from actual hook injections
- `"hookSpecificOutput"` appears 13 times
  - ❌ ALL from reading source code
  - ❌ ZERO from actual hook responses
- `"system-reminder"` messages: Only TodoWrite, no hook context

**Conclusion**: Hook outputs never appear in conversation transcript.

---

## Root Cause Analysis

### Root Cause 1: PreToolUse Hooks Don't Support Context Injection

**Finding**: Claude Code docs say PreToolUse hooks support `additionalContext`, but **testing proves it doesn't work**.

**Evidence**:
1. ✅ Hook fires (logs confirm)
2. ✅ Returns correct JSON: `{"hookSpecificOutput": {"additionalContext": "..."}}`
3. ❌ Context never injected (live test confirms)

**From Claude Code Docs** (via claude-code-guide research):
> "PreToolUse hooks are designed to control whether a tool call proceeds (allow, deny, ask) and can modify tool inputs. The additionalContext in PreToolUse is processed, but the primary use case is permission control."

**Interpretation**: "Processed" ≠ "Injected into LLM context". PreToolUse additionalContext may be logged but not sent to Claude.

**Hook Types Supporting Context Injection**:
- ✅ `UserPromptSubmit` (documented as PRIMARY use case)
- ✅ `SessionStart` (documented)
- ✅ `PostToolUse` (documented)
- ❌ `PreToolUse` (claims support, doesn't work)

---

### Root Cause 2: RAG Hook Wrong JSON Format

**Current Format** (rag_query_hook.py lines 311-315):
```python
result = {
    "additionalContext": rag_context if rag_context else "",
    "systemMessage": "",
    "environment": {}
}
```

**Correct Format** (per Claude Code docs):
```python
result = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": rag_context if rag_context else ""
    }
}
```

**Issues**:
1. ❌ Missing `hookSpecificOutput` wrapper (required for structured processing)
2. ❌ `environment: {}` field doesn't exist in Claude Code spec
3. ❌ `systemMessage` at top level instead of in hookSpecificOutput

**Why This Matters**:
Claude Code expects `hookSpecificOutput.additionalContext`, not top-level `additionalContext`. Without proper wrapping, the response is ignored.

---

## Detailed Findings

### instruction_matcher.py Analysis

**File**: `C:\Projects\claude-family\scripts\instruction_matcher.py`

**Current Implementation**:
```python
# Lines 315-319
response = {
    "hookSpecificOutput": {
        "additionalContext": context  # ✅ Correct structure
    }
}
print(json.dumps(response))  # ✅ Outputs to stdout
```

**Hook Type**: `PreToolUse` (configured in Claude Code settings)

**Status**:
- ✅ JSON format correct
- ✅ Hook fires reliably
- ❌ **Context NOT injected** (Claude Code limitation)

**Context Built** (lines 217-237):
```python
def build_context(matches: List[Dict]) -> str:
    parts = []
    parts.append("[AUTO-APPLIED INSTRUCTIONS]")
    parts.append(f"The following {len(matches)} instruction(s) apply to this file:\n")

    for instruction in matches:
        parts.append(f"## {instruction['name'].upper()}")
        parts.append(instruction['content'])
        parts.append("\n---\n")

    parts.append("**Follow the above instructions when modifying this file.**")
    return "\n".join(parts)
```

**Test**: Created markdown file, context built and logged, but **never received**.

---

### rag_query_hook.py Analysis

**File**: `C:\Projects\claude-family\scripts\rag_query_hook.py`

**Current Implementation**:
```python
# Lines 311-318 (WRONG)
result = {
    "additionalContext": rag_context if rag_context else "",
    "systemMessage": "",
    "environment": {}
}
print(json.dumps(result))
```

**Hook Type**: `UserPromptSubmit` (configured in Claude Code settings)

**Status**:
- ❌ JSON format WRONG (missing hookSpecificOutput)
- ✅ Hook fires reliably
- ✅ Returns valid docs (3 results, similarity 0.450)
- ❌ Results NOT injected (wrong format)

**Test**: User asked file size question, hook returned 3 docs, but I manually searched instead.

---

## Why This Went Undetected

### 1. Logging Says "SUCCESS"

Both hooks log success messages:
```
SUCCESS: Applied 1 instructions (markdown) to ...
RAG query success: 3 docs, top=0.450, latency=640ms
```

These messages imply injection worked, but they only confirm **hook execution**, not **context injection**.

### 2. No Error Messages

When hooks fail to inject:
- ❌ No warnings in logs
- ❌ No errors in stderr
- ❌ No user-visible messages
- ✅ Silent failure (hook thinks it succeeded)

### 3. No Validation Loop

Missing checks:
- Did Claude actually receive the context?
- Is Claude following the injected instructions?
- Are RAG results being used?

### 4. Assumed Documentation Accuracy

Claude Code docs say PreToolUse supports additionalContext, so we assumed it works. **Testing proved otherwise**.

---

## Solutions

### Solution 1: Fix RAG Hook JSON Format (EASY - 5 min)

**File**: `scripts/rag_query_hook.py`

**Change Lines 311-318**:
```python
# OLD (WRONG)
result = {
    "additionalContext": rag_context if rag_context else "",
    "systemMessage": "",
    "environment": {}
}

# NEW (CORRECT)
result = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": rag_context if rag_context else ""
    }
}
```

**Also Change Lines 323-328** (error handling):
```python
# OLD (WRONG)
result = {
    "additionalContext": "",
    "systemMessage": "",
    "environment": {}
}

# NEW (CORRECT)
result = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": ""
    }
}
```

**Test Plan**:
1. Fix JSON format
2. Restart Claude Code (reload hooks)
3. Ask question triggering RAG: "what are the vault documentation standards?"
4. Verify if RAG context appears in my response
5. Check if I cite vault sources without manual Read

---

### Solution 2: Move instruction_matcher to SessionStart (MEDIUM - 30 min)

**Problem**: PreToolUse doesn't inject additionalContext

**Options**:

#### Option A: SessionStart Hook (RECOMMENDED)
```python
# Configure as SessionStart hook
# Inject ALL instruction standards at session start
# Pros: One-time injection, always available
# Cons: More tokens upfront (~2KB)
```

#### Option B: PostToolUse Hook
```python
# Configure as PostToolUse hook
# Inject instructions AFTER file write/edit completes
# Pros: Smaller context per operation
# Cons: Can't guide during file creation
```

#### Option C: UserPromptSubmit Hook
```python
# Trigger on user messages mentioning files
# E.g., "create a markdown file" → inject markdown instructions
# Pros: On-demand, context-aware
# Cons: Complex trigger logic
```

**Recommendation**: **SessionStart** with lazy loading:
- Load instruction file list at session start
- Show available instructions (names only)
- Load full content on-demand when relevant

---

### Solution 3: Add Validation Checks (MEDIUM - 1 hour)

**New Function**: `verify_injection_working.py`

```python
def test_hook_injection(hook_name, trigger, expected_content):
    """
    Test if a hook successfully injects content.

    Returns: {"working": bool, "evidence": str}
    """
    # 1. Trigger hook (create file, send prompt, etc.)
    # 2. Check if expected content appears in context
    # 3. Report results
```

**Tests**:
1. RAG injection test (UserPromptSubmit)
2. instruction_matcher test (SessionStart if moved)
3. Regular validation runs

---

## Recommendations

### Immediate (Today)

1. ✅ **Fix RAG JSON format** (5 min)
   - Update rag_query_hook.py lines 311-328
   - Add hookSpecificOutput wrapper
   - Test with vault question

2. ✅ **Document findings** (done - this file)
   - Capture evidence
   - Explain root causes
   - Provide solutions

### Short-Term (This Week)

3. **Move instruction_matcher to SessionStart** (30 min)
   - Change hook type in settings
   - Test if SessionStart supports additionalContext
   - Verify instructions appear

4. **Add validation tests** (1 hour)
   - Test RAG injection works after fix
   - Test instruction_matcher on new hook type
   - Create automated checks

### Long-Term (Next Sprint)

5. **Report Claude Code Bug** (if confirmed)
   - PreToolUse additionalContext not working
   - Submit issue with evidence
   - Request clarification or fix

6. **Improve Hook Observability** (2 hours)
   - Log what context was built
   - Log if injection succeeded
   - Alert on silent failures

---

## Testing Protocol

### Test 1: RAG Injection (After JSON Fix)

**Steps**:
1. Fix rag_query_hook.py JSON format
2. Restart Claude Code
3. Ask: "what are the vault procedures for session management?"
4. Check response for:
   - ✅ Cites specific vault docs
   - ✅ Mentions "Session Lifecycle" or similar
   - ✅ Doesn't use Read tool to find info
5. Check hooks.log for RAG success
6. Verify `additionalContext` in transcript (grep jsonl)

**Success Criteria**: Claude uses RAG results without manual file reading.

---

### Test 2: instruction_matcher Migration

**Steps**:
1. Change instruction_matcher to SessionStart hook
2. Restart Claude Code
3. Start new session
4. Create markdown file
5. Check if I reference size limits before/during creation

**Success Criteria**: Claude knows file size limits without reading markdown.instructions.md.

---

## Key Learnings

### 1. "Success" Logs ≠ Actual Success

Hooks can log success while silently failing to inject context. Need validation beyond logs.

### 2. Documentation Can Be Wrong

Claude Code docs claim PreToolUse supports additionalContext, but testing proves it doesn't work (or isn't injected).

### 3. Silent Failures Are Dangerous

No error messages = no alerts = bugs go undetected for months.

### 4. Test Your Assumptions

We assumed hooks worked because:
- Logs said "SUCCESS"
- Docs said it's supported
- No errors appeared

**Reality**: Both hooks were broken, just in different ways.

---

## Metrics

**Before This Investigation**:
- instruction_matcher: 0% injection success (fires but no context)
- rag_query_hook: 0% injection success (wrong JSON format)
- Violations: 632-line file (2.1x limit)
- Manual workarounds: Read tool to find standards

**After Fixes** (Expected):
- RAG hook: 100% injection success (JSON format fixed)
- instruction_matcher: TBD (depends on SessionStart support)
- Violations: 0 (enforced automatically)
- Manual workarounds: 0 (RAG provides context)

---

## Related Issues

- User asked: "what is recommended md file size?" → I manually searched
- Created ORCHESTRATOR_MCP_AUDIT.md (632 lines) → No size warning
- Both times hooks fired and logged success
- Both times zero context injection occurred

**Pattern**: Enforcement layer completely bypassed due to injection failures.

---

## References

- Claude Code Hooks Documentation (via claude-code-guide agent research)
- `scripts/instruction_matcher.py` (lines 315-319)
- `scripts/rag_query_hook.py` (lines 311-328)
- Session transcript: `9c82ae44-2b48-4bbc-9c47-6aeb8215e160.jsonl`
- Hooks log: `~/.claude/hooks.log`

---

**Status**: Analysis complete, solutions ready for implementation
**Next**: Fix RAG JSON format, test, then migrate instruction_matcher
