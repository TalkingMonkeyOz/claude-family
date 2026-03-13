# Architecture - Claude Family Infrastructure

**Project**: claude-family
**Version**: 2.0
**Updated**: 2026-03-14
**Status**: Active

---

## Overview

Claude Family is the infrastructure layer that enables coordinated AI-assisted software development across multiple Claude Code instances. It provides shared configuration, commands, scripts, hooks, and a PostgreSQL-backed state management system with cognitive memory, BPMN process modeling, and automated RAG.

```
┌─────────────────────────────────────────────────────────────────┐
│                    User (John) - Desktop                        │
├─────────────────────────────────────────────────────────────────┤
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │ Claude Code  │  │ Claude Code  │  │ Claude Code  │        │
│   │ Instance #1  │  │ Instance #2  │  │ Instance #3  │        │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│          └────────────────┬┴─────────────────┘                 │
│   ┌───────────────────────▼─────────────────────────────────┐  │
│   │              Shared Infrastructure Layer                 │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│   │  │ CLAUDE.md   │  │  /commands  │  │  MCP Servers    │  │  │
│   │  │ (per proj)  │  │  (shared)   │  │  (project-tools │  │  │
│   │  └─────────────┘  └─────────────┘  │   bpmn-engine)  │  │  │
│   └─────────────────────────┬───────────┴─────────────────┘  │  │
│   ┌─────────────────────────▼───────────────────────────────┐  │
│   │           PostgreSQL: ai_company_foundation              │  │
│   │                 claude schema (63 tables)                │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. Claude Code Instances

Multiple instances run simultaneously, each on different projects. They share slash commands, global `~/.claude/CLAUDE.md`, database access, work tracking, and automatic RAG via the UserPromptSubmit hook.

### 2. PostgreSQL Database

**Schema**: `claude` | **Tables**: 63 | **DB**: `ai_company_foundation`

Key groups: sessions, projects/workspaces, work items (features/tasks), knowledge (3-tier memory), entities (catalog), workfiles, activities (WCC), BPMN registry, messages, config templates, and data quality tables. See [Architecture Details Part 1](knowledge-vault/10-Projects/claude-family/architecture-details-part1.md) for full table inventory and hook details.

### 3. MCP Servers

| Server | Purpose | Scope |
|--------|---------|-------|
| postgres | Database read access, SQL execution | Global |
| project-tools | Work tracking, knowledge, config, messaging, workfiles (~60+ tools) | Global |
| sequential-thinking | Complex multi-step reasoning | Global |
| python-repl | Python code execution | Global |
| bpmn-engine | Process model query, validation, navigation | Global |
| nimbus-knowledge | Nimbus domain knowledge (pending migration) | Nimbus only |
| mui | MUI X component documentation | Selected projects |
| playwright | Browser automation and testing | Selected projects |

**Retired**: `orchestrator` (2026-02-24) — messaging migrated to project-tools, agent spawning uses native Task tool.

### 4. Hook System

Hooks live in `.claude/settings.local.json` (DB-generated — never edit manually). Full hook script details in [Architecture Details Part 1](knowledge-vault/10-Projects/claude-family/architecture-details-part1.md).

| Script | Hook Event | Purpose |
|--------|-----------|---------|
| `session_startup_hook_enhanced.py` | SessionStart | Log session, load state |
| `rag_query_hook.py` | UserPromptSubmit | RAG + core protocol injection |
| `todo_sync_hook.py` | PostToolUse(TodoWrite) | Sync todos to DB |
| `task_sync_hook.py` | PostToolUse(TaskCreate) | Sync tasks to claude.todos |
| `task_discipline_hook.py` | PreToolUse(Write/Edit) | Block if no tasks created |
| `context_injector_hook.py` | PreToolUse(Write/Edit) | Inject coding standards |
| `precompact_hook.py` | PreCompact | Inject session state |
| `session_end_hook.py` | SessionEnd | Auto-close session in DB |
| `subagent_start_hook.py` | SubagentStart | Log agent spawns |

### 5. Mission Control Web (MCW)

Next.js web app providing visibility: sessions, projects, work items, feedback, activity feed.

---

## Directory Structure

```
C:\Projects\claude-family\
├── CLAUDE.md                  # AI constitution (self-healing from DB)
├── PROBLEM_STATEMENT.md
├── ARCHITECTURE.md            # This document
├── README.md
├── .claude/
│   ├── commands/              # 24 slash commands
│   ├── instructions/          # Auto-apply coding standards
│   ├── skills/                # Domain skills (9 skills)
│   ├── rules/                 # Enforcement rules
│   ├── agents/                # Agent profiles
│   ├── collections/           # Agent groupings
│   └── settings.local.json    # Generated from DB (do not edit)
├── scripts/                   # Python utilities + 11 hook scripts
├── mcp-servers/
│   ├── project-tools/         # Main work tracking server
│   ├── bpmn-engine/           # BPMN process modeling server
│   └── flaui-testing/         # Windows UI automation (C#)
├── knowledge-vault/           # Obsidian vault (Markdown + YAML)
│   ├── 00-Inbox/
│   ├── 10-Projects/
│   ├── 20-Domains/
│   ├── 30-Patterns/
│   └── 40-Procedures/
├── templates/                 # Project scaffolding templates
└── docs/
    └── adr/                   # Architecture decision records
