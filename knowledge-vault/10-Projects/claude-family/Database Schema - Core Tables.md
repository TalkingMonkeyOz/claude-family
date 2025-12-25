---
projects:
  - claude-family
tags:
  - database
  - schema
  - reference
  - core-tables
synced: false
---

# Database Schema - Core Tables

**Database**: `ai_company_foundation`
**Schema**: `claude` (57 tables total)
**Core Tables**: 7 (session/identity tracking)

This document provides detailed column-level documentation for the core session and identity tracking tables in the Claude Family database.

---

## Overview

The Claude Family uses PostgreSQL to track sessions, identities, projects, and coordination across multiple Claude instances. This document covers the 7 **core tables** that form the foundation of session tracking.

### Core Tables

| Table | Purpose | Records | Key Columns |
|-------|---------|---------|-------------|
| **sessions** | Session logging | 395 | session_id, identity_id, project_name |
| **identities** | Claude identity registry | 12 | identity_id, identity_name, platform |
| **projects** | Project registry | 20 | project_id, project_name, phase |
| **workspaces** | Launcher workspaces | 10 | id, project_name, project_path |
| **agent_sessions** | Spawned agent tracking | 144 | session_id, agent_type, success |
| **mcp_usage** | MCP tool call tracking | 13 | usage_id, session_id, tool_name |
| **session_state** | Cross-session state | varies | project_name, todo_list, current_focus |

---

## Table Relationships (Current State)

**Critical Finding**: Only `mcp_usage` has proper foreign key constraints. All other relationships are enforced by application logic only, leading to data integrity issues.

```
┌─────────────┐
│ identities  │
│ (12 rows)   │
└──────┬──────┘
       │
       │ ⚠️  NO FK!
       │
┌──────▼──────┐      ⚠️  NO FK!      ┌──────────────┐
│  sessions   │◄────────────────────│   projects   │
│ (395 rows)  │  project_name only  │  (20 rows)   │
└──────┬──────┘                     └──────────────┘
       │
       │ ✅ HAS FK!
       │
┌──────▼──────┐
│  mcp_usage  │
│  (13 rows)  │
└─────────────┘

┌──────────────┐     ⚠️  NO FK!
│agent_sessions│  (no parent link)
│  (144 rows)  │
└──────────────┘

┌──────────────┐
│session_state │  (singleton per project)
│              │
└──────────────┘

┌──────────────┐     ⚠️  NO FK!
│ workspaces   │  added_by_identity_id
│  (10 rows)   │
└──────────────┘
```

---

## 1. claude.sessions

**Purpose**: Tracks every Claude Code session from start to end.

### Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| session_id | uuid | NO | - | Primary key, unique session identifier |
| identity_id | uuid | YES | - | ⚠️ Which Claude instance (NO FK to identities) |
| project_schema | varchar | YES | - | Legacy field (deprecated) |
| project_name | varchar | YES | - | ⚠️ Project name (NO FK to projects) |
| session_start | timestamp | YES | - | When session began |
| session_end | timestamp | YES | - | When session ended (NULL if active) |
| tasks_completed | text[] | YES | - | Array of completed tasks |
| learnings_gained | text[] | YES | - | Array of insights |
| challenges_encountered | text[] | YES | - | Array of problems faced |
| session_summary | text | YES | - | Generated summary at session end |
| session_metadata | jsonb | YES | - | Additional metadata |
| created_at | timestamp | YES | - | Record creation time |

### Constraints

- **Primary Key**: `session_id`
- **Check**: `sessions_session_id_not_null`
- **Missing FK**: `identity_id` → `identities.identity_id` ⚠️
- **Missing FK**: Should have `project_id` → `projects.project_id` ⚠️

### Indexes

- `sessions_pkey` on `session_id` (unique)
- **Missing**: Index on `identity_id` (slow lookups) ⚠️
- **Missing**: Index on `project_name` (frequent filter) ⚠️
- **Missing**: Index on `session_start DESC` (ordering) ⚠️

### Data Quality Issues

| Issue | Count | Percentage |
|-------|-------|------------|
| NULL `identity_id` | 39/395 | 10% |
| NULL `session_summary` | 164/395 | 41.5% |
| NULL `tasks_completed` | 186/395 | 47% |
| NULL `session_end` (stale) | 2 | 0.5% |

### Example Queries

