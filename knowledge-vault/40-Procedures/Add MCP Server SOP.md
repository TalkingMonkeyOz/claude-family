---
title: Add MCP Server SOP
category: procedure
status: active
created: 2025-12-27
updated: 2026-01-26
tags:
- sop
- mcp
- configuration
- windows
projects:
- nimbus-mui
---

# Add MCP Server SOP

Standard procedure for adding MCP servers to Claude Family projects.

---

## Decision: Global vs Project-Specific

**Install globally** if: Used by multiple projects, core infrastructure, rarely changes

**Install project-specific** if: Only used by one project, project-specific config, experimental

---

## Method 0: Add Project-Specific MCP (Database-Driven, RECOMMENDED)

**Use this for**: Project-specific tools (MUI docs, Playwright, project-specific APIs)

**Source of Truth**: Database `workspaces.startup_config.mcp_configs`

**Generated File**: `<project-root>/.mcp.json` (auto-generated, self-healing)

### How It Works

```
Database (mcp_configs)  →  generate_mcp_config.py  →  .mcp.json (Generated)
                                   ↑
                            Called by start-claude.bat
```

The launcher generates `.mcp.json` from database on every startup. Manual edits are overwritten.

### 1. Add MCP Config to Database

```sql
-- Add MCP server config for a project
UPDATE claude.workspaces
SET startup_config = startup_config || '{
  "mcp_configs": {
    "mui": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@mui/mcp"]
    }
  },
  "enabledMcpjsonServers": ["mui"]
}'::jsonb
WHERE project_name = 'nimbus-mui';
```

**Note**: Use simple npx command - Windows wrapper is applied automatically!

### 2. Regenerate Config (or Launch via Launcher)

```bash
# Manual regeneration
python C:\Projects\claude-family\scripts\generate_mcp_config.py PROJECT_NAME

# Or just launch via start-claude.bat - it regenerates automatically
```

### 3. Verify

```bash
# Check generated file
cat .mcp.json

# Should see Windows wrapper applied automatically:
# "command": "cmd", "args": ["/c", "npx", "-y", ...]
```

### Adding Multiple Servers

```sql
UPDATE claude.workspaces
SET startup_config = startup_config || '{
  "mcp_configs": {
    "mui": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@mui/mcp"]
    },
    "ag-grid": {
      "type": "stdio",
      "command": "npx",
      "args": ["ag-mcp"]
    },
    "custom-server": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "C:/path/to/server.py"]
    }
  },
  "enabledMcpjsonServers": ["mui", "ag-grid", "custom-server"]
}'::jsonb
WHERE project_name = 'your-project';
```

### Windows Wrapper (Automatic)

The generator automatically applies `cmd /c` wrapper for npx commands on Windows:

**You write in database**:
```json
{ "command": "npx", "args": ["-y", "@mui/mcp"] }
```

**Generated .mcp.json**:
```json
{ "command": "cmd", "args": ["/c", "npx", "-y", "@mui/mcp"] }
```

Non-npx commands (uv, python, node) are left unchanged.

### Legacy: Manual .mcp.json (NOT RECOMMENDED)

If you need to create `.mcp.json` manually (not database-driven):

```json
{
  "mcpServers": {
    "mui": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@mui/mcp"],
      "type": "stdio"
    }
  }
}
```

**Warning**: Manual files will be overwritten if database has `mcp_configs` for the project.

---

## Method 1: Add Global MCP (All Claude Instances)

**Use this for**: Core infrastructure MCPs (postgres, orchestrator, vault-rag, etc.)

**Location**: `~/.claude/mcp.json` (manually maintained)

### 1. Edit Global MCP Config

```bash
# Edit ~/.claude/mcp.json
code ~/.claude/mcp.json
```

Add entry following the pattern:

```json
{
  "mcpServers": {
    "your-mcp-name": {
      "type": "stdio",
      "command": "C:/venvs/mcp/Scripts/python.exe",
      "args": ["C:/Projects/claude-family/mcp-servers/your-mcp/server.py"],
      "env": {
        "DATABASE_URL": "postgresql://..."
      }
    }
  }
}
```

### 2. Add Audit Trail

```sql
INSERT INTO claude.mcp_configs (
    config_id, project_name, mcp_server_name, mcp_package,
    install_date, is_active, reason, installed_by_identity_id
) VALUES (
    gen_random_uuid(),
    'global',
    'your-mcp-name',
    'local:mcp-servers/your-mcp',
    NOW(),
    true,
    'Purpose and expected impact',
    (SELECT identity_id FROM claude.identities WHERE identity_name = 'Claude Sonnet 4.5' LIMIT 1)
);
```

### 3. Restart Claude Code

Global MCPs are loaded at startup, not during SessionStart hook.

**Effect**: All Claude instances get the MCP immediately on next restart.

---

## Method 1: Add to Project Type (All Projects of Type)

```sql
-- Add to all infrastructure projects
UPDATE claude.project_type_configs
SET default_mcp_servers = array_append(default_mcp_servers, 'sequential-thinking')
WHERE project_type = 'infrastructure'
  AND NOT ('sequential-thinking' = ANY(default_mcp_servers));

-- Verify
SELECT project_type, default_mcp_servers FROM claude.project_type_configs
WHERE project_type = 'infrastructure';
```

**Effect**: Next SessionStart, all infrastructure projects get the MCP.

---

## Method 2: Add to Specific Project

