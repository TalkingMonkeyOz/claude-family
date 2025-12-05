# Project Management Domain - Data Gateway Workflow Analysis

**Database Schema**: `claude`
**Analysis Date**: 2025-12-04
**Purpose**: Design specification for Data Gateway workflow tools

---

## Table of Contents

1. [Table Analyses](#table-analyses)
2. [Workflow Tool Specifications](#workflow-tool-specifications)
3. [Business Rules Summary](#business-rules-summary)
4. [Recommended Validations](#recommended-validations)

---

## Table Analyses

### 1. PROGRAMS Table

**Purpose**: Top-level grouping for projects (e.g., "Work", "Personal", "Ideas")

#### Schema
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

#### Valid Status Values
Based on actual data:
- `ACTIVE` - Program is currently active (observed in data)
- `COMPLETED` - Program has finished
- `ON_HOLD` - Program temporarily paused
- `ARCHIVED` - Program is archived

**Recommended**: Use ENUM or CHECK constraint to enforce these values.

#### Valid Priority Values
Based on actual data: **1-10** (integer scale)
- Observed values: 1, 2, 3, 4
- Lower number = higher priority
- **Recommended range**: 1 (Critical) to 5 (Low)

#### Required Fields
```sql
NOT NULL constraints needed:
- program_id (already enforced)
- program_name (should be required)
- status (should default to 'ACTIVE')
- created_at (should auto-populate)
```

#### Business Rules
1. **Unique Constraint**: `program_code` should be unique (not currently enforced)
2. **Status Lifecycle**:
   - New programs start as `ACTIVE`
   - Can transition: ACTIVE → ON_HOLD → ACTIVE
   - Can transition: ACTIVE → COMPLETED
   - Can transition: * → ARCHIVED
3. **Date Validation**: `completion_date` should only be set when status = 'COMPLETED'
4. **Cascading**: Archiving a program should cascade to its projects (warning required)

#### Relationships
- **One-to-Many**: Program → Projects (via `projects.program_id`)
- **Note**: Currently NO foreign key constraint enforced (should be added)

---

### 2. PROJECTS Table

**Purpose**: Individual projects within a program

#### Schema
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

#### Valid Status Values
Based on actual data (inconsistent casing observed):
- `ACTIVE` / `active` - Project is active
- `IN_PROGRESS` / `in_progress` - Project is being worked on
- `COMPLETED` - Project finished successfully
- `ON_HOLD` - Project paused
- `CANCELLED` - Project cancelled
- `ARCHIVED` / `archived` - Project archived

**Issue Detected**: Mixed case in data ('active' vs 'ACTIVE'). Recommend standardizing to UPPER_CASE.

#### Valid Priority Values
Based on actual data: **0-10** (integer scale)
- Observed values: 0, 1, 5, 9, NULL
- Many records have NULL priority (needs default)
- **Recommended**: 1 (Critical) to 5 (Low), with default of 3 (Medium)

#### Valid Health Status Values
```sql
- HEALTHY (green) - All metrics good
- AT_RISK (yellow) - Some concerns
- CRITICAL (red) - Major issues
- UNKNOWN (grey) - Not assessed
```

#### Valid Maturity Level Values
```sql
- PROTOTYPE - Early stage, experimental
- DEVELOPMENT - Active development
- STABLE - Production-ready, maintained
- MATURE - Well-established, documented
- LEGACY - Old but still used
- DEPRECATED - Being phased out
```

#### Required Fields
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

#### Business Rules
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

#### Relationships
- **Many-to-One**: Projects → Program (via `program_id`)
- **One-to-Many**: Project → Phases (via `phases.project_id`)
- **One-to-Many**: Project → Ideas (via `ideas.project_id`)

---

### 3. PHASES Table

**Purpose**: Sequential or parallel phases within a project (e.g., "Design", "Development", "Testing")

#### Schema
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

#### Valid Status Values
Based on actual data:
- `NOT_STARTED` - Phase not yet begun
- `IN_PROGRESS` - Phase currently active
- `COMPLETED` - Phase finished
- `BLOCKED` - Phase blocked by dependencies
- `SKIPPED` - Phase skipped (not needed)

#### Priority
**Note**: Phases do NOT have a priority field. Priority is determined by `phase_number` (sequence).

#### Required Fields
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

#### Business Rules
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

#### Relationships
- **Many-to-One**: Phases → Project (via `project_id`)
- **One-to-Many**: Phase → Tasks (via `pm_tasks.phase_id`)
- **Self-Referential**: Phase → Dependent Phases (via `dependencies` JSONB)

---

### 4. PM_TASKS Table

**Purpose**: Granular work items within a phase

#### Schema
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

#### Valid Status Values
Based on actual data:
- `TODO` - Not started (observed in data)
- `IN_PROGRESS` - Currently being worked on
- `COMPLETED` - Finished (observed in data)
- `BLOCKED` - Cannot proceed
- `CANCELLED` - Task cancelled
- `ON_HOLD` - Paused

#### Valid Priority Values
Based on actual data: **1-10** (integer scale)
- Observed values: 6, 7, 8, 9, 10
- Higher number seems to indicate higher priority (inverse of programs)
- **Issue**: Inconsistent with program priority scale
- **Recommended**: Standardize to 1 (Low) to 5 (Critical), consistent across all tables

#### Valid Task Types
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

#### Required Fields
```sql
NOT NULL constraints needed:
- task_id (enforced)
- task_name (should be required)
- status (should default to 'TODO')
- priority (should default to 3)
- created_at (should auto-populate)
```

#### Business Rules
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

#### Relationships
- **Many-to-One**: Tasks → Phase (via `phase_id`)
- **Many-to-One**: Tasks → Work Package (via `work_package_id`)
- **Self-Referential**: Task → Dependent Task (via `depends_on`)

---

### 5. IDEAS Table

**Purpose**: Capture ideas that may become tasks or phases

#### Schema
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

#### Valid Status Values
Based on actual data:
- `OPEN` - Idea submitted, not yet reviewed (observed in data)
- `UNDER_REVIEW` - Being evaluated
- `APPROVED` - Approved for implementation
- `REJECTED` - Not proceeding with idea
- `CONVERTED` - Converted to task or phase
- `DUPLICATE` - Duplicate of another idea

#### Valid Priority Values
Based on actual data: **1-10** (integer scale)
- Observed value: 5
- **Recommended**: 1 (Low) to 5 (Critical), consistent with other tables

#### Required Fields
```sql
NOT NULL constraints needed:
- idea_id (enforced)
- idea_title (should be required)
- status (should default to 'OPEN')
- created_at (should auto-populate)
- created_by (should be required)
```

#### Business Rules
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

#### Relationships
- **Many-to-One**: Ideas → Project (via `project_id`, optional)
- **One-to-One**: Idea → Phase (via `converted_to_phase_id`, optional)
- **One-to-One**: Idea → Task (via `converted_to_task_id`, optional)

---

## Workflow Tool Specifications

### Tool 1: `create_project`

**Purpose**: Create a new project with validation and defaults

#### Input Parameters
```typescript
{
  project_name: string;          // REQUIRED
  project_code: string;          // REQUIRED, must be unique
  description?: string;
  program_id?: uuid;             // Optional FK to programs
  priority?: 1-5;                // Default: 3
  start_date?: date;             // Default: TODAY
  target_date?: date;
  owner_session?: string;
  metadata?: jsonb;
}
```

#### Workflow Steps
1. **Validation**:
   - Check `project_code` is unique (case-insensitive)
   - If `program_id` provided, verify program exists and is not archived
   - Validate `target_date` >= `start_date`
   - Validate `priority` in range 1-5
2. **Defaults**:
   - `project_id` = generate UUID
   - `status` = 'ACTIVE'
   - `is_archived` = false
   - `created_at` = NOW()
   - `updated_at` = NOW()
   - `start_date` = TODAY (if not provided)
   - `priority` = 3 (if not provided)
3. **Insert** into `claude.projects`
4. **Log Activity**:
   - Insert into `claude.activity_feed`
   - Message: "Project {project_code} created"
5. **Return**: Created project object with full details

#### Error Handling
- `project_code` duplicate → Return error: "Project code already exists"
- Invalid `program_id` → Return error: "Program not found"
- Invalid dates → Return error: "Target date must be >= start date"

---

### Tool 2: `update_project_status`

**Purpose**: Change project status with validation and side effects

#### Input Parameters
```typescript
{
  project_id: uuid;              // REQUIRED
  new_status: string;            // REQUIRED, validated enum
  archive_reason?: string;       // Required if new_status = 'ARCHIVED'
  completion_date?: date;        // Required if new_status = 'COMPLETED'
}
```

#### Workflow Steps
1. **Validation**:
   - Verify project exists
   - Validate status transition is legal (see state machine below)
   - If status = 'ARCHIVED', require `archive_reason`
   - If status = 'COMPLETED', require `completion_date`
2. **Status Transition Rules**:
   ```
   ACTIVE → [IN_PROGRESS, ON_HOLD, CANCELLED, ARCHIVED]
   IN_PROGRESS → [COMPLETED, ON_HOLD, CANCELLED, ARCHIVED]
   ON_HOLD → [IN_PROGRESS, CANCELLED, ARCHIVED]
   COMPLETED → [ARCHIVED]
   CANCELLED → [ARCHIVED]
   ARCHIVED → [none - final state]
   ```
3. **Side Effects**:
   - If status = 'ARCHIVED':
     - Set `is_archived = true`
     - Set `archived_at = NOW()`
     - Set `archive_reason`
     - Archive all child phases (cascade)
   - If status = 'COMPLETED':
     - Set `completion_date`
     - Verify all phases are COMPLETED or SKIPPED
4. **Update** `claude.projects`
5. **Log Activity**
6. **Return**: Updated project with new status

#### Error Handling
- Invalid transition → Return error: "Cannot transition from {old} to {new}"
- Missing archive_reason → Return error: "Archive reason required"
- Incomplete phases → Return warning: "Project has incomplete phases"

---

### Tool 3: `add_phase`

**Purpose**: Add a new phase to a project with dependency management

#### Input Parameters
```typescript
{
  project_id: uuid;              // REQUIRED
  phase_name: string;            // REQUIRED
  phase_number?: integer;        // Auto-assign if not provided
  description?: string;
  duration_weeks?: numeric;
  can_run_parallel?: boolean;    // Default: false
  dependencies?: uuid[];         // Array of phase_ids
  assigned_to?: string;
  start_date?: date;
  target_date?: date;
}
```

#### Workflow Steps
1. **Validation**:
   - Verify project exists and is not archived
   - If `phase_number` provided, check uniqueness within project
   - If `dependencies` provided, verify all phase_ids exist in same project
   - Validate no circular dependencies
2. **Auto-Numbering**:
   - If `phase_number` not provided:
     ```sql
     SELECT COALESCE(MAX(phase_number), 0) + 1
     FROM claude.phases
     WHERE project_id = :project_id
     ```
3. **Date Calculation**:
   - If `target_date` not provided and `duration_weeks` provided:
     ```sql
     target_date = start_date + (duration_weeks * 7 days)
     ```
4. **Defaults**:
   - `phase_id` = generate UUID
   - `status` = 'NOT_STARTED'
   - `progress_percentage` = 0.00
   - `created_at` = NOW()
   - `can_run_parallel` = false (if not provided)
5. **Insert** into `claude.phases`
6. **Update Dependencies**:
   - Store dependencies as JSONB array
7. **Log Activity**
8. **Return**: Created phase object

#### Error Handling
- Project archived → Return error: "Cannot add phase to archived project"
- Duplicate phase_number → Return error: "Phase number already exists"
- Invalid dependencies → Return error: "Dependency phase not found"
- Circular dependency → Return error: "Circular dependency detected"

---

### Tool 4: `convert_idea_to_task`

**Purpose**: Convert an idea into an actionable task

#### Input Parameters
```typescript
{
  idea_id: uuid;                 // REQUIRED
  phase_id?: uuid;               // Optional - which phase to add task to
  task_name?: string;            // Default: idea.idea_title
  task_type?: string;            // Default: 'DEVELOPMENT'
  priority?: 1-5;                // Default: idea.priority
  estimated_hours?: numeric;
  assigned_to?: string;
  due_date?: date;
}
```

#### Workflow Steps
1. **Validation**:
   - Verify idea exists
   - Verify idea.status is 'APPROVED' or 'OPEN'
   - Verify idea not already converted
   - If `phase_id` provided, verify phase exists and belongs to idea's project
2. **Create Task**:
   ```sql
   INSERT INTO claude.pm_tasks (
     task_id, phase_id, task_name, description,
     task_type, status, priority, created_at
   ) VALUES (
     gen_random_uuid(),
     :phase_id,
     COALESCE(:task_name, idea.idea_title),
     idea.description,
     COALESCE(:task_type, 'DEVELOPMENT'),
     'TODO',
     COALESCE(:priority, idea.priority, 3),
     NOW()
   )
   RETURNING task_id;
   ```
3. **Update Idea**:
   ```sql
   UPDATE claude.ideas
   SET status = 'CONVERTED',
       converted_to_task_id = :new_task_id
   WHERE idea_id = :idea_id;
   ```
4. **Copy Tags** (if applicable):
   - Add idea tags to task.metadata as JSONB
5. **Log Activity**:
   - "Idea '{idea_title}' converted to task"
6. **Return**: Object with both idea and created task

#### Error Handling
- Idea already converted → Return error: "Idea already converted"
- Invalid phase → Return error: "Phase not found or doesn't belong to idea's project"
- Idea not approved → Return warning: "Idea status is {status}, not approved"

---

### Tool 5: `convert_idea_to_phase` (Additional)

**Purpose**: Convert a large idea into a project phase

#### Input Parameters
```typescript
{
  idea_id: uuid;                 // REQUIRED
  project_id?: uuid;             // Default: idea.project_id
  phase_name?: string;           // Default: idea.idea_title
  duration_weeks?: numeric;
  can_run_parallel?: boolean;
}
```

#### Workflow Steps
1. **Validation**:
   - Verify idea exists and not already converted
   - Verify project exists and not archived
   - Verify idea.status is 'APPROVED'
2. **Auto-Number Phase**:
   - Get next phase_number for project
3. **Create Phase**:
   ```sql
   INSERT INTO claude.phases (
     phase_id, project_id, phase_name, phase_number,
     description, status, progress_percentage, created_at
   ) VALUES (
     gen_random_uuid(),
     COALESCE(:project_id, idea.project_id),
     COALESCE(:phase_name, idea.idea_title),
     :next_phase_number,
     idea.description,
     'NOT_STARTED',
     0.00,
     NOW()
   )
   RETURNING phase_id;
   ```
4. **Update Idea**:
   ```sql
   UPDATE claude.ideas
   SET status = 'CONVERTED',
       converted_to_phase_id = :new_phase_id
   WHERE idea_id = :idea_id;
   ```
5. **Log Activity**
6. **Return**: Object with idea and created phase

---

## Business Rules Summary

### Cross-Table Rules

1. **Cascading Deletes** (should be enforced):
   - Deleting Program → Warning + option to delete child Projects
   - Deleting Project → Warning + option to delete child Phases/Ideas
   - Deleting Phase → Warning + option to delete child Tasks

2. **Cascading Status Updates**:
   - Archiving Project → Auto-archive all Phases
   - Completing Phase → Check if all Tasks are complete

3. **Priority Consistency**:
   - **Standardize**: 1 (Critical) to 5 (Low) across ALL tables
   - Current issue: Mixed scales (1-10, NULL values)

4. **Status Consistency**:
   - **Standardize**: UPPER_CASE for all status values
   - Current issue: Mixed case ('active' vs 'ACTIVE')

5. **Circular Dependency Prevention**:
   - Phase dependencies must be acyclic (directed acyclic graph)
   - Task dependencies must be acyclic

6. **Audit Trail**:
   - All status changes should log to `activity_feed`
   - Track who made change, when, old value, new value

---

## Recommended Validations

### Database-Level (DDL Changes Needed)

```sql
-- 1. Add Foreign Key Constraints
ALTER TABLE claude.projects
  ADD CONSTRAINT fk_projects_program
  FOREIGN KEY (program_id) REFERENCES claude.programs(program_id);

ALTER TABLE claude.phases
  ADD CONSTRAINT fk_phases_project
  FOREIGN KEY (project_id) REFERENCES claude.projects(project_id);

ALTER TABLE claude.pm_tasks
  ADD CONSTRAINT fk_tasks_phase
  FOREIGN KEY (phase_id) REFERENCES claude.phases(phase_id);

ALTER TABLE claude.ideas
  ADD CONSTRAINT fk_ideas_project
  FOREIGN KEY (project_id) REFERENCES claude.projects(project_id);

-- 2. Add Unique Constraints
ALTER TABLE claude.programs
  ADD CONSTRAINT uq_programs_code UNIQUE (program_code);

ALTER TABLE claude.projects
  ADD CONSTRAINT uq_projects_code UNIQUE (project_code);

ALTER TABLE claude.phases
  ADD CONSTRAINT uq_phases_project_number
  UNIQUE (project_id, phase_number);

-- 3. Add CHECK Constraints
ALTER TABLE claude.projects
  ADD CONSTRAINT chk_projects_status
  CHECK (status IN ('ACTIVE', 'IN_PROGRESS', 'COMPLETED', 'ON_HOLD', 'CANCELLED', 'ARCHIVED'));

ALTER TABLE claude.projects
  ADD CONSTRAINT chk_projects_priority
  CHECK (priority BETWEEN 1 AND 5);

ALTER TABLE claude.phases
  ADD CONSTRAINT chk_phases_status
  CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED', 'SKIPPED'));

ALTER TABLE claude.phases
  ADD CONSTRAINT chk_phases_progress
  CHECK (progress_percentage BETWEEN 0 AND 100);

ALTER TABLE claude.pm_tasks
  ADD CONSTRAINT chk_tasks_status
  CHECK (status IN ('TODO', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED', 'CANCELLED', 'ON_HOLD'));

ALTER TABLE claude.pm_tasks
  ADD CONSTRAINT chk_tasks_priority
  CHECK (priority BETWEEN 1 AND 5);

ALTER TABLE claude.ideas
  ADD CONSTRAINT chk_ideas_status
  CHECK (status IN ('OPEN', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'CONVERTED', 'DUPLICATE'));

ALTER TABLE claude.ideas
  ADD CONSTRAINT chk_ideas_priority
  CHECK (priority BETWEEN 1 AND 5);

-- 4. Add NOT NULL Constraints
ALTER TABLE claude.programs
  ALTER COLUMN program_name SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE claude.projects
  ALTER COLUMN project_name SET NOT NULL,
  ALTER COLUMN project_code SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE claude.phases
  ALTER COLUMN project_id SET NOT NULL,
  ALTER COLUMN phase_name SET NOT NULL,
  ALTER COLUMN phase_number SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE claude.pm_tasks
  ALTER COLUMN task_name SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE claude.ideas
  ALTER COLUMN idea_title SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN created_by SET NOT NULL;

-- 5. Add Default Values
ALTER TABLE claude.programs
  ALTER COLUMN status SET DEFAULT 'ACTIVE',
  ALTER COLUMN priority SET DEFAULT 3,
  ALTER COLUMN created_at SET DEFAULT NOW(),
  ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE claude.projects
  ALTER COLUMN status SET DEFAULT 'ACTIVE',
  ALTER COLUMN priority SET DEFAULT 3,
  ALTER COLUMN is_archived SET DEFAULT false,
  ALTER COLUMN created_at SET DEFAULT NOW(),
  ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE claude.phases
  ALTER COLUMN status SET DEFAULT 'NOT_STARTED',
  ALTER COLUMN progress_percentage SET DEFAULT 0.00,
  ALTER COLUMN can_run_parallel SET DEFAULT false,
  ALTER COLUMN created_at SET DEFAULT NOW(),
  ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE claude.pm_tasks
  ALTER COLUMN status SET DEFAULT 'TODO',
  ALTER COLUMN priority SET DEFAULT 3,
  ALTER COLUMN created_at SET DEFAULT NOW(),
  ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE claude.ideas
  ALTER COLUMN status SET DEFAULT 'OPEN',
  ALTER COLUMN priority SET DEFAULT 3,
  ALTER COLUMN created_at SET DEFAULT NOW();
```

### Application-Level (Workflow Tool Logic)

1. **Pre-Insert Validations**:
   - Check uniqueness of codes
   - Verify parent entities exist
   - Validate date ranges
   - Check for circular dependencies

2. **State Transition Validations**:
   - Enforce valid status transitions
   - Require additional fields for certain transitions
   - Prevent changes to archived entities

3. **Business Logic Validations**:
   - Cannot complete phase if tasks incomplete
   - Cannot archive program if active projects exist
   - Must convert idea before closing

4. **Audit Logging**:
   - Log all creates, updates, deletes
   - Track old/new values
   - Record user session

---

## Entity Relationship Diagram (ERD)

```
┌─────────────┐
│  PROGRAMS   │
│             │
│ program_id  │◄────┐
│ status      │     │
│ priority    │     │
└─────────────┘     │
                    │ 1:N
                    │
                ┌───┴──────────┐
                │   PROJECTS   │
                │              │
                │ project_id   │◄────┐
                │ program_id   │     │
                │ status       │     │
                │ priority     │     │
                │ is_archived  │     │ 1:N
                └──────────────┘     │
                    │                │
              1:N   │                │
            ┌───────┼────────────────┤
            │       │                │
            │       │                │
    ┌───────▼─────┐ │        ┌───────▼─────┐
    │   PHASES    │ │        │    IDEAS    │
    │             │ │        │             │
    │ phase_id    │ │        │ idea_id     │
    │ project_id  │ │        │ project_id  │
    │ phase_num   │ │        │ status      │
    │ status      │ │        │ converted_to│
    │ progress_%  │ │        │   phase_id  │──┐
    │ dependencies│ │        │   task_id   │──┼─┐
    └─────────────┘ │        └─────────────┘  │ │
            │       │                          │ │
        1:N │       │                          │ │
            │       │                          │ │
    ┌───────▼─────┐ │                          │ │
    │  PM_TASKS   │◄┘                          │ │
    │             │                            │ │
    │ task_id     │◄───────────────────────────┘ │
    │ phase_id    │                              │
    │ status      │                              │
    │ priority    │                              │
    │ depends_on  │───┐                          │
    └─────────────┘   │                          │
            ▲         │                          │
            └─────────┘                          │
            (self-reference)                     │
                                                 │
                        (converted ideas) ───────┘
```

---

## Workflow State Machines

### Project Status Transitions
```
        ┌──────┐
        │ACTIVE│
        └───┬──┘
            │
    ┌───────┼───────────┐
    │       │           │
    ▼       ▼           ▼
┌───────┐ ┌────────┐ ┌──────────┐
│ON_HOLD│ │IN_PROG │ │CANCELLED │
└───┬───┘ └───┬────┘ └────┬─────┘
    │         │           │
    └────┬────┘           │
         │                │
         ▼                │
    ┌─────────┐           │
    │COMPLETED│           │
    └────┬────┘           │
         │                │
         └────────┬───────┘
                  ▼
             ┌─────────┐
             │ARCHIVED │
             └─────────┘
               (final)
```

### Phase Status Transitions
```
┌────────────┐
│NOT_STARTED │
└─────┬──────┘
      │
      ▼
┌───────────┐◄──┐
│IN_PROGRESS│   │
└─────┬─────┘   │
      │         │
  ┌───┼────┐    │
  │   │    │    │
  ▼   ▼    ▼    │
┌────┐  ┌────┐  │
│SKIP│  │COMP│  │
└────┘  └────┘  │
                │
         ┌──────▼───┐
         │ BLOCKED  │
         └──────────┘
```

### Task Status Transitions
```
┌──────┐
│ TODO │
└───┬──┘
    │
    ▼
┌───────────┐◄──┐
│IN_PROGRESS│   │
└─────┬─────┘   │
      │         │
  ┌───┼────┐    │
  │   │    │    │
  ▼   ▼    ▼    │
┌────┐  ┌────┐  │
│CANC│  │COMP│  │
└────┘  └────┘  │
   ▲            │
   │     ┌──────▼───┐
   │     │ BLOCKED  │
   │     └──────────┘
   │            │
   │     ┌──────▼───┐
   │     │ ON_HOLD  │
   │     └──────┬───┘
   │            │
   └────────────┘
```

### Idea Status Transitions
```
┌──────┐
│ OPEN │
└───┬──┘
    │
    ▼
┌─────────────┐
│UNDER_REVIEW │
└──────┬──────┘
       │
   ┌───┼─────┐
   │   │     │
   ▼   ▼     ▼
┌────┐ ┌───┐ ┌────┐
│REJ │ │APP│ │DUP │
└────┘ └─┬─┘ └────┘
         │
         ▼
    ┌─────────┐
    │CONVERTED│
    └─────────┘
     (final)
```

---

## Sample Workflow Scenarios

### Scenario 1: Create New Project with Phases

```typescript
// Step 1: Create project
const project = await create_project({
  project_name: "Mobile App Redesign",
  project_code: "MOBILE-V2",
  description: "Complete redesign of mobile application",
  priority: 2, // High priority
  start_date: "2025-12-15",
  target_date: "2026-03-31"
});

// Step 2: Add phases
const phase1 = await add_phase({
  project_id: project.project_id,
  phase_name: "Research & Discovery",
  phase_number: 1,
  duration_weeks: 4,
  can_run_parallel: false
});

const phase2 = await add_phase({
  project_id: project.project_id,
  phase_name: "Design",
  phase_number: 2,
  duration_weeks: 6,
  dependencies: [phase1.phase_id] // Must complete phase 1 first
});

const phase3 = await add_phase({
  project_id: project.project_id,
  phase_name: "Development",
  phase_number: 3,
  duration_weeks: 12,
  dependencies: [phase2.phase_id]
});

const phase4 = await add_phase({
  project_id: project.project_id,
  phase_name: "Testing",
  phase_number: 4,
  duration_weeks: 4,
  can_run_parallel: true, // Can test while developing
  dependencies: [phase3.phase_id]
});
```

### Scenario 2: Convert Idea to Task

```typescript
// User submits idea
const idea = await createIdea({
  project_id: project.project_id,
  idea_title: "Add dark mode support",
  description: "Users have requested dark mode for better nighttime viewing",
  priority: 4,
  tags: ["feature", "ui", "accessibility"]
});

// Product manager approves idea
await updateIdeaStatus(idea.idea_id, "APPROVED");

// Convert to task in Development phase
const task = await convert_idea_to_task({
  idea_id: idea.idea_id,
  phase_id: phase3.phase_id, // Development phase
  task_type: "DEVELOPMENT",
  priority: 4,
  estimated_hours: 20,
  assigned_to: "claude-code-unified"
});

// Result: idea.status = 'CONVERTED', idea.converted_to_task_id = task.task_id
```

### Scenario 3: Complete Project

```typescript
// Mark all phases complete
await updatePhaseStatus(phase1.phase_id, "COMPLETED");
await updatePhaseStatus(phase2.phase_id, "COMPLETED");
await updatePhaseStatus(phase3.phase_id, "COMPLETED");
await updatePhaseStatus(phase4.phase_id, "COMPLETED");

// Complete project
await update_project_status({
  project_id: project.project_id,
  new_status: "COMPLETED",
  completion_date: "2026-04-05"
});

// Archive project (optional)
await update_project_status({
  project_id: project.project_id,
  new_status: "ARCHIVED",
  archive_reason: "Project successfully completed and deployed to production"
});
```

---

## Data Quality Issues Found

### 1. Inconsistent Status Casing
- **Issue**: Projects have both 'active' and 'ACTIVE'
- **Fix**: Standardize to UPPER_CASE, add CHECK constraint
- **Migration**:
  ```sql
  UPDATE claude.projects SET status = UPPER(status);
  ```

### 2. Inconsistent Priority Scales
- **Issue**: Programs use 1-4, Tasks use 6-10, many have NULL
- **Fix**: Standardize to 1-5 scale, add defaults
- **Migration**:
  ```sql
  -- Normalize tasks: 10 → 5, 8 → 3, 6 → 1
  UPDATE claude.pm_tasks
  SET priority = CASE
    WHEN priority >= 10 THEN 5
    WHEN priority >= 8 THEN 3
    WHEN priority >= 6 THEN 1
    ELSE priority
  END;

  -- Set NULL priorities to default 3
  UPDATE claude.pm_tasks SET priority = 3 WHERE priority IS NULL;
  UPDATE claude.projects SET priority = 3 WHERE priority IS NULL;
  ```

### 3. Missing Foreign Key Constraints
- **Issue**: No FK constraints enforced in database
- **Fix**: Add all FK constraints (see DDL section above)
- **Risk**: May find orphaned records

### 4. Missing Unique Constraints
- **Issue**: project_code, program_code not enforced as unique
- **Fix**: Add unique constraints after checking for duplicates

### 5. No Default Values
- **Issue**: Many required fields have NULL values
- **Fix**: Add DEFAULT clauses and backfill NULLs

---

## Performance Recommendations

### 1. Indexes Needed

```sql
-- For lookups by project
CREATE INDEX idx_phases_project_id ON claude.phases(project_id);
CREATE INDEX idx_pm_tasks_phase_id ON claude.pm_tasks(phase_id);
CREATE INDEX idx_ideas_project_id ON claude.ideas(project_id);

-- For status queries
CREATE INDEX idx_projects_status ON claude.projects(status) WHERE is_archived = false;
CREATE INDEX idx_phases_status ON claude.phases(status);
CREATE INDEX idx_pm_tasks_status ON claude.pm_tasks(status);

-- For priority sorting
CREATE INDEX idx_projects_priority ON claude.projects(priority);
CREATE INDEX idx_pm_tasks_priority ON claude.pm_tasks(priority);

-- For date range queries
CREATE INDEX idx_projects_dates ON claude.projects(start_date, target_date);
CREATE INDEX idx_pm_tasks_due_date ON claude.pm_tasks(due_date) WHERE status != 'COMPLETED';
```

### 2. Views for Common Queries

```sql
-- Active projects with phase counts
CREATE VIEW claude.v_active_projects AS
SELECT
  p.project_id,
  p.project_code,
  p.project_name,
  p.status,
  p.priority,
  pg.program_name,
  COUNT(ph.phase_id) as total_phases,
  COUNT(ph.phase_id) FILTER (WHERE ph.status = 'COMPLETED') as completed_phases,
  COUNT(DISTINCT t.task_id) as total_tasks,
  COUNT(DISTINCT t.task_id) FILTER (WHERE t.status = 'COMPLETED') as completed_tasks
FROM claude.projects p
LEFT JOIN claude.programs pg ON p.program_id = pg.program_id
LEFT JOIN claude.phases ph ON p.project_id = ph.project_id
LEFT JOIN claude.pm_tasks t ON ph.phase_id = t.phase_id
WHERE p.is_archived = false
GROUP BY p.project_id, p.project_code, p.project_name, p.status, p.priority, pg.program_name;

-- Tasks due soon
CREATE VIEW claude.v_upcoming_tasks AS
SELECT
  t.task_id,
  t.task_name,
  t.status,
  t.priority,
  t.due_date,
  t.assigned_to,
  ph.phase_name,
  p.project_code,
  p.project_name
FROM claude.pm_tasks t
JOIN claude.phases ph ON t.phase_id = ph.phase_id
JOIN claude.projects p ON ph.project_id = p.project_id
WHERE t.status NOT IN ('COMPLETED', 'CANCELLED')
  AND t.due_date IS NOT NULL
  AND t.due_date <= CURRENT_DATE + INTERVAL '7 days'
ORDER BY t.due_date, t.priority DESC;
```

---

## Testing Checklist

### Unit Tests for Workflow Tools

- [ ] `create_project` with all valid parameters
- [ ] `create_project` with duplicate project_code (should fail)
- [ ] `create_project` with invalid program_id (should fail)
- [ ] `create_project` with target_date < start_date (should fail)
- [ ] `update_project_status` with valid transition
- [ ] `update_project_status` with invalid transition (should fail)
- [ ] `update_project_status` to ARCHIVED without archive_reason (should fail)
- [ ] `update_project_status` cascades to phases
- [ ] `add_phase` auto-numbers correctly
- [ ] `add_phase` validates dependencies exist
- [ ] `add_phase` prevents circular dependencies
- [ ] `add_phase` to archived project (should fail)
- [ ] `convert_idea_to_task` creates task and updates idea
- [ ] `convert_idea_to_task` with already-converted idea (should fail)
- [ ] `convert_idea_to_task` copies tags to metadata

### Integration Tests

- [ ] Complete project lifecycle (create → phases → tasks → complete)
- [ ] Idea to task to completion workflow
- [ ] Multi-phase project with dependencies
- [ ] Archive project with all children
- [ ] Update priorities across hierarchy

---

## Next Steps

1. **Database Schema Updates**:
   - Run DDL migrations to add constraints
   - Backfill NULL values with defaults
   - Normalize priority values

2. **Implement Workflow Tools**:
   - Create stored procedures or application functions
   - Add validation logic
   - Implement state machines

3. **Build Data Gateway Layer**:
   - Create TypeScript/C# interfaces
   - Implement tool definitions for Claude Code
   - Add audit logging

4. **Create UI Components** (if applicable):
   - Project creation form
   - Status update buttons
   - Idea conversion workflow

5. **Documentation**:
   - API documentation for each tool
   - Workflow diagrams
   - User guide

---

**Analysis Complete**: 2025-12-04
**Database**: PostgreSQL `ai_company_foundation.claude`
**Analyst**: Claude (Sonnet 4.5)
