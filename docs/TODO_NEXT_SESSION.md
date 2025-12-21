# Next Session TODO

**Last Updated**: 2025-12-21
**Last Session**: Startup hook fixes, deprecated schema migration, Blazor project finalization

## Completed This Session

- **Blazor Project Finalized**
  - Installed NuGet packages: MudBlazor 8.15.0, Npgsql 10.0.1, Markdig 0.44.0
  - Added to `claude.workspaces` table and `workspaces.json`
  - Created `docs/TODO_NEXT_SESSION.md` for Blazor project
  - Sent handoff message with full porting instructions

- **Startup Hook Error - FIXED**
  - Root cause: `check_messages_hook.py` used deprecated `claude_family.instance_messages`
  - Fixed to use `claude.messages`

- **Duplicate Commands - FIXED**
  - Removed `session-start.md` and `session-end.md` from `~/.claude/commands/`
  - Project-level commands in plugins now sole source

- **Deprecated Schema Migration - COMPLETE**
  - Fixed 8 scripts from `claude_family.*` to `claude.*`:
    - `C:/claude/shared/scripts/check_messages_hook.py`
    - `C:/claude/shared/scripts/show_startup_notification.py`
    - `C:/claude/shared/scripts/sync_postgres_to_mcp.py`
    - `scripts/end_current_session.py`
    - `scripts/deploy_optimized_mcps.py`
    - `scripts/orchestrate_mission_control_build.py`
    - `scripts/sync_anthropic_usage.py`
    - `scripts/view_usage.py`

- **Knowledge Captured**
  - Created `knowledge-vault/30-Patterns/Windows Bash and MCP Gotchas.md`
  - Documents: dir/ls issue, startup hooks, duplicate commands, MCP exit errors

- **Broadcast Sent** - Notified all Claude instances of fixes

---

## Next Steps (Priority Order)

1. **P1: Migrate claude-mission-control** - Update code to use `claude.*` instead of deprecated schemas
   - 64 files reference `claude_family.` or `claude_pm.`
   - BLOCKED: Can't drop deprecated tables until MCW migrated

2. **P2: Fix Roslyn MSBuild issue** - Some machines fail to locate MSBuild
   - Options: VS Build Tools install, explicit MSBuild path, or switch to OmniSharp

3. **P3: Sync knowledge vault** - Install psycopg2 in MCP venv, run sync_obsidian_to_db.py

---

## Key Learnings

| Learning | Details |
|----------|---------|
| Use `ls` not `dir` | Git Bash on Windows uses Unix commands |
| Startup hook = schema issue | `claude_family.*` refs cause hook failures |
| Duplicate commands = user vs project | Commands in both locations cause duplicates |
| MCP exit errors = bug #1935 | External dependency, cosmetic only |

---

## Files Changed

| File | Change |
|------|--------|
| `C:/claude/shared/scripts/check_messages_hook.py` | Schema fix |
| `C:/claude/shared/scripts/show_startup_notification.py` | Schema fix |
| `C:/claude/shared/scripts/sync_postgres_to_mcp.py` | Schema fix |
| `scripts/end_current_session.py` | Schema fix |
| `scripts/deploy_optimized_mcps.py` | Schema fix |
| `scripts/orchestrate_mission_control_build.py` | Schema fix |
| `scripts/sync_anthropic_usage.py` | Schema fix |
| `scripts/view_usage.py` | Schema fix |
| `workspaces.json` | Added claude-launcher-blazor |
| `knowledge-vault/30-Patterns/Windows Bash and MCP Gotchas.md` | **NEW** |
| `~/.claude/commands/session-start.md` | **DELETED** |
| `~/.claude/commands/session-end.md` | **DELETED** |

---

**Version**: 8.0
**Status**: Hook fixes deployed, schema migration complete, Blazor ready for development
