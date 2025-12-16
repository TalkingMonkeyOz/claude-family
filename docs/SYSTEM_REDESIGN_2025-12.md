# Claude Family System Redesign - December 2025

**Status**: IN PROGRESS
**Author**: claude-opus-4-5 + John
**Created**: 2025-12-16
**Purpose**: Comprehensive system redesign following PID (Project Initiation Document) methodology

---

## 1. Executive Summary

### Current State
The Claude Family infrastructure has grown organically to include:
- PostgreSQL database with 3 schemas, 13+ tables
- 3 custom MCP servers (orchestrator, flaui-testing, tool-search)
- 32 workflows via process router
- 6 Claude identities
- Session management (start/end/resume)
- Hook-based enforcement system

### Problems Identified
1. **Context Loss** - Claude loses context quickly, especially in Desktop
2. **Knowledge Discovery** - Claude doesn't know what tools/docs exist to use
3. **Database Integrity** - 15 missing constraints, orphan risks
4. **Documentation Bloat** - 100+ files, unclear what's authoritative
5. **Hook Performance** - Concern about slowdown from too many hooks

### Goals
1. Feature-rich system with minimal code (AI-first approach)
2. Proper referential integrity across all tables
3. Knowledge discovery system so Claude knows what it can use
4. Well-documented with testable process flows
5. Optimized hooks - effective but not slow

---

## 2. Research Summary

### 2.1 AI Context Management Best Practices

**Key Findings:**

1. **CLAUDE.md as Pointer Document** (< 200 lines)
   - Should be a navigation map, not knowledge base
   - Include "Before starting, check..." sections
   - Link to hierarchical docs

2. **Parent-Child Document Chunking**
   - Small "child" chunks (100-500 tokens) for retrieval/embedding
   - Larger "parent" chunks (500-2000 tokens) for context
   - Retrieval finds child, returns parent for full context

3. **Tiered Storage Architecture**
   - Immediate: Current file/function
   - Session: What's been discussed this session
   - Project: Overall architecture
   - Historical: Past decisions

4. **RAG Best Practices**
   - 10 good chunks > 100 mediocre chunks
   - Two-step retrieval: fast filter → LLM rerank
   - Place critical info at beginning/end of context

### 2.2 Process Documentation Best Practices

**Key Findings:**

1. **Agent Stories Format**
   ```
   As [Agent Name/Type]
   When [trigger condition]
   I should [autonomous action]
   With tools [tool list]
   Success criteria: [measurable outcome]
   Escalate if: [conditions requiring human intervention]
   ```

2. **YAML Process Definitions** - Machine-readable, AI-parseable

3. **Mermaid Diagrams** - Render in Markdown, version controllable

4. **Event Sourcing for Sessions** - Immutable log of AI decisions

### 2.3 Database Integrity Analysis

**Critical Missing Constraints (15 total):**

| Issue | Tables Affected | Priority |
|-------|-----------------|----------|
| ON DELETE missing | api_usage_data, api_cost_data, usage_summary, budget_alerts, usage_sync_status | CRITICAL |
| No FK validation on arrays | shared_knowledge.related_knowledge[] | HIGH |
| No project registry | api_usage_data.project_name, etc. | HIGH |
| No CHECK constraints | knowledge_type, context_type, bucket_width, etc. | MEDIUM |

---

## 3. Proposed Architecture

### 3.1 Knowledge Discovery System

**Problem**: Claude doesn't know what docs/tools exist to use them

**Solution**: Layered Knowledge Discovery

```
┌─────────────────────────────────────────────────────────────┐
│                     CLAUDE.md (Layer 0)                      │
│  ~100 lines - Pointer document with "Before doing X, see Y" │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Knowledge Index (Layer 1)                  │
│  KNOWLEDGE_INDEX.md - Categorized list of all resources     │
│  Categories: Commands, SOPs, Standards, APIs, Tools         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Feature Documents (Layer 2)                 │
│  Individual docs with details: SOPs, ADRs, Standards        │
│  Each doc is self-contained but cross-referenced            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Memory Graph (Layer 3)                       │
│  MCP Memory server for semantic search                       │
│  Entities: concepts, learnings, gotchas, patterns           │
└─────────────────────────────────────────────────────────────┘
```

**Key Components:**

