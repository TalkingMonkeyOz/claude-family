---
name: agentic-orchestration
description: Spawn and coordinate Claude agents for parallel work
model: opus
context: fork
allowed-tools:
  - Read
  - mcp__orchestrator__*
---

# Agentic Orchestration Skill

**Status**: Active
**Last Updated**: 2026-01-08

---

## Overview

This skill provides guidance for spawning and coordinating Claude agents for parallel work, subtasks, and specialized operations.

---

## When to Use

Invoke this skill when:
- Task requires specialized expertise (security, architecture, testing)
- Work can be parallelized across multiple agents
- Need to offload time-consuming subtasks
- Coordinating multi-agent workflows
- Spawning agents for code review, testing, or research

---

## Quick Reference

### Available Agent Types

| Agent | Model | Use For | Cost | Timeout |
|-------|-------|---------|------|---------|
| **coder-haiku** | Haiku 4.5 | Code writing, refactoring | $0.035 | 1200s |
| **python-coder-haiku** | Haiku 4.5 | Python + DB + REPL | $0.045 | 900s |
| **lightweight-haiku** | Haiku 4.5 | Simple file operations | $0.01 | 600s |
| **reviewer-sonnet** | Sonnet 4.5 | Code review | $0.105 | 900s |
| **security-sonnet** | Sonnet 4.5 | Security audits | $0.24 | 600s |
| **analyst-sonnet** | Sonnet 4.5 | Research, docs | $0.30 | 600s |
| **architect-opus** | Opus 4.5 | Architecture design | $0.825 | 900s |
| **tester-haiku** | Haiku 4.5 | Unit/integration tests | $0.052 | 600s |
| **web-tester-haiku** | Haiku 4.5 | E2E Playwright tests | $0.05 | 600s |

**Full list**: Use `mcp__orchestrator__list_agent_types()` for all 13 agent types

---

## Spawning Agents

### Synchronous (Blocking)

Wait for agent to complete before continuing:

```python
result = mcp__orchestrator__spawn_agent(
    agent_type="reviewer-sonnet",
    task="Review src/auth.ts for security vulnerabilities and code quality",
    workspace_dir="C:/Projects/myproject"
)

if result['success']:
    print(result['output'])
else:
    print(f"Agent failed: {result['error']}")
```

### Asynchronous (Non-Blocking)

Spawn agent in background, continue working:

```python
task_result = mcp__orchestrator__spawn_agent_async(
    agent_type="analyst-sonnet",
    task="Research OAuth 2.0 best practices and create implementation guide",
    workspace_dir="C:/Projects/myproject",
    callback_project="claude-family"  # Where to send completion message
)

task_id = task_result['task_id']

# Continue with other work...

# Later, check status
status = mcp__orchestrator__check_async_task(task_id=task_id)
if status['status'] == 'completed':
    print(status['result'])
```

---

## Parallel Agent Patterns

### Pattern 1: Independent Parallel Work

Spawn multiple agents for independent tasks:

```python
# Spawn 3 agents in parallel
tasks = [
    ("security-sonnet", "Scan src/ for security issues"),
    ("reviewer-sonnet", "Review src/ for code quality"),
    ("tester-haiku", "Add unit tests for src/auth.ts")
]

task_ids = []
for agent_type, task in tasks:
    result = mcp__orchestrator__spawn_agent_async(
        agent_type=agent_type,
        task=task,
        workspace_dir="C:/Projects/myproject"
    )
    task_ids.append(result['task_id'])

# Wait for all to complete
for task_id in task_ids:
    status = mcp__orchestrator__check_async_task(task_id=task_id)
    # Process results...
```

### Pattern 2: Coordinator + Workers

Use coordinator agent to spawn and manage sub-agents:

```python
# Coordinator spawns multiple researchers
result = mcp__orchestrator__spawn_agent(
    agent_type="research-coordinator-sonnet",
    task="""
    Research modern authentication patterns:
    1. JWT vs session tokens
    2. OAuth 2.0 providers
    3. Refresh token strategies

    Spawn parallel researcher agents and compile findings.
    """,
    workspace_dir="C:/Projects/myproject"
)
```

---

## Agent Selection Guide

### When to Use Each Agent

**coder-haiku**:
- Simple features (< 100 lines)
- Refactoring existing code
- Bug fixes
- Adding logging/comments

**python-coder-haiku**:
- Python scripts
- Database migrations
- MCP server development
- Testing code in Python REPL

