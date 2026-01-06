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

## Tools (19 total)

### Agent Spawning (7 tools)

| Tool | Purpose |
|------|---------|
| `search_agents` | Search agents by capability (progressive discovery) |
| `spawn_agent` | Spawn agent (blocks until complete) |
| `spawn_agent_async` | Background spawn, returns task_id |
| `check_async_task` | Check async agent status |
| `list_agent_types` | List all agents with costs |
| `recommend_agent` | Get agent recommendation |
| `get_spawn_status` | Spawn safeguards/slots |

### Agent Coordination (5 tools) **NEW**

| Tool | Purpose |
|------|---------|
| `get_context_for_task` | Get composed context from context_rules |
| `update_agent_status` | Agent reports status to boss |
| `get_agent_statuses` | Boss monitors all active agents |
| `send_agent_command` | Boss sends ABORT/REDIRECT/INJECT/PAUSE/RESUME |
| `check_agent_commands` | Agent checks for pending commands |

### Messaging (5 tools)

| Tool | Purpose |
|------|---------|
| `check_inbox` | Check pending messages |
| `send_message` | Message specific project/session |
| `broadcast` | Message ALL Claude instances |
| `reply_to` | Reply to message |
| `acknowledge` | Mark message read/actioned |

### Statistics (2 tools)

| Tool | Purpose |
|------|---------|
| `get_agent_stats` | Agent usage/cost stats |
| `get_mcp_stats` | MCP tool call stats |

---

## Boss-Worker Architecture (NEW)

**Implemented**: 2026-01-05

The main Claude session (Boss) now operates with minimal MCPs and delegates to specialized agents (Workers).

### Boss Configuration
- **MCPs**: orchestrator + postgres + sequential-thinking only (~12k tokens)
- **Role**: Planning, coordination, synthesis, oversight
- **Keeps**: Read, Grep, Glob, Edit (trivial), WebSearch, TodoWrite

### Workflow
```
1. Boss receives task
2. Boss plans approach (sequential-thinking)
3. Boss spawns specialist(s) for execution
4. Workers complete focused tasks
5. Boss reviews, synthesizes, presents
```

### When to Delegate

| Task | Delegate to |
|------|-------------|
| Write new code | coder-haiku, python-coder-haiku |
| MUI components | mui-coder-sonnet |
| Git operations | git-haiku |
| Code review | reviewer-sonnet |
| Testing | tester-haiku, web-tester-haiku |
| Security audit | security-sonnet |

### Quality Benefits
- 70% token savings → more context for reasoning
- Focused specialists → better task performance
- Built-in review cycle → iteration and quality checks

---

## Agent Coordination System **NEW**

**Implemented**: 2026-01-06

Database-driven context injection and real-time agent control.

### Context Rules

Rules in `claude.context_rules` auto-inject coding standards based on:
- **Task keywords**: "database", "sql", "winforms", etc.
- **File patterns**: `**/*.cs`, `**/*.sql`, etc.
- **Agent type**: coder-haiku, python-coder-haiku, etc.

```sql
-- View active rules
SELECT name, task_keywords, priority FROM claude.context_rules
WHERE active = true ORDER BY priority DESC;
```

**Current rules**: winforms-development, mui-development, database-operations, testing-patterns, csharp-development, python-development, typescript-react, documentation-standards

### Agent Status Tracking

Agents report status every 5-7 tool calls to `claude.agent_status`:
- `current_status`: starting, working, waiting, completed, failed, aborted
- `progress_pct`: 0-100
- `discoveries`: JSON array of findings

```
Boss: get_agent_statuses()
→ See all active agents, their progress, what they found
```

### Agent Commands

Boss can control running agents via `claude.agent_commands`:

| Command | Purpose |
|---------|---------|
| `ABORT` | Stop agent immediately |
| `REDIRECT` | Change agent's task focus |
| `INJECT` | Add context to agent's understanding |
| `PAUSE` | Temporarily halt (future) |
| `RESUME` | Continue after pause (future) |

```
Boss: send_agent_command(target_session_id, "REDIRECT", {new_focus: "..."})
Agent: check_agent_commands(session_id) → executes pending commands
```

### Coordination Protocol

Automatically injected into spawned agents:
1. Report status every 5-7 tool calls
2. Check for commands from boss
3. Act on ABORT/REDIRECT/INJECT immediately

---

## Agent Types (17 total)

### Fast/Cheap (Haiku $0.01-0.08)

| Agent | Cost | Use Case |
|-------|------|----------|
| `lightweight-haiku` | $0.01 | Simple file ops |
| `git-haiku` | $0.015 | **NEW** Git operations |
| `coder-haiku` | $0.035 | New code, bug fixes |
| `python-coder-haiku` | $0.045 | Python + DB + REPL |
| `winforms-coder-haiku` | $0.045 | WinForms development |
| `tester-haiku` | $0.052 | Unit/integration tests |
| `web-tester-haiku` | $0.05 | E2E Playwright tests |
| `doc-keeper-haiku` | $0.03 | Doc maintenance |

### Balanced (Sonnet $0.10-0.35)

| Agent | Cost | Use Case |
|-------|------|----------|
| `reviewer-sonnet` | $0.105 | Code review |
| `mui-coder-sonnet` | $0.12 | **NEW** MUI X components (design quality) |
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

**Search agents first** (progressive discovery):
```
search_agents(query="python testing", detail_level="summary")
→ Returns matching agents with costs
```

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

---

## Progressive Discovery Pattern

**Problem**: Loading all 15 agent definitions upfront wastes tokens

**Solution**: Use `search_agents` first, load details on-demand

### Detail Levels

| Level | Returns | Use Case |
|-------|---------|----------|
| `name` | Just agent names | Browsing options |
| `summary` | Name + description + cost | Decision making |
| `full` | Complete spec + MCP config | Ready to spawn |

### Example Flow

```
1. search_agents(query="testing", detail_level="name")
   → ["tester-haiku", "web-tester-haiku"]

2. search_agents(query="web-tester-haiku", detail_level="full")
   → Complete spec

3. spawn_agent(agent_type="web-tester-haiku", ...)
```

**Token savings**: ~98% reduction in upfront context

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
| `claude.context_rules` | **NEW** Context injection rules |
| `claude.agent_status` | **NEW** Real-time agent status |
| `claude.agent_commands` | **NEW** Boss→agent commands |

---

## Related

- [[MCP Registry]] - All MCPs
- [[Claude Tools Reference]] - All tools
- [[Claude Family Postgres]] - Database access

---

**Version**: 5.0 (Agent Coordination System - context injection, status tracking, commands)
**Created**: 2025-12-26
**Updated**: 2026-01-06
**Location**: Claude Family/Orchestrator MCP.md
