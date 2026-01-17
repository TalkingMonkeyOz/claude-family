---
projects:
- claude-family
tags:
- claude-code
- integration
- v2.1.x
- quick-reference
synced: false
---

# Claude Code 2.1.x Integration

**Status**: In Progress | **Date**: 2026-01-17 (Updated for 2.1.9)

---

## Summary

Integrated Claude Code 2.1.0-2.1.2 features into Claude Family infrastructure.

---

## Key Features Implemented

### Hooks

| Feature | Status | Notes |
|---------|--------|-------|
| `once: true` | ✅ | SessionStart runs only once per session |
| SubagentStart | ✅ | Logs agent spawns to `claude.agent_sessions` |
| SubagentStop data | ✅ | agent_id, agent_transcript_path documented |
| PreToolUse `ask` + `updatedInput` | ✅ | Middleware pattern in standards_validator.py |
| PermissionRequest | 📋 Future | Auto-approve safe patterns (needs use case) |
| **`agent_type` in SessionStart** | ✅ 2.1.2 | Hook input includes agent type if `--agent` specified |

### Skills

| Feature | Status | Notes |
|---------|--------|-------|
| YAML frontmatter | ✅ | All 12 skills have `allowed-tools` |
| `context: fork` | ✅ | code-review, agentic-orchestration |
| `agent` field | ✅ | 7 skills linked to agent types |
| Hooks in frontmatter | ✅ | database, work-item-routing skills |
| `skill-inheritance` | ✅ | Cross-skill knowledge sharing |
| **Automatic hot-reload** | ✅ 2.1.0 | Skills in `.claude/skills` reload without restart |
| **YAML-style lists** | ✅ 2.1.0 | `allowed-tools:` can use YAML list syntax |
| **Visible in / menu** | ✅ 2.1.0 | Skills show in slash command menu by default |

### Commands

| Feature | Status | Notes |
|---------|--------|-------|
| Version footers | ✅ | All 16 commands have footers |
| Schema migration | ✅ | Migrated to `claude.*` |

### Configuration

| Feature | Status | Notes |
|---------|--------|-------|
| `.claude/rules/` | ✅ | 3 rule files created |
| MCP wildcard permissions | ✅ | `mcp__postgres__*` pattern |
| **Bash wildcard permissions** | ✅ 2.1.0 | `Bash(npm *)`, `Bash(npx playwright *)` |
| Spawn limit | ✅ | Increased to 10 agents |
| **`respectGitignore`** | ✅ 2.1.0 | Control @-mention file picker per-project |
| **`language` setting** | ✅ 2.1.0 | Configure Claude's response language |

### Environment Variables (New)

| Variable | Purpose | Version |
|----------|---------|---------|
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | Override file read token limit | 2.1.0 |
| `FORCE_AUTOUPDATE_PLUGINS` | Allow plugin autoupdate when main updater disabled | 2.1.2 |

### Output Handling (2.1.2)

| Feature | Status | Notes |
|---------|--------|-------|
| **Large bash outputs to disk** | ✅ | Saved to disk instead of truncated - great for Playwright! |
| **Large tool outputs to disk** | ✅ | Full output via file references |

### PreToolUse Enhancements (2.1.9)

| Feature | Status | Notes |
|---------|--------|-------|
| **`additionalContext` now works** | ✅ | Previously broken (2026-01-02 bug) - NOW FIXED |
| **`stopOnMatch` option** | 📋 Future | Stop after first matching hook |
| **Context injection system** | ✅ IMPLEMENTED | See [[PreToolUse Context Injection]] |

**Implemented**: Database-driven context injection via `context_injector_hook.py`:
- `PreToolUse[Write/Edit]` + `**/*.md` → markdown standards injected
- `PreToolUse[mcp__postgres__*]` → SQL/database standards injected
- Managed via MUI: Global Settings → Context Rules tab

### MCP Configuration (2.1.9)

| Feature | Status | Notes |
|---------|--------|-------|
| **`mcpToolSearch: "auto:N"`** | 📋 Planned | Reduce MCP tool listing overhead |
| **Per-agent MCP configs** | ✅ | Agents can have different MCP servers |

### Agents (v2.0.28+)

| Feature | Status | Notes |
|---------|--------|-------|
| Async messaging | ✅ | Documented in agentic-orchestration skill |
| Agent resume | ✅ | Task tool `resume` parameter documented |
| Dynamic model choice | ✅ | Model override patterns documented |

---

## Files Changed

### New Files
- `scripts/subagent_start_hook.py` - Agent spawn monitoring
- `scripts/context_injector_hook.py` - PreToolUse context injection (2.1.9)
- `.claude/rules/database-rules.md` - SQL patterns
- `.claude/rules/commit-rules.md` - Git commit standards
- `.claude/rules/testing-rules.md` - Test requirements

### Updated Files
- `scripts/standards_validator.py` - `ask_with_suggestion()` pattern
- All 12 skill files - YAML frontmatter
- 8 command files - Version footers + schema migration
- `mcp-servers/orchestrator/orchestrator_prototype.py` - Spawn limit 10
- `knowledge-vault/40-Procedures/Session Lifecycle - *.md` - Updated docs
- `knowledge-vault/Claude Family/Claude Hooks.md` - v2.1.0 features

### Database Updates
- `claude.config_templates` - hooks-base v2 with once:true, SubagentStart
- `claude.context_rules` - Added `tool_patterns` column for PreToolUse matching

### MUI Updates (claude-manager-mui)
- `src/types/index.ts` - Added `ContextRule` type
- `src/services/api.ts` - Added context rules API stubs
- `src/features/configuration/global/ContextRulesManager.tsx` - New component
- `src/features/configuration/global/GlobalSettings.tsx` - Added Context Rules tab

---

## Config Propagation

Database-driven config auto-regenerates on SessionStart:
1. `generate_project_settings.py` reads `claude.config_templates`
2. Writes to `.claude/settings.local.json`
3. All projects get updated hooks automatically

---

## Testing Checklist

- [ ] Verify `once: true` - SessionStart runs only once
- [ ] Test SubagentStart - Spawn agent, check `agent_sessions`
- [ ] Test PreToolUse - Write file, verify ask+updatedInput works
- [ ] Verify skills in `/` menu
- [ ] Test spawn limit 10

---

## Related Docs

- [[Claude Hooks]] - Hook configuration details
- [[Session Lifecycle - Overview]] - Session workflow
- [[MCP Registry]] - MCP server configuration

---

**Version**: 3.1 (Implemented PreToolUse context injection system)
**Created**: 2026-01-08
**Updated**: 2026-01-17
**Location**: knowledge-vault/Claude Family/Claude Code 2.1.x Integration.md