```sql
-- Recent sessions for a project
SELECT session_id::text, session_start, session_summary
FROM claude.sessions
WHERE project_name = 'claude-family'
ORDER BY session_start DESC
LIMIT 5;

-- Active sessions (currently running)
SELECT session_id::text, project_name, session_start,
       AGE(NOW(), session_start) as duration
FROM claude.sessions
WHERE session_end IS NULL
  AND session_start >= NOW() - INTERVAL '24 hours';

-- Sessions by identity
SELECT i.identity_name, COUNT(*) as session_count
FROM claude.sessions s
LEFT JOIN claude.identities i ON s.identity_id = i.identity_id
GROUP BY i.identity_name
ORDER BY session_count DESC;
```

---

## 2. claude.identities

**Purpose**: Registry of all Claude instances (CLI, Desktop, Cursor, etc.)

### Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| identity_id | uuid | NO | - | Primary key |
| identity_name | varchar | YES | - | Human-readable name (e.g., 'claude-code-unified') |
| platform | varchar | YES | - | Platform type (claude-code-console, desktop, cursor) |
| role_description | text | YES | - | Description of role |
| capabilities | jsonb | YES | - | Capabilities metadata |
| personality_traits | jsonb | YES | - | Personality attributes |
| learning_style | jsonb | YES | - | Learning preferences |
| status | varchar | YES | - | active or archived (CHECK constraint) |
| created_at | timestamp | YES | - | When identity was created |
| last_active_at | timestamp | YES | - | Last activity timestamp |

### Constraints

- **Primary Key**: `identity_id`
- **Check**: `identities_identity_id_not_null`
- **Check**: `chk_identities_status` (active, archived)
- **Missing**: UNIQUE constraint on `identity_name` ⚠️

### Indexes

- `identities_pkey` on `identity_id` (unique)
- **Missing**: Index on `identity_name` (lookups) ⚠️
- **Missing**: Index on `status` (filtering) ⚠️
- **Missing**: Index on `platform` (grouping) ⚠️

### Current Identities

```sql
SELECT identity_name, platform, status, last_active_at
FROM claude.identities
ORDER BY last_active_at DESC NULLS LAST;
```

Results:
- **claude-code-unified** (active) - Primary CLI identity
- **claude-desktop** (active) - Desktop app
- **claude-mcw** (archived)
- 9 other archived identities

### Example Queries

```sql
-- Active identities
SELECT identity_name, platform
FROM claude.identities
WHERE status = 'active';

-- Update last active
UPDATE claude.identities
SET last_active_at = NOW()
WHERE identity_id = 'YOUR-IDENTITY-ID'::uuid;
```

---

## 3. claude.projects

**Purpose**: Central project registry with lifecycle tracking.

### Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| project_id | uuid | NO | - | Primary key |
| program_id | uuid | YES | - | Parent program (NO FK) |
| project_name | varchar | YES | - | Human-readable name |
| project_code | varchar | YES | - | Short code |
| description | text | YES | - | Project description |
| status | varchar | YES | - | active, paused, archived, completed |
| priority | integer | YES | - | 1-5 (1=critical, CHECK constraint) |
| start_date | date | YES | - | Project start |
| target_date | date | YES | - | Target completion |
| completion_date | date | YES | - | Actual completion |
| owner_session | varchar | YES | - | ⚠️ Always NULL (unused) |
| created_at | timestamp | YES | - | Record creation |
| updated_at | timestamp | YES | - | Last update |
| metadata | jsonb | YES | - | Additional data |
| last_audit_date | timestamp | YES | - | Last audit |
| next_audit_due | timestamp | YES | - | Next audit scheduled |
| health_status | varchar | YES | - | Project health |
| maturity_level | varchar | YES | - | Maturity rating |
| audit_required | boolean | YES | - | Audit flag |
| audit_reason | text | YES | - | Why audit needed |
| code_lines | integer | YES | - | LOC count |
| documentation_score | integer | YES | - | Doc quality 0-100 |
| test_coverage | integer | YES | - | Test coverage % |
| tech_debt_score | integer | YES | - | Tech debt rating |
| is_archived | boolean | YES | false | Archive flag |
| archived_at | timestamp | YES | - | When archived |
| archive_reason | text | YES | - | Why archived |
| phase | varchar | YES | 'planning' | Lifecycle phase (CHECK constraint) |

### Constraints

- **Primary Key**: `project_id`
- **Check**: `chk_projects_priority` (1-5)
- **Check**: `chk_projects_phase` (planning, implementation, maintenance, etc.)
- **Missing**: UNIQUE on `project_name` ⚠️

### Indexes

