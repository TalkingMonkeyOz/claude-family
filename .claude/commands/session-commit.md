**COMPLETE SESSION WORKFLOW: Logging + Git**

Performs BOTH session logging AND git commit in one workflow.

**Use this for:** Normal work sessions where you want to commit your changes.
**Use `/session-end` instead:** If you're just exploring or have uncommitted experiments.

---

## Step 1: Close Session in Database

```sql
-- Get current session ID
SELECT session_id::text, session_start, project_name
FROM claude.sessions
WHERE project_name = '$PROJECT_NAME'
  AND session_end IS NULL
ORDER BY session_start DESC
LIMIT 1;

-- Update session with summary (replace $SESSION_ID)
UPDATE claude.sessions
SET
    session_end = NOW(),
    session_summary = 'Brief summary of what was accomplished',
    tasks_completed = ARRAY['Task 1', 'Task 2'],
    learnings_gained = ARRAY['Key learning or pattern discovered'],
    session_metadata = COALESCE(session_metadata, '{}'::jsonb) || jsonb_build_object(
        'outcome', 'success',
        'commit_hash', 'will-add-after-commit'
    )
WHERE session_id = '$SESSION_ID'::uuid
RETURNING session_id, session_end;
```

---

## Step 2: Store Knowledge (If Applicable)

**Only if you discovered a reusable pattern:**

```sql
INSERT INTO claude.knowledge
(pattern_name, category, description, example_code, gotchas, confidence_level)
VALUES (
    'Pattern Name',
    'category',  -- csharp, mcp, git, windows, sql, etc.
    'What this solves',
    'Code example',
    'Gotchas to watch for',
    8  -- confidence 1-10
);
```

---

## Step 3: Git Operations

### Review Changes

```bash
git status
git diff
```

### Stage and Commit

```bash
# Stage specific files (preferred)
git add path/to/file1 path/to/file2

# OR stage all
git add .

# Commit with descriptive message
git commit -m "$(cat <<'EOF'
<type>: <brief summary>

<detailed description>

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Commit types:** `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

### Push to Remote

```bash
git push
# OR for new branch
git push -u origin <branch-name>
```

---

## Step 4: Update Session with Commit Hash

```sql
UPDATE claude.sessions
SET session_metadata = session_metadata || jsonb_build_object(
    'commit_hash', '<actual-commit-hash>'
)
WHERE session_id = '$SESSION_ID'::uuid;
```

---

## Quick Checklist

- [ ] Session closed with summary
- [ ] Knowledge stored (if applicable)
- [ ] Changes committed to git
- [ ] Changes pushed to remote
- [ ] Session metadata updated with commit hash

---

## When to Use Which Command

| Situation | Command |
|-----------|---------|
| Done + want to commit | `/session-commit` |
| Done, no commit needed | `/session-end` |
| Mid-session checkpoint | `/session-save` |
| Quick status check | `/session-status` |

---

**Version**: 2.0 (Updated to claude.* schema, removed deprecated MCPs)
**Created**: 2025-12-15
**Updated**: 2026-01-26
**Location**: .claude/commands/session-commit.md
