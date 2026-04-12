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
  - mcp__postgres__execute_sql
---

# Documentation Keeper Skill

## Purpose

Maintain accuracy of documentation, vault entries, and configuration registries.

## Responsibilities

### 1. MCP Registry Verification

Check MCP registry (use `entity_read("MCP registry")` to load) against:
- `~/.claude.json` global mcpServers
- Per-project mcpServers in projects section
- Individual `.mcp.json` files

### 2. Agent Spec Verification

Check `.claude/agents/` directory for:
- All agent_types have a corresponding `.md` agent file
- Agent files are current and reference valid tools
- Note: `mcp-servers/orchestrator/` has been retired (2026-02-24). Agent definitions are now in `.claude/agents/`.

### 3. Skill Path Verification

Check all skills in `.claude/skills/` exist and have content:
- Each skill folder has SKILL.md
- References in docs match actual skill locations

### 4. Vault Entry Staleness

Check knowledge-vault entries for:
- Outdated dates (synced_at > 30 days)
- Broken wiki links
- Missing related entries

## Verification Workflow

Use built-in Read/Glob/Grep tools (filesystem MCP retired Jan 2026):

```
1. Read MCP Registry.md
2. Read ~/.claude.json mcpServers section
3. Glob("**/.mcp.json", path="C:/Projects/") to list project MCP configs
4. Compare and flag discrepancies
5. Glob(".claude/agents/*.md") to list current agent definitions
6. Verify skill paths with Glob(".claude/skills/*/SKILL.md")
7. Output findings
```

## Output Format

```markdown
## Documentation Keeper Report - {date}

### MCP Registry
- [x] postgres: matches
- [x] project-tools: matches
- [ ] bpmn-engine: MISSING from global config

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

- MCP Registry: `entity_read("MCP registry")`
- Agent Definitions: `.claude/agents/` (orchestrator retired 2026-02-24)
- Skills: `.claude/skills/`

---

**Version**: 1.1 (Fix retired refs: mcp__filesystem__*â†’built-in tools, orchestrator agent_specs.jsonâ†’.claude/agents/)
**Created**: 2026-01-08
**Updated**: 2026-03-09
**Location**: .claude/skills/doc-keeper/SKILL.md
