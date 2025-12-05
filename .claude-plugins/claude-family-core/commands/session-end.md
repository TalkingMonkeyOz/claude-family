**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete ALL of the following:

---

## 1. SAVE SESSION STATE (Do This First!)

Save your current todo list and work state for next session resume:

```sql
-- Save session state (uses UPSERT - creates or updates)
INSERT INTO claude.session_state (project_name, todo_list, current_focus, files_modified, pending_actions)
VALUES (
    '<project_name>',  -- e.g., 'claude-family', 'nimbus-user-loader'
    '<todo_list_json>', -- Copy your current TodoWrite list as JSON array
    '<current_focus>',  -- What you were working on (1 sentence)
    ARRAY['file1.py', 'file2.ts'],  -- Files you modified this session
    ARRAY['action1', 'action2']  -- Things that still need to be done
)
ON CONFLICT (project_name) DO UPDATE SET
    todo_list = EXCLUDED.todo_list,
    current_focus = EXCLUDED.current_focus,
    files_modified = EXCLUDED.files_modified,
    pending_actions = EXCLUDED.pending_actions,
    updated_at = NOW();
```

**Quick Example:**
```sql
INSERT INTO claude.session_state (project_name, todo_list, current_focus, files_modified, pending_actions)
VALUES (
    'claude-family',
    '[{"content": "Implement feature X", "status": "in_progress"}, {"content": "Test feature X", "status": "pending"}]'::jsonb,
    'Working on session resume feature',
    ARRAY['scripts/session_startup_hook.py', '.claude/commands/session-end.md'],
    ARRAY['Need to sync commands to other projects']
)
ON CONFLICT (project_name) DO UPDATE SET
    todo_list = EXCLUDED.todo_list,
    current_focus = EXCLUDED.current_focus,
    files_modified = EXCLUDED.files_modified,
    pending_actions = EXCLUDED.pending_actions,
    updated_at = NOW();
```

---

## 2. SESSION LOGGING (postgres MCP)

```sql
-- 1. Get your latest session ID
SELECT session_id FROM claude.sessions
WHERE identity_id = 'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid
ORDER BY session_start DESC LIMIT 1;

-- 2. Update session with summary
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'What was accomplished',
    files_modified = ARRAY['file1.cs', 'file2.cs'],
    outcome = 'success',
    tokens_used = <estimated_tokens>
WHERE session_id = '<session_id>'::uuid;
```

---

## 3. Store Reusable Knowledge (If Applicable)

**If you discovered a reusable pattern:**

```sql
INSERT INTO claude.knowledge
(pattern_name, description, applies_to, example_code, gotchas, created_by_identity_id)
VALUES (
    'Pattern Name',
    'Clear description',
    'When to use this',
    'Code example',
    'Things to watch out for',
    'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid
);
```

---

## Verification Questions

Ask yourself:

- [ ] Did I save session state (todo list, focus, files)?
- [ ] Did I update session log with summary?
- [ ] Did I store reusable patterns if I discovered any?

**IF ANY ANSWER IS NO -> DO IT NOW BEFORE ENDING SESSION**

---

## Why This Matters

- Next session starts with full context of where you left off
- Todo list persists across context resets
- No more rediscovering what you were working on
- Continuous progress across sessions

---

**Remember**: Session state saves your progress. Session logging records history.
