---
projects:
- claude-family
tags:
- architecture
- reference
synced: false
---

# Architecture Details Part 1 — Database, Hooks, Config

Extended details for [ARCHITECTURE.md](../../../ARCHITECTURE.md). See also [Part 2](architecture-details-part2.md) for Skills, BPMN, and advanced systems.

---

## Database Table Inventory

**Schema**: `claude` | **Count**: 63 tables | **DB**: `ai_company_foundation`

| Group | Key Tables | Purpose |
|-------|-----------|---------|
| Sessions | sessions, session_history, session_state | Track Claude instances |
| Projects | projects, project_tech_stack, workspaces | Registry + config |
| Work | features, build_tasks, work_tasks, todos | Work tracking |
| Feedback | feedback | Ideas, bugs, questions |
| Knowledge | knowledge, session_facts, session_notes | 3-tier cognitive memory |
| Entities | entity_types, entities, entity_relationships | Structured catalog (F131) |
| Workfiles | project_workfiles | Cross-session component context |
| Activities | activities | WCC activity detection |
| BPMN | bpmn_processes | Process model registry |
| Messages | messages | Inter-Claude communication |
| Config | config_templates, project_type_configs, profiles | DB-driven config |
| Quality | column_registry, workflow_transitions, audit_log | Data governance |
| Books | books, book_references | Reference library |

---

## Hook Scripts (Complete List)

All 11 hooks registered in `.claude/settings.local.json` (DB-generated — never edit manually).

| Script | Hook Event | Purpose |
|--------|-----------|---------|
| `session_startup_hook_enhanced.py` | SessionStart | Log session (60s dedup guard), load state |
| `rag_query_hook.py` | UserPromptSubmit | RAG + core protocol injection (~30 tokens) |
| `todo_sync_hook.py` | PostToolUse(TodoWrite) | Sync todos to DB |
| `task_sync_hook.py` | PostToolUse(TaskCreate/TaskUpdate) | Sync tasks to `claude.todos` + map file |
| `mcp_usage_logger.py` | PostToolUse(all) | Log MCP tool usage (catch-all matcher) |
| `task_discipline_hook.py` | PreToolUse(Write/Edit/Task/Bash) | Block if no tasks created this session |
| `context_injector_hook.py` | PreToolUse(Write/Edit) | Inject coding standards into context |
| `standards_validator.py` | PreToolUse(Write/Edit) | Validate content against DB standards |
| `precompact_hook.py` | PreCompact | Inject todos + features + session facts |
| `session_end_hook.py` | SessionEnd | Auto-close unclosed sessions (< 24h old) |
| `subagent_start_hook.py` | SubagentStart | Log agent spawns |

**Key gotchas**:
- Spawned agents have `disableAllHooks: true` — no RAG, no auto-logging
- `mcp_usage_logger` uses catch-all matcher; filters to `mcp__` prefix internally
- `task_discipline_hook` checks `_session_id` in map file; stale maps are blocked
- PostToolUse hooks use field `tool_response` (not `tool_output`)
- PreToolUse deny pattern: exit code 0 + JSON `permissionDecision: "deny"`

---

## Config Management System

**Database is source of truth. Files are generated. Never edit `settings.local.json` manually.**

### Config Flow

```
claude.config_templates (hooks-base template, template_id=1)
  + claude.workspaces.startup_config (per-project JSONB overrides)
        │
        ▼
scripts/generate_project_settings.py
        │
        ▼
.claude/settings.local.json  ← generated, overwrites on SessionStart
```

### Permanent Config Changes

```sql
-- All projects (hooks, permissions):
UPDATE claude.config_templates SET ... WHERE template_id = 1;

-- Single project override:
UPDATE claude.workspaces
SET startup_config = jsonb_set(startup_config, '{key}', '"value"')
WHERE project_name = 'your-project';
```

Regenerate manually: `python scripts/generate_project_settings.py <project-name>`

Full procedure: `knowledge-vault/40-Procedures/Config Management SOP.md`

---

## Cognitive Memory System (F130)

3-tier memory replacing unbounded knowledge graph dumps.

| Tier | Table Column | Promoted When | Best For |
|------|-------------|--------------|---------|
| SHORT | `session_facts` | Auto via hooks | Credentials, configs, decisions this session |
| MID | `knowledge` tier='mid' | Default for `remember()` | Decisions, learned facts |
| LONG | `knowledge` tier='long' | access_count >= 5, age >= 7d | Proven patterns, gotchas |
| ARCHIVED | `knowledge` tier='archived' | confidence < 30, not accessed 90d | Inactive |

**Tools**: `remember(content, memory_type)`, `recall_memories(query, budget)`, `consolidate_memories(trigger)`

**Lifecycle**: `consolidate_memories()` auto-runs on session_end + 24h periodic.

**Pipeline fixes (2026-03-11)**:
- Quality gate in `remember()`: rejects < 80 chars and junk patterns
- MID→LONG promotion: retrieval-frequency based (access_count >= 5, age >= 7d)
- Dedup threshold lowered from 0.85 to 0.75
- `recall_knowledge()` excludes archived entries

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/claude-family/architecture-details-part1.md
