# Claude Family Architecture Plan v1.0
**Created:** 2025-12-01
**Status:** DRAFT - For Review
**Author:** claude-code-unified (Opus 4.5)

---

## Executive Summary

This document provides a comprehensive architectural analysis of the Claude Family infrastructure, identifying what exists, what's missing, and detailed designs for closing the gaps. The goal is to establish proper governance, automated monitoring, and institutional memory.

---

## Part 1: Current State Audit

### 1.1 Database Overview

| Schema | Tables | Purpose | Status |
|--------|--------|---------|--------|
| `claude_family` | 20 | Core infrastructure (identities, sessions, knowledge) | **Active, needs cleanup** |
| `claude_pm` | 11 | Project management (projects, feedback, tasks) | **Active** |
| `claude_mission_control` | 13 | MCW app data (build tasks, components, features) | **Active** |
| `nimbus_context` | 12 | Nimbus project API metadata | **Active** |
| `tax_calculator` | 37 | ATO tax calculation data | **Active, well-structured** |
| `public` | 10 | Legacy/backup tables | **Mostly unused** |

**Total: 108 tables**

### 1.2 Active Tables (By Usage)

| Table | Rows | Purpose | Health |
|-------|------|---------|--------|
| `nimbus_context.api_entities` | 366 | Nimbus API schema cache | OK |
| `claude_family.session_history` | 154 | Session logs | OK, well-used |
| `claude_mission_control.build_tasks` | 145 | MCW build tracking | OK |
| `claude_family.shared_knowledge` | 136 | Knowledge base | Needs restructure |
| `claude_mission_control.requirements` | 109 | MCW requirements | OK |
| `claude_mission_control.components` | 102 | MCW components | OK |
| `claude_pm.project_feedback` | 36 | Feedback/issues | OK |
| `claude_mission_control.features` | 34 | MCW features | OK |
| `claude_pm.projects` | 20 | Projects registry | OK |
| `claude_family.procedure_registry` | 18 | SOPs/procedures | OK |
| `claude_family.feature_backlog` | 17 | Backlog items | OK |
| `claude_family.instance_messages` | 15 | Inter-instance messages | Underused |
| `claude_family.identities` | 12 | Claude identities | Needs cleanup (9 archived) |
| `claude_family.ai_cron_jobs` | 6 | Scheduled jobs | Exists but not running |

### 1.3 Empty/Abandoned Tables (0 rows, 0 bytes)

**claude_family:**
- `api_cost_data`, `api_usage_data` - Never populated
- `cross_reference_log` - Never used
- `startup_context` - Never used
- `ui_test_results`, `ui_test_screenshots`, `ui_test_scripts` - Never used
- `usage_sync_status` - Never used

**claude_mission_control:**
- `app_settings`, `audit_log` - Never used
- `implementation_verification`, `instance_health`, `instance_messages` - Never used
- `plan_documents` - Never used

**tax_calculator:**
- Multiple calculation/entry tables empty (user data tables, waiting for app)

### 1.4 Existing Scheduling Infrastructure

`claude_family.ai_cron_jobs` exists with 6 jobs:

| Job | Type | Schedule | Last Run | Status |
|-----|------|----------|----------|--------|
| Documentation Audit | audit | Monthly | Never | Defined only |
| PostgreSQL Backup | backup | Weekly | Never | Defined only |
| User Import Sync | sync | Daily | Never | Defined only |
| MCP Memory Sync | sync | Daily | 2025-10-27 | Ran once |
| Anthropic Usage Sync | sync | Daily | 2025-11-05 | Ran once |
| Agent Health Check | health_check | Hourly | 2025-11-05 | Ran once |

**Problem:** Jobs are defined but no scheduler is executing them automatically.

---

## Part 2: Gap Analysis

### 2.1 Documentation Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| No schema registry | Rebuild tables we forgot exist | **HIGH** |
| No ADRs (Architecture Decision Records) | Don't know WHY things were built | **HIGH** |
| CLAUDE.md column names wrong | Queries fail, confusion | MEDIUM |
| No central MCP inventory | Don't know what MCPs exist | MEDIUM |
| No versioning on docs | Can't track changes | MEDIUM |

