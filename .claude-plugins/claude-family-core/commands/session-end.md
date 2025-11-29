---
description: End the current Claude Family session with summary logging
---

# Session End

Execute the following steps to properly close your session:

## Step 1: Find Active Session

```sql
SELECT session_id, session_start, project_name
FROM claude_family.session_history
WHERE identity_id = '<your-identity-uuid>'
  AND session_end IS NULL
ORDER BY session_start DESC
LIMIT 1;
```

## Step 2: Gather Session Summary

Ask the user or generate from context:

**Template:**
```
What was accomplished:
-

Key decisions made:
-

Issues encountered:
-

Next steps:
-
```

## Step 3: Update Session Record

```sql
UPDATE claude_family.session_history
SET
  session_end = NOW(),
  session_summary = '<full-summary>',
  tasks_completed = ARRAY['task1', 'task2'],
  learnings_gained = ARRAY['learning1'],
  challenges_encountered = ARRAY['challenge1']
WHERE session_id = '<session-id>';
```

## Step 4: Log Significant Learnings (Optional)

If major patterns or solutions were discovered:

```sql
INSERT INTO claude_family.shared_knowledge
(knowledge_type, title, content, source_project, source_session_id)
VALUES ('pattern', '<title>', '<description>', '<project>', '<session-id>');
```

## Output

```
✅ Session Ended
Duration: [X] minutes
Summary logged to database

Key accomplishments:
- [list]

See you next time!
```
