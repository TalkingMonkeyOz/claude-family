---
title: Config Management SOP
category: procedure
status: active
created: 2025-12-27
updated: 2025-12-27
tags: [sop, configuration, database, architecture]
---

# Config Management SOP

**Purpose**: Explains how Claude Family configuration management works

**Key Principle**: Database is source of truth. Files are generated. Manual file edits are temporary.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE (Source of Truth)                │
│                                                              │
│  claude.config_templates     → Base hook configurations     │
│  claude.project_type_configs → Defaults per project type    │
│  claude.workspaces          → Per-project overrides         │
│  claude.projects            → Project registry              │
└──────────────────────────────┬──────────────────────────────┘
                               │ SessionStart hook calls
                               │ generate_project_settings.py
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FILES (Runtime Config)                    │
│                                                              │
│  .claude/settings.local.json  ← Generated, not hand-edited  │
│  .claude/commands/            ← Copied from plugins         │
│  .claude/skills/              ← Copied from plugins         │
└──────────────────────────────┬──────────────────────────────┘
                               │ Claude reads on startup
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE.md (Entry Point)                   │
│                                                              │
│  "For procedures → read vault SOP → execute via skill"      │
│  Links to: 40-Procedures/New Project SOP.md                 │
│            40-Procedures/Add MCP Server SOP.md              │
│            40-Procedures/Config Management SOP.md           │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration Layers

Configuration is built in **merge order** (last wins):

### 1. Base Template (Foundation)

**Source**: `claude.config_templates` where `template_name = 'hooks-base'`

**Contains**:
- Core hooks (SessionStart, SessionEnd, UserPromptSubmit, PreToolUse)
- Instruction matcher
- Session auto-logging

**Query**:
```sql
SELECT content FROM claude.config_templates WHERE template_name = 'hooks-base';
```

### 2. Project Type Defaults (By Project Type)

**Source**: `claude.project_type_configs`

**Contains**:
- Default MCP servers for project type
- Default skills
- Default instructions
- Reference to hook template

**Project Types**:
- `infrastructure` - Tooling/infrastructure projects
- `csharp-desktop` - C# .NET desktop apps
- `csharp-winforms` - C# WinForms apps
- `web-app` - Web applications
- `tauri-react` - Tauri desktop apps

**Query**:
```sql
SELECT * FROM claude.project_type_configs WHERE project_type = 'infrastructure';
```

### 3. Project-Specific Overrides (Per Project)

**Source**: `claude.workspaces.startup_config` (JSONB column)

**Contains**:
- Additional MCP servers for this project
- Additional hooks
- Disabled hooks
- Custom permissions

**Query**:
```sql
SELECT project_name, startup_config
FROM claude.workspaces
WHERE project_name = 'claude-family';
```

### 4. Current Permissions (Preserved)

**Source**: Existing `.claude/settings.local.json`

**Preserved During Regeneration**:
- `permissions.allow` - Approved tools
- `permissions.deny` - Blocked tools
- `permissions.ask` - Tools requiring approval

**Why**: User grants permissions at runtime; database shouldn't override.

---

## Configuration Flow

### On Every SessionStart

1. **Hook Triggers**: `SessionStart` hook in `.claude/settings.local.json` calls `session_startup_hook.py`

2. **Config Sync**: Hook calls `generate_project_settings.py`:
   ```python
   sync_project_config(project_name, cwd)
   ```

3. **Database Reads**:
   - Get project type from `workspaces`
   - Get base template from `config_templates`
   - Get type defaults from `project_type_configs`
   - Get overrides from `workspaces.startup_config`

4. **Merge**:
   ```python
   base = get_base_template()
   type_defaults = get_project_type_defaults(project_type)
   overrides = get_workspaces_overrides(project_name)

   merged = deep_merge(base, type_defaults)
   final = deep_merge(merged, overrides)
   ```

5. **Write**: Generate `.claude/settings.local.json` with merged config

6. **Session Continues**: Claude Code reads the newly generated settings

**This is self-healing**: Corrupted/manually-edited files get regenerated every session.

---

## Updating Configuration