### 2.2 Knowledge Base Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| Flat structure (no project scoping) | Wrong knowledge applied to wrong projects | **HIGH** |
| Inconsistent `knowledge_type` values | Can't query properly | MEDIUM |
| No lessons learned category | Repeat same mistakes | MEDIUM |
| `learned_by_identity_id` mostly NULL | Can't track who learned what | LOW |

### 2.3 Monitoring & Automation Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| No event-driven scheduling | Manual checks only | **HIGH** |
| No code health monitoring | Don't know if projects are stale | **HIGH** |
| No test tracking | MCW loses test state on crash | **HIGH** |
| No activity feed | Can't see what happened | MEDIUM |
| No security scanning | Vulnerabilities unknown | MEDIUM |

### 2.4 Integration Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| Message board not visible in MCW | Can't see communications | MEDIUM |
| No schema browser UI | DB knowledge tribal | LOW |
| No dashboard for job status | Don't know if jobs ran | MEDIUM |

---

## Part 3: Architectural Designs

### 3.1 Schema Registry Table

**Purpose:** Track all tables/views with their purpose, owner, version, and dependencies.

```sql
CREATE TABLE claude_family.schema_registry (
    registry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identification
    schema_name VARCHAR(100) NOT NULL,
    object_name VARCHAR(200) NOT NULL,
    object_type VARCHAR(50) NOT NULL DEFAULT 'table', -- table, view, function

    -- Documentation
    purpose TEXT NOT NULL,
    owner_identity_id UUID REFERENCES claude_family.identities(identity_id),
    version VARCHAR(20) DEFAULT '1.0.0',

    -- Dependencies
    used_by_projects TEXT[], -- ['mcw', 'nimbus', 'ato']
    depends_on TEXT[], -- ['claude_family.identities']

    -- Governance
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    last_reviewed_at TIMESTAMP,
    last_reviewed_by VARCHAR(100),
    is_deprecated BOOLEAN DEFAULT FALSE,
    deprecation_note TEXT,
    migration_path TEXT, -- If deprecated, where to migrate

    -- Change tracking
    change_log JSONB DEFAULT '[]'::jsonb,
    -- Format: [{"date": "2025-12-01", "change": "Added column X", "by": "claude-code-unified"}]

    UNIQUE(schema_name, object_name)
);

CREATE INDEX idx_schema_registry_schema ON claude_family.schema_registry(schema_name);
CREATE INDEX idx_schema_registry_deprecated ON claude_family.schema_registry(is_deprecated);
```

### 3.2 Architecture Decision Records (ADRs)

**Purpose:** Document WHY architectural decisions were made.

```sql
CREATE TABLE claude_family.architecture_decisions (
    adr_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identification
    adr_number INTEGER UNIQUE, -- ADR-001, ADR-002
    title VARCHAR(200) NOT NULL,
    status VARCHAR(50) DEFAULT 'proposed', -- proposed, accepted, deprecated, superseded

    -- Context
    context TEXT NOT NULL, -- Problem we're solving
    decision TEXT NOT NULL, -- What we decided
    consequences TEXT, -- Trade-offs and implications
    alternatives_considered JSONB, -- Other options we rejected

    -- Relationships
    supersedes_adr_id UUID REFERENCES claude_family.architecture_decisions(adr_id),
    related_schemas TEXT[], -- Which schemas this affects
    related_projects TEXT[], -- Which projects this affects

    -- Governance
    proposed_by VARCHAR(100),
    proposed_at TIMESTAMP DEFAULT NOW(),
    accepted_by VARCHAR(100),
    accepted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3.3 Knowledge Base Restructure

**Problem:** Current `shared_knowledge` has flat structure with inconsistent categorization.

**Solution:** Add proper scoping and standardize categories.

```sql
-- Add new columns to existing table
ALTER TABLE claude_family.shared_knowledge
ADD COLUMN scope VARCHAR(50) DEFAULT 'universal',
ADD COLUMN scope_target VARCHAR(200), -- project name, domain name, etc.
ADD COLUMN is_lesson_learned BOOLEAN DEFAULT FALSE,
ADD COLUMN failure_context TEXT, -- What went wrong that taught us this
ADD COLUMN verified_count INTEGER DEFAULT 0; -- Times this was confirmed useful

