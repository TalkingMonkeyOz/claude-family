# Master TODO - Claude Family Infrastructure
**Created:** 2025-12-02
**Status:** Active Planning
**Author:** claude-code-unified (Opus 4.5)

---

## Executive Summary

This document consolidates ALL outstanding work across Claude Family infrastructure, MCW features, data fixes, scheduler system, documents management, and RTX 5080 local AI integration.

---

## PART 1: Immediate Fixes (This Session)

### 1.1 Data Quality Issues
- [ ] **Knowledge table is empty in MCW** - 139 rows exist in `claude.knowledge` but MCW shows empty
  - Check MCW data layer: `packages/database/src/data/knowledge.ts`
  - Verify API endpoint exists
  - May need to create page/component

- [ ] **Documents table has test data** - Only 10 rows, mostly E2E test artifacts
  - Clean up test documents
  - Need document scanner/indexer to populate real docs

- [ ] **MCP Memory graph has good data** - 40+ entities, needs sync to PostgreSQL
  - Run `sync_postgres_to_mcp.py` in reverse direction
  - Or create `sync_mcp_to_postgres.py`

### 1.2 Schema Updates Completed Today
- [x] Created `claude.session_state` table
- [x] Updated all code from `claude_family.*` to `claude.*` schema
- [x] Orchestrator MCP updated
- [x] Plugin commands updated

---

## PART 2: MCW Feature Requests (Send to MCW)

### 2.1 Messaging View
**Priority:** HIGH
```
Feature: Messages/Inbox Tab
- Display `claude.messages` table
- Show pending/read/acknowledged status
- Allow sending messages to other Claude instances
- Filter by project, priority, message_type
- Real-time refresh
```

### 2.2 Agents & Skills Dashboard
**Priority:** HIGH
```
Feature: Agents Tab
- List all orchestrator agents (from agent_types.json)
- Show each agent's:
  - Model (haiku/sonnet/opus)
  - MCP servers allocated
  - Cost per task
  - Use cases
  - Read-only status
- List Task tool subagents (Explore, Plan, general-purpose)
- Show recent agent executions from `claude.agent_sessions`
```

### 2.3 Claude Configuration Tab (Per Project)
**Priority:** MEDIUM
```
Feature: Project > Claude Config Tab
- Show for each project:
  - Global CLAUDE.md contents
  - Project CLAUDE.md contents
  - .mcp.json configuration
  - .claude/settings.local.json
  - Slash commands available
  - Hooks configured
- Read-only initially, edit later
```

### 2.4 Knowledge Base Tab
**Priority:** HIGH
```
Feature: Knowledge Tab (currently empty)
- Wire to `claude.knowledge` table (139 rows exist!)
- Show: title, knowledge_type, knowledge_category, description
- Filter by type, category, project
- Search functionality
- Add/Edit capability
```

### 2.5 Scheduler/Jobs Dashboard
**Priority:** MEDIUM
```
Feature: Jobs Tab
- Display `claude.scheduled_jobs` (6 jobs defined)
- Show `claude.job_run_history`
- Manual trigger button
- Enable/disable jobs
- Show next_run, last_run, success rate
```

### 2.6 Activity Feed
**Priority:** LOW
```
Feature: Activity Feed Page
- Display `claude.activity_feed`
- Real-time updates
- Filter by project, severity, type
```

---

## PART 3: Documents Management System

### 3.1 Current State
- `claude.documents` - 10 rows (mostly test data)
- `claude.doc_templates` - exists, unknown state
- `claude.project_docs` - exists, unknown state
- No document scanner/indexer running

### 3.2 Design: Document Scanner Job
```python
# Periodic job to scan project docs folders
# Run on session start OR daily

Scan locations:
- C:\Projects\*\docs\*.md
- C:\Projects\*\CLAUDE.md
- C:\Projects\*\README.md
- C:\claude\shared\docs\*.md

For each document:
1. Calculate file hash (detect changes)
2. Categorize by type:
   - ARCHITECTURE - architecture*.md
   - CLAUDE_CONFIG - CLAUDE.md
   - README - README.md
   - SOP - *sop*.md, procedure*.md
   - GUIDE - *guide*.md, how-to*.md
   - API - api*.md, swagger*.md
   - SESSION_NOTE - session*.md, notes*.md
   - SPEC - *spec*.md, requirement*.md
3. Extract metadata (title, version if present)
4. Upsert to claude.documents
5. Link to project via project_id
```

### 3.3 Core Documents Registry
Special treatment for critical documents:

| Document Type | Location | Purpose |
|--------------|----------|---------|
| Global CLAUDE.md | ~/.claude/CLAUDE.md | User preferences, identity |
| Project CLAUDE.md | C:\Projects\{proj}\CLAUDE.md | Project rules |
| Architecture Plan | docs/ARCHITECTURE*.md | System design |
| Problem Statement | docs/PROBLEM_STATEMENT.md | What we're solving |
| Schema Registry | claude.schema_registry | Database documentation |
| ADRs | claude.architecture_decisions | Why decisions were made |

