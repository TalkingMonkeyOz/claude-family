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
- Shared commands → `claude-family/.claude/commands/`
- Project commands → `{project}/.claude/commands/`

**Why**: Unlike hooks and MCPs (database-driven with distribution), commands are still file-based. Shared commands are maintained in claude-family and referenced by all projects.

---

## Shared Commands (claude-family)

| Command | Purpose |
|---------|---------|
| `/session-start` | Begin session with logging |
| `/session-resume` | Quick status view (no logging) |
| `/session-end` | End session with summary |
| `/session-commit` | End session + git commit |
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

## Migration Note (2025-12-27)

Removed duplicate commands from ATO-Tax-Agent:
- Deleted: feedback-*.md, session-*.md (6 files)
- Reason: Outdated duplicates of claude-family canonical versions
- Impact: ATO now uses claude-family shared commands only

**Future**: Convert to database-driven distribution (like hooks/MCPs)
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: Claude Family/Slash command's.md