-- Scope values:
-- 'universal' - Applies everywhere
-- 'domain' - Applies to a domain (tax, solar, pm)
-- 'project' - Applies to specific project (mcw, nimbus)
-- 'technology' - Applies to tech stack (react, python, csharp)

-- Standardized knowledge_type values:
-- 'pattern' - Reusable code/design pattern
-- 'troubleshooting' - How to fix specific problems
-- 'architecture' - System design decisions
-- 'best-practice' - Recommended approaches
-- 'reference' - Facts/data (like tax rates)
-- 'lesson-learned' - From failures

-- Create view for easy querying by scope
CREATE VIEW claude_family.knowledge_by_scope AS
SELECT
    k.*,
    CASE
        WHEN scope = 'universal' THEN 1
        WHEN scope = 'domain' THEN 2
        WHEN scope = 'technology' THEN 3
        WHEN scope = 'project' THEN 4
    END as scope_priority
FROM claude_family.shared_knowledge k
ORDER BY scope_priority, confidence_level DESC;
```

### 3.4 Event-Driven Scheduling System

**Concept:** Instead of background cron, run checks when Claude starts a session based on conditions.

```sql
-- Extend ai_cron_jobs for event-driven execution
ALTER TABLE claude_family.ai_cron_jobs
ADD COLUMN trigger_type VARCHAR(50) DEFAULT 'schedule', -- 'schedule', 'session_start', 'session_end', 'on_demand'
ADD COLUMN trigger_condition JSONB DEFAULT '{}',
-- Examples:
-- {"days_since_last_run": 7}
-- {"project_match": "mcw"}
-- {"check_type": "security", "min_days_stale": 14}
ADD COLUMN priority INTEGER DEFAULT 5, -- 1=highest, run first
ADD COLUMN estimated_duration_seconds INTEGER DEFAULT 60,
ADD COLUMN run_as_agent BOOLEAN DEFAULT FALSE, -- Spawn as sub-agent?
ADD COLUMN agent_type VARCHAR(100); -- If run_as_agent, which type

-- Job run history for tracking
CREATE TABLE claude_family.job_run_history (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES claude_family.ai_cron_jobs(job_id),

    -- Execution
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    triggered_by VARCHAR(50), -- 'session_start', 'manual', 'schedule'
    triggered_by_session_id UUID,

    -- Results
    status VARCHAR(50), -- 'running', 'success', 'failed', 'timeout'
    output TEXT,
    error_message TEXT,
    findings JSONB, -- Structured results

    -- If run as agent
    agent_session_id UUID,
    cost_usd DECIMAL(10, 4)
);

CREATE INDEX idx_job_history_job ON claude_family.job_run_history(job_id, started_at DESC);
```

**Session Start Hook Integration:**

```python
# In session_startup_hook.py, add:

def check_due_jobs(project_name: str):
    """Check if any jobs should run based on conditions."""
    query = """
        SELECT j.*,
               EXTRACT(DAY FROM NOW() - COALESCE(j.last_run, j.created_at)) as days_since_run
        FROM claude_family.ai_cron_jobs j
        WHERE j.is_active = true
        AND j.trigger_type = 'session_start'
        AND (
            -- Check days_since_last_run condition
            (j.trigger_condition->>'days_since_last_run')::int <=
            EXTRACT(DAY FROM NOW() - COALESCE(j.last_run, j.created_at))
            OR
            -- Check project match
            j.trigger_condition->>'project_match' = %s
            OR
            j.trigger_condition->>'project_match' IS NULL
        )
        ORDER BY j.priority ASC
        LIMIT 5; -- Don't overwhelm session start
    """
    # Return jobs that need running, let Claude decide to run them
