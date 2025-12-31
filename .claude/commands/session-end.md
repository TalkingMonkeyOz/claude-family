**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete ALL of the following:

---

## 🚨 MCP USAGE CHECKLIST 🚨

### ✅ Session Logging (postgres MCP)

```sql
-- 1. Get your latest session ID
SELECT id FROM claude_family.session_history
WHERE identity_id = 5
ORDER BY session_start DESC LIMIT 1;

-- 2. Update session with summary
UPDATE claude_family.session_history
SET
    session_end = NOW(),
    summary = 'What was accomplished',
    files_modified = ARRAY['file1.cs', 'file2.cs'],
    outcome = 'success',
    tokens_used = <estimated_tokens>
WHERE id = <session_id>;
```

### ✅ Store Reusable Knowledge (postgres MCP)

**If you discovered a reusable pattern:**

```sql
INSERT INTO claude_family.universal_knowledge
(pattern_name, description, applies_to, example_code, gotchas, created_by_identity_id)
VALUES (
    'Pattern Name',
    'Clear description',
    'When to use this',
    'Code example',
    'Things to watch out for',
    5
);
```

**If project-specific:**

```sql
INSERT INTO nimbus_context.patterns (pattern_type, solution, context)
VALUES ('bug-fix', 'Solution details', 'When this applies');
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
