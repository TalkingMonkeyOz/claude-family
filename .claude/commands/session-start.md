**MANDATORY SESSION STARTUP PROTOCOL**

Session logging is **AUTOMATIC** via SessionStart hook. This command provides additional context loading if needed.

---

## What Happens Automatically

The SessionStart hook already:
1. Logs session to `claude.sessions`
2. Loads active todos from `claude.todos`
3. Checks for pending messages via orchestrator
4. Queries RAG for relevant vault context

---

## Optional: Load Additional Context

### Check Last Session State

```sql
SELECT current_focus, next_steps
FROM claude.session_state
WHERE project_name = '{project_name}';
```

### Check Open Feedback

```sql
SELECT feedback_type, COUNT(*) as count
FROM claude.feedback f
JOIN claude.workspaces w ON f.project_id = w.project_id
WHERE w.project_name = '{project_name}'
  AND f.status IN ('new', 'in_progress')
GROUP BY feedback_type;
```

### Check Active Features

```sql
SELECT 'F' || short_code as code, feature_name, status
FROM claude.features f
JOIN claude.workspaces w ON f.project_id = w.project_id
WHERE w.project_name = '{project_name}'
  AND f.status IN ('planned', 'in_progress');
```

---

## Quick Start Checklist

- [x] Session logged (automatic via hook)
- [x] Todos loaded (automatic via hook)
- [x] Messages checked (automatic via hook)
- [ ] Review session_state for context (if resuming work)
- [ ] Check git status for uncommitted changes

---

**Note**: Most startup steps are now handled by hooks. This command is for additional context when needed.

---

**Version**: 3.0
**Created**: 2025-10-21
**Updated**: 2026-01-10
**Location**: .claude/commands/session-start.md
