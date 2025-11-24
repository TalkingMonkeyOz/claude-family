# Session Workflow Commands - Quick Reference

**Three commands, three use cases:**

---

## 📋 Command Comparison

| Command | Purpose | Includes MCP Logging | Includes Git | Use When |
|---------|---------|---------------------|--------------|----------|
| `/session-start` | Begin session | ✅ Yes (creates record) | ❌ No | **Every session start** |
| `/session-end` | End session (knowledge only) | ✅ Yes (updates record) | ❌ No (reminder only) | Exploration, research, no commits |
| `/session-commit` | End session + commit | ✅ Yes (updates record) | ✅ Yes (full git workflow) | Normal work sessions |

---

## 🎯 Decision Tree

```
Start Session
    ↓
[/session-start] ← ALWAYS RUN THIS FIRST
    ↓
Do work...
    ↓
Ready to end?
    ↓
    ├─→ Have code to commit? 
    │       ↓ YES
    │   [/session-commit]  ← Does logging + git in one step
    │
    └─→ NO
        [/session-end]     ← Does logging only, reminds about git
```

---

## 📝 Typical Workflows

### Normal Work Session (80% of cases)
```bash
# Start
/session-start

# Work on code...

# End with commit
/session-commit
# → Updates PostgreSQL session log
# → Stores learnings in memory graph
# → Commits and pushes code
```

### Exploration Session
```bash
# Start
/session-start

# Explore codebase, answer questions, research...

# End without committing
/session-end
# → Updates PostgreSQL session log
# → Stores learnings in memory graph
# → Reminds you about git (but doesn't force it)
```

### Multi-Commit Session
```bash
# Start
/session-start

# Work on feature A
git add . && git commit -m "feat: A"

# Work on feature B
git add . && git commit -m "feat: B"

# End session (code already committed)
/session-end
# → Updates session log with summary of BOTH features
# → Reminds you to push if you haven't
```

---

## 🔍 What Each Command Does

### `/session-start`
- ✅ Loads startup context (identity, knowledge, recent sessions)
- ✅ Syncs workspace mappings
- ✅ Creates session record in PostgreSQL
- ✅ Queries memory graph for relevant context
- ✅ Checks for existing solutions

### `/session-end`
- ✅ Updates PostgreSQL session with summary
- ✅ Stores reusable patterns in universal_knowledge
- ✅ Creates entities/relations in memory graph
- ✅ **NEW:** Reminds you about git operations
- ❌ Does NOT commit or push code

### `/session-commit`
- ✅ Everything `/session-end` does
- ✅ **PLUS:** Guides you through git workflow
  - Review changes (status/diff)
  - Stage files
  - Commit with formatted message
  - Push to remote

---

## 💡 Pro Tips

1. **Always run `/session-start`** - Even for quick 5-minute sessions
2. **Use `/session-commit` by default** - Covers 80% of cases
3. **Use `/session-end`** when:
   - Just exploring/researching
   - Code has WIP experiments you don't want to commit
   - Already committed manually during session
4. **Don't skip MCP logging** - Future sessions depend on it!

---

## 🚨 Common Mistakes

❌ **Skipping `/session-start`**
- Next session wastes 30 minutes rediscovering context

❌ **Using `/session-end` then forgetting to commit**
- Work gets lost when switching projects
- → Solution: Use `/session-commit` instead

❌ **Committing without session logging**
- Knowledge stays siloed, patterns not shared
- → Solution: Always use `/session-commit` or `/session-end`

---

## 📊 Example: Full Session with `/session-commit`

```sql
-- At session end, this SQL will be pre-filled:
UPDATE claude_family.session_history
SET
    session_end = NOW(),
    session_summary = 'Added git reminder to /session-end, created /session-commit command',
    tasks_completed = ARRAY[
        'Updated /session-end.md with git operations reminder',
        'Created /session-commit.md command for atomic logging+git workflow',
        'Documented session workflows in SESSION_WORKFLOWS.md'
    ],
    learnings_gained = ARRAY[
        'Separation of concerns: Keep session-end pure for knowledge, session-commit for full workflow',
        'Git reminder checklist helps build habits without forcing actions'
    ],
    session_metadata = session_metadata || jsonb_build_object(
        'files_modified', ARRAY[
            '.claude/commands/session-end.md',
            '.claude/commands/session-commit.md',
            'docs/SESSION_WORKFLOWS.md'
        ],
        'outcome', 'success'
    )
WHERE session_id = '<current-session-id>'::uuid;
```

Then git operations:
```bash
git add .claude/commands/session-end.md \
        .claude/commands/session-commit.md \
        docs/SESSION_WORKFLOWS.md

git commit -m "$(cat <<'EOF'
feat: Add session-commit command and improve session workflows

Created new /session-commit command that performs both MCP logging and git
operations in a single atomic workflow. This covers the 80% use case where
developers want to commit their work at session end.

Changes:
- Updated /session-end with git operations reminder checklist
- Created /session-commit for complete logging + git workflow
- Added SESSION_WORKFLOWS.md documenting all three approaches
- Session-end stays pure (knowledge only) for exploration sessions
- Session-commit does everything for normal work sessions

Benefits:
- Reduces forgotten commits (common pain point)
- Clear separation: session-end (pure logging) vs session-commit (full workflow)
- Flexibility for different session types

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

git push
```

---

**Version:** 1.0
**Created:** 2025-11-15
**Location:** C:\Projects\claude-family\docs\SESSION_WORKFLOWS.md
