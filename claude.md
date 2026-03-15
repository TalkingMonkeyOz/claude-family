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

**Regenerate manually:** `python scripts/generate_project_settings.py <project-name>` (run from project directory)

**Full details**: See `knowledge-vault/40-Procedures/config-management/Config Management SOP.md`

---

## Current Phase

**Phase**: Implementation
**Focus**: Infrastructure optimization and governance enforcement

---

## Architecture Overview

Infrastructure for the Claude Family ecosystem:
- **Database**: PostgreSQL `ai_company_foundation`, schema `claude` (58 tables)
- **MCP Servers**: postgres, project-tools (~60 tools), python-repl, sequential-thinking, bpmn-engine
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
| A task to do | build_tasks | `create_linked_task(feature_code, ...)` |
| Work right now | TodoWrite | session only |

**Data Gateway**: Before writing, check `claude.column_registry` for valid values.

### Workflow Tools (v3 Application Layer)

Status changes go through the **WorkflowEngine** state machine. Invalid transitions are rejected.

| Tool | Use When |
|------|----------|
| `advance_status(type, id, status)` | Move any item through its state machine |
| `start_work(task_code)` | Start a build task (todo→in_progress + loads plan_data) |
| `complete_work(task_code)` | Finish a task (in_progress→completed + suggests next task) |
| `get_work_context(scope)` | Token-budgeted context: current/feature/project |
| `create_linked_task(feature, name, desc, verification, files)` | Add detailed task to active feature |

### Config Tools (v3)

| Tool | Use When |
|------|----------|
| `update_claude_md(project, section, content)` | Update a CLAUDE.md section atomically |
| `deploy_claude_md(project)` | Deploy CLAUDE.md from DB to file (one-way) |
| `deploy_project(project, components)` | Deploy settings/rules/skills from DB |
| `regenerate_settings(project)` | Regenerate settings.local.json from DB |

### Memory Tools (F130 - Cognitive Memory)

3-tier memory system: SHORT (session facts) → MID (working knowledge) → LONG (proven patterns).

| Tool | Use When |
|------|----------|
| `remember(content, memory_type)` | Learn something — auto-routes to right tier, dedup/merge, auto-link |
| `recall_memories(query, budget)` | Load context before tasks — 3-tier retrieval, budget-capped |
| `consolidate_memories(trigger)` | Lifecycle: promote short→mid, mid→long, decay, archive |

**Prefer these over** `store_knowledge` / `recall_knowledge` (legacy, still available).

### Knowledge Tools (v3)

| Tool | Use When |
|------|----------|
| `store_book(title, author, ...)` | Add book to reference library |
| `store_book_reference(book, concept, ...)` | Add concept reference with embedding |
| `recall_book_reference(query, ...)` | Semantic search over book references |
| `catalog(entity_type, properties, ...)` | Store structured entity (book, API, OData, pattern) |
| `recall_entities(query, entity_type?, ...)` | RRF search over cataloged entities |
| `extract_insights(session_id)` | Extract knowledge from past conversations |
| `search_conversations(query, ...)` | Full-text search across stored conversations |
| `extract_conversation(session_id)` | Parse JSONL conversation log |

### Filing Cabinet Tools (Cross-Session Component Context)

Project-scoped working files that bridge sessions. Filing cabinet metaphor: project = cabinet, component = drawer, title = file.

| Tool | Use When |
|------|----------|
| `stash(component, title, content)` | Save component working context (approach notes, findings, questions) |
| `unstash(component, title?)` | Retrieve workfile(s) by component, updates access stats |
| `list_workfiles(project?, component?)` | Browse cabinet — component counts, pinned status |
| `search_workfiles(query)` | Semantic search across workfiles via Voyage AI |

**Key features**: UPSERT on (project, component, title), `mode="append"` to concatenate, `is_pinned=True` for session-start surfacing. Pinned workfiles preserved in precompact.

### Work Context Container (WCC) — Automatic Activity-Based Context

WCC automatically detects which activity you're working on and assembles relevant context from 6 sources. Runs in the RAG hook — no manual tool calls needed.

