# Messaging Skill

**Status**: Active
**Last Updated**: 2025-12-26

---

## Overview

This skill provides guidance for inter-Claude communication: sending messages, checking inbox, broadcasting to all instances, and coordinating work.

---

## When to Use

Invoke this skill when:
- Coordinating work across multiple Claude instances
- Handing off work to another Claude instance
- Broadcasting announcements to all instances
- Checking for messages from other instances
- Asynchronous agent completion notifications

---

## Quick Reference

### Messaging Commands

| Command | Purpose | Recipients |
|---------|---------|------------|
| `/check-messages` or `/inbox-check` | View pending messages | Current instance |
| `/broadcast` | Send to all active instances | All |
| `/team-status` | View active Claude instances | - |

---

## Message Types

| Type | Purpose | Example |
|------|---------|---------|
| `task_request` | Request work from another instance | "Please review PR #123" |
| `status_update` | Share progress update | "Completed user auth feature" |
| `question` | Ask for input/decision | "Which approach for caching?" |
| `notification` | Inform about event | "Database migration completed" |
| `handoff` | Transfer work to another instance | "Taking over nimbus-import work" |
| `broadcast` | Announce to all | "New coding standard added" |

---

## Message Context Template (REQUIRED for Actionable Messages)

**When sending `task_request`, `question`, or `handoff` messages, ALWAYS include structured context.**

### Required Fields

| Field | Purpose | Example |
|-------|---------|---------|
| **BACKGROUND** | Why is this needed? What led to this? | "We're adding login functionality. UI is complete but needs backend." |
| **CURRENT STATE** | What's already done? What exists? | "LoginPage.xaml exists, ViewModel is stub, API not implemented" |
| **SPECIFIC ASK** | Exactly what action is needed? | "Implement login API call and wire up ViewModel" |
| **FILES** | Which specific file paths are relevant? | "src/ViewModels/LoginViewModel.cs, src/Services/AuthService.cs (create)" |
| **SUCCESS CRITERIA** | How to verify completion? | "User can login, success navigates to Dashboard, failure shows error" |

### Template

```
Subject: [Clear, specific title]

BACKGROUND:
[Why is this being requested? What led to this need?]

CURRENT STATE:
[What's already done? What files/work exists?]

SPECIFIC ASK:
[Exactly what action is needed from the recipient?]

FILES:
- [Full path to file 1] - [purpose]
- [Full path to file 2] - [purpose]

SUCCESS CRITERIA:
[How will the recipient know they did it correctly?]
```

### Example Good Message

```python
mcp__orchestrator__send_message(
    to_project="claude-family-manager",
    message_type="task_request",
    subject="Implement user authentication flow",
    body="""
BACKGROUND:
We're adding login functionality to the app. The UI is complete but needs
backend integration with the PostgreSQL database.

CURRENT STATE:
- LoginPage.xaml exists at src/Views/LoginPage.xaml
- LoginViewModel stub at src/ViewModels/LoginViewModel.cs
- User table exists in database with password_hash column
- API client infrastructure not yet implemented

SPECIFIC ASK:
Implement the login API call and wire up the ViewModel to handle user login.

FILES:
- src/ViewModels/LoginViewModel.cs - Wire up login command
- src/Services/AuthService.cs - Create new, implement login logic
- src/Models/LoginRequest.cs - Create new, login request DTO
- src/Models/LoginResponse.cs - Create new, login response DTO

SUCCESS CRITERIA:
- User can enter email/password and click Login button
- Success → navigates to DashboardPage with user context
- Failure → shows error message in UI (invalid credentials, network error, etc.)
- Passwords are never logged or stored in plaintext
    """,
    priority="normal"
)
```

### Example Bad Message (DON'T DO THIS)

```python
mcp__orchestrator__send_message(
    to_project="claude-family-manager",
    message_type="task_request",
    subject="Fix the login",
    body="Please implement the authentication we discussed.",
    priority="normal"
)
```

