**COMPLETE SESSION WORKFLOW: Logging + Git**

This command performs BOTH session logging AND git operations in one atomic workflow.

**Use this for:** Normal work sessions where you want to commit your changes.
**Don't use if:** You're just exploring, or have uncommitted experiments (use `/session-end` instead).

---

## Step 1: MCP Session Logging

### ✅ Update Session in PostgreSQL

```sql
-- 1. Get your latest session ID
SELECT session_id, session_start, project_name 
FROM claude_family.session_history
WHERE identity_id = 'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid
  AND session_end IS NULL
ORDER BY session_start DESC 
LIMIT 1;

-- 2. Update session with summary
-- Replace <session_id> with the UUID from step 1
UPDATE claude_family.session_history
SET
    session_end = NOW(),
    session_summary = '**Brief summary of what was accomplished**',
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
    ],
    session_metadata = session_metadata || jsonb_build_object(
        'files_modified', ARRAY['path/to/file1.cs', 'path/to/file2.md'],
        'outcome', 'success',
        'estimated_tokens', 50000
    )
WHERE session_id = '<session_id>'::uuid
RETURNING session_id, session_end;
```

### ✅ Store Reusable Knowledge (If Applicable)

**If you discovered a reusable pattern:**

```sql
INSERT INTO claude_family.universal_knowledge
(pattern_name, category, description, example_code, gotchas, confidence_level, times_applied, created_by_identity)
VALUES (
    'Pattern Name',
    'category',  -- e.g., 'csharp', 'mcp', 'git', 'windows'
    'Clear description of what this solves',
    'Code example or command',
    'Things to watch out for',
    10,  -- confidence 1-10
    1,   -- times applied so far
    'claude-code-unified'
)
RETURNING knowledge_id;
```

### ✅ Store in Memory Graph (Optional)

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

## Step 2: Git Operations

### Review Changes

```bash
# See what changed
git status

# Review diffs
git diff
```

### Stage and Commit

```bash
# Stage specific files
git add path/to/file1 path/to/file2

# OR stage all changes
git add .

# Commit with descriptive message
git commit -m "$(cat <<'EOF'
<type>: <brief summary>

<detailed description of changes>

<optional: breaking changes, migration notes>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Commit message types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code restructuring
- `test:` - Adding tests
- `chore:` - Maintenance tasks

### Push to Remote

```bash
# Push to current branch
git push

# OR if first push on new branch
git push -u origin <branch-name>
```

---

## Step 3: Verification

- [ ] Session logged in PostgreSQL with summary
- [ ] Knowledge stored (if applicable)
- [ ] Changes committed to git
- [ ] Changes pushed to remote
- [ ] Ready to close Claude Code

---

## Quick Checklist Template

**Session Summary:**
- What: [Brief description]
- Files: [List of modified files]
- Outcome: [success/partial/blocked]
- Next: [What's next for future session]

**Commit Message:**
- Type: [feat/fix/docs/refactor/etc.]
- Summary: [One line description]
- Details: [What changed and why]

---

**Remember**: This workflow ensures both institutional knowledge (MCP) and code (git) are preserved!