**How it works**: Every prompt → `detect_activity()` → if changed → `assemble_wcc()` queries workfiles, knowledge, features, facts, vault, BPMN → cached → injected at priority 2 → per-source RAG skipped.

| Tool | Use When |
|------|----------|
| `create_activity(name, aliases, desc)` | Explicitly create an activity with aliases for detection |
| `list_activities(project)` | Browse activities and access stats |
| `update_activity(id, aliases, is_active)` | Manage aliases, deactivate stale activities |
| `assemble_context(name, budget)` | Manual WCC assembly (debugging/inspection) |

**Detection priority**: 1) `session_fact("current_activity")` override, 2) exact name/alias match, 3) word overlap, 4) workfile component fallback.

**State Machines** (enforced by `claude.workflow_transitions`):
- **Feedback**: new → triaged → in_progress → resolved
- **Features**: draft → planned → in_progress → completed (requires all_tasks_done)
- **Build tasks**: todo → in_progress → completed (triggers feature check)

All transitions logged to `claude.audit_log`.

---

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

- **New project**: See `knowledge-vault/40-Procedures/New Project SOP.md`
- **Add MCP**: See `knowledge-vault/40-Procedures/Add MCP Server SOP.md`
- **Manage config**: See `knowledge-vault/40-Procedures/config-management/Config Management SOP.md`

## Key Procedures

1. **Session Start** - Automatic via SessionStart hook (logs session, loads todos, checks messages)
2. `/session-end` - Run manually to save summary and learnings
3. Data writes - Check column_registry for valid values
4. Config changes - Update database, files regenerate automatically

---

## Skills System (ADR-005)

**Architecture**: Skills-First (replaced process_router)

Core skills available:

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
| bpmn-modeling | BPMN-first process design, query/model/test workflows |

**Usage**: When a skill applies, use the `Skill` tool to invoke it.

**Legacy**: Process registry archived (25 active, 7 deprecated). See ADR-005 for migration details

---

## Auto-Apply Instructions

Coding standards in `~/.claude/instructions/` auto-apply based on file patterns.

**Available** (9 files): csharp, winforms, winforms-dark-theme, wpf-ui, mvvm, a11y, sql-postgres, playwright, markdown

**Override**: Create `.claude/instructions/[name].instructions.md` for project-specific rules.

---

## Knowledge System

3-tier memory: SHORT (session facts) → MID (working knowledge) → LONG (proven patterns). `remember()` auto-routes, `recall_memories()` retrieves with budget cap. `consolidate_memories()` promotes/decays/archives (auto on session end + 24h periodic). Vault docs in `knowledge-vault/` auto-searched via RAG hook. See `storage-rules.md` for which system to use.

---

## Recent Changes

| Date | Change |
|------|--------|
| 2026-03-15 | **Unified Deployment System**: Created `sync_project.py` replacing 3 scripts (generate_project_settings, generate_mcp_config, deploy_project_configs) + shared folder copy. All components (skills, commands, agents, rules) now DB-backed in `claude.skills` table with new scopes (`command`, `agent`). Launcher updated to single `sync_project.py` call. Background job scheduler activated via Windows Task Scheduler. No-loose-ends rule added. |
| 2026-03-14 | **Background Job Runner**: `job_runner.py` + `setup_scheduler.bat` + 6 new maintenance jobs (bpmn-sync, knowledge-decay, memory-consolidation, system-maintenance, vault-embeddings, insight-extraction). Removed 4 WCC tools from MCP surface. Storage skill created (`/skill-load-memory-storage`). |
| 2026-03-13 | **Entity Catalog System**: Type-extensible entity storage with RRF search. 3 new tables (`entity_types`, `entities`, `entity_relationships`), 2 new MCP tools (`catalog`/`recall_entities`), BPMN model + 15 tests, book data migration (49 entities). Core Protocol v12. |
**Full changelog**: See git log

---

**Version**: 4.2 (Trimmed: removed duplicates with global CLAUDE.md, condensed knowledge section)
**Created**: 2025-10-21
**Updated**: 2026-03-15
**Location**: C:\Projects\claude-family\CLAUDE.md