### 3.4 Document Categories for MCW
```sql
-- Add to claude.documents or create enum
doc_categories:
- 'architecture'    -- System design docs
- 'claude_config'   -- CLAUDE.md files
- 'api'             -- API documentation
- 'sop'             -- Procedures/SOPs
- 'guide'           -- How-to guides
- 'spec'            -- Requirements/specs
- 'session_note'    -- Session notes (archive after 30 days)
- 'readme'          -- Project READMEs
- 'adr'             -- Architecture Decision Records
```

---

## PART 4: Scheduler System Design

### 4.1 Current State
- `claude.scheduled_jobs` has 6 jobs defined
- None are running automatically
- `trigger_type` column doesn't exist yet

### 4.2 Event-Driven Execution Model
```sql
-- Add columns to scheduled_jobs
ALTER TABLE claude.scheduled_jobs ADD COLUMN IF NOT EXISTS
  trigger_type VARCHAR(50) DEFAULT 'session_start';
  -- Values: 'session_start', 'session_end', 'on_demand', 'schedule'

ALTER TABLE claude.scheduled_jobs ADD COLUMN IF NOT EXISTS
  trigger_condition JSONB DEFAULT '{}';
  -- Examples:
  -- {"days_since_last_run": 7}
  -- {"project_match": "mcw"}
  -- {"check_type": "docs", "max_stale_days": 14}
```

### 4.3 Session Startup Hook Integration
```python
# Add to session_startup_hook.py

def check_due_jobs(project_name: str) -> list:
    """Check for jobs that should run this session."""
    query = """
        SELECT job_id, job_name, job_description, command
        FROM claude.scheduled_jobs
        WHERE is_active = true
        AND trigger_type = 'session_start'
        AND (
            -- Days since last run check
            (trigger_condition->>'days_since_last_run')::int <=
            EXTRACT(DAY FROM NOW() - COALESCE(last_run, created_at))
            OR
            -- Project match
            trigger_condition->>'project_match' = %s
            OR
            trigger_condition->>'project_match' IS NULL
        )
        ORDER BY priority ASC NULLS LAST
        LIMIT 3;
    """
    # Return list of due jobs for Claude to decide whether to run
```

### 4.4 Initial Job Set
| Job | Trigger | Condition | Action |
|-----|---------|-----------|--------|
| Document Scanner | session_start | days >= 1 | Scan and index docs |
| Reminder Check | session_start | always | Check due reminders |
| MCP Memory Sync | session_start | days >= 3 | Sync memory to DB |
| Security Scan | session_start | days >= 7, project_match | Run security-sonnet |
| Test Health Check | session_start | days >= 3 | Report test pass rates |
| DB Backup | schedule | weekly | Backup PostgreSQL |

---

## PART 5: RTX 5080 Local AI Integration

### 5.1 Hardware Specs
- **VRAM:** 16GB GDDR7
- **Architecture:** Blackwell
- **Performance:** ~70 tok/s on DeepSeek-r1:14b (verified!)

### 5.2 Current Setup Status (Updated 2025-12-02)

**Framework:** Ollama v0.13.0 (installed and working)

**Models Installed:**
| Model | Size | Status | Performance | Use Case |
|-------|------|--------|-------------|----------|
| deepseek-r1:14b | 9.0 GB | ✅ INSTALLED | 70 tok/s | Reasoning, complex tasks |
| qwen2.5-coder:14b | 9.0 GB | ⏳ DOWNLOADING | ~70 tok/s | Code generation |
| nomic-embed-text | 274 MB | ✅ INSTALLED | Fast | Embeddings for RAG |
| gemma3:4b | 3.3 GB | ✅ INSTALLED | ~100+ tok/s | Fast fallback |
| llama3.3:8b | ~5 GB | ⏳ PENDING | ~90 tok/s | General purpose |

**MCP Server:** `ollama-mcp` configured in `.mcp.json`
```json
"ollama": {
  "type": "stdio",
  "command": "cmd",
  "args": ["/c", "npx", "-y", "ollama-mcp"],
  "env": {
    "OLLAMA_HOST": "http://localhost:11434"
  }
}
```

### 5.3 MCP Integration Options

