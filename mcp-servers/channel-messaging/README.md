# Channel Messaging MCP Server

Real-time inter-Claude messaging via PostgreSQL LISTEN/NOTIFY and Claude Code channels.

## How It Works

1. PostgreSQL trigger fires `pg_notify` on every INSERT to `claude.messages`
2. This MCP server listens for those notifications via `LISTEN`
3. Notifications are pushed into Claude's session via the channels API
4. Claude sees messages in real-time, not just at prompt boundaries

## Setup

### Prerequisites
- Claude Code 2.1.80+ (channels support)
- PostgreSQL with the `claude.notify_new_message` trigger installed
- Node.js 18+

### Install
```bash
cd mcp-servers/channel-messaging
npm install
```

### Add to MCP Config
Add to your project's `.mcp.json`:
```json
{
  "mcpServers": {
    "channel-messaging": {
      "command": "node",
      "args": ["C:/Projects/claude-family/mcp-servers/channel-messaging/server.js"],
      "env": {
        "PGPASSWORD": "your-password"
      }
    }
  }
}
```

### Launch with Channels
During research preview, use:
```bash
claude --dangerously-load-development-channels server:channel-messaging
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | localhost:5432/ai_company_foundation |
| `CLAUDE_PROJECT` | Project name to listen for | Auto-detected from directory name |
| `PGPASSWORD` | PostgreSQL password | (empty) |

## Testing

Send a test message from another session:
```
send_message(message_type="notification", body="Hello from the other side!", to_project="claude-family")
```

The receiving session should see it appear in real-time.

---
**Version**: 0.1
**Created**: 2026-03-24
**Updated**: 2026-03-24
**Location**: mcp-servers/channel-messaging/README.md
