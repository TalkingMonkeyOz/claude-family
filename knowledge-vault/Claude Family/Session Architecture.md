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

How Claude sessions work end-to-end, including all hooks, database tables, and built-in features.

---

## The Big Picture

```
SessionStart Hook → Load State → Work → PreCompact Hook → SessionEnd Hook
     (auto)          (auto)              (if compaction)     (auto-close)
                                              ↓
                                    /session-end (manual)
                                    Full summary + knowledge
```

**Goal**: Never lose context. Always know who did what, when, and why.

---

## Hook Chain (Complete)

| Order | Hook Event | Script | What It Does |
|-------|-----------|--------|--------------|
| 1 | **SessionStart** | `session_startup_hook_enhanced.py` | Log session, load state, health check |
| 2 | **UserPromptSubmit** | `rag_query_hook.py` | RAG context + core protocol + periodic reminders |
| 3 | **PreToolUse** (Write/Edit) | `context_injector_hook.py` | Inject coding standards from context_rules |
| 3b | **PreToolUse** (Write/Edit) | `standards_validator.py` | Validate content against standards |
| 4 | **PostToolUse** (TodoWrite) | `todo_sync_hook.py` | Sync todos to claude.todos |
| 5 | **PostToolUse** (all) | `mcp_usage_logger.py` | Log MCP tool usage (filters to mcp__ prefix) |
| 6 | **SubagentStart** | `subagent_start_hook.py` | Log agent spawns to agent_sessions |
| 7 | **PreCompact** | `precompact_hook.py` | Inject active work items before compaction |
| 8 | **SessionEnd** | `session_end_hook.py` | Auto-close session in database |

**Key design**: MCP usage logger uses a catch-all matcher (no matcher = fires for ALL PostToolUse). The script internally filters to `tool_name.startswith('mcp__')`.

---

## Database Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `claude.sessions` | All sessions | session_id, identity_id, project_name, session_start/end, session_summary |
| `claude.session_state` | Per-project state | project_name (PK), current_focus, next_steps |
| `claude.todos` | Persistent todos | project_id, content, status, priority |
| `claude.session_facts` | Crash-recoverable facts | session_id, fact_key, fact_value, fact_type |
| `claude.identities` | Claude instances | identity_id, identity_name, platform |
| `claude.agent_sessions` | Spawned agents | session_id, agent_type, task_description |
| `claude.mcp_usage` | MCP tool calls | mcp_server, tool_name, session_id, success |

**FK Constraints**:
- `sessions.identity_id` → `identities.identity_id` (exists)
- `agent_sessions.parent_session_id` → `sessions.session_id` (exists)

---

## Built-in Claude Code Features (No Custom Code Needed)

| Feature | What | Command |
|---------|------|---------|
| Resume session | Full conversation history restored | `claude --resume` |
| Continue last | Pick up most recent session | `claude --continue` |
| Session naming | Name sessions for easy resume | `/rename my-feature` |
| Context compression | Summarize conversation | `/compact` (instant) |
| Task persistence | Tasks survive compaction | Built-in TaskList |
| Auto memory | Persistent patterns across sessions | `MEMORY.md` (200 lines loaded) |
| Session export | Save conversation to file | `/export` |
| Session stats | Usage, streaks, tokens | `/stats` |

---

## Our Custom Enhancements (Beyond Built-in)

| Enhancement | Why We Need It |
|-------------|----------------|
| DB session tracking | Cross-instance visibility, queryable history |
| Todo sync to DB | Persistence beyond local session, cross-project visibility |
| RAG on every prompt | Auto-inject relevant vault + knowledge context |
| PreCompact state injection | Preserve active work items across compaction |
| Auto session close | Prevent orphaned unclosed sessions |
| MCP usage logging | Analytics on tool usage patterns |
| Session facts | Crash recovery for credentials, decisions |
| Inter-Claude messaging | Multi-agent coordination |

---

## Configuration (Database-Driven)

```
config_templates (hooks-base) → generate_project_settings.py → settings.local.json
     ↑                                                               ↓
project_type_configs (defaults)                              Claude Code reads this
     ↑
workspaces.startup_config (overrides)
```

**Self-healing**: Settings regenerate from DB on every `generate_project_settings.py` run.
**Central deployment**: Same script works for all projects.

---

## System Status

| Component | Status | Note |
|-----------|--------|------|
| Session creation | Working | SessionStart hook creates records |
| State persistence | Working | Todos, focus, next steps saved |
| Agent tracking | Working | All spawns logged with FK |
| Config sync | Working | Self-healing from database |
| MCP usage logging | Working | Catch-all matcher, 3,500+ records |
| PreCompact hook | Working | Injects session state from DB |
| SessionEnd auto-close | Working | Command hook auto-closes sessions |
| Identity resolution | Hardcoded | Uses default identity |

---

## Related

- [[Config Management SOP]] - Database-driven config system
- [[Family Rules]] - Mandatory procedures
- [[Claude Hooks]] - Hook system details

---

**Version**: 3.0 (Full rewrite - accurate to 2026-02-07 system state)
**Created**: 2025-12-26
**Updated**: 2026-02-07
**Location**: Claude Family/Session Architecture.md
