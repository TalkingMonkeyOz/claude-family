---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.753880'
---

# Session Start Workflow

**Command**: `/session-start`

## What It Does

1. Logs session to `claude.sessions`
2. Checks inbox for messages
3. Loads previous context
4. Restores pending todos

## Hook

`session_startup_hook.py` runs on SessionStart event.

## Mandatory

Run at start of EVERY session - see [[claud.md structure]]

See also: [[session End]], [[Claude Hooks]]