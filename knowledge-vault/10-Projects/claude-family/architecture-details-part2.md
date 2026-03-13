---
projects:
- claude-family
tags:
- architecture
- reference
synced: false
---

# Architecture Details Part 2 — Skills, BPMN, Entity Catalog, WCC

Extended details for [ARCHITECTURE.md](../../../ARCHITECTURE.md). See also [Part 1](architecture-details-part1.md) for database, hooks, and config.

---

## Skills System (ADR-005)

Skills replaced the deprecated Process Router (December 2025). Invoke via the `Skill` tool.

| Skill | Location | Purpose |
|-------|----------|---------|
| `database-operations` | `.claude/skills/database/` | SQL validation, column_registry checks |
| `work-item-routing` | `.claude/skills/work-item-routing/` | Feedback, features, build_tasks routing |
| `session-management` | `.claude/skills/session-management/` | Session lifecycle |
| `code-review` | `.claude/skills/code-review/` | Pre-commit review |
| `project-ops` | `.claude/skills/project-ops/` | `/project-init`, retrofit, phases |
| `messaging` | `.claude/skills/messaging/` | Inter-Claude communication |
| `agentic-orchestration` | `.claude/skills/agentic-orchestration/` | Agent spawning, parallel work |
| `testing-patterns` | `.claude/skills/testing/` | Test writing and execution |
| `bpmn-modeling` | `.claude/skills/bpmn-modeling/` | BPMN-first process design |

**Legacy**: Process registry archived (25 active, 7 deprecated). See ADR-005 in `claude.architecture_decisions`.

---

## BPMN Process Modeling

Every system workflow is modeled in BPMN. Model is source of truth; code implements the model.

### Storage

| Layer | Location | Purpose |
|-------|----------|---------|
| Files | `mcp-servers/bpmn-engine/processes/` | Git source of truth (.bpmn XML) |
| Registry | `claude.bpmn_processes` | Central search + Voyage AI embeddings |

### Process Hierarchy

| Level | Scope | Example |
|-------|-------|---------|
| L0 | System-wide | Full architecture with swim lanes |
| L1 | Subsystem | Session management, enforcement |
| L2 | Detailed workflow | Individual hook, feature lifecycle |

### bpmn-engine MCP Tools

| Tool | Purpose |
|------|---------|
| `list_processes` | Discover all modeled processes |
| `get_process(id)` | Read process structure |
| `search_processes(query)` | Find by keyword across all files |
| `validate_process(id)` | Run process tests |
| `get_current_step(id, completed)` | GPS-style workflow navigation |
| `check_alignment(id)` | Verify model matches implementation |
| `get_dependency_tree` | Process dependency graph |
| `file_alignment_gaps` | Find unmodeled code paths |

**Rule**: Model in BPMN first → write tests → then implement code. Never commit code without a corresponding model update. See `.claude/rules/system-change-process.md`.

---

## Entity Catalog System (F131)

Type-extensible structured storage for reference data (books, APIs, OData entities, patterns).

**Tables**: `entity_types`, `entities`, `entity_relationships`

**Tools**:
- `catalog(entity_type, properties, ...)` — store structured entity
- `recall_entities(query, entity_type?, ...)` — RRF search (full-text + vector)

**Search**: RRF (Reciprocal Rank Fusion) combining BM25 full-text + Voyage AI vector similarity.

**Seed data**: 49 book entities migrated from legacy `books` table.

---

## Work Context Container (WCC)

Automatic activity-based context assembly. Runs in RAG hook — no manual tool calls needed.

### How It Works

```
Every prompt → detect_activity()
    │
    ├── Activity changed? → assemble_wcc()
    │       ├── workfiles (component context)
    │       ├── knowledge (mid/long tier)
    │       ├── features (active work)
    │       ├── session_facts (current session)
    │       ├── vault (RAG embeddings)
    │       └── bpmn_processes (process models)
    │
    └── Inject at priority 2, budget-capped
```

### Activity Detection Priority

1. `session_fact("current_activity")` — explicit override
2. Exact name or alias match in `claude.activities`
3. Word overlap scoring
4. Workfile component fallback

### WCC Tools

| Tool | Purpose |
|------|---------|
| `create_activity(name, aliases, desc)` | Register activity with detection aliases |
| `list_activities(project)` | Browse activities and access stats |
| `update_activity(id, aliases, is_active)` | Manage aliases, deactivate stale |
| `assemble_context(name, budget)` | Manual WCC assembly for debugging |

---

## Project Workfiles (FB177)

Cross-session component-scoped working context. Filing cabinet metaphor: project=cabinet, component=drawer, title=file.

**Table**: `claude.project_workfiles` — UPSERT on (project_id, component, title), Voyage AI embeddings

**Tools**:
- `stash(component, title, content)` — save or update workfile
- `unstash(component, title?)` — retrieve workfile(s)
- `list_workfiles(project?, component?)` — browse cabinet
- `search_workfiles(query)` — semantic search via Voyage AI

**Key features**:
- `mode="append"` concatenates with `\n---\n` separator
- `is_pinned=True` auto-surfaces workfile at session start and in precompact
- `start_session()` shows `active_workfiles` count

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/claude-family/architecture-details-part2.md
