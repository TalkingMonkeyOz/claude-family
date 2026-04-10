# Messaging Protocol Research

Research findings for the Claude Family inter-Claude messaging system.

---

## 1. Database Schema — `claude.messages`

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `message_id` | uuid | NO | `gen_random_uuid()` |
| `from_session_id` | uuid | YES | — |
| `to_session_id` | uuid | YES | — |
| `to_project` | varchar | YES | — |
| `message_type` | varchar | YES | — |
| `priority` | varchar | YES | — |
| `subject` | varchar | YES | — |
| `body` | text | YES | — |
| `metadata` | jsonb | YES | — |
| `status` | varchar | YES | `'pending'` |
| `read_at` | timestamp | YES | — |
| `acknowledged_at` | timestamp | YES | — |
| `created_at` | timestamp | YES | `now()` |
| `expires_at` | timestamp | YES | — |
| `from_project` | varchar | YES | — |
| `parent_message_id` | uuid | YES | — |
| `thread_id` | uuid | YES | — |

**Key observations:**
- No `to_session_id` is mandatory — routing is project-based (`to_project`)
- Threading uses `parent_message_id` + `thread_id` (thread_id = first message's ID in thread)
- Status defaults to `'pending'`; `metadata` inserts as `{}`

---

## 2. Column Registry — Constrained Values

| Column | Valid Values |
|--------|-------------|
| `message_type` | `task_request`, `status_update`, `question`, `notification`, `handoff`, `broadcast` |
| `priority` | `urgent`, `normal`, `low` |
| `status` | `pending`, `read`, `acknowledged`, `actioned`, `deferred` |

---

## 3. MCP Tool Signatures

### `send_message` (server_v2.py line 6260)

```python
def send_message(
    message_type: Literal["task_request", "status_update", "question", "notification", "handoff", "broadcast"],
    body: str,
    subject: str = "",
    to_project: str = "",
    to_session_id: str = "",
    priority: Literal["urgent", "normal", "low"] = "normal",
    from_session_id: str = "",
    from_project: str = "",
    parent_message_id: str = "",
) -> dict
```

**Validation logic:**
1. Auto-detects `from_project` from `claude.sessions` if `from_session_id` provided and `from_project` is empty.
2. Validates `to_project` against `claude.workspaces` (case-insensitive). On failure, returns fuzzy-match suggestions.
3. Resolves threading: looks up parent's `thread_id`; uses `parent_message_id` as `thread_id` if parent has none.

**SQL INSERT:**
```sql
INSERT INTO claude.messages
(from_session_id, from_project, to_session_id, to_project,
 message_type, priority, subject, body, metadata,
 parent_message_id, thread_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING message_id::text, created_at
```

**Returns:** `{success, message_id, created_at, from_project}`

---

### `reply_to` (server_v2.py line 6524)

```python
def reply_to(
    original_message_id: str,
    body: str,
    from_session_id: str = "",
    from_project: str = "",
) -> dict
```

**Logic:**
1. Fetches original message's `from_session_id`, `from_project`, `subject`, `thread_id`.
2. Auto-marks original as `read` (only if currently `pending`) before replying.
3. Routes reply to `original.from_project`; falls back to session lookup if `from_project` is empty.
4. Calls `send_message()` with `message_type="notification"`, prepending `"Re: "` to subject.

**Note:** `reply_to` always sends as type `notification` regardless of the original's type.

---

### Supporting Tools

| Tool | Line | Purpose |
|------|------|---------|
| `check_inbox` | 6161 | Poll pending messages by project or session |
| `acknowledge` | 6417 | Transition status: `read`, `acknowledged`, `actioned`, `deferred` |
| `get_unactioned_messages` | 6645 | Filter to `task_request`/`question`/`handoff` not yet actioned/deferred |
| `bulk_acknowledge` | 6606 | Batch status transition for multiple message IDs |

---

## 4. Database Triggers on `claude.messages`

Two `INSERT` triggers fire on every new message:

### `message_channel_notify` → `notify_new_message()`
Sends `pg_notify` to two channels:
- `claude_msg_{to_project}` — for targeted delivery (when `to_project` is set)
- `claude_msg_broadcast` — for broadcast messages (when `message_type = 'broadcast'`)

Payload JSON: `{message_id, from_project, to_project, message_type, subject, priority}`

### `tr_message_to_activity` → `log_message_to_activity()`
Inserts into `claude.activity_feed` with:
- `source_type = 'message'`
- `activity_type = 'message_broadcast'` or `'message_sent'`
- `severity = 'warning'` for urgent, `'info'` otherwise

---

## 5. Channel Messaging MCP — `server.js`

**Location:** `C:\Projects\claude-family\mcp-servers\channel-messaging\server.js`
**Runtime:** Node.js, MCP SDK `@modelcontextprotocol/sdk`, `pg` client

**Architecture:**
- Single-tool MCP server (`channel_status`) — its primary function is receiving push notifications, not sending.
- Uses `experimental: { 'claude/channel': {} }` capability to inject real-time messages into Claude's context.
- Listens on two PostgreSQL channels via `LISTEN`:
  - `claude_msg_{project_name}` (normalized: lowercase, dashes→underscores)
  - `claude_msg_broadcast`
- Project name resolved from `CLAUDE_PROJECT` env var, or `CLAUDE_PROJECT_DIR` basename, or `cwd()` basename.

**Message delivery flow (receive path):**
1. DB trigger fires `notify_new_message()` on INSERT.
2. PostgreSQL sends `pg_notify` to the relevant channel.
3. `server.js` receives notification, parses payload.
4. Pushes `notifications/claude/channel` MCP notification to Claude.
5. Claude sees: `"New {type} from {from}: {subject}. Use check_inbox() to read the full message."`

**`channel_status` tool returns:**
```json
{
  "connected": true,
  "project": "claude-family",
  "listening_channels": ["claude_msg_claude_family", "claude_msg_broadcast"],
  "database": "localhost"
}
```

**Key constraint:** Channel messaging is receive-only at the MCP level. All sends go through `project-tools` `send_message()`.

---

## 6. Gaps and Observations

1. **No `conversation_mode` field** — `message_type` has no value for conversational back-and-forth distinct from `notification`. This is the gap tracked in FB229/task #600.
2. **`reply_to` always uses `notification` type** — recipients cannot distinguish a reply from a system notification without checking `parent_message_id`.
3. **No targeted session-to-session delivery** — `to_session_id` exists in schema but `channel_status` only listens on project-level channels. A session-targeted message would not trigger a channel notify unless `to_project` is also set.
4. **`metadata` always inserts as `{}`** — not used for custom payload extension currently.
5. **No expiry enforcement** — `expires_at` column exists but no trigger/cleanup queries found.

---

**Version**: 1.0
**Created**: 2026-03-29
**Updated**: 2026-03-29
**Location**: docs/messaging-protocol-research.md
