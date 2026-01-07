# How Claude Code Works - Quick Reference

**Purpose**: Quick overview of what's working in this project.
**Detailed docs**: See `knowledge-vault/Claude Family/System Architecture.md`

---

## Active Hooks

| Hook | Script | What It Does |
|------|--------|--------------|
| SessionStart | `session_startup_hook.py` | Creates session, loads todos/state |
| UserPromptSubmit | `rag_query_hook.py` | RAG + session context injection |
| PostToolUse/TodoWrite | `todo_sync_hook.py` | Syncs todos to database |
| PreToolUse/Write\|Edit | `standards_validator.py` | Validates coding standards |

## Active MCP Servers

`postgres`, `orchestrator`, `memory`, `sequential-thinking`, `vault-rag`

## Key Database Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `sessions` | Session history | 495 |
| `todos` | Todo tracking | 680 |
| `vault_embeddings` | RAG chunks | 8,450 |
| `rag_usage_log` | RAG metrics | 322 |

## Dead Code (Can Remove)

- `scheduled_jobs` - Last ran Dec 13, no automation
- `process_registry` - Replaced by skills (ADR-005)

## Commands

| Command | Purpose |
|---------|---------|
| `/session-resume` | Database-driven context |
| `/session-end` | Save summary |

---

**Version**: 1.0
**Created**: 2026-01-07
**Location**: docs/HOW_I_WORK.md