1. **CLAUDE.md** - Navigation map only
   - Project identity
   - Quick commands reference
   - "Before X, check Y" pointers
   - Recent changes (last 5)

2. **KNOWLEDGE_INDEX.md** - Master resource list
   - All commands with one-line descriptions
   - All SOPs categorized
   - All standards listed
   - Tools and MCPs available
   - "See also" cross-references

3. **Process Router Enhancement** - Inject knowledge hints
   - When matching workflow, include "Available resources" hint
   - Link to relevant docs for that workflow

### 3.2 Database Schema - Fixed & Expanded

**Phase 1: Integrity Fixes** (SQL script to run)

```sql
-- 1. Add ON DELETE SET NULL to usage tables
ALTER TABLE claude_family.api_usage_data
DROP CONSTRAINT IF EXISTS api_usage_data_identity_id_fkey,
ADD CONSTRAINT api_usage_data_identity_id_fkey
  FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
  ON DELETE SET NULL;

-- (similar for api_cost_data, usage_summary, budget_alerts, usage_sync_status)

-- 2. Add CHECK constraints
ALTER TABLE claude_family.shared_knowledge
ADD CONSTRAINT knowledge_type_check CHECK (
  knowledge_type IN ('pattern','gotcha','bug-fix','architecture','technique',
                     'best-practice','troubleshooting','process','configuration',
                     'mcp-tool','mcp-server')
);

-- 3. Create projects_registry for referential integrity
CREATE TABLE IF NOT EXISTS claude_family.projects_registry (
  project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_name VARCHAR(255) UNIQUE NOT NULL,
  project_schema VARCHAR(100),
  project_type VARCHAR(50),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create knowledge_relations junction table
CREATE TABLE IF NOT EXISTS claude_family.knowledge_relations (
  relation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_knowledge_id UUID NOT NULL REFERENCES claude_family.shared_knowledge(knowledge_id) ON DELETE CASCADE,
  related_knowledge_id UUID NOT NULL REFERENCES claude_family.shared_knowledge(knowledge_id) ON DELETE CASCADE,
  relation_type VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(parent_knowledge_id, related_knowledge_id)
);
```

**Phase 2: New Tables**

```sql
-- Document chunks for AI retrieval
CREATE TABLE claude_family.document_chunks (
  chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_id UUID REFERENCES claude.documents(doc_id) ON DELETE CASCADE,
  parent_chunk_id UUID REFERENCES claude_family.document_chunks(chunk_id),
  chunk_type VARCHAR(20) CHECK (chunk_type IN ('parent', 'child')),
  content TEXT NOT NULL,
  embedding VECTOR(1536),  -- For semantic search
  token_count INTEGER,
  chunk_order INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Test storage (per user request)
CREATE TABLE claude.stored_tests (
  test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES claude.projects(project_id) ON DELETE CASCADE,
  test_name VARCHAR(255) NOT NULL,
  test_type VARCHAR(50) CHECK (test_type IN ('unit', 'integration', 'e2e', 'process', 'workflow')),
  test_definition JSONB NOT NULL,  -- YAML stored as JSON
  last_run_at TIMESTAMPTZ,
  last_result VARCHAR(20) CHECK (last_result IN ('pass', 'fail', 'skip', 'error')),
  run_count INTEGER DEFAULT 0,
  is_archived BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  created_by_identity_id UUID REFERENCES claude_family.identities(identity_id)
);
```

### 3.3 Session Flow (BPMN-Inspired)

