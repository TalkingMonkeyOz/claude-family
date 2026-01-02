**MANDATORY SESSION STARTUP PROTOCOL**

Execute these steps at the start of EVERY session:

---

## Step 1: Session Auto-Logged

The `SessionStart` hook automatically:
- Creates session record in `claude.sessions`
- Loads todos from `claude.todos`
- Checks messages from `claude.messages`
- Pre-loads RAG context from vault

**No manual action needed** - hook handles this.

---

## Step 2: Check Context (If Needed)

```sql
-- Check for existing solutions
SELECT pattern_name, description, example_code
FROM claude.knowledge
WHERE pattern_name ILIKE '%keyword%'
   OR description ILIKE '%keyword%';

-- Check past sessions
SELECT summary, outcome, project_name
FROM claude.sessions
WHERE summary ILIKE '%keyword%'
ORDER BY session_start DESC LIMIT 5;
```

---

## Step 3: Check Open Feedback (If Project Has It)

```sql
SELECT feedback_type, COUNT(*) as count
FROM claude.feedback
WHERE project_id = 'YOUR-PROJECT-ID'::uuid
  AND status IN ('new', 'in_progress')
GROUP BY feedback_type;
```

Use `/feedback-check` for formatted view.

---

## Checklist

- [x] Session logged (automatic via hook)
- [x] Todos loaded (automatic via hook)
- [x] Messages checked (automatic via hook)
- [ ] Queried for existing solutions (if relevant)
- [ ] Checked open feedback (if applicable)

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-01-03
**Location**: .claude/commands/session-start.md
