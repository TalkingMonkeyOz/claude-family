**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete ALL of the following:

---

## 🔍 RAG Feedback (Self-Learning)

**Quick assessment** - Were the auto-loaded vault docs helpful today?

Ask the user ONE question:

> "Before we wrap up: Were the knowledge vault docs I auto-loaded helpful this session?"
> - Yes (worked well)
> - Mixed (some useful, some not)
> - No (mostly irrelevant)
> - Didn't notice them

**Log the response:**

```sql
-- Record explicit session feedback
INSERT INTO claude.rag_feedback (session_id, helpful, signal_type, signal_confidence, feedback_text)
VALUES (
    '<current_session_id>',
    <true/false/null>,  -- Yes=true, No=false, Mixed/Didn't notice=null
    'session_end_survey',
    0.95,
    '<user response if they elaborated>'
);
```

**If user mentions specific bad docs**, flag them:

```sql
UPDATE claude.rag_doc_quality
SET miss_count = miss_count + 1,
    last_miss_at = NOW(),
    flagged_for_review = CASE WHEN miss_count >= 2 THEN true ELSE false END
WHERE doc_path = '<mentioned_doc_path>';
```

---

## ✅ Session Logging (postgres MCP)

```sql
-- 1. Find current session
SELECT session_id, session_start, project_name
FROM claude.sessions
WHERE project_name = '<current_project>'
ORDER BY session_start DESC LIMIT 1;

-- 2. Update with summary
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'What was accomplished',
    outcome = 'success'  -- success, partial, blocked, abandoned
WHERE session_id = '<session_id>';
```

---

## ✅ Store Learnings

**If you discovered a reusable pattern**, add to knowledge vault:

1. Create/update markdown doc in `knowledge-vault/30-Patterns/`
2. Re-embed: `python scripts/embed_vault_documents.py`

**If project-specific**, use `/knowledge-capture` skill.

---

## ✅ Memory Graph (memory MCP)

```
mcp__memory__create_entities(entities=[{
    "name": "Session <date>",
    "entityType": "Session",
    "observations": [
        "Project: X",
        "Completed: Y",
        "Key decision: Z"
    ]
}])
```

---

## Quick Verification

- [ ] Session logged to claude.sessions?
- [ ] RAG feedback collected?
- [ ] Learnings captured (if any)?
- [ ] Uncommitted changes? → Run `/session-commit`

---

**Version**: 2.0 (Updated for claude schema + RAG feedback)
**Updated**: 2026-01-04
