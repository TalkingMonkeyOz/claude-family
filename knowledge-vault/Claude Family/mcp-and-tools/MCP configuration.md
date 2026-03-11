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

## Architecture (DB-Centralized, 3-Layer Merge)

All MCP servers come from database. No manual `~/.claude/mcp.json`. Each project gets a single `.mcp.json` generated from a 3-layer merge chain.

```
config_templates (global server configs: mcp-postgres, mcp-project-tools, mcp-sequential-thinking)
    ↓ filtered by
project_type_configs.default_mcp_servers (which globals each project type gets)
    ↓ merged with
workspaces.startup_config.mcp_configs (project-specific: mui, playwright, bpmn-engine)
    ↓ resolved
npx → direct node.exe paths (resolve_server_command)
    ↓
{project}/.mcp.json (single output, all servers)
```

**Key Points**:
- Database is the single source of truth for ALL MCP configs
- `.mcp.json` is auto-generated on every launch via `generate_mcp_config.py`
- Manual edits to `.mcp.json` are overwritten
- npx commands resolved to direct `node.exe` paths (eliminates cmd.exe shim overhead)
- Graceful degradation: if DB unavailable, falls back to reading existing `.mcp.json`

---

## 3-Layer Merge Chain

| Layer | Source | Contains | Example |
|-------|--------|----------|---------|
| **1. Templates** | `claude.config_templates` | Full server configs (command, args, env) | `mcp-postgres`, `mcp-project-tools` |
| **2. Type Defaults** | `claude.project_type_configs` | Which templates each project type gets | `infrastructure` → `['postgres', 'project-tools', 'sequential-thinking']` |
| **3. Workspace** | `claude.workspaces.startup_config` | Project-specific servers | `claude-family` → `{mui, playwright, bpmn-engine}` |

Template names follow convention: `mcp-{server_name}` (e.g., `mcp-postgres` for server `postgres`).

---

## Common Tasks

### Add Project-Specific MCP

Update workspace config in database. `.mcp.json` regenerates automatically:

```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  startup_config,
  '{mcp_configs}',
  COALESCE(startup_config->'mcp_configs', '{}'::jsonb) || '{
    "ag-grid": {
      "type": "stdio",
      "command": "npx",
      "args": ["ag-mcp"]
    }
  }'::jsonb
)
WHERE project_name = 'your-project';
```

**Note**: Use simple `npx` command in DB - the generator resolves to direct `node` paths automatically.

Then regenerate or restart via launcher:
```bash
python scripts/generate_mcp_config.py your-project
```

### Add MCP to ALL Projects of a Type

Add to `project_type_configs.default_mcp_servers` + create a `config_templates` entry:

```sql
-- 1. Create the template
INSERT INTO claude.config_templates (template_name, config_type, description, content)
VALUES ('mcp-new-server', 'mcp', 'New MCP server', '{"type":"stdio","command":"node","args":["server.js"]}'::jsonb);

-- 2. Add to project type defaults
UPDATE claude.project_type_configs
SET default_mcp_servers = array_append(default_mcp_servers, 'new-server')
WHERE project_type = 'web-app';
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

### BPMN Process Model

The MCP configuration deployment process is modeled in BPMN:
- **Process**: `L2_mcp_config_deployment` (`processes/infrastructure/mcp_config_deployment.bpmn`)
- **Flow A (Launcher)**: select project → 3-layer DB merge → resolve npx → write .mcp.json → launch Claude
- **Flow B (Add/Remove)**: update DB → regenerate .mcp.json → audit log

---

## Database Tables

| Table/Column | Purpose |
|--------------|---------|
| `config_templates` (mcp-* entries) | Layer 1: Full server config (command, args, env) |
| `project_type_configs.default_mcp_servers` | Layer 2: Which templates each project type gets |
| `workspaces.startup_config.mcp_configs` | Layer 3: Project-specific server configs |
| `workspaces.startup_config.enabledMcpjsonServers` | Optional whitelist filter |

---

## Generated File Structure

The generator creates `.mcp.json` with direct node paths (no cmd.exe shims):

```json
{
  "mcpServers": {
    "postgres": {
      "type": "stdio",
      "command": "C:\\venvs\\mcp\\Scripts\\postgres-mcp.exe",
      "args": ["--access-mode=unrestricted"]
    },
    "project-tools": {
      "type": "stdio",
      "command": "C:\\venvs\\mcp\\Scripts\\python.exe",
      "args": ["C:\\Projects\\claude-family\\mcp-servers\\project-tools\\server_v2.py"]
    },
    "mui": {
      "type": "stdio",
      "command": "C:\\Program Files\\nodejs\\node.exe",
      "args": ["C:\\...\\@mui\\mcp\\dist\\stdio.cjs.js"]
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

**Prerequisites**: Install npx packages globally first:
```bash
npm install -g @mui/mcp @modelcontextprotocol/server-sequential-thinking @playwright/mcp ag-mcp
```

Non-npx commands (uv, python, node) are left unchanged.

---

## Checking Configuration

**Database config** (source of truth):
```sql
-- Layer 1: Templates
SELECT template_name, content FROM claude.config_templates WHERE template_name LIKE 'mcp-%';

-- Layer 2: Type defaults
SELECT project_type, default_mcp_servers FROM claude.project_type_configs;

-- Layer 3: Workspace overrides
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
| MCP missing from .mcp.json | Check: (1) template exists in config_templates, (2) server in default_mcp_servers for project type, or (3) in workspace mcp_configs |
| .mcp.json edits lost | Expected - file is generated from database. Update database instead |
| MCP loads but fails | Check command/args are correct in config_templates or workspace config |
| npx falls back to cmd /c | Package not globally installed. Run `npm install -g <package>` and regenerate |
| No .mcp.json generated | Check workspace exists in DB for project name. Check DB connectivity. |

**Debug**:
```bash
# Check logs
cat ~/.claude/hooks.log | grep mcp_config

# Regenerate
python scripts/generate_mcp_config.py PROJECT_NAME

# Check database layers
psql -c "SELECT template_name FROM claude.config_templates WHERE template_name LIKE 'mcp-%';"
psql -c "SELECT default_mcp_servers FROM claude.project_type_configs WHERE project_type = 'infrastructure';"
psql -c "SELECT startup_config->'mcp_configs' FROM claude.workspaces WHERE project_name = 'X';"
```

---

## Related

- [[Add MCP Server SOP]] - Step-by-step procedure
- [[Config Management SOP]] - Full config system
- [[MCP Windows npx Wrapper Pattern]] - Legacy pattern (replaced by direct node resolution)

---

**Version**: 6.0 (DB-centralized 3-layer merge, removed two-tier/global file references)
**Created**: 2025-12-26
**Updated**: 2026-03-01
**Location**: Claude Family/MCP configuration.md
