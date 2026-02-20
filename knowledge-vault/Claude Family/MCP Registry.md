---
projects:
- claude-family
synced: false
synced_at: '2025-12-27T00:00:00.000000'
tags:
- quick-reference
- mcp
- claude-family
---

# MCP Registry

Registry of installed MCPs with project assignments and token costs.

**For installation**: See [[Add MCP Server SOP]]

---

## Active MCPs (Global - in `~/.claude.json`)

### postgres
**Purpose**: Database access to `ai_company_foundation`
**Tokens**: ~6k
**Package**: `postgres-mcp.exe`
**Scope**: Global (all projects)

### orchestrator
**Purpose**: Spawn agents (19 types) + inter-Claude messaging + agent stats
**Tokens**: ~9k
**Package**: Custom (`mcp-servers/orchestrator/`)
**Scope**: Global (all projects)
**Docs**: [[Orchestrator MCP]]

### project-tools
**Purpose**: Work tracking, knowledge, config ops, conversations, books
**Tokens**: ~12k
**Package**: Custom (`mcp-servers/project-tools/`)
**Scope**: Global (all projects)
**Key tools**: advance_status, start_work, complete_work, update_claude_md, extract_conversation, store_book, recall_knowledge (40+ total)
**Note**: v3 (2026-02-11): Added 15 tools across 4 pillars (P0: Conversations, P1: Config, P2: Knowledge, P3: Work Tracking)

### sequential-thinking
**Purpose**: Complex multi-step reasoning
**Tokens**: ~2k
**Package**: `@modelcontextprotocol/server-sequential-thinking` (globally installed, direct node path)
**Scope**: Global (all projects)

### python-repl
**Purpose**: Execute Python code with persistent session
**Tokens**: ~2k
**Package**: `mcp-python` v0.1.4 (3rd party, MIT)
**Scope**: Global
**Note**: No sandboxing - local dev only. `list_variables` bug patched locally.

## Active MCPs (Project-specific - in `.mcp.json` or settings)

### nimbus-knowledge
**Purpose**: Nimbus project domain knowledge (facts, patterns, learnings)
**Tokens**: ~3k
**Package**: Custom (`mcp-servers/nimbus-knowledge/`)
**Scope**: Nimbus projects only (`nimbus_context` schema)
**Data**: 61 facts, 12 patterns, 12 learnings

### mui
**Purpose**: MUI X component documentation
**Tokens**: ~2k
**Package**: `@mui/mcp` (globally installed, direct node path)
**Scope**: Project (nimbus-import, ATO-Tax-Agent, claude-family, claude-manager-mui, nimbus-mui)

### playwright
**Purpose**: Browser automation and testing via Playwright
**Tokens**: ~3k
**Package**: `@playwright/mcp` (globally installed, direct node path)
**Scope**: Project (claude-family, claude-manager-mui)

## Removed MCPs

| MCP | Removed | Replaced By |
|-----|---------|-------------|
| filesystem | 2026-01 | Built-in Read/Write/Edit tools |
| memory | 2026-01 | project-tools knowledge + session facts |
| vault-rag | 2026-01 | UserPromptSubmit hook (auto RAG) |

---

## Installation Decision Tree

**Before installing**:

1. **Is it needed globally?** → Add to `~/.claude.json`
2. **Per-project?** → Add to `.mcp.json` (git-tracked)
3. **This machine only?** → Add to `~/.claude.json` projects[path]

**Token cost check**:
- Under 3k: ✅ Fine
- 3-6k: ⚠️ Consider if needed
- Over 6k: ❌ Only if essential

**Alternatives?**
- filesystem → Read/Write/Edit tools (built-in)
- memory → project-tools knowledge (better integration)
- web fetch → WebFetch tool (built-in)
- vault-rag → UserPromptSubmit hook (automatic)

---

## Quick Install (npx package)

**Step 1**: Install globally (eliminates cmd.exe shim overhead):
```bash
npm install -g @package/name
```

**Step 2**: Add to database (use simple npx format - generator resolves to direct node):
```sql
UPDATE claude.workspaces
SET startup_config = jsonb_set(startup_config, '{mcp_configs,mcp-name}',
  '{"type": "stdio", "command": "npx", "args": ["-y", "@package/name"]}'::jsonb)
WHERE project_name = 'your-project';
```

**Step 3**: Regenerate:
```bash
python scripts/generate_mcp_config.py your-project
```

Generator automatically resolves `npx` to `node.exe <entry_point>` if globally installed.

**Full guide**: [[Add MCP Server SOP]]

---

## Token Budgets by Project

| Project | Current | Target | Max |
|---------|---------|--------|-----|
| claude-family | ~25k | 25k | 30k |
| ATO-Tax-Agent | ~17k | 20k | 25k |
| mission-control-web | ~15k | 20k | 25k |

---

## Before Adding MCP

- [ ] Token cost <6k?
- [ ] No built-in alternative?
- [ ] Globally installed? (`npm install -g`)
- [ ] Tested locally?

---

## Related

- [[Add MCP Server SOP]] - Installation procedure
- [[MCP configuration]] - Database-driven config
- [[Setting's File]] - Settings structure
- [[Claude Tools Reference]] - All available tools
- [[Orchestrator MCP]] - Orchestrator details

---

**Version**: 4.0 (npx resolved to direct node paths, added playwright entry, updated install flow)
**Created**: 2025-12-26
**Updated**: 2026-02-20
**Location**: Claude Family/MCP Registry.md
