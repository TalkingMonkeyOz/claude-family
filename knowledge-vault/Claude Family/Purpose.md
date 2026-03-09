---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T23:29:45.932135'
tags:
- quick-reference
- claude-family
---

# Claude Family Vault

The Claude Family manages coordination across multiple Claude instances with shared knowledge persistence.

---

## Core System Components

| Component | Documentation |
|-----------|---------------|
| CLAUDE.md hierarchy | [[claud.md structure]] |
| Database | [[Claude Family Postgres]], [[Database Architecture]] |
| Session Architecture | [[Session Architecture]] - How sessions work |
| Knowledge System | [[Knowledge System]] |
| Session Workflows | [[Claude Family todo Session Start]], [[session End]] |
| MCP Servers | [[MCP configuration]], [[MCP Registry]], [[Orchestrator MCP]] |
| Claude Desktop | [[Claude Desktop Setup]] - GUI interface setup |
| Plugins | [[Plugins]] |
| Hooks | [[Claude Hooks]] |
| Commands | [[Slash command's]] |
| Settings | [[Setting's File]] |
| Observability | [[Observability]] |
| Documentation System | [[Auto-Apply Instructions]], [[Documentation Philosophy]] |

---

## Vault Structure

| Folder | Purpose |
|--------|---------|
| `00-Inbox/` | Quick capture (unsorted) |
| `10-Projects/` | Project-specific knowledge |
| `20-Domains/` | Domain expertise (APIs, Database) |
| `30-Patterns/` | Gotchas, solutions |
| `40-Procedures/` | SOPs, [[Family Rules]], [[Documentation Standards]] |
| `Claude Family/` | Core system docs (this folder) |

---

## Key Procedures

- [[Family Rules]] - Coordination rules (MANDATORY)
- [[Documentation Standards]] - How to write vault docs
- [[Knowledge Capture SOP]] - How to capture knowledge

---

## Current Projects

- [[Project - Claude Family]] - Infrastructure (`infrastructure` domain)
- [[Project - ATO-tax-agent]] - Tax agent (`ato` domain)
- [[Project - Mission Control Web]] - Dashboard UI (`claude-tools` domain)
- [[Project - Metis]] - Next-generation platform (`infrastructure` domain)
- [[Project - Trading Intelligence]] - Finance intelligence system (`finance` domain)

---

**Version**: 2.3
**Created**: 2025-12-20
**Updated**: 2026-03-09
**Location**: knowledge-vault/Claude Family/Purpose.md
**Changelog**:
- 2.3: Added Project-Metis and Trading Intelligence to current projects list
- 2.2: Added [[Claude Desktop Setup]] documentation; integrated Desktop as full Family member