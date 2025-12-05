# Claude Family - Infrastructure Project

**Type**: Infrastructure
**Status**: Implementation
**Project ID**: `20b5627c-e72c-4501-8537-95b559731b59`

---

## Problem Statement

Enable coordinated AI-assisted software development across multiple Claude instances with:
- Consistent project structure and documentation
- Enforced procedures via hooks and constraints
- Shared knowledge that persists across sessions
- Quality data in tracking systems

**Full details**: See `PROBLEM_STATEMENT.md`

---

## Current Phase

**Phase**: Implementation (governance system)
**Focus**: Building the Claude Governance System (Phase A)
**Plan**: `docs/CLAUDE_GOVERNANCE_SYSTEM_PLAN.md`

---

## Architecture Overview

Infrastructure for the Claude Family ecosystem:
- **Database**: PostgreSQL `ai_company_foundation`, schema `claude`
- **MCP Servers**: orchestrator, postgres, memory, filesystem
- **Enforcement**: Hooks, database constraints, column_registry
- **UI**: Mission Control Web (MCW) for visibility

**Full details**: See `ARCHITECTURE.md`

---

## Project Structure

```
claude-family/
├── CLAUDE.md              # This file - AI constitution
├── PROBLEM_STATEMENT.md   # Problem definition
├── ARCHITECTURE.md        # System design
├── .claude/commands/      # Slash commands
├── docs/
│   ├── adr/              # Architecture decisions
│   ├── sop/              # Standard operating procedures
│   └── *.md              # Plans, specs, guides
├── scripts/              # Python utilities
├── mcp-servers/          # MCP server implementations
└── templates/            # Project templates
```

---

## Coding Standards

- **Python**: PEP 8, type hints where helpful
- **SQL**: Use `claude` schema (not legacy `claude_family`, `claude_pm`)
- **Docs**: Markdown, follow template structure
- **Commits**: Descriptive messages, reference issues

---

## Work Tracking

| I have... | Put it in... | How |
|-----------|--------------|-----|
| An idea | feedback | type='idea' |
| A bug | feedback | type='bug' |
| A feature to build | features | link to project |
| A task to do | build_tasks | link to feature |
| Work right now | TodoWrite | session only |

**Data Gateway**: Before writing, check `claude.column_registry` for valid values.

---

## Key Procedures

1. **Session Start**: Run `/session-start` (auto-logs to DB)
2. **Session End**: Run `/session-end` (saves summary)
3. **Data Writes**: Check column_registry for valid values
4. **Doc Changes**: Update version footer, set updated date

**SOPs**: See `docs/sop/` folder

---

## Recent Changes

| Date | Change |
|------|--------|
| 2025-12-04 | Created Claude Governance System Plan |
| 2025-12-04 | Added Data Gateway (column_registry, CHECK constraints) |
| 2025-12-04 | Updated to new CLAUDE.md standard |
| 2025-12-04 | Cleaned test data from work_tasks, feedback |

---

## Quick Queries

```sql
-- Check project status
SELECT * FROM claude.projects WHERE project_name = 'claude-family';

-- Recent sessions
SELECT session_start, summary FROM claude.sessions
WHERE project_name = 'claude-family' ORDER BY session_start DESC LIMIT 5;

-- Valid values for any field
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

---

**Version**: 2.0 (Governance System Standard)
**Created**: 2025-10-21
**Updated**: 2025-12-04
**Location**: C:\Projects\claude-family\CLAUDE.md