```
┌─────────────────────────────────────────────────────────────┐
│                    SESSION LIFECYCLE                         │
└─────────────────────────────────────────────────────────────┘

[User Opens Claude]
       │
       ▼
┌──────────────────┐
│  SessionStart    │ ◀── Hook fires automatically
│  Hook            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────────┐
│ Load Identity    │────▶│ Query claude.identities │
│ (BLOCKING)       │     └─────────────────────────┘
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────────┐
│ Load Project     │────▶│ Detect from CWD         │
│ Context          │     │ Query claude.projects   │
└────────┬─────────┘     └─────────────────────────┘
         │
         ▼
┌──────────────────┐
│ Check Previous   │────▶ Did last session end cleanly?
│ Session          │      │
└────────┬─────────┘      ├─ YES: Load summary
         │                └─ NO: Offer to resume
         ▼
┌──────────────────┐     ┌─────────────────────────┐
│ Check Messages   │────▶│ orchestrator.check_inbox│
│ & Knowledge      │     │ memory.query            │
└────────┬─────────┘     └─────────────────────────┘
         │
         ▼
┌──────────────────┐
│ Present Startup  │────▶ Display to user:
│ Card             │      - Identity confirmed
└────────┬─────────┘      - Project: {name}
         │                - Previous session: {summary}
         ▼                - Pending messages: {count}
┌──────────────────┐      - Suggested action: {next}
│ Ready for Work   │
└──────────────────┘
         │
    (User works)
         │
         ▼
┌──────────────────┐
│  SessionEnd      │ ◀── User runs /session-end OR triggered
│  Hook            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────────────┐
│ Save Session     │────▶│ Update claude.sessions  │
│ State            │     │ Save to memory graph    │
└────────┬─────────┘     │ Write TODO_NEXT_SESSION │
         │               └─────────────────────────┘
         ▼
┌──────────────────┐
│ Extract          │────▶ What was learned?
│ Knowledge        │      Store in shared_knowledge
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Session Complete │
└──────────────────┘
```

### 3.4 Hook Optimization Strategy

**Current Concern**: Too many hooks = slow performance

**Proposed Solution**: Tiered Hook Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     HOOK TIERS                                │
├──────────────────────────────────────────────────────────────┤
│ TIER 1: Always Run (< 100ms)                                 │
│ - Session start/end detection                                 │
│ - Critical validation (prevent data loss)                     │
│                                                               │
│ TIER 2: Smart Activation (100-500ms)                         │
│ - Process router (only on user prompts)                       │
│ - DB validation (only on write operations)                    │
│                                                               │
│ TIER 3: On-Demand (async, no blocking)                       │
│ - Knowledge extraction                                        │
│ - Documentation staleness checks                              │
│ - Message checking (periodic, not every action)               │
└──────────────────────────────────────────────────────────────┘
```

**Implementation**: Configure hooks.json with conditional execution

```json
{
  "hooks": [
    {
      "event": "UserPromptSubmit",
      "command": "python process_router.py",
      "timeout": 5000,
      "condition": "prompt.length > 10"  // Skip trivial prompts
    },
    {
      "event": "PreToolUse",
      "command": "python validate_db_write.py",
      "timeout": 2000,
      "condition": "tool.name.startsWith('mcp__postgres')"  // Only DB ops
    }
  ]
}
```

---

## 4. User Stories

### 4.1 Core User Stories (John's Perspective)

#### US-001: Start a Work Session
```
As John
When I open Claude Code in a project folder
I want Claude to automatically know:
  - What project this is
  - What I was working on last time
  - Any messages from other Claude instances
  - What I should do next
So that I can immediately continue productive work without re-explaining context
```

**Acceptance Criteria:**
- [ ] Session starts within 5 seconds
- [ ] Previous session summary displayed
- [ ] Pending todos shown
- [ ] No manual setup required

#### US-002: Find the Right Process
```
As John
When I describe what I want to do (e.g., "fix this bug", "add a feature")
I want Claude to automatically:
  - Detect what type of work this is
  - Load relevant standards/SOPs
  - Guide me through the right process
So that work is consistent and nothing is forgotten
```

**Acceptance Criteria:**
- [ ] Process detection in < 2 seconds
- [ ] Relevant docs automatically loaded
- [ ] Step-by-step guidance provided
- [ ] Manual override available

#### US-003: Store and Run Tests
```
As John
When I create a test for a workflow or feature
I want to save it for future runs
So that I can re-validate that things still work after changes
```

**Acceptance Criteria:**
- [ ] Tests stored in database with metadata
- [ ] Can list all tests for a project
- [ ] Can run individual or all tests
- [ ] Results tracked over time

#### US-004: Discover Available Features
```
As John
When I ask "what can Claude do?" or "how do I X?"
I want Claude to search its knowledge and tell me:
  - What commands are available
  - What SOPs apply
  - What tools can help
