---
projects:
- claude-family
tags:
- session
- architecture
- quick-reference
synced: false
---

# Session Architecture

Human-friendly overview of how Claude sessions work, including database-driven config sync.

---

## The Big Picture

```
Session Start → Config Sync → Identity → Load State → Work → Session End → Save All
```

**Goal**: Never lose context. Always know who did what, when, and why.

---

## Core Components

| Component | Purpose | Table |
|-----------|---------|-------|
| Session logging | Track all Claude work | `sessions` |
| State persistence | Save todos, focus, next steps | `session_state` |
| Identity resolution | Determine "which Claude" | `identities` |
| Agent tracking | Log spawned agents | `agent_sessions` |
| MCP usage | Track tool calls | `mcp_usage` |
| Config sync | Auto-regenerate settings from DB | `project_type_configs`, `workspaces` |

---

## Session Lifecycle

### 1. Session Start

1. SessionStart hook → `session_startup_hook.py`
2. **Config sync**: `generate_project_settings.py` regenerates `.claude/settings.local.json` from database
3. Determine project name (from cwd)
4. Resolve identity (currently hardcoded)
5. Create session record in `claude.sessions`
6. Load saved state from `claude.session_state`
7. Check messages from other Claudes
8. Return context to Claude

**Config Sync**: Self-healing. Settings regenerate from database every session. See [[Config Management SOP]]

### 2. During Session

- TodoWrite updates tracked (saved at end)
- Agent spawns logged to `agent_sessions`
- MCP calls should log to `mcp_usage` (broken)
- Hooks fire per configuration

### 3. Session End

1. Run `/session-end`
2. Generate summary, extract tasks/learnings
3. Update session record (`session_end`, `summary`, `tasks_completed`)
4. Save state to `session_state` (todo list, focus, next steps)
5. Capture knowledge to memory graph

---

## Database Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `sessions` | All Claude sessions | session_id, identity_id, project_name, session_start/end |
| `session_state` | Per-project state | project_name (PK), todo_list, current_focus, next_steps |
| `identities` | Claude instances | identity_id, identity_name, platform |
| `projects` | Project registry | project_id, project_name, phase, status |
| `workspaces` | Project paths + config | workspace_id, path, project_name, startup_config |
| `agent_sessions` | Spawned agents | session_id, agent_type, task, success, cost_usd |
| `mcp_usage` | MCP tool calls | session_id, tool_name, success, duration_ms |

**Key Relationships**:
- `sessions.identity_id` → `identities.identity_id` (FK **MISSING**)
- `sessions.project_name` → `projects.project_name` (string, not FK)
- `agent_sessions` → `sessions` (parent link **MISSING**)

---

## System Status

| Component | Status | Issue/Note |
|-----------|--------|------------|
| Session creation | ✅ Working | SessionStart hook creates records |
| State persistence | ✅ Working | Todos, focus, next steps saved |
| Agent tracking | ✅ Working | All spawns logged |
| Config sync | ✅ Working | Auto-regenerates settings from database |
| Identity resolution | ⚠️ Broken | Hardcoded, not per-project |
| FK constraints | ⚠️ Missing | No FKs on sessions→identities, agents→sessions |
| MCP usage logging | ❌ Broken | CLAUDE_SESSION_ID env var not exported |

**Data Quality**:
- 395 total sessions (39 with NULL identity, 10%)
- 144 agent spawns (all orphaned, no parent_session_id)
- 13 MCP usage records (should be thousands)

---

## Key Principles

1. **Config Syncs First** - Every session starts with database config sync (self-healing)
2. **Self-Healing** - Manual edits to `settings.local.json` get overwritten (by design)
3. **Database is Source of Truth** - Update database for permanent changes
4. **Sessions Auto-Logged** - SessionStart hook creates record automatically
5. **State Persists** - Todos and focus saved at session end
6. **Everything Tracked** - Sessions, agents, MCP calls (when working) all logged

---

## Related

- [[Session Lifecycle - Overview]] - Complete session flow
- [[Session Quick Reference]] - Quick SQL queries
- [[Database Schema - Core Tables]] - Detailed table docs
- [[Identity System - Overview]] - Identity resolution
- [[Config Management SOP]] - Database-driven config system
- [[Family Rules]] - Mandatory procedures

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/Session Architecture.md
