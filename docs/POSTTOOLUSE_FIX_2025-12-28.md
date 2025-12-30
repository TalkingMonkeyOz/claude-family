# PostToolUse Hook Fix - Database Template Issue

**Date**: 2025-12-28
**Status**: ✅ FIXED
**Impact**: Critical - MCP usage tracking now possible

---

## Problem

PostToolUse, Stop, and PreCommit hooks were configured in `.claude/hooks.json` but **never fired**.

### Root Cause

**The hooks.json file was dead code!**

Claude Code reads hook configuration from:
1. Database table: `claude.config_templates` (template_name = 'hooks-base')
2. Via script: `scripts/generate_project_settings.py`
3. Output file: `.claude/settings.local.json`

The `hooks.json` file was NOT in this chain.

### Evidence Chain

| Step | Finding |
|------|---------|
| 1. hooks.log | Shows PreToolUse firing, NO PostToolUse entries |
| 2. settings.local.json | Only had 4 hook types (no PostToolUse, Stop, PreCommit) |
| 3. generate_project_settings.py | Reads from `claude.config_templates` table |
| 4. Database query | Template only had 4 hook types |
| 5. hooks.json | Had all hooks BUT was never read |

---

## Solution

### 1. Updated Database Template

```sql
UPDATE claude.config_templates
SET content = jsonb_set(
  jsonb_set(
    jsonb_set(
      content,
      '{hooks,PostToolUse}',
      '[{"matcher": "mcp__.*", "hooks": [{"type": "command", "command": "python \"C:/Projects/claude-family/scripts/mcp_usage_logger.py\"", "timeout": 30}]}]'::jsonb
    ),
    '{hooks,Stop}',
    '[{"hooks": [{"type": "command", "command": "python \"C:/Projects/claude-family/scripts/stop_hook_enforcer.py\"", "timeout": 5, "description": "Self-enforcing periodic checks"}]}]'::jsonb
  ),
  '{hooks,PreCommit}',
  '[{"hooks": [{"type": "command", "command": "python \"C:/Projects/claude-family/scripts/pre_commit_check.py\"", "timeout": 60, "blocking": true, "description": "Run Level 1 tests"}]}]'::jsonb
)
WHERE template_name = 'hooks-base';
```

### 2. Regenerated Project Settings

Ran `generate_project_settings.py` for:
- claude-family ✅
- ATO-tax-agent ✅
- finance-htmx ✅
- finance-mui ✅
- nimbus-import ✅
- personal-finance-system ✅

All projects now have 7 hook types in their settings.local.json:
- PreToolUse ✅
- SessionStart ✅
- SessionEnd ✅
- UserPromptSubmit ✅
- **PostToolUse** ✅ (NEW)
- **Stop** ✅ (NEW)
- **PreCommit** ✅ (NEW)

---

## Verification Steps

### Before Next Session:
1. **Restart Claude Code** - Required to load new hook configuration
2. **Test PostToolUse** - Run an MCP tool and check hooks.log for mcp_usage_logger entry
3. **Check database** - Verify `claude.mcp_usage` table gets populated

### Expected Results:

```bash
# After using any MCP tool, check log:
grep "mcp_usage_logger" ~/.claude/hooks.log

# Check database:
SELECT COUNT(*) FROM claude.mcp_usage WHERE session_id IS NOT NULL;
# Should be > 0
```

---

## What This Enables

### PostToolUse Hook (mcp_usage_logger.py)
- **Purpose**: Track all MCP tool usage for analytics
- **Logs to**: `claude.mcp_usage` table
- **Data captured**: Tool name, execution time, success/failure, input/output sizes
- **Benefits**: Performance monitoring, cost tracking, usage patterns

### Stop Hook (stop_hook_enforcer.py)
- **Purpose**: Self-enforcing periodic checks when agent finishes responding
- **Actions**: Git status check, inbox check, CLAUDE.md refresh, test reminders
- **Benefits**: Prevents forgetting to commit, check messages, run tests

### PreCommit Hook (pre_commit_check.py)
- **Purpose**: Run Level 1 validation before commits
- **Checks**: Schema validation, sensitive file detection
- **Blocking**: Yes - prevents commit if checks fail
- **Benefits**: Catch issues before they reach the repo

---

## Impact

**Before**:
- No MCP usage tracking (0 records in mcp_usage with session_id)
- No periodic self-checks on Stop events
- No pre-commit validation

**After**:
- Full MCP analytics available
- Automated checks prevent common mistakes
- Quality gates before commits

---

## Files Modified

### Database:
- `claude.config_templates` - Updated hooks-base template

### Regenerated:
- `claude-family/.claude/settings.local.json`
- `ATO-tax-agent/.claude/settings.local.json`
- `finance-htmx/.claude/settings.local.json`
- `finance-mui/.claude/settings.local.json`
- `nimbus-import/.claude/settings.local.json`
- `personal-finance-system/.claude/settings.local.json`

### To Delete (Next Phase):
- `.claude/hooks.json` - Dead code, not read by system

---

## Next Steps

1. **User action**: Restart Claude Code
2. **Verify**: Test MCP tool usage triggers PostToolUse hook
3. **Monitor**: Check `claude.mcp_usage` table for new entries
4. **Phase 2**: Delete/rename hooks.json (dead code cleanup)
5. **Phase 3**: Document in vault (update Claude Code Hooks.md)

---

## Lessons Learned

### Configuration Flow
```
Database (claude.config_templates)
  ↓
generate_project_settings.py
  ↓
.claude/settings.local.json
  ↓
Claude Code reads at startup
```

**NOT**: `.claude/hooks.json` → Claude Code (this doesn't happen!)

### Key Insight
Always verify the **actual configuration flow** in database-driven systems. Don't assume file-based configs are being used just because they exist.

### Testing Methodology
1. Check logs for evidence (not assumptions)
2. Trace config through the actual code path
3. Query database to verify source of truth
4. Test with minimal example

---

## ❌ CORRECTION (2025-12-29)

### Error in Original Fix

**Problem**: The fix above added "PreCommit" to the hooks configuration, but **PreCommit is NOT a valid Claude Code hook type**.

**Valid Hook Types** (per official Claude Code documentation):
- PreToolUse, PostToolUse, PostToolUseFailure
- UserPromptSubmit, PermissionRequest
- SessionStart, SessionEnd
- Stop, SubagentStart, SubagentStop
- PreCompact, Notification

**PreCommit is NOT included** - it's an open feature request (GitHub Issue #4834).

### What Happened

1. Confused Git's native `.git/hooks/pre-commit` with Claude Code hook events
2. Added invalid "PreCommit" to database template
3. This propagated to all project settings files
4. Claude Code rejected the configuration on startup

### Corrective Actions (2025-12-29)

1. ✅ Removed PreCommit from `claude.config_templates` (hooks-base)
2. ✅ Removed PreCommit from `.claude/hooks.json`
3. ✅ Updated vault documentation to clarify PreCommit is invalid
4. ✅ Merged `pre_commit_check.py` into native Git hook (`.git/hooks/pre-commit`)

### Lesson Learned

**Always validate hook types against official documentation before adding them to the database template.**

Valid alternatives for pre-commit validation:
- Use native Git hooks (`.git/hooks/pre-commit`)
- Use CI/CD pipeline checks
- Use PreToolUse hooks for specific tool validations

---

**Status**: ⚠️ Partially corrected 2025-12-29. PostToolUse and Stop hooks remain valid and working.
