# Audit: Hooks System

**Part of**: [Infrastructure Audit Report](../INFRASTRUCTURE_AUDIT_REPORT.md)

---

## Registered Hooks (11 total)

| Hook Type | Script | Status |
|-----------|--------|--------|
| SessionStart | session_startup_hook.py | ✅ Working |
| UserPromptSubmit | rag_query_hook.py | ✅ Working |
| PreToolUse (Write) | standards_validator.py | ✅ Working |
| PreToolUse (Edit) | standards_validator.py | ✅ Working |
| PostToolUse (mcp__*) | mcp_usage_logger.py | ✅ Working |
| PostToolUse (TodoWrite) | todo_sync_hook.py | ⚠️ Race condition |
| Stop | stop_hook_enforcer.py | ✅ Working |
| PreCompact (manual) | precompact_hook.py | ✅ Working |
| PreCompact (auto) | precompact_hook.py | ✅ Working |
| SessionEnd | prompt hook | ✅ Working |

---

## Script Analysis

### session_startup_hook.py (901 lines)
- Creates session in `claude.sessions`
- Loads todos from `claude.todos`
- Checks messages, reminders, scheduled jobs
- Exports SESSION_ID, PROJECT_ID env vars
- Output: JSON with `additionalContext`

### rag_query_hook.py (335 lines)
- Queries `claude.vault_embeddings` on every prompt
- Similarity threshold: 0.30
- Logs to `claude.rag_usage_log`
- Silent injection (no visible output)

### standards_validator.py (401 lines)
- Validates Write/Edit against `claude.coding_standards`
- Block-and-correct pattern
- Output: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny"}}`

### todo_sync_hook.py (497 lines)
- Syncs TodoWrite to `claude.todos`
- Fuzzy matching: 75% threshold
- Does NOT auto-delete (by design)
- ⚠️ Potential race condition

---

## Best Practices Compliance

| Requirement | Status |
|-------------|--------|
| Valid hook types | ✅ |
| JSON output format | ✅ |
| Exit code 0 for JSON | ✅ |
| hookEventName field | ✅ |
| Hooks in settings.local.json | ✅ |

---

**Version**: 1.0
**Created**: 2026-01-03
**Location**: docs/audit/AUDIT_HOOKS.md
