---
title: Core Protocol Injection
created: 2026-01-21
updated: 2026-02-21
tags: [rag, hooks, context-injection, core-protocol, enforcement]
category: system
status: active
---

# Core Protocol Injection

## Overview

Static text injection on **every user prompt** to ensure Claude always has the core behavioral rules fresh in context. Unlike RAG (semantic search), this is unconditional - no keyword matching required. Injected via `rag_query_hook.py` on the `UserPromptSubmit` hook event.

## The Protocol (v3 - 2026-02-21)

```
STOP! Read the user's message fully.
1. DECOMPOSE: Create a task (TaskCreate) for EVERY distinct directive BEFORE
   acting on ANY of them. Include thinking/design tasks, not just code.
   No tool calls until all tasks exist.
2. NOTEPAD: Use store_session_fact() to save credentials, decisions, endpoints,
   findings, progress. These survive compaction. Use list_session_facts() to
   review. recall_session_fact() works across sessions. This is your memory.
3. DELEGATE: Tasks touching 3+ files = spawn an agent (coder-sonnet for complex,
   coder-haiku for simple). Don't bloat the main context. save_checkpoint()
   after completing each task.
4. BPMN-FIRST: For any process or system change - model it in BPMN first,
   write tests, then implement code. Never code without a model.
5. Verify before claiming - read files, query DB. Never guess.
6. Check MCP tools first - project-tools has 40+ tools.
```

## What Each Rule Does

| # | Name | Problem It Solves | Enforcement |
|---|------|-------------------|-------------|
| 1 | DECOMPOSE | Claude ignores multi-part messages, acts on first thing only | Forces task creation BEFORE any action |
| 2 | NOTEPAD | Context gets lost during compaction, Claude forgets decisions | Session facts persist in DB, survive compaction |
| 3 | DELEGATE | Claude bloats context doing everything itself, then crashes | Spawn agents for multi-file work, checkpoint progress |
| 4 | BPMN-FIRST | Code changes without process understanding cause regressions | Model the process, test it, then implement |
| 5 | Verify | Claude claims files/tables exist without checking | Forces read/query before assertions |
| 6 | MCP-first | Claude writes raw SQL instead of using MCP tools | 40+ project-tools available |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-01-21 | 4 rules: break into tasks, verify, MCP-first, session facts |
| v2 | 2026-02-20 | 5 rules: added DECOMPOSE (explicit), PRESERVE (user_intent), BUDGET (heavy/medium/light classification) |
| v3 | 2026-02-21 | 6 rules: rewrote DECOMPOSE (blocking), NOTEPAD (full scratchpad), DELEGATE (concrete 3+ files), added BPMN-FIRST |

## Session Facts (Rule 2 Detail)

Session facts are Claude's **working memory** - a notepad that survives context compaction.

| When This Happens | Do This |
|-------------------|---------|
| User gives credential/key | `store_session_fact("api_key", "...", "credential", is_sensitive=True)` |
| User tells you config/endpoint | `store_session_fact("api_url", "...", "endpoint")` |
| A decision is made | `store_session_fact("auth_approach", "JWT with refresh", "decision")` |
| You discover something important | `store_session_fact("finding_X", "...", "note")` |
| Multi-step task in progress | `store_session_fact("task_progress", "Done: A,B. Next: C", "note")` |

**Valid types:** credential, config, endpoint, decision, note, data, reference

**Functions:**
- `store_session_fact(key, value, type)` - save to notepad
- `list_session_facts()` - see your notepad
- `recall_session_fact(key)` - get a specific fact
- `recall_previous_session_facts()` - get facts from past sessions

## Tasks vs Todos vs Session Facts

| Concept | Scope | Tool | Persistence | Use For |
|---------|-------|------|-------------|---------|
| **Task** | Session | TaskCreate/TaskUpdate | In-memory only | Tracking current work |
| **Todo** | Cross-session | TodoWrite → claude.todos | Database | Work that spans sessions |
| **Session Fact** | Session+ | store/recall_session_fact | Database | Notepad - credentials, decisions, findings |

## Implementation

**File**: `scripts/rag_query_hook.py`

**Constant**: `CORE_PROTOCOL` (top of file, ~100 tokens)

**Injection** (in `main()`):
```python
combined_context_parts = []
combined_context_parts.append(CORE_PROTOCOL)  # ALWAYS first
# Then session facts, config warning, RAG, knowledge, skills...
```

## Context Injection Order

| Order | Content | Condition |
|-------|---------|-----------|
| 1 | **Core Protocol** | **ALWAYS** (~100 tokens) |
| 2 | **Session Facts** | **ALWAYS** (from notepad) |
| 3 | Config Warning | If config keywords detected |
| 4 | Skill Suggestions | If non-action prompt (FB138 re-enabled) |
| 5 | Knowledge Recall | If semantic match >= threshold |
| 6 | Vault RAG | If question/exploration prompt |

## Deployment

All projects receive this via `settings.local.json` which points to the shared hook:

```
scripts/rag_query_hook.py → UserPromptSubmit hook → every prompt, every project
```

Changes take effect on next prompt - no restart needed. The `start-claude.bat` launcher deploys settings from DB on every project launch.

## Modifying the Protocol

1. Edit `CORE_PROTOCOL` constant in `scripts/rag_query_hook.py`
2. Keep it focused (~100 tokens max)
3. Update this vault doc to match
4. Update `MEMORY.md` Core Protocol section
5. No restart needed - takes effect on next prompt

## Related

- [[RAG Usage Guide]] - Full RAG system documentation
- [[Claude Code Hooks]] - Hook system overview
- [[Session Lifecycle - Overview]] - Session lifecycle

---

**Version**: 4.0 (v3 protocol: 6 rules - DECOMPOSE, NOTEPAD, DELEGATE, BPMN-FIRST, verify, MCP-first)
**Created**: 2026-01-21
**Updated**: 2026-02-21
**Location**: knowledge-vault/20-Domains/Core Protocol Injection.md
