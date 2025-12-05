# Data Gateway Master Plan

**Version**: 1.0
**Created**: 2025-12-04
**Author**: claude-code-unified
**Status**: Draft - Pending Implementation

---

## Executive Summary

The Data Gateway is an architectural pattern to ensure data quality and consistency across the Claude Family system. Instead of allowing direct SQL writes to tables, all data modifications go through validated workflow tools that enforce business rules, check data quality, and maintain consistency.

### The Problem

1. **Inconsistent data**: Status fields have random values (`in_progress` vs `active` vs `ACTIVE`)
2. **Missing relationships**: Features created without projects, tasks without features
3. **No validation**: Any value accepted, no business rule enforcement
4. **Forgotten updates**: Claude instances forget to update build tracker, log sessions, etc.
5. **Duplicate data**: Same information entered differently by different instances

### The Solution

```
┌─────────────────────┐
│  Claude Instance    │
│  or MCW UI          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA GATEWAY LAYER                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Orchestrator    │  │ Validation      │  │ column_     │ │
│  │ Workflow Tools  │──│ Layer (Haiku/   │──│ registry    │ │
│  │ (MCP endpoints) │  │ Local AI)       │  │ (rules)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    POSTGRESQL DATABASE                       │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ CHECK           │  │ Tables with     │                   │
│  │ Constraints     │  │ enforced FKs    │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Domain Analysis Summary

### 4 Domains Identified

| Domain | Tables | Workflow Tools | Priority |
|--------|--------|----------------|----------|
| **Build Tracker** | features, components, build_tasks, requirements | 9 tools | HIGH |
| **Project Management** | projects, programs, phases, pm_tasks, ideas | 8 tools | HIGH |
| **Feedback & Docs** | feedback, feedback_comments, documents, document_projects | 7 tools | MEDIUM |
| **Infrastructure** | sessions, messages, identities, scheduled_jobs, reminders, knowledge, activity_feed | 12 tools | MEDIUM |

**Total: 36 workflow tools across 20 tables**

---

## Standardized Valid Values

### Status Fields (All Tables)

| Table | Field | Valid Values |
|-------|-------|--------------|
| projects | status | `active`, `on_hold`, `completed`, `archived` |
| programs | status | `active`, `on_hold`, `completed`, `archived` |
| features | status | `not_started`, `planned`, `in_progress`, `blocked`, `completed`, `cancelled` |
| components | status | `planned`, `in_progress`, `completed`, `blocked` |
| build_tasks | status | `todo`, `in_progress`, `completed`, `blocked`, `cancelled` |
| requirements | status | `defined`, `in_progress`, `verified`, `failed` |
| phases | status | `not_started`, `in_progress`, `completed`, `blocked`, `skipped` |
| pm_tasks | status | `todo`, `in_progress`, `completed`, `blocked`, `cancelled` |
| ideas | status | `open`, `under_review`, `approved`, `rejected`, `converted`, `duplicate` |
| feedback | status | `new`, `in_progress`, `resolved`, `wont_fix`, `duplicate` |
| documents | status | `DRAFT`, `ACTIVE`, `ARCHIVED`, `DEPRECATED` |
| sessions | status | `active`, `ended`, `abandoned` |
| messages | status | `pending`, `read`, `acknowledged`, `expired` |
| reminders | status | `pending`, `completed`, `dismissed`, `snoozed` |
| scheduled_jobs | last_status | `SUCCESS`, `FAILED`, `RUNNING`, `SKIPPED` |
| identities | status | `active`, `archived` |

### Priority Fields

**Standardize to 1-5 scale across ALL tables:**
- `1` = Critical
- `2` = High
- `3` = Medium
- `4` = Low
- `5` = Nice-to-have

### Type Fields

| Table | Field | Valid Values |
|-------|-------|--------------|
| features | feature_type | `system`, `ui`, `feature`, `enhancement`, `integration`, `bugfix` |
| components | component_type | `page`, `component`, `service`, `hook`, `api`, `store`, `layout`, `dialog`, `module` |
| build_tasks | task_type | `code`, `test`, `docs`, `review`, `deploy`, `config` |
| requirements | requirement_type | `functional`, `ui`, `data`, `api`, `performance`, `security` |
| feedback | feedback_type | `bug`, `design`, `question`, `change` |
| documents | doc_type | `ARCHITECTURE`, `README`, `SOP`, `GUIDE`, `API`, `SPEC`, `SESSION_NOTE`, `ADR`, `REFERENCE`, `TROUBLESHOOTING`, `COMPLETION_REPORT`, `CLAUDE_CONFIG`, `TEST_DOC`, `MIGRATION`, `ARCHIVE`, `OTHER` |
| messages | message_type | `task_request`, `status_update`, `question`, `notification`, `handoff`, `broadcast` |
| messages | priority | `urgent`, `normal`, `low` |
| scheduled_jobs | job_type | `sync`, `backup`, `audit`, `maintenance`, `indexer`, `health_check`, `security` |
| scheduled_jobs | trigger_type | `session_start`, `session_end`, `schedule`, `on_demand` |
| knowledge | knowledge_type | `pattern`, `gotcha`, `best-practice`, `bug-fix`, `reference`, `architecture`, `troubleshooting`, `api-reference` |
| activity_feed | activity_type | `session_started`, `session_ended`, `message_sent`, `feature_completed`, `task_completed`, `feedback_created`, `document_added` |
| activity_feed | severity | `info`, `warning`, `error`, `success` |

---

## Workflow Tools Specification

### Build Tracker Domain (9 tools)

#### 1. `add_feature`
```
Input:
  - project_id: uuid (required, must exist)
  - feature_name: string (required, min 5 chars)
  - feature_type: enum (required)
  - description: string (required, min 20 chars)
  - priority: int 1-5 (default 3)

