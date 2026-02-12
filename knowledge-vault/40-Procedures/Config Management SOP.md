---
title: Config Management SOP
category: procedure
status: active
created: 2025-12-27
updated: 2026-01-02
tags:
- sop
- configuration
- database
projects:
- claude-family
---

# Config Management SOP

**Purpose**: Database-driven configuration system for Claude Family projects

**Key Principle**: Database is source of truth. Files are generated and self-healing.

---

## Architecture

```
Database → generate_project_settings.py → .claude/settings.local.json (ALL config)
                                        → Claude Code
```

**Source Tables**:
- `config_templates` - Base hook configurations
- `project_type_configs` - Defaults per project type
- `workspaces` - Per-project overrides (startup_config column)
- `config_deployment_log` - Audit trail

**Generated Files** (regenerated every SessionStart):
- `.claude/settings.local.json` - ALL settings (hooks, MCP servers, skills, permissions)

**Note**: Claude Code reads hooks from settings files only (`settings.json` or `settings.local.json`), NOT from a separate `hooks.json` file.

---

## Configuration Layers

Config built in **merge order** (last wins):

1. **Base Template** (`config_templates` where `template_name = 'hooks-base'`)
   - Core hooks: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse

2. **Project Type Defaults** (`project_type_configs`)
   - Default MCP servers, skills, instructions for project type
   - Types: infrastructure, csharp-desktop, csharp-winforms, web-app, tauri-react

3. **Project Overrides** (`workspaces.startup_config`)
   - Additional MCPs, hooks, or disabled defaults

4. **Current Permissions** (preserved from existing settings)
   - User-granted tool permissions

---

## SessionStart Flow

1. SessionStart hook triggers `session_startup_hook.py`
2. Calls `generate_project_settings.py`
3. Reads database (project type, base template, type defaults, overrides)
4. Merges configs: `base → type defaults → project overrides`
5. Preserves permissions from existing settings
6. Writes `.claude/hooks.json` (hooks only) and `.claude/settings.local.json` (rest)

**Self-Healing**: Corrupted/manually-edited files regenerate every session.

---

## Updating Configuration

### All Projects of Type

```sql
-- Add MCP to all infrastructure projects
UPDATE claude.project_type_configs
SET default_mcp_servers = array_append(default_mcp_servers, 'new-mcp')
WHERE project_type = 'infrastructure';
```

### Single Project

```sql
-- Add custom hook to one project
UPDATE claude.workspaces
SET startup_config = '{
  "mcp_servers": ["postgres", "custom-mcp"],
  "hooks": {...}
}'::jsonb
WHERE project_name = 'project-name';
```

### All Projects (Base Template)

```sql
-- Add hook to all projects
UPDATE claude.config_templates
SET content = jsonb_set(content, '{hooks,PostToolUse}', '[...]'::jsonb)
WHERE template_name = 'hooks-base';
```

---

## v3 Config Tools (MCP)

**New in v3**: Config operations now available as MCP tools that handle file + DB atomically.

### Available Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `update_claude_md(section, content)` | Update CLAUDE.md sections | Update "Architecture Overview" section |
| `sync_profile(direction)` | Sync file ↔ DB | "file_to_db" or "db_to_file" |
| `deploy_project(components)` | Deploy from DB to files | ["skills", "instructions", "rules"] |
| `regenerate_settings()` | Regenerate settings.local.json | Force config refresh |

### Benefits

1. **Atomic operations**: File and database updated together (no drift)
2. **Audit trail**: All changes logged to `config_deployment_log`
3. **No manual SQL**: Tools handle validation and constraints
4. **Idempotent**: Safe to re-run

### Usage Examples

**Update CLAUDE.md section**:
```python
# Via MCP tool
update_claude_md(
  section="Architecture Overview",
  content="New architecture description..."
)
# Updates: CLAUDE.md file + profiles.config->'behavior'
```

**Sync configuration**:
```python
# File → Database
sync_profile(direction="file_to_db")

# Database → File
sync_profile(direction="db_to_file")
```

**Deploy components**:
```python
# Deploy all skills from DB to .claude/skills/
deploy_project(components=["skills"])

# Deploy multiple
deploy_project(components=["skills", "instructions", "rules"])
```

**Regenerate settings**:
```python
# Force regeneration from DB
regenerate_settings()
# Recreates .claude/settings.local.json
```

### When to Use

- ✅ **Use tools**: When you need to update config during a session
- ✅ **Use SQL**: When seeding initial data or bulk operations
- ⚠️ **Never manual file edits**: Files regenerate from DB

**See**: [[Application Layer v3]] for full v3 architecture.

---

## Inspecting Configuration

