---
projects:
- claude-family
tags:
- session
- architecture
- index
- quick-reference
synced: false
---

# Session Architecture

**Purpose**: Human-friendly overview of how Claude sessions work
**Audience**: Developers and Claude instances needing to understand the system
**Last Updated**: 2025-12-26

---

## The Big Picture

When you launch Claude on a project, here's what happens:

1. **Session Hook Fires** → Creates a record in the database
2. **Identity Resolved** → Determines "which Claude" you are
3. **Context Loaded** → Restores your previous work state
4. **You Work** → Your actions are tracked (sessions, agents, MCP calls)
5. **Session Ends** → Everything is saved for next time

**Goal**: Never lose context between sessions. Always know who did what, when, and why.

---

## Core Principles

### 1. Every Session is Logged
- Each time Claude starts, a session record is created in `claude.sessions`
- Tracks: who (identity), what (project), when (timestamps), outcomes (summary, tasks)
- **Gap**: Currently 10% of sessions have NULL identity_id

### 2. State Persists Between Sessions
- Todo list, current focus, next steps saved to `claude.session_state`
- When you resume next day, you pick up exactly where you left off
- **Pattern**: One state record per project (singleton)

### 3. Identity Per Instance
- Each Claude instance has an identity (e.g., claude-code-unified, claude-desktop)
- **Target**: Each project should have its own identity (e.g., claude-ato-agent)
- **Current Problem**: All CLI sessions use same hardcoded identity

### 4. Agents are Tracked Separately
- When Claude spawns an agent, it's logged to `claude.agent_sessions`
- Includes cost tracking, success/failure, results
- **Gap**: No parent_session_id linkage (all 144 agents are orphaned)

### 5. Everything is Connected
- Sessions → Projects → Identities → Workspaces
- Agents → Sessions (parent tracking missing)
- MCP usage → Sessions (currently broken, env var not exported)

---

## Database Structure (Core 7 Tables)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Session Tracking Layer                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  identities  │        │   projects   │        │  workspaces  │
│──────────────│        │──────────────│        │──────────────│
│ identity_id  │        │ project_id   │        │ workspace_id │
│ identity_name│        │ project_name │        │ path         │
│ platform     │        │ phase        │        │ project_name │
│ status       │        │ status       │        │ display_name │
└──────┬───────┘        └──────┬───────┘        └──────────────┘
       │                       │
       │                       │
       └───────┬───────────────┘
               │
               ▼
       ┌──────────────┐
       │   sessions   │◄──────────────────┐
       │──────────────│                   │
       │ session_id   │                   │ (parent_session_id - MISSING)
       │ identity_id  │◄─────────┐        │
       │ project_name │           │        │
       │ session_start│           │        │
       │ session_end  │           │   ┌────┴──────────┐
       │ summary      │           │   │agent_sessions │
       │ tasks_done   │           │   │───────────────│
       │ learnings    │           │   │ session_id    │
       └──────┬───────┘           │   │ agent_type    │
              │                   │   │ task_desc     │
              │                   │   │ success       │
              ▼                   │   │ result        │
       ┌──────────────┐           │   │ cost_usd      │
       │session_state │           │   └───────────────┘
       │──────────────│           │
       │ project_name │ (PK)      │
       │ todo_list    │           │
       │ current_focus│           │
       │ next_steps   │           │
       └──────────────┘           │
                                  │
       ┌──────────────┐           │
       │  mcp_usage   │───────────┘
       │──────────────│
       │ session_id   │ (FK to sessions)
       │ tool_name    │
       │ success      │
       │ duration_ms  │
       └──────────────┘
```

**Key Relationships:**
- `sessions.identity_id` → `identities.identity_id` (FK **MISSING**)
- `sessions.project_name` → `projects.project_name` (string, not FK)
- `agent_sessions.created_by` → `sessions.session_id` (column **MISSING**)
- `mcp_usage.session_id` → `sessions.session_id` (FK **EXISTS**, only table with proper FKs!)

---

## How It Works: Session Lifecycle

### Session Start

```
User launches Claude
    ↓
SessionStart hook fires
    ↓
session_startup_hook.py runs
    ↓
┌─────────────────────────────┐
│ 1. Determine project name   │ (from cwd)
│ 2. Resolve identity         │ (hardcoded currently)
│ 3. Create session record    │ (INSERT sessions)
│ 4. Load saved state         │ (SELECT session_state)
│ 5. Check messages           │ (SELECT messages)
│ 6. Load CLAUDE.md files     │ (global + project)
└─────────────────────────────┘
    ↓
Return context to Claude
    ↓
Claude ready to work
```

**What Gets Logged:**
```sql
INSERT INTO claude.sessions (session_id, identity_id, project_name, session_start)
VALUES (gen_random_uuid(), 'ff32276f-9d05...', 'ATO-Tax-Agent', NOW());
```

### During Session

- **TodoWrite** → Updates todo list (in-memory, saved at session end)
- **Agent Spawn** → Logs to `agent_sessions` table
- **MCP Tool Calls** → Should log to `mcp_usage` (broken, env var not exported)
- **Work Progress** → Tracked in conversation, summarized at end

### Session End

```
User runs /session-end
    ↓
