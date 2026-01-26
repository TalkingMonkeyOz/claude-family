---
title: Core Protocol Injection
created: 2026-01-21
updated: 2026-01-24
tags: [rag, hooks, context-injection, input-processing, tasks]
category: system
status: active
---

# Core Protocol Injection

## Overview

Static text injection on **every user prompt** to ensure Claude always has the input processing workflow fresh in context. Unlike RAG (semantic search), this is unconditional - no keyword matching required.

## The Protocol

```
## ⛔ STOP - READ THIS BEFORE RESPONDING

**SELF-CHECK (answer before ANY response):**
→ Does user's message contain a request/task/question requiring action?
→ If YES: Have I called TaskCreate for EACH action I will take?
→ If NO tasks created: **STOP. Create tasks FIRST. Then respond.**

---

## Task Discipline (NON-NEGOTIABLE)

**Every file edit, DB write, search, or command = 1 task.**

User: "update the vault"
  ↓
TaskCreate: "Update Database Integration Guide"
TaskCreate: "Update RAG Usage Guide"
  ↓
TaskUpdate(in_progress) → Execute → TaskUpdate(completed)
  ↓
Next task...

**THE RULE:** No tool calls until TaskCreate is done. Period.

---

## Working Memory (Session Facts = Your Notepad)

Long conversations compress. Things get lost. **Use session facts as your notepad.**

| When This Happens | Do This |
|-------------------|---------|
| User gives credential/key | store_session_fact("api_key", "...", "credential", is_sensitive=True) |
| User tells you config/endpoint | store_session_fact("api_url", "...", "endpoint") |
| A decision is made | store_session_fact("auth_approach", "JWT with refresh", "decision") |
| You discover something important | store_session_fact("finding_X", "...", "note") |
| Multi-step task in progress | store_session_fact("task_progress", "Done: A,B. Next: C", "note") |

**Valid types:** credential, config, endpoint, decision, note, data, reference

**Anytime:** Run list_session_facts() to see your notepad.
**Session feels long?** Check your notepad for what you stored earlier.

---

## Quick Reference

| User says... | I do FIRST |
|--------------|------------|
| "fix X" | TaskCreate for each fix |
| "check Y" | TaskCreate: "Check Y" |
| "update Z" | TaskCreate for each file |
| Short question | Answer directly (no task needed) |

---

## Other Rules
- **NEVER guess** - Verify files/tables exist before claiming they do/don't
- **Large data?** - Use python-repl to keep data out of context
```

## Tasks vs Todos vs Session Facts

| Concept | Scope | Tool | Persistence | Use For |
|---------|-------|------|-------------|---------|
| **Task** | Session | TaskCreate/TaskUpdate/TaskList | In-memory only | Tracking current work |
| **Todo** | Cross-session | TodoWrite → claude.todos | Database | Work that spans sessions |
| **Session Fact** | Session+ | store_session_fact/list_session_facts | Database | Notepad - things told to you, findings, decisions |

**Lifecycle:**
1. Session start: Load Todos from database
2. User gives work: Create Tasks (session-scoped)
3. User tells you important info: Store as Session Fact (your notepad)
4. Work through Tasks: Mark in_progress → completed
5. Make discoveries/decisions: Store as Session Facts
6. Session end: Incomplete Tasks → Todos (persist to DB)
7. Next session: Todos reload, Session Facts recoverable via recall_previous_session_facts()

## Why This Exists

| Problem | Solution |
|---------|----------|
| CLAUDE.md loaded once at session start | Protocol injected every prompt |
| Long conversations lose context | Always first in injection order |
| Semantic search unreliable for meta-instructions | Static text, no matching needed |
| ~110 tokens | Negligible overhead |

## Implementation

**File**: `scripts/rag_query_hook.py`

**Constant** (top of file):
```python
CORE_PROTOCOL = """
## Input Processing Protocol

**MANDATORY RULES (non-negotiable):**
1. **NEVER guess** - Do not assume files, tables, or features exist. VERIFY first by reading/querying.
2. **NEVER skip TaskCreate** - Every discrete action (file edit, DB write, command) MUST have a task.
3. **ALWAYS mark status** - TaskUpdate(in_progress) BEFORE starting. TaskUpdate(completed) IMMEDIATELY after.

**WORKFLOW:**
1. ANALYZE - Read the ENTIRE user message first
2. EXTRACT - TaskCreate for EACH action you will perform (no exceptions)
3. VERIFY - Query/read to confirm existence BEFORE claiming "X exists" or "X doesn't exist"
4. EXECUTE - One task at a time, status=in_progress first
5. COMPLETE - TaskUpdate(completed) the instant you finish each action

**SELF-CHECK before responding:** Did I create tasks for ALL actions I'm about to take?

Note: Tasks are session-scoped. At /session-end, incomplete tasks become persistent Todos.
"""
```

**Injection** (in `main()`):
```python
combined_context_parts = []
# ALWAYS inject core protocol FIRST
combined_context_parts.append(CORE_PROTOCOL)
# Then session context, knowledge, RAG...
```

## Context Injection Order

| Order | Content | Condition |
|-------|---------|-----------|
| 1 | **Core Protocol** | **ALWAYS** |
| 2 | Session Context | If session keywords detected |
| 3 | Knowledge Recall | If semantic match ≥ 0.45 |
| 4 | Vault RAG | If semantic match ≥ 0.30 |
| 5 | **Periodic Reminders** | At intervals (see below) |

## Periodic Reminders

The RAG hook also handles interval-based reminders (merged from stop_hook_enforcer.py):

| Reminder | Interval | Purpose |
|----------|----------|---------|
| Inbox Check | Every 15 prompts | Check for messages from other Claudes |
| Vault Refresh | Every 25 prompts | Re-read CLAUDE.md if unsure |
| Git Check | Every 10 prompts | Check for uncommitted changes |

**State File**: `~/.claude/state/rag_hook_state.json`

This consolidates all context injection into a single UserPromptSubmit hook, eliminating the need for a separate Stop hook.

## Modifying the Protocol

To change the injected protocol:

1. Edit `CORE_PROTOCOL` constant in `scripts/rag_query_hook.py`
2. Keep it focused (~100-150 tokens max)
3. No restart needed - takes effect on next prompt

## Related

- [[Tasks vs Todos Lifecycle]] - Full lifecycle documentation
- [[RAG Usage Guide]] - Full RAG system documentation
- [[PreToolUse Context Injection]] - Tool-specific context injection
- [[Claude Code Hooks]] - Hook system overview
- [[Session Lifecycle - Session End]] - Session end workflow

---

## Deployment

**Global** (all projects): `~/.claude/settings.json`
```json
"UserPromptSubmit": [
  {
    "hooks": [{
      "type": "command",
      "command": "python \"C:/Projects/claude-family/scripts/rag_query_hook.py\"",
      "timeout": 10,
      "description": "Core protocol + RAG injection on every user prompt"
    }]
  }
]
```

**Note**: New Claude sessions on ANY project will receive the core protocol injection. Existing sessions need restart to pick up changes.

---

**Version**: 3.1 (Added Working Memory section - session facts as notepad)
**Created**: 2026-01-21
**Updated**: 2026-01-26
**Location**: knowledge-vault/20-Domains/Core Protocol Injection.md
