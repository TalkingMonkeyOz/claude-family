# Messaging — SQL Reference

## Common Queries

```sql
-- Unread messages for project
SELECT
    message_id::text, from_session_id::text,
    message_type, subject, body, priority, created_at
FROM claude.messages
WHERE to_project = 'claude-family'
  AND status = 'pending'
ORDER BY
    CASE priority WHEN 'urgent' THEN 1 WHEN 'normal' THEN 2 WHEN 'low' THEN 3 END,
    created_at ASC;

-- Messages sent by me
SELECT to_project, to_session_id::text, subject, status, created_at
FROM claude.messages
WHERE from_session_id = 'your-session-id'::uuid
ORDER BY created_at DESC LIMIT 20;

-- Broadcast messages (last 7 days)
SELECT subject, body, created_at
FROM claude.messages
WHERE message_type = 'broadcast'
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```
