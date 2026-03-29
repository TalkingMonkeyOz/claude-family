---
name: agentic-orchestration
description: Spawn and coordinate Claude agents for parallel work
model: opus
context: fork
allowed-tools:
  - Read
  - Task
  - mcp__project-tools__*
skill-inheritance:
  - messaging
---

# Agentic Orchestration Skill

**Status**: Active

---

## Overview

Spawn and coordinate Claude agents using the native `Task` tool with `.claude/agents/*.md` definitions.

**Detailed reference**: See [reference.md](./reference.md) for full examples, context-safe patterns, and coordinator recipes.

---

## When to Delegate

- Tasks touching 3+ files
- Need parallel execution (review + test + security)
- Specialized expertise needed (security, architecture)
- Long-running research tasks

---

## Agent Selection Table

| Agent | Model | Use For | Cost |
|-------|-------|---------|------|
| **lightweight-haiku** | Haiku | Simple file ops | $0.01 |
| **coder-haiku** | Haiku | Code writing (1-3 files) | $0.035 |
| **python-coder-haiku** | Haiku | Python + DB + REPL | $0.045 |
| **tester-haiku** | Haiku | Unit/integration tests | $0.052 |
| **web-tester-haiku** | Haiku | E2E Playwright tests | $0.05 |
| **reviewer-sonnet** | Sonnet | Code review (read-only) | $0.105 |
| **mui-coder-sonnet** | Sonnet | React/MUI UI | $0.12 |
| **security-sonnet** | Sonnet | Security audits (read-only) | $0.24 |
| **analyst-sonnet** | Sonnet | Research, docs | $0.30 |
| **architect-opus** | Opus | Architecture design | $0.825 |
| **general-purpose** | (caller's) | Fallback / model override | varies |

**Cost rule**: Haiku ($0.01-0.05) < Sonnet ($0.10-0.30) < Opus ($0.80+)

**Source of truth**: `claude.agent_definitions` table.

---

## Quick Usage

```
# Basic delegation
Task(subagent_type="coder-haiku", prompt="Implement X in src/file.ts")

# Parallel (call multiple in one message)
Task(subagent_type="reviewer-sonnet", prompt="Review changes")
Task(subagent_type="tester-haiku", prompt="Add tests")

# Background
Task(subagent_type="analyst-sonnet", prompt="Research...", run_in_background=true)
```

---

## Context-Safe Delegation (CRITICAL)

Agents write detailed results to files/notes. Parent gets 1-line summary only.

Always instruct agents: `"Return ONLY a 1-line summary. Write details to store_session_notes()."`

---

## Key Gotchas

1. **Wrong agent for task** — using architect-opus ($0.83) for simple refactoring
2. **Spawned agents have hooks disabled** — no RAG, no auto-logging in sub-agents
3. **Agent definitions are DB-driven** — edit `claude.agent_definitions`, run `generate_agent_files.py`
4. **Context flooding** — always use context-safe delegation pattern

---

## Related Skills

- `messaging` - Agent completion notifications
- `code-review` - Quality gate agents

---

**Version**: 3.0 (Progressive disclosure: split to SKILL.md overview + reference.md detail)
**Created**: 2025-12-26
**Updated**: 2026-03-29
**Location**: .claude/skills/agentic-orchestration/SKILL.md
