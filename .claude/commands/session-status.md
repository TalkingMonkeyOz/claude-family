**QUICK SESSION RESUME - Context at a Glance**

Get instant visibility into project state without starting a new session.

**Purpose**: Quick status view only - NO database writes, NO session logging

---

## When to Use This

- Quick check on project status
- See what's pending before deciding to work
- Review context before starting full session
- Check messages and todos between sessions

**For full session start with logging**: Use `/session-start` instead

---

## What This Shows

1. **Last Session Summary** - What was done previously
2. **Active Todos** - What's pending from database
3. **Pending Messages** - Messages requiring action
4. **Uncommitted Files** - Git status count

---

## Step 1: Get Last Session Summary

```sql
-- Get most recent session for this project
SELECT
    session_id::text,
    session_start,
    session_end,
    session_summary,
    tasks_completed,
    session_metadata
FROM claude.sessions
WHERE project_name = 'your-project-name'
ORDER BY session_start DESC
LIMIT 1;
```

Display:
```
📅 LAST SESSION:
   Date: [session_start]
   Duration: [X hours]
   Summary: [session_summary]

   Completed:
   - [task 1]
   - [task 2]
```

---

## Step 2: Get Active Todos from Database

```sql
-- Get project ID
SELECT project_id FROM claude.projects WHERE project_name = 'your-project-name';

-- Get active todos
SELECT
    todo_id::text,
    content,
    active_form,
    status,
    priority,
    created_at,
    source_message_id::text
FROM claude.todos
WHERE project_id = 'project-uuid'
  AND is_deleted = false
  AND status IN ('pending', 'in_progress')
ORDER BY
    CASE status
        WHEN 'in_progress' THEN 1
        WHEN 'pending' THEN 2
    END,
    priority ASC,
    created_at ASC;
```

Display:
```
📋 ACTIVE TODOS:

🔄 IN PROGRESS ([count]):
  - [P1] Content here
  - [P2] Content here

📌 PENDING ([count]):
  - [P1] Content here
  - [P3] Content here (from message ✉️)

Total: [X] active todos
```

---

## Step 3: Check Pending Messages

```
mcp__orchestrator__check_inbox(project_name="your-project-name", include_broadcasts=true, include_read=false)
```

**Display FULL message details:**

```
📬 PENDING MESSAGES ([count]):

[For each message:]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Subject: [subject]
🏷️  Type: [message_type] | Priority: [priority]
📅 Created: [created_at]
👤 From: [from_session_id or "System"]

📄 [body content]

[If task_request/question/handoff:]
⚠️  ACTIONABLE - Requires: action/defer/response
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actionable messages: [count]
Informational messages: [count]
```

---

## Step 4: Check Uncommitted Files

```bash
git status --short | wc -l
```

Display:
```
📁 UNCOMMITTED FILES: [count]
```

---

## Step 5: Display Resume Dashboard

```
╔══════════════════════════════════════════════════════════════╗
║  SESSION RESUME - [project name]                            ║
╠══════════════════════════════════════════════════════════════╣
║  Last Session: [date] ([X hours ago])                       ║
║  Summary: [brief session summary]                            ║
╠══════════════════════════════════════════════════════════════╣
║  CURRENT STATE:                                              ║
║  📬 Messages: [count] pending ([actionable] actionable)      ║
║  📋 Todos: [in_progress] active, [pending] queued            ║
║  📁 Uncommitted: [count] files                               ║
╠══════════════════════════════════════════════════════════════╣
║  TOP PRIORITY:                                               ║
║  1. [Highest priority todo or message]                       ║
║  2. [Second priority todo or message]                        ║
║  3. [Third priority todo or message]                         ║
╚══════════════════════════════════════════════════════════════╝
```

If actionable messages exist:
```
⚠️ ACTION REQUIRED: [count] messages need response
Use /session-start to begin work and action these messages.
```

---

## Quick Actions Reference

**To start full session**: `/session-start`

**To work on todos**:
- View todos: `/todo list`
- Add new todo: `/todo add "content"`
- Start a todo: `/todo start <id>`
- Complete a todo: `/todo complete <id>`

**To handle messages**:
- Read message: Use check_inbox with full display
- Action message: acknowledge(message_id, action='actioned', project_id='...')
- Defer message: acknowledge(message_id, action='deferred', defer_reason='...')

---

## Notes

### 📊 Data Source
All information comes from database, NOT from files:
- Todos from `claude.todos`
- Messages from `claude.messages`
- Session history from `claude.sessions`

### 🚫 What This Doesn't Do
- Does NOT create new session record
- Does NOT log to database
- Does NOT start session timer
- Does NOT load full context

### 💡 When to Use /session-start Instead
- You're ready to work (not just checking status)
- You need full context loading
- You want session logged for tracking
- You need to action messages

---

**Version**: 2.0 (Database-driven status view)
**Updated**: 2025-12-27
**Schema**: claude.* (consolidated)
