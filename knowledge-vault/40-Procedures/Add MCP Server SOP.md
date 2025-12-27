---
title: Add MCP Server SOP
category: procedure
status: active
created: 2025-12-27
updated: 2025-12-27
tags: [sop, mcp, configuration]
---

# Add MCP Server SOP

**Purpose**: Standard procedure for adding MCP servers to Claude Family projects

**Scope**: Covers both global (all projects) and project-specific MCP server installations

---

## Decision: Global vs Project-Specific

**Install globally** if:
- Used by multiple projects (e.g., postgres, memory, orchestrator)
- Part of core infrastructure
- Rarely changes

**Install project-specific** if:
- Only used by one project
- Project-specific configuration
- Experimental or temporary

---

## Method 1: Add to Project Type (Affects All Projects of That Type)

Use this to add MCP server to all projects of a certain type.

### Example: Add `sequential-thinking` to all infrastructure projects

```sql
-- Update project_type_configs
UPDATE claude.project_type_configs
SET default_mcp_servers = array_append(default_mcp_servers, 'sequential-thinking')
WHERE project_type = 'infrastructure'
  AND NOT ('sequential-thinking' = ANY(default_mcp_servers));

-- Verify
SELECT project_type, default_mcp_servers
FROM claude.project_type_configs
WHERE project_type = 'infrastructure';
```

**Next Session**: All infrastructure projects will have `sequential-thinking` in their `enabledMcpjsonServers` list.

---

## Method 2: Add to Specific Project (One Project Only)

Use this for project-specific MCP servers.

### Example: Add `custom-api` MCP to `personal-finance-system` project

```sql
-- Update workspaces.startup_config
UPDATE claude.workspaces
SET startup_config = jsonb_set(
    COALESCE(startup_config, '{}'::jsonb),
    '{enabledMcpjsonServers}',
    COALESCE(startup_config->'enabledMcpjsonServers', '[]'::jsonb) || '["custom-api"]'::jsonb
)
WHERE project_name = 'personal-finance-system';

-- Verify
SELECT project_name, startup_config->'enabledMcpjsonServers' AS mcp_servers
FROM claude.workspaces
WHERE project_name = 'personal-finance-system';
```

**Next Session**: Only `personal-finance-system` will have `custom-api` available.

---

## Method 3: Add to Global Settings (All Projects, All Types)

Use this for core infrastructure MCP servers like postgres, memory, orchestrator.

### Option A: Edit Global Settings File

Edit `~/.claude/settings.json`:

```json
{
  "enabledMcpjsonServers": [
    "postgres",
    "memory",
    "orchestrator",
    "new-global-mcp"
  ]
}
```

**Limitation**: This is NOT database-driven, so it's not part of the unified config system.

### Option B: Add to Base Template (Recommended)

```sql
-- Update the hooks-base template to include new MCP
UPDATE claude.config_templates
SET content = jsonb_set(
    content,
    '{enabledMcpjsonServers}',
    content->'enabledMcpjsonServers' || '["new-global-mcp"]'::jsonb
)
WHERE template_name = 'hooks-base';

-- Verify
SELECT template_name, content->'enabledMcpjsonServers' AS mcp_servers
FROM claude.config_templates
WHERE template_name = 'hooks-base';
```

**Next Session**: All projects using `hooks-base` template will have the new MCP server.

---

## Installing the MCP Server Package

After configuring which projects use the MCP, you need to install the actual package:

### Check if MCP is Available

```bash
# List all available MCP servers
claude mcp list
```

### Install from Package

```bash
# Install from npm
npx -y @modelcontextprotocol/create-server@latest

# Or install globally
npm install -g @modelcontextprotocol/server-name
```

### Configure MCP Server

MCP servers are configured in:
- **Global**: `~/.claude/mcpServers.json`
- **Project**: `.claude/mcpServers.json`

Example `mcpServers.json`:

```json
{
  "mcpServers": {
    "custom-api": {
      "command": "node",
      "args": [
        "C:/path/to/custom-api/build/index.js"
      ],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

---

## Recording Installation in Database

Track MCP installations for audit and compliance:

```sql
-- Record MCP installation
INSERT INTO claude.mcp_configs (
    config_id,
    project_name,
    mcp_server_name,
    mcp_package,
    install_date,
    is_active,
    reason,
    installed_by_identity_id
) VALUES (
    gen_random_uuid(),
    'personal-finance-system',
    'custom-api',
    '@company/custom-api-mcp',
    NOW(),
    true,
    'Required for bank API integration',
    'ff32276f-9d05-4a18-b092-31b54c82fff9'  -- Your identity_id
);
```

---

## Verification

After adding MCP server, verify it's available:

### 1. Check Settings Generated Correctly

```bash
# In project directory
cat .claude/settings.local.json | grep -A 10 enabledMcpjsonServers
```

Should show your new MCP server.

### 2. Check MCP Server Starts

Start Claude Code and check:
```
[MCP] Starting server: custom-api
[MCP] Server ready: custom-api
```

### 3. Check Tools Available

In Claude Code session:
```
# List tools from the new MCP
You should see tools from the new MCP server in your available tools
```

### 4. Check Logs

```bash
# Check hooks.log for config sync
cat ~/.claude/hooks.log | grep "MCP servers"

# Should show something like:
# 2025-12-27 10:30:00 - config_generator - INFO - MCP servers: ['postgres', 'memory', 'custom-api']
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
    '{enabledMcpjsonServers}',
    (
        SELECT jsonb_agg(elem)
        FROM jsonb_array_elements_text(startup_config->'enabledMcpjsonServers') elem
        WHERE elem != 'old-mcp'
    )
)
WHERE project_name = 'project-name';
```

### Mark as Inactive in Database

```sql
UPDATE claude.mcp_configs
SET is_active = false,
    removal_date = NOW(),
    reason = 'No longer needed'
WHERE project_name = 'project-name'
  AND mcp_server_name = 'old-mcp';
```

---

## Available MCP Servers

Current Claude Family MCP servers:

| MCP Server | Purpose | Projects Using |
|------------|---------|----------------|
| postgres | Database access, session logging | All infrastructure |
| memory | Persistent memory graph | All projects |
| orchestrator | Agent spawning, messaging | Infrastructure only |
| sequential-thinking | Complex problem solving | As needed |
| filesystem | File operations | Built-in |
| mui-mcp | Material-UI docs | nimbus-import |

---

## Troubleshooting

**Problem**: MCP server not showing in settings.local.json

**Solution**:
1. Check database config: `SELECT default_mcp_servers FROM claude.project_type_configs WHERE project_type = 'your-type'`
2. Regenerate settings: `python scripts/generate_project_settings.py project-name`
3. Check hooks.log for errors

**Problem**: MCP server in settings but not starting

**Solution**:
1. Check mcpServers.json has configuration
2. Check command path is correct
3. Check environment variables are set
4. Run manually: `node path/to/mcp/server/index.js`

**Problem**: Settings regenerate but MCP server disappears

**Solution**: You're adding to file manually, but database-driven config overwrites it.
- Add to database instead (project_type_configs or workspaces.startup_config)

---

## Best Practices

1. **Document Why**: Always add `reason` in mcp_configs table
2. **Test First**: Test MCP in one project before adding to project type
3. **Database-Driven**: Add to DB, not manually to settings files
4. **Audit Trail**: Use mcp_configs table to track installations
5. **Security**: Never commit API keys - use environment variables

---

## Related Procedures

- [[New Project SOP]] - Creating new projects with MCP servers
- [[Config Management SOP]] - How configuration flows from DB to files
- [[Session Lifecycle - Session Start]] - When configuration syncs happen

---

**Version**: 1.0
**Author**: Claude Family
**Last Review**: 2025-12-27
