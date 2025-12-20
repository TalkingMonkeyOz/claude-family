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
│   └── skills/            # Domain skills (nimbus-api, etc.)
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

## Process Guidance (MANDATORY)

When you see `<process-guidance>` tags injected by the process router hook:

1. **MUST Follow Steps**: Execute each step in the order listed
2. **MUST NOT Skip [BLOCKING]**: Blocking steps must complete before proceeding
3. **MUST Use TodoWrite**: Add all workflow steps to your todo list immediately
4. **MUST Track Progress**: Mark todos in_progress/completed as you work
5. **MUST Check column_registry**: Before any database write, verify valid values

**Example Response Pattern**:
```
I see this triggers the Bug Fix Workflow. Let me follow the steps:

[TodoWrite with all steps]

Step 1: Create Feedback Entry...
[Execute step]
[Mark todo completed]

Step 2: Investigate Root Cause...
[Execute step]
...
```

**If Workflow Doesn't Apply**: State why and proceed normally.

**Process Registry**: 32 workflows across 7 categories (COMM, DATA, DEV, DOC, PROJECT, QA, SESSION)

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

Complete knowledge lifecycle for institutional memory:

```
CAPTURE ──────> STORE ──────> DELIVER
(Obsidian)    (PostgreSQL)   (Hooks)
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Obsidian Vault** | `knowledge-vault/` | Markdown knowledge capture with YAML frontmatter |
| **Sync Script** | `scripts/sync_obsidian_to_db.py` | Vault → Database sync |
| **Process Router** | `scripts/process_router.py` | Keyword-based knowledge retrieval |
| **Retrieval Log** | `claude.knowledge_retrieval_log` | Observability for what knowledge is queried |
| **Enforcement Log** | `claude.enforcement_log` | Tracks reminder triggers |

### Key Commands

- `/knowledge-capture` - Save a learning to the Obsidian vault
- `/session-end` - Prompts for session learnings before close

### Sync Knowledge

```bash
# Dry run (see what would sync)
python scripts/sync_obsidian_to_db.py --dry-run

# Actually sync
python scripts/sync_obsidian_to_db.py

# Force resync everything
python scripts/sync_obsidian_to_db.py --force
```

### Test Suite

```bash
# Run all 15 user story tests
python scripts/run_regression_tests.py --verbose

# Quick mode (first 7 tests)
python scripts/run_regression_tests.py --quick
```

---

## Recent Changes

| Date | Change |
|------|--------|
| 2025-12-20 | Config restructure: Created Family Rules.md, updated global CLAUDE.md with vault refs, removed stale shared CLAUDE.md |
| 2025-12-20 | Fixed P0 postgres password bug, timeout single source of truth, PostToolUse hook |
| 2025-12-18 | Implemented Knowledge System (Obsidian vault, sync script, logging) |
| 2025-12-18 | Created test suite for all 15 user stories from spec |
| 2025-12-18 | Added skills folder (.claude/skills/) with nimbus-api placeholder |
| 2025-12-08 | Added MANDATORY Process Guidance section - Claude must follow workflow steps |
| 2025-12-08 | Workflow regression: All 32 processes now have steps and triggers |
| 2025-12-08 | Added 7 new triggers (IDs 47-53) for 6 processes |
| 2025-12-06 | Proposed Tool Search for deferred loading (ADR-004) |
| 2025-12-06 | Added beta headers support (1M context, interleaved thinking) |
| 2025-12-06 | Added LLM-as-Judge pattern to reviewer-sonnet |
| 2025-12-06 | Created git worktrees SOP for parallel work |
| 2025-12-06 | Implemented async agent workflow (ADR-003) |
| 2025-12-04 | Created Claude Governance System Plan |
| 2025-12-04 | Added Data Gateway (column_registry, CHECK constraints) |

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

**Version**: 2.4 (Config restructure, vault integration)
**Created**: 2025-10-21
**Updated**: 2025-12-20
**Location**: C:\Projects\claude-family\CLAUDE.md
