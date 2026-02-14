**CHECKPOINT SESSION PROGRESS (Without Closing)**

Save current progress mid-session. Use this when you want to preserve state without ending the session.

---

## Execute These Steps

### Step 1: Review Current Work

Check what's been done this session:

```bash
git status --short
git diff --stat
```

Review your task list (TaskList) for completed/pending items.

### Step 2: Save Session Notes (MCP)

Call `mcp__project-tools__store_session_notes` with:
- `progress`: What has been completed so far (bullet points)
- `decisions`: Key decisions made (if any)
- `blockers`: Any blockers encountered (if any)

### Step 3: Store Key Findings as Session Facts

For any important discoveries, decisions, or credentials found during the session:

Call `mcp__project-tools__store_session_fact` with:
- `key`: Short identifier (e.g., "finding_auth_bug", "decision_api_pattern")
- `value`: The finding/decision details
- `fact_type`: One of: credential, config, endpoint, decision, note, data, reference
- `is_sensitive`: true for credentials/secrets

### Step 4: Store Knowledge (If Applicable)

If you discovered a reusable pattern, gotcha, or solution:

Call `mcp__project-tools__store_knowledge` with:
- `title`: Clear name
- `content`: What was learned
- `knowledge_type`: pattern, gotcha, solution, fact, or procedure
- `topic`: Relevant topic
- `confidence`: 1-100

### Step 5: Confirm

Display a brief checkpoint summary:
- Tasks completed so far
- Session notes saved
- Session facts stored
- "Session still active - continue working or use `/session-end` when done"

---

## Notes

- **Does NOT close the session** - session remains active in `claude.sessions`
- **Survives compaction** - session facts and notes persist even if context is compressed
- **Use before risky changes** - checkpoint before large refactors or experiments
- **Not a commit** - use `/session-commit` if you also want to git commit

---

**Version**: 1.0
**Created**: 2026-02-14
**Updated**: 2026-02-14
**Location**: .claude/commands/session-save.md
