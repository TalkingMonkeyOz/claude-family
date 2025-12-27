---
projects:
- claude-family
tags:
- mcp
- configuration
- database-driven
synced: false
---

# MCP Configuration

Database-driven MCP configuration across Claude projects.

---

## Configuration Tiers

| Tier | Location | Scope | Update Method |
|------|----------|-------|---------------|
| 1. Global | `~/.claude.json` | All projects | Manual file edit |
| 2. Project Type | `project_type_configs.default_mcp_servers` | All projects of type | `UPDATE project_type_configs` |
| 3. Project Override | `workspaces.startup_config` | Single project | `UPDATE workspaces` |
| 4. Generated | `.claude/settings.local.json` | Runtime (regenerated) | Auto on SessionStart |

**Global MCPs**: postgres, orchestrator, sequential-thinking, python-repl

---

## Architecture

```
project_type_configs → workspaces.startup_config → generate_project_settings.py → settings.local.json
```

**Self-Healing**: Settings regenerate every SessionStart from database.

---

## Common Tasks

### Add MCP to All Infrastructure Projects

```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY_APPEND(default_mcp_servers, 'custom-mcp')
WHERE project_type = 'infrastructure';
```

### Add MCP to One Project

```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  COALESCE(startup_config, '{}'::jsonb),
  '{enabledMcpjsonServers}',
  jsonb_build_array('postgres', 'orchestrator', 'custom-mcp')
)
WHERE project_name = 'claude-family';
```

### Remove MCP from Type

```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY_REMOVE(default_mcp_servers, 'memory')
WHERE project_type = 'infrastructure';
```

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `project_type_configs` | MCP defaults by project type |
| `workspaces` | Project-specific overrides (startup_config) |
| `mcp_configs` | Audit tracking |
| `config_deployment_log` | Change history |

---

## Checking Configuration

**Current loaded MCPs**:
```bash
cat .claude/settings.local.json | jq '.enabledMcpjsonServers'
```

**Project type defaults**:
```sql
SELECT default_mcp_servers FROM claude.project_type_configs
WHERE project_type = 'infrastructure';
```

**Project overrides**:
```sql
SELECT startup_config FROM claude.workspaces WHERE project_name = 'X';
```

**Regenerate manually**:
```bash
python scripts/generate_project_settings.py claude-family
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP won't load | Check `enabledMcpjsonServers` in settings.local.json |
| Changes not applying | Regenerate or wait for next SessionStart |
| Wrong MCPs loaded | Check project type matches expected |
| Database update ignored | Verify `project_type_configs` was updated, check logs |

**Debug**:
```bash
# Check what's loaded
cat .claude/settings.local.json | grep -A 10 enabledMcpjsonServers

# Check database
psql -d ai_company_foundation -c "SELECT default_mcp_servers FROM claude.project_type_configs"

# Regenerate
python scripts/generate_project_settings.py PROJECT
```

---

## Related

- [[MCP Registry]] - Complete MCP list
- [[Settings File]] - Database-driven settings
- [[Config Management SOP]] - Full config system
- [[Orchestrator MCP]] - Agent spawning

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/MCP configuration.md
