---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T12:04:35.251654'
---

# Settings File

Claude Code configuration.

## Locations

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Shared settings (git tracked) |
| `.claude/settings.local.json` | Local overrides (gitignored) |

## Key Settings

```json
{
  "permissions": { "allow": [...], "deny": [...] },
  "enabledMcpjsonServers": ["postgres", "memory", "orchestrator"],
  "hooks": [...]
}
```

## Environment

`.env` files (in order):
1. `scripts/.env`
2. Project root `.env`
3. `C:\claude\shared\.env`

See also: [[MCP configuration]], [[Claude Hooks]]