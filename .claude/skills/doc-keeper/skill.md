---
name: doc-keeper
description: Documentation Keeper - maintains vault and registry accuracy
model: haiku
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - mcp__filesystem__*
  - mcp__postgres__execute_sql
---

# Documentation Keeper Skill

## Purpose

Maintain accuracy of documentation, vault entries, and configuration registries.

## Responsibilities

### 1. MCP Registry Verification

Check `knowledge-vault/Claude Family/MCP Registry.md` against:
- `~/.claude.json` global mcpServers
- Per-project mcpServers in projects section
- Individual `.mcp.json` files

### 2. Agent Spec Verification

Check `mcp-servers/orchestrator/agent_specs.json` for:
- All agent_types have corresponding config in configs/
- Removed agents list is accurate
- Token costs are reasonable estimates

### 3. Skill Path Verification

Check all skills in `.claude/skills/` exist and have content:
- Each skill folder has skill.md
- References in docs match actual skill locations

### 4. Vault Entry Staleness

Check knowledge-vault entries for:
- Outdated dates (synced_at > 30 days)
- Broken wiki links
- Missing related entries

## Verification Workflow

```
1. Read MCP Registry.md
2. Read ~/.claude.json mcpServers section
3. List all .mcp.json files in C:\Projects\
4. Compare and flag discrepancies
5. Check agent_specs.json
6. Verify skill paths
7. Output findings
```

## Output Format

```markdown
## Documentation Keeper Report - {date}

### MCP Registry
- [x] postgres: matches
- [ ] filesystem: STALE - now project-specific only
- [x] orchestrator: matches

### Agent Specs
- [x] 14 agents in spec
- [ ] doc-keeper-haiku: missing config (FIXED)

### Skills
- [x] database: exists
- [x] doc-keeper: exists
- [ ] nimbus-api: placeholder only

### Actions Taken
- Updated MCP Registry.md line 45
- Created feedback #xyz for nimbus-api skill
```

## Schedule

- Recommended: Weekly (Sunday 7am)
- Trigger: `claude.scheduled_jobs` with job_name='doc-keeper-weekly'

## Related

- MCP Registry: `knowledge-vault/Claude Family/MCP Registry.md`
- Agent Specs: `mcp-servers/orchestrator/agent_specs.json`
- Skills: `.claude/skills/`
