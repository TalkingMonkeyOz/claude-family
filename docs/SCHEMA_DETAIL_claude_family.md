# Claude Family Schema - Detailed Architecture Document
**Version:** 1.0
**Last Updated:** 2025-12-01
**Owner:** claude-code-unified

---

## Overview

The `claude_family` schema contains infrastructure tables for managing Claude instances, sessions, knowledge, and coordination. This document describes each table at the field level with actual usage status.

---

## Table: `identities`

**Purpose:** Registry of all Claude instances/personas that can operate in the system.

**Usage Status:** ACTIVE - Queried on every session start

**Used By:**
- `session_startup_hook.py` - Identity detection
- Session logging
- Message sender identification

### Columns

| Column | Type | Nullable | Description | Actually Used? |
|--------|------|----------|-------------|----------------|
| `identity_id` | UUID | NO | Primary key | YES |
| `identity_name` | VARCHAR(100) | NO | Unique name (e.g., 'claude-code-unified') | YES - main identifier |
| `platform` | VARCHAR(50) | NO | Platform type (claude-code-console, desktop) | YES - for detection |
| `role_description` | TEXT | NO | What this identity does | YES - displayed |
| `capabilities` | JSONB | YES | Capability flags | NO - never populated |
| `personality_traits` | JSONB | YES | Personality config | NO - never populated |
| `learning_style` | JSONB | YES | Learning preferences | NO - never populated |
| `status` | VARCHAR(20) | YES | 'active', 'archived' | YES - filtering |
| `created_at` | TIMESTAMP | YES | Creation timestamp | RARELY |
| `last_active_at` | TIMESTAMP | YES | Last activity | YES - updated on session start |

### Indexes
- `identities_pkey` - Primary key on identity_id
- `identities_identity_name_key` - Unique on identity_name
- `idx_identities_platform` - For platform-based queries
- `idx_identities_status` - For filtering active identities

### Foreign Keys
- None (root table)

### Current Data
- 12 identities total
- 3 active: claude-code-unified, claude-desktop, claude-mcw
- 9 archived (legacy identities from earlier architecture)

### Recommended Changes
- DROP unused JSONB columns (capabilities, personality_traits, learning_style)
- Or populate them with actual data

---

## Table: `session_history`

**Purpose:** Log of all Claude sessions for tracking work done.

**Usage Status:** ACTIVE - Written every session start/end

**Used By:**
- `/session-start` command
- `/session-end` command
- MCW session dashboard (read)
- Context queries ("what did I do last time?")

### Columns

| Column | Type | Nullable | Description | Actually Used? |
|--------|------|----------|-------------|----------------|
| `session_id` | UUID | NO | Primary key | YES |
| `identity_id` | UUID | YES | FK to identities | YES |
| `project_schema` | VARCHAR(100) | YES | Schema being worked on | RARELY - often NULL |
| `project_name` | VARCHAR(100) | YES | Project name | YES - main filter |
| `session_start` | TIMESTAMP | YES | When session began | YES |
| `session_end` | TIMESTAMP | YES | When session ended | YES - NULL if open |
| `tasks_completed` | TEXT[] | YES | Array of completed tasks | SOMETIMES |
| `learnings_gained` | TEXT[] | YES | Array of learnings | RARELY |
| `challenges_encountered` | TEXT[] | YES | Array of challenges | RARELY |
| `session_summary` | TEXT | YES | Free-text summary | YES - main content |
| `session_metadata` | JSONB | YES | Extra data | RARELY |
| `created_at` | TIMESTAMP | YES | Creation timestamp | NO - redundant with session_start |

### Indexes
- `session_history_pkey` - Primary key
- `idx_session_history_identity` - For identity + time queries
- `idx_session_history_project` - For project-based queries
- `idx_session_history_recent` - For recent sessions

### Foreign Keys
- `identity_id` → `identities(identity_id)`

### Current Data
- 154 sessions logged
- Most have session_summary filled
- tasks_completed often NULL (should be populated more)

### Recommended Changes
- Rename to match CLAUDE.md documentation (or update docs)
- Add constraint: session_end > session_start when both present

---

## Table: `session_state`

**Purpose:** Store current session state for "where we left off" resume feature.

**Usage Status:** ACTIVE - Used by startup hook

**Used By:**
- `session_startup_hook.py` - Check for pending work
- `/session-start` - Display resume prompt

### Columns

| Column | Type | Nullable | Description | Actually Used? |
|--------|------|----------|-------------|----------------|
| `state_id` | UUID | NO | Primary key | YES |
| `identity_id` | UUID | NO | Which identity | YES |
| `project_name` | VARCHAR(100) | NO | Which project | YES |
| `state_data` | JSONB | NO | Current state (pending_tasks, context, etc.) | YES |
| `created_at` | TIMESTAMP | YES | When created | YES |
| `updated_at` | TIMESTAMP | YES | Last update | YES |
| `expires_at` | TIMESTAMP | YES | When to auto-clear | PLANNED but not enforced |

