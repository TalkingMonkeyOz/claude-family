# Obsolete Startup Scripts (Archived 2025-12-16)

These scripts were used for the original "PostgreSQL to MCP memory sync" approach
that ran at Windows startup. They are now obsolete.

## Why Obsolete

1. **Direct Database Access** - Claude Code has MCP postgres, can query on-demand
2. **Session Commands** - `/session-start` and `/session-end` handle session management
3. **Process Router** - Hooks inject relevant context per-request
4. **TODO Files** - `TODO_NEXT_SESSION.md` provides session continuity

## What These Scripts Did

| Script | Purpose |
|--------|---------|
| `STARTUP.bat` | Manual startup (with console output) |
| `STARTUP_SILENT.bat` | Windows Startup version (silent) |
| `auto_sync_startup.py` | Orchestrated the sync process |
| `load_claude_startup_context.py` | Loaded identity/knowledge/sessions from PostgreSQL |
| `sync_postgres_to_mcp.py` | Generated JSON for MCP memory import |
| `show_startup_balloon.ps1` | Showed Windows notification |

## Known Issues (at time of archival)

- Used legacy schema `claude_family.identities` instead of `claude.identities`
- Referenced old paths in `ai-workspace`
- `capabilities` field bug caused startup failures

## Safe to Delete

These files can be permanently deleted if disk space is needed.
They serve no purpose in the current architecture.
