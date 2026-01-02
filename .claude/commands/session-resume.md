**QUICK SESSION RESUME - Context at a Glance**

Get instant visibility into project state from DATABASE.

**Purpose**: Quick status view only - NO database writes, NO session logging

---

## Step 1: Get Last Session Summary

```sql
-- Get most recent session for this project
SELECT
    session_id::text,
    session_start,
    session_end,
    session_summary,
    tasks_completed
FROM claude.sessions
WHERE project_name = 'claude-family'
ORDER BY session_start DESC
LIMIT 1;
```

---

## Step 2: Get Active Todos from Database

```sql
-- Get active todos
SELECT
    content,
    status,
    priority,
    created_at
FROM claude.todos
WHERE project_id = '20b5627c-e72c-4501-8537-95b559731b59'::uuid
  AND is_deleted = false
  AND status IN ('pending', 'in_progress')
ORDER BY
    CASE status
        WHEN 'in_progress' THEN 1
        WHEN 'pending' THEN 2
    END,
    priority ASC,
    created_at ASC
LIMIT 10;
```

---

## Step 3: Check Pending Messages

```
mcp__orchestrator__check_inbox(project_name="claude-family", include_broadcasts=true, include_read=false)
```

---

## Step 4: Check Uncommitted Files

```bash
git status --short | wc -l
```

---

## Display Format

```
╔══════════════════════════════════════════════════════════════╗
║  SESSION RESUME - claude-family                              ║
╠══════════════════════════════════════════════════════════════╣
║  Last Session: [date] ([X hours ago])                       ║
║  Summary: [brief session summary]                            ║
╠══════════════════════════════════════════════════════════════╣
║  CURRENT STATE:                                              ║
║  📬 Messages: [count] pending                                ║
║  📋 Todos: [in_progress] active, [pending] queued            ║
║  📁 Uncommitted: [count] files                               ║
╠══════════════════════════════════════════════════════════════╣
║  TOP PRIORITY TODOS:                                         ║
║  1. [First todo]                                             ║
║  2. [Second todo]                                            ║
║  3. [Third todo]                                             ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Data Source

ALL information comes from DATABASE, NOT files:
- Todos from `claude.todos`
- Messages from `claude.messages`
- Session history from `claude.sessions`

---

**Version**: 3.0 (Database-only, no file reading)
**Updated**: 2026-01-02