### Update All Projects of a Type

**Use Case**: Add new hook to all infrastructure projects

```sql
-- Option 1: Update project_type_configs
UPDATE claude.project_type_configs
SET default_mcp_servers = array_append(default_mcp_servers, 'new-mcp')
WHERE project_type = 'infrastructure';

-- Option 2: Update base template (affects ALL projects)
UPDATE claude.config_templates
SET content = jsonb_set(
    content,
    '{hooks,PostToolUse}',
    '[{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo done", "timeout": 1}]}]'::jsonb
)
WHERE template_name = 'hooks-base';
```

**Next Session**: All projects of that type get the update automatically.

### Update Single Project

**Use Case**: Add custom hook to one project

```sql
UPDATE claude.workspaces
SET startup_config = '{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "prompt",
        "prompt": "Custom reminder for this project",
        "timeout": 5
      }]
    }]
  }
}'::jsonb
WHERE project_name = 'specific-project';
```

**Next Session**: Only that project gets the custom hook.

### Update Global Settings (Not Recommended)

**Why Not**: Manual file edits bypass the database system.

**If You Must**:
1. Edit `~/.claude/settings.json` (global, all projects)
2. Edit `.claude/settings.json` (project-level, git-tracked)
3. DO NOT edit `.claude/settings.local.json` (regenerated every session)

---

## Inspecting Current Configuration

### What Project Has Right Now

```bash
# Check generated settings
cat .claude/settings.local.json | jq .

# Check hooks
cat .claude/settings.local.json | jq '.hooks | keys'

# Check MCP servers
cat .claude/settings.local.json | jq '.enabledMcpjsonServers'
```

### What Database Says It Should Have

```sql
-- Check project type
SELECT project_type FROM claude.workspaces WHERE project_name = 'project-name';

-- Check type defaults
SELECT default_mcp_servers, default_skills
FROM claude.project_type_configs
WHERE project_type = (
    SELECT project_type FROM claude.workspaces WHERE project_name = 'project-name'
);

-- Check project overrides
SELECT startup_config
FROM claude.workspaces
WHERE project_name = 'project-name';
```

### Regenerate Manually (For Testing)

```bash
cd C:\Projects\project-name
python C:\Projects\claude-family\scripts\generate_project_settings.py project-name

# Check logs
cat ~/.claude/hooks.log | tail -20
```

---

## Configuration Tables Reference

### claude.config_templates

**Purpose**: Reusable configuration templates

**Key Columns**:
- `template_id` - Primary key
- `template_name` - Unique name (e.g., 'hooks-base')
- `config_type` - 'hooks', 'commands', 'settings', 'mcp', 'instructions'
- `content` - JSONB config
- `extends_template_id` - Inheritance support
- `version` - Version number

**Constraints**:
- `config_type` must be in allowed list
- `template_name` must be unique

### claude.project_type_configs

**Purpose**: Default configurations per project type

**Key Columns**:
- `project_type` - Unique type identifier
- `default_hook_template_id` - FK to config_templates
- `default_mcp_servers` - TEXT[] array
- `default_skills` - TEXT[] array
- `default_instructions` - TEXT[] array

**Constraints**:
- `project_type` must be lowercase-with-hyphens
- Length between 3-50 chars

### claude.workspaces

**Purpose**: Project registry and overrides

**Key Columns**:
- `project_name` - Project identifier
- `project_path` - Filesystem path
- `project_type` - FK to project_type_configs
- `startup_config` - JSONB overrides

**Constraints**:
- `startup_config` must be valid JSON object or NULL

### claude.project_config_assignments

**Purpose**: Track which templates are assigned to which projects

**Key Columns**:
- `project_id` - FK to projects
- `template_id` - FK to config_templates
- `override_content` - JSONB project-specific overrides
- `deployed_at` - Timestamp
- `deployment_hash` - File hash for change detection

### claude.config_deployment_log

**Purpose**: Audit trail of configuration deployments

**Key Columns**:
- `project_id` - Which project
- `config_type` - What type of config
- `file_path` - Where it was deployed
- `action` - 'deployed', 'updated', 'deleted'
- `deployed_at` - When

