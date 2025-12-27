# Session Summary - Hook System Fix - 2025-12-27

## Critical Discovery: Root Cause Found

**Problem**: Hooks weren't firing across projects despite being "deployed"

**Root Cause**: Hooks deployed to `.claude/hooks.json` but Claude Code reads from `.claude/settings.local.json`

**Evidence**: Official Claude Code schema validation + debug logs showing "0 hooks registered"

---

## What We Fixed

### 1. Hook Migration (3 Projects)

Moved hooks from wrong file to correct file:

| Project | Status | Hooks Migrated |
|---------|--------|----------------|
| claude-family | ✅ Fixed | 7 hook types (UserPromptSubmit, PreToolUse, SessionStart, SessionEnd, PostToolUse, Stop) |
| claude-family-manager-v2 | ✅ Fixed | 4 hook types (UserPromptSubmit, PreToolUse, SessionStart, SessionEnd) |
| nimbus-import | ✅ Fixed | 4 hook types (UserPromptSubmit, PreToolUse, SessionStart, SessionEnd) |

**Files Modified:**
- `C:\Projects\claude-family\.claude\settings.local.json`
- `C:\Projects\claude-family-manager-v2\.claude\settings.local.json`
- `C:\Projects\nimbus-import\.claude\settings.local.json`

**Note**: Removed unsupported "PreCommit" hook (not a valid Claude Code hook type)

### 2. Added File-Based Logging

All hooks now log to `~/.claude/hooks.log` for tracking success/failure:

**Files Modified:**
- `C:\Projects\claude-family\scripts\instruction_matcher.py`
  - Added logging setup (lines 38-54)
  - Added logging to main() function
  - Logs: hook invocation, file processing, matched instructions, errors

- `C:\Projects\claude-family\.claude-plugins\claude-family-core\scripts\session_startup_hook.py`
  - Added logging setup (lines 16-30)
  - Added logging to create_session() and main()
  - Logs: session creation, database operations, state loading, errors

**Log Output Examples:**
```
2025-12-27 14:30:15 - instruction_matcher - INFO - Hook invoked
2025-12-27 14:30:15 - instruction_matcher - INFO - Processing file: test.cs
2025-12-27 14:30:15 - instruction_matcher - INFO - SUCCESS: Applied 2 instructions (csharp, a11y) to test.cs

2025-12-27 14:30:20 - session_startup - INFO - SessionStart hook invoked (resume=False)
2025-12-27 14:30:20 - session_startup - INFO - Project: claude-family
2025-12-27 14:30:20 - session_startup - INFO - SUCCESS: Session created - ID: abc123...
```

---

## Deployment State Before/After

### Before:
```
ATO-Tax-Agent:         ✅ Correct (already in settings.local.json)
nimbus-user-loader:    ✅ Correct (already in settings.local.json)
claude-family:         ❌ Wrong (hooks.json only)
claude-family-manager-v2: ❌ Wrong (hooks.json only)
nimbus-import:         ❌ Wrong (hooks.json only)
```

### After:
```
ALL 5 PROJECTS: ✅ Correct (hooks in settings.local.json)
```

---

## What Works Now

1. **Skills-First Prompt**: UserPromptSubmit hook reminds Claude to use skills
2. **Auto-Apply Instructions**: PreToolUse hook injects coding standards based on file type
3. **Session Auto-Logging**: SessionStart hook creates database records automatically
4. **Session State Prompts**: SessionEnd hook reminds to save state
5. **Stop Hook Self-Enforcement**: Periodic reminders for git status, inbox, etc. (claude-family only)
6. **MCP Usage Logging**: PostToolUse tracks MCP tool calls (claude-family only)

---

## Next Steps (from User Request)

### Immediate:
- [ ] Update all CLAUDE.md files to document hooks/skills system
- [ ] Test hooks are actually firing in next session
- [ ] Check ~/.claude/hooks.log for entries

### Research Tasks:
- [ ] Research database-driven hooks (generate settings.local.json dynamically)
- [ ] Research better knowledge/learning systems (for comparison, don't implement)
- [ ] Audit knowledge system effectiveness

### New Project:
- [ ] Create SOP for new project setup (hooks, skills, CLAUDE.md template)
- [ ] Investigate requirements for user's new project idea

---

## Technical Details

### Valid Claude Code Hook Types (from schema):
- PreToolUse
- PostToolUse
- PostToolUseFailure
- Notification
- UserPromptSubmit
- SessionStart
- SessionEnd
- Stop
- SubagentStart
- SubagentStop
- PreCompact
- PermissionRequest

**NOT valid**: PreCommit (was in our hooks.json, removed during migration)

### Hook Configuration Hierarchy:
1. `.claude/settings.local.json` (gitignored, project-specific)
2. `.claude/settings.json` (git tracked, project-level)
3. `~/.claude/settings.json` (global, all projects)

Precedence: Local > Project > Global

---

## Files Created/Modified

**New:**
- `C:\Projects\claude-family\test_hooks_working.cs` (test file to verify hooks)
- `C:\Projects\claude-family\docs\SESSION_SUMMARY_2025-12-27_HOOK_FIX.md` (this file)

**Modified:**
- `.claude/settings.local.json` (3 projects)
- `scripts/instruction_matcher.py` (logging added)
- `.claude-plugins/claude-family-core/scripts/session_startup_hook.py` (logging added)

**Reference:**
- `docs/CONFIG_AUDIT_COMPREHENSIVE_2025-12-27.md` (deep research findings)
- `C:\Users\johnd\.claude\plans\wobbly-shimmying-wilkes.md` (implementation plan)

---

## Lessons Learned

1. **RTFM First**: Always check official docs - hooks.json was a red herring, never supported
2. **Validate Assumptions**: Debug logs are gospel - showed "0 hooks registered" clearly
3. **Logging is Critical**: Without file logs, hook failures are invisible
4. **Schema Validation Works**: Claude Code caught "PreCommit" as invalid immediately
5. **Documentation Gap**: CLAUDE.md files don't document the hooks infrastructure (fix pending)

---

## User Questions Raised

> "Can we move hooks to database and create them dynamically?"

**Answer**: Yes, possible approach:
1. Store hooks config in `claude.projects.hooks_config` (jsonb column)
2. Script reads from DB, generates `.claude/settings.local.json`
3. Run script during SessionStart or launcher init

**Recommendation**: After we finish current fixes. Template-based approach (standard + overrides) might be simpler.

---

**Session Date**: 2025-12-27
**Claude Instance**: claude-code-unified
**Project**: claude-family
**Duration**: ~2 hours
**Status**: Phase 1 & 2 Complete (Migration + Logging), Phase 3-5 Pending
