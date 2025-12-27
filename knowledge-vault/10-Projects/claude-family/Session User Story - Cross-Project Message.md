---
projects:
  - claude-family
tags:
  - user-stories
  - messaging
  - cross-project
  - coordination
synced: false
---

# Session User Story - Cross-Project Message

**Actor**: Claude (claude-family project)
**Goal**: Send task request to ATO-tax-agent project
**Trigger**: Need to coordinate work across projects

See [[Session User Stories - Overview]]

---

## Step-by-Step Flow

### 1. Claude Identifies Need to Message Another Project

**Scenario**: Claude working on claude-family needs ATO-tax-agent to run its test suite.

**Claude Decision**: Use orchestrator messaging system

---

### 2. Claude Sends Message

**MCP Tool**: `mcp__orchestrator__send_message`

```json
{
  "message_type": "task_request",
  "subject": "Run test suite",
  "body": "Please run your full test suite and report any failures. The database schema was updated and we need to ensure compatibility.",
  "to_project": "ATO-Tax-Agent",
  "from_session_id": "e4f5a6b7-c8d9-0123-4567-890abcdef012",
  "priority": "normal"
}
```

---

### 3. Orchestrator Creates Message Record

**File**: `mcp-servers/orchestrator/server.py`

**Handler**: `handle_send_message()`

```python
message_id = str(uuid.uuid4())

cursor.execute("""
    INSERT INTO claude.messages (
        message_id,
        message_type,
        subject,
        body,
        to_project,
        from_session_id,
        priority,
        status,
        created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', NOW())
    RETURNING message_id
""", (message_id, 'task_request', 'Run test suite', body,
      'ATO-Tax-Agent', from_session_id, 'normal'))
```

**Database Write** → `claude.messages`:
```sql
message_id: f5a6b7c8-d9e0-1234-5678-90abcdef0123
message_type: task_request
subject: Run test suite
body: Please run your full test suite and report any failures...
to_project: ATO-Tax-Agent
to_session_id: NULL
from_project: claude-family
from_session_id: e4f5a6b7-c8d9-0123-4567-890abcdef012
priority: normal
status: pending
created_at: 2025-12-26 15:00:00
read_at: NULL
acknowledged_at: NULL
```

---

### 4. Message Waits for Recipient

**Status**: Message sits in `claude.messages` table with `status = 'pending'`

---

### 5. User Launches Claude on ATO-Tax-Agent Project (Later)

**SessionStart Hook Fires**:

**File**: `session_startup_hook.py`

**Checks for Messages**:
```python
cursor.execute("""
    SELECT message_id, subject, body, from_project
    FROM claude.messages
    WHERE (to_project = %s OR to_project IS NULL)
      AND status = 'pending'
""", ('ATO-Tax-Agent',))
```

**Database Read** ← `claude.messages`:
```sql
message_id: f5a6b7c8-d9e0-1234-5678-90abcdef0123
subject: Run test suite
body: Please run your full test suite and report any failures...
from_project: claude-family
```

---

### 6. Claude Receives Message at Session Start

**SessionStart Hook Returns**:
```json
{
  "session_id": "...",
  "project_name": "ATO-Tax-Agent",
  "session_state": {...},
  "messages": [
    {
      "message_id": "f5a6b7c8-d9e0-1234-5678-90abcdef0123",
      "subject": "Run test suite",
      "body": "Please run your full test suite and report any failures...",
      "from_project": "claude-family"
    }
  ]
}
```

**Claude Shows User**:
```
Session started for ATO-Tax-Agent.

You have 1 pending message:

From: claude-family
Subject: Run test suite
Body: Please run your full test suite and report any failures. The database schema was updated and we need to ensure compatibility.

Would you like me to run the test suite now?
```

---

### 7. Claude Acts on Message

**User**: "Yes, run the tests"

**Claude Executes**:
```bash
dotnet test ATO-Tax-Agent.Tests.csproj
```

**Test Results**:
```
Total tests: 45
Passed: 43
Failed: 2

Failed tests:
- TaxCalculator_ValidateDeductions_WithNewSchema
- Form1040_Calculate_WithUpdatedRules
```

---

### 8. Claude Marks Message as Read

**MCP Tool**: `mcp__orchestrator__acknowledge`

```json
{
  "message_id": "f5a6b7c8-d9e0-1234-5678-90abcdef0123",
  "action": "read"
}
```

**Database Write** → `claude.messages` (UPDATE):
```sql
message_id: f5a6b7c8-d9e0-1234-5678-90abcdef0123
status: read
read_at: 2025-12-26 15:30:00
```

---

### 9. Claude Sends Reply

**MCP Tool**: `mcp__orchestrator__reply_to`

```json
{
  "original_message_id": "f5a6b7c8-d9e0-1234-5678-90abcdef0123",
  "body": "Test suite completed. 2 tests failed:\n\n1. TaxCalculator_ValidateDeductions_WithNewSchema\n2. Form1040_Calculate_WithUpdatedRules\n\nBoth failures are due to schema changes in deductions table. Fixing now.",
  "from_session_id": "a6b7c8d9-e0f1-2345-6789-0abcdef01234"
}
```

**Database Write** → `claude.messages` (new record):
```sql
message_id: a7b8c9d0-e1f2-3456-789a-bcdef0123456
message_type: notification
subject: Re: Run test suite
body: Test suite completed. 2 tests failed...
to_project: claude-family
from_project: ATO-Tax-Agent
from_session_id: a6b7c8d9-e0f1-2345-6789-0abcdef01234
in_reply_to: f5a6b7c8-d9e0-1234-5678-90abcdef0123
priority: normal
status: pending
created_at: 2025-12-26 15:35:00
```

---

### 10. Original Sender Receives Reply (Next Session)

When Claude launches on claude-family project next time:

**SessionStart Hook Checks Messages**:
```sql
SELECT * FROM claude.messages
WHERE to_project = 'claude-family' AND status = 'pending';
```

**Finds Reply**:
```
From: ATO-Tax-Agent
Subject: Re: Run test suite
Body: Test suite completed. 2 tests failed...
```

**Claude Shows User**:
```
You have 1 pending message:

From: ATO-Tax-Agent (reply to your message)
Subject: Re: Run test suite
Body: Test suite completed. 2 tests failed:
1. TaxCalculator_ValidateDeductions_WithNewSchema
2. Form1040_Calculate_WithUpdatedRules
Both failures are due to schema changes in deductions table. Fixing now.
```

---

## Files Involved

| File | Purpose |
|------|---------|
| `mcp-servers/orchestrator/server.py` | Handles send_message, reply_to, acknowledge |
| `session_startup_hook.py` | Checks for pending messages at session start |

---

## Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.messages` | INSERT | Original message (status=pending) |
| `claude.messages` | SELECT | Check for pending messages (at session start) |
| `claude.messages` | UPDATE | Mark as read (read_at timestamp) |
| `claude.messages` | INSERT | Reply message (in_reply_to links to original) |

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Session User Story - Cross-Project Message.md