**Current generated config**:
```bash
# All settings (including hooks)
cat .claude/settings.local.json | jq .

# Just hooks
cat .claude/settings.local.json | jq '.hooks'

# MCP servers
cat .claude/settings.local.json | jq '.mcp_servers'
```

**Database source**:
```sql
-- Project type
SELECT project_type FROM claude.workspaces WHERE project_name = 'X';

-- Type defaults
SELECT default_mcp_servers, default_skills
FROM claude.project_type_configs
WHERE project_type = 'infrastructure';

-- Project overrides
SELECT startup_config FROM claude.workspaces WHERE project_name = 'X';
```

**Regenerate manually**:
```bash
python scripts/generate_project_settings.py project-name
cat ~/.claude/hooks.log | tail -20
```

---

## Database Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `config_templates` | Reusable configs | template_name, config_type, content (JSONB) |
| `project_type_configs` | Type defaults | project_type, default_mcp_servers[], default_skills[] |
| `workspaces` | Project registry | project_name, project_type, startup_config (JSONB) |
| `project_config_assignments` | Template assignments | project_id, template_id, override_content |
| `config_deployment_log` | Audit trail | project_id, config_type, file_path, deployed_at |
| `profiles` | CLAUDE.md content | name, source_type, config (JSONB with 'behavior' key) |
| `coding_standards` | Auto-apply standards | name, category, content, applies_to_patterns[] |
| `skills` | Skill definitions | name, scope, project_id, content |
| `instructions` | Instruction files | name, scope, applies_to, content |
| `rules` | Rule files | name, scope, content, rule_type |

### CLAUDE.md in Database

CLAUDE.md content is stored in `profiles.config->'behavior'`:

```sql
-- Global CLAUDE.md
SELECT config->>'behavior' FROM claude.profiles WHERE name = 'Global Configuration';

-- Project CLAUDE.md  
SELECT config->>'behavior' FROM claude.profiles WHERE name = 'project-name';
```

**MUI Manager**: Use `claude-manager-mui` → Configuration → Global/Project to edit via GUI.

**Column Registry**:
```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'config_templates' AND column_name = 'config_type';
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Settings not updating | Config sync failed | Check `~/.claude/hooks.log`, regenerate manually |
| Manual edits disappear | Self-healing (by design) | Update database instead of files |
| Hook not firing | Invalid syntax or path | Verify with `jq`, test command manually, check logs |
| DB connection failed | PostgreSQL down | Check `pg_isready`, verify connection string |
| Wrong config applied | Wrong project type | Verify project type matches expected |

**Debug Steps**:
```bash
# Regenerate
python scripts/generate_project_settings.py project-name

# Check logs
cat ~/.claude/hooks.log | grep -i error

# Verify hook syntax
cat .claude/settings.local.json | jq '.hooks.SessionStart'
cat .claude/settings.local.json | jq '.hooks.PreToolUse'
```

---

## Best Practices

1. ✅ **Update database, not files** - settings.local.json regenerates every session
2. ✅ **Test on one project first** - Then expand to project type
3. ✅ **Check logs** - `~/.claude/hooks.log` after changes
4. ✅ **Use column_registry** - Validate values before insert
5. ✅ **Audit trail** - config_deployment_log tracks changes
6. ⚠️ **Don't edit settings.local.json** - Will be overwritten on next session
7. ⚠️ **Restart Claude Code after config changes** - Hooks load at startup, not dynamically

---

## Migration from Manual Config

If project has manual `.claude/settings.local.json`:

1. **Extract current config**:
   ```bash
   cat .claude/settings.local.json | jq . > backup-settings.json
   ```
2. **Decide tier**: Common → project_type_configs, specific → workspaces.startup_config
3. **Add to database**: `UPDATE claude.workspaces SET startup_config = {...}`
4. **Test**: `python scripts/generate_project_settings.py project-name`
5. **Compare**:
   ```bash
   diff backup-settings.json .claude/settings.local.json
   ```
6. **Verify**: Restart Claude Code, check hooks fire

---

## Configuration Schema

**Settings Structure**:
```typescript
{
  hooks: { [hookType]: [{ matcher?, hooks: [{ type, command, timeout }] }] }
  enabledMcpjsonServers: string[]
  skills: string[]
  instructions: string[]
  permissions: { allow: [], deny: [], ask: [] }
}
```

**Hook Types**: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, Stop

---

## Related

- [[New Project SOP]] - Uses config system for new projects
- [[Add MCP Server SOP]] - Adding MCPs via database
- [[Session Lifecycle - Session Start]] - When config sync happens
- [[Settings File]] - Detailed configuration guide

---

**Version**: 3.2 (Added v3 MCP config tools)
**Created**: 2025-12-27
**Updated**: 2026-02-11
**Location**: 40-Procedures/Config Management SOP.md
