---
projects:
- claude-family
tags:
- architecture
- reference
- hooks
- database
synced: false
---

# Claude Family System Architecture

**Purpose**: Detailed architecture showing data flows, hooks, and active systems.
**Quick reference**: See `docs/HOW_I_WORK.md`

---

## Hook Data Flows

### SessionStart Hook

```
User launches Claude Code
    ↓
session_startup_hook.py fires
    ↓
├─ INSERT claude.sessions (session_id, project_name)
├─ SELECT claude.session_state (focus, next_steps)
├─ SELECT claude.todos (pending, in_progress)
├─ SELECT claude.messages (pending)
└─ Auto-complete obvious todos
    ↓
Context injected, env vars set (SESSION_ID, PROJECT_ID)
```

### UserPromptSubmit Hook (RAG)

```
User types message
    ↓
rag_query_hook.py fires
    ↓
├─ Generate embedding (Voyage AI)
├─ SELECT vault_embeddings WHERE embedding <=> query
├─ INSERT rag_usage_log
├─ If session keywords → inject session context
└─ Track implicit feedback
    ↓
Relevant docs injected (silent)
```

### TodoWrite Sync Hook

```
Claude calls TodoWrite([...])
    ↓
todo_sync_hook.py fires
    ↓
├─ Parse tool output
├─ UPSERT claude.todos
└─ Maintain display_order
    ↓
Database reflects todo state
```

---

## Database Schema (Key Tables)

### claude.sessions
```sql
session_id UUID PRIMARY KEY
identity_id UUID
project_name VARCHAR
session_start TIMESTAMP
session_end TIMESTAMP
session_summary TEXT
tasks_completed TEXT[]
learnings_gained TEXT[]
```

### claude.todos
```sql
todo_id UUID PRIMARY KEY
project_id UUID REFERENCES projects
content TEXT
active_form TEXT
status VARCHAR (pending|in_progress|completed|cancelled)
priority INTEGER (1-5)
display_order INTEGER
is_deleted BOOLEAN
```

### claude.vault_embeddings
```sql
embedding_id UUID PRIMARY KEY
doc_path VARCHAR
doc_title VARCHAR
chunk_text TEXT
embedding VECTOR(1024)
doc_source VARCHAR (vault|project)
```

---

## File Locations

| Location | Purpose |
|----------|---------|
| `~/.claude/commands/` | Global commands (all projects) |
| `~/.claude/hooks.log` | Hook execution logs |
| `.claude/settings.local.json` | Generated config (from DB) |
| `scripts/rag_query_hook.py` | RAG hook |
| `scripts/todo_sync_hook.py` | Todo sync |
| `.claude-plugins/.../session_startup_hook.py` | Session start |

---

## Dead Code Inventory

| Item | Last Used | Reason Unused |
|------|-----------|---------------|
| `scheduled_jobs` | Dec 13 | No automation triggers |
| `process_registry` | Never | Replaced by skills |
| `reminders` | Never | No hook checks |
| `session_state.todo_list` | Deprecated | Use `claude.todos` |

---

## Verification Queries

```sql
-- Recent sessions
SELECT session_start, session_summary
FROM claude.sessions WHERE project_name = 'claude-family'
ORDER BY session_start DESC LIMIT 3;

-- Active todos
SELECT content, status, priority FROM claude.todos t
JOIN claude.projects p ON t.project_id = p.project_id
WHERE p.project_name = 'claude-family'
  AND status IN ('pending', 'in_progress');

-- RAG working?
SELECT query_text, results_count, latency_ms
FROM claude.rag_usage_log ORDER BY created_at DESC LIMIT 5;
```

---

See also: [[Session Quick Reference]], [[Slash command's]], [[Claude Hooks]]

---

**Version**: 1.0
**Created**: 2026-01-07
**Updated**: 2026-01-07
**Location**: knowledge-vault/Claude Family/System Architecture.md
