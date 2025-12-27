---
projects:
- claude-family
tags:
- configuration
- settings
- database-driven
- self-healing
synced: false
---

# Settings File (Database-Driven Configuration)

**Purpose**: Document how Claude settings are generated from the database
**Audience**: Developers, DevOps, Claude instances managing configurations
**Last Updated**: 2025-12-27

---

## Overview

Claude settings are now **database-driven** instead of manually maintained:

```
Database (Source of Truth)
        ↓
generate_project_settings.py (Generator)
        ↓
.claude/settings.local.json (Generated - Don't Edit)
        ↓
Claude Code (Reads Settings)
```

**Key Principle**: The database is the source of truth. Generated files are temporary and will be overwritten on the next session.

---

## Configuration Flow

### Step 1: Database Tables (Source of Truth)

| Table | Purpose | When Updated |
|-------|---------|--------------|
| `config_templates` | Reusable config blocks (hooks, skills, MCPs) | Manually via SQL or UI |
| `project_type_configs` | Default settings for project type (infrastructure, web-app, etc.) | Manually via SQL or UI |
| `workspaces` | Project registry with `startup_config` column for project-specific overrides | Manually via SQL or UI |
| `mcp_configs` | Tracks installed MCP servers across projects | Auto-updated when MCP added |
| `config_deployment_log` | Audit trail - who changed what, when | Auto-logged on each generation |

### Step 2: Configuration Generator

**File**: `scripts/generate_project_settings.py`

**Function**: Reads database → Generates `.claude/settings.local.json`

**Merge Order (Inheritance Chain)**:
```
1. Base template (hooks-base) from config_templates
   ↓ (override with)
2. Project type defaults from project_type_configs
   ↓ (override with)
3. Project-specific overrides from workspaces.startup_config
   ↓ (preserve)
4. Current permissions from existing settings.local.json
   ↓
= Final merged settings.local.json
```

**Usage**:
```bash
# Manual generation
python scripts/generate_project_settings.py claude-family

# Automatic (on every SessionStart)
# Called by session_startup_hook.py
```

### Step 3: Generated Settings File

**Location**: `.claude/settings.local.json` (per project)

**Not in Git**: Included in `.gitignore` (each project regenerates on startup)

**Content**: Complete Claude Code settings including:
- Hooks (SessionStart, SessionEnd, PreToolUse, UserPromptSubmit, PostToolUse, etc.)
- Enabled MCP servers (postgres, orchestrator, memory, etc.)
- Skills available to Claude
- Instruction files to inject

**Example**:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "always",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude-plugins/claude-family-core/scripts/session_startup_hook.py",
            "timeout": 30
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/instruction_matcher.py",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "enabledMcpjsonServers": [
    "postgres",
    "orchestrator",
    "memory"
  ]
}
```

---

## Configuration Tiers

### Tier 1: Project Type Defaults

Set once per project type, applies to all projects of that type:

```sql
SELECT project_type, default_mcp_servers, default_skills
FROM claude.project_type_configs
WHERE project_type = 'infrastructure';
```

**Example**: All "infrastructure" projects get:
- MCP servers: postgres, orchestrator, memory
- Skills: 7 core infrastructure skills
- Instructions: SQL best practices file

**Update**: Change the database row, regenerate settings on next session

### Tier 2: Project-Specific Overrides

Override defaults for a single project:

```sql
UPDATE claude.workspaces
SET startup_config = '{
  "enabledMcpjsonServers": ["postgres", "orchestrator", "custom-mcp"],
  "hooks": {
    "PostToolUse": [...]
  }'::jsonb
WHERE project_name = 'claude-family';
```

**Use Case**: Add a custom MCP only to "claude-family", not all infrastructure projects

### Tier 3: Global Settings

Settings that apply to ALL Claude instances:

- Location: `~/.claude.json`
- Controlled by: Claude Code CLI and user preferences
- **Note**: Not part of the database-driven system (yet)

---

## Self-Healing Configuration

### How It Works

1. Settings are **generated fresh on every SessionStart**
2. Any manual edits to `settings.local.json` get overwritten
3. This prevents drift and ensures consistency

### Why It's Good

✅ **Consistency**: All projects of same type behave the same way
✅ **Reliability**: Corrupted settings auto-recover on next session
✅ **Centralized**: Update database once, all projects get change
✅ **Auditable**: Every change logged in `config_deployment_log`

### Important Notes

⚠️ **Don't edit settings.local.json manually** - Changes won't persist
⚠️ **Update the database instead** - Use SQL to change project_type_configs or workspaces
✅ **Emergency override**: Edit workspaces.startup_config to add temporary settings

---

## Example: Adding MCP Server

### Scenario 1: Add to All Infrastructure Projects

```sql
-- Step 1: Update project type defaults
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY_APPEND(
  default_mcp_servers,
  'custom-mcp'
)
WHERE project_type = 'infrastructure';

