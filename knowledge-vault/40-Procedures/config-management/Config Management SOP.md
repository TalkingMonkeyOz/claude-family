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
Database → sync_project.py → .claude/settings.local.json (ALL config)
                           → .claude/skills/              (from claude.skills)
                           → .claude/rules/               (from claude.rules)
                           → .claude/instructions/        (from claude.instructions)
                           → .claude/agents/              (from claude.skills scope='agent')
                           → .claude/commands/            (from claude.skills scope='command')
```

**Source Tables**:
- `config_templates` - Base hook configurations
- `project_type_configs` - Defaults per project type
- `workspaces` - Per-project overrides (startup_config column)
- `config_deployment_log` - Audit trail
- `skills` - Skills, commands, and agents (distinguished by `scope`)
- `rules` - Rule files
- `instructions` - Auto-apply instruction files

**Generated Files** (regenerated every SessionStart):
- `.claude/settings.local.json` - ALL settings (hooks, MCP servers, skills, permissions)
- `.claude/skills/`, `.claude/rules/`, `.claude/instructions/` - Deployed from DB
- `.claude/commands/`, `.claude/agents/` - Deployed from DB (`claude.skills` table)

**Note**: Claude Code reads hooks from settings files only (`settings.json` or `settings.local.json`), NOT from a separate `hooks.json` file.

---

## Unified Deployment Script

`scripts/sync_project.py` (980 lines) is the single entry point for all project config deployment. It replaces three earlier scripts (`generate_project_settings.py`, `generate_mcp_config.py`, `deploy_project_configs.py`) and the manual `C:\claude\shared\commands\` folder copy step.

**What it deploys in one pass**:

| Component | Source table | Output location |
|-----------|-------------|-----------------|
| `settings.local.json` | `config_templates` + `workspaces` | `.claude/settings.local.json` |
| Skills | `claude.skills` where `scope IN ('global','project')` | `.claude/skills/` |
| Rules | `claude.rules` | `.claude/rules/` |
| Instructions | `claude.instructions` | `.claude/instructions/` |
| Commands | `claude.skills` where `scope='command'` | `.claude/commands/` |
| Agents | `claude.skills` where `scope='agent'` | `.claude/agents/` |

**Launcher integration**: `C:\claude\start-claude.bat` calls `sync_project.py --no-interactive` once at startup instead of the previous four separate script calls.

**Commands migrated to skills (2026-03-15)**: All 24 legacy commands converted to skills with YAML frontmatter. The `claude.skills` table stores all component types via `scope`:
- `scope='global'` — skills available to all projects (24 active)
- `scope='project'` — skills scoped to a single project (31 active)
- `scope='agent'` — agent definitions (19 active)
- `scope='command'` — deprecated (deactivated, migrated to global skills)

**File protection**: PreToolUse hook blocks direct edits to all DB-managed files: `CLAUDE.md`, `.claude/skills/*/SKILL.md`, `.claude/rules/*.md`, `.claude/agents/*.md`, `settings.local.json`, `.mcp.json`. Redirects to proper DB update channels.

**CLAUDE.md versioning**: `update_claude_md()` MCP tool now creates `profile_versions` snapshots on every edit, matching core protocol versioning pattern.

**Hooks**: 10 hook types, 19 handlers (was 7/16). New: PostCompact, TaskCompleted, ConfigChange.

**Counts (2026-03-15)**: 32 skills (24 global + 8 project-specific), 19 agents, 7 rules, 9 instructions.

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
2. Calls `sync_project.py` (previously `generate_project_settings.py`)
3. Reads database (project type, base template, type defaults, overrides, skills, rules, instructions)
4. Merges configs: `base → type defaults → project overrides`
5. Preserves permissions from existing settings
6. Writes `settings.local.json` plus deploys skills, rules, instructions, commands, and agents

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

Config operations available as MCP tools that handle file + DB atomically. All changes logged to `config_deployment_log`.

| Tool | Purpose |
|------|---------|
| `update_claude_md(section, content)` | Update CLAUDE.md sections (DB + file together) |
| `deploy_claude_md(project)` | Deploy CLAUDE.md from DB to file (one-way) |
| `deploy_project(components)` | Deploy skills/instructions/rules from DB to files |
| `regenerate_settings()` | Force-recreate `settings.local.json` from DB |

- ✅ **Use tools** for session-time config changes
- ✅ **Use SQL** for bulk seeding or initial data
- ⚠️ **Never manual file edits** — files regenerate from DB

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
python scripts/sync_project.py project-name
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
| `skills` | Skills, commands, and agents | name, **scope** (`global`/`project`/`command`/`agent`), project_id, content |
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
# Regenerate (all components: settings, skills, rules, commands, agents)
python scripts/sync_project.py project-name

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

Back up existing config, add to DB (`workspaces.startup_config` for one project, `project_type_configs` for a type), run `sync_project.py`, compare output, restart Claude Code.

---

## Related

- [[New Project SOP]] - Uses config system for new projects
- [[Add MCP Server SOP]] - Adding MCPs via database
- [[Session Lifecycle - Session Start]] - When config sync happens
- [[Settings File]] - Detailed configuration guide

---

**Version**: 3.4 (Commands→skills migration, file protection, 10 hook types, CLAUDE.md versioning)
**Created**: 2025-12-27
**Updated**: 2026-03-15
**Location**: 40-Procedures/Config Management SOP.md
