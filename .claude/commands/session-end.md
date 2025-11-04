**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete ALL of the following:

---

## 🚨 MCP USAGE CHECKLIST 🚨

### ✅ Session Logging (postgres MCP)

```sql
-- 1. Get your latest unclosed session ID
SELECT session_id, project_name, session_start
FROM claude_family.session_history
WHERE identity_id = (
    SELECT identity_id FROM claude_family.identities
    WHERE identity_name = 'claude-code-unified'  -- Or your identity name
)
AND session_end IS NULL
ORDER BY session_start DESC LIMIT 1;

-- 2. Update session with summary
UPDATE claude_family.session_history
SET
    session_end = NOW(),
    session_summary = 'What was accomplished in this session',
    tasks_completed = ARRAY['Task 1 completed', 'Task 2 fixed'],
    learnings_gained = ARRAY['Learned X', 'Discovered Y'],
    challenges_encountered = ARRAY['Challenge Z']
WHERE session_id = '<uuid-from-step-1>';
```

### ✅ Store Reusable Knowledge (postgres MCP)

**If you discovered a reusable pattern:**

```sql
INSERT INTO claude_family.shared_knowledge
(title, description, knowledge_type, knowledge_category, confidence_level, created_by_identity_id)
VALUES (
    'Pattern Name',
    'Clear description of what was learned',
    'pattern',  -- or 'technique', 'gotcha', 'best-practice'
    'category', -- e.g., 'mcp', 'csharp', 'database'
    10,         -- Confidence: 1-10
    (SELECT identity_id FROM claude_family.identities WHERE identity_name = 'claude-code-unified')
);
```

**If project-specific (Nimbus example):**

```sql
INSERT INTO nimbus_context.project_learnings (learning_type, lesson_learned, outcome)
VALUES ('bug-fix', 'Solution details', 'Positive outcome');
```

### ✅ Store in Memory Graph (memory MCP)

```
mcp__memory__create_entities(entities=[{
    "name": "Session Summary",
    "entityType": "Session",
    "observations": [
        "Completed: X",
        "Key decision: Y",
        "Files modified: Z",
        "Pattern discovered: P"
    ]
}])
```

**If you solved a problem:**

```
mcp__memory__create_relations(relations=[{
    "from": "Problem Name",
    "relationType": "solved-by",
    "to": "Solution Pattern"
}])
```

---

## Verification Questions

Ask yourself:

- [ ] Did I log session start to postgres?
- [ ] Did I query for existing knowledge before proposing solutions?
- [ ] Did I use tree-sitter for code analysis (if applicable)?
- [ ] Did I store learnings in memory graph?
- [ ] Did I update session log with summary?
- [ ] Did I store reusable patterns in postgres?

**IF ANY ANSWER IS NO → DO IT NOW BEFORE ENDING SESSION**

---

## Cost of Skipping MCPs

- Next Claude spends 30 minutes rediscovering your solution
- Same bug gets solved 3 times by different Claudes
- Institutional knowledge stays at zero
- User gets frustrated repeating themselves

---

**Remember**: MCP usage is NOT optional. It's how the Claude Family learns and grows.
