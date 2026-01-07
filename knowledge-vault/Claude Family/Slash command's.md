---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.779590'
tags:
- quick-reference
- claude-family
---

# Slash Commands

Quick actions via `/command` syntax.

---

## Command Architecture

**Status**: File-based (not yet database-driven like hooks/MCPs)

**Current Design**:
- Global commands → `~/.claude/commands/` (apply to ALL projects)
- Shared commands → `claude-family/.claude/commands/`
- Project commands → `{project}/.claude/commands/`

**Priority**: Project > Global (project-level overrides global)

---

## Session Commands

| Command | Purpose | Source |
|---------|---------|--------|
| `/session-start` | Auto via hook (manual if needed) | Automatic |
| `/session-resume` | Database-driven context (todos, focus, last session) | Global |
| `/session-end` | Save summary and learnings | Project |
| `/session-commit` | Session end + git commit | Project |
| `/session-status` | Quick read-only status check | Project |

**Note**: Session start is automatic via SessionStart hook. `/session-resume` queries the database for todos, focus, and last session summary.

---

## Shared Commands (claude-family)

| Command | Purpose |
|---------|---------|
| `/feedback-check` | View open feedback |
| `/feedback-create` | Create new feedback |
| `/feedback-list` | List/filter feedback |
| `/project-init` | Initialize new project |
| `/phase-advance` | Advance project phase |
| `/check-compliance` | Check project compliance |
| `/knowledge-capture` | Save learning to vault |
| `/review-docs` | Review doc staleness |
| `/review-data` | Review data quality |
| `/todo` | Persistent TODO management |

**Location**: `C:\Projects\claude-family\.claude\commands\`

---

## Project-Specific Commands

**ATO-Tax-Agent**:
- `/ato-compliance-check` - Tax compliance verification
- `/ato-test-scenarios` - Tax scenario testing
- `/ato-validate` - Tax validation rules

**Location**: `{project}\.claude\commands\`

---

## Data Sources

Session commands query the `claude.*` schema:
- `claude.sessions` - Session history and summaries
- `claude.session_state` - Current focus, next_steps
- `claude.todos` - Active todos with priorities
- `claude.messages` - Pending messages

---

## Change History

| Date | Change |
|------|--------|
| 2026-01-07 | Updated session-resume to database-driven (global) |
| 2025-12-27 | Removed duplicate commands from ATO-Tax-Agent |

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2026-01-07
**Location**: Claude Family/Slash command's.md
