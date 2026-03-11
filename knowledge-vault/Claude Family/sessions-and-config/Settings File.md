---
projects:
- claude-family
tags:
- configuration
- settings
- database-driven
synced: false
---

# Settings File (Database-Driven)

Claude settings are **database-driven**, not manually maintained.

**Flow**: Database → `generate_project_settings.py` → `.claude/settings.local.json` (auto-generated on SessionStart)

---

## Architecture

```
Database (Source of Truth)
    ↓
project_type_configs + workspaces.startup_config
    ↓
generate_project_settings.py
    ↓
.claude/settings.local.json (Generated - Don't Edit)
```

**Key Principle**: Database is source of truth. Files are temporary and self-healing.

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `config_templates` | Reusable config blocks (hooks, MCPs) |
| `project_type_configs` | Defaults per project type |
| `workspaces` | `startup_config` column for overrides |
| `config_deployment_log` | Audit trail |

---

## Inheritance Chain

```
Base template → Project type defaults → Project overrides → Permissions → Final settings
```

---

## Configuration Levels

**All infrastructure projects**:
```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY['postgres', 'orchestrator']
WHERE project_type = 'infrastructure';
```

**One project only**:
```sql
UPDATE claude.workspaces
SET startup_config = '{"mcp_servers": ["postgres", "custom"]}'::jsonb
WHERE project_name = 'claude-family';
```

---

## Self-Healing

- Settings regenerate every SessionStart
- Manual edits to `settings.local.json` get overwritten
- Update database instead of files
- Prevents drift, ensures consistency

---

## Common Tasks

| Need to... | SQL |
|------------|-----|
| Add MCP to all type | `UPDATE project_type_configs SET default_mcp_servers = ARRAY_APPEND(...)` |
| Add MCP to one project | `UPDATE workspaces SET startup_config = jsonb_set(...)` |
| Check current config | `SELECT startup_config FROM workspaces WHERE project_name = 'X'` |
| See audit trail | `SELECT * FROM config_deployment_log WHERE project_name = 'X'` |

**Regenerate manually**:
```bash
python scripts/generate_project_settings.py claude-family
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Settings won't persist | Expected - update database not file |
| Changes not working | Verify `project_type_configs`, check project type matches |
| Need immediate update | Run `generate_project_settings.py` manually |
| Generation failed | `tail -100 ~/.claude/hooks.log \| grep error` |

---

## Related

See [[Config Management SOP]] for complete guide

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-27
**Updated**: 2025-12-27
**Location**: Claude Family/Settings File.md
