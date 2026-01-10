# Dynamic Agent Architecture Analysis

**Analysis Type**: ULTRATHINK | **Date**: 2026-01-10

---

## Tiered Agent System

| Tier | System | Use For | Cost |
|------|--------|---------|------|
| 1 | Task Tool | Quick subtasks (Explore, Bash) | Low |
| 2 | Orchestrator | Specialized work (coder, designer) | Medium |
| 3 | Multi-Agent | Complex coordination | High |

---

## Key Insight: Use recommend_agent First

```
mcp__orchestrator__recommend_agent(task="Review SQL for security")
→ Returns: security-sonnet
```

**Pattern**: Always let orchestrator decide the agent type.

---

## Selection Quick Reference

| Task | Agent |
|------|-------|
| Find files | Task:Explore |
| Run build | Task:Bash |
| Write code | coder-haiku |
| Security review | security-sonnet |
| UI design | designer-sonnet |
| Architecture | architect-opus |

---

## Recommendations

1. **Call recommend_agent before spawning** - Let system decide
2. **Default to haiku** - Escalate to sonnet only when needed
3. **Use spawn_agent_async for long tasks** - Don't block
4. **Document agent catalog** - What each agent does best

---

## Cost Tiers

| Model | Cost | Use For |
|-------|------|---------|
| Haiku | $ | Routine coding, testing |
| Sonnet | $$ | Complex analysis, reviews |
| Opus | $$$ | Architecture, research |

---

**Version**: 1.0
**Created**: 2026-01-10
**Location**: docs/findings/AGENT_ARCHITECTURE.md
