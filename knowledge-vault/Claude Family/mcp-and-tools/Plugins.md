---
projects:
- claude-family
tags:
- plugins
- configuration
- database-driven
synced: false
---

# Plugins

Plugin architecture distributes configurations through database-driven system.

---

## Structure

```
.claude-plugins/claude-family-core/
├── .claude-plugin/plugin.json
├── commands/          # Slash commands
├── scripts/           # session_startup_hook.py, instruction_matcher.py
└── agents/            # Specialty agents
```

---

## SessionStart Workflow

```
1. Claude reads .claude/settings.local.json (auto-generated from DB)
2. SessionStart hook fires
3. session_startup_hook.py:
   • Calls generate_project_settings.py
   • Syncs config from database
   • Creates session record
4. Claude ready
```

**Key**: Config sync happens **first**, ensuring settings current.

---

## Database-Driven Distribution

Plugins distribute via **database**, not manual file copies.

### Configuration Flow

```
config_templates (reusable blocks)
    ↓
project_type_configs (type defaults)
    ↓
workspaces.startup_config (project overrides)
    ↓
= settings.local.json (auto-generated)
```

**Self-Healing**: Regenerates every session from database.

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `config_templates` | Reusable hook/MCP/skill blocks |
| `project_type_configs` | Defaults per project type |
| `workspaces` | Project-specific overrides |
| `mcp_configs` | MCP server tracking |
| `config_deployment_log` | Audit trail |

---

## Distribution Steps

1. **Define config** in `config_templates` (hooks, MCPs, skills)
2. **Link to type** in `project_type_configs`
3. **Override per project** in `workspaces.startup_config`
4. **Auto-sync** on SessionStart via `generate_project_settings.py`

---

## Components Distributed

### Hooks
- **Location**: `config_templates` → `settings.local.json`
- **Types**: SessionStart, SessionEnd, PreToolUse, PostToolUse
- **Status**: Database-driven

### Commands
- **Location**: `commands/` → `.claude/commands/`
- **Distribution**: Copied during setup
- **Status**: File-based (existing system)

### Skills
- **Location**: Referenced in `project_type_configs.default_skills`
- **Examples**: database-operations, code-review, testing-patterns
- **Distribution**: Merged into settings during generation

### MCP Servers
- **Location**: `project_type_configs.default_mcp_servers`
- **Distribution**: Merged into settings
- **Status**: Database-driven

---

## Related

- [[Config Management SOP]] - Complete unified configuration
- [[MCP configuration]] - MCP management
- [[Settings File]] - Generated settings
- [[Claude Hooks]] - Hook types
- [[Slash command's]] - Commands

---

**Version**: 3.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/Plugins.md
