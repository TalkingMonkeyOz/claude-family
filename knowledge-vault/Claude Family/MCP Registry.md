---
projects:
- claude-family
synced: false
synced_at: '2025-12-27T00:00:00.000000'
tags:
- quick-reference
- mcp
- claude-family
---

# MCP Registry

Registry of installed MCPs with project assignments and token costs.

**For installation**: See [[Add MCP Server SOP]]

---

## Installed MCPs

### postgres
**Purpose**: Database access to `ai_company_foundation`
**Tokens**: ~6k
**Package**: `postgres-mcp.exe` (custom)
**Scope**: Global (all projects)

### orchestrator
**Purpose**: Spawn agents (15 types) + inter-Claude messaging
**Tokens**: ~9k
**Package**: Custom (`mcp-servers/orchestrator/`)
**Scope**: Global (claude-family, ATO, MCW, nimbus)
**Docs**: [[Orchestrator MCP]]

### mui-mcp
**Purpose**: MUI X documentation
**Tokens**: ~2k
**Package**: `@mui/mcp@latest`
**Scope**: Project (nimbus-import, ATO-Tax-Agent)

### filesystem
**Purpose**: File operations via MCP
**Tokens**: ~9k (heavy!)
**Package**: `@modelcontextprotocol/server-filesystem`
**Scope**: Project-specific (claude-family only)
**Note**: Often unnecessary - Read/Write/Edit tools work fine

### memory
**Purpose**: Persistent entity graph
**Tokens**: ~6k
**Package**: `@modelcontextprotocol/server-memory`
**Scope**: Project-specific (claude-family only)
**Note**: Consider postgres tables instead

### sequential-thinking
**Purpose**: Complex multi-step reasoning
**Tokens**: ~2k
**Package**: `@modelcontextprotocol/server-sequential-thinking`
**Scope**: Global (all projects)

### python-repl
**Purpose**: Execute Python code
**Tokens**: ~2k
**Package**: `mcp-python.exe`
**Scope**: Global (claude-family)

---

## Installation Decision Tree

**Before installing**:

1. **Is it needed globally?** → Add to `~/.claude.json`
2. **Per-project?** → Add to `.mcp.json` (git-tracked)
3. **This machine only?** → Add to `~/.claude.json` projects[path]

**Token cost check**:
- Under 3k: ✅ Fine
- 3-6k: ⚠️ Consider if needed
- Over 6k: ❌ Only if essential

**Alternatives?**
- filesystem → Read/Write/Edit tools
- memory → postgres tables
- web fetch → WebFetch tool

---

## Quick Install (npx package)

**Windows**:
```json
{
  "mcp-name": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "@package/name@latest"]
  }
}
```

**Enable in settings**:
```json
{
  "enabledMcpjsonServers": ["postgres", "orchestrator", "new-mcp"]
}
```

**Full guide**: [[Add MCP Server SOP]]

---

## Token Budgets by Project

| Project | Current | Target | Max |
|---------|---------|--------|-----|
| claude-family | ~25k | 25k | 30k |
| ATO-Tax-Agent | ~17k | 20k | 25k |
| mission-control-web | ~15k | 20k | 25k |

---

## Before Adding MCP

- [ ] Token cost <6k?
- [ ] No built-in alternative?
- [ ] Windows `cmd /c` wrapper?
- [ ] Tested locally?

---

## Related

- [[Add MCP Server SOP]] - Installation procedure
- [[MCP configuration]] - Database-driven config
- [[Setting's File]] - Settings structure
- [[Claude Tools Reference]] - All available tools
- [[Orchestrator MCP]] - Orchestrator details

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/MCP Registry.md
