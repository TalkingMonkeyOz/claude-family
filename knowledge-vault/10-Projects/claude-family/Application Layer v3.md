---
projects:
- claude-family
tags:
- architecture
- mcp
- v3
synced: false
---

# Project-Tools v3 Application Layer

## Overview

The v3 application layer extends project-tools from workflow enforcement to a comprehensive operations platform. **Vision**: "Every repeated operation becomes an MCP tool."

**Core Principle**: Minimize context overhead, maximize automation. Claude shouldn't write SQL for routine operations - it should call tools.

**Tool Count**: 40+ tools across 4 priority tiers.

**Related**: See [[Application Layer v2]] for state machine details.

---

## v3 Architecture

```
Claude Code → MCP Tool → Application Layer v3
                              │
                              ├─ P0: Conversation Persistence (extract, search, insights)
                              ├─ P1: Config Operations (update, sync, deploy, regenerate)
                              ├─ P2: Knowledge Enhancement (books, embeddings, enhanced recall)
                              └─ P3: Unified Work Tracking (enhanced task/session workflows)
```

---

## Four Pillars

### P0 - Conversation Persistence

**Problem**: Session JSONL logs exist but are never analyzed. Decisions, insights, and learnings are lost.

**Solution**: Extract, persist, and search conversation history.

| Tool | Purpose |
|------|---------|
| `extract_conversation` | Parse JSONL session logs → `claude.conversations` table |
| `search_conversations` | Query past conversations with semantic context |
| `extract_insights` | Pattern-match for decisions/rules/learnings → knowledge entries |

**Data Flow**:
```
Session JSONL → extract_conversation → conversations table
                                    → search_conversations (find precedents)
                                    → extract_insights → knowledge entries
```

**Use Cases**:
- "What did we decide about error handling in session X?"
- "Show me conversations about state machine design"
- "Extract all decisions from the last week"

---

### P1 - Config Operations

**Problem**: Config management required manual SQL + file edits. Easy to drift.

**Solution**: MCP tools that handle file + DB atomically.

| Tool | Purpose |
|------|---------|
| `update_claude_md(section, content)` | Update CLAUDE.md sections (file + profiles table) |
| `sync_profile(direction)` | Sync CLAUDE.md ↔ profiles table (file_to_db / db_to_file) |
| `deploy_project(components)` | Deploy skills/instructions/rules from DB to files |
| `regenerate_settings()` | Regenerate `.claude/settings.local.json` from DB |

**Data Flow**:
```
MCP Tool → Update profiles/skills/instructions tables
         → Write to .claude/ files
         → Log to config_deployment_log
```

**Use Cases**:
- "Update the Architecture Overview section in CLAUDE.md"
- "Deploy all skills from database to project files"
- "Regenerate settings after database changes"

**Related**: See [[Config Management SOP]]

---

### P2 - Knowledge Enhancement

**Problem**: Knowledge system lacked domain-specific sources (books, docs) and advanced search.

**Solution**: Structured knowledge sources + embedding-powered search.

| Tool | Purpose |
|------|---------|
| `store_book` | Store book metadata in `claude.books` |
| `store_book_reference` | Store concept references with VECTOR(1024) embeddings |
| `recall_book_reference` | Semantic search book references |
| `recall_knowledge` (enhanced) | Now supports filters: domain, source_type, tags, date_range_days |

**New Tables**:
- `claude.books` - Book metadata (title, author, ISBN, topics)
- `claude.book_references` - Concept references with pgvector embeddings
- `claude.knowledge_routes` - Task pattern → knowledge source routing (10 seed routes)

**Data Flow**:
```
Book → store_book → books table
Concept → store_book_reference → Voyage AI embedding → book_references (VECTOR)
Query → recall_book_reference → pgvector cosine similarity → ranked results
```

**Use Cases**:
- "Store 'Clean Architecture' book with concepts"
- "Find all references to dependency inversion from books"
- "Show me knowledge entries about state machines from last 30 days"

---

### P3 - Unified Work Tracking

**Problem**: Task creation, session start/end, and work context were disconnected.

**Solution**: Enhanced workflows with richer context and automation.

