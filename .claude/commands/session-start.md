**SESSION START - Automatic via Hook**

Session logging is now **automatic** via the SessionStart hook. You don't need to manually run this command.

---

## What Happens Automatically

When you start Claude Code in any project:

1. **SessionStart hook fires** - Creates session record in `claude.sessions`
2. **Loads session state** - Retrieves `current_focus`, `next_steps` from `claude.session_state`
3. **Loads active todos** - Queries `claude.todos` for pending/in_progress items
4. **Checks messages** - Looks for pending messages in `claude.messages`

---

## When to Use This Command

Only use `/session-start` if:
- The SessionStart hook failed (check `~/.claude/hooks.log`)
- You need to manually re-initialize context
- You're debugging session lifecycle

---

## Manual Session Start (If Needed)

### Step 1: Create Session Record

```sql
INSERT INTO claude.sessions
(session_id, identity_id, project_name, session_start)
VALUES (
    gen_random_uuid(),
    'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid,  -- claude-code-unified identity
    '{project_name}',
    NOW()
)
RETURNING session_id;
```

### Step 2: Load Context

Use `/session-resume` to display current context from database.

### Step 3: Check Feedback (Optional)

```sql
SELECT feedback_type, COUNT(*) as count
FROM claude.feedback
WHERE project_id = '{project_id}'::uuid
  AND status IN ('new', 'in_progress')
GROUP BY feedback_type;
```

---

## Related Commands

| Command | Purpose |
|---------|---------|
| `/session-resume` | Show context from database (todos, focus, last session) |
| `/session-status` | Quick read-only status check |
| `/session-end` | Save summary and learnings |
| `/session-commit` | End session + git commit |

---

## Troubleshooting

**Hook not firing?**
1. Check `~/.claude/hooks.log` for errors
2. Verify hook is configured in `settings.json`
3. Check database connectivity

**Session not created?**
1. Run the manual INSERT above
2. Save the returned session_id for session-end

---

**Version**: 3.0 (Simplified - hooks handle session logging)
**Created**: 2025-10-21
**Updated**: 2026-01-07
**Location**: .claude/commands/session-start.md
