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

## Architecture Overview

Infrastructure for the Claude Family ecosystem:
- **Database**: PostgreSQL `ai_company_foundation`, schema `claude` (60+ tables)
- **MCP Servers**: postgres, project-tools (~60 tools), sequential-thinking, bpmn-engine, channel-messaging
- **Enforcement**: Hooks, database constraints, column_registry
- **Knowledge**: DB-first (Memory, Filing Cabinet, Reference Library, Credential Vault) + vault embeddings for domain concept dossiers
- **UI**: Mission Control Web (MCW) for visibility

**Full details**: See `ARCHITECTURE.md`

## Project Structure

```
claude-family/
├── CLAUDE.md              # This file
├── PROBLEM_STATEMENT.md   # Problem definition
├── ARCHITECTURE.md        # System design
├── .claude/
│   ├── rules/             # Auto-loaded enforcement rules
│   ├── skills/            # 32 domain skills (use Skill tool)
│   ├── instructions/      # Auto-apply coding standards
│   └── commands/          # Slash commands
├── knowledge-vault/       # Obsidian vault (reference documentation)
│   ├── 10-Projects/       # Project knowledge
│   ├── 20-Domains/        # Domain expertise
│   ├── 30-Patterns/       # Patterns, gotchas
│   └── 40-Procedures/     # SOPs, workflows
├── scripts/               # Python hooks + utilities
├── mcp-servers/           # MCP server implementations
│   ├── project-tools/     # Main tooling (server_v2.py, ~60 tools)
│   └── bpmn-engine/       # Process models + test runner
└── templates/             # Project templates
```

## Build & Run

```bash
# Sync all project config from DB
python scripts/sync_project.py

# Run background jobs manually
python scripts/job_runner.py --list        # See all jobs
python scripts/job_runner.py --force JOB   # Force-run a job

# BPMN process tests
cd mcp-servers/bpmn-engine && pytest tests/ -v

# Vault embedding update
python scripts/embed_vault_documents.py --all-projects
```

---

## Information Discovery


| I need... | Search |
|-----------|--------|
| Hook architecture, how hooks work | `recall_memories("hook system architecture")` |
| Storage systems, which to use | Load skill: `/skill-load-memory-storage` |
| Config management, how files regenerate | `recall_memories("config management SOP")` |
| Database schema, table structures | `get_schema()` tool |
| Embedding pipeline, FastEmbed | `recall_memories("FastEmbed embedding pipeline")` |
| Session lifecycle, startup/end | `recall_memories("session lifecycle")` |
| BPMN process models | `search_processes("keyword")` |
| Agent delegation patterns | `recall_memories("agent selection")` |
| Nimbus API patterns | `recall_entities("nimbus", entity_type="domain_concept")` |
| Any domain concept | `explore_entities(entity_type="domain_concept")` |
| Component working notes | `list_workfiles()` then `unstash("component")` |
| Credentials/API keys | `get_secret(key, project)` — check before asking user |


## Work Tracking

| I have... | Tool |
|-----------|------|
| A bug | `create_feedback(type='bug', title='...', description='...')` |
| An idea | `create_feedback(type='idea', title='...', description='...')` |
| A feature to build | `create_feature(name='...', description='...')` |
| A task within a feature | `create_linked_task(feature_code, name, desc, verification, files)` |
| Work to start | `start_work(task_code)` / `complete_work(task_code)` |
| Status to check | `get_work_context(scope='current')` or `get_build_board(project)` |
| Config to update | `update_config(component_type, project, name, content, reason)` |
| CLAUDE.md section to update | `update_claude_md(project, section, content)` |

**Data Gateway**: Before INSERT/UPDATE on constrained columns, check `claude.column_registry`.

---

## Project-Specific Rules

### Config Management (CRITICAL)

**Database is source of truth.** Files regenerate from DB on every launch.

| File | Source | Rule |
|------|--------|------|
| `.claude/settings.local.json` | `config_templates` + `workspaces.startup_config` | NEVER edit manually |
| `CLAUDE.md` | `profiles.config->behavior` | Edit via `update_claude_md()` |
| Skills, rules, instructions | `claude.skills`, `claude.rules`, `claude.instructions` | Edit via `update_config()` |

### Schema Rules

- **ALWAYS** use `claude.*` schema — NEVER `claude_family.*` or `claude_pm.*`
- Check `claude.column_registry` before writing to constrained columns

### BPMN-First

Before modifying hooks, workflow code, config management, or enforcement rules:
1. `search_processes("system name")` to find existing model
2. Update BPMN model FIRST, then implement code
3. Commit model + code together

---

**Version**: 5.0
**Created**: 2025-10-21
**Updated**: 2026-04-08
**Template**: claude-md-standard v1.0
