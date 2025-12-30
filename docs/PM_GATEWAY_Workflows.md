# PM Domain - Workflow Tool Specifications

**Database Schema**: `claude`
**Purpose**: Detailed specifications for Data Gateway workflow tools

See [[PM_GATEWAY_Overview]] for navigation and introduction.

---

## Tool 1: `create_project`

**Purpose**: Create a new project with validation and defaults

### Input Parameters
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

### Workflow Steps
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

### Error Handling
- `project_code` duplicate → Return error: "Project code already exists"
- Invalid `program_id` → Return error: "Program not found"
- Invalid dates → Return error: "Target date must be >= start date"

---

## Tool 2: `update_project_status`

**Purpose**: Change project status with validation and side effects

### Input Parameters
```typescript
{
  project_id: uuid;              // REQUIRED
  new_status: string;            // REQUIRED, validated enum
  archive_reason?: string;       // Required if new_status = 'ARCHIVED'
  completion_date?: date;        // Required if new_status = 'COMPLETED'
}
```

### Workflow Steps
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

### Error Handling
- Invalid transition → Return error: "Cannot transition from {old} to {new}"
- Missing archive_reason → Return error: "Archive reason required"
- Incomplete phases → Return warning: "Project has incomplete phases"

---

## Tool 3: `add_phase`

**Purpose**: Add a new phase to a project with dependency management

### Input Parameters
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

### Workflow Steps
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

### Error Handling
- Project archived → Return error: "Cannot add phase to archived project"
- Duplicate phase_number → Return error: "Phase number already exists"
- Invalid dependencies → Return error: "Dependency phase not found"
- Circular dependency → Return error: "Circular dependency detected"

---

## Tool 4: `convert_idea_to_task`

**Purpose**: Convert an idea into an actionable task

### Input Parameters
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

### Workflow Steps
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

### Error Handling
- Idea already converted → Return error: "Idea already converted"
- Invalid phase → Return error: "Phase not found or doesn't belong to idea's project"
- Idea not approved → Return warning: "Idea status is {status}, not approved"

---

## Tool 5: `convert_idea_to_phase` (Additional)

**Purpose**: Convert a large idea into a project phase

### Input Parameters
```typescript
{
  idea_id: uuid;                 // REQUIRED
  project_id?: uuid;             // Default: idea.project_id
  phase_name?: string;           // Default: idea.idea_title
  duration_weeks?: numeric;
  can_run_parallel?: boolean;
}
```

### Workflow Steps
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

**Version**: 2.0
**Created**: 2025-12-04
**Updated**: 2025-12-26
**Location**: docs/PM_GATEWAY_Workflows.md
