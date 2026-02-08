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

| Order | Event | Script | Purpose | Status |
|-------|-------|--------|---------|--------|
| 1 | SessionStart | `session_startup_hook.py` | Log session, load state, check inbox | ✅ Working |
| 2 | UserPromptSubmit | `rag_query_hook.py` | RAG context + core protocol + periodic reminders | ✅ Active |
| 3 | PreToolUse (Write/Edit) | `context_injector_hook.py` | Inject coding standards from context_rules | ✅ Working |
| 3b | PreToolUse (Write/Edit) | `standards_validator.py` | Validate content against standards | ✅ Working |
| 4 | PostToolUse (TodoWrite) | `todo_sync_hook.py` | Sync todos to database | ✅ Working |
| 5 | PostToolUse (catch-all) | `mcp_usage_logger.py` | Log MCP tool usage (filters to mcp__ prefix) | ✅ Working |
| 6 | SubagentStart | `subagent_start_hook.py` | Log agent spawns to agent_sessions | ✅ Working |
| 7 | PreCompact (manual+auto) | `precompact_hook.py` | Inject active todos, features, session state | ✅ Working |
| 8 | SessionEnd | `session_end_hook.py` | Auto-close session in database | ✅ Working |

**Key design**: MCP usage logger uses a catch-all matcher (no matcher = fires for ALL PostToolUse). The script internally filters to `tool_name.startswith('mcp__')`.

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
| **`agent_type` in SessionStart** | v2.1.2 | Hook input includes agent type if `--agent` specified |

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

**2026-02-07**:
- SessionEnd hook changed from prompt type → command type (`session_end_hook.py`)
- PreCompact hook enhanced: now queries DB for active todos, features, session state
- PostToolUse MCP logger changed to catch-all matcher (68 entries → 2)
- Deleted dead code: `stop_hook_enforcer.py` (merged into rag_query_hook.py)
- Deleted security risk: `end_current_session.py` (hardcoded credentials)
- Added `context_injector_hook.py` and `subagent_start_hook.py` to Active Hooks table

**2026-01-09**:
- Added `agent_type` in SessionStart hook input (v2.1.2)
- Large bash/tool outputs now saved to disk instead of truncated (v2.1.2)

**2026-01-08**:
- Updated standards_validator.py with `ask_with_suggestion()` pattern
- Documented new v2.1.0 hook features (SubagentStart, PermissionRequest, frontmatter hooks)

**2026-01-02**:
- CRITICAL FIX: Hooks in `settings.local.json`, NOT `hooks.json`

**2025-12-31**:
- RE-ENABLED UserPromptSubmit hook (rag_query_hook.py)

---

**Version**: 2.0 (Full hook chain audit, SessionEnd/PreCompact rework)
**Created**: 2025-12-26
**Updated**: 2026-02-07
**Location**: Claude Family/Claude Hooks.md
