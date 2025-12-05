---
description: View active Claude Family members and their current work
---

# Team Status

Show all active Claude instances and their current sessions.

## Step 1: Query Active Sessions

```sql
SELECT
  i.identity_name,
  sh.project_name,
  sh.session_start,
  EXTRACT(EPOCH FROM (NOW() - sh.session_start))/60 as minutes_active,
  sh.session_summary as current_task
FROM claude.sessions sh
JOIN claude.identities i ON sh.identity_id = i.identity_id
WHERE sh.session_end IS NULL
ORDER BY sh.session_start DESC;
```

## Step 2: Query Orchestrator

```
mcp__orchestrator__get_active_sessions()
```

## Step 3: Display Team Dashboard

```
👥 Claude Family Status

ACTIVE NOW:
┌─────────────────┬─────────────────┬──────────┬─────────────────────┐
│ Identity        │ Project         │ Duration │ Current Task        │
├─────────────────┼─────────────────┼──────────┼─────────────────────┤
│ claude-unified  │ mission-control │ 45 min   │ Building dashboard  │
│ claude-desktop  │ nimbus          │ 12 min   │ Session started     │
└─────────────────┴─────────────────┴──────────┴─────────────────────┘

RECENT SESSIONS (Last 24h):
- claude-unified: 3 sessions, 4.2 hours total
- claude-desktop: 1 session, 0.5 hours

📊 Family Statistics:
- Active instances: 2
- Total sessions today: 4
- Messages pending: 1
```

## Step 4: Optional Actions

- `/inbox-check` - Check messages
- `/broadcast` - Send message to all
