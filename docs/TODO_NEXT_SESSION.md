# Next Session TODO

**Last Updated**: 2025-12-20
**Last Session**: Blazor MCP config, duplicate command cleanup, MCP orphan root cause

## Completed This Session

- **Blazor Project MCP Config** - Configured `claude-launcher-blazor` with:
  - roslyn (C# code analysis)
  - memory (context persistence)
  - postgres, orchestrator, sequential-thinking (global)
  - Disabled python-repl (not needed for C#)

- **Vault Sync** - Ran `sync_obsidian_to_db.py`, 8 documents synced

- **PostToolUse Hooks** - Confirmed MCP tools work via `mcp__.*` matcher pattern

- **Duplicate Commands Fixed** - Deleted 4 outdated files from `.claude/commands/`:
  - `session-end.md`, `session-start.md`, `feedback-check.md`, `feedback-create.md`
  - These used deprecated `claude_family.*` schema
  - Correct versions in `.claude-plugins/claude-family-core/commands/` retained

- **MCP Orphan Process Leak** - Root cause identified:
  - Claude Code bug #1935 (external dependency)
  - Cannot fix via hooks - requires Claude Code team fix
  - Marked feedback `cdd6b455-7dc0-4b76-a9ed-7e49270f6bba` as `wont_fix`

- **Roslyn MCP Install** - Installed `dotnet-roslyn-mcp` globally
  - Still has MSBuild locator issue on some machines

---

## Next Steps (Priority Order)

1. **P1: Migrate claude-mission-control** - Update code to use `claude.*` instead of deprecated schemas
   - 64 files reference `claude_family.` or `claude_pm.`
   - Key dependencies: `procedure_registry`, `project_feedback_comments`
   - BLOCKED: Can't drop deprecated tables until MCW migrated

2. **P2: Fix Roslyn MSBuild issue** - Some machines fail to locate MSBuild
   - Options: VS Build Tools install, explicit MSBuild path, or switch to OmniSharp

3. **Build claude-launcher-blazor** - Scaffold MAUI Blazor Hybrid app
   - Port UI from claude-family-manager (Electron)
   - See `C:\Projects\claude-launcher-blazor\CLAUDE.md` for spec

---

## Key Learnings

| Learning | Details |
|----------|---------|
| MCP orphan = Claude Code bug | Issue #1935, external dependency, can't fix via hooks |
| Duplicate commands cause confusion | Old `.claude/commands/` conflicted with `.claude-plugins/` |
| PostToolUse supports MCP | Use `mcp__.*` matcher pattern |
| Schema migration mostly done | Only docs/plugins had old refs, source already migrated |

---

## Files Changed

| File | Change |
|------|--------|
| `~/.claude.json` | Added roslyn/memory MCPs to claude-family-manager |
| `C:\Projects\claude-launcher-blazor\CLAUDE.md` | **NEW** - Blazor project spec |
| `C:\Projects\claude-launcher-blazor\.mcp.json` | **NEW** - Project MCP config |
| `.claude/commands/session-end.md` | **DELETED** - duplicate |
| `.claude/commands/session-start.md` | **DELETED** - duplicate |
| `.claude/commands/feedback-check.md` | **DELETED** - duplicate |
| `.claude/commands/feedback-create.md` | **DELETED** - duplicate |

---

**Version**: 7.0
**Status**: MCP config deployed, duplicates cleaned, ready for Blazor build
