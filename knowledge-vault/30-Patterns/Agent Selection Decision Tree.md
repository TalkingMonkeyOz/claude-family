---
projects:
  - claude-family
tags:
  - orchestration
  - agents
  - delegation
  - patterns
synced: false
---

# Agent Selection Decision Tree

**Purpose**: Guide ALL Claudes on when and how to delegate work to specialized agents.

---

## Core Principle

> "Use premium models for thinking, cheap models for doing."
> - OpenAI Codex / Copilot pattern

**I am the orchestrator**, not the worker. My job is to:
1. Understand the task
2. Plan the approach
3. Delegate to specialists
4. Integrate results
5. Present to user

---

## Decision Flowchart

```
START: New Task Received
         ↓
┌─────────────────────────────────────────┐
│ Is this exploration/search?             │
│ (finding files, understanding code)     │
├─────────────────────────────────────────┤
│ YES → Task(Explore) or analyst-sonnet   │
│ NO  → Continue ↓                        │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Is this planning/architecture?          │
│ (task breakdown, design decisions)      │
├─────────────────────────────────────────┤
│ YES → Task(Plan) or planner-sonnet      │
│ NO  → Continue ↓                        │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ How many files affected?                │
├─────────────────────────────────────────┤
│ 1-2 files  → coder-haiku (simple)       │
│ 3-10 files → coder-sonnet               │
│ 10+ files  → Full orchestration         │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Does task require convention adherence? │
│ (version footers, strict standards)     │
├─────────────────────────────────────────┤
│ YES → coder-sonnet (better reasoning)   │
│ NO  → Continue to domain selection ↓    │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ What domain/technology?                 │
├─────────────────────────────────────────┤
│ Python + DB    → python-coder-haiku     │
│ React/MUI      → mui-coder-sonnet       │
│ WinForms       → winforms-coder-haiku   │
│ General simple → coder-haiku            │
│ General complex→ coder-sonnet           │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ BEFORE COMMIT (ALWAYS):                 │
│ → Spawn reviewer-sonnet                 │
│ → Spawn tester-haiku (if applicable)    │
└─────────────────────────────────────────┘
```

---

## Agent Tier Selection

| Tier | Models | Cost/Task | Best For |
|------|--------|-----------|----------|
| **Haiku** | coder-haiku, tester-haiku, git-haiku | $0.01-0.05 | Structured, simple tasks |
| **Sonnet** | **coder-sonnet**, reviewer-sonnet, planner-sonnet, mui-coder-sonnet | $0.10-0.35 | Complex reasoning, convention adherence |
| **Opus** | researcher-opus, architect-opus | $0.70-0.85 | Deep research, architecture |

**Rule**: Use the cheapest tier that can handle the task complexity.

**When Haiku Fails**: If coder-haiku misses conventions (version footers, tool usage rules), retry with coder-sonnet. Sonnet processes long context (~4000 tokens) better than Haiku.

---

## Task-to-Agent Mapping

| Task Type | Complexity | Recommended Agent |
|-----------|------------|-------------------|
| File operations | Simple | lightweight-haiku |
| Git operations | Simple | git-haiku |
| Documentation | Simple | doc-keeper-haiku |
| Unit tests | Simple | tester-haiku |
| Simple coding (<3 files) | Simple | coder-haiku |
| Complex coding (3+ files) | Medium | **coder-sonnet** |
| Convention-heavy coding | Medium | **coder-sonnet** |
| E2E tests | Medium | web-tester-haiku |
| Code review | Medium | reviewer-sonnet |
| Task planning | Medium | planner-sonnet |
| React/MUI code | Medium | mui-coder-sonnet |
| Research | Complex | analyst-sonnet |
| Deep research | Complex | researcher-opus |
| Architecture | Complex | architect-opus |

---

## Database-Driven Rules

The `claude.context_rules` table maps task keywords to agents:

```sql
SELECT name, task_keywords, agent_types
FROM claude.context_rules
WHERE active = true;
```

Example rules:
- `['review', 'pr', 'code quality']` → `reviewer-sonnet`
- `['test', 'pytest', 'jest']` → `tester-haiku, web-tester-haiku`
- `['typescript', 'react', 'tsx']` → `coder-haiku, mui-coder-sonnet`

---

## When NOT to Delegate

- **Trivial tasks** (single line fix, typo)
- **User explicitly asks ME to do it**
- **Sensitive operations** requiring human oversight
- **Context already built up** and delegation would lose it

---

## Anti-patterns to Avoid

| Anti-pattern | Better Approach |
|--------------|-----------------|
| Doing all exploration myself | Use Task(Explore) to preserve context |
| Using Haiku for complex multi-file changes | Use Sonnet for better reasoning |
| Skipping code review before commit | ALWAYS spawn reviewer-sonnet |
| Spawning Opus for simple tasks | Match agent tier to task complexity |

---

## Related Documents

- [[Orchestrator MCP]] - Agent spawning mechanics
- [[Structured Autonomy Workflow]] - 3-phase workflow pattern
- [[Family Rules]] - Coordination guidelines

---

**Version**: 1.1 (Added coder-sonnet for complex/convention-heavy tasks)
**Created**: 2026-01-10
**Updated**: 2026-01-10
**Location**: knowledge-vault/30-Patterns/Agent Selection Decision Tree.md