Validation:
  - Project must exist and not be archived
  - Feature name unique within project
  - Description quality check (meaningful, not placeholder)

Side Effects:
  - Sets status = 'not_started'
  - Sets created_at = NOW()
  - Logs to activity_feed

Returns:
  - feature_id on success
  - Error message on validation failure
```

#### 2. `update_feature_status`
```
Input:
  - feature_id: uuid (required)
  - new_status: enum (required)
  - notes: string (optional, required if blocked/cancelled)

Validation:
  - Feature must exist
  - Status transition must be valid:
    not_started -> planned, cancelled
    planned -> in_progress, blocked, cancelled
    in_progress -> completed, blocked, on_hold
    blocked -> in_progress (requires unblock reason)
  - If completed: all components must be completed
  - If blocked: must provide blocked_reason

Side Effects:
  - Updates started_date when -> in_progress
  - Updates completed_date when -> completed
  - Logs to activity_feed
  - Notifies assigned identity
```

#### 3. `add_component`
```
Input:
  - feature_id: uuid (required, must exist)
  - component_name: string (required)
  - component_type: enum (required)
  - file_path: string (optional)

Validation:
  - Feature must exist and not be completed
  - Component name unique within feature

Side Effects:
  - Sets status = 'planned'
  - Recalculates feature completion_percentage
```

#### 4. `add_task`
```
Input:
  - feature_id: uuid (required)
  - component_id: uuid (optional)
  - task_name: string (required, min 10 chars)
  - task_description: string (required, min 30 chars)
  - task_type: enum (required)
  - priority: int 1-5 (default 3)
  - estimated_hours: decimal (optional)

Validation:
  - Feature must exist
  - If component_id provided, must belong to feature
  - Description must be actionable (quality check)

Quality Checks:
  - Task description should start with verb
  - Should include acceptance criteria or "done when"
  - Reject generic descriptions like "Fix bug" or "Update code"
```

#### 5. `complete_task`
```
Input:
  - task_id: uuid (required)
  - actual_hours: decimal (optional)
  - notes: string (optional)

Validation:
  - Task must exist and be in_progress
  - Task must not be blocked

Side Effects:
  - Sets status = 'completed'
  - Sets completed_at = NOW()
  - Recalculates component completion
  - Recalculates feature completion_percentage
  - Logs to activity_feed
```

### Project Management Domain (8 tools)

#### 6. `create_project`
```
Input:
  - project_name: string (required, min 3 chars)
  - project_code: string (required, uppercase, 2-10 chars)
  - program_id: uuid (optional)
  - description: string (required, min 20 chars)
  - priority: int 1-5 (default 3)

Validation:
  - project_code must be unique
  - If program_id provided, must exist
  - No duplicate project names

Side Effects:
  - Sets status = 'active'
  - Sets is_archived = false
  - Logs to activity_feed
```

#### 7. `update_project_status`
```
Input:
  - project_id: uuid (required)
  - new_status: enum (required)
  - reason: string (required if on_hold/archived)

Validation:
  - Valid transitions only:
    active -> on_hold, completed, archived
    on_hold -> active, archived
    completed -> archived
  - Cannot un-archive (create new project instead)