- `projects_pkey` on `project_id` (unique)
- **Missing**: Index on `project_name` (frequent lookups) ⚠️
- **Missing**: Index on `status` (filtering) ⚠️

### Phase Values (from column_registry)

```
idea → research → planning → implementation → maintenance → archived
```

### Example Queries

```sql
-- Active projects
SELECT project_name, phase, status, updated_at
FROM claude.projects
WHERE status = 'active'
ORDER BY updated_at DESC;

-- Projects by phase
SELECT phase, COUNT(*) as count
FROM claude.projects
WHERE status = 'active'
GROUP BY phase;
```

---

## 4. claude.workspaces

**Purpose**: Workspace configurations for the launcher application.

### Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| id | integer | NO | - | ⚠️ Primary key (should be UUID) |
| project_name | varchar | YES | - | Project name (NO FK to projects) |
| project_path | text | YES | - | File system path |
| project_type | varchar | YES | - | Type (csharp-winforms, nextjs, etc.) |
| is_active | boolean | YES | - | Active flag |
| description | text | YES | - | Description |
| added_by_identity_id | uuid | YES | - | ⚠️ NO FK to identities |
| added_at | timestamp | YES | - | When added |
| updated_at | timestamp | YES | - | Last update |
| mandatory_workflows | text[] | YES | - | Required workflows |
| startup_config | jsonb | YES | - | Startup configuration |

### Constraints

- **Primary Key**: `id` (integer)
- **Issue**: Uses integer PK instead of UUID (inconsistent with other tables) ⚠️

### Indexes

- `workspaces_pkey` on `id` (unique)
- **Missing**: Index on `project_name` ⚠️
- **Missing**: Index on `is_active` ⚠️

### Example Queries

```sql
-- Active workspaces
SELECT id, project_name, project_path, project_type
FROM claude.workspaces
WHERE is_active = true
ORDER BY project_name;

-- Workspaces by type
SELECT project_type, COUNT(*) as count
FROM claude.workspaces
WHERE is_active = true
GROUP BY project_type;
```

---

## 5. claude.agent_sessions

**Purpose**: Tracks spawned agent executions (via orchestrator MCP).

### Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| session_id | uuid | NO | gen_random_uuid() | Primary key |
| agent_type | varchar | NO | - | Agent type (coder-haiku, reviewer-sonnet, etc.) |
| task_description | text | NO | - | Task given to agent |
| workspace_dir | varchar | NO | - | Working directory |
| spawned_at | timestamp | NO | CURRENT_TIMESTAMP | When spawned |
| completed_at | timestamp | YES | - | When completed |
| execution_time_seconds | numeric | YES | - | Duration |
| success | boolean | YES | - | Success flag |
| output_text | text | YES | - | Agent output |
| error_message | text | YES | - | Error if failed |
| stderr_text | text | YES | - | Stderr output |
| estimated_cost_usd | numeric | YES | - | Estimated cost |
| model | varchar | YES | - | Claude model used |
| mcp_servers | jsonb | YES | - | MCP servers available |
| metadata | jsonb | YES | - | ⚠️ Always NULL (parent_session_id should be here) |
| created_by | varchar | YES | 'claude-code-unified' | Created by (string, not FK) |

### Constraints

- **Primary Key**: `session_id`
- **Check**: NOT NULL on key fields (agent_type, task_description, workspace_dir, spawned_at)
- **Missing**: No link to parent session! ⚠️

### Indexes

- `agent_sessions_pkey` on `session_id` (unique)
- `idx_agent_sessions_type` on `agent_type`
- `idx_agent_sessions_spawned` on `spawned_at DESC`
- `idx_agent_sessions_success` on `success`

### Example Queries

```sql
-- Recent agent runs
SELECT agent_type, task_description, spawned_at, success
FROM claude.agent_sessions
ORDER BY spawned_at DESC
LIMIT 10;

-- Agent success rates
SELECT agent_type,
       COUNT(*) as total,
       COUNT(*) FILTER (WHERE success = true) as successful,
       ROUND(100.0 * COUNT(*) FILTER (WHERE success = true) / COUNT(*), 1) as success_rate
FROM claude.agent_sessions
GROUP BY agent_type
ORDER BY total DESC;

-- Average cost by agent
SELECT agent_type,
       ROUND(AVG(estimated_cost_usd), 4) as avg_cost_usd,
       ROUND(AVG(execution_time_seconds), 2) as avg_time_sec
FROM claude.agent_sessions
WHERE estimated_cost_usd IS NOT NULL
GROUP BY agent_type
ORDER BY avg_cost_usd DESC;
```

