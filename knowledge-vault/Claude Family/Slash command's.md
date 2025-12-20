---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T12:04:35.253508'
---

# Slash Commands

Quick actions via `/command` syntax.

## Locations

| Location | Scope |
|----------|-------|
| `~/.claude/commands/` | Global (all projects) |
| `.claude/commands/` | Project-specific |

## Core Commands

| Command | Purpose |
|---------|---------|
| `/session-start` | Begin session |
| `/session-end` | End session |
| `/feedback-check` | View open issues |
| `/feedback-create` | New issue |
| `/knowledge-capture` | Save learning |
| `/project-init` | New project |

## Creating Commands

1. Create `.claude/commands/{name}.md`
2. Add template with `$ARGUMENTS` for params
3. Reference process in `process_registry`

See also: [[Plugins]], [[Claude Hooks]]