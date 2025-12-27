---
projects:
- claude-family
tags:
- plugins
- configuration
- architecture
- hooks
synced: false
synced_at: '2025-12-27T14:00:00.000000'
---

# Plugins

Plugin architecture for distributing Claude configurations.

## Structure

```
.claude-plugins/claude-family-core/
├── .claude-plugin/plugin.json
├── .mcp.json
├── commands/
├── hooks/
│   ├── SessionStart
│   ├── SessionEnd
│   ├── PreToolUse
│   ├── UserPromptSubmit
│   └── PostToolUse
├── scripts/
│   ├── session_startup_hook.py
│   ├── instruction_matcher.py
│   └── config validator scripts
└── agents/
    └── (specialty agents for this project)
```

## Plugin Hooks (SessionStart Integration)

All plugin hooks are now coordinated through **unified configuration system**:

### SessionStart Hook Workflow

When Claude starts on a project with this plugin:

```
1. Claude Code reads .claude/settings.local.json
   (generated from database each session)
   ↓
2. SessionStart hook fires
   ↓
3. session_startup_hook.py runs:
   • Calls generate_project_settings.py
   • Syncs config from database
   • Creates session record
   • Loads previous state
   ↓
4. Claude ready to work
```

**Key**: Config sync happens **first** before session creation, ensuring settings are current

### Hook Files

Hooks are **no longer** stored in `.claude/hooks.json`:

✅ **Correct location**: `.claude/settings.local.json`
❌ **Wrong location**: `.claude/hooks.json` (not used)

The unified config system automatically includes plugin hooks in `settings.local.json` during generation.

## Installation & Distribution

Plugins distribute configuration through **database-driven system**:

### Old System (Pre-2025-12-27)
```
❌ install_plugin.py copies hooks manually
❌ Hooks stored in .claude/hooks.json
❌ Multiple overlapping systems
```

### New System (Unified Config)
```
✅ Database = Single source of truth (project_type_configs, config_templates)
✅ Hooks stored in config_templates (reusable blocks)
✅ generate_project_settings.py merges everything
✅ settings.local.json regenerates on SessionStart
✅ Auto-sync prevents drift across projects
```

### Plugin Distribution Steps

1. **Define reusable config** in `config_templates`:
   - Hook definitions
   - MCP server configs
   - Skill sets

2. **Link to project type** in `project_type_configs`:
   - Reference template IDs
   - Specify defaults for this type

3. **Override per project** in `workspaces.startup_config`:
   - Add project-specific tweaks
   - Reference custom MCPs

4. **Auto-sync on SessionStart**:
   - `generate_project_settings.py` runs
   - Merges all layers
   - Generates `settings.local.json`

## Unified Configuration System

The plugin system now integrates with **database-driven configuration**:

**See**: [[Config Management SOP]] for complete system design

### Database Tables (Plugin Data)

| Table | Contents | Updated By |
|-------|----------|-----------|
| `config_templates` | Reusable hook/MCP/skill blocks | SQL or UI |
| `project_type_configs` | Defaults for infrastructure/web-app/etc. | SQL or UI |
| `workspaces` | Project-specific overrides (startup_config column) | SQL or UI |
| `mcp_configs` | Installed MCP server tracking | Auto on MCP add |
| `config_deployment_log` | Audit trail of all changes | Auto on generation |

### Configuration Hierarchy

```
config_templates (base blocks)
    ↓
project_type_configs (type defaults)
    ↓
workspaces.startup_config (project overrides)
    ↓
existing file permissions (preserved)
    ↓
= Final settings.local.json (generated)
```

**Self-Healing**: Regenerates every session, preventing manual edits from causing drift

## Commands & Skills Integration

Plugins also distribute:

### Commands
- Location: `commands/` directory
- Distribution: Copied to `.claude/commands/` during setup
- **Status**: Works via existing command system

### Skills
- Location: Database reference in project_type_configs
- Example: "database-operations", "code-review", "testing-patterns"
- Distribution: Merged into settings during generation

## Related Docs

- [[Config Management SOP]] - Complete unified configuration guide
- [[MCP configuration]] - MCP server management (now database-driven)
- [[Settings File]] - Generated settings documentation
- [[Claude Hooks]] - Hook types and usage
- [[Slash command's]] - Command distribution

---

**Version**: 2.0 (Unified Config System)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/Plugins.md