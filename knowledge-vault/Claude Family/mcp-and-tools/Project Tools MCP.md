---
projects:
- claude-family
tags:
- mcp
- tools
- knowledge
- session-facts
- quick-reference
synced: false
---

# Project Tools MCP

MCP server providing project-aware tooling for Claude Family. **45 tools** across session management, workflow engine, config ops, conversations, books, knowledge, work tracking, session persistence, and project workfiles.

**Server**: `mcp-servers/project-tools/server_v2.py` (globally deployed via `~/.claude/mcp.json`)

**Detailed Architecture**: See [[Application Layer v3]] for pillar breakdown and data flows. See [[Application Layer v2]] for state machine details.

---

## Complete Tool Reference (45 tools)

### Session Lifecycle (3)

| Tool | Purpose |
|------|---------|
| `start_session(project)` | Load ALL context: project info, active todos, features, ready tasks, pending messages, recent decisions, relevant knowledge |
| `end_session(project, summary, learnings)` | Close session, auto-extract conversation to DB, store summary |
| `save_checkpoint(project, summary)` | Mid-session checkpoint without closing |

### Workflow Engine (5)

State machine enforced via `claude.workflow_transitions` table. Invalid transitions rejected.

| Tool | Purpose |
|------|---------|
| `advance_status(type, id, status)` | Move feedback/feature/task through state machine |
| `start_work(task_code)` | `todo` → `in_progress` + load plan_data |
| `complete_work(task_code)` | `in_progress` → `completed` + check feature completion + suggest next task |
| `get_work_context(scope)` | Token-budgeted context: `current`, `feature`, or `project` |
| `create_linked_task(feature, name, desc, verification, files)` | Add task to active feature with quality gates |

**State Machines**:
- **Feedback**: new → triaged → in_progress → resolved (+ wont_fix, duplicate)
- **Features**: draft → planned → in_progress → completed (requires all_tasks_done)
- **Build tasks**: todo → in_progress → completed (triggers feature completion check)

### Config Operations (4)

Atomic file + DB operations. No more manual edits that drift.

| Tool | Purpose |
|------|---------|
| `update_claude_md(project, section, content)` | Update CLAUDE.md section (file + profiles table) |
| `deploy_claude_md(project)` | Deploy CLAUDE.md from DB to file (one-way, DB is source of truth) |
| `deploy_project(project, components)` | Deploy skills/instructions/rules from DB to `.claude/` files |
| `regenerate_settings(project)` | Regenerate `settings.local.json` from DB templates |

### Conversation Persistence (3)

Extract and search session history. Prevents decision/learning loss.

| Tool | Purpose |
|------|---------|
| `extract_conversation(project, session_id)` | Parse JSONL session log → `claude.conversations` table |
| `search_conversations(query, project, limit)` | Full-text search across stored conversations |
| `extract_insights(session_id)` | Pattern-match decisions/rules/learnings → knowledge entries |

### Book References (3)

Structured knowledge from books with semantic search via pgvector.

| Tool | Purpose |
|------|---------|
| `store_book(title, author, ...)` | Add book metadata to `claude.books` |
| `store_book_reference(book, concept, page, ...)` | Store concept with Voyage AI embedding (VECTOR 1024) |
| `recall_book_reference(query, book, limit)` | Semantic search book references via cosine similarity |

### Knowledge (5)

Long-term knowledge storage with embeddings and graph relations.

| Tool | Purpose |
|------|---------|
| `store_knowledge(title, desc, type, category, ...)` | Store with auto-embedding (Voyage AI) |
| `recall_knowledge(query, domain, source_type, tags, date_range)` | Semantic search with structured filters |
| `link_knowledge(source_id, target_id, relation)` | Create typed relation between entries |
| `get_related_knowledge(id, relation_type)` | Traverse knowledge graph |
| `mark_knowledge_applied(id, success, context)` | Track application success/failure |

### Session Facts (4)

Within-session fact cache that survives context compaction.

| Tool | Purpose |
|------|---------|
| `store_session_fact(key, value, type, is_sensitive)` | Cache a fact (credential, config, decision, etc.) |
| `recall_session_fact(key)` | Get specific fact by key |
| `list_session_facts()` | Show all session facts |
| `recall_previous_session_facts(n_sessions, types)` | Recovery from previous sessions |

**Fact types**: `credential`, `config`, `endpoint`, `decision`, `note`, `data`, `reference`

### Session Notes (2)

Structured note-taking for progress/decisions/blockers during sessions.

| Tool | Purpose |
|------|---------|
| `store_session_notes(content, section)` | Add note to section (decisions, progress, blockers, findings) |
| `get_session_notes(section)` | Retrieve notes, optionally by section |

**Storage**: `~/.claude/session_notes/{project_name}.md`

### Work Tracking (5)

Create and manage feedback, features, and build tasks.

| Tool | Purpose |
|------|---------|
| `create_feedback(project, type, description, ...)` | Create bug/idea/question (validates via column_registry) |
| `create_feature(project, name, description, ...)` | Create feature with plan_data |
| `add_build_task(feature, name, type, ...)` | Add task to a feature |
| `get_ready_tasks(project)` | Get unblocked tasks ready for work |
| `update_work_status(type, id, status)` | Legacy status update (routes through WorkflowEngine) |

