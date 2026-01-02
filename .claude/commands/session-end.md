**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete these steps:

---

## Step 1: Update Session Summary

```sql
-- Get your session ID (from SESSION_ID env var or query)
UPDATE claude.sessions
SET
    session_end = NOW(),
    summary = 'What was accomplished',
    outcome = 'success'
WHERE session_id = 'YOUR-SESSION-UUID';
```

---

## Step 2: Store Reusable Knowledge (If Applicable)

```sql
-- If you discovered a reusable pattern
INSERT INTO claude.knowledge
(pattern_name, description, applies_to, example_code, gotchas)
VALUES (
    'Pattern Name',
    'Clear description',
    'When to use this',
    'Code example',
    'Things to watch out for'
);
```

---

## Step 3: Update Memory Graph (Optional)

```
mcp__memory__create_entities(entities=[{
    "name": "Session Summary",
    "entityType": "Session",
    "observations": ["Completed: X", "Key decision: Y"]
}])
```

---

## Verification Checklist

- [ ] Session summary updated in database
- [ ] Reusable patterns captured (if any)
- [ ] Memory graph updated (if significant learnings)
- [ ] Todos synced (automatic via hook)

---

## Why This Matters

- Next Claude avoids rediscovering your solution
- Institutional knowledge grows
- User doesn't repeat themselves

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-01-03
**Location**: .claude/commands/session-end.md
