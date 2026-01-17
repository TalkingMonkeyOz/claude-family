---
projects:
- claude-family
tags:
- procedure
- debugging
- session
synced: false
---

# Session Self-Diagnosis SOP

When a session feels "off" - wrong context, unexpected references, confusion about identity or project - follow this diagnostic procedure.

---

## Quick Identity Check

Run these immediately when confused:

```bash
# 1. What project am I in?
pwd
cat CLAUDE.md | head -20

# 2. What session ID am I?
grep -o '"session_id":"[^"]*"' ~/.claude/logs/*.jsonl | tail -1
```

```sql
-- 3. Verify project in database
SELECT project_id, project_name, current_phase, status
FROM claude.projects WHERE project_name = 'MY-PROJECT-NAME';
```

---

## Unexpected References Diagnosis

If seeing references to OTHER projects (e.g., nimbus in claude-family):

### Check 1: Conversation History
```bash
# Count references in current session log
grep -c "OTHER_PROJECT" ~/.claude/projects/C--Projects-CURRENT/*.jsonl | tail -1

# Find where they came from
grep -o '"content":"[^"]*OTHER_PROJECT[^"]*"' LOGFILE.jsonl | head -5
```

**Common causes**:
- User mentioned it in their message
- Summary context from crashed/previous session
- Cross-project queries you ran
- Background tasks searching across projects

### Check 2: RAG Context Injection
```bash
# Recent RAG queries (may pull cross-project docs)
tail -50 ~/.claude/hooks.log | grep -i "rag\|vault"
```

### Check 3: Summary Context
Look at the top of the session for `<summary>` or system messages mentioning other projects.

---

## Feature/Plan Recovery

When asked "what were we working on?" or after a crash:

### Step 1: Check Database Plans
```sql
-- Active features for this project
SELECT 'F' || short_code, feature_name, status, plan_data
FROM claude.features
WHERE project_id = 'PROJECT_UUID' AND status IN ('in_progress', 'planned')
ORDER BY updated_at DESC;
```

### Step 2: Check Plan Files
```bash
# Plan files from recent sessions
ls -lt ~/.claude/plans/*.md | head -5
```

### Step 3: Check Inter-Claude Messages
```sql
SELECT subject, body, created_at
FROM claude.messages
WHERE to_project = 'PROJECT_NAME' AND body LIKE '%plan%'
ORDER BY created_at DESC LIMIT 5;
```

### Step 4: Check Conversation Logs
```bash
# Find recent .jsonl files for project
ls -lt ~/.claude/projects/C--Projects-PROJECT/*.jsonl | head -5

# Search for plan content
grep -o '"content":".*Plan.*"' LOGFILE.jsonl | head -10
```

---

## Session Context Contamination

If context seems "polluted" with unrelated information:

### Symptom: Wrong project context
**Cause**: Usually summary context from previous session or user's message mentioning other projects.
**Fix**: Re-read current project's CLAUDE.md and clarify with user.

### Symptom: Outdated information
**Cause**: Summary may contain stale data from before crash.
**Fix**: Re-query database for current state.

### Symptom: Conflicting instructions
**Cause**: Global CLAUDE.md vs project CLAUDE.md vs skills.
**Fix**: Project CLAUDE.md takes precedence. Re-read it.

---

## Verification Checklist

After diagnosis, verify:

- [ ] Correct project CLAUDE.md read
- [ ] Project ID matches database
- [ ] Active features/todos are for THIS project
- [ ] No conflicting session context

---

## When to Use This SOP

- Session feels "confused" about identity
- Unexpected project references appearing
- After crash/context compaction
- User asks "what's going on?"
- Feature work seems misaligned

---

## Related

- [[Session Lifecycle - Overview]]
- [[Feature Planning System]]
- [[Interlinked Documentation Pattern]]

---

**Version**: 1.0
**Created**: 2026-01-17
**Location**: knowledge-vault/40-Procedures/Session Self-Diagnosis SOP.md