Side Effects:
  - If archived: sets archived_at, archive_reason
  - Updates updated_at
  - Logs to activity_feed
```

#### 8. `add_phase`
#### 9. `convert_idea_to_task`
#### 10. `archive_project`

### Feedback & Docs Domain (7 tools)

#### 11. `create_feedback`
```
Input:
  - project_id: uuid (required)
  - feedback_type: enum (required: bug, design, question, change)
  - description: string (required)
  - priority: enum (high, medium, low)
  - screenshot_paths: array (optional)

Validation:
  - Project must exist and be active
  - For bugs: description min 50 chars, should include:
    - Steps to reproduce
    - Expected vs actual behavior
  - Priority required for bugs

Quality Checks (AI validation):
  - Is this a duplicate of existing feedback?
  - Does description have enough detail?
  - Should this be a feature request instead of bug?
```

#### 12. `resolve_feedback`
```
Input:
  - feedback_id: uuid (required)
  - resolution: enum (resolved, wont_fix, duplicate)
  - notes: string (required, min 20 chars)
  - duplicate_of: uuid (required if resolution=duplicate)

Validation:
  - Feedback must exist and be new/in_progress
  - Notes must explain resolution
```

#### 13. `register_document`
#### 14. `link_document_to_project`
#### 15. `add_feedback_comment`
#### 16. `archive_document`

### Infrastructure Domain (12 tools)

#### 17. `start_session`
```
Input:
  - identity_id: uuid (required)
  - project_name: string (required)

Validation:
  - Identity must exist and be active
  - Project must exist

Side Effects:
  - Creates session record
  - Updates identity.last_active_at
  - Checks for pending messages
  - Checks for due reminders
  - Checks for due scheduled_jobs
  - Logs to activity_feed
```

#### 18. `end_session`
```
Input:
  - session_id: uuid (required)
  - summary: string (required, min 50 chars)
  - tasks_completed: array (optional)
  - learnings_gained: string (optional)

Validation:
  - Session must exist and be active
  - Summary must be meaningful (quality check)

Side Effects:
  - Sets session_end = NOW()
  - Saves session_state for resume
  - Logs to activity_feed
```

#### 19. `send_message`
#### 20. `acknowledge_message`
#### 21. `create_reminder`
#### 22. `complete_reminder`
#### 23. `record_knowledge`
#### 24. `log_activity`
#### 25. `execute_scheduled_job`

---

## Validation Layer Architecture

### Option A: Haiku AI Validator (Recommended for complex checks)

```python
# Pseudo-code for validation layer
def validate_with_ai(tool_name: str, inputs: dict) -> ValidationResult:
    """Use Claude Haiku for complex quality checks"""

    # Get validation rules from column_registry
    rules = get_validation_rules(tool_name)

    # Build prompt with ONLY the relevant schema
    prompt = f"""
    You are validating input for {tool_name}.

    Rules:
    {rules}

    Input to validate:
    {inputs}

    Check:
    1. Are all required fields present?
    2. Are enum values valid?
    3. Is description detailed enough?
    4. Any quality issues?

    Return JSON: {{"valid": bool, "errors": [], "suggestions": []}}
    """

    return call_haiku(prompt)
```

**When to use AI validation:**
- Description quality checks ("is this detailed enough?")
- Duplicate detection ("does similar item exist?")
- Routing suggestions ("this should be X not Y")
- Format validation ("task should start with verb")

### Option B: Rule-based Validation (For simple checks)

```python
def validate_with_rules(tool_name: str, inputs: dict) -> ValidationResult:
    """Fast rule-based validation from column_registry"""

    errors = []

    # Get valid values from column_registry
    valid_values = get_valid_values(tool_name)

    for field, value in inputs.items():
        if field in valid_values:
            if value not in valid_values[field]:
                errors.append(f"{field} must be one of: {valid_values[field]}")

        if is_required(field) and not value:
            errors.append(f"{field} is required")

    return ValidationResult(valid=len(errors)==0, errors=errors)
```

**When to use rule-based:**
- Enum validation (status, type, priority)
- Required field checks
- Format validation (length, pattern)
- Relationship validation (FK exists)

### Hybrid Approach

```
Input → Rule-based validation (fast, cheap)
         ↓
      Pass? → AI validation (quality checks)
         ↓
      Pass? → Database write (with CHECK constraints as safety net)
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [x] Create column_registry table
- [ ] Populate column_registry with all valid values
- [ ] Add CHECK constraints to critical tables
- [ ] Standardize existing data to valid values