So that I don't have to remember everything or read all docs
```

**Acceptance Criteria:**
- [ ] Quick response (< 3 seconds)
- [ ] Returns relevant commands/docs
- [ ] Includes "how to use" examples
- [ ] Works conversationally

#### US-005: Maintain Context Across Sessions
```
As John
When I resume work the next day or after Desktop loses context
I want Claude to pick up where we left off
So that I don't have to re-explain the entire project state
```

**Acceptance Criteria:**
- [ ] Session state persisted to database
- [ ] Memory graph retains key facts
- [ ] TODO_NEXT_SESSION.md available as backup
- [ ] Claude proactively reads context at startup

### 4.2 Agent Stories (Claude's Perspective)

#### AS-001: Session Initialization
```
As claude-code-unified
When SessionStart hook fires
I should:
  1. Query my identity from claude_family.identities
  2. Detect project from working directory
  3. Load previous session context from claude.sessions
  4. Query memory graph for relevant knowledge
  5. Check inbox via mcp__orchestrator__check_inbox
  6. Create new session record
  7. Present startup summary to user

With tools:
  - mcp__postgres__execute_sql
  - mcp__memory__query
  - mcp__orchestrator__check_inbox
  - Read (file system)

Success criteria:
  - Session record created in database
  - Context loaded within 5 seconds
  - User sees startup card

Escalate if:
  - Cannot determine identity (ask user)
  - Database connection fails after 3 retries
  - Multiple orphaned sessions found (ask which to resume)
```

#### AS-002: Process Classification
```
As claude-code-unified
When user submits a prompt (UserPromptSubmit event)
I should:
  1. Run fast regex matching against 53 triggers
  2. If match found, inject process guidance
  3. If no match, use LLM classification
  4. If still no match, proceed without process
  5. Include relevant standards in context

With tools:
  - process_router.py
  - LLM classification (fallback)

Success criteria:
  - Classification within 2 seconds
  - Correct process identified 90%+ of time
  - Relevant standards injected

Escalate if:
  - Classification confidence < 50%
  - Multiple processes could apply
