# PM Domain - Design & Quality Assessment

**Database Schema**: `claude`
**Purpose**: Architecture diagrams, quality analysis, and recommendations

See [[PM_GATEWAY_Overview]] for navigation and introduction.

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
- **Fix**: Add all FK constraints (see PM_GATEWAY_Workflows.md for DDL)
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

---

**Version**: 2.0
**Created**: 2025-12-04
**Updated**: 2025-12-26
**Location**: docs/PM_GATEWAY_Design_Quality.md
