---
projects:
- claude-family
- Project-Metis
tags:
- audit
- hooks
- enforcement
synced: false
---

# Audit: Hook System (Event-Driven Behavior Layer)

**Parent**: [[claude-family-systems-audit]]
**Raw data**: `docs/audit/hooks_audit.md` (28K chars)

---

## What It Is

Python scripts intercepting Claude Code lifecycle events to inject context, enforce rules, and persist state. Configured in `.claude/settings.local.json`. Each hook receives JSON on stdin, returns JSON on stdout.

## How It Works

```
Claude Code Event → settings.local.json matcher → Python script
  ↓ stdin (JSON)                                    ↓
  Hook reads event, queries DB, assembles context    ↓
  ↓ stdout (JSON)                                   ↓
  additionalContext / systemMessage / allow/deny  → Claude sees result
```

Events: SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, SubagentStart, SessionEnd.

---

## Hook Inventory

### Working Hooks (8)

| Hook | Event | Purpose | DB Tables | BPMN |
|------|-------|---------|-----------|------|
| `session_startup_hook_enhanced.py` | SessionStart (once) | Log session, health check, stale todo archive, memory consolidation | sessions, todos, projects, knowledge | session_lifecycle.bpmn |
| `rag_query_hook.py` | UserPromptSubmit | RAG retrieval, core protocol, context health, session facts, failure surfacing | knowledge, sessions, session_facts, feedback | rag_pipeline.bpmn |
| `task_discipline_hook.py` | PreToolUse(Write/Edit/Task/Bash) | Block writing without tasks; context health gate | build_tasks, features, session_state | hook_chain.bpmn |
| `context_injector_hook.py` | PreToolUse(Write/Edit) | Inject coding standards from DB | context_rules, coding_standards | hook_chain.bpmn |
| `standards_validator.py` | PreToolUse(Write/Edit) | Validate content against standards | coding_standards | content_validation.bpmn |
| `todo_sync_hook.py` | PostToolUse(TodoWrite) | Sync todos to DB (75% fuzzy match) | todos | todo_sync.bpmn |
| `task_sync_hook.py` | PostToolUse(TaskCreate/Update) | Sync tasks to DB, bridge to build_tasks, audit log | todos, build_tasks, audit_log | task_sync.bpmn |
| `mcp_usage_logger.py` | PostToolUse(all) | Log MCP tool usage (fast-path skip for built-ins) | mcp_usage | mcp_usage_logging.bpmn |

### Broken Hooks (3)

| Hook | Event | Issue |
|------|-------|-------|
| `validate_db_write.py` | PreToolUse(SQL) | Expects SQL as CLI args; gets hook JSON on stdin. Fails open silently. |
| `validate_phase.py` | PreToolUse(SQL) | Same input-parsing mismatch. No enforcement. |
| `validate_parent_links.py` | PreToolUse(SQL) | Same issue. Dead code providing zero orphan prevention. |

### Partially Working (3)

| Hook | Event | Issue |
|------|-------|-------|
| `subagent_start_hook.py` | SubagentStart | Empty `subagent_id` from Claude Code → most spawns not logged |
| `precompact_hook.py` | PreCompact | Works but limits session facts to 5 (rest lost from injected context) |
| `session_end_hook.py` | SessionEnd | Ordering bug: queries for facts before session marked closed → current-session facts never promoted |

---

## Significant Issues

1. **3 plugin validators are dead code** — Vestigial from older architecture where SQL was passed as arguments. Current hook format passes JSON on stdin.

2. **session_end fact promotion ordering bug** — `consolidate_session_facts` runs `WHERE session_end IS NOT NULL` but `session_end` is set AFTER this function runs. Current-session facts are never caught.

3. **No aggregate token cap on RAG injection** — 7 context blocks (protocol, facts, knowledge, vault, schema, skills, health) can all fire simultaneously. No ceiling on total injection.

4. **52 orphaned session_end fallback entries** — JSONL fallback written when DB unavailable, but no replay mechanism. Sessions stay orphaned forever.

5. **Windows-only file locking** — `import msvcrt` in task_discipline and task_sync. No cross-platform fallback.

6. **RAG hook uses cwd basename, not git root** for project name in checkpoint check — inconsistent with other hooks.

## Effectiveness Assessment

The hook system is **Claude Family's most innovative component**. It proves LLM behavior can be meaningfully shaped through context injection (2,000-6,000 tokens/prompt) and tool gating. The task discipline hook alone prevents untargeted code generation. The RAG hook provides continuity across sessions.

**For Metis**: Preserve the hook-based architecture pattern but implement via a proper event bus (not stdin/stdout pipes). Add health monitoring, cross-platform support, and configurable token budgets.

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-audit-hooks.md
