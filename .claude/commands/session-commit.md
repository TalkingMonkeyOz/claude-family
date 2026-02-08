**COMPLETE SESSION WORKFLOW: Logging + Git**

Performs session summary, knowledge capture, and git commit in one workflow.

**Use this for:** Normal work sessions where you want to commit your changes.
**Don't use if:** Just exploring or have uncommitted experiments (use `/session-end` instead).

---

## Step 1: Session Summary

Summarize the session work:

1. **What was accomplished** (bullet points)
2. **Key decisions made** (if any)
3. **What's next** (for future sessions)

### Update Session State (MCP)

Use `mcp__project-tools__store_session_notes` to save:
- `progress`: What was completed
- `decisions`: Key decisions made
- `blockers`: Any blockers encountered

### Update Session Focus

```sql
UPDATE claude.session_state
SET current_focus = 'Brief description of current state',
    next_steps = '[{"step": "Next action", "priority": 2}]'::jsonb,
    updated_at = NOW()
WHERE project_name = '{project_name}';
```

---

## Step 2: Store Knowledge (If Applicable)

If you discovered a reusable pattern, gotcha, or solution:

Use `mcp__project-tools__store_knowledge` with:
- `title`: Clear name
- `content`: What was learned
- `knowledge_type`: pattern, gotcha, solution, fact, or procedure
- `topic`: Relevant topic
- `confidence`: 1-100

---

## Step 3: Git Operations

### Review Changes

```bash
git status
git diff --stat
```

### Stage and Commit

```bash
# Stage specific files (preferred)
git add path/to/file1 path/to/file2

# Commit with descriptive message
git commit -m "$(cat <<'EOF'
<type>: <brief summary>

<detailed description>

Co-Authored-By: Claude <model> <noreply@anthropic.com>
EOF
)"
```

**Types:** `feat:` `fix:` `docs:` `refactor:` `test:` `chore:`

### Push (if requested)

```bash
git push
```

---

## Step 4: Verification

- [ ] Session notes saved
- [ ] Knowledge stored (if applicable)
- [ ] Changes committed to git
- [ ] Session state updated with next steps

---

**Version**: 2.0 (Simplified: uses MCP tools, removed memory MCP and raw SQL session logging)
**Created**: 2025-12-15
**Updated**: 2026-02-08
**Location**: .claude/commands/session-commit.md
