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
- **MCP Servers**: orchestrator, postgres, memory, filesystem, vault-rag
- **Enforcement**: Hooks, database constraints, column_registry
- **Knowledge**: Vault embeddings (RAG) for semantic search
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

## Configuration (Database-Driven)

**Project Type**: `infrastructure` (inherits defaults from `project_type_configs`)

**Config Flow**: Database → `generate_project_settings.py` → `.claude/settings.local.json` (generated)

**Self-Healing**: Settings regenerate from database on every SessionStart. Manual file edits are temporary.

**Customization**: Update `claude.workspaces.startup_config` (JSONB) to override defaults.

**Details**: See [[Config Management SOP]]

---

## Standard Operating Procedures

**Workflow**: CLAUDE.md → Vault SOP → Skill → Done

- **New project**: See `knowledge-vault/40-Procedures/New Project SOP.md`
- **Add MCP**: See `knowledge-vault/40-Procedures/Add MCP Server SOP.md`
- **Manage config**: See `knowledge-vault/40-Procedures/Config Management SOP.md`

## Key Procedures

1. `/session-start` - Auto-logs to DB, syncs config
2. `/session-end` - Saves summary
3. Data writes - Check column_registry
4. Config changes - Update database, not files

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

## Auto-Apply Instructions

Coding standards auto-inject based on file patterns via `instruction_matcher.py` hook.

**Available**: csharp, winforms, a11y, sql-postgres, playwright (in `~/.claude/instructions/`)

**Override**: Create `.claude/instructions/[name].instructions.md` for project-specific rules.


---

## Knowledge System

```
CAPTURE (Obsidian) ──> EMBED (Voyage AI) ──> SEARCH (RAG) ──> DELIVER (On-Demand)
```

- **Vault**: `knowledge-vault/` - Markdown with YAML frontmatter, Obsidian-compatible
- **Embeddings**: Voyage AI (voyage-3, 1024 dimensions) → PostgreSQL pgvector
- **RAG**: `vault-rag` MCP server - Semantic search over vault (85% token reduction)
- **Versioning**: File hash tracking - only re-embed changed files
- **Commands**: `/knowledge-capture`, `/session-end`

### Using RAG

**When to search vault**:
- User asks "how do I..." procedural questions → Search SOPs
- Looking for domain knowledge (APIs, DB, WinForms, etc.) → Search 20-Domains/
- Need patterns or gotchas → Search 30-Patterns/
- Unsure which vault doc has the answer → Use semantic search

**Tools** (`vault-rag` MCP):
- `semantic_search(query)` - Find relevant chunks by natural language
- `get_document(path)` - Retrieve full document
- `list_vault_documents(folder)` - Browse available docs
- `vault_stats()` - Check embedding status

**Details**: See `knowledge-vault/Claude Family/RAG Usage Guide.md`

### Maintaining Embeddings

```bash
# Update embeddings (incremental - only changed files)
python scripts/embed_vault_documents.py

# Force re-embed everything
python scripts/embed_vault_documents.py --force
```

**Details**: See `knowledge-vault/40-Procedures/Vault Embeddings Management SOP.md`

---

## Recent Changes

| Date | Change |
|------|--------|
| 2025-12-30 | **RAG System**: vault-rag MCP, Voyage AI embeddings, file versioning, 85% token reduction |
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

**Version**: 2.8 (Database-driven config, SOP router)
**Created**: 2025-10-21
**Updated**: 2025-12-27
**Location**: C:\Projects\claude-family\CLAUDE.md