### Workfile Tools (4)

| Tool | Purpose |
|------|---------|
| `stash(component, title, content)` | Store/update component-scoped workfile (UPSERT). mode=replace\|append |
| `unstash(component, title?)` | Retrieve workfile(s) by component, updates access stats |
| `list_workfiles(project?, component?)` | Browse components with file counts, pinned status |
| `search_workfiles(query)` | Semantic search across workfiles via Voyage AI embeddings |

### Work Context Container (4)

Automatically assemble and inject context when activity changes. **Runs in RAG hook — no manual calls needed.**

| Tool | Purpose |
|------|---------|
| `create_activity(project, name, aliases)` | Create named activity (e.g., "user-auth-flow"). Aliases enable fuzzy detection. |
| `list_activities(project)` | Browse activities + access stats + last changed |
| `update_activity(activity_id, name, aliases)` | Rename or add aliases for better detection |
| `assemble_context(activity_id, budget)` | Manually assemble context for an activity (usually auto-triggered) |

**How it works**: Every prompt → `detect_activity()` checks for activity change → if changed, `assemble_wcc()` queries 6 sources in parallel (workfiles 25%, knowledge 25%, features/tasks 15%, session facts 10%, vault RAG 15%, BPMN/skills 10%) → context cached 5 min → injected at priority 2 in RAG hook.

**Key gotcha**: When WCC active, per-source knowledge/RAG/nimbus queries are **SKIPPED** (WCC replaces them, not adds). Net token budget unchanged.

### Context & Discovery (7)

| Tool | Purpose |
|------|---------|
| `get_schema(project)` | Introspect database tables for project schemas |
| `get_project_context(project)` | Load project context (deprecated → use `start_session`) |
| `get_session_resume(project)` | Resume context (deprecated → use `start_session`) |
| `get_incomplete_todos(project)` | Get pending/in_progress todos |
| `restore_session_todos(session_id)` | Load past session's todos for TodoWrite |
| `todos_to_build_tasks(project)` | Convert session todos to persistent build_tasks |
| `find_skill(query)` | Search skill_content by task keywords |

---

## When to Use What

| Need | Use This |
|------|----------|
| Start of session | `start_session` (returns everything) |
| API credentials, config values | `store_session_fact` (survives compaction) |
| Progress tracking, decisions | `store_session_notes` |
| Learned pattern for future sessions | `store_knowledge` (with embeddings) |
| Task to do right now | TodoWrite (synced to DB via hook) |
| Task linked to feature | `create_linked_task` |
| Change work item status | `advance_status` (NOT raw SQL) |
| Update CLAUDE.md | `update_claude_md` (NOT manual edit) |
| Deploy config from DB | `deploy_project` or `regenerate_settings` |
| Search past conversations | `search_conversations` |
| Store book concepts | `store_book` + `store_book_reference` |
| Component working context (cross-session) | `stash()` / `unstash()` |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `claude.sessions` | Session tracking (659 rows) |
| `claude.todos` | Todo persistence (1,807 rows) |
| `claude.feedback` | Bugs, ideas, questions (86 rows) |
| `claude.features` | Feature tracking (100 rows) |
| `claude.build_tasks` | Tasks linked to features (338 rows) |
| `claude.knowledge` | Long-term knowledge with embeddings (434 rows) |
| `claude.knowledge_relations` | Knowledge graph relations |
| `claude.session_facts` | Session fact cache (133 rows) |
| `claude.audit_log` | Immutable transition audit trail (56 rows) |
| `claude.mcp_usage` | MCP tool usage log (4,671 rows) |
| `claude.conversations` | Extracted session conversations |
| `claude.books` | Book metadata |
| `claude.book_references` | Concept references with pgvector embeddings |
| `claude.knowledge_routes` | Task pattern → knowledge source routing |
| `claude.workflow_transitions` | Valid state machine transitions (28 rules) |
| `claude.vault_embeddings` | Vault document embeddings (8,856 rows) |
| `claude.project_workfiles` | Component-scoped cross-session working context |
| `claude.activities` | Named activities per project with aliases, embeddings, access stats |

---

## Configuration

**Global**: `~/.claude/mcp.json`
```json
"project-tools": {
  "type": "stdio",
  "command": "C:/venvs/mcp/Scripts/python.exe",
  "args": ["C:/Projects/claude-family/mcp-servers/project-tools/server_v2.py"],
  "env": {
    "DATABASE_URI": "postgresql://...",
    "VOYAGE_API_KEY": "${VOYAGE_API_KEY}"
  }
}
```

**Per-project-type**: `claude.project_type_configs.default_mcp_servers` - all 15 project types include `project-tools`.

---

## Related

- [[Application Layer v3]] - Detailed v3 architecture and data flows
- [[Application Layer v2]] - State machine details and WorkflowEngine
- [[Config Management SOP]] - Config tools usage procedures
- [[RAG Usage Guide]] - How knowledge recall integrates with RAG
- [[Claude Hooks]] - Hooks that use project-tools
- [[Family Rules]] - When to use project-tools vs raw SQL

---

**Version**: 2.2
**Created**: 2026-01-23
**Updated**: 2026-03-10
**Location**: knowledge-vault/Claude Family/Project Tools MCP.md
**Changes**: Added Work Context Container (4 new tools, activities table, RAG hook integration)