| Tool | Purpose |
|------|---------|
| `create_linked_task` (enhanced) | Now requires description, verification_criteria, files_affected |
| `start_session` (enhanced) | Returns recommended_actions, recent_decisions, relevant_knowledge |
| `end_session` (enhanced) | Auto-extracts conversation to DB on session close |

**Hook Integration**:
- `task_sync_hook.py` now bridges TaskCreate/Update → build_tasks (fuzzy matching, dedup)

**Data Flow**:
```
start_session → Load work context (active tasks, feature state, recent decisions)
              → Inject into session
create_linked_task → Validate feature status → Create in build_tasks → Sync to todos
complete_work → Check feature completion → Suggest next task
end_session → Extract conversation → conversations table → knowledge entries
```

**Use Cases**:
- "Start session with context for current feature"
- "Create task with verification criteria and affected files"
- "End session and extract key decisions to knowledge base"

---

## Complete Tool Inventory

### v2 Tools (State Machine - 27 total)

**Core Workflow** (5):
- advance_status, start_work, complete_work, get_work_context, create_linked_task

**Legacy Work Tracking** (22):
- create_feedback, create_feature, add_build_task, update_work_status, link_work_items, create_comment, resolve_feedback, etc.

### v3 Tools (New - 15 total)

**P0 - Conversations** (3):
- extract_conversation, search_conversations, extract_insights

**P1 - Config** (4):
- update_claude_md, sync_profile, deploy_project, regenerate_settings

**P2 - Knowledge** (5):
- store_book, store_book_reference, recall_book_reference
- recall_knowledge (enhanced)
- recall_project_knowledge (enhanced)

**P3 - Work Tracking** (3):
- create_linked_task (enhanced)
- start_session (enhanced)
- end_session (enhanced)

**Total**: 40+ tools

---

## Data Flow: Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│ Session Start                                                   │
│ start_session() → Returns:                                      │
│   - Active tasks (todo/in_progress)                             │
│   - Feature context (current feature, plan_data)                │
│   - Recommended actions (next steps)                            │
│   - Recent decisions (from conversations)                       │
│   - Relevant knowledge (from knowledge_routes)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ During Work                                                     │
│ create_linked_task(description, criteria, files) → build_tasks │
│ start_work(task_code) → Load plan_data → Set focus             │
│ advance_status(type, id, status) → State machine transition    │
│ complete_work(task_code) → Check feature completion            │
│ store_knowledge(fact, domain, tags) → Knowledge base           │
│ update_claude_md(section, content) → CLAUDE.md + profiles      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Session End                                                     │
│ end_session(summary, learnings) → Close session                │
│   → extract_conversation(session_id) → conversations table     │
│   → extract_insights(session_id) → knowledge entries           │
│   → search_conversations(query) → Find similar patterns        │
└─────────────────────────────────────────────────────────────────┘
```

---

## New Tables Summary

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `claude.books` | Book metadata | title, author, isbn, topics, publication_year |
| `claude.book_references` | Concept references | book_id, concept, page_number, embedding VECTOR(1024) |
| `claude.knowledge_routes` | Task → knowledge routing | task_pattern, knowledge_sources[], priority |

**Embeddings**: Voyage AI (voyage-3, 1024 dimensions) via pgvector.

---

## Implementation Notes

**Location**: `mcp-servers/project-tools/server_v2.py` (uncommitted, safe to modify)

**Migration Strategy**: All v2 tools remain functional. v3 adds new tools + enhances existing ones. No breaking changes.

**Performance**: New tools use optimized queries (LATERAL joins, pgvector indexes, minimal context injection).

**Token Budget**: ~12k tokens (up from ~8k in v2) for 40+ tools. Still under orchestrator (~9k).

---

## Related Documentation

- [[Application Layer v2]] - State machine details
- [[Config Management SOP]] - Config tools usage
- [[Knowledge System]] - Knowledge architecture
- [[Session Lifecycle - Overview]] - Session workflow

---

**Version**: 1.0
**Created**: 2026-02-11
**Updated**: 2026-02-11
**Location**: 10-Projects/claude-family/Application Layer v3.md
