# Claude Code Coordinator Pattern

**Analysis Type**: Research | **Date**: 2026-01-10

---

## Can Claude Code Spawn Other Claude Instances?

**Yes**, via two mechanisms:

### 1. Task Tool (Built-in)

```
Task tool → subagent_type="general-purpose"
         → Up to 10 concurrent agents
         → Background execution available
```

### 2. Orchestrator MCP (spawn_agent)

```
spawn_agent → agent_type="coder-haiku"
           → Isolated Claude with custom MCPs
           → Returns when complete
```

---

## Hierarchy Limitation

**Maximum 2 levels**:
```
Primary Claude (you)
  └── Spawned Agent (can use tools)
        └── CANNOT spawn another agent
```

Subagents cannot spawn other subagents.

---

## Practical Patterns

### Pattern 1: Parallel Specialists
```
Primary spawns: [coder-haiku, tester-haiku, reviewer-sonnet]
All work concurrently, report back
```

### Pattern 2: Sequential Pipeline
```
Primary → coder → (waits) → tester → (waits) → reviewer
```

### Pattern 3: Async with Messaging
```
spawn_agent_async → returns task_id immediately
Agent sends message when done
Primary continues other work
```

---

## Quick Win: Headless Claude via Bash

```bash
claude --print "task description" --output-format json
```

Spawns CLI Claude, captures output. No MCP access.

---

## Recommendations

1. Use Task tool for quick exploration
2. Use Orchestrator for specialized work
3. Use async spawning for long tasks
4. Check spawn status: `get_spawn_status()`

---

**Version**: 1.0
**Created**: 2026-01-10
**Location**: docs/findings/COORDINATOR_PATTERN.md
