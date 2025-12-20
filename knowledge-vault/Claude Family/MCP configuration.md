---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.759391'
---

# MCP Configuration

How MCPs are configured across Claude projects.

---

## Config Hierarchy

| Level | Location | Scope |
|-------|----------|-------|
| **Global** | `~/.claude.json` → `mcpServers` | All projects |
| **Project** | `.mcp.json` in project root | Git-tracked, shared |
| **Local** | `~/.claude.json` → `projects[path].mcpServers` | Per-project overrides |

---

## Current Global MCPs

These load for ALL projects:

| Server | Purpose | Tokens |
|--------|---------|--------|
| postgres | Database access | ~6k |
| orchestrator | Agent spawning | ~9k |
| sequential-thinking | Complex reasoning | ~2k |
| python-repl | Python execution | ~2k |

---

## Project-Specific MCPs

| MCP | Projects | Notes |
|-----|----------|-------|
| filesystem | claude-family only | Moved from global to save tokens |
| memory | claude-family only | Moved from global to save tokens |
| mui-mcp | nimbus-import, ATO | React/MUI projects only |

---

## Adding MCPs

### Via CLI
```bash
claude mcp add <name> -- <command>
```

### Manual (Windows npx)
```json
{
  "mcp-name": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "@package/name@latest"],
    "env": {}
  }
}
```

### Enable in Project
Add to `.claude/settings.local.json`:
```json
{
  "enabledMcpjsonServers": ["postgres", "orchestrator"]
}
```

---

## Related Docs

- [[MCP Registry]] - Complete MCP list with install guidelines
- [[Orchestrator MCP]] - Agent spawning and messaging tools
- [[Setting's File]] - All settings file locations
- [[Claude Tools Reference]] - All available tools

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-20 | Moved filesystem/memory from global to project-specific |
| 2025-12-20 | Added doc-keeper-haiku agent to orchestrator |