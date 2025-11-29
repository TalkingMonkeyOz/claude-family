**MANDATORY SESSION STARTUP PROTOCOL**

Execute ALL of the following steps at the start of EVERY session:

---

## Step 1: Check Where We Left Off

```sql
-- Check for saved session state (todo list, focus, pending actions)
SELECT
    todo_list,
    current_focus,
    files_modified,
    pending_actions,
    updated_at
FROM claude_family.session_state
WHERE project_name = '<current-project-name>';
```

**If state exists:** Resume from todo list. Report what was in progress.

**If no state:** Fresh start, proceed normally.

---

## Step 2: Load Startup Context (Optional)

```bash
python C:/claude/shared/scripts/load_claude_startup_context.py
```

This restores:
- Your identity and role
- Universal knowledge (patterns, gotchas, techniques)
- Recent sessions (last 7 days across all Claudes)
- Project-specific context

---

## Step 3: Log Session Start (postgres MCP)

```sql
-- Log the session start
INSERT INTO claude_family.session_history
(identity_id, session_start, project_name, session_summary)
VALUES (
    'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid,  -- claude-code-unified
    NOW(),
    '<project-name>',
    'Session started'
)
RETURNING session_id;

-- Save the returned ID - you'll need it for session end
```

---

## Step 4: Check for Pending Messages

```sql
-- Check for messages from other Claude instances
SELECT message_id, from_session_id, subject, body, created_at
FROM claude_family.instance_messages
WHERE status = 'pending'
  AND (to_project = '<project-name>' OR to_project IS NULL)
ORDER BY created_at DESC;
```

Or use: `mcp__orchestrator__check_inbox`

---

## Step 5: Query Relevant Context (If Needed)

Based on the user's request, check for existing solutions:

```sql
-- Check universal knowledge
SELECT pattern_name, description, example_code
FROM claude_family.universal_knowledge
WHERE pattern_name ILIKE '%keyword%'
   OR description ILIKE '%keyword%';
```

---

## Checklist

Before starting work, verify:

- [ ] Checked for saved session state (where we left off)
- [ ] Loaded todo list from session_state if exists
- [ ] Logged session start to PostgreSQL
- [ ] Checked for pending messages
- [ ] Checked for existing solutions if relevant

**IF ANY ANSWER IS NO -> DO IT NOW BEFORE STARTING WORK**

---

## Quick Resume Flow

If resuming from previous session:

1. Check `session_state` table for todo list
2. Report: "Resuming from where we left off: [current_focus]"
3. Show todo list with status markers
4. Continue with in_progress item

---

**Remember**: The session state hook runs automatically. This is for manual checks when needed.
