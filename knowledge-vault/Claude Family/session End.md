---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.775851'
---

# Session End Workflow

**Command**: `/session-end`

## What It Does

1. Prompts for session summary
2. Saves to `claude.sessions`
3. Updates `TODO_NEXT_SESSION.md`
4. Captures learnings to vault

## Hook

`session_end_hook.py` checks for doc updates.

## Mandatory

Run before closing EVERY session.

See also: [[Claude Family todo Session Start]], [[Claude Hooks]]