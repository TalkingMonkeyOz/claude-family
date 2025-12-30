# Claude Family System Audit - 2025-12-27

## Executive Summary

Audit of recent system changes to determine what's actually working vs. what was designed.

**Status**: 🟡 **Partially Working** - Infrastructure exists, effectiveness unclear

---

## 1. Skills System 🟡 PARTIALLY WORKING

### Configuration Status: ✅ EXISTS
- **Location**: `.claude/hooks.json` lines 3-13
- **Hook Type**: `UserPromptSubmit` → Forced-eval prompt
- **Prompt**: "Evaluate: Does this task benefit from a skill? Check: database-operations (SQL), work-routing (feedback/features), code-review (commits), session-management (start/end), project-ops (setup), messaging (coordination). Use Skill tool if applicable."
- **Timeout**: 2 seconds

### Skills Inventory: ✅ COMPLETE
**Project Skills** (`.claude/skills/`):
- agentic-orchestration/
- code-review/
- database-operations/
- doc-keeper/
- feature-workflow/
- messaging/
- project-ops/
- session-management/
- testing/
- winforms/
- work-item-routing/
- wpf-ui/

**Global Skills** (`~/.claude/skills/`):
- messaging/SKILL.md
- project-ops/SKILL.md

### Questions:
1. ❓ **Is the prompt actually being shown/evaluated on each user message?**
   - No visible evidence in this conversation
   - User reports not seeing improvements
2. ❓ **Does this trigger on ALL projects or only claude-family?**
   - hooks.json is project-local, not global
   - Other projects may not have this configured

### Verdict: 🟡 **CONFIGURED BUT EFFECTIVENESS UNKNOWN**

---

## 2. Auto-Apply Instructions 🟡 PARTIALLY WORKING

### Configuration Status: ✅ EXISTS
- **Hook**: `PreToolUse` for `Write` and `Edit` tools
- **Script**: `C:/Projects/claude-family/scripts/instruction_matcher.py`
- **Timeout**: 5 seconds
- **Mechanism**: Matches file path against glob patterns, injects matching instructions

### Instruction Files: ✅ COMPLETE (9 files)
**Global** (`~/.claude/instructions/`):
1. `a11y.instructions.md` - Accessibility (WCAG AA)
2. `csharp.instructions.md` - C# conventions, async patterns
3. `markdown.instructions.md` - Markdown formatting
4. `mvvm.instructions.md` - MVVM patterns for ViewModels/XAML
5. `playwright.instructions.md` - E2E testing
6. `sql-postgres.instructions.md` - PostgreSQL best practices
7. `winforms.instructions.md` - WinForms rules, layout
8. `winforms-dark-theme.instructions.md` - Dark theme colors
9. `wpf-ui.instructions.md` - WPF UI library patterns **(User specifically asked about this!)**

**Project-Specific** (`.claude/instructions/`):
- None found in claude-family project

### How It Should Work:
1. User calls `Edit` or `Write` tool
2. PreToolUse hook triggers BEFORE tool execution
3. instruction_matcher.py receives file path
4. Matches path against `applyTo` patterns in instruction files
5. Returns matching instructions as `additionalContext`
6. Claude Code injects instructions into context

### Questions:
1. ❓ **Is instruction_matcher.py actually being called?**
   - Configured in hooks.json
   - But no visible evidence it's running
2. ❓ **Are instructions visible in Claude's context when editing?**
   - User reports no WPF UI skill improvement
   - Suggests instructions may NOT be injecting
3. ❓ **Does this work in OTHER projects?**
   - hooks.json is project-local
   - Other projects wouldn't have this hook unless copied

### Test Needed:
Create/edit a .cs file and check if C# instructions appear in context

### Verdict: 🟡 **CONFIGURED BUT MAY NOT BE FIRING**

---

## 3. Agent System 🔴 ISSUES CONFIRMED

### Success Rates (Last 30 Days):