-- Step 2: On next SessionStart, all infrastructure projects get the new MCP
```

**Result**: claude-family, manager-v2, nimbus-import all get "custom-mcp"

### Scenario 2: Add to One Project Only

```sql
-- Step 1: Add to project-specific overrides
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  COALESCE(startup_config, '{}'::jsonb),
  '{enabledMcpjsonServers}',
  jsonb_build_array(
    'postgres', 'orchestrator', 'custom-mcp'
  )
)
WHERE project_name = 'claude-family';

-- Step 2: On next SessionStart, only claude-family gets custom-mcp
```

**Result**: Only claude-family gets "custom-mcp", other infrastructure projects unchanged

---

## Configuration Templates

Reusable config blocks in `config_templates` table:

| Template ID | Name | Purpose | Used By |
|-----------|------|---------|---------|
| 1 | hooks-base | Standard hooks for all projects | All project types |
| 2 | mcp-postgres | PostgreSQL database access | infrastructure, web-app |
| 3 | mcp-orchestrator | Agent spawning | infrastructure |
| 4 | skills-database | Database management skills | infrastructure |

**How Templates Work**:
1. Project type references template ID
2. Generator reads template content
3. Merged into final settings

**Creating Custom Template**:
```sql
INSERT INTO claude.config_templates (name, description, template_content)
VALUES (
  'my-custom-template',
  'Custom hooks for special use case',
  '{"hooks": {...}}'::jsonb
);
```

---

## Logging & Audit Trail

Every settings generation is logged:

```sql
SELECT * FROM claude.config_deployment_log
WHERE project_name = 'claude-family'
ORDER BY deployed_at DESC;
```

**Shows**:
- Who generated the settings
- When (timestamp)
- Which project
- Configuration hash (detects changes)
- Status (success/failure)

---

## Troubleshooting

### "Settings.local.json won't stay updated"

✅ **Expected behavior** - It's self-healing. Update the database instead:
```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY['postgres', 'orchestrator']
WHERE project_type = 'infrastructure';
```

### "Changes aren't taking effect"

1. **Check database was updated**:
```sql
SELECT * FROM claude.project_type_configs WHERE project_type = 'infrastructure';
```

2. **Verify project type matches**:
```sql
SELECT project_type FROM claude.workspaces WHERE project_name = 'claude-family';
```

3. **Regenerate manually**:
```bash
python scripts/generate_project_settings.py claude-family
```

4. **Check logs**:
```bash
tail -50 ~/.claude/hooks.log
```

### "I need settings now, not next session"

Regenerate manually:
```bash
python scripts/generate_project_settings.py claude-family
```

### "Settings generation failed"

Check error logs:
```bash
tail -100 ~/.claude/hooks.log | grep -i error
```

---

## Migration from Manual to Database-Driven

### Before (Manual)
```
Edit .claude/settings.local.json by hand
↓
Copy to other projects manually
↓
Hope they stay in sync
↓
Debug when they don't
```

### After (Database-Driven)
```
Update database once
↓
All projects of same type auto-update
↓
Self-healing prevents drift
↓
Audit trail shows all changes
```

### Migration Steps

1. **Backup current settings** (keep for reference):
   ```bash
   cp .claude/settings.local.json .claude/settings.local.json.backup
   ```

2. **Verify project type is set**:
   ```sql
   SELECT project_type FROM claude.workspaces WHERE project_name = 'your-project';
   ```

3. **Check project type defaults**:
   ```sql
   SELECT * FROM claude.project_type_configs
   WHERE project_type = 'your-type';
   ```

4. **Generate new settings**:
   ```bash
   python scripts/generate_project_settings.py your-project
   ```

5. **Test in next session**:
   ```
   Hooks should fire automatically
   Check ~/.claude/hooks.log for entries
   ```

---

## Related Documents

- [[Config Management SOP]] - Complete configuration system guide
- [[New Project SOP]] - Creating new projects with proper config
- [[Add MCP Server SOP]] - Managing MCP servers across projects
- [[Session Architecture]] - How config sync integrates with SessionStart
- [[Family Rules]] - Mandatory configuration procedures

---

## Quick Reference

**Need to...** | **Do this:**
---|---
Add MCP to one project | `UPDATE claude.workspaces SET startup_config = ...`
Add MCP to all type | `UPDATE claude.project_type_configs SET default_mcp_servers = ...`
Check current config | `SELECT startup_config FROM claude.workspaces WHERE project_name = '...';`
Regenerate manually | `python scripts/generate_project_settings.py PROJECT`
See audit trail | `SELECT * FROM claude.config_deployment_log;`
Check project type | `SELECT project_type FROM claude.workspaces WHERE project_name = '...';`

---

## Key Points to Remember

1. **Database is source of truth** - Always update there, not files
2. **Files are temporary** - Will be regenerated on next session
3. **Self-healing is by design** - Manual edits get overwritten
4. **Inheritance chain matters** - Base → Type → Project → Permissions
5. **Logging is essential** - Check hooks.log when things fail

---

**Version**: 1.0
**Created**: 2025-12-27
**Updated**: 2025-12-27
**Location**: knowledge-vault/Claude Family/Settings File.md
