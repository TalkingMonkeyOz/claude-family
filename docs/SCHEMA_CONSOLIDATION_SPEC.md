# Schema Consolidation Specification
**Version:** 1.0
**Date:** 2025-12-01
**Status:** APPROVED FOR IMPLEMENTATION
**Assigned To:** claude-mcw

---

## Executive Summary

Consolidate 4 overlapping schemas (`claude_family`, `claude_pm`, `claude_mission_control`, `public`) into ONE schema: **`claude`**.

**Reason:** Current split causes confusion, duplicates, and "where does this go?" problems. One schema with strong documentation discipline is simpler.

---

## Decision: ONE SCHEMA

**Schema Name:** `claude`

**Safeguards:**
1. `schema_registry` table documents every table
2. `architecture_decisions` table records WHY
3. Clear, descriptive table names (no abbreviations)
4. No table creation without documentation

---

## Part 1: Tables to KEEP (Move to `claude` schema)

### From `claude_family` (Infrastructure)

| Current Table | New Name | Purpose | Rows |
|---------------|----------|---------|------|
| `identities` | `identities` | Claude instance registry | 12 |
| `session_history` | `sessions` | Session logs | 154 |
| `session_state` | `session_state` | Resume feature | ~5 |
| `shared_knowledge` | `knowledge` | Knowledge base | 136 |
| `instance_messages` | `messages` | Inter-Claude messaging | 15 |
| `procedure_registry` | `procedures` | SOPs/procedures | 18 |
| `ai_cron_jobs` | `scheduled_jobs` | Scheduled tasks | 6 |
| `project_workspaces` | `workspaces` | Project registry | 7 |
| `mcp_configurations` | `mcp_configs` | MCP tracking | 6 |

### From `claude_pm` (Project Management)

| Current Table | New Name | Purpose | Rows |
|---------------|----------|---------|------|
| `projects` | `projects` | Project registry | 20 |
| `programs` | `programs` | Program groupings | ? |
| `phases` | `phases` | Project phases | ? |
| `tasks` | `pm_tasks` | PM tasks (rename to avoid collision) | 11 |
| `project_feedback` | `feedback` | Feedback/issues | 36 |
| `feedback_conversations` | `feedback_comments` | Comments | ? |
| `feedback_screenshots` | `feedback_screenshots` | Screenshots | ? |
| `project_documents` | `project_docs` | Project docs | ? |
| `project_ideas` | `ideas` | Ideas backlog | ? |
| `document_templates` | `doc_templates` | Templates | ? |

### From `claude_mission_control` (Build Tracking)

| Current Table | New Name | Purpose | Rows |
|---------------|----------|---------|------|
| `features` | `features` | Feature tracking | 34 |
| `components` | `components` | Component tracking | 102 |
| `requirements` | `requirements` | Requirements | 109 |
| `build_tasks` | `build_tasks` | Build tasks | 145 |
| `work_tasks` | `work_tasks` | Work tasks | ? |
| `documents` | `documents` | Documents | ? |

---

## Part 2: Tables to DELETE

### Duplicates (Keep ONE, Delete Other)

| Delete | Keep Instead | Reason |
|--------|--------------|--------|
| `claude_mission_control.instance_messages` | `claude_family.instance_messages` | Duplicate, MCW doesn't use it |
| `claude_family.feature_backlog` | `claude_mission_control.features` | Same purpose, features has more data |

### Empty Tables (0 rows, never used)

