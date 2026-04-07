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

## CRITICAL: Config Management (READ FIRST)

**Database is source of truth for config.**

| File | Source | Behavior |
|------|--------|----------|
| `.claude/settings.local.json` | `config_templates` + `workspaces.startup_config` | Generated from DB. Manual edits overwritten by `regenerate_settings()`. |
| `CLAUDE.md` | `profiles.config->behavior` | Stored in DB. Edit via `update_claude_md()`. Deploy via `deploy_claude_md()`. Manual file edits are OK but won't persist to DB. |

**DO NOT manually edit settings.local.json** - changes will be overwritten.

**To change config permanently:**
```sql
-- All projects: Update config_templates (template_id=1 = hooks-base)
-- Project type: Update project_type_configs
-- Single project: Update workspaces.startup_config
```

**Regenerate manually:** `python scripts/sync_project.py` (run from project directory)

**Full details**: See [[Config Management SOP]]

## Current Phase

**Phase**: Implementation
**Focus**: Infrastructure optimization and governance enforcement

---

## Architecture Overview

Infrastructure for the Claude Family ecosystem:
- **Database**: PostgreSQL `ai_company_foundation`, schema `claude` (60+ tables)
- **MCP Servers**: postgres, project-tools (~60 tools), python-repl, sequential-thinking, bpmn-engine
- **Enforcement**: Hooks, database constraints, column_registry
- **Knowledge**: Vault embeddings (RAG) for semantic search
- **UI**: Mission Control Web (MCW) for visibility

**Full details**: See `ARCHITECTURE.md`

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

**File placement rules**: See [[File Placement Standards]] for where new files should go, line limits, and DB-managed file rules.

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
| A task to do | build_tasks | `create_linked_task(feature_code, ...)` |
| Work right now | TodoWrite | session only |

**Data Gateway**: Before writing, check `claude.column_registry` for valid values.

**Task tool preference**: Use `create_linked_task` by default (enforces quality: description >=100 chars, verification, files). Use `add_build_task` only for quick/informal tasks.

### Workflow Tools (Application Layer)

Status changes go through the **WorkflowEngine** state machine. Invalid transitions are rejected.

| Tool | Use When |
|------|----------|
| `advance_status(type, id, status)` | Move any item through its state machine |
| `start_work(task_code)` | Start a build task (todo→in_progress + loads plan_data) |
| `complete_work(task_code)` | Finish a task (in_progress→completed + suggests next task) |
| `get_work_context(scope)` | Token-budgeted context: current/feature/project |
| `create_linked_task(feature, name, desc, verification, files)` | Add detailed task to active feature |

### Config Tools (v3+)

| Tool | Use When |
|------|----------|
| `update_config(component_type, project, name, content, reason)` | **Update ANY config (skill/rule/instruction/claude_md) with versioning + deploy** |
| `update_claude_md(project, section, content)` | Update a CLAUDE.md section atomically |
| `deploy_claude_md(project)` | Deploy CLAUDE.md from DB to file (one-way) |
| `deploy_project(project, components)` | Deploy settings/rules/skills from DB |
| `regenerate_settings(project)` | Regenerate settings.local.json from DB |

## Configuration (Database-Driven)

**Project Type**: `infrastructure` (inherits defaults from `project_type_configs`)

**Config Flow**: Database → `sync_project.py` → all project files (settings.local.json, .mcp.json, skills, commands, rules, agents)

**Self-Healing**: All configs regenerate from database on every launch and SessionStart. Manual file edits are temporary.

**Customization**: Update `claude.workspaces.startup_config` (JSONB) to override defaults.

**Components in DB**: `claude.skills` (scope: global/project/command/agent), `claude.rules`, `claude.instructions`

**Details**: See [[Config Management SOP]]

---

## Standard Operating Procedures

**Workflow**: CLAUDE.md → Vault SOP → Skill → Done

- **New project**: See [[New Project SOP]]
- **Add MCP**: See [[Add MCP Server SOP]]
- **Manage config**: See [[Config Management SOP]]

## Key Procedures

1. **Session Start** - Automatic via SessionStart hook (logs session, loads todos, checks messages)
2. `/session-end` - Run manually to save summary and learnings
3. Data writes - Check column_registry for valid values
4. Config changes - Update database, files regenerate automatically

---

## Skills System (ADR-005)

## Skills, Instructions & Information Discovery

**Skills**: 32 skills in `.claude/skills/`. Use the `Skill` tool when a task matches. See Global CLAUDE.md for full skill list and descriptions.

**Instructions**: Auto-apply coding standards based on file patterns. See Global CLAUDE.md for available standards.

**Information Discovery**: See [[Information Discovery Architecture]] for the full 8-layer model — how information flows from CLAUDE.md through protocol, rules, RAG, skills, and MCP tools.

## Auto-Apply Instructions

Coding standards in `~/.claude/instructions/` auto-apply based on file patterns. See Global CLAUDE.md for available standards and override instructions.

## Knowledge System

3-tier memory: SHORT (session facts) → MID (working knowledge) → LONG (proven patterns). `remember()` auto-routes, `recall_memories()` retrieves with budget cap. `consolidate_memories()` promotes/decays/archives (auto on session end + 24h periodic). Vault docs in `knowledge-vault/` auto-searched via RAG hook. See storage-rules (auto-loaded via `.claude/rules/`) for which system to use.

## Recent Changes

| Date | Change |
|------|--------|
| 2026-03-17 | **Routing Fix**: Replaced hardcoded vault paths in CLAUDE.md with wiki-links and tool-based routing. Entity catalog is the indirection layer — paths change in catalog, CLAUDE.md stays stable. |
| 2026-03-15 | **Unified Deployment System**: Created `sync_project.py` replacing 3 scripts. All components DB-backed. Background job scheduler activated. No-loose-ends rule added. |
| 2026-03-14 | **Background Job Runner**: `job_runner.py` + 6 maintenance jobs. Storage skill created (see `storage-rules` for usage). |
| 2026-03-13 | **Entity Catalog System**: Type-extensible entity storage with RRF search. 3 new tables, 2 new MCP tools (`catalog`/`recall_entities`). |
**Full changelog**: See git log

| 2026-04-07 | **Entity Catalog v2** [F187]: Deep property search (BM25 indexes JSONB content), `explore_entities()` 3-stage progressive disclosure browser, relationship walking (OData nav props + domain concept refs). See [[Entity Catalog: Search vs Browse Pattern]]. |