---

## Troubleshooting

### Settings Not Updating

**Symptom**: Changed database config, but settings.local.json unchanged

**Causes**:
1. Config sync failed (check `~/.claude/hooks.log`)
2. Database not accessible
3. Wrong project name

**Fix**:
```bash
# Regenerate manually
python scripts/generate_project_settings.py project-name

# Check logs
cat ~/.claude/hooks.log | grep config_generator
```

### Manual Edits Keep Getting Overwritten

**Symptom**: I edit `.claude/settings.local.json` but changes disappear next session

**Explanation**: This is **by design** (self-healing). Settings regenerate from database every session.

**Fix**: Add your changes to database instead:
```sql
UPDATE claude.workspaces
SET startup_config = '{your custom config}'::jsonb
WHERE project_name = 'project-name';
```

### Hook Not Firing

**Symptom**: Added hook to database, but it doesn't execute

**Diagnose**:
1. Check settings.local.json has the hook
2. Check hook syntax is valid
3. Check hook command/script exists and is executable
4. Check hooks.log for errors

**Fix**:
```bash
# Verify hook in settings
cat .claude/settings.local.json | jq '.hooks.HookType'

# Test hook command manually
python path/to/hook/script.py

# Check logs
cat ~/.claude/hooks.log | grep HookType
```

### Database Connection Failed

**Symptom**: Config sync fails with "Database not available"

**Causes**:
1. PostgreSQL not running
2. Wrong connection string
3. Network issues

**Fix**:
```bash
# Check PostgreSQL running
pg_isready

# Check connection string
echo $DATABASE_URL

# Check ai-workspace config
cat c:/Users/johnd/OneDrive/Documents/AI_projects/ai-workspace/config.py
```

---

## Best Practices

1. **Never Edit settings.local.json**: Always update database instead
2. **Test Changes**: Update one project first, then expand to project type
3. **Use Comments**: Add `description` field in JSON for documentation
4. **Version Control**: Database changes are tracked, file changes aren't
5. **Audit Trail**: Use config_deployment_log to track changes
6. **Schema Enforcement**: Database constraints prevent invalid configs
7. **Check Logs**: Always check `~/.claude/hooks.log` after changes

---

## Migration from Manual to DB-Driven

If you have a project with manual `.claude/settings.local.json`:

### 1. Extract Current Config

```bash
cat .claude/settings.local.json | jq . > current-config.json
```

### 2. Decide What Goes Where

- **Common across type**: → project_type_configs
- **Project-specific**: → workspaces.startup_config
- **One-off/temporary**: → Keep manual (will be regenerated)

### 3. Add to Database

```sql
-- Add project-specific hooks
UPDATE claude.workspaces
SET startup_config = '{...config from step 1...}'::jsonb
WHERE project_name = 'project-name';
```

### 4. Test Regeneration

```bash
# Backup current settings
cp .claude/settings.local.json .claude/settings.local.json.backup

# Regenerate from database
python scripts/generate_project_settings.py project-name

# Compare
diff .claude/settings.local.json.backup .claude/settings.local.json
```

### 5. Verify Next Session

Start new session, check hooks fire correctly.

---

## Related Procedures

- [[New Project SOP]] - Uses this config system for new projects
- [[Add MCP Server SOP]] - Adding MCP servers via database
- [[Session Lifecycle - Session Start]] - When config sync happens

---

## Configuration Schema

```typescript
interface Settings {
  hooks?: {
    [hookType: string]: HookConfig[]
  }
  enabledMcpjsonServers?: string[]
  skills?: string[]
  instructions?: string[]
  permissions?: {
    allow: string[]
    deny: string[]
    ask: string[]
  }
}

interface HookConfig {
  matcher?: string  // For PreToolUse, PostToolUse
  hooks: Hook[]
}

interface Hook {
  type: 'command' | 'prompt'
  command?: string  // For type=command
  prompt?: string   // For type=prompt
  timeout: number   // Seconds
  description?: string
}
```

---

**Version**: 1.0
**Author**: Claude Family
**Last Review**: 2025-12-27
