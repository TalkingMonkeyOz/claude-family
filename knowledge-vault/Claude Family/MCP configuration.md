---
projects:
- claude-family
tags:
- mcp
- configuration
synced: false
---

# MCP Configuration

How MCP servers are configured across Claude projects.

---

## Configuration Tiers

| Tier | Source of Truth | Generated File | Update Method |
|------|-----------------|----------------|---------------|
| **1. Global MCPs** | `~/.claude/mcp.json` | — | Manual file edit |
| **2. Project MCPs** | Database `mcp_configs` | `.mcp.json` | Database UPDATE |
| 3. Enable Control | Database `enabledMcpjsonServers` | `settings.local.json` | Database UPDATE |

**Global MCPs**: postgres, orchestrator, sequential-thinking, project-tools

**Note**: `~/.claude/mcp.json` is the global config (manually maintained). Do NOT confuse with `~/.claude.json` which is Claude Code's internal config file managed by `/mcp add` CLI.

---

## Architecture (Database-Driven)

**IMPORTANT**: As of 2026-01-26, `.mcp.json` is GENERATED from database.

```
Database (Source of Truth)
    workspaces.startup_config.mcp_configs
        ↓
    generate_mcp_config.py (called by start-claude.bat)
        ↓
    .mcp.json (Generated, self-healing)
        ↓
    Claude Code reads .mcp.json
```

**Key Points**:
- Database `mcp_configs` is the source of truth
- `.mcp.json` is auto-generated on every launch
- Manual edits to `.mcp.json` are overwritten
- npx commands resolved to direct `node.exe` paths (eliminates cmd.exe shim overhead)

---

## Common Tasks

### Add Project-Specific MCP

**Update database** - `.mcp.json` will be generated automatically:

```sql
-- Add MCP config to a project
UPDATE claude.workspaces
SET startup_config = startup_config || '{
  "mcp_configs": {
    "ag-grid": {
      "type": "stdio",
      "command": "npx",
      "args": ["ag-mcp"]
    }
  },
  "enabledMcpjsonServers": ["ag-grid"]
}'::jsonb
WHERE project_name = 'your-project';
```

**Note**: Use simple `npx` command in DB - the generator resolves to direct `node` paths automatically!

Then regenerate or restart via launcher:
```bash
python scripts/generate_mcp_config.py your-project
```

### Add Multiple Servers

```sql
UPDATE claude.workspaces
SET startup_config = startup_config || '{
  "mcp_configs": {
    "mui": { "type": "stdio", "command": "npx", "args": ["-y", "@mui/mcp"] },
    "ag-grid": { "type": "stdio", "command": "npx", "args": ["ag-mcp"] },
    "custom": { "type": "stdio", "command": "uv", "args": ["run", "server.py"] }
  },
  "enabledMcpjsonServers": ["mui", "ag-grid", "custom"]
}'::jsonb
WHERE project_name = 'your-project';
```

### Disable an MCP (Keep Config)

```sql
-- Remove from enabledMcpjsonServers (keeps config for later)
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  startup_config,
  '{enabledMcpjsonServers}',
  (SELECT jsonb_agg(elem) FROM jsonb_array_elements_text(startup_config->'enabledMcpjsonServers') elem
   WHERE elem != 'ag-grid')
)
WHERE project_name = 'your-project';
```

### Add Global MCP (All Projects)

Edit `~/.claude/mcp.json` directly (manual file edit - not database-driven).

### BPMN Process Model

The MCP configuration deployment process is modeled in BPMN:
- **Process**: `L2_mcp_config_deployment` (`processes/infrastructure/mcp_config_deployment.bpmn`)
- **Flow A (Launcher)**: start-claude.bat → read DB → generate .mcp.json → launch Claude
- **Flow B (Add/Remove)**: scope decision → global (manual edit) or project (DB update → regenerate)

---

## Database Tables

| Table/Column | Purpose | Used? |
|--------------|---------|-------|
| `workspaces.startup_config.mcp_configs` | MCP server definitions | ✅ Source of truth |
| `workspaces.startup_config.enabledMcpjsonServers` | Which servers to include | ✅ Filters output |
| `mcp_configs` (table) | Audit tracking only | ⚠️ Informational |

---

## Generated File Structure

The generator creates `.mcp.json` with direct node paths (no cmd.exe shims):

```json
{
  "_comment": "Generated from database - DO NOT EDIT MANUALLY",
  "_generated": true,
  "_project": "project-name",
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "C:\\Program Files\\nodejs\\node.exe",
      "args": ["C:\\Users\\johnd\\AppData\\Roaming\\npm\\node_modules\\@pkg\\name\\dist\\index.js"]
    }
  }
}
```

---

## npx Resolution (Automatic)

The generator resolves npx commands to direct `node.exe` paths, eliminating cmd.exe shim overhead:

**You write in database**:
```json
{ "command": "npx", "args": ["-y", "@mui/mcp"] }
```

**Generated .mcp.json** (if globally installed):
```json
{ "command": "C:\\Program Files\\nodejs\\node.exe", "args": ["C:\\...\\@mui\\mcp\\dist\\stdio.cjs.js"] }
```

**Fallback** (if NOT globally installed): wraps with `cmd /c npx` as before.

**How it works**:
1. Checks `%APPDATA%/npm/node_modules/<package>/package.json` for entry point
2. If found, uses `node.exe <entry_point>` directly (0 extra processes)
3. If not found, falls back to `cmd /c npx` wrapper (2 extra cmd.exe processes)

**Prerequisites**: Install npx packages globally first:
```bash
npm install -g @mui/mcp @modelcontextprotocol/server-sequential-thinking @playwright/mcp ag-mcp
```

Non-npx commands (uv, python, node) are left unchanged.

---

## Checking Configuration

**Database config** (source of truth):
```sql
SELECT startup_config->'mcp_configs' FROM claude.workspaces WHERE project_name = 'X';
```

**Generated .mcp.json**:
```bash
cat .mcp.json
```

**Regenerate manually**:
```bash
python C:\Projects\claude-family\scripts\generate_mcp_config.py PROJECT_NAME
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP not in .mcp.json | Check database has `mcp_configs` AND server is in `enabledMcpjsonServers` |
| .mcp.json edits lost | Expected - file is generated from database. Update database instead |
| MCP loads but fails | Check command/args are correct in database |
| npx falls back to cmd /c | Package not globally installed. Run `npm install -g <package>` and regenerate |
| No .mcp.json generated | Check `startup_config->'mcp_configs'` exists in workspaces |

**Debug**:
```bash
# Check logs
cat ~/.claude/hooks.log | grep mcp_config

# Regenerate
python scripts/generate_mcp_config.py PROJECT_NAME

# Check database
psql -c "SELECT startup_config->'mcp_configs' FROM claude.workspaces WHERE project_name = 'X';"
```

---

## Related

- [[Add MCP Server SOP]] - Step-by-step procedure
- [[Config Management SOP]] - Full config system
- [[MCP Windows npx Wrapper Pattern]] - Legacy pattern (replaced by direct node resolution)

---

**Version**: 5.1 (Fixed global MCPs location: ~/.claude/mcp.json not ~/.claude.json, added BPMN reference)
**Created**: 2025-12-26
**Updated**: 2026-02-21
**Location**: Claude Family/MCP configuration.md