### Current Data
- Actively used for session resume

---

## Table: `shared_knowledge`

**Purpose:** Institutional knowledge base - patterns, troubleshooting, best practices.

**Usage Status:** ACTIVE - Written frequently, queried occasionally

**Used By:**
- Manual queries for context
- Should be queried by startup hook (not yet implemented)

### Columns

| Column | Type | Nullable | Description | Actually Used? |
|--------|------|----------|-------------|----------------|
| `knowledge_id` | UUID | NO | Primary key | YES |
| `learned_by_identity_id` | UUID | YES | Who learned this | RARELY - often NULL |
| `knowledge_type` | VARCHAR(50) | NO | Type of knowledge | YES but inconsistent |
| `knowledge_category` | VARCHAR(100) | YES | Category | YES but inconsistent |
| `title` | VARCHAR(200) | NO | Short title | YES |
| `description` | TEXT | NO | Full description | YES |
| `applies_to_projects` | TEXT[] | YES | Which projects | SOMETIMES |
| `applies_to_platforms` | TEXT[] | YES | Which platforms | RARELY |
| `confidence_level` | INTEGER | YES | 1-10 confidence | RARELY |
| `times_applied` | INTEGER | YES | Usage count | NO - never incremented |
| `times_failed` | INTEGER | YES | Failure count | NO - never incremented |
| `code_example` | TEXT | YES | Code snippet | SOMETIMES |
| `related_knowledge` | UUID[] | YES | Related entries | NO - never used |
| `created_at` | TIMESTAMP | YES | Creation time | YES |
| `updated_at` | TIMESTAMP | YES | Update time | YES |
| `last_applied_at` | TIMESTAMP | YES | Last use time | NO - never updated |

### Current Data
- 136 entries
- Inconsistent knowledge_type values (34 different values)
- Most learned_by_identity_id are NULL

### Recommended Changes
- Standardize knowledge_type to: pattern, troubleshooting, architecture, best-practice, reference, lesson-learned
- Add scope column (universal, domain, project, technology)
- Either use tracking columns (times_applied, etc.) or remove them

---

## Table: `instance_messages`

**Purpose:** Inter-Claude messaging system.

**Usage Status:** ACTIVE - Used by orchestrator MCP

**Used By:**
- Orchestrator MCP tools: check_inbox, send_message, broadcast
- `/inbox-check` command

### Columns

| Column | Type | Nullable | Description | Actually Used? |
|--------|------|----------|-------------|----------------|
| `message_id` | UUID | NO | Primary key | YES |
| `from_session_id` | UUID | YES | Sender session | SOMETIMES |
| `from_identity_id` | UUID | YES | Sender identity | SOMETIMES |
| `to_session_id` | UUID | YES | Recipient session | RARELY |
| `to_project` | VARCHAR(100) | YES | Target project | YES |
| `message_type` | VARCHAR(50) | NO | Type of message | YES |
| `subject` | VARCHAR(500) | YES | Message subject | YES |
| `body` | TEXT | NO | Message content | YES |
| `priority` | VARCHAR(20) | YES | urgent/normal/low | YES |
| `status` | VARCHAR(50) | YES | pending/read/acknowledged | YES |
| `read_at` | TIMESTAMP | YES | When read | YES |
| `acknowledged_at` | TIMESTAMP | YES | When acknowledged | SOMETIMES |
| `created_at` | TIMESTAMP | YES | Creation time | YES |
| `metadata` | JSONB | YES | Extra data | RARELY |

### Current Data
- 15 messages
- Actively used for coordination

### Note
- **DUPLICATE EXISTS** in claude_mission_control.instance_messages - needs consolidation

---

## Table: `ai_cron_jobs`

**Purpose:** Scheduled jobs/checks that should run periodically.

**Usage Status:** PARTIAL - Jobs defined but no scheduler running them

**Used By:**
- Manual execution
- Should be used by session_startup_hook.py (planned)

### Columns

