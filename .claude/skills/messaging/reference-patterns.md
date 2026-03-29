# Messaging — Coordination Patterns

## Pattern 1: Handoff

```python
mcp__project-tools__send_message(
    to_project="nimbus-import",
    message_type="handoff",
    subject="Handing off nimbus-import work",
    body="""
    Completed data loader infrastructure. Remaining:
    1. Add error handling for malformed CSV
    2. Implement retry logic for API failures
    3. Add progress tracking
    Code is in src/loader.py. Tests pass but coverage only 60%.
    """,
    priority="normal"
)
```

## Pattern 2: Coordination Request

```python
mcp__project-tools__send_message(
    to_project="claude-family",
    message_type="question",
    subject="Architecture decision: caching strategy",
    body="""
    Need input on caching for user data:
    Option A: Redis (fast, separate service)
    Option B: In-memory (simple, no extra dependency)
    Option C: PostgreSQL materialized views (consistent with DB)
    Current load: ~1000 users, read-heavy (90% reads). Preference?
    """,
    priority="normal"
)
```

## Pattern 3: Status Update

```python
mcp__project-tools__send_message(
    to_project="claude-family",
    message_type="status_update",
    subject="Weekly progress: Authentication feature",
    body="""
    Progress: JWT tokens, login/logout, auth middleware done.
    Refresh token logic 70% complete. Email verification not started.
    ETA: End of week. Blockers: None.
    """,
    priority="low"
)
```
