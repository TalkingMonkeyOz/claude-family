# Infrastructure Domain Tables - Data Gateway Analysis

**Created:** 2025-12-04
**Purpose:** Analyze Infrastructure domain tables for Data Gateway workflow tool design
**Schema:** `claude` (consolidated from claude_family, claude_pm, claude_mission_control)
**Status:** ANALYSIS COMPLETE

---

## Executive Summary

This document provides a comprehensive analysis of the 7 core infrastructure tables in the `claude` schema, including:
- Valid status/type values based on actual data
- Required fields and business rules
- Workflow state transitions
- Recommended workflow tools

These tables support the Claude Family's coordination, messaging, scheduling, and knowledge management infrastructure.

---

## Table 1: sessions

**Purpose:** Track Claude instance work sessions across projects

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| session_id | uuid | NO | - | Primary key |
| identity_id | uuid | YES | - | FK to identities |
| project_schema | varchar(100) | YES | - | Database schema for project |
| project_name | varchar(200) | YES | - | Project being worked on |
| session_start | timestamp | YES | - | When session began |
| session_end | timestamp | YES | - | When session ended (NULL = active) |
| tasks_completed | text[] | YES | - | Array of completed tasks |
| learnings_gained | text[] | YES | - | Array of learnings |
| challenges_encountered | text[] | YES | - | Array of challenges |
| session_summary | text | YES | - | Final summary |
| session_metadata | jsonb | YES | - | Additional metadata |
| created_at | timestamp | YES | - | Record creation time |

### Valid Status Values

Sessions have implicit status based on `session_end`:
- **active** - session_end IS NULL
- **ended** - session_end IS NOT NULL

### Required Fields

- `session_id` - Always required (primary key)
- `identity_id` - Should be required (who is working?)
- `project_name` - Should be required (what are they working on?)
- `session_start` - Should be required (when did it start?)

### Business Rules

1. **Session must have identity** - Every session should reference a valid identity
2. **Active sessions** - Only one active session per identity at a time
3. **End time validation** - session_end must be >= session_start
4. **Summary required on close** - session_summary should be required when session_end is set

### Workflow Transitions

```
START SESSION (session_end = NULL)
    ↓
ACTIVE SESSION (working...)
    ↓
END SESSION (set session_end, require summary)
    ↓
CLOSED SESSION (archived)
```

### Recommended Tools

```python
# Start a new session
start_session(identity_id, project_name, project_schema=None)
  → Returns: session_id
  → Sets: session_start = NOW(), session_end = NULL
  → Validates: No other active session for this identity

# End current session
end_session(session_id, summary, tasks=[], learnings=[], challenges=[])
  → Sets: session_end = NOW(), session_summary, tasks_completed, learnings_gained
  → Validates: session exists and is active (session_end IS NULL)
  → Triggers: activity_feed log entry

# Get active session
get_active_session(identity_id)
  → Returns: session_id or None
  → Query: WHERE identity_id = ? AND session_end IS NULL
```

---

## Table 2: messages

**Purpose:** Inter-Claude instance messaging and coordination

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| message_id | uuid | NO | gen_random_uuid() | Primary key |
| from_session_id | uuid | YES | - | Sender session |
| to_session_id | uuid | YES | - | Recipient session (for DM) |
| to_project | varchar(100) | YES | - | Recipient project (for broadcast) |
| message_type | varchar(50) | YES | - | Type of message |
| priority | varchar(20) | YES | - | Message priority |
| subject | varchar(200) | YES | - | Message subject |
| body | text | YES | - | Message content |
| metadata | jsonb | YES | - | Additional data |
| status | varchar(20) | YES | 'pending' | Read/acknowledge status |
| read_at | timestamp | YES | - | When read |
| acknowledged_at | timestamp | YES | - | When acknowledged |
| created_at | timestamp | YES | now() | Creation time |
| expires_at | timestamp | YES | - | Expiration time |

### Valid Type Values

**message_type** (from actual data):
- `task_request` - Request another instance to do work
- `status_update` - Inform about progress
- `notification` - General notification
- `broadcast` - Broadcast to all instances
- `question` - Ask for help/clarification
- `handoff` - Transfer work to another instance