```sql
-- Add to one project only
UPDATE claude.workspaces
SET startup_config = jsonb_set(
    COALESCE(startup_config, '{}'::jsonb),
    '{mcp_servers}',
    COALESCE(startup_config->'mcp_servers', '[]'::jsonb) || '["custom-api"]'::jsonb
)
WHERE project_name = 'personal-finance-system';

-- Verify
SELECT project_name, startup_config->'mcp_servers'
FROM claude.workspaces WHERE project_name = 'personal-finance-system';
```

**Effect**: Only specified project gets the MCP.

---

## Method 3: Add to Base Template (All Projects, All Types)

```sql
-- Update hooks-base template
UPDATE claude.config_templates
SET content = jsonb_set(
    content,
    '{mcp_servers}',
    content->'mcp_servers' || '["new-global-mcp"]'::jsonb
)
WHERE template_name = 'hooks-base';

-- Verify
SELECT template_name, content->'mcp_servers'
FROM claude.config_templates WHERE template_name = 'hooks-base';
```

**Effect**: All projects using `hooks-base` get the MCP.

---

## Installing MCP Server Package

### Check Available MCPs

```bash
claude mcp list
```

### Install Package

```bash
# From npm
npx -y @modelcontextprotocol/create-server@latest

# Or globally
npm install -g @modelcontextprotocol/server-name
```

### Configure MCP Server

**Location**: `~/.claude/mcpServers.json` (global) or `.claude/mcpServers.json` (project)

**Example**:
```json
{
  "mcpServers": {
    "custom-api": {
      "command": "node",
      "args": ["C:/path/to/custom-api/build/index.js"],
      "env": {"API_KEY": "your-api-key"}
    }
  }
}
```

---

## Recording Installation (Audit Trail)

```sql
INSERT INTO claude.mcp_configs (
    config_id, project_name, mcp_server_name, mcp_package,
    install_date, is_active, reason, installed_by_identity_id
) VALUES (
    gen_random_uuid(),
    'personal-finance-system',
    'custom-api',
    '@company/custom-api-mcp',
    NOW(),
    true,
    'Required for bank API integration',
    'your-identity-id-uuid'
);
```

---

## Verification

**1. Check generated settings**:
```bash
cat .claude/settings.local.json | grep -A 10 mcp_servers
```

**2. Check MCP server starts**: Look for `[MCP] Server ready: custom-api` in Claude output

**3. Check tools available**: New MCP tools should appear in available tools list

**4. Check logs**:
```bash
cat ~/.claude/hooks.log | grep "MCP servers"
```

---

## Removing MCP Server

### From Project Type

```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = array_remove(default_mcp_servers, 'old-mcp')
WHERE project_type = 'infrastructure';
```

### From Specific Project

```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(
    startup_config,
    '{mcp_servers}',
    (SELECT jsonb_agg(elem) FROM jsonb_array_elements_text(startup_config->'mcp_servers') elem
     WHERE elem != 'old-mcp')
)
WHERE project_name = 'project-name';
```

### Mark Inactive

```sql
UPDATE claude.mcp_configs
SET is_active = false, removal_date = NOW(), reason = 'No longer needed'
WHERE project_name = 'project-name' AND mcp_server_name = 'old-mcp';
```

---

## Available MCP Servers

| MCP Server | Purpose | Scope | Projects Using |
|------------|---------|-------|----------------|
| postgres | Database access, session logging | Global | All |
| memory | Persistent memory graph | Global | All |
| orchestrator | Agent spawning, messaging | Global | All |
| vault-rag | Semantic knowledge search | Global | All |
| sequential-thinking | Complex problem solving | Global | All |
| python-repl | Python code execution | Global | All |
| filesystem | File operations | Global | All |
| mui | Material-UI docs/components | Project (.mcp.json) | nimbus-mui |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| MCP not in settings.local.json | Check `project_type_configs`, regenerate settings manually |
| MCP in settings but not starting | Check `mcpServers.json` config, verify command path, test manually |
| MCP disappears after regenerate | Added to file manually, not database - update database instead |
| Settings not updating | Regenerate: `python scripts/generate_project_settings.py PROJECT` |
| **Windows: "npx not found" error** | **Use `cmd /c` wrapper**: Change `"command": "npx"` to `"command": "cmd", "args": ["/c", "npx", ...]` |
| **Project-specific MCP not loading** | **Check .mcp.json exists in project root**, not in .claude/ folder |
| MCP shows in /doctor but not /mcp list | Restart Claude Code to pick up .mcp.json changes |

**Debug Commands**:
```sql
-- Check config
SELECT default_mcp_servers FROM claude.project_type_configs WHERE project_type = 'TYPE';
SELECT startup_config FROM claude.workspaces WHERE project_name = 'PROJECT';
```

```bash
# Regenerate
python scripts/generate_project_settings.py project-name

# Check logs
cat ~/.claude/hooks.log | tail -50
```

---

## Best Practices

1. **Document Why** - Always add `reason` in `mcp_configs` table
2. **Test First** - Test in one project before adding to project type
3. **Database-Driven** - Add to database, not manually to settings files
4. **Audit Trail** - Use `mcp_configs` table to track installations
5. **Security** - Never commit API keys, use environment variables

---

## Related

- [[New Project SOP]] - Creating projects with MCPs
- [[Config Management SOP]] - Configuration flow
- [[Session Lifecycle - Session Start]] - When config syncs
- [[MCP Registry]] - Complete MCP list
- [[MCP configuration]] - MCP configuration overview

---

**Version**: 3.0 (Database-driven .mcp.json generation with auto Windows wrapper)
**Created**: 2025-12-27
**Updated**: 2026-01-26
**Location**: 40-Procedures/Add MCP Server SOP.md
