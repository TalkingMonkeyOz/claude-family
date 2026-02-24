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

**Full details**: See `knowledge-vault/40-Procedures/Config Management SOP.md`

---

## Current Phase

**Phase**: Implementation
**Focus**: Infrastructure optimization and governance enforcement

---

## Architecture Overview

Infrastructure for the Claude Family ecosystem:
- **Database**: PostgreSQL `ai_company_foundation`, schema `claude`
- **MCP Servers**: postgres, project-tools, python-repl, sequential-thinking, bpmn-engine
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

### Knowledge Tools (v3)

| Tool | Use When |
|------|----------|
| `store_book(title, author, ...)` | Add book to reference library |
| `store_book_reference(book, concept, ...)` | Add concept reference with embedding |
| `recall_book_reference(query, ...)` | Semantic search over book references |
| `extract_insights(session_id)` | Extract knowledge from past conversations |
| `search_conversations(query, ...)` | Full-text search across stored conversations |
| `extract_conversation(session_id)` | Parse JSONL conversation log |

**State Machines** (enforced by `claude.workflow_transitions`):
- **Feedback**: new → triaged → in_progress → resolved
- **Features**: draft → planned → in_progress → completed (requires all_tasks_done)
- **Build tasks**: todo → in_progress → completed (triggers feature check)

All transitions logged to `claude.audit_log`.

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

```
CAPTURE (Obsidian) ──> EMBED (Voyage AI) ──> SEARCH (RAG) ──> DELIVER (On-Demand)
```

- **Vault**: `knowledge-vault/` - Markdown with YAML frontmatter, Obsidian-compatible
- **Embeddings**: Voyage AI (voyage-3, 1024 dimensions) → PostgreSQL pgvector
- **RAG**: Automatic via `rag_query_hook.py` on UserPromptSubmit (85% token reduction)
- **Versioning**: File hash tracking - only re-embed changed files
- **Commands**: `/knowledge-capture`, `/session-end`

### Using RAG

**When to search vault**:
- User asks "how do I..." procedural questions → Search SOPs
- Looking for domain knowledge (APIs, DB, WinForms, etc.) → Search 20-Domains/
- Need patterns or gotchas → Search 30-Patterns/
- Unsure which vault doc has the answer → Use semantic search

**How it works**: The `rag_query_hook.py` (UserPromptSubmit hook) automatically queries vault embeddings
on questions/exploration prompts. Results are silently injected into context. Action prompts skip RAG.

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
| 2026-02-24 | **Orchestrator retirement**: Messaging tools migrated to project-tools. Orchestrator MCP removed. BPMN model for messaging lifecycle added. |
| 2026-02-11 | **v3 Application Layer**: 15 new tools (config ops, knowledge, conversations, books), 3 new tables, 40+ total tools |
| 2026-02-10 | **v2 Application Layer**: WorkflowEngine state machine, 5 new tools, audit_log, trimmed context injection |
| 2026-01-03 | **Infrastructure Audit**: Fixed broken session commands, added 10 DB indexes, removed redundant hooks |
| 2025-12-30 | **RAG System**: Voyage AI embeddings, automatic via hook (85% token reduction) |
| 2025-12-21 | **Skills-First** (ADR-005): Replaced process_router, 8 core skills |
| 2025-12-21 | **Auto-apply instructions**: 9 instruction files in `~/.claude/instructions/` |

**Full changelog**: See git log or `docs/INFRASTRUCTURE_AUDIT_REPORT.md`

---

**Version**: 3.4 (Retired orchestrator MCP - messaging moved to project-tools)
**Created**: 2025-10-21
**Updated**: 2026-02-24
**Location**: C:\Projects\claude-family\CLAUDE.md
