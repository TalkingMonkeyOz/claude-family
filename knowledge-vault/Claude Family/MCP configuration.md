---
projects:
- claude-family
tags:
- mcp
- configuration
- database-driven
- project-types
synced: false
synced_at: '2025-12-27T14:15:00.000000'
---

# MCP Configuration

How MCPs are configured across Claude projects (now database-driven).

---

## Configuration Tiers

### Tier 1: Global (All Projects)

**Location**: `~/.claude.json` → `mcpServers`

**Current Global MCPs**:

| Server | Purpose | Tokens |
|--------|---------|--------|
| postgres | Database access | ~6k |
| orchestrator | Agent spawning | ~9k |
| sequential-thinking | Complex reasoning | ~2k |
| python-repl | Python execution | ~2k |

### Tier 2: Project Type Defaults (Database)

**Location**: `claude.project_type_configs.default_mcp_servers`

**How It Works**: All projects of same type inherit MCP defaults

**Example** - Infrastructure Type:
```sql
SELECT project_type, default_mcp_servers
FROM claude.project_type_configs
WHERE project_type = 'infrastructure';

-- Result:
-- project_type | default_mcp_servers
-- infrastructure | {postgres,orchestrator,memory}
```

**Projects Using**: claude-family, claude-family-manager-v2, nimbus-import

**Update Tier 2 MCPs**:
```sql
-- Add MCP to all infrastructure projects
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY_APPEND(
  default_mcp_servers,
  'custom-mcp'
)
WHERE project_type = 'infrastructure';

-- Changes take effect on next SessionStart for all infrastructure projects
```

### Tier 3: Project-Specific Overrides (Database)

**Location**: `claude.workspaces.startup_config` (JSONB column)

**Use Case**: Add MCP to only one project, not all projects of that type

**Example**:
```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  COALESCE(startup_config, '{}'::jsonb),
  '{enabledMcpjsonServers}',
  jsonb_build_array(
    'postgres', 'orchestrator', 'memory', 'special-custom-mcp'
  )
)
WHERE project_name = 'claude-family';

-- Only claude-family gets special-custom-mcp
```

### Tier 4: Generated Settings