---

## 6. claude.mcp_usage

**Purpose**: Tracks every MCP tool call for analytics.

**Note**: This is the ONLY table with proper foreign key constraints! ✅

### Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| usage_id | uuid | NO | gen_random_uuid() | Primary key |
| session_id | uuid | YES | - | ✅ FK to sessions |
| mcp_server | varchar | NO | - | Server name (postgres, orchestrator, etc.) |
| tool_name | varchar | NO | - | Tool name (execute_sql, spawn_agent, etc.) |
| called_at | timestamp | NO | CURRENT_TIMESTAMP | When called |
| execution_time_ms | integer | YES | - | Execution time |
| success | boolean | YES | true | Success flag |
| error_message | text | YES | - | Error if failed |
| input_size_bytes | integer | YES | - | Input size |
| output_size_bytes | integer | YES | - | Output size |
| identity_id | uuid | YES | - | ✅ FK to identities |
| project_name | varchar | YES | - | Project name (string, not FK) |

### Constraints

- **Primary Key**: `usage_id`
- **Foreign Key**: `session_id` → `sessions.session_id` ✅
- **Foreign Key**: `identity_id` → `identities.identity_id` ✅

### Indexes

- `mcp_usage_pkey` on `usage_id` (unique)
- `idx_mcp_usage_server` on `mcp_server`
- `idx_mcp_usage_tool` on `tool_name`
- `idx_mcp_usage_called` on `called_at DESC`
- `idx_mcp_usage_session` on `session_id`

### Example Queries

```sql
-- Most called MCP tools
SELECT mcp_server, tool_name, COUNT(*) as call_count
FROM claude.mcp_usage
GROUP BY mcp_server, tool_name
ORDER BY call_count DESC
LIMIT 10;

-- MCP usage by session
SELECT s.project_name,
       COUNT(*) as mcp_calls,
       AVG(m.execution_time_ms) as avg_time_ms
FROM claude.mcp_usage m
JOIN claude.sessions s ON m.session_id = s.session_id
GROUP BY s.project_name
ORDER BY mcp_calls DESC;
```

---

## 7. claude.session_state

**Purpose**: Persist state across sessions (singleton per project).

### Columns

| Column | Type | Nullable | Default | Purpose |
|--------|------|----------|---------|---------|
| project_name | varchar | NO | - | Primary key (singleton per project) |
| todo_list | jsonb | YES | - | TodoWrite state |
| current_focus | text | YES | - | What working on |
| files_modified | text[] | YES | - | Modified files |
| pending_actions | text[] | YES | - | Actions to take |
| updated_at | timestamp | YES | now() | Last update |
| next_steps | jsonb | YES | '[]' | Next steps array |

### Constraints

- **Primary Key**: `project_name`
- **Note**: Singleton per project (only 1 row per project)

### Indexes

- `session_state_pkey` on `project_name` (unique)

### Example Queries

```sql
-- Get saved state for project
SELECT todo_list, current_focus, next_steps
FROM claude.session_state
WHERE project_name = 'claude-family';

-- Update state
INSERT INTO claude.session_state (project_name, todo_list, current_focus, updated_at)
VALUES ('claude-family', '{"items": []}', 'Working on docs', NOW())
ON CONFLICT (project_name)
DO UPDATE SET
    todo_list = EXCLUDED.todo_list,
    current_focus = EXCLUDED.current_focus,
    updated_at = NOW();
```

---

## Supporting Tables (Summary)

These 50+ tables support the core functionality. Grouped by domain:

### Work Items (8 tables)
| Table | Purpose |
|-------|---------|
| build_tasks | Development tasks |
| work_tasks | General work items |
| pm_tasks | Project management tasks |
| features | Feature registry |
| feedback | Issue/feedback tracking |
| feedback_comments | Comments on feedback |
| feedback_screenshots | Screenshot attachments |
| ideas | Idea capture |

### Process Workflow (8 tables)
| Table | Purpose |
|-------|---------|
| process_registry | Workflow definitions |
| process_steps | Steps within processes |
| process_triggers | Keyword triggers |
| process_runs | Execution history |
| process_dependencies | Process interconnections |
| process_classification_log | Router decisions |
| workflow_state | Active workflow state |
| procedures | Legacy procedures |

### Governance (8 tables)
| Table | Purpose |
|-------|---------|
| column_registry | Valid values for columns |
| schema_registry | Schema documentation |
| enforcement_log | Reminder/enforcement tracking |
| compliance_audits | Audit results |
| audit_schedule | Audit scheduling |
| reviewer_runs | Auto-reviewer executions |
| reviewer_specs | Reviewer configurations |
| test_runs | Test execution results |

