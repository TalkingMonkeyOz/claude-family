---
name: session-management
description: Session start/end workflows for Claude Family
model: haiku
allowed-tools:
  - Read
  - mcp__postgres__*
  - mcp__project-tools__check_inbox
---

# Session Management Skill

**Status**: Active

---

## Overview

Session lifecycle management: starting sessions, ending sessions, resuming work, and session logging.

**Detailed reference**: See [reference.md](./reference.md) for SQL queries, todo persistence, and smart resume details.

---

## When to Use

- Starting a new Claude Code session
- Ending a session and logging work
- Resuming from a previous session
- Creating session summaries
- Managing session context

---

## Quick Reference

### Session Lifecycle Commands

| Command | Purpose | When |
|---------|---------|------|
| `/session-start` | Initialize session logging | Start of every session |
| `/session-end` | Log summary and clean up | End of every session |
| `/session-status` | View project state (DB-driven) | Quick status check |
| `/session-commit` | Complete session + git commit | End with git commit |
| `/session-resume` | Load previous session context | Continuing work |

---

## Session Start Protocol

**MANDATORY at session start**: `/session-start`

**What it does**:
1. Creates `claude.sessions` record
2. Sets `CLAUDE_SESSION_ID` environment variable
3. Records identity, project, start time
4. Enables session-scoped logging

**Skip only if**: Session already logged by automated hook

---

## Session End Protocol

**MANDATORY at session end**: `/session-end`

**What it does**:
1. Updates `claude.sessions` with summary
2. Records `session_end` timestamp
3. Logs work completed
4. Captures key decisions

**Alternative**: `/session-commit` combines session end + git commit

---

## Session Summary Best Practices

When ending a session, provide:

1. **What was completed** - List key accomplishments
2. **What's pending** - Unfinished work, blockers
3. **Key decisions** - Architectural choices, trade-offs
4. **Next steps** - Clear continuation point

```
Session Summary:
- Completed: Implemented user authentication with JWT
- Pending: Need to add refresh token logic
- Decisions: Using httpOnly cookies (not localStorage) for security
- Next: Add token refresh endpoint, then test login flow
```

---

## Related Skills

- `project-ops` - Project lifecycle management
- `messaging` - Inter-session communication
- `work-item-routing` - Creating session tasks

---

## Key Gotchas

1. **Skipping session start/end** — loses context for future sessions
2. **Vague summaries** — "Worked on the project" provides no value; be specific
3. **Not tracking parent sessions** — use `parent_session_id` when spawning agents

---

**Version**: 3.0 (Progressive disclosure: split to SKILL.md overview + reference.md detail)
**Created**: 2025-12-26
**Updated**: 2026-03-29
**Location**: .claude/skills/session-management/SKILL.md