Claude reviews conversation
    ↓
┌─────────────────────────────┐
│ 1. Generate summary         │
│ 2. Extract tasks completed  │
│ 3. Extract learnings        │
│ 4. Update session record    │ (UPDATE sessions SET session_end, summary, ...)
│ 5. Save session state       │ (UPSERT session_state)
│ 6. Capture knowledge        │ (CREATE memory entities)
└─────────────────────────────┘
    ↓
Session saved!
```

**What Gets Saved:**
```sql
-- Update session with outcomes
UPDATE claude.sessions
SET session_end = NOW(),
    session_summary = 'Implemented tax validation...',
    tasks_completed = ARRAY['Task 1', 'Task 2'],
    learnings_gained = ARRAY['Learning 1', 'Learning 2']
WHERE session_id = '...';

-- Save state for next time
UPSERT INTO claude.session_state (project_name, todo_list, current_focus, next_steps)
VALUES ('ATO-Tax-Agent', '["Todo 1", "Todo 2"]', 'Tax validation', 'Complete tests');
```

---

## Current System Status

### ✅ What's Working

| Component | Status |
|-----------|--------|
| Session creation | ✅ SessionStart hook fires, sessions logged |
| State persistence | ✅ Todo list, focus, next steps saved per project |
| Agent tracking | ✅ All agent spawns logged to agent_sessions |
| Knowledge capture | ✅ Learnings stored in memory graph |
| Message routing | ✅ Inter-Claude messaging via messages table |

### ⚠️ Known Gaps

| Problem | Impact | Fix Needed |
|---------|--------|------------|
| **Identity hardcoded** | All CLI sessions appear as same identity | Implement identity-per-project resolution |
| **10% sessions with NULL identity** | Can't track who did the work | Backfill + enforce identity_id NOT NULL |
| **No FK constraints** | Data integrity risks, orphaned records possible | Add FKs: sessions→identities, agent_sessions→sessions |
| **MCP usage logging broken** | Can't track MCP tool usage per session | Export CLAUDE_SESSION_ID env var in session hook |
| **144 agent sessions orphaned** | Can't link agents back to parent session | Add parent_session_id column to agent_sessions |

### 📊 Data Quality

```sql
-- Sessions
Total: 395 sessions
Missing identity: 39 (10%)
Oldest: 2025-10-29
Recent activity: Daily sessions on claude-family, ATO-Tax-Agent

-- Agent Sessions
Total: 144 agent spawns
Success rate: ~85%
Most used: doc-keeper-haiku, lightweight-haiku
All orphaned (no parent_session_id)

-- MCP Usage
Total: 13 records (should be thousands!)
Hook configured but not firing
```

---

## Navigation Guide

**Need to...** → **Read this doc:**

| Task | Document | Location |
|------|----------|----------|
| Understand table schemas in detail | [[Database Schema - Core Tables]] | 10-Projects/claude-family/ |
| Learn identity system design | [[Identity System]] | 10-Projects/claude-family/ |
| Understand complete session flow | [[Session Lifecycle]] | 40-Procedures/ |
| Quick SQL queries for sessions | [[Session Quick Reference]] | 40-Procedures/ |
| Trace a user story end-to-end | [[Session User Stories]] | 10-Projects/claude-family/ |
| High-level DB overview | [[Database Architecture]] | 20-Domains/ |
| Quick DB table list | [[Claude Family Postgres]] | Claude Family/ |
| Coordination rules | [[Family Rules]] | 40-Procedures/ |

**When to use each:**

- **New to the system?** Start here, then read [[Session Lifecycle]]
- **Need SQL examples?** [[Session Quick Reference]]
- **Understanding a specific table?** [[Database Schema - Core Tables]]
- **Debugging identity issues?** [[Identity System]]
- **Validating a flow?** [[Session User Stories]]
- **Implementing fixes?** [[Session Lifecycle]] + [[Identity System]]

---

## Key Takeaways

1. **Sessions are automatic** - SessionStart hook creates the record, you don't have to
2. **State persists** - Your todo list and focus are saved when you run /session-end
3. **Identity matters** - Once fixed, each project will have its own Claude identity
4. **Everything is logged** - Sessions, agents, MCP calls (when working) all tracked
5. **Gaps are documented** - We know what's broken and how to fix it

**Bottom Line**: The session system works for tracking work and persisting state, but needs improvements in identity resolution, foreign key constraints, and MCP usage logging.

---

## Related Documents

- [[Session Lifecycle]] - Complete session flow (600+ lines)
- [[Session Quick Reference]] - Quick SQL queries and commands
- [[Database Schema - Core Tables]] - Detailed table documentation
- [[Identity System]] - Identity resolution design
- [[Session User Stories]] - 5 traced flows through the system
- [[Claude Family Postgres]] - Quick table reference
- [[Family Rules]] - Mandatory session procedures

---

**Version**: 1.0
**Created**: 2025-12-26
**Location**: knowledge-vault/Claude Family/Session Architecture.md