### Knowledge (5 tables)
| Table | Purpose |
|-------|---------|
| knowledge | Synced from Obsidian vault |
| knowledge_retrieval_log | Query tracking |
| documents | Document registry |
| doc_templates | Document templates |
| document_projects | Doc-project links |

### MCP Orchestration (5 tables)
| Table | Purpose |
|-------|---------|
| mcp_configs | MCP server configurations |
| messages | Inter-Claude messaging |
| async_tasks | Async agent tracking |
| actions | Shared actions for MCW |
| config_deployment_log | Config deployment history |

### Scheduling (3 tables)
| Table | Purpose |
|-------|---------|
| scheduled_jobs | Cron-like job definitions |
| job_run_history | Job execution history |
| reminders | Session reminders |

### Project Management (5 tables)
| Table | Purpose |
|-------|---------|
| programs | Program groupings |
| phases | Project phases |
| requirements | Project requirements |
| project_docs | Document metadata |
| project_command_assignments | Command assignments |
| project_config_assignments | Config assignments |

### Configuration (3 tables)
| Table | Purpose |
|-------|---------|
| config_templates | Config template definitions |
| shared_commands | Shared slash commands |
| components | UI/system components |

### Other (5 tables)
| Table | Purpose |
|-------|---------|
| architecture_decisions | ADR tracking |
| activity_feed | Activity stream |
| capability_usage | Feature usage tracking |
| feature_usage | Feature toggle tracking |

---

## Critical Issues Summary

### Missing Foreign Keys

| Table | Column | Should Reference | Impact |
|-------|--------|------------------|--------|
| sessions | identity_id | identities.identity_id | 10% NULL values, no referential integrity |
| sessions | project_name | projects.project_id | String matching, name variants, no cascade |
| workspaces | added_by_identity_id | identities.identity_id | Can't track who added workspace |
| agent_sessions | metadata | Should have parent_session_id | All 144 agent sessions orphaned |

### Missing Indexes

| Table | Column | Usage | Impact |
|-------|--------|-------|--------|
| sessions | identity_id | Frequent joins | Slow queries |
| sessions | project_name | Frequent filters | Table scans |
| sessions | session_start | Ordering | Slow sorts |
| identities | identity_name | Lookups | No benefit from index |
| projects | project_name | Frequent lookups | Table scans |

### Data Quality Issues

- **39 sessions** (10%) have NULL identity_id
- **164 sessions** (41.5%) missing session_summary
- **2 sessions** still marked active from Dec 21 (stale)
- **144 agent sessions** have no parent link
- **Project names** have variants: "ATO-Tax-Agent" vs "ato-tax-agent"

---

## Recommended Schema Fixes

**Note**: These are documented for future implementation, not implemented yet.

### Priority 1: Add Foreign Keys

```sql
-- Sessions to identities
ALTER TABLE claude.sessions
ADD CONSTRAINT sessions_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude.identities(identity_id);

-- Workspaces to identities
ALTER TABLE claude.workspaces
ADD CONSTRAINT workspaces_identity_fkey
FOREIGN KEY (added_by_identity_id) REFERENCES claude.identities(identity_id);
```

### Priority 2: Add Missing Indexes

```sql
CREATE INDEX idx_sessions_identity ON claude.sessions(identity_id);
CREATE INDEX idx_sessions_project ON claude.sessions(project_name);
CREATE INDEX idx_sessions_start ON claude.sessions(session_start DESC);
CREATE INDEX idx_identities_name ON claude.identities(identity_name);
CREATE INDEX idx_projects_name ON claude.projects(project_name);
```

### Priority 3: Add parent_session_id to agent_sessions

```sql
ALTER TABLE claude.agent_sessions
ADD COLUMN parent_session_id uuid;

ALTER TABLE claude.agent_sessions
ADD CONSTRAINT agent_sessions_parent_fkey
FOREIGN KEY (parent_session_id) REFERENCES claude.sessions(session_id);

CREATE INDEX idx_agent_sessions_parent ON claude.agent_sessions(parent_session_id);
```

---

## Related Documents

- [[Database Architecture]] - Overview of all 57 tables
- [[Identity System]] - How identity per project should work
- [[Session Lifecycle]] - Complete session flow
- [[Family Rules]] - Database usage rules
- [[Claude Hooks]] - Enforcement layer

---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Database Schema - Core Tables.md
