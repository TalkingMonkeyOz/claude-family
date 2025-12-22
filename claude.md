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
├── .claude/
│   ├── commands/          # Slash commands
│   ├── instructions/      # Auto-apply coding standards
│   ├── collections/       # Agent/resource groupings
│   └── skills/            # Domain skills
├── docs/
│   ├── adr/              # Architecture decisions
│   ├── sop/              # Standard operating procedures
│   └── *.md              # Plans, specs, guides
├── knowledge-vault/       # Obsidian vault for knowledge capture
│   ├── 00-Inbox/         # Quick capture
│   ├── 10-Projects/      # Project-specific knowledge
│   ├── 20-Domains/       # Domain knowledge (APIs, DB, etc.)
│   ├── 30-Patterns/      # Reusable patterns, gotchas, solutions
│   ├── 40-Procedures/    # SOPs, Family Rules, workflows
│   └── _templates/       # Note templates
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

## Skills System (ADR-005)

**Architecture**: Skills-First (replaced process_router)

A forced-eval hook prompts skill consideration on each request. Core skills:

| Skill | Purpose |
|-------|---------|
| database-operations | SQL validation, column_registry checks |
| work-item-routing | Feedback, features, build_tasks routing |
| session-management | Session lifecycle (start/end/resume) |
| code-review | Pre-commit review, testing |
| project-ops | Project init, retrofit, phases |
| messaging | Inter-Claude communication |
| agentic-orchestration | Agent spawning, parallel work |
| testing-patterns | Test writing and execution |

**Usage**: When a skill applies, use the `Skill` tool to invoke it.

**Legacy**: Process registry archived (25 active, 7 deprecated). See ADR-005 for migration details

---

## Auto-Apply Instructions (awesome-copilot pattern)

Coding standards auto-inject based on file patterns. No manual invocation needed.

**Search Order** (project-specific overrides global):
1. `{project}/.claude/instructions/` - Project-specific
2. `~/.claude/instructions/` - Global (shared across all projects)

**Global Instructions** (`~/.claude/instructions/`):

| Instruction | Applies To | Purpose |
|-------------|-----------|---------|
| `csharp.instructions.md` | `**/*.cs` | C# conventions, async patterns |
| `winforms.instructions.md` | `**/*.Designer.cs`, `**/Forms/**/*.cs` | WinForms rules, layout strategy |
| `winforms-dark-theme.instructions.md` | `**/*Form.cs`, `**/*Control.cs` | Dark theme colors, contrast |
| `a11y.instructions.md` | `**/*.cs`, `**/*.tsx` | WCAG AA, contrast ratios |
| `sql-postgres.instructions.md` | `**/*.sql` | PostgreSQL best practices |
| `playwright.instructions.md` | `**/*.spec.ts`, `**/tests/**/*.ts` | E2E testing patterns |

**Project-Specific Instructions** (`.claude/instructions/`):

| Instruction | Applies To | Purpose |
|-------------|-----------|---------|
| `nimbus-api.instructions.md` | `**/nimbus-*/**/*` | Nimbus WFM API gotchas |

**How it works**: `instruction_matcher.py` hook runs on Edit/Write, matches file path against `applyTo` patterns, injects matching instructions into context.

**Adding new instructions**: Create `~/.claude/instructions/[name].instructions.md` for global, or `.claude/instructions/[name].instructions.md` for project-specific:
```yaml
---
description: 'What these guidelines cover'
applyTo: '**/*.ext'
---
```

---

## Collections (System Agents)

Collections group related agents for the Launcher UI:

```yaml
# .claude/collections/system-agents.collection.yml
- librarian (doc-keeper-haiku) - Knowledge vault maintenance
- config-auditor (lightweight-haiku) - Validate configs across projects
- session-cleanup (python-coder-haiku) - Archive old sessions
- inbox-monitor (lightweight-haiku) - Check for stale messages
- build-validator (tester-haiku) - Run builds, report failures
```

---

## Agent Capabilities (Beta Features)

**Enabled via `--betas` CLI flag** (requires API key auth):

| Feature | Beta Header | Agents Enabled |
|---------|-------------|----------------|
| 1M Token Context | `context-1m-2025-08-07` | architect-opus, researcher-opus, security-opus |
| Interleaved Thinking | `interleaved-thinking-2025-05-14` | All coordinators, reviewer-sonnet, opus agents |
| Token-Efficient Tools | Native in Claude 4 | All agents (no header needed) |

**Parallel Work Pattern**: Use git worktrees for multiple Claude instances on same repo.
See `docs/sops/GIT_WORKTREES_FOR_PARALLEL_WORK.md`

---

## Knowledge System

```
CAPTURE (Obsidian) ──> STORE (PostgreSQL) ──> DELIVER (Hooks)
```

- **Vault**: `knowledge-vault/` - Markdown with YAML frontmatter
- **Sync**: `python scripts/sync_obsidian_to_db.py`
- **Commands**: `/knowledge-capture`, `/session-end`
- **Tests**: `python scripts/run_regression_tests.py --verbose`

---

## Recent Changes

| Date | Change |
|------|--------|
| 2025-12-21 | **Auto-apply instructions**: instruction_matcher.py hook, 7 instruction files |
| 2025-12-21 | **Skills-First** (ADR-005): Replaced process_router, 8 core skills |
| 2025-12-21 | WinForms support: knowledge notes, agent, skill, dark theme instructions |
| 2025-12-20 | Config restructure: Family Rules.md, global CLAUDE.md update |
| 2025-12-18 | Knowledge System: Obsidian vault, sync script, test suite |

**Full changelog**: See git log or `docs/CHANGELOG.md`

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

**Version**: 2.7 (Global instructions support)
**Created**: 2025-10-21
**Updated**: 2025-12-22
**Location**: C:\Projects\claude-family\CLAUDE.md
