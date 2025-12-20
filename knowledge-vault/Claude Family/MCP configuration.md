---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T12:04:35.234879'
---

# MCP Configuration

## Active Servers

| Server | Purpose |
|--------|---------|
| postgres | Database access |
| memory | Persistent graph |
| orchestrator | Agent spawning |
| filesystem | File operations |

## Config Location

- Project: `.claude-plugins/claude-family-core/.mcp.json`
- Settings: `.claude/settings.local.json`

## Adding MCPs

```bash
claude mcp add <name> -- <command>
```

See also: [[Setting's File]], [[Plugins]]