**Why it's bad:**
- No background context (what discussion?)
- No current state (what exists already?)
- Vague ask ("fix the login" - what's broken?)
- No file references (where to work?)
- No success criteria (how to know when done?)

### Enforcement

The receiving Claude instance will have difficulty understanding vague messages:
- May implement wrong thing
- May waste time exploring codebase
- May ask clarifying questions (delays work)
- May misconstrue intent entirely

**Provide context = Respect recipient's time**

---

## Checking Inbox

### Via Command

```bash
/check-messages
```

or

```bash
/inbox-check
```

**Shows**:
- Unread messages addressed to you
- Broadcast messages to all
- Project-targeted messages
- Message priority (urgent, normal, low)

### Via MCP Tool

```python
messages = mcp__orchestrator__check_inbox(
    project_name="claude-family",  # IMPORTANT: Required to see project messages
    session_id="your-session-id",  # Optional: for direct messages
    include_broadcasts=True,        # Default: true
    include_read=False              # Default: false (only pending)
)

for msg in messages['messages']:
    print(f"From: {msg['from_session_id']}")
    print(f"Type: {msg['message_type']}")
    print(f"Subject: {msg['subject']}")
    print(f"Body: {msg['body']}")
    print(f"Priority: {msg['priority']}")
```

**CRITICAL**: Always pass `project_name` to see project-targeted messages!

---

## Sending Messages

### Direct Message (To Specific Session)

```python
mcp__orchestrator__send_message(
    to_session_id="target-session-id",
    message_type="task_request",
    subject="Please review authentication changes",
    body="I've implemented JWT auth in src/auth.ts. Please review for security and best practices.",
    priority="normal",  # urgent | normal | low
    from_session_id="your-session-id"  # Optional
)
```

### Project-Targeted Message

```python
mcp__orchestrator__send_message(
    to_project="nimbus-user-loader",  # Any Claude working on this project will see it
    message_type="notification",
    subject="Migration completed",
    body="User data migration from legacy system complete. 1,234 users imported.",
    priority="normal"
)
```

### Broadcasting to All

```python
mcp__orchestrator__broadcast(
    subject="New auto-apply instruction added",
    body="Added markdown.instructions.md for documentation standards. Affects all .md file edits.",
    priority="low",
    from_session_id="your-session-id"
)
```

**or via command**:

```bash
/broadcast subject="New standard" body="Message here"
```

---

## Message Workflow

### Async Agent Pattern

When spawning async agents, have them message results:

```python
# Spawn agent async
task_id = mcp__orchestrator__spawn_agent_async(
    agent_type="researcher-opus",
    task=f"""
    Research authentication best practices.

    IMPORTANT: When complete, send results:
    mcp__orchestrator__send_message(
        to_project="claude-family",
        subject="Async Task Complete: {task_id}",
        body="<your findings here>"
    )
    """,
    workspace_dir="C:/Projects/claude-family"
)

# Later, check inbox for completion
messages = mcp__orchestrator__check_inbox(project_name="claude-family")
for msg in messages:
    if task_id in msg['subject']:
        print("Agent completed!")
        print(msg['body'])
```

---

## Acknowledging Messages

### Mark as Read

For informational messages (status_update, notification, broadcast):

```python
mcp__orchestrator__acknowledge(
    message_id="message-uuid",
    action="read"
)
```

### Mark as Acknowledged

For messages you've seen and understood but don't require further action:

```python
mcp__orchestrator__acknowledge(
    message_id="message-uuid",
    action="acknowledged"
)
```

### Mark as Actioned (Create Todo)

For actionable messages (task_request, question, handoff) that you want to convert to a persistent todo:

```python
mcp__orchestrator__acknowledge(
    message_id="message-uuid",
    action="actioned",
    project_id="project-uuid",  # Required
    priority=3  # Optional: 1-5, default 3
)
```

**This will:**
- Create a new todo in `claude.todos` with the message subject as content
- Link the todo to the message via `source_message_id`
- Mark the message status as 'actioned'
- Return the new `todo_id`

### Mark as Deferred (Explicitly Skip)

For messages you're choosing not to action, with a reason:

```python
mcp__orchestrator__acknowledge(
    message_id="message-uuid",
    action="deferred",
    defer_reason="Out of scope for current sprint - will revisit in Q2"  # Required
)
```

**This will:**
- Mark the message status as 'deferred'
- Store the reason in message metadata
- Remove from "unactioned" queries
- Preserve message for audit trail

### Action Decision Tree

```
Is this message actionable?
(task_request / question / handoff)
    │
    ├─ YES
    │   │
    │   ├─ Will you act on it?
    │   │   │
    │   │   ├─ YES → Use action='actioned' + project_id
    │   │   │         (Creates todo, marks as actioned)
    │   │   │
    │   │   └─ NO  → Use action='deferred' + defer_reason
    │   │             (Explicitly skipped with reason)
    │   │
    │   └─ Already completed it?
    │       └─ Use action='acknowledged'
    │          (Work done, no todo needed)
    │
    └─ NO (informational only)
        └─ Use action='read'
           (Just marking as seen)
```

---

## Replying to Messages

```python
mcp__orchestrator__reply_to(
    original_message_id="message-uuid",
    body="I've reviewed the auth changes. Looks good! Just one suggestion: add rate limiting to login endpoint.",
    from_session_id="your-session-id"
)
```

**Creates**: New message with `in_reply_to` link to original

---

## Viewing Active Team

See who's currently working:

```bash
/team-status
```

or

```python
sessions = mcp__orchestrator__get_active_sessions()

for session in sessions['sessions']:
    print(f"{session['identity_name']}: {session['project_name']}")
    print(f"  Session: {session['session_id']}")
    print(f"  Started: {session['session_start']}")
```

---

## Message Priority Guidelines

| Priority | When to Use | Response Time |
|----------|-------------|---------------|
| **urgent** | Security issues, production down, blocking bugs | <1 hour |
| **normal** | Regular work items, reviews, questions | <1 day |
| **low** | FYI, announcements, nice-to-haves | When convenient |

---

## Common Queries

```sql
-- Unread messages for project
SELECT
    message_id::text,
    from_session_id::text,
    message_type,
    subject,
    body,
    priority,
    created_at
FROM claude.messages
WHERE to_project = 'claude-family'
  AND status = 'pending'
ORDER BY
    CASE priority
        WHEN 'urgent' THEN 1
        WHEN 'normal' THEN 2
        WHEN 'low' THEN 3
    END,
    created_at ASC;

-- Messages sent by me
SELECT
    to_project,
    to_session_id::text,
    subject,
    status,
    created_at
FROM claude.messages
WHERE from_session_id = 'your-session-id'::uuid
ORDER BY created_at DESC
LIMIT 20;

-- Broadcast messages
SELECT
    subject,
    body,
    created_at
FROM claude.messages
WHERE message_type = 'broadcast'
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

---

## Coordination Patterns

### Pattern 1: Handoff

```python
# Claude instance A hands off work
mcp__orchestrator__send_message(
    to_project="nimbus-import",
    message_type="handoff",
    subject="Handing off nimbus-import work",
    body="""
    I've completed the data loader infrastructure. Remaining work:
    1. Add error handling for malformed CSV
    2. Implement retry logic for API failures
    3. Add progress tracking

    Code is in src/loader.py. Tests pass but coverage only 60%.
    """,
    priority="normal"
)
```

### Pattern 2: Coordination Request

```python
# Ask for help with decision
mcp__orchestrator__send_message(
    to_project="claude-family",
    message_type="question",
    subject="Architecture decision: caching strategy",
    body="""
    Need input on caching for user data:

    Option A: Redis (fast, separate service)
    Option B: In-memory (simple, no extra dependency)
    Option C: PostgreSQL materialized views (consistent with DB)

    Current load: ~1000 users, read-heavy (90% reads)
    Preference?
    """,
    priority="normal"
)
```

### Pattern 3: Status Update

```python
# Regular progress updates
mcp__orchestrator__send_message(
    to_project="claude-family",
    message_type="status_update",
    subject="Weekly progress: Authentication feature",
    body="""
    Progress this week:
    - ✅ JWT token generation
    - ✅ Login/logout endpoints
    - ✅ Auth middleware
    - 🔄 Refresh token logic (70% complete)
    - ⏳ Email verification (not started)

    ETA: Complete by end of week
    Blockers: None
    """,
    priority="low"
)
```

---

## Related Skills

- `session-management` - Session-scoped messaging
- `agentic-orchestration` - Agent completion notifications
- `project-ops` - Project-targeted messages

---

## Key Gotchas

### 1. Forgetting project_name in check_inbox

**Problem**: Project-targeted messages won't appear

```python
# WRONG: Won't see project messages
messages = mcp__orchestrator__check_inbox()

# CORRECT: Sees project messages
messages = mcp__orchestrator__check_inbox(project_name="claude-family")
```

### 2. Not Acknowledging Messages

**Problem**: Inbox fills with read but unacknowledged messages

**Solution**: Mark messages as read or acknowledged after handling

### 3. Wrong Priority

**Problem**: Using "urgent" for non-urgent items

**Solution**: Reserve "urgent" for true emergencies

### 4. Missing Async Agent Messages

**Problem**: Agent completes but forgets to send completion message

**Solution**: Include messaging instruction in agent task

---

**Version**: 2.0 (Added message context template + actioned/deferred actions)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: .claude/skills/messaging/skill.md
