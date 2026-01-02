---
projects:
  - claude-family
tags:
  - session
  - todos
  - handoff
  - database
synced: false
---

# Session Handoff - Database Approach

**Problem Solved**: Session handoff was broken due to disconnected data sources (files vs database vs session_state)

**Solution**: Database-first approach using `claude.todos` as single source of truth

---

## Architecture

```
TodoWrite → claude.todos (DATABASE)
           ↓
SessionStart → Loads from claude.todos
SessionResume → Queries claude.todos
SessionEnd → Updates claude.sessions
```

**No .md files** - Database is the ONLY source of truth

---

## How It Works

### During Session

**TodoWrite tool**:
- Writes directly to `claude.todos` table
- Sets `project_id`, `created_session_id`
- Updates `status` (pending → in_progress → completed)
- Soft deletes with `is_deleted = true`

### Session Start

**SessionStart hook** (`scripts/session_startup_hook_enhanced.py`):
1. Creates session record in `claude.sessions`
2. Queries `claude.todos` for pending/in_progress items
3. Displays active todos grouped by status
4. Loads `session_state` for current_focus, pending_actions
5. Checks for pending messages

**Output**:
```
=== WHERE WE LEFT OFF ===
Focus: [current_focus from session_state]

Active Todos: 5 total (2 in progress, 3 pending)

In Progress:
  [>] [P3] Fix orchestrator bug
  [>] [P3] Update documentation

Pending (top 5):
  [ ] [P3] Test session lifecycle
  [ ] [P3] Commit changes
  [ ] [P3] Update vault docs
```

### Session Resume

**Command**: `/session-resume` (`.claude/commands/session-resume.md`)

Queries:
1. Last session from `claude.sessions`
2. Active todos from `claude.todos`
3. Pending messages from `claude.messages`
4. Uncommitted files from git

**NO file reading** - Pure database queries

### Session End

**Command**: `/session-end`

Updates:
1. `claude.sessions` - Sets session_end, summary, tasks_completed
2. `claude.session_state` - Updates current_focus, pending_actions
3. Memory graph - Captures knowledge (optional)

**Does NOT**:
- Write TODO files
- Update session_state.todo_list (deprecated column)

---

## Database Schema

### claude.todos (Source of Truth)

```sql
CREATE TABLE claude.todos (
  todo_id UUID PRIMARY KEY,
  project_id UUID REFERENCES claude.projects,
  created_session_id UUID REFERENCES claude.sessions,
  completed_session_id UUID REFERENCES claude.sessions,
  content TEXT NOT NULL,
  active_form TEXT NOT NULL,
  status VARCHAR NOT NULL,  -- pending, in_progress, completed
  priority INTEGER DEFAULT 3,
  display_order INTEGER DEFAULT 0,
  is_deleted BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ,
  source_message_id UUID
);
```

### claude.session_state (Supporting Data)

```sql
CREATE TABLE claude.session_state (
  project_name TEXT PRIMARY KEY,
  current_focus TEXT,           -- What you're working on
  pending_actions TEXT[],        -- Things that need follow-up
  files_modified TEXT[],         -- Files touched
  todo_list JSONB,               -- DEPRECATED - use claude.todos instead
  updated_at TIMESTAMPTZ
);
```

---

## Migration from File-Based

**Old approach** (BROKEN):
- TodoWrite → session_state.todo_list (JSONB)
- SessionEnd → Writes TODO_NEXT_SESSION.md file
- SessionResume → Reads TODO_NEXT_SESSION.md file
- Result: Files get stale, disconnected from database

**New approach** (WORKING):
- TodoWrite → claude.todos table
- SessionStart → Loads from claude.todos
- SessionResume → Queries claude.todos
- Result: Database is always current, no file maintenance

**Deprecated**:
- `docs/TODO_NEXT_SESSION.md` - Deleted
- `session_state.todo_list` - Column exists but not used

---

## Benefits

1. **Single source of truth** - Database only
2. **Always current** - No stale files
3. **Cross-session** - Todos persist automatically
4. **Queryable** - Can filter, sort, analyze todos
5. **Trackable** - Can see which session created/completed each todo
6. **No maintenance** - No manual file updates needed

---

## Troubleshooting

### Todos not loading at session start

Check:
1. SessionStart hook configured in `.claude/hooks.json`
2. Hook script at `scripts/session_startup_hook_enhanced.py`
3. Database connection working (psycopg installed)
4. Project exists in `claude.projects` table

### Todos not persisting

Check:
1. TodoWrite is actually writing to database (query `claude.todos`)
2. `is_deleted = false`
3. `status IN ('pending', 'in_progress')`
4. Correct `project_id`

### Duplicates accumulating

Solution:
```sql
-- Archive stale todos
UPDATE claude.todos
SET is_deleted = true, deleted_at = NOW()
WHERE project_id = 'YOUR-PROJECT-ID'::uuid
  AND created_at < NOW() - INTERVAL '30 days'
  AND status = 'pending';
```

---

## Related Documents

- [[Session Lifecycle - Overview]]
- [[Session Lifecycle - Session Start]]
- [[Session Lifecycle - Session End]]
- [[Database Schema - Core Tables]]

---

**Version**: 1.0
**Created**: 2026-01-02
**Updated**: 2026-01-02
**Location**: knowledge-vault/40-Procedures/Session Handoff - Database Approach.md
