# PM Domain - Table Analyses

**Database Schema**: `claude`
**Purpose**: Detailed schema specification for PM domain tables

See [[PM_GATEWAY_Overview]] for navigation and introduction.

---

## 1. PROGRAMS Table

**Purpose**: Top-level grouping for projects (e.g., "Work", "Personal", "Ideas")

### Schema
```sql
program_id          uuid PRIMARY KEY NOT NULL
program_name        varchar
program_code        varchar
description         text
status              varchar
priority            integer
start_date          date
target_date         date
completion_date     date
owner_session       varchar
created_at          timestamp
updated_at          timestamp
metadata            jsonb
color               varchar
icon                varchar
sort_order          integer
```

### Valid Status Values
Based on actual data:
- `ACTIVE` - Program is currently active (observed in data)
- `COMPLETED` - Program has finished
- `ON_HOLD` - Program temporarily paused
- `ARCHIVED` - Program is archived

**Recommended**: Use ENUM or CHECK constraint to enforce these values.

### Valid Priority Values
Based on actual data: **1-10** (integer scale)
- Observed values: 1, 2, 3, 4
- Lower number = higher priority
- **Recommended range**: 1 (Critical) to 5 (Low)

### Required Fields
```sql
NOT NULL constraints needed:
- program_id (already enforced)
- program_name (should be required)
- status (should default to 'ACTIVE')
- created_at (should auto-populate)
```

### Business Rules
1. **Unique Constraint**: `program_code` should be unique (not currently enforced)
2. **Status Lifecycle**:
   - New programs start as `ACTIVE`
   - Can transition: ACTIVE → ON_HOLD → ACTIVE
   - Can transition: ACTIVE → COMPLETED
   - Can transition: * → ARCHIVED
3. **Date Validation**: `completion_date` should only be set when status = 'COMPLETED'
4. **Cascading**: Archiving a program should cascade to its projects (warning required)

### Relationships
- **One-to-Many**: Program → Projects (via `projects.program_id`)
- **Note**: Currently NO foreign key constraint enforced (should be added)

---

## 2. PROJECTS Table

**Purpose**: Individual projects within a program

### Schema
```sql
project_id              uuid PRIMARY KEY NOT NULL
program_id              uuid (FK to programs)
project_name            varchar
project_code            varchar
description             text
status                  varchar
priority                integer
start_date              date
target_date             date
completion_date         date
owner_session           varchar
created_at              timestamp
updated_at              timestamp
metadata                jsonb
last_audit_date         timestamp
next_audit_due          timestamp
health_status           varchar
maturity_level          varchar
audit_required          boolean
audit_reason            text
code_lines              integer
documentation_score     integer
test_coverage           integer
tech_debt_score         integer
is_archived             boolean (default: false)
archived_at             timestamp
archive_reason          text
```

### Valid Status Values
Based on actual data (inconsistent casing observed):
- `ACTIVE` / `active` - Project is active
- `IN_PROGRESS` / `in_progress` - Project is being worked on
- `COMPLETED` - Project finished successfully
- `ON_HOLD` - Project paused
- `CANCELLED` - Project cancelled
- `ARCHIVED` / `archived` - Project archived

**Issue Detected**: Mixed case in data ('active' vs 'ACTIVE'). Recommend standardizing to UPPER_CASE.

### Valid Priority Values
Based on actual data: **0-10** (integer scale)
- Observed values: 0, 1, 5, 9, NULL
- Many records have NULL priority (needs default)
- **Recommended**: 1 (Critical) to 5 (Low), with default of 3 (Medium)

### Valid Health Status Values
```sql
- HEALTHY (green) - All metrics good
- AT_RISK (yellow) - Some concerns
- CRITICAL (red) - Major issues
- UNKNOWN (grey) - Not assessed
```

### Valid Maturity Level Values
```sql
- PROTOTYPE - Early stage, experimental
- DEVELOPMENT - Active development
- STABLE - Production-ready, maintained
- MATURE - Well-established, documented
- LEGACY - Old but still used
- DEPRECATED - Being phased out
```

### Required Fields
```sql
NOT NULL constraints needed:
- project_id (enforced)
- project_name (should be required)
- project_code (should be required)
- status (should default to 'ACTIVE')
- created_at (should auto-populate)
- updated_at (should auto-populate on change)
- is_archived (already has default: false)
```

### Business Rules
1. **Unique Constraint**: `project_code` must be unique across all projects
2. **Status Lifecycle**:
   ```
   ACTIVE → IN_PROGRESS → COMPLETED
   ACTIVE → ON_HOLD → IN_PROGRESS
   * → CANCELLED
   * → ARCHIVED (sets is_archived = true)
   ```
