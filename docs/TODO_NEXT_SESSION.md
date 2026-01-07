# Next Session TODO

**Last Updated**: 2026-01-07
**Last Session**: Implemented session handoff improvements - RAG-style context injection

---

## Completed This Session

- [x] Verified agent status UPSERT fix works
- [x] Verified all coding standards exist in DB
- [x] **Session Handoff Research** - Analyzed Anthropic's best practices, current implementation
- [x] **Option B Implemented** - RAG hook now detects session keywords and injects context from DB
- [x] **Option A Implemented** - /session-resume command updated to use database queries
- [x] Added SESSION_KEYWORDS list to rag_query_hook.py
- [x] Added get_session_context() function to query todos, session_state, last session
- [x] Updated main() to combine session context with RAG results

---

## Priority 1: Test Session Handoff (NEEDS RESTART)

- [ ] Restart Claude Code to reload rag_query_hook.py
- [ ] Test: Ask "where was I working on?" - should inject session context
- [ ] Test: Ask "what todos do I have?" - should inject session context
- [ ] Test: Run /session-resume - should query database

---

## Priority 2: Clean Up Stale Data

- [ ] Delete deprecated session_state.todo_list content (stale Dec 31)
- [ ] Archive old todos (created_at > 30 days, status=pending)

---

## Priority 4: Expand Native Instructions

- [ ] Add rust.instructions.md to ~/.claude/instructions/
- [ ] Add azure.instructions.md (Bicep, Functions, Logic Apps)
- [ ] Add docker.instructions.md

---

## Backlog

- [ ] Implement forbidden_patterns in standards_validator.py
- [ ] Implement required_patterns checks
- [ ] Review other projects for duplicate session commands

---

## Key Learnings (This Session)

1. **RAG injection pattern works** - UserPromptSubmit hook → additionalContext is the proven approach
2. **Anthropic recommends "progressive context loading"** - Load on demand, not pre-load everything
3. **Database is source of truth** - claude.todos, session_state, sessions
4. **Session keywords trigger context** - "where was I", "what's next", "resume", etc.

---

## Files Modified This Session

**Session Handoff Implementation:**
- `scripts/rag_query_hook.py` - Added SESSION_KEYWORDS, detect_session_keywords(), get_session_context()
- `.claude/commands/session-resume.md` - Changed to use database queries via MCP

**Previous (UPSERT fix):**
- `mcp-servers/orchestrator/db_logger.py` - Changed finalize_agent_status() to use UPSERT
- `mcp-servers/orchestrator/orchestrator_prototype.py` - Pass agent_type to finalize_agent_status()

---

## How Session Handoff Works Now

```
User asks session question (e.g., "where was I?")
    ↓
UserPromptSubmit hook (rag_query_hook.py)
    ↓
detect_session_keywords() matches keyword
    ↓
get_session_context() queries:
  - claude.todos (active items)
  - claude.session_state (focus, next_steps)
  - claude.sessions (last session summary)
  - claude.messages (pending count)
    ↓
Session context + RAG results → additionalContext
    ↓
Claude sees full context automatically
```

**Keywords that trigger**: "where was i", "what's next", "resume", "last session",
"todos", "pending tasks", "continue from", "session context", etc.

---

## If Tests Fail

1. Check `~/.claude/hooks.log` for errors
2. Verify hook is registered in `.claude/settings.local.json` under UserPromptSubmit
3. Run `python -m py_compile scripts/rag_query_hook.py` to check syntax
4. Query database directly to verify data exists:
   ```sql
   SELECT * FROM claude.todos WHERE project_id = '20b5627c-e72c-4501-8537-95b559731b59'
   AND is_deleted = false LIMIT 5;
   ```

---

**Version**: 13.0
**Created**: 2026-01-02
**Updated**: 2026-01-07
**Location**: docs/TODO_NEXT_SESSION.md