**Location**: `.claude/settings.local.json` (generated, don't edit)

**Process**:
```
config_templates (base)
    ↓
project_type_configs (type defaults)
    ↓
workspaces.startup_config (project overrides)
    ↓
generate_project_settings.py
    ↓
.claude/settings.local.json
```

**Generated Section**:
```json
{
  "enabledMcpjsonServers": [
    "postgres",
    "orchestrator",
    "memory",
    "any-project-specific-servers"
  ]
}
```

---

## Database-Driven MCP System (New)

### Before: Manual Configuration

```
❌ Edit .mcp.json manually
❌ Edit .claude/settings.local.json manually
❌ Copy to other projects manually
❌ Hope they stay in sync
❌ Debug when they don't
```

### After: Database-Driven

```
✅ Define in database (project_type_configs or workspaces)
✅ Auto-generate on SessionStart
✅ All projects of same type get update
✅ Audit trail (config_deployment_log)
✅ Self-healing (overwrites manual edits)
```

### Tables Involved

| Table | Purpose | Example |
|-------|---------|---------|
| `project_type_configs` | MCP defaults by project type | infrastructure → {postgres, orchestrator, memory} |
| `workspaces` | Project-specific overrides (startup_config column) | claude-family → custom overrides |
| `mcp_configs` | Audit tracking of installed MCPs | Logs when MCP added |
| `config_deployment_log` | History of all config changes | Who, what, when, why |

---

## Project-Specific MCPs

### Current Setup

| MCP | Type | Projects | Status |
|-----|------|----------|--------|
| filesystem | infrastructure | claude-family | Project-specific |
| memory | infrastructure | claude-family | Project-specific |
| mui-mcp | web-app | nimbus-import, ATO | Per-project |

### Adding to Specific Project

1. **Check project type**:
```sql
SELECT project_type FROM claude.workspaces
WHERE project_name = 'claude-family';
-- Result: infrastructure
```

2. **Add to project override**:
```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  COALESCE(startup_config, '{}'::jsonb),
  '{enabledMcpjsonServers}',
  jsonb_build_array('postgres', 'orchestrator', 'memory', 'new-mcp')
)
WHERE project_name = 'claude-family';
```

3. **On next SessionStart**, new MCP loads automatically

---

## Configuration Examples

### Example 1: Add MCP to All Type Projects

**Goal**: Add "custom-mcp" to all infrastructure projects

```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY_APPEND(
  default_mcp_servers,
  'custom-mcp'
)
WHERE project_type = 'infrastructure';
```

**Effect**:
- claude-family ✅
- claude-family-manager-v2 ✅
- nimbus-import ✅
- All on next SessionStart

### Example 2: Add MCP to One Project

**Goal**: Add "debug-mcp" only to "claude-family"

```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(
  COALESCE(startup_config, '{}'::jsonb),
  '{enabledMcpjsonServers}',
  (COALESCE(startup_config->>'enabledMcpjsonServers', '[]')::jsonb
   || '["debug-mcp"]'::jsonb)
)
WHERE project_name = 'claude-family';
```

**Effect**: Only claude-family gets debug-mcp

### Example 3: Remove MCP from Type

**Goal**: Remove "memory" from all infrastructure projects

```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY_REMOVE(
  default_mcp_servers,
  'memory'
)
WHERE project_type = 'infrastructure';
```

**Effect**: All infrastructure projects lose "memory" on next SessionStart

---

## Adding MCPs (Old vs New)

### Old Method: `.mcp.json`

```json
{
  "mcp-name": {
    "type": "stdio",
    "command": "cmd",
    "args": ["/c", "npx", "-y", "@package/name@latest"]
  }
}
```

**Status**: ⚠️ Still works but not recommended
**Reason**: Not integrated with database-driven system

### New Method: Database + Config Generator

1. **Define in config_templates**:
```sql
INSERT INTO claude.config_templates (name, template_content)
VALUES (
  'my-mcp',
  '{"mcp-name": {"type": "stdio", "command": "..."}}'::jsonb
);
```

2. **Reference from project_type_configs**:
```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY_APPEND(...)
WHERE project_type = 'infrastructure';
```

3. **Auto-generated in settings.local.json** on SessionStart

---

## MCP Registry

**See**: [[MCP Registry]] for complete MCP list with installation guidelines

---

## Troubleshooting

### "MCP won't load"

1. Check it's in enabledMcpjsonServers:
```bash
grep -A 5 "enabledMcpjsonServers" .claude/settings.local.json
```

2. Check database config:
```sql
SELECT default_mcp_servers FROM claude.project_type_configs
WHERE project_type = 'infrastructure';
```

3. Check project override:
```sql
SELECT startup_config FROM claude.workspaces
WHERE project_name = 'claude-family';
```

4. Regenerate settings:
```bash
python scripts/generate_project_settings.py claude-family
```

### "Changes aren't taking effect"

Settings regenerate on SessionStart. Either:
- Wait for next session start, OR
- Manually regenerate:
```bash
python scripts/generate_project_settings.py PROJECT-NAME
```

### "How do I see what MCPs are loaded?"

Check generated settings file:
```bash
cat .claude/settings.local.json | grep -A 10 enabledMcpjsonServers
```

---

## Related Docs

- [[Settings File]] - Generated settings documentation (database-driven)
- [[Config Management SOP]] - Complete configuration system
- [[MCP Registry]] - Complete MCP list
- [[Orchestrator MCP]] - Agent spawning details
- [[Claude Tools Reference]] - Tool documentation

---

## Change Log

| Date | Change |
|------|--------|
| 2025-12-27 | Database-driven MCP configuration (project_type_configs) |
| 2025-12-27 | Auto-generation via generate_project_settings.py |
| 2025-12-21 | Moved filesystem/memory to project-specific |
| 2025-12-20 | Added doc-keeper-haiku to orchestrator |

---

**Version**: 2.0 (Database-Driven)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/MCP configuration.md