**lightweight-haiku**:
- File operations (read/write/edit)
- Code formatting
- Single function additions
- **NOT for**: Complex implementations

**reviewer-sonnet**:
- Pre-commit code review
- Architecture analysis
- Performance review
- LLM-as-Judge validation

**security-sonnet**:
- Security vulnerability scanning
- OWASP Top 10 checks
- Sensitive data detection
- Auth/authorization review

**analyst-sonnet**:
- Technical research
- Documentation writing
- Architecture specs
- Migration planning

**architect-opus**:
- Complex system design
- Multi-service integration
- Performance optimization strategy
- **High cost** - use sparingly

**tester-haiku**:
- Unit tests
- Integration tests
- Test fixtures
- Mock/stub creation

**web-tester-haiku**:
- E2E web tests (Playwright)
- Form validation
- Navigation tests
- Screenshot capture

---

## Timeout Management

### Default Timeouts

Agents use timeouts from `agent_specs.json`. Override only if needed:

```python
# Override timeout (use carefully!)
result = mcp__orchestrator__spawn_agent(
    agent_type="coder-haiku",
    task="Complex refactoring task",
    workspace_dir="C:/Projects/myproject",
    timeout=1800  # 30 minutes (default is 1200s)
)
```

**Warning**: Timeout overrides <50% or >200% of spec will log warnings

---

## Monitoring Agents

### Check Agent Stats

```python
# Get usage statistics
stats = mcp__orchestrator__get_agent_stats(
    agent_type="coder-haiku",
    days=7  # Last 7 days
)

print(f"Total spawns: {stats['total_sessions']}")
print(f"Success rate: {stats['success_rate']}%")
print(f"Avg execution: {stats['avg_execution_time']}s")
print(f"Total cost: ${stats['total_cost']}")
```

### Query Agent Sessions

```sql
-- Recent agent spawns
SELECT
    agent_type,
    task_description,
    success,
    execution_time_seconds,
    estimated_cost_usd
FROM claude.agent_sessions
WHERE spawned_at > NOW() - INTERVAL '7 days'
ORDER BY spawned_at DESC
LIMIT 20;
```

---

## Cost Optimization

### Choose Right Agent for Task

```
Simple task: lightweight-haiku ($0.01) ✅
NOT: architect-opus ($0.825) ❌
```

### Prefer Haiku for Batch Work

```python
# BAD: Spawn Opus for 10 simple tasks = $8.25
for task in simple_tasks:
    spawn_agent("architect-opus", task)  # WASTEFUL!

# GOOD: Spawn Haiku for batch = $0.35
all_tasks = "\n".join(simple_tasks)
spawn_agent("coder-haiku", f"Complete these tasks:\n{all_tasks}")
```

### Use Coordinators Wisely

```
Research coordinator ($0.35) + 3 analysts ($0.90) = $1.25
vs
1 researcher-opus ($0.73) with 83% failure rate ❌
```

---

## Common Queries

```sql
-- Agent success rates
SELECT
    agent_type,
    COUNT(*) as spawns,
    ROUND(AVG(CASE WHEN success THEN 100 ELSE 0 END), 1) as success_pct,
    ROUND(AVG(execution_time_seconds), 2) as avg_exec_sec
FROM claude.agent_sessions
WHERE completed_at IS NOT NULL
GROUP BY agent_type
ORDER BY spawns DESC;

-- Costly failed agents
SELECT
    agent_type,
    COUNT(*) as failures,
    SUM(estimated_cost_usd) as wasted_cost
FROM claude.agent_sessions
WHERE success = false
GROUP BY agent_type
ORDER BY wasted_cost DESC;
```

---

## Related Skills

- `session-management` - Linking agents to parent sessions
- `messaging` - Inter-agent communication
- `database-operations` - Querying agent stats

---

## Key Gotchas

### 1. Wrong Agent for Task

**Problem**: Using architect-opus ($0.83) for simple refactoring

**Solution**: Match agent to task complexity

### 2. Not Tracking Parent Sessions

**Problem**: Can't trace which session spawned which agents

**Solution**: Always set `parent_session_id` in agent_sessions

### 3. Ignoring Failure Patterns

**Problem**: Repeatedly using agents with <60% success rate

**Solution**: Monitor stats, switch agents or adjust tasks

### 4. Timeout Overrides

**Problem**: Hardcoding low timeouts causes premature failures

**Solution**: Use agent spec timeouts, override only when necessary

---

**Version**: 1.0
**Created**: 2025-12-26
**Location**: .claude/skills/agentic-orchestration/skill.md
