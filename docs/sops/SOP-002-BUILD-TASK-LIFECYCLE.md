# SOP-002: Build Task Lifecycle

**Version:** 1.0
**Created:** 2025-12-03
**Status:** Active
**Author:** claude-code-unified

---

## Purpose

Define the lifecycle, statuses, priorities, and rules for managing build tasks in `claude.build_tasks`.

---

## Task Types

| Type | Use For |
|------|---------|
| `code` | Feature implementation, bug fixes, refactoring |
| `test` | Writing tests, test infrastructure |

---

## Task Statuses

```
todo → in_progress → completed
         ↓
       blocked
```

| Status | Meaning |
|--------|---------|
| `todo` | Not started, in backlog |
| `in_progress` | Currently being worked on |
| `completed` | Done and verified |
| `blocked` | Cannot proceed, needs resolution |

### Status Transition Rules
- `todo` → `in_progress`: When starting work
- `in_progress` → `completed`: When code merged and tested
- `in_progress` → `blocked`: When external dependency blocks progress
- `blocked` → `in_progress`: When blocker resolved
- Any → `todo`: To restart/reprioritize

---

## Priority Levels

| Priority | Level | Response Time | Examples |
|----------|-------|---------------|----------|
| 1-2 | Critical | Immediate | Production down, security issue |
| 3-4 | High | Same day | Major bug, blocking feature |
| 5 | Normal | This sprint | Standard feature work |
| 6-7 | Low | Next sprint | Nice to have, improvements |
| 8-10 | Backlog | When time permits | Tech debt, cleanup |

### Priority Assignment Rules
- Default new tasks to priority 5
- Only use 1-2 for actual emergencies
- Backlog items (8-10) reviewed monthly

---

## Required Fields

Every build task MUST have:

| Field | Type | Description |
|-------|------|-------------|
| `task_name` | VARCHAR(255) | Short, descriptive name |
| `task_type` | VARCHAR(50) | `code` or `test` |
| `status` | VARCHAR(50) | Current status |
| `priority` | INTEGER | 1-10 priority level |

---

## Optional Fields

| Field | Type | When to Use |
|-------|------|-------------|
| `task_description` | TEXT | Complex tasks needing detail |
| `component_id` | UUID | When modifying specific component |
| `feature_id` | UUID | When part of a feature |
| `assigned_to` | VARCHAR(100) | When delegating work |
| `estimated_hours` | DECIMAL | For planning |
| `actual_hours` | DECIMAL | For retrospectives |

---

## Creating Tasks

### Minimal Task
```sql
INSERT INTO claude.build_tasks (task_name, task_type, status, priority)
VALUES ('Fix login timeout bug', 'code', 'todo', 4);
```

### Full Task
```sql
INSERT INTO claude.build_tasks (
    task_name, task_description, task_type, status, priority,
    component_id, feature_id, assigned_to
) VALUES (
    'Add password strength indicator',
    'Implement real-time password strength meter on registration form. Show weak/medium/strong with color coding.',
    'code',
    'todo',
    5,
    'component-uuid-here',
    'feature-uuid-here',
    'claude-mcw'
);
```

---

## Task Queries

### My Active Tasks
```sql
SELECT task_name, status, priority
FROM claude.build_tasks
WHERE status IN ('todo', 'in_progress')
ORDER BY priority, created_at;
```

### Blocked Tasks
```sql
SELECT task_name, task_description, status
FROM claude.build_tasks
WHERE status = 'blocked';
```

### Task Completion Report
```sql
SELECT
    DATE(updated_at) as completed_date,
    COUNT(*) as tasks_completed
FROM claude.build_tasks
WHERE status = 'completed'
GROUP BY DATE(updated_at)
ORDER BY completed_date DESC;
```

---

## Workflow Integration

### Starting a Task
1. Set status to `in_progress`
2. Note start time (optional)
3. Link to relevant components/features

### Completing a Task
1. Verify code works
2. Set status to `completed`
3. Update `actual_hours` if tracked
4. Link to any KNOWLEDGE entries if lessons learned

### Blocking a Task
1. Set status to `blocked`
2. Update `task_description` with blocker details
3. Create follow-up task if needed

---

## MCW Integration

The MCW Build Tracker page displays tasks from this table:
- Filter by status, priority, type
- Drag-and-drop status changes
- Bulk priority updates

---

## Related SOPs
- SOP-001: Knowledge vs Documents vs Tasks
- SOP-003: Document Classification

---

**Revision History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-03 | Initial version |
