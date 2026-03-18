**MANDATORY END-OF-SESSION CHECKLIST**

When the user says to end the session (or you invoke /session-end), follow this process:

---

## Step 1: Review Open Work (No Loose Ends)

Before ending, check for unfinished business:

1. Run `TaskList` — are any tasks still in_progress? Complete or create follow-up tasks.
2. Run `get_unactioned_messages(project_name)` — any task_requests, questions, or handoffs not actioned or deferred? Address or defer with reason.
3. Check for "TODO" or "we should do X later" in your conversation — each needs a tracking item (`TaskCreate` or `create_feedback`).
4. Any deferred decisions? File them.

**Rule**: No loose ends. Every piece of deferred work becomes a tracked item. Every message gets a disposition.

---

## Step 2: Capture Cross-Session Knowledge

Review what you learned this session. For each significant finding:

- **Reusable pattern/gotcha/decision?** → `remember(content, memory_type)` (min 80 chars, include why + how to apply)
- **Component working notes?** → `stash(component, title, content)` if not already stashed during session

Skip if nothing new was learned — don't force it.

---

## Step 3: Prepare Summary

Gather these inputs by reviewing your conversation:

- **summary**: 1-2 sentence description of what was accomplished
- **tasks_completed**: List of completed task descriptions
- **next_steps**: What should the next session prioritize?
- **learnings**: Key insights worth preserving (these get embedded as mid-tier knowledge automatically)

---

## Step 4: Call end_session()

Make ONE call with everything gathered:

```
end_session(
    summary="What was accomplished this session",
    tasks_completed=["task 1", "task 2"],
    next_steps=["priority 1", "priority 2"],
    learnings=["insight 1", "insight 2"]
)
```

This single call handles ALL of the following automatically:
- Closes session record in `claude.sessions`
- Saves state to `claude.session_state` (next session picks up here)
- Auto-stashes a session handoff workfile
- Extracts conversation to `claude.conversations`
- Converts learnings to knowledge entries with Voyage AI embeddings
- Extracts insights from conversation
- Runs `consolidate_memories("session_end")` for short→mid tier promotion

**Do NOT** write raw SQL, call individual DB operations, or use retired tools. `end_session()` is the single entry point.

---

## What NOT To Do

- Don't use `claude_family.*` schema (legacy, removed)
- Don't use `mcp__memory__*` tools (memory MCP retired 2026-01)
- Don't write raw SQL to close sessions
- Don't skip the no-loose-ends check
- Don't skip the unactioned messages check
- Don't remember() task completions or progress — only patterns, gotchas, and decisions