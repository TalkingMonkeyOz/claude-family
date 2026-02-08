**MANDATORY END-OF-SESSION CHECKLIST**

Performs session summary, knowledge capture, and cleanup before ending.

**Use this for:** Intentional session endings where you want to capture learnings.
**Automatic fallback:** If you forget, SessionEnd hook auto-closes with a basic summary.

---

## Step 1: Session Summary

Summarize the session work:

1. **What was accomplished** (bullet points)
2. **Key decisions made** (if any)
3. **What's next** (for future sessions)

### Save Session Notes (MCP)

Use `mcp__project-tools__store_session_notes` to save:
- `progress`: What was completed
- `decisions`: Key decisions made
- `blockers`: Any blockers encountered

### Update Session Focus

```sql
UPDATE claude.session_state
SET current_focus = 'Brief description of current state',
    next_steps = '[{"step": "Next action", "priority": 2}]'::jsonb,
    updated_at = NOW()
WHERE project_name = '{project_name}';
```

---

## Step 2: Store Knowledge (If Applicable)

If you discovered a reusable pattern, gotcha, or solution:

Use `mcp__project-tools__store_knowledge` with:
- `title`: Clear name
- `content`: What was learned
- `knowledge_type`: pattern, gotcha, solution, fact, or procedure
- `topic`: Relevant topic
- `confidence`: 1-100

---

## Step 3: Persist Incomplete Work

Check TaskList for any incomplete tasks. For each unfinished task:
- If it should persist: Ensure it exists as a Todo (task_sync_hook should handle this automatically)
- If it's no longer needed: Mark as completed or deleted

---

## Step 4: Verification

- [ ] Session notes saved via MCP
- [ ] Knowledge stored (if applicable)
- [ ] Incomplete tasks persisted as todos
- [ ] Session state updated with next steps

---

**Note**: Session close timestamp is set automatically by the SessionEnd hook. No manual SQL needed.

---

**Version**: 3.0 (Simplified: MCP tools, removed legacy schema/memory MCP references)
**Created**: 2025-12-15
**Updated**: 2026-02-08
**Location**: .claude/commands/session-end.md
