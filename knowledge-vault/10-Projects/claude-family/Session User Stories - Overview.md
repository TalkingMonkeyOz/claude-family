---
projects:
  - claude-family
tags:
  - user-stories
  - session
  - flows
  - validation
synced: false
---

# Session User Stories - Overview

**Purpose**: Traced paths through the system validating architecture documentation
**Related**: [[Session Lifecycle - Overview]], [[Database Schema - Core Tables]], [[Identity System - Overview]]

This document provides an overview of 5 key user stories through the Claude Family system, showing exactly what happens at each step, which files are involved, and what data is written to the database.

## 5 User Stories

### 1. [[Session User Story - Launch Project]]
**Actor**: John (developer)
**Goal**: Start working on ATO-tax-agent project
**Trigger**: Clicks "Launch" in Claude Family Manager WinForms launcher

Traces the complete flow from clicking launch in the WinForms UI through SessionStart hook firing, session creation, state loading, and Claude receiving context.

### 2. [[Session User Story - Spawn Agent]]
**Actor**: Claude (working on claude-family project)
**Goal**: Spawn doc-keeper-haiku agent to audit documentation
**Trigger**: User request or proactive skill invocation

Traces agent spawning through the orchestrator MCP server, agent execution, database logging, and result return to Claude.

### 3. [[Session User Story - End Session]]
**Actor**: John (developer)
**Goal**: Save session state and summary before closing Claude
**Trigger**: User runs `/session-end` slash command

Traces session termination, summary generation, database updates, state preservation, and knowledge capture.

### 4. [[Session User Story - Resume Session]]
**Actor**: John (developer)
**Goal**: Continue working on ATO-tax-agent project from previous day
**Trigger**: User launches Claude next day, runs `/session-resume`

Traces resuming a session the next day, including state restoration, recent session history, pending messages, and memory graph queries.

### 5. [[Session User Story - Cross-Project Message]]
**Actor**: Claude (claude-family project)
**Goal**: Send task request to ATO-tax-agent project
**Trigger**: Need to coordinate work across projects

Traces cross-project messaging, message persistence, retrieval at session start, acknowledgment, and reply handling.

---

## Validation Summary

These 5 user stories validate the following architecture components:

### ✅ Validated Components

| Component | User Stories | Tables Used |
|-----------|--------------|-------------|
| Session lifecycle | 1, 3, 4 | sessions, session_state |
| Identity resolution | 1 | sessions, identities |
| Agent spawning | 2 | agent_sessions |
| State persistence | 3, 4 | session_state |
| Message routing | 5 | messages |
| Hook system | 1, 3, 4, 5 | All tables |
| MCP integration | 2, 3, 4, 5 | All tables |
| Knowledge capture | 3, 4 | Memory graph |

---

### ⚠️ Gaps Identified

| Gap | Affected Stories | Impact |
|-----|------------------|--------|
| CLAUDE_SESSION_ID not exported | 1, 2, 3 | MCP usage logging broken |
| parent_session_id missing | 2 | Agent sessions orphaned |
| Identity hardcoded | 1 | All sessions appear as same identity |
| No FK constraints | All | Data integrity risks |
| Launcher doesn't set identity | 1 | Identity resolution incomplete |

---

### 🔗 Cross-References

Each user story uses multiple documents:

| Story | References |
|-------|-----------|
| 1. Launch Claude | [[Session Lifecycle - Overview]], [[Identity System - Overview]], [[Database Schema - Core Tables]] |
| 2. Spawn Agent | [[Database Schema - Core Tables]] (agent_sessions table) |
| 3. End Session | [[Session Lifecycle - Overview]], [[Database Schema - Core Tables]] (sessions, session_state) |
| 4. Resume Session | [[Session Lifecycle - Overview]], [[Database Schema - Core Tables]] (all core tables) |
| 5. Cross-Project Message | [[Database Schema - Core Tables]] (messages table) |

---

## Testing These Flows

To validate these user stories work correctly:

### Test 1: Launch and Resume
```bash
# 1. Launch Claude on project
cd C:\Projects\ATO-Tax-Agent
claude

# 2. Do some work, run /session-end
# 3. Exit Claude
# 4. Launch again next day
# 5. Run /session-resume

# Expected: Context restored, todos preserved
```

### Test 2: Agent Spawn
```sql
-- Before spawning agent
SELECT COUNT(*) FROM claude.agent_sessions;  -- Note count

-- Spawn agent via MCP
-- After agent completes

SELECT COUNT(*) FROM claude.agent_sessions;  -- Should be +1
SELECT * FROM claude.agent_sessions ORDER BY created_at DESC LIMIT 1;
-- Expected: New record with success=true, result populated
```

### Test 3: Cross-Project Messaging
```sql
-- Claude 1 sends message to Project A

-- Check message created
SELECT * FROM claude.messages WHERE to_project = 'ProjectA' AND status = 'pending';

-- Launch Claude on Project A
-- Expected: Message appears in session context

-- Claude 2 marks as read
SELECT status, read_at FROM claude.messages WHERE message_id = '...';
-- Expected: status=read, read_at populated

-- Claude 2 sends reply
SELECT * FROM claude.messages WHERE in_reply_to = '...' AND to_project = 'OriginalProject';
-- Expected: Reply message exists
```

---

## Related Documents

- [[Session Lifecycle - Overview]] - Complete session flow documentation
- [[Database Schema - Core Tables]] - Detailed table schemas
- [[Identity System - Overview]] - Identity resolution design
- [[Family Rules]] - Coordination procedures
- [[Session Quick Reference]] - Quick reference for session operations

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Session User Stories - Overview.md