```

---

## 5. Implementation Phases

### Phase 1: Database Integrity (Day 1-2)
- [ ] Run integrity fix SQL script
- [ ] Create projects_registry table
- [ ] Create knowledge_relations junction table
- [ ] Verify all FK constraints working
- [ ] Test cascade/set-null behavior

### Phase 2: Knowledge Discovery (Day 3-5)
- [ ] Create KNOWLEDGE_INDEX.md
- [ ] Slim down CLAUDE.md to pointer document
- [ ] Enhance process router to inject knowledge hints
- [ ] Create /discover command for feature discovery
- [ ] Test knowledge retrieval flows

### Phase 3: Session Enhancement (Day 6-8)
- [ ] Improve session start hook (faster, more info)
- [ ] Add session state persistence
- [ ] Create session resume flow
- [ ] Add context transfer between sessions
- [ ] Test session lifecycle end-to-end

### Phase 4: Test Storage (Day 9-10)
- [ ] Create stored_tests table
- [ ] Create /store-test command
- [ ] Create /run-tests command
- [ ] Implement test result tracking
- [ ] Create test report view

### Phase 5: Hook Optimization (Day 11-12)
- [ ] Profile current hook performance
- [ ] Implement tiered hook architecture
- [ ] Add conditional execution
- [ ] Measure improvement
- [ ] Document optimal configuration

### Phase 6: Documentation & Validation (Day 13-14)
- [ ] Update all architecture docs
- [ ] Create BPMN diagrams for key flows
- [ ] Write integration tests
- [ ] User acceptance testing
- [ ] Final cleanup

---

## 6. Unified Plan (Merged with SYSTEM_IMPROVEMENT_PLAN)

### 6.1 PID Development Process (5-Phase)

From pid-process.jsx - the systematic approach we must follow:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PID 5-PHASE PROCESS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: EXPLORATION (Document Review)                         │
│  ├── Load existing code/docs                                     │
│  ├── Gap analysis - what's missing?                              │
│  └── Compile questions list                                      │
│                                                                  │
│  Phase 2: RESOLUTION (Question Resolution)                       │
│  ├── Answer questions with REAL data                             │
│  ├── Validate assumptions against actual system                  │
│  └── Iterate until all gaps resolved                             │
│                                                                  │
│  Phase 3: VALIDATION (Technical Validation)                      │
│  ├── Data flow verification                                      │
│  ├── API/DB confirmation                                         │
│  └── Insert/Update pattern testing                               │
│                                                                  │
│  Phase 4: DESIGN (Application Design)                            │
│  ├── UI specification                                            │
│  ├── Data management approach                                    │
│  └── Logging/debugging strategy                                  │
│                                                                  │
│  Phase 5: REVIEW (Final Review)                                  │
│  ├── E2E walkthrough                                             │
│  ├── Checklist validation                                        │
│  └── Sign-off                                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Anti-Patterns to Avoid:**
- ❌ Don't assume - verify against real data
- ❌ Don't batch questions endlessly - iterate
- ❌ Don't skip edge cases - nulls, duplicates
- ❌ Don't forget logging - needed for debugging
- ❌ Don't hardcode - use lookups/caches
- ❌ Don't trust field names - verify schema

### 6.2 Simplification First (From SYSTEM_IMPROVEMENT_PLAN)

**Before adding new features, simplify:**

| Current | Target | Action |
|---------|--------|--------|
| 32 workflows | 8 core workflows | Archive 24 |
| 50 tables | ~35 tables | Drop 4 empty, archive stale |
| 12 identities | 2 active | Archive unused |
| 23 projects | 5 active | Archive inactive |

**8 Core Workflows to Keep:**
1. Session Start/End
2. Bug Fix
3. Feature Development (with TDD)
4. Code Review
5. Documentation Update
6. Database Change
7. Test Suite (NEW)
8. Deployment

### 6.3 Stop Hook Enforcer (C4 - Critical)

**Problem**: "I'LL FORGET TO USE IT SO WILL YOU"

**Solution**: Counter-based automatic reminders via Stop hook

```
┌─────────────────────────────────────────────────────────────────┐
│                 STOP HOOK ENFORCER                               │
├─────────────────────────────────────────────────────────────────┤
│ Interval    │ Check              │ Reminder                     │
├─────────────┼────────────────────┼──────────────────────────────┤
│ Every 5     │ Git status         │ "Consider committing"        │
│ Every 10    │ Inbox check        │ "Run /inbox-check"           │
│ Every 20    │ CLAUDE.md refresh  │ "Re-read CLAUDE.md"          │
│ On code Δ   │ Test tracking      │ "X files changed, no tests"  │
└─────────────────────────────────────────────────────────────────┘
```

**State Storage**: `~/.claude/state/enforcement_state.json`

### 6.4 Knowledge Auto-Injection (C5)

**Problem**: 161 knowledge entries exist but aren't used

**Solution**: Auto-query `claude.knowledge` on UserPromptSubmit

**Topic Detection Keywords:**
| Topic | Keywords |
|-------|----------|
| nimbus | nimbus, shift, schedule, employment, roster |
| api | api, odata, rest, endpoint, request |
| import | import, importer, loader, sync, migration |
| tax | tax, ato, tfn, abn, bas, payg |
| database | database, postgres, sql, query, schema |
| react | react, component, hook, state, jsx |

**Injection Format:**
```xml
<relevant-knowledge>
Found 3 relevant entries:
### Entry Title
**Category**: api | **Tags**: nimbus, shifts
Content here...
</relevant-knowledge>
```

### 6.5 TDD Enforcement

**New Command**: `/test-first`

**PreCommit Hook Check:**
```python
if code_files_changed and not test_files_changed:
    return BLOCK, "No tests included. Use /test-first"
