---
projects:
  - claude-family
tags:
  - agent
  - orchestrator
  - gotcha
  - timeout
synced: false
---

# Agent Timeout Configuration

**Discovered**: 2026-01-11
**Context**: mui-coder-sonnet timed out at 300s despite recommended_timeout being 900s

---

## The Problem

When spawning agents, always use the `recommended_timeout_seconds` from agent_specs.json.

**Bad**: Hardcoding or guessing timeouts
```typescript
spawn_agent(agent_type="mui-coder-sonnet", timeout=300)  // WRONG
```

**Good**: Use recommended timeout or higher
```typescript
spawn_agent(agent_type="mui-coder-sonnet", timeout=900)  // Correct
```

---

## Additional Overhead Factors

1. **MCP startup time**: MCPs using `npx -y @package@latest` download on first run (~30-60s)
2. **Complex tasks**: UI redesigns, multi-file changes need more time
3. **Extended thinking**: Sonnet models with interleaved thinking take longer

---

## Agent Progress Tracking

Agents SHOULD call `update_agent_status` every ~5 tool calls to:
- Report progress percentage
- Update current activity
- Allow boss to monitor/abort if stuck

**Problem identified**: The timed out agent had `tool_call_count: 0` and never updated status.

---

## Recommended Timeouts by Agent Type

| Agent | Timeout (s) | Notes |
|-------|-------------|-------|
| coder-haiku | 1200 | Fast but may need iteration |
| coder-sonnet | 900 | Complex reasoning |
| mui-coder-sonnet | 900 | MUI MCP startup adds ~60s |
| reviewer-sonnet | 600 | Review is faster |
| tester-haiku | 600 | Test execution time varies |
| designer-sonnet | 600 | Design tasks |

---

## Prevention Checklist

1. Check `agent_specs.json` for `recommended_timeout_seconds` before spawning
2. Add 60-120s buffer for first-run MCP downloads
3. Monitor `claude.agent_status` for progress updates
4. Check `claude.agent_sessions` for timeout patterns

---

**Version**: 1.0
**Created**: 2026-01-11
**Updated**: 2026-01-11
**Location**: knowledge-vault/30-Patterns/gotchas/Agent Timeout Configuration.md