**Option A: ollama-mcp (IMPLEMENTED)**
- Exposes complete Ollama SDK as MCP tools
- 14 tools available for model management and inference
- Package: `npx -y ollama-mcp`
- GitHub: [rawveg/ollama-mcp](https://github.com/rawveg/ollama-mcp)

**Option B: OllamaClade (Token Saving) - Future**
- Delegates coding tasks to local Ollama
- Up to 98.75% Anthropic API token reduction
- Best for: repetitive coding tasks
- GitHub: [jadael/ollamaclade](https://lobehub.com/mcp/jadael-ollamaclade)

**Option C: Ollama MCP Bridge - Future**
- Enables Ollama to USE MCP tools (reverse direction)
- Local LLM can access filesystem, postgres, etc.
- GitHub: [patruff/ollama-mcp-bridge](https://github.com/patruff/ollama-mcp-bridge)

### 5.4 Recommended Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code (Main)                    │
│                    Opus/Sonnet Models                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ Orchestrator │    │  ollama-mcp  │    │  Ollama   │ │
│  │     MCP      │    │     MCP      │    │  Server   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│         │                   │                   │       │
│         ▼                   ▼                   ▼       │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │ Spawn Agents │    │ Delegate to  │    │  Local    │ │
│  │ (haiku/son)  │    │ Local LLM    │    │  Models   │ │
│  └──────────────┘    └──────────────┘    └───────────┘ │
│                                                          │
│  Use Cases:                                              │
│  - Code completion → ollama-mcp → qwen2.5-coder:14b    │
│  - Embeddings → ollama-mcp → nomic-embed-text          │
│  - Complex reasoning → Keep on Claude                   │
│  - Bulk file processing → Local LLM                     │
└─────────────────────────────────────────────────────────┘
```

### 5.5 Implementation Steps
1. [x] Install Ollama on Windows (v0.13.0)
2. [x] Pull deepseek-r1:14b model (9.0 GB, 70 tok/s verified)
3. [ ] Pull qwen2.5-coder:14b model (downloading...)
4. [ ] Pull llama3.3:8b model (pending)
5. [x] Install ollama-mcp server (configured in .mcp.json)
6. [ ] Test delegation of simple tasks (after Claude Code restart)
7. [ ] Measure token savings
8. [ ] Add to orchestrator as optional backend

---

## PART 6: Data Fixes & Cleanup

### 6.1 Knowledge Base
- [ ] Verify MCW can read claude.knowledge (139 rows)
- [ ] Standardize knowledge_type values
- [ ] Standardize knowledge_category values
- [ ] Add scope column (universal/project/domain/technology)
- [ ] Sync MCP memory graph TO postgres

### 6.2 Documents
- [ ] Clean test documents from claude.documents
- [ ] Create document scanner script
- [ ] Index all project docs
- [ ] Categorize core documents

### 6.3 Sessions/History
- [ ] Verify session logging works with new schema
- [ ] Clean up any orphan sessions

### 6.4 Reminders
- [ ] Reminder for Dec 8: Drop backward-compat views
- [ ] Add reminder checking to startup hook

---

## PART 7: Governance & Rules

### 7.1 Database Usage Rules (Reinstate)
```
MANDATORY FOR ALL SESSIONS:
1. Log session start to claude.sessions
2. Check claude.knowledge before proposing solutions
3. Store learnings in claude.knowledge at session end
4. Update claude.session_state with todo list
5. Check claude.reminders on startup
```

### 7.2 Core Files to Maintain
```
Per Project:
- CLAUDE.md (project rules)
- docs/ARCHITECTURE.md (system design)
- docs/PROBLEM_STATEMENT.md (what we're solving)
- .mcp.json (MCP config)
- .claude/settings.local.json (hooks, permissions)

Global:
- ~/.claude/CLAUDE.md (user preferences)
- claude.schema_registry (all tables documented)
- claude.architecture_decisions (all ADRs)
```

---

## PART 8: Priority Order

### Immediate (This Session) - COMPLETED ✅
1. ✅ Create this master TODO document
2. ✅ Send MCW feature requests message (messaging, agents, knowledge, scheduler)
3. ✅ Fix reminder checking in startup hook (`get_due_reminders()`, `get_due_jobs()`)
4. ✅ Create document scanner script (`scripts/scan_documents.py`)
5. ✅ Add scheduler trigger columns (`trigger_type`, `trigger_condition`, `priority`)
6. ✅ Install Ollama + pull deepseek-r1:14b (70 tok/s verified!)
7. ✅ Configure ollama-mcp in .mcp.json

### In Progress
8. ⏳ Pull qwen2.5-coder:14b model (downloading ~10 min)
9. ⏳ Pull llama3.3:8b model (pending)

### This Week
10. Wire MCW knowledge tab
11. Index all project documents (run scan_documents.py)
12. Test ollama-mcp delegation after Claude Code restart

### Next Week
13. MCW implements messaging view
14. MCW implements agents dashboard
15. Full document management system
16. OllamaClade integration for token savings

### Ongoing
- Database governance enforcement
- Knowledge base curation
- Document freshness monitoring
- Reminder-based task tracking

---

## Sources

**RTX 5080 Local AI:**
- [Best Local LLMs for RTX 50 Series](https://apxml.com/posts/best-local-llms-for-every-nvidia-rtx-50-series-gpu)
- [Best GPUs for LLM Inference 2025](https://localllm.in/blog/best-gpus-llm-inference-2025)
- [Local LLM Hosting Guide 2025](https://www.glukhov.org/post/2025/11/hosting-llms-ollama-localai-jan-lmstudio-vllm-comparison/)

**Ollama MCP Integration:**
- [rawveg/ollama-mcp](https://github.com/rawveg/ollama-mcp)
- [OllamaClade for Claude Code](https://lobehub.com/mcp/jadael-ollamaclade)
- [Ollama MCP Bridge](https://github.com/patruff/ollama-mcp-bridge)

---

**Document Version:** 1.0
**Next Review:** 2025-12-09 (after backward-compat views cleanup)
