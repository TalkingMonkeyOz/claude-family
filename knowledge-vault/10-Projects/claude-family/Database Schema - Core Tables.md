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

**Part of**: [[Database Schema - Overview]]

**Database**: `ai_company_foundation`
**Schema**: `claude`
**Focus**: Core session and identity tracking (3 tables)

This document provides detailed column-level documentation for the core session and identity tracking tables in the Claude Family database.

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

## Related Documents

See **[[Database Schema - Overview]]** for full navigation.

- [[Database Schema - Workspace and Agents]] - Next section
- [[Database Architecture]] - Overview of all 57 tables
- [[Session Lifecycle]] - Complete session flow

---

**Version**: 2.0 (split from Database Schema - Core Tables)
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: knowledge-vault/10-Projects/claude-family/Database Schema - Core Tables.md
