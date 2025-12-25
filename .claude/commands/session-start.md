**MANDATORY SESSION STARTUP PROTOCOL**

Execute ALL of the following steps at the start of EVERY session:

---

## Step 1: Load Startup Context

```bash
python C:/claude/shared/scripts/load_claude_startup_context.py
```

This restores:
- Your identity and role
- Universal knowledge (patterns, gotchas, techniques)
- Recent sessions (last 7 days across all Claudes)
- Project-specific context

---

## Step 2: Sync Workspaces

```bash
python C:/claude/shared/scripts/sync_workspaces.py
```

This generates `workspaces.json` from PostgreSQL, mapping project names to locations.

---

## Step 3: Log Session Start (postgres MCP)

**NOTE**: This is typically done automatically by the SessionStart hook (`session_startup_hook.py`).
Only run manually if the hook didn't fire.

```sql
-- Get your identity_id first (check CLAUDE.md for your identity)
-- claude-code-unified: ff32276f-9d05-4a18-b092-31b54c82fff9
-- claude-desktop: 3be37dfb-c3bb-4303-9bf1-952c7287263f

-- Then log the session start
INSERT INTO claude.sessions
(session_id, identity_id, project_name, session_start)
VALUES (gen_random_uuid(), '<your-identity-uuid>'::uuid, 'project-name', NOW())
RETURNING session_id;

-- Save the returned session_id - you'll need it for session end
```

---

## Step 4: Query Relevant Context (memory MCP)

Based on the user's request, search for relevant past knowledge:

```
mcp__memory__search_nodes(query="relevant keywords from user's request")
```

---

## Step 5: Check for Existing Solutions (postgres MCP)

NEVER propose new solutions without checking if we've solved this before:

```sql
-- Check universal knowledge
SELECT pattern_name, description, example_code, gotchas
FROM claude.universal_knowledge
WHERE pattern_name ILIKE '%relevant-keyword%'
   OR description ILIKE '%relevant-keyword%';

-- Check past sessions for similar work
SELECT session_summary, tasks_completed, project_name
FROM claude.sessions
WHERE session_summary ILIKE '%relevant-keyword%'
ORDER BY session_start DESC
LIMIT 10;
```

---

## Step 6: Check Open Feedback (Optional)

If working on a registered project, check for open feedback items:

```sql
-- Quick check for open feedback (if project has feedback tracking)
-- Replace PROJECT-ID with your project's UUID from CLAUDE.md
SELECT
    feedback_type,
    COUNT(*) as count
FROM claude.feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('new', 'in_progress')
GROUP BY feedback_type;
```

**If open items exist:** Briefly mention them to user: "Note: This project has X open feedback items. Use `/feedback-check` to view details."

**Registered Projects** (check `claude.projects` for current list):
- claude-family: `20b5627c-e72c-4501-8537-95b559731b59`
- ATO-Tax-Agent: Check CLAUDE.md for project_id

---

## Checklist

Before starting work, verify:

- [ ] Ran `load_claude_startup_context.py`
- [ ] Synced `workspaces.json` from database
- [ ] Logged session start to PostgreSQL
- [ ] Queried memory graph for context
- [ ] Checked for existing solutions in universal_knowledge
- [ ] Checked past sessions for similar work
- [ ] Checked open feedback (if applicable)

**IF ANY ANSWER IS NO → DO IT NOW BEFORE STARTING WORK**

---

**Remember**: The time spent loading context prevents hours of rediscovering existing solutions.