3. **Archival Rules**:
   - When `status` = 'ARCHIVED', must set `is_archived = true` and `archived_at = NOW()`
   - `archive_reason` should be required when archiving
   - Archived projects cannot be edited (enforce in application logic)
4. **Date Validation**:
   - `target_date` >= `start_date`
   - `completion_date` only set when status = 'COMPLETED'
5. **Program Association**:
   - `program_id` is optional (projects can exist without a program)
   - If set, must reference valid program
6. **Health Status Auto-Calculation** (suggested):
   ```
   HEALTHY: test_coverage >= 80, tech_debt_score <= 3, documentation_score >= 7
   AT_RISK: test_coverage 50-79, tech_debt_score 4-7
   CRITICAL: test_coverage < 50, tech_debt_score > 7
   ```

### Relationships
- **Many-to-One**: Projects → Program (via `program_id`)
- **One-to-Many**: Project → Phases (via `phases.project_id`)
- **One-to-Many**: Project → Ideas (via `ideas.project_id`)

---

## 3. PHASES Table

**Purpose**: Sequential or parallel phases within a project (e.g., "Design", "Development", "Testing")

### Schema
```sql
phase_id            uuid PRIMARY KEY NOT NULL
project_id          uuid (FK to projects)
phase_name          varchar
phase_number        integer
description         text
status              varchar
start_date          date
target_date         date
completion_date     date
duration_weeks      numeric
can_run_parallel    boolean
dependencies        jsonb
assigned_to         varchar
progress_percentage numeric
created_at          timestamp
updated_at          timestamp
metadata            jsonb
```

### Valid Status Values
Based on actual data:
- `NOT_STARTED` - Phase not yet begun
- `IN_PROGRESS` - Phase currently active
- `COMPLETED` - Phase finished
- `BLOCKED` - Phase blocked by dependencies
- `SKIPPED` - Phase skipped (not needed)

### Priority
**Note**: Phases do NOT have a priority field. Priority is determined by `phase_number` (sequence).

### Required Fields
```sql
NOT NULL constraints needed:
- phase_id (enforced)
- project_id (should be required - FK)
- phase_name (should be required)
- phase_number (should be required)
- status (should default to 'NOT_STARTED')
- progress_percentage (should default to 0.00)
- can_run_parallel (should default to false)
- created_at (should auto-populate)
```

### Business Rules
1. **Project Association**:
   - `project_id` is REQUIRED
   - Must reference valid, non-archived project
2. **Phase Numbering**:
   - `phase_number` must be unique within a project
   - Sequential phases: 1, 2, 3, etc.
   - Determines execution order
3. **Status Lifecycle**:
   ```
   NOT_STARTED → IN_PROGRESS → COMPLETED
   NOT_STARTED → SKIPPED
   IN_PROGRESS → BLOCKED → IN_PROGRESS
   ```
4. **Dependency Management**:
   - `dependencies` is JSONB array of phase_ids: `["uuid1", "uuid2"]`
   - Phase can only start when all dependency phases are COMPLETED
   - If `can_run_parallel = true`, phase can run concurrently with others
5. **Progress Validation**:
   - `progress_percentage` must be 0-100
   - When status = 'COMPLETED', progress must = 100
   - When status = 'NOT_STARTED', progress must = 0
6. **Date Validation**:
   - `completion_date` only set when status = 'COMPLETED'
   - `target_date` should be calculated from `duration_weeks` if not set

### Relationships
- **Many-to-One**: Phases → Project (via `project_id`)
- **One-to-Many**: Phase → Tasks (via `pm_tasks.phase_id`)
- **Self-Referential**: Phase → Dependent Phases (via `dependencies` JSONB)

---

## 4. PM_TASKS Table

**Purpose**: Granular work items within a phase

### Schema
```sql
task_id             uuid PRIMARY KEY NOT NULL
phase_id            uuid (FK to phases)
work_package_id     uuid (FK to work_packages - different domain)
task_name           varchar
description         text
task_type           varchar
status              varchar
priority            integer
start_date          date
due_date            date
completion_date     date
estimated_hours     numeric
actual_hours        numeric
assigned_to         varchar
depends_on          uuid (FK to pm_tasks - self-reference)
created_at          timestamp
updated_at          timestamp
metadata            jsonb
```

### Valid Status Values
Based on actual data:
- `TODO` - Not started (observed in data)
- `IN_PROGRESS` - Currently being worked on
- `COMPLETED` - Finished (observed in data)
- `BLOCKED` - Cannot proceed
- `CANCELLED` - Task cancelled
- `ON_HOLD` - Paused

