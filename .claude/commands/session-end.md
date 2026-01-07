**END-OF-SESSION CHECKLIST**

Before ending this session, complete the following steps to preserve knowledge.

---

## Step 1: Update Session Record

```sql
-- 1. Find your current session
SELECT session_id, session_start, project_name
FROM claude.sessions
WHERE project_name = '{project_name}'
  AND session_end IS NULL
ORDER BY session_start DESC
LIMIT 1;

-- 2. Update session with summary
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'Brief summary of what was accomplished this session',
    tasks_completed = ARRAY[
        'Task 1 description',
        'Task 2 description'
    ],
    learnings_gained = ARRAY[
        'Key learning or discovery',
        'Pattern or technique learned'
    ],
    challenges_encountered = ARRAY[
        'Challenge faced and how it was resolved'
    ]
WHERE session_id = '{session_id}'::uuid
RETURNING session_id, session_end;
```

---

## Step 2: Update Session State (Optional)

If the focus changed or there are new next steps:

```sql
UPDATE claude.session_state
SET
    current_focus = 'New focus area',
    next_steps = '["Next step 1", "Next step 2", "Next step 3"]'::jsonb,
    updated_at = NOW()
WHERE project_name = '{project_name}';
```

---

## Step 3: Store Reusable Knowledge (If Applicable)

**If you discovered a reusable pattern:**

```sql
INSERT INTO claude.knowledge
(pattern_name, category, description, example_code, gotchas, confidence_level, times_applied, created_by_identity)
VALUES (
    'Pattern Name',
    'category',  -- e.g., 'csharp', 'sql', 'git', 'windows', 'playwright'
    'Clear description of what this solves',
    'Code example or command',
    'Things to watch out for',
    10,  -- confidence 1-10
    1,   -- times applied so far
    'claude-code-unified'
)
RETURNING knowledge_id;
```

---

## Step 4: Update TODO_NEXT_SESSION.md (Optional)

Only if you want a quick-reference file for next session:

```markdown
# Next Session TODO

**Last Updated**: {today}
**Last Session**: {brief description}

## Completed This Session
- [x] Item 1
- [x] Item 2

## Next Steps
1. First priority
2. Second priority
3. Third priority
```

---

## Step 5: Store in Memory Graph (Optional)

```
mcp__memory__create_entities(entities=[{
    "name": "Session: Brief Title",
    "entityType": "Session",
    "observations": [
        "Completed: X",
        "Key decision: Y",
        "Files modified: Z"
    ]
}])
```

---

## Quick Summary Template

Copy and fill in:

```
Session Summary: [What was accomplished]
Tasks Completed: [List of completed items]
Key Learnings: [Patterns discovered, gotchas found]
Next Steps: [What to do next session]
```

---

## Verification Checklist

- [ ] Session updated with summary in `claude.sessions`
- [ ] Active todos reflect current state in `claude.todos`
- [ ] Reusable patterns stored (if any discovered)
- [ ] Ready for next session

---

## Related Commands

| Command | Purpose |
|---------|---------|
| `/session-commit` | End session + git commit (recommended for normal work) |
| `/session-resume` | Load context at start of next session |
| `/session-status` | Quick read-only status check |

---

**Version**: 3.0 (Updated to claude.* schema)
**Created**: 2025-10-21
**Updated**: 2026-01-07
**Location**: .claude/commands/session-end.md