**priority** (from actual data):
- `urgent` - Immediate attention required
- `normal` - Standard priority (default)
- `low` - Can be delayed

**status** (from actual data):
- `pending` - Not yet read (default)
- `read` - Message has been read
- `acknowledged` - Message acknowledged/acted upon
- `expired` - Message has expired

### Required Fields

- `message_id` - Always required (primary key)
- `from_session_id` - Should be required (who sent it?)
- `message_type` - Should be required (what kind of message?)
- `subject` - Should be required (what's it about?)
- `body` - Should be required (message content)
- **Either** `to_session_id` OR `to_project` - Must have recipient

### Business Rules

1. **Must have recipient** - Either to_session_id OR to_project must be set
2. **Cannot have both recipients** - Only one of to_session_id or to_project
3. **Expiration handling** - Expired messages (expires_at < NOW()) should be ignored
4. **Status progression** - pending → read → acknowledged (one-way only)
5. **Priority defaults** - Default to 'normal' if not specified

### Workflow Transitions

```
CREATE MESSAGE (status = 'pending')
    ↓
READ MESSAGE (status = 'read', set read_at)
    ↓
ACKNOWLEDGE MESSAGE (status = 'acknowledged', set acknowledged_at)
    ↓
[EXPIRED] (expires_at < NOW(), ignore)
```

### Recommended Tools

```python
# Send direct message
send_message(from_session_id, to_session_id, subject, body,
             message_type='notification', priority='normal', expires_in_days=7)
  → Returns: message_id
  → Sets: status = 'pending', created_at = NOW(), expires_at
  → Validates: from_session exists, to_session exists

# Broadcast to project
broadcast_to_project(from_session_id, project_name, subject, body,
                     message_type='broadcast', priority='normal')
  → Returns: message_id
  → Sets: to_project, status = 'pending'
  → Validates: project exists

# Check inbox (pending messages)
get_pending_messages(session_id=None, project_name=None)
  → Returns: List of messages
  → Filters: status = 'pending' AND expires_at > NOW()
  → Can filter by: to_session_id OR to_project

# Mark as read
mark_message_read(message_id)
  → Sets: status = 'read', read_at = NOW()
  → Validates: status = 'pending'

# Acknowledge message
acknowledge_message(message_id)
  → Sets: status = 'acknowledged', acknowledged_at = NOW()
  → Validates: status IN ('pending', 'read')
  → Triggers: activity_feed log entry
```

---

## Table 3: identities

**Purpose:** Registry of Claude instances and their capabilities

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| identity_id | uuid | NO | - | Primary key |
| identity_name | varchar(100) | YES | - | Instance name |
| platform | varchar(50) | YES | - | Platform (Claude Code, MCW, etc) |
| role_description | text | YES | - | Role description |
| capabilities | jsonb | YES | - | What this instance can do |
| personality_traits | jsonb | YES | - | Personality characteristics |
| learning_style | jsonb | YES | - | Learning preferences |
| status | varchar(20) | YES | - | Active or archived |
| created_at | timestamp | YES | - | Creation time |
| last_active_at | timestamp | YES | - | Last activity time |

### Valid Status Values

**status** (from actual data):
- `active` - Currently in use
- `archived` - No longer in use (historical)

### Required Fields

- `identity_id` - Always required (primary key)
- `identity_name` - Should be required (unique name)
- `platform` - Should be required (where does it run?)
- `status` - Should be required, default 'active'

### Business Rules

1. **Unique identity names** - identity_name should be unique across active identities
2. **Auto-update last_active** - Update last_active_at when session starts
3. **Cannot delete** - Only archive (preserve referential integrity)
4. **Capabilities structure** - Should follow standard schema (mcp_servers, tools, etc.)

### Workflow Transitions

```
CREATE IDENTITY (status = 'active')
    ↓
ACTIVE (regular usage, update last_active_at)
    ↓
ARCHIVE (status = 'archived')
```

### Recommended Tools

```python
# Register new identity
register_identity(identity_name, platform, role_description, capabilities={})
  → Returns: identity_id
  → Sets: status = 'active', created_at = NOW()
  → Validates: identity_name unique among active identities

# Update last activity
update_identity_activity(identity_id)
  → Sets: last_active_at = NOW()
  → Called automatically on session start

# Archive identity
archive_identity(identity_id)
  → Sets: status = 'archived'
  → Validates: No active sessions for this identity

# Get active identities
get_active_identities()
  → Returns: List of active identities
  → Query: WHERE status = 'active' ORDER BY last_active_at DESC
```

---

## Table 4: scheduled_jobs

**Purpose:** Event-driven job scheduling system

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| job_id | uuid | NO | - | Primary key |
| project_id | uuid | YES | - | FK to projects (optional) |
| job_name | varchar(200) | YES | - | Job name |
| job_description | text | YES | - | What the job does |
| job_type | varchar(50) | YES | - | Category of job |
| schedule | varchar(100) | YES | - | Cron expression (if time-based) |
| last_run | timestamp | YES | - | Last execution time |
| last_status | varchar(20) | YES | - | Result of last run |
| last_output | text | YES | - | Output from last run |
| last_error | text | YES | - | Error from last run |
| next_run | timestamp | YES | - | Scheduled next run |
| run_count | integer | YES | - | Total runs |
| success_count | integer | YES | - | Successful runs |
| is_active | boolean | YES | - | Enable/disable |
| timeout_seconds | integer | YES | - | Max execution time |
| retry_on_failure | boolean | YES | - | Retry on error |
| max_retries | integer | YES | - | Max retry attempts |
| command | text | YES | - | Command to execute |
| working_directory | text | YES | - | Working directory |
| created_at | timestamp | YES | - | Creation time |
| created_by_identity_id | uuid | YES | - | Creator |
| updated_at | timestamp | YES | - | Last update time |
| metadata | jsonb | YES | - | Additional data |
| trigger_type | varchar(50) | YES | 'session_start' | When to trigger |
| trigger_condition | jsonb | YES | {} | Conditions to check |
| priority | integer | YES | 5 | Execution priority (1=highest) |

### Valid Type Values

**job_type** (from actual data):
- `maintenance` - Cleanup, optimization tasks
- `sync` - Data synchronization
- `backup` - Backup operations
- `audit` - Data quality checks
- `health_check` - System health monitoring
- `indexer` - Document/data indexing
- `security` - Security scans

**trigger_type** (from actual data):
- `session_start` - Run when session starts (event-driven)
- `schedule` - Run on cron schedule (time-based)
- `on_demand` - Manual execution only
- `session_end` - Run when session ends

**last_status** (from actual data):
- `SUCCESS` - Job completed successfully
- `FAILED` - Job failed with error
- `TIMEOUT` - Job exceeded timeout_seconds
- `SKIPPED` - Job skipped due to conditions
- `RUNNING` - Currently executing

### Required Fields

- `job_id` - Always required (primary key)
- `job_name` - Should be required (unique name)
- `job_type` - Should be required (categorization)
- `trigger_type` - Should be required (how to trigger)
- `is_active` - Should be required, default true
- `priority` - Should be required, default 5

### Business Rules

1. **Trigger conditions** - For session_start triggers, check trigger_condition JSON
2. **Priority execution** - Lower number = higher priority (1 is highest)
3. **Frequency limiting** - Use trigger_condition like `{"days_since_last_run": 7}`
4. **Timeout enforcement** - Kill job if exceeds timeout_seconds
5. **Retry logic** - If retry_on_failure=true and status=FAILED, retry up to max_retries
6. **Session start limit** - Don't run more than 5 jobs on session start (performance)

### Workflow Transitions

```
SESSION START
    ↓
CHECK DUE JOBS (is_active=true, check trigger_condition)
    ↓
EXECUTE BY PRIORITY (priority ASC)
    ↓
UPDATE STATUS (last_run, last_status, run_count)
    ↓
[SUCCESS] → increment success_count
[FAILED] → check retry_on_failure
    ↓
LOG TO activity_feed
```

### Recommended Tools

```python
# Create scheduled job
create_scheduled_job(job_name, job_type, command, trigger_type='session_start',
                     trigger_condition={}, priority=5, timeout_seconds=300)
  → Returns: job_id
  → Sets: is_active = true, created_at = NOW()
  → Validates: job_name unique

# Check due jobs (called by session startup hook)
get_due_jobs(project_name=None)
  → Returns: List of jobs to run (max 5)
  → Filters: is_active=true, check trigger_condition
  → Orders: BY priority ASC

# Execute job
execute_job(job_id, session_id=None)
  → Sets: last_run = NOW(), last_status = 'RUNNING'
  → Executes: command in working_directory
  → Updates: last_status, last_output/error, run_count, success_count
  → Returns: execution result
  → Triggers: activity_feed log entry

# Update job status
update_job_result(job_id, status, output=None, error=None)
  → Sets: last_status, last_output, last_error
  → Increments: run_count, success_count (if SUCCESS)
  → Calculates: next_run (if schedule-based)
```

---

## Table 5: reminders

**Purpose:** Follow-up tasks with auto-rescheduling

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| reminder_id | uuid | NO | gen_random_uuid() | Primary key |
| title | varchar(200) | NO | - | Reminder title |
| description | text | YES | - | Details |
| check_after | timestamp | NO | - | Don't check until this date |
| check_type | varchar(50) | YES | - | How to verify |
| check_condition | text | YES | - | SQL query or file path |
| reschedule_days | integer | YES | 7 | Days to reschedule if not done |
| max_reminders | integer | YES | 3 | Max reminder attempts |
| reminder_count | integer | YES | 0 | Current attempt count |
| status | varchar(20) | YES | 'pending' | Current status |
| completed_at | timestamp | YES | - | When completed |
| project_name | varchar(100) | YES | - | Associated project |
| created_by | varchar(100) | YES | - | Creator |
| created_at | timestamp | YES | now() | Creation time |

### Valid Type Values

**check_type** (from actual data + design):
- `manual` - User must manually confirm (from actual data)
- `sql_query` - Run SQL to check if done
- `file_exists` - Check if file exists
- `table_empty` - Check if table has 0 rows

**status** (from actual data + design):
- `pending` - Not yet due or not completed (default, from actual data)
- `done` - Completed successfully
- `dismissed` - User dismissed without completing
- `expired` - Max reminders reached

### Required Fields

- `reminder_id` - Always required (primary key)
- `title` - Always required (what to remind about)
- `check_after` - Always required (when to check)
- `status` - Should be required, default 'pending'

### Business Rules

1. **Don't show until due** - Only surface reminders where check_after <= NOW()
2. **Auto-reschedule** - If not done, reschedule by adding reschedule_days
3. **Max attempts** - After max_reminders, set status = 'expired'
4. **Auto-check** - For check_type='sql_query', run check_condition to verify
5. **Status progression** - pending → (done | dismissed | expired)

### Workflow Transitions

```
CREATE REMINDER (status = 'pending', check_after in future)
    ↓
WAIT UNTIL DUE (check_after <= NOW)
    ↓
CHECK CONDITION
    ↓
[DONE] → status = 'done', set completed_at
[NOT DONE] → increment reminder_count
    ↓
    IF reminder_count < max_reminders:
        Reschedule (check_after += reschedule_days days)
    ELSE:
        status = 'expired'
```

### Recommended Tools

```python
# Create reminder
create_reminder(title, check_after, description=None, check_type='manual',
                check_condition=None, reschedule_days=7, max_reminders=3)
  → Returns: reminder_id
  → Sets: status = 'pending', reminder_count = 0, created_at = NOW()

# Get due reminders
get_due_reminders(project_name=None)
  → Returns: List of reminders
  → Filters: status = 'pending' AND check_after <= NOW()
  → Orders: BY check_after ASC

# Check reminder (called by session startup hook)
check_reminder(reminder_id)
  → If check_type = 'sql_query': Run check_condition
  → If check_type = 'manual': Prompt user
  → Returns: is_done (boolean)

# Complete reminder
complete_reminder(reminder_id)
  → Sets: status = 'done', completed_at = NOW()

# Reschedule reminder
reschedule_reminder(reminder_id)
  → Increments: reminder_count
  → Sets: check_after = NOW() + reschedule_days days
  → If reminder_count >= max_reminders: status = 'expired'

# Dismiss reminder
dismiss_reminder(reminder_id)
  → Sets: status = 'dismissed', completed_at = NOW()
```

---

## Table 6: activity_feed

**Purpose:** Unified activity log for all system events

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | uuid | NO | gen_random_uuid() | Primary key |
| source_type | varchar(50) | NO | - | Source category |
| source_id | uuid | YES | - | Reference to source record |
| actor | varchar(100) | YES | - | Who performed action |
| activity_type | varchar(100) | NO | - | Specific activity |
| title | varchar(500) | NO | - | Activity title |
| summary | text | YES | - | Detailed description |
| project_name | varchar(100) | YES | - | Associated project |
| severity | varchar(20) | YES | 'info' | Importance level |
| created_at | timestamp | YES | now() | When it happened |

### Valid Type Values

**source_type** (from actual data + design):
- `session` - Session start/end (from actual data)
- `message` - Message sent/received (from actual data)
- `job` - Scheduled job execution
- `test` - Test run
- `feedback` - Feedback/issue activity
- `commit` - Git commit
- `alert` - System alert

**activity_type** (examples based on source_type):
- `session_started` - Session began (from actual data)
- `session_ended` - Session completed
- `message_sent` - Message sent (from actual data)
- `message_received` - Message received
- `job_completed` - Job finished
- `job_failed` - Job failed
- `test_passed` - Tests passed
- `test_failed` - Tests failed
- `feedback_created` - New feedback
- `alert_raised` - Alert triggered

**severity** (from actual data + design):
- `info` - Informational (default, from actual data)
- `success` - Positive outcome
- `warning` - Warning condition
- `error` - Error occurred

### Required Fields

- `id` - Always required (primary key)
- `source_type` - Always required (what created this?)
- `activity_type` - Always required (what happened?)
- `title` - Always required (summary)
- `severity` - Should be required, default 'info'

### Business Rules

1. **Auto-populated by triggers** - Use database triggers on sessions, messages, etc.
2. **Immutable** - Once created, activity feed entries should not be updated
3. **Retention policy** - Archive entries older than 90 days
4. **Filtering** - Allow filtering by project_name, severity, source_type
5. **Severity escalation** - Errors should be highly visible

### Workflow Transitions

```
EVENT OCCURS (session start, message sent, job run, etc.)
    ↓
TRIGGER FIRES (on INSERT to source table)
    ↓
CREATE ACTIVITY_FEED ENTRY
    ↓
[IMMUTABLE] (never updated, only queried)
```

### Recommended Tools

```python
# Log activity (usually called by triggers, not directly)
log_activity(source_type, source_id, actor, activity_type, title,
             summary=None, project_name=None, severity='info')
  → Returns: activity_id
  → Sets: created_at = NOW()
  → Triggers: Nothing (this is the end of the chain)

# Get recent activity
get_recent_activity(project_name=None, severity=None, limit=50)
  → Returns: List of activity entries
  → Filters: By project_name, severity if provided
  → Orders: BY created_at DESC
  → Limits: Default 50 entries

# Get activity for source
get_activity_by_source(source_type, source_id)
  → Returns: Activity history for specific source
  → Example: All activity for session_id

# Database triggers (auto-log to activity_feed)
# - On sessions INSERT → log "session_started"
# - On sessions UPDATE (session_end) → log "session_ended"
# - On messages INSERT → log "message_sent"
```

---

## Table 7: knowledge

**Purpose:** Shared knowledge base across Claude instances

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| knowledge_id | uuid | NO | - | Primary key |
| learned_by_identity_id | uuid | YES | - | Who learned this |
| knowledge_type | varchar(50) | YES | - | Category |
| knowledge_category | varchar(100) | YES | - | Sub-category |
| title | varchar(200) | YES | - | Knowledge title |
| description | text | YES | - | Detailed description |
| applies_to_projects | text[] | YES | - | Which projects |
| applies_to_platforms | text[] | YES | - | Which platforms |
| confidence_level | integer | YES | - | 1-10 confidence |
| times_applied | integer | YES | - | Usage count |
| times_failed | integer | YES | - | Failure count |
| code_example | text | YES | - | Code snippet |
| related_knowledge | text[] | YES | - | Related knowledge_ids |
| created_at | timestamp | YES | - | Creation time |
| updated_at | timestamp | YES | - | Last update |
| last_applied_at | timestamp | YES | - | Last usage |

### Valid Type Values

**knowledge_type** (standardized, from actual data):
- `pattern` - Reusable code/design pattern (75 entries)
- `gotcha` - Common pitfalls/traps (16 entries)
- `best-practice` - Recommended approaches (15 entries)
- `bug-fix` - Bug fixes and workarounds (12 entries)
- `reference` - Facts, configs, references (10 entries)
- `architecture` - System design decisions (8 entries)
- `troubleshooting` - How to fix problems (5 entries)
- `api-reference` - API patterns and limitations (3 entries)

**knowledge_category** (examples):
- Technology: 'react', 'typescript', 'postgresql', 'csharp'
- Domain: 'testing', 'security', 'performance', 'ui-ux'
- Process: 'deployment', 'git-workflow', 'documentation'

**confidence_level** (1-10 scale):
- 1-3: Low confidence, experimental
- 4-6: Medium confidence, works sometimes
- 7-9: High confidence, proven
- 10: Absolute certainty, verified multiple times

### Required Fields

- `knowledge_id` - Always required (primary key)
- `knowledge_type` - Should be required (categorization)
- `title` - Should be required (what is this about?)
- `description` - Should be required (the actual knowledge)
- `confidence_level` - Should be required, default 5

### Business Rules

1. **Scope filtering** - Use applies_to_projects to filter relevant knowledge
2. **Confidence tracking** - Increment times_applied on success, times_failed on failure
3. **Auto-adjust confidence** - Recalculate confidence_level based on success/failure ratio
4. **Last applied tracking** - Update last_applied_at when used
5. **Type standardization** - Only allow predefined knowledge_type values
6. **Related knowledge** - Link related knowledge items for discovery

### Workflow Transitions

```
RECORD KNOWLEDGE (new learning)
    ↓
CATEGORIZE (knowledge_type, category, applies_to)
    ↓
AVAILABLE FOR USE (query by project/platform/type)
    ↓
APPLY KNOWLEDGE
    ↓
TRACK RESULT (times_applied++, update confidence)
    ↓
[SUCCESS] → maintain/increase confidence
[FAILED] → times_failed++, decrease confidence
```

### Recommended Tools

```python
# Record new knowledge
record_knowledge(title, description, knowledge_type,
                 applies_to_projects=[], confidence_level=5,
                 learned_by_identity_id=None, code_example=None)
  → Returns: knowledge_id
  → Sets: created_at = NOW(), times_applied = 0, times_failed = 0
  → Validates: knowledge_type in allowed values

# Search knowledge
search_knowledge(project_name=None, knowledge_type=None,
                 search_text=None, min_confidence=5)
  → Returns: List of knowledge items
  → Filters: By project, type, text search, confidence
  → Orders: BY confidence_level DESC, times_applied DESC

# Apply knowledge (track usage)
apply_knowledge(knowledge_id, was_successful=True)
  → Increments: times_applied
  → Sets: last_applied_at = NOW()
  → If not successful: Increments times_failed
  → Recalculates: confidence_level based on success ratio

# Update knowledge
update_knowledge(knowledge_id, **updates)
  → Updates: specified fields
  → Sets: updated_at = NOW()
  → Validates: knowledge_type if changed
```

---

## Summary: Recommended Workflow Tools

### Session Management
- `start_session(identity_id, project_name)` → session_id
- `end_session(session_id, summary, tasks, learnings, challenges)` → void
- `get_active_session(identity_id)` → session_id | None

### Messaging
- `send_message(from_session_id, to_session_id, subject, body, type, priority)` → message_id
- `broadcast_to_project(from_session_id, project, subject, body)` → message_id
- `get_pending_messages(session_id, project_name)` → messages[]
- `mark_message_read(message_id)` → void
- `acknowledge_message(message_id)` → void

### Identity Management
- `register_identity(name, platform, role, capabilities)` → identity_id
- `update_identity_activity(identity_id)` → void
- `archive_identity(identity_id)` → void
- `get_active_identities()` → identities[]

### Job Scheduling
- `create_scheduled_job(name, type, command, trigger_type, condition, priority)` → job_id
- `get_due_jobs(project_name)` → jobs[]
- `execute_job(job_id, session_id)` → result
- `update_job_result(job_id, status, output, error)` → void

### Reminders
- `create_reminder(title, check_after, check_type, condition)` → reminder_id
- `get_due_reminders(project_name)` → reminders[]
- `check_reminder(reminder_id)` → is_done
- `complete_reminder(reminder_id)` → void
- `reschedule_reminder(reminder_id)` → void
- `dismiss_reminder(reminder_id)` → void

### Activity Logging
- `log_activity(source_type, source_id, actor, activity_type, title, severity)` → activity_id
- `get_recent_activity(project_name, severity, limit)` → activities[]
- `get_activity_by_source(source_type, source_id)` → activities[]

### Knowledge Management
- `record_knowledge(title, description, type, applies_to, confidence)` → knowledge_id
- `search_knowledge(project, type, text, min_confidence)` → knowledge[]
- `apply_knowledge(knowledge_id, was_successful)` → void
- `update_knowledge(knowledge_id, **updates)` → void

---

## Integration Points

### Session Startup Hook
The session startup hook should check:
1. **Due reminders** - `get_due_reminders(project_name)`
2. **Pending messages** - `get_pending_messages(session_id, project_name)`
3. **Due jobs** - `get_due_jobs(project_name)` (limit 5)
4. **Recent activity** - `get_recent_activity(project_name, limit=10)`

### Database Triggers
Auto-populate activity_feed:
- Session start → log "session_started"
- Session end → log "session_ended"
- Message sent → log "message_sent"
- Job completed → log "job_completed" or "job_failed"

### Mission Control Web Integration
MCW should display:
- Activity Feed page (`activity_feed` table)
- Messages page (`messages` table)
- Scheduler page (`scheduled_jobs` + job_run_history)
- Reminders page (`reminders` table)
- Knowledge search (`knowledge` table with filters)

---

## Status Enums Reference

### Quick Reference Table

| Table | Field | Valid Values |
|-------|-------|--------------|
| identities | status | active, archived |
| messages | status | pending, read, acknowledged, expired |
| messages | priority | urgent, normal, low |
| messages | message_type | task_request, status_update, notification, broadcast, question, handoff |
| scheduled_jobs | job_type | maintenance, sync, backup, audit, health_check, indexer, security |
| scheduled_jobs | trigger_type | session_start, schedule, on_demand, session_end |
| scheduled_jobs | last_status | SUCCESS, FAILED, TIMEOUT, SKIPPED, RUNNING |
| reminders | status | pending, done, dismissed, expired |
| reminders | check_type | manual, sql_query, file_exists, table_empty |
| activity_feed | source_type | session, message, job, test, feedback, commit, alert |
| activity_feed | severity | info, success, warning, error |
| knowledge | knowledge_type | pattern, gotcha, best-practice, bug-fix, reference, architecture, troubleshooting, api-reference |

---

## Data Quality Recommendations

1. **Add CHECK constraints** - Enforce valid enum values at database level
2. **Add NOT NULL constraints** - Make required fields non-nullable
3. **Add business rule triggers** - Validate business rules (e.g., session end >= start)
4. **Create indexes** - Add indexes on frequently queried columns (status, project_name, created_at)
5. **Add foreign key constraints** - Enforce referential integrity (identity_id, session_id, etc.)
6. **Create views** - Add convenience views (active_sessions, pending_reminders, recent_activity)

---

**Analysis Complete**
**Next Steps:** Implement workflow tools as Python functions or MCP server tools
**Database:** PostgreSQL `claude` schema
**Version:** 1.0
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/INFRASTRUCTURE_GATEWAY_ANALYSIS.md
