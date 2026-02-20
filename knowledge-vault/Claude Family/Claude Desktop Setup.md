---
synced: false
tags:
- claude-family
- configuration
- desktop
projects:
- claude-family
- claude-desktop-config
---

# Claude Desktop Setup

**Type**: Configuration Documentation
**Platform**: Claude Desktop (GUI)
**Status**: Active

---

## Overview

Claude Desktop is the GUI member of the **Claude Family** - a coordinated team of Claude instances working together with shared knowledge persistence.

**Role**: Planning, Research, and Information Layer
**Identity UUID**: `3be37dfb-c3bb-4303-9bf1-952c7287263f`
**Platform**: `desktop`

---

## Configuration Management

Desktop config is managed from the **claude-desktop-config** project at `C:\Projects\claude-desktop-config`.

| What | Where |
|------|-------|
| Live config | `%APPDATA%\Claude\claude_desktop_config.json` |
| Live instructions | `%APPDATA%\Claude\CLAUDE.md` |
| Git-tracked copies | `C:\Projects\claude-desktop-config\reference\` |
| Deploy script | `python scripts/deploy.py` (copies reference -> live) |
| Backup script | `python scripts/backup.py` (copies live -> reference) |

**Not DB-driven.** Desktop config is manually edited and version-controlled in git. This is intentional - Desktop doesn't have hooks for auto-regeneration.

---

## MCP Server Configuration

**6 servers** configured in `claude_desktop_config.json`:

| Server | Package/Binary | Purpose |
|--------|---------------|---------|
| filesystem | `@modelcontextprotocol/server-filesystem` | File access: Desktop, Documents, Downloads, C:\Projects |
| fetch | `@modelcontextprotocol/server-fetch` | Web content fetching for research |
| memory | `@modelcontextprotocol/server-memory` | Persistent knowledge graph |
| sequential-thinking | `@modelcontextprotocol/server-sequential-thinking` | Multi-step reasoning |
| postgres | `postgres-mcp.exe` | Shared DB (ai_company_foundation, unrestricted) |
| project-tools | `server_v2.py` | Work tracking, knowledge, sessions |

**Filesystem scope**: `C:\Users\johnd\Desktop`, `Documents`, `Downloads`, `C:\Projects`

**Not included** (by design):
- orchestrator - Desktop can't spawn agents
- python-repl - Desktop doesn't execute code

---

## Desktop vs Code: Division of Labor

| Capability | Desktop | Code |
|------------|---------|------|
| Query Database | Read/write via MCP | Read/write via MCP |
| Read/Write Files | Via filesystem MCP (scoped dirs) | Native (any path) |
| Fetch Web Content | Via fetch MCP | Via WebFetch tool |
| Read Vault SOPs | Via filesystem MCP | Native |
| Plan Work | Primary role | During implementation |
| Write Code | No | Yes |
| Spawn Agents | No | Yes |
| Run Builds/Tests | No | Yes |
| Create Commits | No | Yes |
| Session Logging | Manual via project-tools | Automatic via hooks |

---

## CLAUDE.md for Desktop

**Location**: `%APPDATA%\Claude\CLAUDE.md`
**Source of truth**: `C:\Projects\claude-desktop-config\reference\CLAUDE.md`

Contains: role definition, available tools, common SQL queries, handoff instructions.

**History**: CLAUDE.md crashed Desktop v1.0.2339 (Dec 2025). Re-deployed Feb 2026 - needs restart to verify.

---

## Database Identity

Registered in `claude.identities`:
- `identity_name`: `claude-desktop`
- `platform`: `desktop`
- `status`: `active`

Project in `claude.projects`:
- `project_name`: `claude-desktop-config`
- `project_code`: `claude-desktop`
- `status`: `active`

---

## Handoff Pattern

**Desktop -> Code Handoff**:
1. Desktop provides information, answers questions, helps plan
2. When implementation needed: "This needs Claude Code to implement"
3. Optionally queue via project-tools `send_message` or `create_feedback`
4. Code executes, logs session to database
5. Desktop can later query what Code did

---

## Maintenance

### When to Update Desktop Config
1. New MCP server adds value for planning/research
2. Filesystem scope needs changing
3. Database connection changes

### Update Workflow
1. Edit `reference/` files in `C:\Projects\claude-desktop-config`
2. Run `python scripts/deploy.py`
3. Restart Claude Desktop
4. Commit changes to git

### When NOT to Add to Desktop
- Project-specific MCPs (eslint, shadcn, etc.)
- Heavy execution tools (python-repl, orchestrator)
- Build/test tools

---

## Related Documentation

- [[Purpose]] - Claude Family overview
- [[Family Rules]] - Coordination rules
- `C:\Projects\claude-desktop-config\CLAUDE.md` - Project instructions
- `docs/CLAUDE_DESKTOP_INTEGRATION_DESIGN.md` (in claude-family) - Original design doc (Dec 2025)

---

**Version**: 2.0
**Created**: 2025-12-29
**Updated**: 2026-02-18
**Location**: knowledge-vault/Claude Family/Claude Desktop Setup.md