| Agent Type | Spawns | Success Rate | Status |
|------------|--------|--------------|--------|
| **researcher-opus** | 6 | **16.7%** 🔴 | FAILING |
| **sandbox-haiku** | 2 | **0%** 🔴 | FAILING |
| **analyst-sonnet** | 14 | **42.9%** 🟡 | LOW |
| **architect-opus** | 5 | **40.0%** 🟡 | LOW |
| **planner-sonnet** | 6 | **50.0%** 🟡 | MEDIOCRE |
| **research-coordinator** | 4 | **50.0%** 🟡 | MEDIOCRE |
| **reviewer-sonnet** | 9 | **55.6%** 🟡 | MEDIOCRE |
| **coder-haiku** | 56 | **64.3%** 🟢 | OK |
| **tester-haiku** | 3 | **66.7%** 🟢 | OK |
| **python-coder-haiku** | 37 | **78.4%** 🟢 | GOOD |
| **lightweight-haiku** | 12 | **83.3%** 🟢 | GOOD |
| **web-tester-haiku** | 2 | **100%** ✅ | EXCELLENT |
| **doc-keeper-haiku** | 1 | **100%** ✅ | EXCELLENT |
| **security-sonnet** | 1 | **100%** ✅ | EXCELLENT |

### Issues:
1. 🔴 **researcher-opus**: 83% failure rate (5/6 failed)
   - Known issue - there's a TODO to investigate/deprecate
2. 🔴 **sandbox-haiku**: 100% failure rate (2/2 failed)
   - New finding!
3. 🟡 **Sonnet agents** generally underperforming (40-56% success)
   - analyst, reviewer, planner all <60%
4. 🟢 **Haiku agents** performing better (64-100% success)
   - Lightweight, python-coder, web-tester all strong

### Verdict: 🔴 **SIGNIFICANT ISSUES - Need investigation**

---

## 4. Logging System ✅ WORKING

### Session Logging: ✅ CONFIRMED WORKING
**Evidence**: Database query shows active sessions logged:
- Dec 27 (today): claude-family (1 session)
- Dec 26: claude-family (1), claude-family-manager-v2 (2)
- Dec 23: ato-tax-agent (1), claude-family (1), claude-family-manager-v2 (1)
- Dec 21: claude-family (9), claude-family-manager-v2 (4), ATO-Tax-Agent (1)
- Dec 20: **claude-family (165 sessions!!)** - very active day

### Mechanism:
- **Hook**: SessionStart → `session_startup_hook.py`
- **Action**: Creates record in `claude.sessions` table
- **Auto-logged**: Yes, session_id generated and exported as env var

### MCP Usage Logging: 🟡 CONFIGURED
- **Hook**: PostToolUse (matcher: `mcp__.*`)
- **Script**: `mcp_usage_logger.py`
- **Status**: Configured, but usage not verified in this audit

### Verdict: ✅ **SESSION LOGGING CONFIRMED WORKING**

---

## 5. Documentation Strategy 🟡 UNCLEAR

### The Plan: Shorter, interrelated documents
**Implementation**: Split large files into focused pieces (e.g., Session User Stories split into multiple files)

**Evidence of Strategy**:
- `Session User Stories - Overview.md`
- `Session User Story - Cross-Project Message.md`
- `Session User Story - End Session.md`
- `Session User Story - Launch Project.md`
- `Session User Story - Resume Session.md`
- `Session User Story - Spawn Agent.md`

**Questions**:
1. ❓ Is this pattern being followed consistently for NEW docs?
2. ❓ Are existing large docs being split or just new ones?
3. ❓ Is there guidance for "how small is too small"?

### Vault Compliance:
- User mentioned "93% non-compliant files" in TODO_NEXT_SESSION.md
- Suggests documentation standards not being met

### Verdict: 🟡 **PATTERN EXISTS, ADOPTION UNCLEAR**

---

## 6. WPF UI Skill ❓ EFFECTIVENESS UNKNOWN

### Skill Status: ✅ EXISTS
- **Location**: `.claude/skills/wpf-ui/skill.md`
- **Size**: 1,050 lines (comprehensive)
- **Content**: Real-world examples, XAML templates, 6 example files
- **Global Instruction**: `~/.claude/instructions/wpf-ui.instructions.md` (8,734 bytes)

### User Feedback:
> "i cant say i have seen a significant improvement"

