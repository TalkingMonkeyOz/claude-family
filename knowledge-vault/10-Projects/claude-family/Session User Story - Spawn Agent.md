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

**Claude Decision**: Use the native `Task` tool to spawn a subagent

---

### 2. Claude Uses Native Task Tool to Spawn Agent

> **Updated**: The `orchestrator` MCP was retired 2026-02-24. Agent spawning now uses Claude Code's native `Task` tool.

**Tool**: Native `Task` tool

**Parameters**:
```json
{
  "description": "Audit knowledge vault for staleness and accuracy",
  "prompt": "You are a doc-keeper agent. Read the knowledge vault at C:\\Projects\\claude-family\\knowledge-vault and audit for stale documents (last updated > 30 days ago), broken wiki-links, and missing version footers. Generate a report of findings.",
  "subagent_type": "claude-haiku-4-5"
}
```

The spawned agent has access to built-in Read/Glob/Grep tools and any MCPs configured in `disableAllHooks: false` mode.

**Logging**: Spawn is tracked via the `subagent_start_hook.py` PostToolUse hook, which writes to `claude.agent_sessions`.

---

### 3. Agent Executes Task

> **Note**: Steps 3-4 from the original orchestrator flow (server-side handler, explicit subprocess launch) no longer apply. The native `Task` tool handles agent lifecycle internally.

**The spawned agent**:

1. Reads knowledge vault files using built-in `Read`/`Glob` tools
2. Checks for stale documents
3. Verifies cross-links
4. Generates report and returns it as the task result

**Database Write** → `claude.agent_sessions` (via `subagent_start_hook.py`):
```sql
session_id: b2c3d4e5-f6a7-8901-bcde-f12345678901
agent_type: Task (subagent)
task_description: Audit knowledge vault for staleness and accuracy
created_at: 2025-12-26 10:35:00
```

---

### 4. Result Returned to Claude

**Native Task tool returns**:
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

**Claude Receives Result**: Can now show user the audit report

---

## Data Flow Summary

```
User request
    ↓
Claude uses native Task tool
    ↓
├─ subagent_start_hook.py fires (PostToolUse)
├─ INSERT → claude.agent_sessions (log spawn)
└─ Agent process starts with built-in tools
    ↓
Agent executes task
    ↓
├─ Agent uses built-in Read/Glob/Grep to read vault
└─ Agent generates report
    ↓
Agent completes
    ↓
└─ Return result to Claude (Task tool result)
    ↓
Claude shows report to user
```

---

## Files Involved

| File | Purpose |
|------|---------|
| `scripts/subagent_start_hook.py` | Logs agent spawns to claude.agent_sessions (PostToolUse hook) |

---

## Tables Written/Read

| Table | Operation | Data |
|-------|-----------|------|
| `claude.agent_sessions` | INSERT | Initial spawn record |
| `claude.agent_sessions` | UPDATE | Completion, success, result, cost |

---

**Version**: 3.0 (Updated to native Task tool; orchestrator MCP retired 2026-02-24)
**Created**: 2025-12-26
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/claude-family/Session User Story - Spawn Agent.md
