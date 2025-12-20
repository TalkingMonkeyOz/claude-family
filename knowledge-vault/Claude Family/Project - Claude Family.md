---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T12:04:35.245743'
---

# Project - Claude Family

**Type**: Infrastructure
**Phase**: Implementation
**Path**: `C:\Projects\claude-family`

## Purpose

Governance infrastructure for all Claude instances.

## Components

| Component | Location |
|-----------|----------|
| Database | [[Claude Family Postgres]] |
| Memory | [[Claude Family Memory Graph]] |
| Hooks | [[Claude Hooks]] |
| Commands | [[Slash command's]] |
| MCPs | [[MCP configuration]] |
| Settings | [[Setting's File]] |

## Config Files

- `CLAUDE.md` - Project rules
- `.claude/settings.local.json` - Local config
- `.claude/commands/` - 13 commands
- `.claude/skills/` - 4 skills

## Key Scripts

| Script | Purpose |
|--------|---------|
| `process_router.py` | Workflow injection |
| `sync_obsidian_to_db.py` | Vault sync |
| `install_plugin.py` | Plugin installer |

See also: [[claud.md structure]], [[Purpose]]