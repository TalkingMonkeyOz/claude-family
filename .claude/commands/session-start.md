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
-- Check universal knowledge
SELECT pattern_name, description, example_code, gotchas
FROM claude_family.universal_knowledge
WHERE pattern_name ILIKE '%relevant-keyword%'
   OR description ILIKE '%relevant-keyword%';

-- Check past sessions for similar work
SELECT summary, outcome, files_modified, project_name
FROM claude_family.session_history
WHERE task_description ILIKE '%relevant-keyword%'
   OR summary ILIKE '%relevant-keyword%'
ORDER BY session_start DESC
LIMIT 10;
```

---

## Step 6: Check Messages (orchestrator MCP)

Check for messages from other Claude instances:

```
mcp__orchestrator__check_inbox(
  project_name="<current-project-name>",
  include_broadcasts=true
)
```

**IMPORTANT**: You MUST pass `project_name` to see project-targeted messages. Without it, only broadcasts are returned.

If messages exist:
- Display count and summaries
- For task_request messages, acknowledge and consider adding to your work plan
- For notifications, acknowledge and inform user if relevant

---

## Step 7: Check Open Feedback (Optional)

If working on a registered project, check for open feedback items:

```sql
-- Quick check for open feedback (if project has feedback tracking)
-- Replace PROJECT-ID with your project's UUID from CLAUDE.md
SELECT
    feedback_type,
    COUNT(*) as count
FROM claude_pm.project_feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('new', 'in_progress')
GROUP BY feedback_type;
```

**If open items exist:** Briefly mention them to user: "📋 Note: This project has X open feedback items. Use `/feedback-check` to view details."

**Registered Projects:**
- claude-pm: `a3097e59-7799-4114-86a7-308702115905`
- nimbus-user-loader: `07206097-4caf-423b-9eb8-541d4c25da6c`
- ATO-Tax-Agent: `7858ecf4-4550-456d-9509-caea0339ec0d`

---

## Checklist

Before starting work, verify:

- [ ] Ran `load_claude_startup_context.py`
- [ ] Synced `workspaces.json` from database
- [ ] Logged session start to PostgreSQL
- [ ] Queried memory graph for context
- [ ] Checked for existing solutions in universal_knowledge
- [ ] Checked past sessions for similar work
- [ ] **Checked messages from other Claudes** (pass project_name!)
- [ ] Checked open feedback (if applicable)

**IF ANY ANSWER IS NO → DO IT NOW BEFORE STARTING WORK**

---

**Remember**: The time spent loading context prevents hours of rediscovering existing solutions.
