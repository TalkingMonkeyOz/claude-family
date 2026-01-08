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

-- NOTE: SessionStart hook now logs sessions automatically!
-- Manual logging only if needed:
INSERT INTO claude.sessions
(session_id, project_name, session_start, identity_id)
VALUES (gen_random_uuid(), 'project-name', NOW(), '<your-identity-uuid>')
RETURNING session_id;

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
SELECT title, content, tags
FROM claude.knowledge
WHERE title ILIKE '%relevant-keyword%'
   OR content ILIKE '%relevant-keyword%';

-- Check past sessions for similar work
SELECT session_summary, session_end, project_name
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
- [ ] Checked open feedback (if applicable)

**IF ANY ANSWER IS NO → DO IT NOW BEFORE STARTING WORK**

---

**Remember**: The time spent loading context prevents hours of rediscovering existing solutions.

---

**Note**: Most of these steps are now handled AUTOMATICALLY by the SessionStart hook. This command is for manual context loading when needed.

---

**Version**: 2.1
**Created**: 2025-10-21
**Updated**: 2026-01-08
**Location**: .claude/commands/session-start.md
