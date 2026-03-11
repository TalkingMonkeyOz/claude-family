---
projects:
- ato-tax-agent
synced: true
synced_at: '2025-12-20T13:15:19.768879'
tags:
- quick-reference
- claude-family
---

# Project - ATO Tax Agent

**Type**: Python Tool
**Phase**: Development
**Path**: `C:\Projects\ATO-Tax-Agent`
**Project ID**: `ato-tax-agent`

---

## Purpose

Automated Australian tax return assistance - 64 section wizard with compliance checking.

---

## MCP Configuration

| MCP | Source | Tokens |
|-----|--------|--------|
| postgres | `.mcp.json` | ~6k |
| orchestrator | `.mcp.json` | ~9k |
| mui-mcp | `~/.claude.json projects[ATO]` | ~2k |

**Total**: ~17k tokens ✅ (under 25k target)

**NOT loaded**: filesystem, memory (not needed, saves ~15k tokens)

---

## Config Files

| File | Purpose |
|------|---------|
| `.mcp.json` | postgres + orchestrator |
| `.claude/settings.local.json` | Hooks, permissions, enabled MCPs |
| `CLAUDE.md` | Project rules |

---

## Infrastructure Links

| Component | Link |
|-----------|------|
| CLAUDE.md hierarchy | [[claud.md structure]] |
| Database | [[Claude Family Postgres]] |
| Hooks | [[Claude Hooks]] |
| MCP setup | [[MCP configuration]] |
| All MCPs | [[MCP Registry]] |

---

## Agents Available

Via [[Orchestrator MCP]]:

| Agent | Use Case |
|-------|----------|
| `ux-tax-screen-analyzer` | ATO-specific wizard analysis |
| `coder-haiku` | Feature implementation |
| `web-tester-haiku` | E2E testing with Playwright |
| `analyst-sonnet` | Documentation, specs |

---

## Project-Specific

- 64 tax sections (commercial scalability)
- IndexedDB for client-sensitive data (privacy-first)
- MUI X Pro components
- Next.js 14+ frontend (planned)

See also: [[Purpose]], [[MCP Registry]], [[Orchestrator MCP]]
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: Claude Family/Project - ATO-tax-agent.md