### Phase 2: Core Tools (Week 2)
- [ ] Implement 5 highest-priority tools in orchestrator:
  - `create_project`
  - `add_feature`
  - `add_task`
  - `create_feedback`
  - `start_session` / `end_session`
- [ ] Add rule-based validation layer
- [ ] Test with manual usage

### Phase 3: AI Validation (Week 3)
- [ ] Add Haiku validation for quality checks
- [ ] Implement duplicate detection
- [ ] Add routing suggestions
- [ ] Test with various input quality levels

### Phase 4: Full Rollout (Week 4)
- [ ] Implement remaining workflow tools
- [ ] Update MCW to use workflow tools
- [ ] Update CLAUDE.md with new procedures
- [ ] Monitor and tune validation rules

---

## Database Changes Required

### CHECK Constraints to Add

```sql
-- Projects
ALTER TABLE claude.projects
ADD CONSTRAINT chk_projects_status
CHECK (status IN ('active', 'on_hold', 'completed', 'archived'));

-- Features
ALTER TABLE claude.features
ADD CONSTRAINT chk_features_status
CHECK (status IN ('not_started', 'planned', 'in_progress', 'blocked', 'completed', 'cancelled'));

ALTER TABLE claude.features
ADD CONSTRAINT chk_features_type
CHECK (feature_type IN ('system', 'ui', 'feature', 'enhancement', 'integration', 'bugfix'));

-- Build Tasks
ALTER TABLE claude.build_tasks
ADD CONSTRAINT chk_tasks_status
CHECK (status IN ('todo', 'in_progress', 'completed', 'blocked', 'cancelled'));

-- Feedback
ALTER TABLE claude.feedback
ADD CONSTRAINT chk_feedback_status
CHECK (status IN ('new', 'in_progress', 'resolved', 'wont_fix', 'duplicate'));

ALTER TABLE claude.feedback
ADD CONSTRAINT chk_feedback_type
CHECK (feedback_type IN ('bug', 'design', 'question', 'change'));

-- Messages
ALTER TABLE claude.messages
ADD CONSTRAINT chk_messages_status
CHECK (status IN ('pending', 'read', 'acknowledged', 'expired'));

-- Priority (all tables using priority)
-- Standardize to 1-5 across all tables
```

### Data Cleanup Required

```sql
-- Standardize project status
UPDATE claude.projects SET status = 'active' WHERE status = 'in_progress';
UPDATE claude.projects SET status = lower(status) WHERE status != lower(status);

-- Standardize component status
UPDATE claude.components SET status = 'completed' WHERE status = 'complete';

-- Standardize priority to 1-5 scale
UPDATE claude.features SET priority = LEAST(priority, 5) WHERE priority > 5;
UPDATE claude.build_tasks SET priority = LEAST(priority, 5) WHERE priority > 5;
```

---

## Success Metrics

1. **Data Quality**: Zero invalid status/type values in database
2. **Consistency**: All Claude instances use same workflow tools
3. **Completeness**: Build tracker always updated when work done
4. **Traceability**: All changes logged to activity_feed
5. **Adoption**: 100% of writes go through Data Gateway within 2 weeks

---

## Related Documents

- `BUILD_TRACKER_DATA_GATEWAY_SPEC.md` - Detailed Build Tracker analysis
- `PM_DOMAIN_DATA_GATEWAY_ANALYSIS.md` - Project Management analysis
- `DATA_GATEWAY_DOMAIN_ANALYSIS.md` - Feedback & Docs analysis
- `INFRASTRUCTURE_GATEWAY_ANALYSIS.md` - Infrastructure analysis
- `DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md` - SQL implementations
- `DATA_GATEWAY_QUICK_REFERENCE.md` - Quick reference guide

---

## Appendix: column_registry Schema

```sql
CREATE TABLE claude.column_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    is_nullable BOOLEAN DEFAULT true,
    description TEXT,
    valid_values JSONB,           -- ["value1", "value2", ...]
    default_value TEXT,
    example_value TEXT,
    constraints TEXT,             -- CHECK constraint definition
    min_length INTEGER,           -- For string quality checks
    max_length INTEGER,
    quality_rules JSONB,          -- AI validation rules
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(table_name, column_name)
);
```

---

**Next Steps:**
1. Review and approve this plan
2. Populate column_registry with all values
3. Add CHECK constraints
4. Implement first 5 workflow tools
5. Message MCW with integration requirements