```

### 3.5 Test Tracking System

**Purpose:** Persist test results across sessions, track trends, survive crashes.

```sql
CREATE TABLE claude_family.test_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    project_id UUID REFERENCES claude_pm.projects(project_id),
    project_name VARCHAR(100) NOT NULL,
    session_id UUID REFERENCES claude_family.session_history(session_id),

    -- Execution
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    test_type VARCHAR(50) NOT NULL, -- 'e2e', 'unit', 'integration', 'security'
    test_framework VARCHAR(50), -- 'playwright', 'pytest', 'jest', 'nunit'

    -- Environment
    git_branch VARCHAR(200),
    git_commit VARCHAR(40),
    environment VARCHAR(50) DEFAULT 'development',

    -- Results
    total_tests INTEGER,
    passed INTEGER,
    failed INTEGER,
    skipped INTEGER,
    pass_rate DECIMAL(5, 2) GENERATED ALWAYS AS (
        CASE WHEN total_tests > 0 THEN (passed::decimal / total_tests) * 100 ELSE 0 END
    ) STORED,

    -- Details
    failed_tests JSONB, -- [{name, error, file, line}]
    duration_seconds DECIMAL(10, 2),
    output_log TEXT,

    -- Change context
    triggered_by VARCHAR(100), -- 'manual', 'ci', 'pre-commit', 'agent'
    related_files_changed TEXT[],

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_test_runs_project ON claude_family.test_runs(project_name, started_at DESC);
CREATE INDEX idx_test_runs_type ON claude_family.test_runs(test_type, started_at DESC);

-- View for test health dashboard
CREATE VIEW claude_family.test_health_summary AS
SELECT
    project_name,
    test_type,
    COUNT(*) as total_runs,
    AVG(pass_rate) as avg_pass_rate,
    MAX(started_at) as last_run,
    EXTRACT(DAY FROM NOW() - MAX(started_at)) as days_since_last_run,
    (SELECT pass_rate FROM claude_family.test_runs t2
     WHERE t2.project_name = t.project_name
     AND t2.test_type = t.test_type
     ORDER BY started_at DESC LIMIT 1) as latest_pass_rate
FROM claude_family.test_runs t
GROUP BY project_name, test_type;
```

### 3.6 Reminders / Calendar System

**Purpose:** Track follow-up tasks that need checking after X days. Auto-reschedule if not done.

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

**Session Start Integration:**

```python
# In session_startup_hook.py, check due reminders:
def check_reminders():
    query = """
        SELECT * FROM claude.reminders
        WHERE check_after <= NOW() AND status = 'pending'
        ORDER BY check_after ASC
    """
    for reminder in results:
        if reminder.check_type == 'sql_query':
            # Run check_condition, if returns true -> mark done
            pass
        elif reminder.check_type == 'manual':
            # Show to user, ask if done
            pass

        if not done:
            # Increment count, reschedule
            UPDATE reminders SET
                reminder_count = reminder_count + 1,
                check_after = NOW() + (reschedule_days || ' days')::interval
            WHERE reminder_id = ...

            # If max reached, expire
            IF reminder_count >= max_reminders:
                UPDATE reminders SET status = 'expired'