| Column | Type | Nullable | Description | Actually Used? |
|--------|------|----------|-------------|----------------|
| `job_id` | UUID | NO | Primary key | YES |
| `project_id` | UUID | YES | Scoped to project | SOMETIMES |
| `job_name` | VARCHAR(200) | NO | Job name | YES |
| `job_description` | TEXT | YES | Description | YES |
| `job_type` | VARCHAR(50) | NO | audit/backup/sync/health_check | YES |
| `schedule` | VARCHAR(100) | YES | Human-readable schedule | YES |
| `last_run` | TIMESTAMP | YES | Last execution | YES |
| `last_status` | VARCHAR(50) | YES | SUCCESS/FAILED | YES |
| `last_output` | TEXT | YES | Output text | RARELY |
| `last_error` | TEXT | YES | Error message | RARELY |
| `next_run` | TIMESTAMP | YES | Planned next run | NOT ENFORCED |
| `run_count` | INTEGER | YES | Total runs | YES |
| `success_count` | INTEGER | YES | Successful runs | YES |
| `is_active` | BOOLEAN | YES | Enabled flag | YES |
| `timeout_seconds` | INTEGER | YES | Timeout | YES |
| `retry_on_failure` | BOOLEAN | YES | Auto-retry | YES |
| `max_retries` | INTEGER | YES | Retry limit | YES |
| `command` | TEXT | YES | Command to run | YES |
| `working_directory` | TEXT | YES | Working dir | YES |
| `created_at` | TIMESTAMP | YES | Creation time | YES |
| `created_by_identity_id` | UUID | YES | Creator | YES |
| `updated_at` | TIMESTAMP | YES | Update time | YES |
| `metadata` | JSONB | YES | Extra config | RARELY |

### Current Data
- 6 jobs defined
- Most have never run (last_run NULL)
- 3 have run once

### Recommended Changes
- Add trigger_type column (schedule, session_start, session_end, on_demand)
- Add trigger_condition JSONB for event-driven execution
- Create job_run_history table for execution tracking

---

## Table: `feature_backlog`

**Purpose:** Track feature ideas and enhancements.

**Usage Status:** ACTIVE - Used for planning

### Current Data
- 17 items
- Categories: orchestrator, plugin, hook, infrastructure, mcp-best-practices

### Note
- **POTENTIAL DUPLICATE** with claude_mission_control.features - needs analysis

---

## Table: `procedure_registry`

**Purpose:** Registry of all SOPs and procedures.

**Usage Status:** ACTIVE - Referenced for process compliance

### Current Data
- 18 procedures registered
- Includes session workflows, compliance checks

---

## Tables NOT Actively Used

| Table | Rows | Status | Recommendation |
|-------|------|--------|----------------|
| `api_cost_data` | 0 | Never used | DELETE or populate |
| `api_usage_data` | 0 | Never used | DELETE or populate |
| `cross_reference_log` | 0 | Never used | DELETE |
| `startup_context` | 0 | Never used | DELETE |
| `ui_test_results` | 0 | Never used | Repurpose for test_runs |
| `ui_test_screenshots` | 0 | Never used | DELETE or repurpose |
| `ui_test_scripts` | 0 | Never used | DELETE or repurpose |
| `usage_sync_status` | 0 | Never used | DELETE |
| `tool_evaluations` | ? | Unknown | Investigate |
| `budget_alerts` | ? | Unknown | Investigate |
| `mcp_configurations` | ? | Unknown | Investigate |
| `project_workspaces` | ? | Unknown | Investigate |

---

## MCP Configurations Used

### Orchestrator MCP (`mcp-servers/orchestrator/`)

**Tools Provided:**
1. `spawn_agent` - Spawn isolated Claude agent
2. `list_agent_types` - List available agents
3. `recommend_agent` - Suggest best agent for task
4. `check_inbox` - Check messages
5. `send_message` - Send message
6. `broadcast` - Broadcast to all
7. `acknowledge` - Mark message read
8. `get_active_sessions` - See who's online
9. `reply_to` - Reply to message

**Database Tables Used:**
- `claude_family.instance_messages` - Messaging
- `claude_family.identities` - Identity lookup (planned)
- Custom `agent_sessions` table in orchestrator (separate logging)

### Other MCPs Available
- `postgres` - Direct DB access
- `memory` - Knowledge graph (8 entities)
- `filesystem` - File operations
- `sequential-thinking` - Complex reasoning

---

## Hooks Configuration

**Session Start Hook:** `session_startup_hook.py`
- Detects identity from `identities` table
- Logs session to `session_history`
- Checks `session_state` for resume
- Should check `ai_cron_jobs` for due jobs (planned)

**Session End:** `/session-end` command
- Updates `session_history` with summary
- Clears `session_state`
- Should check inbox and broadcast status (planned)

---

## Summary: What Claude-Family Actually Uses

### Actively Used (Core)
- `identities` - Identity management
- `session_history` - Session tracking
- `session_state` - Resume feature
- `shared_knowledge` - Knowledge base
- `instance_messages` - Messaging
- `procedure_registry` - SOPs
- `feature_backlog` - Planning

### Partially Used
- `ai_cron_jobs` - Jobs defined but not scheduled

### Not Used (Candidates for Deletion)
- 8 tables with 0 rows, 0 bytes
- Several JSONB columns never populated

---

**Document Version:** 1.0
**Next Review:** After MCW analysis received
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/SCHEMA_DETAIL_claude_family.md
