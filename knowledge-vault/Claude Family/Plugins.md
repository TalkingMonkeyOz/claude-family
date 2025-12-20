---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.766746'
---

# Plugins

Plugin architecture for distributing Claude configurations.

## Structure

```
.claude-plugins/claude-family-core/
├── .claude-plugin/plugin.json
├── .mcp.json
├── commands/
├── hooks/
├── scripts/
└── agents/
```

## Installation

`scripts/install_plugin.py` copies:
- Commands → `.claude/commands/`
- Hooks → merged with project hooks
- Scripts → validation/enforcement

See also: [[MCP configuration]], [[Claude Hooks]], [[Slash command's]]