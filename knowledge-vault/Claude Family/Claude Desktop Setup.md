---
synced: false
tags:
- claude-family
- configuration
- desktop
projects:
- claude-family
---

# Claude Desktop Setup

**Type**: Configuration Documentation
**Platform**: Claude Desktop (GUI)
**Created**: 2025-12-29
**Status**: Active

---

## Overview

Claude Desktop is the GUI member of the **Claude Family** - a coordinated team of Claude instances working together with shared knowledge persistence.

**Role**: Information & Planning Layer
**Identity UUID**: `3be37dfb-c3bb-4303-9bf1-952c7287263f`
**Platform**: `desktop`

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Claude Family Ecosystem               │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────┐    ┌──────────────────┐  │
│  │  Claude Desktop  │◄──►│   Claude Code    │  │
│  │  (GUI/Planning)  │    │  (Execution)     │  │
│  └────────┬─────────┘    └────────┬─────────┘  │
│           │                       │             │
│           │    ┌─────────────────┐│             │
│           └───►│   PostgreSQL    │◄─────────────┘
│                │ ai_company_fdn  │              │
│                └─────────────────┘              │
│                         │                       │
│                ┌────────▼────────┐              │
│                │ Knowledge Vault │              │
│                │   (Obsidian)    │              │
│                └─────────────────┘              │
└─────────────────────────────────────────────────┘
```

---

## Desktop vs Code: Division of Labor

| Capability | Desktop | Code |
|------------|---------|------|
| **Query Database** | ✅ Read-only | ✅ Read/Write |
| **Read Vault SOPs** | ✅ | ✅ |
| **Answer Questions** | ✅ Primary role | ⚠️ During work |
| **Plan Work** | ✅ Primary role | ⚠️ During implementation |
| **Write Code** | ❌ | ✅ |
| **Spawn Agents** | ❌ | ✅ |
| **Modify DB Structure** | ❌ | ✅ |
| **Run Builds/Tests** | ❌ | ✅ |
| **Create Commits** | ❌ | ✅ |
| **Session Logging** | ❌ | ✅ Mandatory |

---

## Configuration Files

### 1. CLAUDE.md Instructions

**Status**: ❌ **NOT SUPPORTED in v1.0.2339**
**Location**: `%APPDATA%\Claude\CLAUDE.md` (when supported)
**Issue**: Any CLAUDE.md file (even minimal) causes Claude Desktop to crash on startup

**Tested**: 2025-12-30
- Minimal version (~20 lines) - crashes
- Full version (~113 lines with code blocks/tables) - crashes
- No file - works fine

**Conclusion**: Desktop v1.0.2339 does not support CLAUDE.md identity files like Claude Code does. Feature may be added in future versions.

**Workaround**: Desktop uses default behavior without custom identity/instructions.

### 2. MCP Server Configuration

**Location**: `%APPDATA%\Claude\claude_desktop_config.json`

**Configured Servers**:
```json
{
  "mcpServers": {
    "postgres": {
      "command": "C:\\venvs\\mcp\\Scripts\\postgres-mcp.exe",
      "args": ["--access-mode=unrestricted"],
      "env": {
        "DATABASE_URI": "postgresql://postgres:***@localhost/ai_company_foundation"
      }
    },
    "memory": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "filesystem": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Projects\\claude-family\\knowledge-vault"
      ]
    },
    "sequential-thinking": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    }
  }
}
```

**Design Decisions**:
- ✅ **postgres**: Same DB as Code for shared state
- ✅ **memory**: Persistent context across Desktop chats
- ✅ **filesystem**: Scoped ONLY to knowledge-vault (lean)
- ✅ **sequential-thinking**: Deep analysis capability
- ❌ **orchestrator**: NOT included (Desktop can't spawn agents)
- ❌ **python-repl**: NOT included (Desktop doesn't execute code)

**Filesystem Scope**: Narrowed from 4 locations to 1 (knowledge-vault only) to keep Desktop lean and focused.

---

## Database Identity

Desktop is registered in the `claude.identities` table:

```sql
SELECT * FROM claude.identities
WHERE identity_id = '3be37dfb-c3bb-4303-9bf1-952c7287263f';
```

**Record**:
- `identity_name`: `claude-desktop`
- `platform`: `desktop`
- `role_description`: "GUI Interface - Claude Desktop app for visual work, strategy discussions, and design. Works across all projects with visual context."
- `status`: `active`

---

## Common Workflows

### 1. User Asks "What's Code Working On?"

Desktop queries:
```sql
SELECT project_name, task_description, session_start, session_end
FROM claude.sessions
WHERE platform = 'claude-code'
ORDER BY session_start DESC
LIMIT 10;
```

Responds with summary, offers to open Code if user wants to contribute.

### 2. User Asks "How Do I Add an MCP Server?"

1. Desktop reads `40-Procedures/Add MCP Server SOP.md` from vault
2. Summarizes the procedure
3. Says: "Want to implement this? Let's open Claude Code to add the configuration."

### 3. User Asks "Show Me Open Issues"

Desktop queries:
```sql
SELECT feedback_id::text, feedback_type, description, status, priority
FROM claude.feedback
WHERE status IN ('new', 'in_progress')
ORDER BY priority, created_at DESC;
```

Displays results, can read related project docs from vault.

### 4. User Asks "Explain the Family System"

1. Reads `Claude Family/Purpose.md`
2. Reads `40-Procedures/Family Rules.md`
3. Explains: Database coordination, multiple instances, shared vault
4. Shows who's in the family (queries `claude.identities`)

---

## Handoff Pattern

**Desktop → Code Handoff**:
1. Desktop provides information, answers questions, helps plan
2. When implementation needed, Desktop says: **"Ready to implement? Let's hand this off to Claude Code for execution."**
3. User opens Code with context from Desktop conversation
4. Code executes, logs session to database
5. Desktop can later query what Code did

This prevents duplication and clarifies roles.

---

## Key Differences from Code

| Aspect | Desktop | Code |
|--------|---------|------|
| **Instructions** | `%APPDATA%\Claude\CLAUDE.md` | `~/.claude/CLAUDE.md` (global) + project CLAUDE.md |
| **MCP Servers** | 4 (lean) | 6 (full featured) |
| **Filesystem Scope** | Knowledge vault only | All of C:\Projects |
| **Session Logging** | No | Yes (mandatory) |
| **Skills** | None | database-operations, work-item-routing, session-management, etc. |
| **Hooks** | None | SessionStart, compact, etc. |
| **Primary Use** | Chat, planning, questions | Code writing, execution, automation |

---

## Maintenance

### When to Update Desktop Config

1. **New MCP Server**: If a lightweight MCP adds value for planning/questions (e.g., web-search)
2. **Vault Restructure**: If knowledge-vault moves location
3. **New Database**: If switching databases (update DATABASE_URI)
4. **Role Change**: If Desktop's role evolves (update CLAUDE.md)

### When NOT to Add to Desktop

❌ Project-specific MCPs (eslint, shadcn, etc.) - Desktop works across all projects
❌ Heavy execution tools (python-repl, orchestrator) - Desktop doesn't execute
❌ Build tools - Desktop doesn't run builds

---

## Troubleshooting

### Desktop Can't Access Vault
Check: `%APPDATA%\Claude\claude_desktop_config.json` → filesystem → args → path is correct

### Desktop Doesn't Know Its Role
Check: `%APPDATA%\Claude\CLAUDE.md` exists and has content

### Desktop Tries to Execute Code
Reminder in CLAUDE.md: Desktop's role is planning, NOT execution. Handoff to Code.

### Desktop Has Stale Project Info
Desktop queries DB in real-time. If Code just worked on something, Desktop will see it in `claude.sessions` immediately.

---

## Related Documentation

**Setup & Configuration**:
- [[Purpose]] - Claude Family overview
- [[Family Rules]] - Coordination rules
- [[MCP Configuration]] - MCP server setup guide

**Workflows**:
- [[Session Lifecycle]] - How Code manages sessions (Desktop doesn't do this)
- [[Knowledge System]] - How vault knowledge works

**Reference**:
- [[Database Architecture]] - Database schema details
- [[claud.md structure]] - CLAUDE.md hierarchy

---

## Files Managed

| File | Location | Purpose |
|------|----------|---------|
| `CLAUDE.md` | `%APPDATA%\Claude\` | Desktop's instructions |
| `claude_desktop_config.json` | `%APPDATA%\Claude\` | MCP server configuration |
| `Claude Desktop Setup.md` | `knowledge-vault/Claude Family/` | This document |

---

## Version History

**v1.0** (2025-12-29):
- Initial Desktop setup
- Created CLAUDE.md with identity, role, example queries
- Optimized MCP config (narrowed filesystem to vault-only)
- Documented handoff pattern
- Registered Desktop as full Family member

---

**Maintained By**: Claude Family
**Review Frequency**: When Desktop's role changes or new capabilities are needed
**Last Updated**: 2025-12-29