```

---

## Key Workflows

### Session Lifecycle

```
SessionStart hook (AUTO) → logs session, loads state
UserPromptSubmit hook (AUTO) → RAG + core protocol (8 rules)
PostToolUse hooks (AUTO) → todo sync, MCP usage logging
PreCompact hook (AUTO) → injects active work before compaction
SessionEnd hook (AUTO) → auto-closes session in DB
/session-end (MANUAL) → detailed summary + knowledge capture
```

### Work Tracking Flow

```
IDEA ──▶ feedback (type='idea')
               │ (approved)
        features table
               │ (breakdown)
        build_tasks table ──▶ advance_status() / start_work() / complete_work()
               │ (in session)
         TodoWrite tool
```

State changes flow through WorkflowEngine (`claude.workflow_transitions`, 28 transitions). All transitions logged to `claude.audit_log`.

### RAG + Context Injection

```
UserPromptSubmit → rag_query_hook.py
  ├── WCC activity detection → assemble_wcc() (6 sources, budget-capped)
  │   OR per-source RAG (vault embeddings + knowledge + session facts)
  └── Core protocol injection (8 rules, every prompt)
```

---

## Enforcement Hierarchy

```
Weak ───────────────────────────────────────────────────▶ Strong

CLAUDE.md    Slash      Hooks        DB            Reviewer
(guidance) ─▶ Commands ─▶ (block) ─▶ Constraints ─▶ Agents
              (manual)   (enforce)   (reject)       (verify)
```

---

## Architectural Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Consolidate 4 schemas into unified claude schema | Accepted |
| ADR-002 | Core Documentation and Process System | Accepted |
| ADR-003 | Data Gateway Pattern for Validated Writes | Accepted |
| ADR-005 | Skills-First Architecture (replacing Process Router) | Accepted |

---

## Related Documents

- [Architecture Details Part 1](knowledge-vault/10-Projects/claude-family/architecture-details-part1.md) — Full table inventory, all hook scripts, config system, cognitive memory
- [Architecture Details Part 2](knowledge-vault/10-Projects/claude-family/architecture-details-part2.md) — Skills, BPMN modeling, Entity Catalog, WCC, Workfiles
- `CLAUDE.md` — AI constitution with full tool index
- `PROBLEM_STATEMENT.md` — Problem definition
- `knowledge-vault/40-Procedures/Config Management SOP.md`

---

**Maintained by**: Claude Family Infrastructure Team
**Review Cycle**: Monthly or on major changes

---

**Version**: 2.0
**Created**: 2025-10-21
**Updated**: 2026-03-14
**Location**: C:\Projects\claude-family\ARCHITECTURE.md
