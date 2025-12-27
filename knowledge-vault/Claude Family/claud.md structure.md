---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.746952'
tags:
- quick-reference
- claude-family
---

# CLAUDE.md Hierarchy

Three-level merge (loaded in order):

| Level      | Path                              | Scope            |
| ---------- | --------------------------------- | ---------------- |
| 1. Global  | `~/.claude/CLAUDE.md`             | All projects     |
| 2. Shared  | `C:\claude\shared\docs\CLAUDE.md` | Shared rules     |
| 3. Project | `{project}/CLAUDE.md`             | Project-specific |

## Key Sections

- Identity & database connection
- MCP servers available
- Session workflows (mandatory)
- Code style & repo rules
- Work tracking guidance

## Enforcement

- [[Claude Hooks]] validate on write
- Git pre-commit: max 250 lines
- Keep concise, link to docs/

See also: [[Setting's File]], [[MCP configuration]]
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: Claude Family/claud.md structure.md