---
projects:
- claude-family
synced: true
synced_at: '2026-01-08T12:00:00.000000'
tags:
- hooks
- quick-reference
- claude-family
---

# Claude Hooks

Enforcement layer for Claude Family governance.

## Active Hooks

| Event | Script | Purpose | Status |
|-------|--------|---------|--------|
| SessionStart | `session_startup_hook.py` | Log session, load state, check inbox | ✅ Working |
| UserPromptSubmit | `rag_query_hook.py` | Auto-query RAG for vault context | ✅ Active |
| PreToolUse (Write/Edit) | `standards_validator.py` | Validate against coding standards | ✅ Working |
| PostToolUse (TodoWrite) | `todo_sync_hook.py` | Sync todos to database | ✅ Working |
| PostToolUse (MCP) | `mcp_usage_logger.py` | Analytics logging | ✅ Working |
| Stop | `stop_hook_enforcer.py` | Vault check every 5 interactions | ✅ Working |
| PreCompact | `precompact_hook.py` | CLAUDE.md/vault refresh | ✅ Working |
| SessionEnd | (prompt) | Reminder to run /session-end | ✅ Working |

## New Hook Features (v2.1.0)

### PreToolUse: ask + updatedInput Pattern
Can now modify input AND ask for permission:
```python
response = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": "Suggested correction...",
        "updatedInput": { ...modified_tool_input... }
    }
}
```

### Additional Hook Types
| Type | Version | Purpose |
|------|---------|---------|
| SubagentStart | v2.0.43 | Monitor agent spawning |
| PermissionRequest | v2.0.45 | Auto-approve safe patterns |
| Hooks in frontmatter | v2.1.0 | Define hooks in skill/agent files |
| `once: true` config | v2.1.0 | Run hook only once per session |

### Hooks in Skill Frontmatter
```yaml
---
name: my-skill
hooks:
  PreToolUse:
    - matcher: Write
      command: "python validate.py"
---
```

## Git Hooks (Native)

| Hook | Purpose |
|------|---------|
| `.git/hooks/pre-commit` | CLAUDE.md max 250 lines |

**Note**: Claude Code does NOT support PreCommit/PostCommit events. Use native Git hooks.

## Config Flow

```
Database (claude.config_templates)
    ↓
generate_project_settings.py
    ↓
.claude/settings.local.json
```

**Source of truth**: `claude.config_templates` table
**Auto-regenerated**: Every SessionStart (self-healing)
**Important**: Hooks must be in `settings.local.json`, NOT `hooks.json`!

## Recent Changes

**2026-01-08**:
- Updated standards_validator.py with `ask_with_suggestion()` pattern
- Documented new v2.1.0 hook features (SubagentStart, PermissionRequest, frontmatter hooks)

**2026-01-02**:
- CRITICAL FIX: Hooks in `settings.local.json`, NOT `hooks.json`

**2025-12-31**:
- RE-ENABLED UserPromptSubmit hook (rag_query_hook.py)

---

**Version**: 1.4
**Created**: 2025-12-26
**Updated**: 2026-01-08
**Location**: Claude Family/Claude Hooks.md