```

### 6.6 Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Table utilization | 30% | 80% |
| Workflow completion | Unknown | 90% |
| Test coverage | 0% | 70% |
| Session closure | Unknown | 95% |
| Agent success | ~46% | 80% |
| Context carryover | Manual | Auto |

---

## 7. Revised Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | A: Cleanup | Drop empty tables, archive inactive projects |
| 1 | B: DB Integrity | Fix 15 FK constraints, add registries |
| 2 | C: Simplification | 8 core workflows, quick ref cards |
| 2 | D: Stop Hook | Implement counter-based enforcer |
| 3 | E: Knowledge | Auto-injection from claude.knowledge |
| 3 | F: TDD | /test-first command, precommit check |
| 4 | G: Session | Enhanced context persistence |
| 5 | H: Documentation | Architecture diagrams, validation |

---

## 8. Files to Create/Modify

### Status Check (Verified 2025-12-16)
| File | Status |
|------|--------|
| `scripts/stop_hook_enforcer.py` | **CREATED** 2025-12-16 - needs hook config + testing |
| `scripts/sql/db_integrity_fix.sql` | **CREATED** 2025-12-16 - needs running on DB |
| `.claude/commands/test-first.md` | **CREATED** 2025-12-16 - needs testing |
| `scripts/process_router.py` | EXISTS - has standards injection, NO knowledge auto-injection yet |

### Still To Create
| File | Purpose |
|------|---------|
| `scripts/cleanup_archive.sql` | Archive stale data |
| `docs/KNOWLEDGE_INDEX.md` | Master resource list |
| `docs/standards/DEVELOPMENT_QUICKREF.md` | Quick reference |
| Knowledge injection in `process_router.py` | Auto-query claude.knowledge on UserPromptSubmit |

---

## 9. Context Persistence Note

**For Claude instances reading this document:**

This document is the working plan for the Claude Family system redesign.

**Key files to check:**
- `/home/user/claude-family/ARCHITECTURE.md` - Current system design
- `/home/user/claude-family/docs/CLAUDE_GOVERNANCE_SYSTEM_PLAN.md` - Existing plan (compare/merge)
- `/home/user/claude-family/postgres/schema/` - Database schemas
- `/home/user/claude-family/.claude/hooks.json` - Current hooks

**Database research completed - see Section 2.3 for findings.**

**Research completed - see Section 2.1 and 2.2 for best practices.**

---

## 10. Infrastructure Reality Check (What's Working NOW)

**Verified 2025-12-16** - These systems are deployed and have real usage data.

### 10.1 Orchestrator MCP - PRODUCTION READY

| Metric | Value | Source |
|--------|-------|--------|
| Total Agent Sessions | 98 | claude.agent_sessions |
| Agent Types Available | 13 (reduced from 31) | agent_specs.json |
| Status | Production Ready | mcp-servers/orchestrator/STATUS.md |

**Top Agents by Usage:**
| Agent | Sessions | Success Rate |
|-------|----------|--------------|
| coder-haiku | 28 | 46% |
| python-coder-haiku | 25 | 80% |
| lightweight-haiku | 12 | 83% |
| reviewer-sonnet | 8 | 50% |
| researcher-opus | 5 | 20% |

**Issue**: coder-haiku (most used) has 46% failure rate - needs investigation.

### 10.2 Session System - WORKING

| Component | Status | Location |
|-----------|--------|----------|
| session_history table | 154 sessions logged | claude_family.session_history |
| SessionStart hook | Active | .claude/hooks.json |
| SessionEnd hook | Active | .claude/hooks.json |
| session_startup_hook.py | EXISTS | scripts/ |

### 10.3 Messaging System - WORKING

| Metric | Value |
|--------|-------|
| Messages in DB | 84 |
| MCP Tool | mcp__orchestrator__check_inbox |

### 10.4 Process Router - PARTIALLY WORKING

| Feature | Status |
|---------|--------|
| 53 workflow triggers | Active |
| Standards injection | Working |
| Knowledge auto-injection | **NOT IMPLEMENTED** |
| LLM fallback classification | Working |

### 10.5 Database Logging - WORKING

| Table | Purpose | Active |
|-------|---------|--------|
| claude.agent_sessions | Agent spawn/completion | YES |
| claude_family.session_history | Session tracking | YES |
| claude_family.shared_knowledge | 161 entries | YES (but not auto-queried) |

### 10.6 What's NOT Working / Missing

| Feature | Status | Action Needed |
|---------|--------|---------------|
| Stop Hook Enforcer | Script created, not deployed | Add to hooks.json |
| Knowledge Auto-Injection | Designed, not implemented | Add to process_router.py |
| TDD Enforcement | Command created, not tested | Test /test-first |
| DB Integrity | Script created, not run | Run db_integrity_fix.sql |
| PreCommit test check | Not implemented | Add to pre_commit_check.py |

---

**Version**: 0.2 (Draft - Files Created)
**Last Updated**: 2025-12-16
**Location**: /home/user/claude-family/docs/SYSTEM_REDESIGN_2025-12.md
