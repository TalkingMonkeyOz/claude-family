---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.755745'
---

# Claude Hooks

Enforcement layer for governance.

## Active Hooks

| Event | Script | Purpose |
|-------|--------|---------|
| SessionStart | `session_startup_hook.py` | Log session, check inbox |
| UserPromptSubmit | `process_router.py` | Inject workflows |
| PreToolUse (Write) | `validate_claude_md.py` | CLAUDE.md compliance |
| PreToolUse (DB) | `validate_db_write.py` | Column registry check |
| PostToolUse (MCP) | `mcp_usage_logger.py` | Analytics |
| PreCommit | `pre_commit_check.py` | Validation |

## Git Hooks

| Hook | Purpose |
|------|---------|
| `.git/hooks/pre-commit` | CLAUDE.md max 250 lines |

## Config

`.claude/settings.local.json` → hooks array

See also: [[Setting's File]], [[claud.md structure]]