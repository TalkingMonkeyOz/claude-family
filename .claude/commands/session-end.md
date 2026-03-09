**END-OF-SESSION CHECKLIST — Save Progress and Close**

Run this command to close the current session, capture knowledge, and leave a clean state for the next Claude.

**Do NOT query `claude_family.*`, `claude_pm.*`, or `nimbus_context.*` tables. Do NOT use `mcp__memory__*` tools. Use `mcp__project-tools__end_session` and `remember()` instead.**

---

## Execute These Steps

### Step 1: Capture Reusable Knowledge

For every pattern, gotcha, or decision discovered this session, call `remember()`:

```
mcp__project-tools__remember(
    content="[What you learned — be specific]",
    memory_type="pattern"   -- or "fact", "decision", "gotcha", "procedure"
)
```

**When to remember:**
- A non-obvious behavior or constraint discovered (gotcha)
- A decision made with reasoning that should persist (decision)
- A reusable technique confirmed to work (pattern)
- A learned fact about the codebase or system (fact)

Skip this step if nothing notable was learned.

### Step 2: End the Session (Single Call)

Call `mcp__project-tools__end_session` with:
- `summary` - 2-4 sentences: what was accomplished, key decisions, outcome
- `outcome` - One of: `success`, `partial`, `blocked`, `abandoned`
- `files_modified` - List of significant files changed (optional)

```
mcp__project-tools__end_session(
    summary="Brief description of what was accomplished this session",
    outcome="success",
    files_modified=["path/to/file1.py", "path/to/file2.md"]
)
```

This closes the session in `claude.sessions`, triggers `consolidate_memories()` to promote short-term session facts, and formats the closing summary.

### Step 3: Commit Changes (If Applicable)

If there are uncommitted changes that should be committed:

```bash
git status --short
git add -A
git commit -m "type: description [BT-code or F-code]"
```

Follow commit format from `.claude/rules/commit-rules.md`.

### Step 4: Display Closing Summary

Display the `display` string from Step 2. Done.

---

## Session Knowledge Guidelines

| Discovered | Action |
|-----------|--------|
| Reusable pattern or technique | `remember(type="pattern")` |
| Non-obvious gotcha | `remember(type="gotcha")` |
| Architecture decision | `remember(type="decision")` |
| Project fact or config | `remember(type="fact")` |
| Detailed vault document needed | Create file in `knowledge-vault/00-Inbox/` |

**Prefer `remember()` for concise facts. Create vault docs only for topics needing 200+ lines of explanation.**

---

## Checklist

Before ending, verify:

- [ ] Called `remember()` for each reusable insight (if any)
- [ ] Called `end_session()` with summary and outcome
- [ ] Uncommitted work committed or intentionally left staged
- [ ] User is aware of any blockers or next steps

---

**Version**: 2.0 (Rewrote: use mcp__project-tools__end_session + remember(), removed retired schemas/tools)
**Created**: 2025-12-20
**Updated**: 2026-03-09
**Location**: .claude/commands/session-end.md