### Valid Priority Values
Based on actual data: **1-10** (integer scale)
- Observed values: 6, 7, 8, 9, 10
- Higher number seems to indicate higher priority (inverse of programs)
- **Issue**: Inconsistent with program priority scale
- **Recommended**: Standardize to 1 (Low) to 5 (Critical), consistent across all tables

### Valid Task Types
```sql
- DEVELOPMENT - Code development (observed in data)
- TESTING - Testing work
- DOCUMENTATION - Documentation work
- DESIGN - Design work
- RESEARCH - Research/investigation
- BUG_FIX - Bug fix
- DEPLOYMENT - Deployment work
- REVIEW - Code/design review
```

### Required Fields
```sql
NOT NULL constraints needed:
- task_id (enforced)
- task_name (should be required)
- status (should default to 'TODO')
- priority (should default to 3)
- created_at (should auto-populate)
```

### Business Rules
1. **Parent Association**:
   - Must have EITHER `phase_id` OR `work_package_id` (not both, not neither)
   - If `phase_id` set, must reference valid phase
2. **Status Lifecycle**:
   ```
   TODO → IN_PROGRESS → COMPLETED
   TODO → CANCELLED
   IN_PROGRESS → BLOCKED → IN_PROGRESS
   IN_PROGRESS → ON_HOLD → IN_PROGRESS
   ```
3. **Dependency Management**:
   - `depends_on` references another task's `task_id`
   - Cannot start until dependent task is COMPLETED
   - Circular dependencies must be prevented
4. **Time Tracking**:
   - `actual_hours` should only be set when status = 'COMPLETED' or 'IN_PROGRESS'
   - Variance = `actual_hours - estimated_hours` (track in application)
5. **Date Validation**:
   - `completion_date` only when status = 'COMPLETED'
   - `due_date` >= `start_date`
6. **Assignment**:
   - `assigned_to` should reference valid session/user (not enforced currently)

### Relationships
- **Many-to-One**: Tasks → Phase (via `phase_id`)
- **Many-to-One**: Tasks → Work Package (via `work_package_id`)
- **Self-Referential**: Task → Dependent Task (via `depends_on`)

---

## 5. IDEAS Table

**Purpose**: Capture ideas that may become tasks or phases

### Schema
```sql
idea_id                 uuid PRIMARY KEY NOT NULL
project_id              uuid (FK to projects)
idea_title              varchar
description             text
tags                    text[] (array)
priority                integer
status                  varchar
converted_to_phase_id   uuid (FK to phases)
converted_to_task_id    uuid (FK to pm_tasks)
created_at              timestamp
created_by              varchar
metadata                jsonb
```

### Valid Status Values
Based on actual data:
- `OPEN` - Idea submitted, not yet reviewed (observed in data)
- `UNDER_REVIEW` - Being evaluated
- `APPROVED` - Approved for implementation
- `REJECTED` - Not proceeding with idea
- `CONVERTED` - Converted to task or phase
- `DUPLICATE` - Duplicate of another idea

### Valid Priority Values
Based on actual data: **1-10** (integer scale)
- Observed value: 5
- **Recommended**: 1 (Low) to 5 (Critical), consistent with other tables

### Required Fields
```sql
NOT NULL constraints needed:
- idea_id (enforced)
- idea_title (should be required)
- status (should default to 'OPEN')
- created_at (should auto-populate)
- created_by (should be required)
```

### Business Rules
1. **Project Association**:
   - `project_id` is optional (ideas can be unassigned)
   - If set, should reference valid project
2. **Status Lifecycle**:
   ```
   OPEN → UNDER_REVIEW → APPROVED → CONVERTED
   OPEN → UNDER_REVIEW → REJECTED
   OPEN → DUPLICATE
   ```
3. **Conversion Tracking**:
   - When status = 'CONVERTED':
     - Must set EITHER `converted_to_phase_id` OR `converted_to_task_id`
     - Cannot set both
     - Cannot unconvert (one-way operation)
4. **Tag Management**:
   - `tags` is PostgreSQL text array
   - Standardize tags (e.g., lowercase, no spaces)
   - Suggested tags: ["feature", "bug", "enhancement", "research"]
5. **Priority Auto-Assignment**:
   - Default priority = 3 (Medium)
   - Can be changed during review

### Relationships
- **Many-to-One**: Ideas → Project (via `project_id`, optional)
- **One-to-One**: Idea → Phase (via `converted_to_phase_id`, optional)
- **One-to-One**: Idea → Task (via `converted_to_task_id`, optional)

---

**Version**: 2.0
**Created**: 2025-12-04
**Updated**: 2025-12-26
**Location**: docs/PM_GATEWAY_Table_Analysis.md
