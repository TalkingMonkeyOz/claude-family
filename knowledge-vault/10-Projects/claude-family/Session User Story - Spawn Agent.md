---
projects:
  - claude-family
tags:
  - user-stories
  - agents
  - orchestration
  - mcp
synced: false
---

# Session User Story - Spawn Agent

**Actor**: Claude (working on claude-family project)
**Goal**: Spawn doc-keeper-haiku agent to audit documentation
**Trigger**: User request or proactive skill invocation

See [[Session User Stories - Overview]]

---

## Step-by-Step Flow

### 1. User Requests Agent

**User**: "Run the doc-keeper agent to audit the knowledge vault"

**Claude Decision**: Use orchestrator MCP server to spawn agent

---

### 2. Claude Calls spawn_agent MCP Tool

**Tool**: `mcp__orchestrator__spawn_agent`

**Parameters**:
```json
{
  "agent_type": "doc-keeper-haiku",
  "task": "Audit knowledge vault for staleness and accuracy",
  "workspace_dir": "C:\\Projects\\claude-family"
}
```

---

### 3. Orchestrator MCP Server Receives Call

**File**: `mcp-servers/orchestrator/server.py`

**Handler**: `handle_spawn_agent()`

**Actions**:

1. **Load Agent Spec**:
```python
agent_spec = load_agent_spec('doc-keeper-haiku')
# {
#   "agent_type": "doc-keeper-haiku",
#   "model": "haiku",
#   "mcp_config": "configs/agent-configs/doc-keeper-haiku.mcp.json",
#   "timeout": 300
# }
```

2. **Generate Agent Session ID**:
```python
agent_session_id = str(uuid.uuid4())
# Example: 'b2c3d4e5-f6a7-8901-bcde-f12345678901'
```

3. **Log Spawn to Database**:
```python
agent_logger.log_spawn(
    session_id=agent_session_id,
    agent_type='doc-keeper-haiku',
    task_description='Audit knowledge vault for staleness and accuracy',
    workspace_dir='C:\\Projects\\claude-family'
)
```

**Database Write** → `claude.agent_sessions`:
```sql
session_id: b2c3d4e5-f6a7-8901-bcde-f12345678901
agent_type: doc-keeper-haiku
task_description: Audit knowledge vault for staleness and accuracy
created_at: 2025-12-26 10:35:00
created_by: NULL  -- Gap: No parent session tracking
started_at: 2025-12-26 10:35:00
completed_at: NULL
success: NULL
result: NULL
error_message: NULL
estimated_cost_usd: NULL
```

**Gap**: `created_by` is NULL because parent session ID not tracked

---

### 4. Orchestrator Launches Agent Process

**Command**:
```bash
claude \
  --model haiku \
  --mcp-config "C:\Projects\claude-family\mcp-servers\orchestrator\configs\agent-configs\doc-keeper-haiku.mcp.json" \
  --message "Audit knowledge vault for staleness and accuracy"
```

**Agent MCP Config** (`doc-keeper-haiku.mcp.json`):
```json
{
  "postgres": {
    "command": "python",
    "args": ["C:\\Projects\\claude-family\\mcp-servers\\postgres\\server.py"]
  },
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem",
             "C:\\Projects\\claude-family\\knowledge-vault"]
  }
}
```

Agent has access to:
- PostgreSQL database (read-only typically)
- Knowledge vault filesystem

---

### 5. Agent Executes Task

**Agent Actions**:
1. Read knowledge vault files
2. Check for stale documents (updated_at > 30 days)
3. Verify cross-links
4. Generate report

**Agent Output**:
```
# Documentation Audit Report

## Stale Documents (5)
- Database Architecture.md (60 days old)
- Session Management.md (45 days old)
...

## Broken Links (2)
- Identity System.md → [[Missing Document]]
...

## Recommendations
1. Update Database Architecture.md
2. Create missing Identity System.md
```

---

### 6. Agent Completes

**Orchestrator Detects Completion**:
```python
agent_logger.log_completion(
    session_id=agent_session_id,
    success=True,
    result=agent_output,
    estimated_cost_usd=0.08
)
```

**Database Write** → `claude.agent_sessions` (UPDATE):
```sql
session_id: b2c3d4e5-f6a7-8901-bcde-f12345678901
completed_at: 2025-12-26 10:40:00
success: TRUE
result: "# Documentation Audit Report\n\n..."
error_message: NULL
estimated_cost_usd: 0.08
```

---

### 7. Result Returned to Claude

**Orchestrator Returns**:
```json
{
  "session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "success": true,
  "output": "# Documentation Audit Report...",
  "cost": 0.08
}
```

**Claude Receives Result**: Can now show user the audit report

---

## Data Flow Summary

```
User request
    ↓
Claude calls mcp__orchestrator__spawn_agent
    ↓
Orchestrator MCP server
    ↓
├─ INSERT → claude.agent_sessions (log spawn)
├─ Load agent spec
├─ Launch claude subprocess with agent config
└─ Wait for completion
    ↓
Agent executes task
    ↓
├─ Agent uses filesystem MCP to read vault
├─ Agent uses postgres MCP to query database
└─ Agent generates report
    ↓
Agent completes
    ↓
├─ UPDATE → claude.agent_sessions (log completion)
└─ Return result to Claude
    ↓
Claude shows report to user
```

---

## Files Involved

| File | Purpose |
|------|---------|
| `mcp-servers/orchestrator/server.py` | MCP server handling spawn_agent |
| `mcp-servers/orchestrator/agent_specs.json` | Agent type definitions |
| `mcp-servers/orchestrator/db_logger.py` | AgentLogger class |
| `mcp-servers/orchestrator/configs/agent-configs/doc-keeper-haiku.mcp.json` | Agent MCP config |

---

## Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.agent_sessions` | INSERT | Initial spawn record |
| `claude.agent_sessions` | UPDATE | Completion, success, result, cost |

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Session User Story - Spawn Agent.md
