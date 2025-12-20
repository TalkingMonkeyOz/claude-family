---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.765085'
---

# Orchestrator MCP

Custom MCP server for spawning specialized Claude agents and inter-Claude messaging.

**Location**: `mcp-servers/orchestrator/server.py`
**Tokens**: ~9k
**Config**: `mcp-servers/orchestrator/agent_specs.json`

---

## Tools

### Agent Spawning

| Tool | Purpose |
|------|---------|
| `spawn_agent` | Spawn isolated Claude agent (sync, blocks until complete) |
| `spawn_agent_async` | Spawn agent in background, returns task_id |
| `check_async_task` | Check status of async spawned agent |
| `list_agent_types` | List all available agent types with costs |
| `recommend_agent` | Get agent recommendation for a task |
| `get_spawn_status` | Current spawn safeguards and slots |

### Messaging (Inter-Claude Communication)

| Tool | Purpose |
|------|---------|
| `check_inbox` | Check for pending messages from other Claudes |
| `send_message` | Send message to specific project/session |
| `broadcast` | Send message to ALL active Claude instances |
| `reply_to` | Reply to a specific message |
| `acknowledge` | Mark message as read/acknowledged |
| `get_active_sessions` | See who's currently online |

### Statistics

| Tool | Purpose |
|------|---------|
| `get_agent_stats` | Usage stats for spawned agents |
| `get_mcp_stats` | Usage stats for MCP tool calls |

---

## Agent Types (14 total)

### Fast/Cheap (Haiku ~$0.01-0.08/task)

| Agent | Cost | Use Case |
|-------|------|----------|
| `lightweight-haiku` | $0.01 | Simple file ops, quick edits |
| `coder-haiku` | $0.035 | New functions, bug fixes |
| `python-coder-haiku` | $0.045 | Python + REPL + DB |
| `tester-haiku` | $0.052 | Unit/integration tests |
| `web-tester-haiku` | $0.05 | E2E testing with Playwright |
| `doc-keeper-haiku` | $0.03 | Documentation maintenance |
| `ux-tax-screen-analyzer` | $0.08 | ATO-specific UX analysis |

### Balanced (Sonnet ~$0.10-0.35/task)

| Agent | Cost | Use Case |
|-------|------|----------|
| `reviewer-sonnet` | $0.105 | Code review, LLM-as-Judge |
| `planner-sonnet` | $0.21 | Task breakdown, roadmaps |
| `security-sonnet` | $0.24 | Security audits, OWASP |
| `analyst-sonnet` | $0.30 | Research, documentation |
| `research-coordinator-sonnet` | $0.35 | Coordinate research teams |

### Premium (Opus ~$0.70-0.85/task)

| Agent | Cost | Use Case |
|-------|------|----------|
| `researcher-opus` | $0.725 | Deep analysis, root cause |
| `architect-opus` | $0.825 | System design, strategy |

---

## Usage Examples

### Spawn Agent (Sync)

```
mcp__orchestrator__spawn_agent(
  agent_type="coder-haiku",
  task="Add input validation to the login form",
  workspace_dir="C:\\Projects\\my-app"
)
```

### Spawn Agent (Async)

```
task_id = mcp__orchestrator__spawn_agent_async(
  agent_type="researcher-opus",
  task="Analyze authentication patterns in the codebase",
  workspace_dir="C:\\Projects\\my-app"
)

# Later...
result = mcp__orchestrator__check_async_task(task_id=task_id)
```

### Check Messages

```
mcp__orchestrator__check_inbox(
  project_name="claude-family",
  include_broadcasts=True
)
```

### Send Message

```
mcp__orchestrator__send_message(
  message_type="notification",
  to_project="ATO-Tax-Agent",
  subject="Config Updated",
  body="MUI MCP has been configured for your project"
)
```

### Broadcast to All

```
mcp__orchestrator__broadcast(
  subject="System Update",
  body="New agent type doc-keeper-haiku available"
)
```

---

## Agent Selection Guide

| Task Type | Recommended Agent |
|-----------|-------------------|
| Quick file edit | `lightweight-haiku` |
| New feature code | `coder-haiku` |
| Python/DB work | `python-coder-haiku` |
| Write tests | `tester-haiku` |
| E2E web tests | `web-tester-haiku` |
| Code review | `reviewer-sonnet` |
| Security audit | `security-sonnet` |
| Documentation | `analyst-sonnet` |
| Plan breakdown | `planner-sonnet` |
| Complex research | `researcher-opus` |
| Architecture | `architect-opus` |
| Multi-agent research | `research-coordinator-sonnet` |
| Doc maintenance | `doc-keeper-haiku` |

---

## Configuration

### Agent Specs

All agents defined in `mcp-servers/orchestrator/agent_specs.json`:

```json
{
  "agent_type": {
    "model": "claude-haiku-4-5",
    "description": "...",
    "use_cases": [...],
    "allowed_tools": [...],
    "disallowed_tools": [...],
    "mcp_config": "configs/agent.mcp.json",
    "workspace_jail_template": "{project_root}/",
    "read_only": false,
    "permission_mode": "bypassPermissions",
    "system_prompt": "...",
    "cost_profile": {...}
  }
}
```

### Per-Agent MCP Configs

Each agent has isolated MCP access in `configs/`:
- `coder-haiku.mcp.json` - filesystem only
- `python-coder-haiku.mcp.json` - filesystem + postgres + python-repl
- `web-tester-haiku.mcp.json` - filesystem + playwright
- etc.

---

## Scheduled Jobs

| Job | Schedule | Agent |
|-----|----------|-------|
| `vault-knowledge-sync` | Daily 7am | Script |
| `doc-keeper-weekly` | Sunday 7am | `doc-keeper-haiku` |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `claude.messages` | Inter-Claude messaging |
| `claude.sessions` | Active session tracking |
| `claude.scheduled_jobs` | Scheduled agent spawns |

---

See also: [[MCP Registry]], [[Claude Tools Reference]], [[Claude Family Postgres]]