### Possible Reasons:
1. **Skill not being invoked** - Skills prompt may not be triggering
2. **Instruction not being injected** - PreToolUse hook may not be firing
3. **Skill content not relevant** - Examples don't match user's use cases
4. **Claude not applying knowledge** - Skill exists but not used effectively

### Test Needed:
1. Edit a XAML or WPF ViewModel file
2. Check if wpf-ui.instructions.md content appears in context
3. Check if Claude references WPF UI skill patterns

### Verdict: ❓ **EXISTS BUT USER REPORTS NO IMPROVEMENT**

---

## 7. Critical Finding: Hooks May Not Fire Globally

### Issue:
**`.claude/hooks.json` is project-local, not global**

This means:
- Skills-first evaluation: ONLY in claude-family project
- Auto-apply instructions: ONLY in claude-family project
- Other projects (ato-tax-agent, claude-family-manager-v2, etc.): ❌ NO HOOKS

### Impact:
- User works on multiple projects
- Most projects don't have the hooks configured
- User wouldn't see skills prompting or instructions injecting

### Solution Options:
1. **Copy `.claude/hooks.json` to all projects** (manual, fragile)
2. **Create global hooks** (if Claude Code supports `~/.claude/hooks/hooks.json`)
3. **Use plugin system** (if Claude Code plugins can provide hooks globally)

---

## 8. New Issues Found

### 1. Acknowledge Function Broken 🔴
**Error**: `could not determine data type of parameter $1`
**Location**: `mcp__orchestrator__acknowledge()` function
**Impact**: Cannot defer old messages, message accountability broken

### 2. 10 Unactioned Messages 🟡
**Status**: Deferred (attempted but failed due to acknowledge bug)
**Range**: Nov 29 - Dec 21 (predates accountability system)

---

## Recommendations

### Immediate (High Priority):
1. **Test if hooks are firing**
   - Edit a .cs file, check if csharp.instructions.md appears in context
   - Check Claude Code logs for hook execution
2. **Fix acknowledge function**
   - Debug SQL parameter issue in orchestrator
3. **Investigate failing agents**
   - researcher-opus (16.7% success) - fix or deprecate
   - sandbox-haiku (0% success) - fix or remove
   - analyst-sonnet (42.9%) - improve or replace

### Short-Term (This Week):
1. **Make hooks global**
   - Test if `~/.claude/hooks/hooks.json` works
   - If not, copy to all active projects
2. **Verify instruction injection working**
   - Add debug logging to instruction_matcher.py
   - Confirm instructions appear in context
3. **Test WPF UI skill effectiveness**
   - Use on real WPF task
   - Get specific user feedback on what's missing

### Medium-Term (Next Sprint):
1. **Document hook system**
   - How hooks work
   - How to verify they're firing
   - Troubleshooting guide
2. **Agent performance review**
   - Analyze failures for patterns
   - Improve prompts/configs for low-performing agents
3. **Documentation compliance**
   - Address 93% non-compliant vault files
   - Create compliance checking tool

---

## Summary Table

| System | Status | Evidence | Action Needed |
|--------|--------|----------|---------------|
| **Skills System** | 🟡 Config exists | hooks.json | Verify firing, test effectiveness |
| **Auto-Instructions** | 🟡 Config exists | hooks.json + matcher.py | Verify firing, test injection |
| **Agent System** | 🔴 Issues | 16-50% failure rates | Fix/deprecate failing agents |
| **Session Logging** | ✅ Working | DB sessions logged | None - working well |
| **MCP Logging** | 🟡 Configured | hooks.json | Verify usage data captured |
| **Documentation** | 🟡 Unclear | Split files exist | Check adoption, compliance |
| **WPF UI Skill** | ❓ Unknown | Skill exists, user says no improvement | Test and get specific feedback |

---

## Next Steps for This Session:

1. ✅ Defer old messages (attempted - acknowledge broken)
2. ✅ Create audit report (this document)
3. ⏭️ Test if hooks fire (create/edit file, check for instructions)
4. ⏭️ Fix acknowledge function
5. ⏭️ Check if hooks.json can be global

---

**Audit Date**: 2025-12-27
**Auditor**: claude-code-unified (session resumed)
**Next Review**: After hook firing tests complete
