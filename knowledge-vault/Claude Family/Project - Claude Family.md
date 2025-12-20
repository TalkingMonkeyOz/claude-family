---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.770384'
---

# Project - Claude Family

**Type**: Infrastructure
**Phase**: Implementation
**Path**: `C:\Projects\claude-family`
**Project ID**: `20b5627c-e72c-4501-8537-95b559731b59`

---

## Purpose

Governance infrastructure for all Claude instances - shared database, hooks, commands, and agent orchestration.

---

## MCP Configuration

| MCP | Source | Tokens |
|-----|--------|--------|
| postgres | Global | ~6k |
| orchestrator | Global | ~9k |
| sequential-thinking | Global | ~2k |
| python-repl | Global | ~2k |
| filesystem | Project-specific | ~9k |
| memory | Project-specific | ~6k |

**Total**: ~34k tokens (infrastructure project, higher budget OK)

---

## Components

| Component | Location | Docs |
|-----------|----------|------|
| Database | PostgreSQL `claude.*` | [[Claude Family Postgres]] |
| Memory | Entity graph | [[Claude Family Memory Graph]] |
| Hooks | Process router | [[Claude Hooks]] |
| Commands | `.claude/commands/` | [[Slash command's]] |
| MCPs | See above | [[MCP configuration]] |
| Settings | `.claude/settings*.json` | [[Setting's File]] |
| Orchestrator | `mcp-servers/orchestrator/` | [[Orchestrator MCP]] |
| Knowledge | `knowledge-vault/` | [[MCP Registry]] |

---

## Config Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project rules, instructions |
| `.mcp.json` | Project MCP servers |
| `.claude/settings.local.json` | Hooks, permissions |
| `.claude/commands/` | 20+ slash commands |
| `.claude/skills/` | 5 skills |

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `process_router.py` | Workflow injection hook |
| `sync_obsidian_to_db.py` | Vault → DB sync |
| `install_plugin.py` | Cross-project plugin installer |
| `run_regression_tests.py` | Knowledge system tests |

---

## Skills

| Skill | Purpose |
|-------|---------|
| database-operations | Data Gateway patterns |
| testing-patterns | Test level guidance |
| feature-workflow | Feature tracking |
| doc-keeper | Documentation maintenance |
| nimbus-api | Nimbus API patterns |

---

## Scheduled Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `vault-knowledge-sync` | Daily 7am | Sync vault to DB |
| `doc-keeper-weekly` | Sunday 7am | Verify documentation |

---

See also: [[claud.md structure]], [[Purpose]], [[MCP Registry]], [[Orchestrator MCP]]