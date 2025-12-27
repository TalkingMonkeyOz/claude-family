---
title: Add MCP Server SOP
category: procedure
status: active
created: 2025-12-27
updated: 2025-12-27
tags:
- sop
- mcp
- configuration
projects: []
---

# Add MCP Server SOP

Standard procedure for adding MCP servers to Claude Family projects.

---

## Decision: Global vs Project-Specific

**Install globally** if: Used by multiple projects, core infrastructure, rarely changes

**Install project-specific** if: Only used by one project, project-specific config, experimental

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
    '{enabledMcpjsonServers}',
    COALESCE(startup_config->'enabledMcpjsonServers', '[]'::jsonb) || '["custom-api"]'::jsonb
)
WHERE project_name = 'personal-finance-system';

-- Verify
SELECT project_name, startup_config->'enabledMcpjsonServers'
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
    '{enabledMcpjsonServers}',
    content->'enabledMcpjsonServers' || '["new-global-mcp"]'::jsonb
)
WHERE template_name = 'hooks-base';

-- Verify
SELECT template_name, content->'enabledMcpjsonServers'
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
cat .claude/settings.local.json | grep -A 10 enabledMcpjsonServers
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
    '{enabledMcpjsonServers}',
    (SELECT jsonb_agg(elem) FROM jsonb_array_elements_text(startup_config->'enabledMcpjsonServers') elem
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

| Problem | Solution |
|---------|----------|
| MCP not in settings.local.json | Check `project_type_configs`, regenerate settings manually |
| MCP in settings but not starting | Check `mcpServers.json` config, verify command path, test manually |
| MCP disappears after regenerate | Added to file manually, not database - update database instead |
| Settings not updating | Regenerate: `python scripts/generate_project_settings.py PROJECT` |

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

**Version**: 2.0 (Condensed)
**Created**: 2025-12-27
**Updated**: 2025-12-27
**Location**: 40-Procedures/Add MCP Server SOP.md
