---
projects:
  - claude-family
tags:
  - database
  - schema
  - reference
  - workspace
  - agents
synced: false
---

# Database Schema - Workspace and Agents

**Part of**: [[Database Schema - Overview]]

**Database**: `ai_company_foundation`
**Schema**: `claude`
**Focus**: Workspace configurations and agent execution tracking (4 tables)

This document covers workspace configurations, spawned agent tracking, MCP tool usage analytics, and cross-session state persistence.

---

## 1. claude.workspaces

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

## 2. claude.agent_sessions

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

## 3. claude.mcp_usage

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

## 4. claude.session_state

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

## 5-7. Agent Coordination Tables (NEW)

**Implemented**: 2026-01-06

Three new tables support the Agent Coordination System:

| Table | Purpose | Details |
|-------|---------|---------|
| `claude.context_rules` | DB-driven coding standard injection | 8 seed rules, matches by task/pattern/agent |
| `claude.agent_status` | Real-time agent status tracking | Status, progress, discoveries |
| `claude.agent_commands` | Boss→agent control commands | ABORT, REDIRECT, INJECT, PAUSE, RESUME |

**Full documentation**: See [[Orchestrator MCP#Agent Coordination System]]

---

## Data Quality Summary

### agent_sessions Issues ⚠️
- **144 agent sessions** have no parent link to main session
- **metadata column** unused (always NULL)
- No way to correlate agent runs with parent session

### workspaces Issues ⚠️
- Uses **integer PK** instead of UUID (inconsistent)
- No FK to projects (project_name is string)
- No FK to identities (added_by_identity_id not constrained)

### mcp_usage Strengths ✅
- Proper foreign keys to sessions and identities
- Good indexes for common queries
- Reliable for analytics

---

## Related Documents

See **[[Database Schema - Overview]]** for full navigation.

- [[Database Schema - Core Tables]] - Previous section
- [[Database Schema - Supporting Tables]] - Next section
- [[Database Architecture]] - Overview of all 57 tables

---

**Version**: 3.0 (Added Agent Coordination tables: context_rules, agent_status, agent_commands)
**Created**: 2025-12-26
**Updated**: 2026-01-06
**Location**: knowledge-vault/10-Projects/claude-family/Database Schema - Workspace and Agents.md
