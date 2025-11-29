---
description: Check messages from other Claude instances
---

# Inbox Check

Check for messages from other Claude Family members.

## Step 1: Query Messages

Use the orchestrator MCP:

```
mcp__orchestrator__check_inbox(
  project_name="<current-project>",
  include_broadcasts=true
)
```

## Step 2: Display Messages

Format output by priority and type:

```
📬 Inbox for [Project Name]

🔴 URGENT
  [message_type] from [sender]: [subject]
  [body preview...]

📨 NORMAL
  [message_type] from [sender]: [subject]
  [body preview...]

📭 No pending messages (if empty)
```

## Message Types

| Type | Description |
|------|-------------|
| task_request | Another Claude needs help |
| status_update | Progress notification |
| question | Clarification needed |
| notification | FYI message |
| handoff | Task transfer |
| broadcast | Message to all Claudes |

## Step 3: Acknowledge (Optional)

For important messages, mark as read:

```
mcp__orchestrator__acknowledge(
  message_id="<uuid>",
  action="read"
)
```

Or reply:

```
mcp__orchestrator__reply_to(
  original_message_id="<uuid>",
  body="Your response here"
)
```