| Schema | Table | Action |
|--------|-------|--------|
| `claude_family` | `api_cost_data` | DELETE |
| `claude_family` | `api_usage_data` | DELETE |
| `claude_family` | `cross_reference_log` | DELETE |
| `claude_family` | `startup_context` | DELETE |
| `claude_family` | `ui_test_results` | DELETE |
| `claude_family` | `ui_test_screenshots` | DELETE |
| `claude_family` | `ui_test_scripts` | DELETE |
| `claude_family` | `usage_sync_status` | DELETE |
| `claude_mission_control` | `app_settings` | DELETE |
| `claude_mission_control` | `audit_log` | DELETE (we'll create activity_feed) |
| `claude_mission_control` | `implementation_verification` | DELETE |
| `claude_mission_control` | `instance_health` | DELETE |
| `claude_mission_control` | `plan_documents` | DELETE |

### Legacy Tables (Diana era, stale)

| Schema | Table | Action |
|--------|-------|--------|
| `public` | `sops` | DELETE (replaced by procedure_registry) |
| `public` | `backup_*` | DELETE (old backups) |
| `public` | `programs` | DELETE (duplicate) |
| `public` | `phases` | DELETE (duplicate) |
| `public` | `projects` | DELETE (duplicate) |
| `public` | `work_packages` | DELETE or migrate |

---

## Part 3: NEW Tables to Create

### `schema_registry` - Document Every Table

```sql
CREATE TABLE claude.schema_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL UNIQUE,
    purpose TEXT NOT NULL,
    owner VARCHAR(100), -- Which Claude/system owns this
    category VARCHAR(50), -- 'infrastructure', 'app', 'testing', 'reference'
    used_by TEXT[], -- ['mcw', 'orchestrator', 'hooks']
    row_count_approx INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    last_reviewed DATE,
    notes TEXT
);
```

### `architecture_decisions` - ADRs

```sql
CREATE TABLE claude.architecture_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    adr_number SERIAL UNIQUE, -- ADR-001, ADR-002
    title VARCHAR(200) NOT NULL,
    status VARCHAR(50) DEFAULT 'accepted', -- proposed, accepted, deprecated
    context TEXT NOT NULL, -- Problem being solved
    decision TEXT NOT NULL, -- What we decided
    consequences TEXT, -- Trade-offs
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100)
);
```

### `activity_feed` - Unified Activity Log

```sql
CREATE TABLE claude.activity_feed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL, -- 'session', 'message', 'job', 'test', 'feedback'
    source_id UUID,
    actor VARCHAR(100), -- Identity name
    activity_type VARCHAR(100) NOT NULL, -- 'session_started', 'test_completed', etc.
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    project_name VARCHAR(100),
    severity VARCHAR(20) DEFAULT 'info', -- 'info', 'warning', 'error', 'success'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_activity_feed_time ON claude.activity_feed(created_at DESC);
CREATE INDEX idx_activity_feed_project ON claude.activity_feed(project_name, created_at DESC);
```

### `test_runs` - Test History

```sql
CREATE TABLE claude.test_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(100) NOT NULL,
    test_type VARCHAR(50) NOT NULL, -- 'e2e', 'unit', 'integration'
    test_framework VARCHAR(50), -- 'playwright', 'pytest', 'jest'

    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,

    total_tests INTEGER,
    passed INTEGER,
    failed INTEGER,
    skipped INTEGER,
    pass_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE WHEN total_tests > 0 THEN (passed::decimal / total_tests) * 100 ELSE 0 END
    ) STORED,

    git_branch VARCHAR(200),
    git_commit VARCHAR(40),

    failed_tests JSONB, -- [{name, error, file}]
    duration_seconds DECIMAL(10,2),

    triggered_by VARCHAR(100), -- 'manual', 'ci', 'agent'
    session_id UUID,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_test_runs_project ON claude.test_runs(project_name, started_at DESC);
```

### `job_run_history` - Scheduled Job Executions

```sql
CREATE TABLE claude.job_run_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES claude.scheduled_jobs(job_id),

    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    triggered_by VARCHAR(50), -- 'session_start', 'manual', 'schedule'

    status VARCHAR(50), -- 'running', 'success', 'failed', 'timeout'
    output TEXT,
    error_message TEXT,
    findings JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);
```

### `reminders` - Calendar/Follow-up System

```sql
CREATE TABLE claude.reminders (
    reminder_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What to remind about
    title VARCHAR(200) NOT NULL,
    description TEXT,

    -- When to check
    check_after TIMESTAMP NOT NULL,  -- Don't show until this date

    -- How to verify if done
    check_type VARCHAR(50),  -- 'manual', 'sql_query', 'file_exists', 'table_empty'
    check_condition TEXT,    -- SQL query or file path to check

    -- Reschedule behavior
    reschedule_days INTEGER DEFAULT 7,  -- If not done, check again in X days
    max_reminders INTEGER DEFAULT 3,    -- Give up after X reminders
    reminder_count INTEGER DEFAULT 0,   -- How many times reminded

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, done, dismissed, expired
    completed_at TIMESTAMP,

    -- Context
    project_name VARCHAR(100),
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reminders_due ON claude.reminders(check_after) WHERE status = 'pending';
CREATE INDEX idx_reminders_project ON claude.reminders(project_name, status);
```

**Use Cases:**
- Follow-up checks after X days (e.g., "remove backward-compat views")
- Auto-reschedule if not done
- Auto-checkable via SQL queries

---

## Part 4: Migration Steps

### Step 1: Create New Schema
```sql
CREATE SCHEMA IF NOT EXISTS claude;
```

### Step 2: Create New Tables First
Create `schema_registry`, `architecture_decisions`, `activity_feed`, `test_runs`, `job_run_history` in new schema.

### Step 3: Migrate Data (With Renames)

```sql
-- Example: Move identities
CREATE TABLE claude.identities AS
SELECT * FROM claude_family.identities;

-- Add primary key
ALTER TABLE claude.identities ADD PRIMARY KEY (identity_id);

-- Example: Move and rename
CREATE TABLE claude.sessions AS
SELECT * FROM claude_family.session_history;

-- Continue for all tables...
```

### Step 4: Create Views for Backward Compatibility

```sql
-- MCW queries claude_pm.projects - create view so it still works
CREATE VIEW claude_pm.projects AS
SELECT * FROM claude.projects;

CREATE VIEW claude_family.session_history AS
SELECT * FROM claude.sessions;

-- etc. for all moved tables
```

### Step 5: Update MCW Data Layer

Update all queries in `packages/data/src/` to use new schema:
- `FROM claude_pm.projects` → `FROM claude.projects`
- `FROM claude_family.session_history` → `FROM claude.sessions`
- etc.

### Step 6: Drop Views and Old Schemas

After MCW is updated and tested:
```sql
DROP VIEW claude_pm.projects;
DROP SCHEMA claude_pm CASCADE;
DROP SCHEMA claude_family CASCADE;
DROP SCHEMA claude_mission_control CASCADE;
DROP SCHEMA public CASCADE; -- Be careful here!
```

---

## Part 5: Final Schema Structure

```
claude (ONE schema)
├── Infrastructure
│   ├── identities
│   ├── sessions
│   ├── session_state
│   ├── messages
│   ├── scheduled_jobs
│   ├── job_run_history
│   ├── mcp_configs
│   └── workspaces
│
├── Knowledge
│   ├── knowledge
│   └── procedures
│
├── Projects & Work
│   ├── projects
│   ├── programs
│   ├── phases
│   ├── features
│   ├── components
│   ├── requirements
│   ├── build_tasks
│   ├── work_tasks
│   └── pm_tasks
│
├── Feedback
│   ├── feedback
│   ├── feedback_comments
│   └── feedback_screenshots
│
├── Documents
│   ├── documents
│   ├── project_docs
│   ├── doc_templates
│   └── ideas
│
├── Testing
│   └── test_runs
│
├── Governance (NEW)
│   ├── schema_registry
│   ├── architecture_decisions
│   ├── activity_feed
│   └── reminders
│
└── Standalone (KEEP SEPARATE)
    ├── nimbus_context.* (separate schema)
    └── tax_calculator.* (separate schema)
```

---

## Part 6: MCW Changes Required

### Data Layer Files to Update

```
packages/data/src/
├── agents.ts      → Change claude_family.identities → claude.identities
├── sessions.ts    → Change claude_family.session_history → claude.sessions
├── projects.ts    → Change claude_pm.projects → claude.projects
├── feedback.ts    → Change claude_pm.project_feedback → claude.feedback
├── features.ts    → Change claude_mission_control.features → claude.features
├── components.ts  → Change claude_mission_control.components → claude.components
├── tasks.ts       → Change claude_mission_control.work_tasks → claude.work_tasks
├── documents.ts   → Change claude_mission_control.documents → claude.documents
└── procedures.ts  → Change public.sops → claude.procedures
```

### New Data Layer Files to Create

```
packages/data/src/
├── activity.ts    → Query claude.activity_feed
├── test-runs.ts   → Query claude.test_runs
└── governance.ts  → Query schema_registry, architecture_decisions
```

### New MCW Pages (Optional but Recommended)

- `/activity` - Activity feed view
- `/test-history` - Test run history with trends
- `/schema` - Schema browser (shows schema_registry)

---

## Part 7: Checklist for Implementation

### Phase 1: Preparation
- [ ] Review this spec, ask questions
- [ ] Create `claude` schema
- [ ] Create governance tables (schema_registry, architecture_decisions, activity_feed, reminders)
- [ ] Create test_runs, job_run_history tables
- [ ] Document first ADR (ADR-001: Schema Consolidation)

### Phase 2: Migration
- [ ] Migrate claude_family tables
- [ ] Migrate claude_pm tables
- [ ] Migrate claude_mission_control tables
- [ ] Create backward-compat views
- [ ] Populate schema_registry with all tables

### Phase 3: MCW Update
- [ ] Update data layer files (one at a time, test each)
- [ ] Run E2E tests after each file
- [ ] Create new data layer files for new tables
- [ ] Add activity feed trigger on sessions table

### Phase 4: Cleanup
- [ ] Drop backward-compat views
- [ ] Drop old schemas (after confirming nothing breaks)
- [ ] Delete empty/duplicate tables
- [ ] Update CLAUDE.md documentation

### Phase 5: Verification
- [ ] All MCW pages work
- [ ] E2E tests pass
- [ ] schema_registry is complete
- [ ] Activity feed populating

---

## Notes

1. **nimbus_context and tax_calculator stay separate** - They're product data, not infrastructure

2. **public schema** - Be careful, some PostgreSQL things live here. Only drop tables, not the schema itself.

3. **Backward compat views** - These let MCW keep working while we migrate. Drop them only after MCW is fully updated.

4. **Test after each step** - Don't do it all at once. Migrate one table, test, repeat.

5. **Activity feed trigger** - Add a trigger on `sessions` table to auto-log to activity_feed when sessions start/end.

---

## Questions for Claude-MCW

1. Any tables I missed that MCW uses?
2. Preferred order for migration (which tables first)?
3. Any concerns with renaming (e.g., `session_history` → `sessions`)?
4. Want to do build_tracker entries for this work?

---

**Document Author:** claude-code-unified
**Approved By:** User (2025-12-01)
**Implementation Assigned To:** claude-mcw
