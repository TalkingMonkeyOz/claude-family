---
projects:
- claude-family
tags:
- mcp
- tools
- knowledge
- session-facts
- quick-reference
synced: false
---

# Project Tools MCP

MCP server providing project-aware tooling for Claude Family.

---

## Overview

`project-tools` is globally deployed to ALL projects via `~/.claude/mcp.json`. It provides:
- Project context loading
- Work tracking (feedback, features, build_tasks)
- Knowledge operations with semantic search
- **Session facts** (crash-resistant fact cache)
- **Session notes** (structured note-taking for progress/decisions)

---

## Session Facts (New)

Within-session cache for important facts that might get lost in long conversations.

### When to Use

| Situation | Use Session Facts |
|-----------|-------------------|
| User gives API credentials | `store_session_fact("api_creds", "...", "credential", is_sensitive=True)` |
| Important config value mentioned | `store_session_fact("db_name", "production_db", "config")` |
| Key decision made | `store_session_fact("auth_approach", "JWT with refresh tokens", "decision")` |
| Need to recall something | `recall_session_fact("api_creds")` |
| After crash, need recovery | `recall_previous_session_facts(n_sessions=3)` |

### Tools

| Tool | Purpose |
|------|---------|
| `store_session_fact` | Cache a fact with key/value/type |
| `recall_session_fact` | Get specific fact by key |
| `list_session_facts` | Show all session facts |
| `recall_previous_session_facts` | Crash recovery from previous sessions |

### Fact Types

Valid `fact_type` values: `credential`, `config`, `endpoint`, `decision`, `note`, `data`, `reference`

### Example

```python
# Store
store_session_fact(
    fact_key="nimbus_api",
    fact_value="endpoint=https://api.foo.com user=john key=abc123",
    fact_type="credential",
    is_sensitive=True
)

# Recall later
recall_session_fact("nimbus_api")

# After crash - recover from last 3 sessions
recall_previous_session_facts(n_sessions=3, fact_types=["credential", "config"])
```

---

## Session Notes

Structured note-taking for tracking progress during sessions. Persists to markdown file.

### When to Use

| Situation | Use Session Notes |
|-----------|-------------------|
| Recording progress on complex task | `store_session_notes("Completed auth flow", section="progress")` |
| Key decision made | `store_session_notes("Using JWT not sessions", section="decisions")` |
| Hit a blocker | `store_session_notes("Need API key from user", section="blockers")` |
| Important finding | `store_session_notes("Found legacy code in lib/", section="findings")` |

### Tools

| Tool | Purpose |
|------|---------|
| `store_session_notes` | Add note to a section (decisions, progress, blockers, findings) |
| `get_session_notes` | Retrieve notes (optionally by section) |

### Storage

Notes stored in: `~/.claude/session_notes/{project_name}.md`

---

## Knowledge Tools

Semantic search over learned knowledge.

| Tool | Purpose |
|------|---------|
| `store_knowledge` | Store with auto-embedding (Voyage AI) |
| `recall_knowledge` | Semantic search by query |
| `link_knowledge` | Create typed relations |
| `get_related_knowledge` | Traverse knowledge graph |
| `mark_knowledge_applied` | Track success/failure |

---

## Work Tracking Tools

| Tool | Purpose |
|------|---------|
| `create_feedback` | Create bug/idea/question (validates via column_registry) |
| `create_feature` | Create feature with plan_data |
| `add_build_task` | Add task to a feature |
| `get_ready_tasks` | Get unblocked tasks |
| `update_work_status` | Update status of any work item |

---

## Project Context Tools

| Tool | Purpose |
|------|---------|
| `get_project_context` | Load CLAUDE.md equivalent, settings, tech stack, active work |
| `get_incomplete_todos` | Get pending/in_progress todos |
| `restore_session_todos` | Load past session's todos for TodoWrite |
| `todos_to_build_tasks` | Convert session todos to persistent build_tasks |
| `find_skill` | Search skill_content by task keywords |

---

## Database Tables Used

| Table | Purpose |
|-------|---------|
| `claude.session_facts` | Session fact cache |
| `claude.knowledge` | Long-term knowledge with embeddings |
| `claude.knowledge_relations` | Knowledge graph relations |
| `claude.feedback` | Bugs, ideas, questions |
| `claude.features` | Feature tracking |
| `claude.build_tasks` | Tasks linked to features |
| `claude.todos` | Session-level todos |

---

## Configuration

**Global**: `~/.claude/mcp.json`
```json
"project-tools": {
  "type": "stdio",
  "command": "C:/venvs/mcp/Scripts/python.exe",
  "args": ["C:/Projects/claude-family/mcp-servers/project-tools/server.py"],
  "env": {
    "DATABASE_URI": "postgresql://...",
    "VOYAGE_API_KEY": "${VOYAGE_API_KEY}"
  }
}
```

**Per-project-type**: `claude.project_type_configs.default_mcp_servers`
- All 15 project types include `project-tools`

---

## Session Facts vs Notes vs Knowledge vs Todos

| Need | Use This |
|------|----------|
| Important fact during session (API creds, config) | `session_facts` |
| Progress tracking, decisions, blockers | `session_notes` |
| Learned pattern/gotcha for future sessions | `knowledge` |
| Task to do right now | TodoWrite |
| Task for later, linked to feature | `build_tasks` |

---

## Related

- [[RAG Usage Guide]] - How knowledge recall integrates with RAG
- [[Claude Hooks]] - Hooks that use project-tools
- [[Family Rules]] - When to use project-tools vs raw SQL

---

**Version**: 1.1
**Created**: 2026-01-23
**Updated**: 2026-01-23
**Location**: knowledge-vault/Claude Family/Project Tools MCP.md