```

**Use Cases:**
- "Check if backward-compat views can be removed in 7 days"
- "Verify activity_feed is being populated in 3 days"
- "Review security scan results monthly"

---

### 3.7 Activity Feed / Message Board

**Purpose:** Unified view of all system activity.

```sql
CREATE TABLE claude_family.activity_feed (
    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source
    source_type VARCHAR(50) NOT NULL, -- 'session', 'message', 'job', 'test', 'commit', 'alert'
    source_id UUID, -- Reference to source table

    -- Actor
    actor_identity_id UUID REFERENCES claude_family.identities(identity_id),
    actor_name VARCHAR(100),

    -- Content
    activity_type VARCHAR(100) NOT NULL, -- 'session_started', 'test_completed', 'job_ran', etc.
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    metadata JSONB DEFAULT '{}',

    -- Context
    project_name VARCHAR(100),
    severity VARCHAR(20) DEFAULT 'info', -- 'info', 'warning', 'error', 'success'

    -- Visibility
    is_broadcast BOOLEAN DEFAULT FALSE,
    visible_to TEXT[], -- NULL = everyone, or list of identity names

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_activity_feed_time ON claude_family.activity_feed(created_at DESC);
CREATE INDEX idx_activity_feed_project ON claude_family.activity_feed(project_name, created_at DESC);
CREATE INDEX idx_activity_feed_type ON claude_family.activity_feed(activity_type);

-- Auto-populate from session starts
CREATE OR REPLACE FUNCTION log_session_to_activity()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO claude_family.activity_feed (
        source_type, source_id, actor_identity_id, actor_name,
        activity_type, title, project_name, severity
    )
    SELECT
        'session', NEW.session_id, NEW.identity_id, i.identity_name,
        'session_started',
        'Started session on ' || COALESCE(NEW.project_name, 'unknown project'),
        NEW.project_name,
        'info'
    FROM claude_family.identities i
    WHERE i.identity_id = NEW.identity_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_session_to_activity
AFTER INSERT ON claude_family.session_history
FOR EACH ROW EXECUTE FUNCTION log_session_to_activity();
```

---

## Part 4: Event-Driven Job Configuration

### 4.1 Proposed Jobs for Session Start

| Job | Condition | Action | Agent? |
|-----|-----------|--------|--------|
| Security Scan | days_since_last_run >= 7 | Run security-sonnet on project | Yes |
| Test Health Check | days_since_last_run >= 3 | Check test pass rates, report | No |
| Doc Staleness Check | days_since_last_run >= 14 | Report outdated docs | No |
| Dependency Check | days_since_last_run >= 7 | Check for outdated packages | No |
| Schema Drift Check | days_since_last_run >= 7 | Compare DB to docs | No |

### 4.2 MCW Integration Points

MCW should display:
1. **Activity Feed Page** - Show `activity_feed` table
2. **Jobs Dashboard** - Show `ai_cron_jobs` + `job_run_history`
3. **Test Tracker Page** - Show `test_runs` with trends
4. **Schema Browser** - Show `schema_registry`
5. **Knowledge Search** - Query `shared_knowledge` with scope filters

---

## Part 5: Implementation Roadmap

### Phase 1: Foundation (This Session)
- [ ] Create `schema_registry` table
- [ ] Create `architecture_decisions` table
- [ ] Alter `shared_knowledge` for scoping
- [ ] Create `test_runs` table
- [ ] Create `activity_feed` table + trigger

### Phase 2: Data Migration
- [ ] Populate `schema_registry` with all 108 tables
- [ ] Standardize `shared_knowledge` types
- [ ] Migrate inconsistent knowledge entries
- [ ] Clean up stale identities

### Phase 3: Event-Driven Scheduling
- [ ] Extend `ai_cron_jobs` schema
- [ ] Create `job_run_history` table
- [ ] Update `session_startup_hook.py`
- [ ] Define initial job set

### Phase 4: MCW Integration
- [ ] Activity Feed page
- [ ] Jobs Dashboard
- [ ] Test Tracker page
- [ ] Schema Browser

---

## Part 6: Open Questions

1. **Job execution model:** Should jobs run as sub-agents (isolated, logged) or inline in session startup hook (faster but blocks)?

2. **Test tracker granularity:** Track individual test cases or just run summaries?

3. **Activity feed retention:** How long to keep? Auto-archive after 90 days?

4. **Schema registry auto-population:** Script to crawl DB and populate, or manual entry only?

---

## Appendix A: Schema Summary by Domain

### Core Infrastructure (claude_family)
- identities, session_history, session_state
- shared_knowledge, procedure_registry
- instance_messages, feature_backlog
- ai_cron_jobs, mcp_configurations

### Project Management (claude_pm)
- projects, programs, phases, tasks
- project_feedback, project_feedback_comments
- project_documents, project_ideas

### Mission Control Web (claude_mission_control)
- build_tasks, components, features, requirements
- documents, work_tasks
- audit_log, app_settings

### Nimbus (nimbus_context)
- api_entities, api_properties, api_types
- project_facts, project_learnings, project_decisions

### ATO Tax (tax_calculator)
- 37 tables for tax return structure, wizard, calculations

---

**Document Version:** 1.0
**Next Review:** After implementation of Phase 1
