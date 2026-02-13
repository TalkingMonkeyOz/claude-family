**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete ALL steps below in order.

---

## Step 1: Review Session Work

Analyze what was accomplished this session:

1. Check git status for uncommitted changes
2. Review your task list (TaskList) for completed/pending items
3. Identify key decisions, learnings, and blockers

## Step 2: Generate Summary

Write a concise session summary covering:
- **Completed**: What was accomplished (reference feature/task codes)
- **Pending**: Unfinished work, blockers
- **Decisions**: Key choices made and rationale
- **Next steps**: Clear continuation points for next session

## Step 3: Save to Database

Call `mcp__project-tools__end_session` with:
- `summary`: Your session summary (1-3 sentences)
- `next_steps`: Array of prioritized next actions
- `tasks_completed`: Array of completed task descriptions
- `learnings`: Array of key insights (optional)

This properly closes the session in `claude.sessions` with timestamp and summary.

## Step 4: Capture Knowledge (If Applicable)

If you discovered reusable patterns, solutions, or gotchas:

```
mcp__project-tools__store_knowledge(
    title="Pattern Name",
    description="What was learned",
    knowledge_type="solution|pattern|gotcha|learned",
    knowledge_category="relevant-category"
)
```

## Step 5: Check for Loose Ends

- [ ] Any uncommitted changes that should be committed?
- [ ] Any unactioned messages in inbox?
- [ ] Any session facts worth persisting as knowledge?

---

## What NOT to Do

- Do NOT write to `claude_family.*` tables (legacy, deprecated)
- Do NOT use `mcp__memory__` (removed)
- Do NOT skip calling `end_session` - without it, the session gets marked "auto-closed"

---

**Version**: 5.0 (Uses mcp__project-tools__end_session instead of legacy SQL)
**Created**: 2025-10-21
**Updated**: 2026-02-13
**Location**: .claude/commands/session-end.md
