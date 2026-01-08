---
projects:
- claude-family
tags:
- claude-code
- integration
- v2.1.0
- quick-reference
synced: false
---

# Claude Code 2.1.0 Integration

**Status**: Complete | **Date**: 2026-01-09

---

## Summary

Integrated Claude Code 2.1.0 features into Claude Family infrastructure.

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

### Skills

| Feature | Status | Notes |
|---------|--------|-------|
| YAML frontmatter | ✅ | All 12 skills have `allowed-tools` |
| `context: fork` | ✅ | code-review, agentic-orchestration |
| `agent` field | ✅ | 7 skills linked to agent types |
| Hooks in frontmatter | ✅ | database, work-item-routing skills |
| `skill-inheritance` | ✅ | Cross-skill knowledge sharing |

### Commands

| Feature | Status | Notes |
|---------|--------|-------|
| Version footers | ✅ | All 16 commands have footers |
| Schema migration | ✅ | Migrated to `claude.*` |

### Configuration

| Feature | Status | Notes |
|---------|--------|-------|
| `.claude/rules/` | ✅ | 3 rule files created |
| Wildcard permissions | ✅ | `mcp__postgres__*` pattern |
| Spawn limit | ✅ | Increased to 10 agents |

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

**Version**: 1.1
**Created**: 2026-01-08
**Updated**: 2026-01-09
**Location**: knowledge-vault/Claude Family/Claude Code 2.1.0 Integration.md
