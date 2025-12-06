# ADR-003: Async Agent Workflow

**Status**: Implemented
**Date**: 2025-12-06
**Context**: Claude Governance System

---

## Context

The current `spawn_agent` implementation is **synchronous** - the calling Claude instance blocks until the spawned agent completes. For short tasks (5-30 seconds), this is fine. For longer tasks, it ties up the main session.

User observation: "you spawn other claudes and they work under your control, but so they dont hold up your time"

## Decision

Implement an **async agent workflow** where:

1. `spawn_agent_async()` returns immediately with a task_id
2. The spawned agent works independently
3. Agent reports completion via the messaging system
4. Caller can check status or continue working

## Design

### New Tool: spawn_agent_async

```python
async def spawn_agent_async(
    agent_type: str,
    task: str,
    workspace_dir: str,
    callback_project: str = None,  # Where to send completion message
    timeout: int = 300
) -> dict:
    """
    Spawn agent asynchronously.

    Returns:
        {
            "task_id": "uuid",
            "status": "spawned",
            "message": "Agent will report to <project> when complete"
        }
    """
```

### Workflow

```
Parent Claude                    Child Agent
     │                                │
     ├─ spawn_agent_async() ─────────►│ (starts working)
     │  ◄─ returns task_id             │
     │                                 │
     │  (continues working)            │ (doing task)
     │                                 │
     │                                 │ (completes)
     │  ◄──────────────────────────────┤ send_message(
     │     "task_request" notification │   type="status_update",
     │                                 │   subject="Task Complete: <task_id>",
     │                                 │   body="<result>"
     │                                 │ )
     │                                 │
     ├─ check_inbox() ─────────────────┤
     │  (sees completion message)      │
```

### Database: async_tasks table

```sql
CREATE TABLE claude.async_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,
    task_description TEXT NOT NULL,
    workspace_dir TEXT NOT NULL,
    callback_project VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    spawned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,
    error TEXT,
    parent_session_id UUID,  -- Who spawned it
    CONSTRAINT chk_async_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);
```

### Implementation Changes

#### 1. orchestrator_prototype.py

Add `spawn_agent_async()` that:
- Creates async_tasks record
- Starts subprocess without waiting
- Returns immediately with task_id

```python
async def spawn_agent_async(
    self,
    agent_type: str,
    task: str,
    workspace_dir: str,
    callback_project: str = None
) -> dict:
    # Generate task_id
    task_id = str(uuid.uuid4())

    # Insert pending record
    insert_async_task(task_id, agent_type, task, workspace_dir, callback_project)

    # Build command (same as spawn_agent)
    cmd = self._build_agent_command(agent_type, task, workspace_dir)

    # Wrap task to send completion message
    wrapped_task = f"""
    {task}

    IMPORTANT: When done, send result via:
    mcp__orchestrator__send_message(
        message_type="status_update",
        to_project="{callback_project}",
        subject="Async Task Complete: {task_id}",
        body="<your result here>"
    )
    """

    # Start subprocess without awaiting
    asyncio.create_task(self._run_and_report(task_id, cmd, callback_project))

    return {
        "task_id": task_id,
        "status": "spawned",
        "message": f"Agent will report to {callback_project} when complete"
    }
```

#### 2. server.py

Add new MCP tools:
- `spawn_agent_async` - Non-blocking spawn
- `check_async_task` - Check task status by ID
- `list_async_tasks` - List pending/recent tasks

#### 3. Coordinator agents

Update coordinator agents (test-coordinator, review-coordinator) to:
- Use `spawn_agent_async` for child tasks
- Periodically check inbox for results
- Aggregate when all children complete

## Alternatives Considered

### 1. Polling-based

Parent polls `check_task_status(task_id)` periodically.
**Rejected**: Wasteful, delays response.

### 2. Webhook callback

Agent calls HTTP endpoint on completion.
**Rejected**: Requires HTTP server, more complex.

### 3. Messaging (selected)

Uses existing messaging infrastructure.
**Selected**: Already exists, simple, no new dependencies.

## Consequences

### Positive

- Long tasks don't block main session
- Parent can work on other things
- Natural fit with existing messaging
- Coordinators can parallelize effectively

### Negative

- More complex flow to track
- Results may be missed if not checking inbox
- Need to handle orphaned async tasks

## Migration

1. Add async_tasks table
2. Add spawn_agent_async to server.py
3. Update coordinator agents to use async pattern
4. Document usage in README

## Status Tracking

| Component | Status |
|-----------|--------|
| async_tasks table | Complete |
| spawn_agent_async function | Complete |
| MCP tool exposure | Complete |
| check_async_task tool | Complete |
| Coordinator updates | Pending |
| Documentation | This ADR |

## Implementation Notes (2025-12-06)

Files modified:
- `mcp-servers/orchestrator/orchestrator_prototype.py` - Added `spawn_agent_async()` and `_run_async_agent()`
- `mcp-servers/orchestrator/db_logger.py` - Added `log_async_spawn()` and `update_async_task()`
- `mcp-servers/orchestrator/server.py` - Added `spawn_agent_async` and `check_async_task` MCP tools

Usage:
```python
# Spawn async - returns immediately
result = mcp__orchestrator__spawn_agent_async(
    agent_type="coder-haiku",
    task="Write a utility function",
    workspace_dir="C:/Projects/myproject",
    callback_project="claude-family"
)
# Returns: {"task_id": "uuid", "status": "spawned", ...}

# Check status later
status = mcp__orchestrator__check_async_task(task_id="uuid")
# Returns task status, result, or error

# Or just check inbox for completion message
messages = mcp__orchestrator__check_inbox(project_name="claude-family")
```

---

**Version**: 1.0
**Created**: 2025-12-06
**Author**: Claude Family Infrastructure
