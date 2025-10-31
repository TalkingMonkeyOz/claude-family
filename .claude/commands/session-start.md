**MANDATORY SESSION STARTUP PROTOCOL**

Execute ALL of the following steps at the start of EVERY session:

---

## Step 1: Load Previous Session Context (postgres MCP)

**BEFORE doing anything else**, load where we left off:

```sql
-- Get the most recent session for this project
SELECT
    session_summary,
    tasks_completed,
    learnings_gained,
    challenges_encountered,
    session_metadata->>'next_steps' as next_steps,
    session_metadata->>'pending_tasks' as pending_tasks,
    session_metadata->>'files_in_progress' as files_in_progress,
    session_metadata->>'decisions_pending' as decisions_pending,
    session_metadata->'current_state' as current_state,
    session_metadata->'resumption_context' as resumption_context,
    session_start,
    session_end
FROM claude_family.session_history
WHERE project_name = 'current-project-name'
ORDER BY session_start DESC
LIMIT 1;
```

**Read this CAREFULLY before doing anything else.** This tells you:
- What was accomplished last session
- What needs to be done next
- What's incomplete
- Current state of the project
- Any decisions pending

---

## Step 2: Load Startup Context Script

```bash
python C:\claude\shared\scripts\load_claude_startup_context.py
```

This restores:
- Your identity and role
- Universal knowledge (patterns, gotchas, techniques)
- Recent sessions (last 7 days across all Claudes)
- Project-specific context

---

## Step 3: Check Memory Graph Context (memory MCP)

Based on the user's request or previous session, search for relevant knowledge:

```
mcp__memory__search_nodes(query="relevant keywords from project or last session")
```

---

## Step 4: Log New Session Start (postgres MCP)

```sql
-- Get your identity_id
SELECT identity_id, identity_name
FROM claude_family.identities
WHERE identity_name = 'your-identity-name';

-- Log the session start
INSERT INTO claude_family.session_history
(identity_id, session_start, project_name, project_schema)
VALUES (
    'your-identity-uuid',
    NOW(),
    'project-name',
    'project_schema_if_applicable'
)
RETURNING session_id;

-- SAVE this session_id - you'll need it for session end
```

---

## Step 5: Check for Existing Solutions (postgres MCP)

NEVER propose new solutions without checking if we've solved this before:

```sql
-- Check shared knowledge
SELECT title, description, code_example, gotchas, applies_to_projects
FROM claude_family.shared_knowledge
WHERE title ILIKE '%relevant-keyword%'
   OR description ILIKE '%relevant-keyword%'
   OR knowledge_category ILIKE '%relevant-keyword%'
ORDER BY confidence_level DESC, created_at DESC
LIMIT 10;

-- Check past sessions for similar work
SELECT session_summary, tasks_completed, learnings_gained, project_name, session_start
FROM claude_family.session_history
WHERE session_summary ILIKE '%relevant-keyword%'
   OR 'relevant-keyword' = ANY(tasks_completed)
ORDER BY session_start DESC
LIMIT 10;
```

---

## Step 6: Communicate Context to User

**Tell the user what you found:**

"I've loaded the previous session context. Here's where we left off:

**Last Session Summary:** [brief summary]

**Completed:** [key accomplishments]

**Next Steps:**
1. [First priority]
2. [Second priority]
3. [Third priority]

**Pending Work:**
- [Incomplete task 1]
- [Incomplete task 2]

**Current State:**
- Build: [status]
- Tests: [status]
- Branch: [name]

**Decisions Pending:**
- [Any user decisions needed]

Ready to continue?"

---

## 📋 Startup Checklist

Before starting work, verify:

- [ ] **Loaded previous session** from postgres (what was done, what's next)
- [ ] **Ran startup context script** to load identity and universal knowledge
- [ ] **Queried memory graph** for relevant context
- [ ] **Logged new session start** to PostgreSQL (saved session_id)
- [ ] **Checked for existing solutions** in shared_knowledge
- [ ] **Checked past sessions** for similar work
- [ ] **Communicated context** to user (where we left off, what's next)

**IF ANY ANSWER IS NO → DO IT NOW BEFORE STARTING WORK**

---

## 💡 Why This Matters

**Without loading previous context:**
- ❌ Spend 30 minutes asking "what were we doing?"
- ❌ User has to repeat everything from last session
- ❌ Forget about pending tasks
- ❌ Ignore decisions that were made
- ❌ Start from scratch instead of continuing

**With comprehensive context loading:**
- ✅ Resume in 2 minutes
- ✅ User says "continue where we left off" and you can
- ✅ Remember all pending work
- ✅ Respect previous decisions
- ✅ Pick up exactly where we stopped

---

## 🎯 Quick Resume Pattern

If user says "continue where we left off" or similar:

1. Load previous session (Step 1) → Get next_steps
2. Confirm with user: "I see we were [context]. Next steps are: [list]. Should I proceed?"
3. User says yes → Start executing from next_steps
4. User says no/changes direction → Clarify new direction, update your mental plan

**Goal**: Zero context gathering time, instant productive work.

---

**Remember**: The 5 minutes spent loading context saves 30 minutes of "what were we doing?"
