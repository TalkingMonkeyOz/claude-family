**MANDATORY SESSION STARTUP PROTOCOL**

Execute ALL of the following steps at the start of EVERY session:

---

## Step 1: Load Startup Context

```bash
python "C:\claude\shared\scripts\load_claude_startup_context.py"
```

This restores:
- Your identity and role
- Shared knowledge (patterns, gotchas, techniques)
- Recent sessions (last 7 days across all Claudes)
- Project-specific context

---

## Step 2: Sync Workspaces

```bash
python "C:\claude\shared\scripts\sync_workspaces.py"
```

This generates `workspaces.json` from PostgreSQL, mapping project names to locations.

---

## Step 3: Log Session Start (postgres MCP)

```sql
-- Get your identity_id first (check CLAUDE.md for your identity)
-- claude-desktop-001: Use appropriate ID
-- claude-code-console-001: Use appropriate ID
-- diana: Use appropriate ID

-- Then log the session start
INSERT INTO claude_family.session_history
(identity_id, session_start, project_name, task_description)
VALUES ('<your-identity-uuid>', NOW(), 'project-name', 'Brief task description')
RETURNING id;

-- Save the returned ID - you'll need it for session end
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
-- Check shared knowledge
SELECT title, description, knowledge_category, confidence_level
FROM claude_family.shared_knowledge
WHERE title ILIKE '%relevant-keyword%'
   OR description ILIKE '%relevant-keyword%'
ORDER BY confidence_level DESC, times_applied DESC
LIMIT 10;

-- Check past sessions for similar work
SELECT session_summary, tasks_completed, project_name, session_start
FROM claude_family.session_history
WHERE session_summary ILIKE '%relevant-keyword%'
   OR 'relevant-keyword' = ANY(tasks_completed)
ORDER BY session_start DESC
LIMIT 10;
```

---

## Checklist

Before starting work, verify:

- [ ] Ran `load_claude_startup_context.py`
- [ ] Synced `workspaces.json` from database
- [ ] Logged session start to PostgreSQL
- [ ] Queried memory graph for context
- [ ] Checked for existing solutions in shared_knowledge
- [ ] Checked past sessions for similar work

**IF ANY ANSWER IS NO → DO IT NOW BEFORE STARTING WORK**

---

**Remember**: The time spent loading context prevents hours of rediscovering existing solutions.
