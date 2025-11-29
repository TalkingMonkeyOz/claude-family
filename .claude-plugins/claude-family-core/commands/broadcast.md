---
description: Send a message to all Claude Family members
---

# Broadcast Message

Send a message to ALL active Claude instances.

## Step 1: Gather Message Details

Prompt the user for:
- **Subject**: Brief title (optional but recommended)
- **Body**: Message content (required)
- **Priority**: urgent, normal, or low (default: normal)

## Step 2: Send Broadcast

```
mcp__orchestrator__broadcast(
  body="<message-body>",
  subject="<subject>",
  priority="<priority>",
  from_session_id="<your-session-id>"
)
```

## Step 3: Confirm

```
📢 Broadcast Sent

Subject: [subject]
Priority: [priority]
Message ID: [uuid]

All active Claude instances will see this message.
```

## Priority Guidelines

| Priority | Use When |
|----------|----------|
| urgent | Blocking issue, immediate attention needed |
| normal | General updates, coordination |
| low | FYI, non-time-sensitive |

## Example Messages

**Coordination:**
```
Subject: Starting database migration
Body: About to run migration on ai_company_foundation. Please avoid DB writes for next 5 minutes.
Priority: urgent
```

**Status update:**
```
Subject: New MCP server available
Body: Installed new shadcn MCP server. Available for web projects.
Priority: normal
```
