---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.775851'
tags:
- session
- quick-reference
- claude-family
---

# Session End Workflow

**Command**: `/session-end`

## What It Does

1. Updates session record in `claude.sessions` with summary
2. Saves tasks_completed, learnings_gained, challenges_encountered
3. Optionally updates `claude.session_state` with new focus/next_steps
4. Optionally stores reusable patterns in `claude.knowledge`

## Schema

Uses `claude.*` schema (consolidated):
- `claude.sessions` - Session record with summary
- `claude.session_state` - Persistent focus and next_steps
- `claude.knowledge` - Reusable patterns

## When to Run

- End of work day
- Before long break
- After major milestone
- When switching projects

## Related Commands

| Command | Purpose |
|---------|---------|
| `/session-commit` | Session end + git commit (recommended for normal work) |
| `/session-resume` | Database-driven context at session start |
| `/session-status` | Quick read-only status check |

See also: [[Session Quick Reference]], [[Session Lifecycle - Overview]], [[Claude Hooks]]

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2026-01-07
**Location**: Claude Family/session End.md
