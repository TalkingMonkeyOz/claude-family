# Claude Desktop Configuration

**Type**: Configuration
**Status**: Planning
**Project ID**: See claude.projects table

---

## Purpose

Central documentation and configuration management for:
- **Claude Desktop** - The desktop app (claude.ai wrapper)
- **Claude Code Console** - CLI tool integrated with Claude Desktop

---

## Configuration Locations

### Claude Desktop
- Config: `%APPDATA%\Claude\` (Windows)
- Settings: TBD

### Claude Code
- Global config: `~/.claude/`
- Project config: `.claude/` in each project

---

## Key Files

| File | Purpose |
|------|---------|
| `claude_desktop_config.json` | MCP server definitions for Claude Desktop |
| `settings.json` | Claude Code settings |
| `CLAUDE.md` | Project instructions |

---

## MCP Integration

Claude Desktop can connect to MCP servers. Configuration goes in:
`%APPDATA%\Claude\claude_desktop_config.json`

Example structure:
```json
{
  "mcpServers": {
    "postgres": { ... },
    "memory": { ... }
  }
}
```

---

## TODO

- [ ] Document actual config file locations
- [ ] Create backup/sync scripts for configs
- [ ] Document MCP server setup for Claude Desktop
- [ ] Add Claude Code Console launch scripts

---

**Version**: 1.0
**Created**: 2025-12-21
**Updated**: 2025-12-21
