---
projects:
- claude-family
synced: true
synced_at: '2025-12-28T22:15:00.000000'
tags:
- hooks
- quick-reference
- claude-family
---

# Claude Hooks

Enforcement layer for governance.

## Active Hooks

| Event | Script | Purpose | Status |
|-------|--------|---------|--------|
| SessionStart | `session_startup_hook.py` | Log session, check inbox, regen config | ✅ Working |
| PreToolUse (Write/Edit) | `instruction_matcher.py` | Auto-apply coding standards | ✅ Working |
| PreToolUse (Write/Edit) | `validate_claude_md.py` | CLAUDE.md compliance | ✅ Working |
| PreToolUse (SQL) | `validate_db_write.py` | Column registry check | ✅ Working |
| PreToolUse (SQL) | `validate_phase.py` | Phase validation | ✅ Working |
| PreToolUse (SQL) | `validate_parent_links.py` | Prevent orphans | ✅ Working |
| PostToolUse (MCP) | `mcp_usage_logger.py` | Analytics | ✅ Fixed 2025-12-28 |
| Stop | `stop_hook_enforcer.py` | Vault check every 5 interactions | ✅ Updated 2025-12-29 |
| PreCompact (manual/auto) | `precompact_hook.py` | Re-examine CLAUDE.md and vault | ✅ Added 2025-12-29 |
| SessionEnd | (prompt) | Reminder to run /session-end | ✅ Working |
| UserPromptSubmit | `rag_query_hook.py` | Auto-query Voyage AI RAG for vault context | ✅ ACTIVE 2025-12-31 |

## Git Hooks (Native)

**Note**: Claude Code does NOT support `PreCommit` or `PostCommit` hook events (GitHub Issue #4834 is an open feature request). Use native Git hooks instead.

| Hook | Purpose |
|------|---------|
| `.git/hooks/pre-commit` | CLAUDE.md max 250 lines + pre_commit_check.py |

## Context Refresh Strategy

**Stop Hook** (every 5 interactions):
- Reminds to check CLAUDE.md and knowledge-vault/ for answers
- Almost any question (configuration, procedures, patterns) has answers in the vault
- Helps combat context drift during long sessions

**PreCompact Hook** (before manual `/compact` or auto-compact):
- Injects strong reminder to re-examine CLAUDE.md (global + project) and vault
- Critical moment: After compaction, Claude should start with fresh understanding
- Emphasizes: Database is source of truth, vault has answers

## Config Flow

Database (`claude.config_templates`) → `generate_project_settings.py` → `.claude/settings.local.json`

**Source of truth**: `claude.config_templates` table (hooks-base template)
**Auto-regenerated**: Every SessionStart (self-healing)
**Important**: Claude Code reads hooks from `settings.local.json`, NOT a separate `hooks.json` file!

See also: [[Settings File]], [[claud.md structure]], [[Config Management SOP]]

## Recent Changes

**2026-01-02**:
- CRITICAL FIX: Hooks must be in `settings.local.json`, NOT `hooks.json` (hooks.json is ignored!)
- Updated `generate_project_settings.py` to put hooks in settings.local.json
- Legacy hooks.json files are now auto-deleted during config regeneration
- Root cause of "hooks not working" bug from 2026-01-01 was wrong config file, not cache bloat

**2025-12-31**:
- RE-ENABLED UserPromptSubmit hook with correct implementation (rag_query_hook.py)
- Now uses silent JSON output format (no "chatty" messages)
- Automatically queries Voyage AI on every user prompt for vault context injection
- Fixed SessionStart RAG pre-load threshold (0.6 → 0.5)
- Added vault-rag to .mcp.json for manual MCP calls

**2025-12-29** (afternoon):
- Added PreCompact hook (`precompact_hook.py`) for CLAUDE.md and vault refresh before compaction
- Updated Stop hook: Reduced interval from 20 to 5 interactions for vault checks
- Updated reminder message: Emphasizes checking vault for answers to almost any question
- Added "Context Refresh Strategy" section documenting the approach

**2025-12-29** (morning):
- CORRECTED: PreCommit is NOT a valid Claude Code hook type (was incorrectly added 2025-12-28)
- Moved pre_commit_check.py functionality to native Git hook (`.git/hooks/pre-commit`)

**2025-12-28**:
- Fixed PostToolUse, Stop hooks (were in hooks.json but NOT in database)
- Removed UserPromptSubmit hook (was blocking casual questions)
- ❌ ERROR: Added invalid "PreCommit" hook (corrected 2025-12-29)

---

**Version**: 1.3
**Created**: 2025-12-26
**Updated**: 2026-01-02
**Location**: Claude Family/Claude Hooks.md