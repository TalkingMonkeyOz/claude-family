---
projects:
- claude-family
synced: false
synced_at: '2025-12-27T00:00:00.000000'
tags:
- quick-reference
- mcp
- claude-family
- orchestration
---

# Orchestrator MCP

Custom MCP for spawning specialized agents and inter-Claude messaging.

**Location**: `mcp-servers/orchestrator/server.py`
**Tokens**: ~9k
**Agent Specs**: `agent_specs.json`

---

## Tools (13 total)

### Agent Spawning (6 tools)

| Tool | Purpose |
|------|---------|
| `spawn_agent` | Spawn agent (blocks until complete) |
| `spawn_agent_async` | Background spawn, returns task_id |
| `check_async_task` | Check async agent status |
| `list_agent_types` | List all agents with costs |
| `recommend_agent` | Get agent recommendation |
| `get_spawn_status` | Spawn safeguards/slots |

### Messaging (6 tools)

| Tool | Purpose |
|------|---------|
| `check_inbox` | Check pending messages |
| `send_message` | Message specific project/session |
| `broadcast` | Message ALL Claude instances |
| `reply_to` | Reply to message |
| `acknowledge` | Mark message read/actioned |
| `get_active_sessions` | See who's online |

### Statistics (2 tools)

| Tool | Purpose |
|------|---------|
| `get_agent_stats` | Agent usage/cost stats |
| `get_mcp_stats` | MCP tool call stats |

---

## Agent Types (15 total)

### Fast/Cheap (Haiku $0.01-0.08)

| Agent | Cost | Use Case |
|-------|------|----------|
| `lightweight-haiku` | $0.01 | Simple file ops |
| `coder-haiku` | $0.035 | New code, bug fixes |
| `python-coder-haiku` | $0.045 | Python + DB + REPL |
| `tester-haiku` | $0.052 | Unit/integration tests |
| `web-tester-haiku` | $0.05 | E2E Playwright tests |
| `doc-keeper-haiku` | $0.03 | Doc maintenance |
| `winforms-coder-haiku` | $0.045 | WinForms development |

### Balanced (Sonnet $0.10-0.35)

| Agent | Cost | Use Case |
|-------|------|----------|
| `reviewer-sonnet` | $0.105 | Code review |
| `planner-sonnet` | $0.21 | Task breakdown |
| `security-sonnet` | $0.24 | Security audits |
| `analyst-sonnet` | $0.30 | Research, docs |
| `research-coordinator-sonnet` | $0.35 | Multi-agent research |

### Premium (Opus $0.70-0.85)

| Agent | Cost | Use Case |
|-------|------|----------|
| `researcher-opus` | $0.725 | Deep analysis |
| `architect-opus` | $0.825 | System design |

---

## Quick Reference

**Spawn agent**:
```
spawn_agent(agent_type="coder-haiku", task="...", workspace_dir="...")
```

**Check messages**:
```
check_inbox(project_name="claude-family")
```

**Send message**:
```
send_message(to_project="ATO-Tax-Agent", message_type="notification", ...)
```

**Broadcast**:
```
broadcast(subject="...", body="...")
```

---

## Configuration

**Agent specs**: `mcp-servers/orchestrator/agent_specs.json`
**Per-agent MCPs**: `mcp-servers/orchestrator/configs/*.mcp.json`

Each agent has isolated MCP access:
- `coder-haiku` → filesystem only
- `python-coder-haiku` → filesystem + postgres + python-repl
- `web-tester-haiku` → filesystem + playwright

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `claude.messages` | Inter-Claude messaging |
| `claude.agent_sessions` | Agent spawn history |
| `claude.scheduled_jobs` | Scheduled spawns |

---

## Related

- [[MCP Registry]] - All MCPs
- [[Claude Tools Reference]] - All tools
- [[Claude Family Postgres]] - Database access

---

**Version**: 2.0 (Condensed)
**Created**: 2025-12-26
**Updated**: 2025-12-27
**Location**: Claude Family/Orchestrator MCP.md
