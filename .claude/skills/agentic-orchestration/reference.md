# Agentic Orchestration Skill — Detailed Reference

## Native Agents — Full Examples

### Basic Delegation

```
Task(
    subagent_type="coder-haiku",
    description="Implement auth middleware",
    prompt="Create JWT auth middleware in src/middleware/auth.ts following existing patterns."
)
```

### Parallel Delegation

```
# These run in parallel when called in the same message:
Task(subagent_type="reviewer-sonnet", prompt="Review src/auth/ changes")
Task(subagent_type="tester-haiku", prompt="Add tests for src/auth/middleware.ts")
Task(subagent_type="security-sonnet", prompt="Scan src/auth/ for vulnerabilities")
```

### Background Agents

```
Task(
    subagent_type="analyst-sonnet",
    description="Research OAuth patterns",
    prompt="Research modern OAuth 2.0 patterns...",
    run_in_background=true
)
# Returns output_file path - check later with Read tool
```

### Model Override

```
Task(
    subagent_type="general-purpose",
    model="haiku",  # Override to cheaper model
    prompt="Simple file organization task"
)
```

---

## Context-Safe Delegation (CRITICAL)

**Problem**: Agent results flood parent context, causing premature compaction.

**Rule**: Agents write detailed results to files or session notes. Parent gets 1-line summary only.

### How to Instruct Agents

Always include in agent prompts:

```
"Write your detailed findings to store_session_notes(content, 'findings').
Return ONLY a 1-line summary to me (the parent). Do NOT return full analysis."
```

For code agents:

```
"Write the code changes directly to files. Return ONLY a 1-line summary
of what you changed (e.g., 'Updated 3 files: auth.ts, middleware.ts, types.ts')."
```

### After Agent Completes

1. Read the 1-line summary (already in your context)
2. Only read detailed results via `get_session_notes()` or `Read` tool if needed
3. `save_checkpoint()` after each agent batch

---

## Coordinator Patterns

### Pattern 1: Plan + Delegate

```
1. I (Opus) analyze the task and create build tasks
2. Spawn coder-haiku/sonnet per task
3. Spawn reviewer-sonnet before commit
```

### Pattern 2: Research Coordinator

```
Task(subagent_type="analyst-sonnet", prompt="Research topic A. Write to store_session_notes(). Return 1-line summary.")
Task(subagent_type="analyst-sonnet", prompt="Research topic B. Write to store_session_notes(). Return 1-line summary.")
# Both run in parallel, read notes only if needed
```

### Pattern 3: Quality Gate

```
# After writing code:
Task(subagent_type="reviewer-sonnet", prompt="Review changes. Return pass/fail + 1-line summary.")
Task(subagent_type="security-sonnet", prompt="Security scan. Return pass/fail + 1-line summary.")
Task(subagent_type="tester-haiku", prompt="Add tests")
# Only commit if all pass
```

---

## Monitoring

```sql
-- Agent success rates
SELECT agent_type, COUNT(*) as spawns,
    ROUND(AVG(CASE WHEN success THEN 100 ELSE 0 END), 1) as success_pct
FROM claude.agent_sessions
WHERE completed_at IS NOT NULL
GROUP BY agent_type ORDER BY spawns DESC;
```
