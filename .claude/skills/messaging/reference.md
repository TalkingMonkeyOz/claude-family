# Messaging Skill — Detailed Reference

## Message Context Template (REQUIRED for Actionable Messages)

**When sending `task_request`, `question`, or `handoff` messages, ALWAYS include structured context.**

### Required Fields

| Field | Purpose | Example |
|-------|---------|---------|
| **BACKGROUND** | Why is this needed? | "Adding login functionality. UI complete, needs backend." |
| **CURRENT STATE** | What exists? | "LoginPage.xaml exists, ViewModel is stub" |
| **SPECIFIC ASK** | What action needed? | "Implement login API call and wire up ViewModel" |
| **FILES** | Which file paths? | "src/ViewModels/LoginViewModel.cs" |
| **SUCCESS CRITERIA** | How to verify? | "User can login, failure shows error" |

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

### Example Good vs Bad Message

**Good**: Includes background, current state, specific ask, files, success criteria.

**Bad**: `"Please implement the authentication we discussed."` — No context, no files, no criteria.

**Provide context = Respect recipient's time**

---

## Checking Inbox — Detailed Examples

```python
messages = mcp__project-tools__check_inbox(
    project_name="claude-family",  # IMPORTANT: Required to see project messages
    session_id="your-session-id",  # Optional: for direct messages
    include_broadcasts=True,        # Default: true
    include_read=False              # Default: false (only pending)
)

for msg in messages['messages']:
    print(f"From: {msg['from_project']}, Type: {msg['message_type']}")
    print(f"Subject: {msg['subject']}, Priority: {msg['priority']}")
```

**Filtering behavior**: No params = broadcasts only. With `project_name` = project messages + broadcasts.

---

## Sending Messages — Full Examples

### Direct Message

```python
mcp__project-tools__send_message(
    to_session_id="target-session-id",
    message_type="task_request",
    subject="Please review authentication changes",
    body="I've implemented JWT auth in src/auth.ts. Please review.",
    priority="normal"
)
```

### Project-Targeted Message

```python
mcp__project-tools__send_message(
    to_project="nimbus-user-loader",
    message_type="notification",
    subject="Migration completed",
    body="User data migration complete. 1,234 users imported.",
    from_project="claude-family",
    priority="normal"
)
```

### Broadcasting

```python
mcp__project-tools__broadcast(
    subject="New auto-apply instruction added",
    body="Added markdown.instructions.md. Affects all .md file edits.",
    priority="low"
)
```

---

## Acknowledging Messages — All Actions

| Action | When | Required Params |
|--------|------|-----------------|
| `read` | Informational messages | message_id |
| `acknowledged` | Seen, understood, no action needed | message_id |
| `actioned` | Convert to todo | message_id, project_id |
| `deferred` | Explicitly skip | message_id, defer_reason |

### Actioned (Creates Todo)

```python
mcp__project-tools__acknowledge(
    message_id="uuid", action="actioned",
    project_id="project-uuid", priority=3
)
```

Creates todo in `claude.todos`, links via `source_message_id`, returns `todo_id`.

### Deferred

```python
mcp__project-tools__acknowledge(
    message_id="uuid", action="deferred",
    defer_reason="Out of scope for current sprint"
)
```

Marks as deferred, stores reason, removes from unactioned queries.

### Action Decision Tree

```
Actionable? (task_request/question/handoff)
  YES → Will act? → YES: actioned + project_id
                   → NO:  deferred + reason
        Already done? → acknowledged
  NO  → read
```

---

## Replying to Messages

```python
mcp__project-tools__reply_to(
    original_message_id="uuid",
    body="Reviewed auth changes. Looks good! Add rate limiting.",
    from_project="claude-family"
)
```

Routes to original sender's `from_project` (not ephemeral session ID).

---

## Async Agent Pattern

```python
task_id = "researcher-auth-<timestamp>"
Task(
    subagent_type="researcher-opus",
    prompt=f"Research auth. When complete, send_message(to_project='claude-family', subject='Async Complete: {task_id}', body='<findings>')",
    run_in_background=True
)
# Later: check_inbox for task_id in subject
```

---

## Common SQL Queries

See [reference-sql.md](./reference-sql.md) for full SQL examples.

---

## Coordination Patterns

See [reference-patterns.md](./reference-patterns.md) for handoff, coordination, and status update patterns.

---

## Key Gotchas

1. **Forgetting project_name in check_inbox** — project messages won't appear
2. **Not acknowledging messages** — inbox fills up
3. **Wrong priority** — reserve "urgent" for true emergencies
4. **Missing async agent messages** — include messaging instruction in agent task
5. **Unknown recipient** — use `list_recipients()` first
6. **Reply to dead session** — fixed: `reply_to()` now routes to `from_project`
