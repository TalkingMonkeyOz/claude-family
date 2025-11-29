---
description: Start a new Claude Family session with full context loading
---

# Session Start

Execute the following steps to initialize your session:

## Step 1: Identify Yourself

Detect your identity from the environment or working directory. Common identities:
- claude-code-unified (ID: ff32276f-9d05-4a18-b092-31b54c82fff9)
- claude-desktop (ID: 3be37dfb-c3bb-4303-9bf1-952c7287263f)

## Step 2: Detect Project

Determine the current project from the working directory. Check `workspaces.json` or query:

```sql
SELECT project_name, project_path FROM claude_family.project_workspaces;
```

## Step 3: Log Session Start

```sql
INSERT INTO claude_family.session_history
(identity_id, session_start, project_name, session_summary)
VALUES ('<identity-uuid>', NOW(), '<project-name>', 'Session started')
RETURNING session_id;
```

Save the session_id for session-end.

## Step 4: Load Recent Context

```sql
SELECT session_summary, project_name, session_start
FROM claude_family.session_history
WHERE project_name = '<current-project>'
ORDER BY session_start DESC
LIMIT 5;
```

## Step 5: Check Messages

```
mcp__orchestrator__check_inbox(
  project_name="<current-project>",
  include_broadcasts=true
)
```

Display any pending messages to the user.

## Step 6: Check Feedback (if applicable)

```sql
SELECT feedback_type, COUNT(*) as count
FROM claude_pm.project_feedback
WHERE project_id = '<project-uuid>'
  AND status IN ('new', 'in_progress')
GROUP BY feedback_type;
```

## Output

Display a summary:
```
✅ Session Started
Identity: [name]
Project: [name]
Session ID: [uuid]

Recent Context: [last session summary]
Messages: [count] pending
Feedback: [count] open items
```
