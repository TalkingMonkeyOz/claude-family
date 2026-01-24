---
title: Core Protocol Injection
created: 2026-01-21
updated: 2026-01-21
tags: [rag, hooks, context-injection, input-processing]
category: system
status: active
---

# Core Protocol Injection

## Overview

Static text injection on **every user prompt** to ensure Claude always has the input processing workflow fresh in context. Unlike RAG (semantic search), this is unconditional - no keyword matching required.

## The Protocol

```
## Input Processing Protocol
When receiving a task request:
1. **ANALYZE** - Read entire message before acting
2. **EXTRACT** - Identify ALL tasks (explicit + implied) → TodoWrite immediately
3. **VERIFY** - Don't guess, don't assume. Check the database, vault, or codebase first.
4. **EXECUTE** - Work through each todo sequentially, marking in_progress
5. **COMPLETE** - Mark each todo done immediately after finishing
```

## Why This Exists

| Problem | Solution |
|---------|----------|
| CLAUDE.md loaded once at session start | Protocol injected every prompt |
| Long conversations lose context | Always first in injection order |
| Semantic search unreliable for meta-instructions | Static text, no matching needed |
| ~60 tokens | Negligible overhead |

## Implementation

**File**: `scripts/rag_query_hook.py`

**Constant** (top of file):
```python
CORE_PROTOCOL = """
## Input Processing Protocol
When receiving a task request:
1. **ANALYZE** - Read entire message before acting
2. **EXTRACT** - Identify ALL tasks (explicit + implied) → TodoWrite immediately
3. **EXECUTE** - Work through each todo sequentially, marking in_progress
4. **COMPLETE** - Mark each todo done immediately after finishing
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

## Modifying the Protocol

To change the injected protocol:

1. Edit `CORE_PROTOCOL` constant in `scripts/rag_query_hook.py`
2. Keep it short (~60-100 tokens max)
3. No restart needed - takes effect on next prompt

## Related

- [[RAG Usage Guide]] - Full RAG system documentation
- [[PreToolUse Context Injection]] - Tool-specific context injection
- [[Claude Code Hooks]] - Hook system overview

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

**Version**: 1.1
**Created**: 2026-01-21
**Updated**: 2026-01-21
**Location**: knowledge-vault/20-Domains/Core Protocol Injection.md
